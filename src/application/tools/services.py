"""Concrete tool services and example tool implementations.

This module provides registry, validation, permission, routing, and execution
services along with a few MVP tool implementations.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from time import perf_counter
from typing import Any

from src.domain.enums import EventSeverity, EventType, ToolStatus
from src.domain.models import ObservationEvent, TaskRequest, ToolRequest, ToolResponse
from src.domain.models._serialization import new_id, utcnow
from src.interfaces.interface_layer import ValidationResult
from src.interfaces.observability import ObservationManager
from src.interfaces.tools import (
    BaseTool,
    ToolExecutor,
    ToolPermissionManager,
    ToolPolicy,
    ToolRegistry,
    ToolRouter,
    ToolValidator,
)


def _schema_errors(schema: dict[str, Any], parameters: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = schema.get("required", [])
    for key in required:
        if key not in parameters:
            errors.append(f"Missing required parameter: {key}")
    type_map: dict[str, tuple[type, ...]] = {
        "string": (str,),
        "integer": (int,),
        "number": (int, float),
        "boolean": (bool,),
        "object": (dict,),
        "array": (list,),
    }
    properties = schema.get("properties", {})
    for key, definition in properties.items():
        if key not in parameters or "type" not in definition:
            continue
        expected = type_map.get(definition["type"])
        if expected and not isinstance(parameters[key], expected):
            errors.append(
                f"Parameter '{key}' must be of type {definition['type']}"
            )
    return errors


def _task_request_from_tool_request(request: ToolRequest) -> TaskRequest:
    raw = request.metadata.get("task_request")
    if isinstance(raw, dict):
        return TaskRequest.from_dict(raw)
    return TaskRequest(
        task_id=request.task_id,
        session_id=request.session_id,
        task_type="tool_call",
        payload={"tool_name": request.tool_name, "parameters": request.parameters},
    )


class InMemoryToolRegistry(ToolRegistry):
    """Register and resolve tool instances in process memory."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        self._tools.pop(tool_name, None)

    def get_tool(self, tool_name: str) -> BaseTool | None:
        return self._tools.get(tool_name)

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def get_tool_schemas(self) -> dict[str, dict[str, object]]:
        return {name: tool.schema for name, tool in self._tools.items()}


class DefaultToolValidator(ToolValidator):
    """Validate tool requests and normalized responses."""

    def validate_request(
        self, request: ToolRequest, tool: BaseTool
    ) -> ValidationResult:
        return tool.validate_input(request.parameters)

    def validate_response(self, response: ToolResponse, tool: BaseTool) -> bool:
        if not response.is_success():
            return True
        return tool.validate_output(response.output)


class AllowAllToolPermissionManager(ToolPermissionManager):
    """Permit all tool usage unless a registered policy denies it."""

    def __init__(self) -> None:
        self._policies: list[ToolPolicy] = []

    def is_permitted(self, tool_name: str, task_request: TaskRequest) -> bool:
        return self.get_denied_reason(tool_name, task_request) is None

    def get_denied_reason(self, tool_name: str, task_request: TaskRequest) -> str | None:
        for policy in self._policies:
            decision = policy.evaluate(tool_name, task_request)
            if not decision.allowed:
                return decision.reason or f"Tool {tool_name} is not permitted"
        return None

    def register_policy(self, policy: ToolPolicy) -> None:
        self._policies.append(policy)


class DefaultToolExecutor(ToolExecutor):
    """Execute tools with validation, permission checks, and observability."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        tool_validator: ToolValidator,
        tool_permission_manager: ToolPermissionManager,
        observation_manager: ObservationManager,
    ) -> None:
        self._tool_registry = tool_registry
        self._tool_validator = tool_validator
        self._tool_permission_manager = tool_permission_manager
        self._observation_manager = observation_manager

    def execute(self, request: ToolRequest) -> ToolResponse:
        started = perf_counter()
        tool = self._tool_registry.get_tool(request.tool_name)
        if tool is None:
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.FAILED,
                error=f"Unknown tool: {request.tool_name}",
                error_code="tool_not_found",
            )

        task_request = _task_request_from_tool_request(request)
        denied_reason = self._tool_permission_manager.get_denied_reason(
            request.tool_name, task_request
        )
        if denied_reason is not None:
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.PERMISSION_DENIED,
                error=denied_reason,
                error_code="permission_denied",
            )

        validation = self._tool_validator.validate_request(request, tool)
        if not validation.is_valid:
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.VALIDATION_ERROR,
                error="; ".join(validation.errors),
                error_code="validation_error",
            )

        self._observation_manager.record_event(
            ObservationEvent(
                event_id=new_id(),
                event_type=EventType.TOOL_INVOKED,
                source="tool_executor",
                task_id=request.task_id,
                session_id=request.session_id,
                severity=EventSeverity.INFO,
                message=f"Invoking tool {request.tool_name}",
                data={"parameters": request.parameters},
            )
        )

        try:
            response = tool.execute(request)
            duration_ms = int((perf_counter() - started) * 1000)
            if response.execution_duration_ms == 0:
                response = ToolResponse(
                    request_id=response.request_id,
                    tool_name=response.tool_name,
                    status=response.status,
                    output=response.output,
                    error=response.error,
                    error_code=response.error_code,
                    execution_duration_ms=duration_ms,
                    metadata=response.metadata,
                    completed_at=response.completed_at,
                )
            if not self._tool_validator.validate_response(response, tool):
                return ToolResponse(
                    request_id=request.request_id,
                    tool_name=request.tool_name,
                    status=ToolStatus.FAILED,
                    error="Tool output failed validation",
                    error_code="output_validation_failed",
                    execution_duration_ms=duration_ms,
                )
            self._observation_manager.record_event(
                ObservationEvent(
                    event_id=new_id(),
                    event_type=EventType.TOOL_COMPLETED,
                    source="tool_executor",
                    task_id=request.task_id,
                    session_id=request.session_id,
                    severity=EventSeverity.INFO,
                    message=f"Completed tool {request.tool_name}",
                    data={"status": response.status.value, "duration_ms": duration_ms},
                )
            )
            return response
        except Exception as error:
            duration_ms = int((perf_counter() - started) * 1000)
            self._observation_manager.record_event(
                ObservationEvent(
                    event_id=new_id(),
                    event_type=EventType.TOOL_FAILED,
                    source="tool_executor",
                    task_id=request.task_id,
                    session_id=request.session_id,
                    severity=EventSeverity.ERROR,
                    message=f"Tool {request.tool_name} failed",
                    data={"error": str(error), "duration_ms": duration_ms},
                )
            )
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.FAILED,
                error=str(error),
                error_code="tool_execution_failed",
                execution_duration_ms=duration_ms,
            )

    async def execute_async(self, request: ToolRequest) -> ToolResponse:
        return await asyncio.to_thread(self.execute, request)


class DefaultToolRouter(ToolRouter):
    """Resolve a tool request and dispatch it through the executor."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        tool_permission_manager: ToolPermissionManager,
    ) -> None:
        self._tool_registry = tool_registry
        self._tool_executor = tool_executor
        self._tool_permission_manager = tool_permission_manager

    def route_request(self, request: ToolRequest) -> ToolResponse:
        if not self._tool_registry.has_tool(request.tool_name):
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.FAILED,
                error=f"Unknown tool: {request.tool_name}",
                error_code="tool_not_found",
            )
        return self._tool_executor.execute(request)


class FilesystemTool(BaseTool):
    """Read, write, and list files under a configured root path."""

    def __init__(self, root_path: str | Path | None = None) -> None:
        self._root_path = Path(root_path or ".").resolve()

    def get_name(self) -> str:
        return "filesystem"

    def get_description(self) -> str:
        return "Read, write, and list files under a configured root path."

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["action", "path"],
            "properties": {
                "action": {"type": "string"},
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
        }

    def validate_input(self, parameters: dict[str, Any]) -> ValidationResult:
        errors = _schema_errors(self.get_schema(), parameters)
        action = parameters.get("action")
        if action not in {"read", "write", "list"}:
            errors.append("Parameter 'action' must be one of: read, write, list")
        if action == "write" and "content" not in parameters:
            errors.append("Parameter 'content' is required for write action")
        return ValidationResult(is_valid=not errors, errors=errors)

    def execute(self, request: ToolRequest) -> ToolResponse:
        action = str(request.parameters["action"])
        relative_path = str(request.parameters["path"])
        target = (self._root_path / relative_path).resolve()
        if not str(target).startswith(str(self._root_path)):
            raise ValueError("Path escapes the configured filesystem root")
        if action == "read":
            output: Any = target.read_text()
        elif action == "write":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(request.parameters["content"]))
            output = {"path": str(target), "written": True}
        else:
            if target.is_dir():
                output = sorted(child.name for child in target.iterdir())
            else:
                output = []
        return ToolResponse(
            request_id=request.request_id,
            tool_name=self.get_name(),
            status=ToolStatus.SUCCESS,
            output=output,
            completed_at=utcnow(),
        )

    def validate_output(self, output: Any) -> bool:
        return isinstance(output, (str, dict, list))


class SearchTool(BaseTool):
    """Search file contents under a configured root path."""

    def __init__(self, root_path: str | Path | None = None) -> None:
        self._root_path = Path(root_path or ".").resolve()

    def get_name(self) -> str:
        return "search"

    def get_description(self) -> str:
        return "Search file contents under a configured root path."

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "pattern": {"type": "string"},
            },
        }

    def validate_input(self, parameters: dict[str, Any]) -> ValidationResult:
        errors = _schema_errors(self.get_schema(), parameters)
        return ValidationResult(is_valid=not errors, errors=errors)

    def execute(self, request: ToolRequest) -> ToolResponse:
        query = str(request.parameters["query"])
        pattern = str(request.parameters.get("pattern", "**/*"))
        matches: list[dict[str, Any]] = []
        for path in self._root_path.glob(pattern):
            if not path.is_file():
                continue
            try:
                content = path.read_text()
            except UnicodeDecodeError:
                continue
            if query in content:
                matches.append(
                    {
                        "path": str(path.relative_to(self._root_path)),
                        "match_count": content.count(query),
                    }
                )
        return ToolResponse(
            request_id=request.request_id,
            tool_name=self.get_name(),
            status=ToolStatus.SUCCESS,
            output=matches,
            completed_at=utcnow(),
        )

    def validate_output(self, output: Any) -> bool:
        return isinstance(output, list)


class EchoTool(BaseTool):
    """Return the supplied value unchanged."""

    def get_name(self) -> str:
        return "echo"

    def get_description(self) -> str:
        return "Return the supplied value unchanged."

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["value"],
            "properties": {"value": {}},
        }

    def validate_input(self, parameters: dict[str, Any]) -> ValidationResult:
        errors = [] if "value" in parameters else ["Missing required parameter: value"]
        return ValidationResult(is_valid=not errors, errors=errors)

    def execute(self, request: ToolRequest) -> ToolResponse:
        return ToolResponse(
            request_id=request.request_id,
            tool_name=self.get_name(),
            status=ToolStatus.SUCCESS,
            output=request.parameters["value"],
            completed_at=utcnow(),
        )

    def validate_output(self, output: Any) -> bool:
        return True
