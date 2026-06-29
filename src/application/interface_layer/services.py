"""Concrete interface-layer services.

The implementations in this module validate raw requests, manage sessions,
transform incoming payloads into domain models, and delegate execution to the
orchestrator.
"""

from __future__ import annotations

from typing import Any

from src.domain.enums import TaskPriority, TaskStatus
from src.domain.models import TaskContext, TaskRequest, TaskResult
from src.domain.models._serialization import new_id, utcnow
from src.interfaces.interface_layer import (
    InterfaceManager,
    RequestTransformer,
    RequestValidator,
    Session,
    SessionManager,
    ValidationResult,
    ValidationRule,
)
from src.interfaces.orchestration import Orchestrator, StateManager


class RequiredFieldsValidationRule(ValidationRule):
    """Validate that a raw request contains a fixed set of fields."""

    def __init__(self, required_fields: list[str]) -> None:
        self._required_fields = required_fields

    def validate(self, raw_input: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for field in self._required_fields:
            if field not in raw_input:
                errors.append(f"Missing required field: {field}")
        return errors


class DefaultRequestValidator(RequestValidator):
    """Apply registered validation rules to incoming raw requests."""

    def __init__(self, rules: list[ValidationRule] | None = None) -> None:
        self._rules: list[ValidationRule] = rules or [
            RequiredFieldsValidationRule(["task_type", "payload"])
        ]

    def validate_request(self, raw_input: dict[str, object]) -> ValidationResult:
        errors: list[str] = []
        for rule in self._rules:
            errors.extend(rule.validate(dict(raw_input)))
        if "payload" in raw_input and not isinstance(raw_input["payload"], dict):
            errors.append("Field 'payload' must be a dictionary")
        if "metadata" in raw_input and not isinstance(raw_input["metadata"], dict):
            errors.append("Field 'metadata' must be a dictionary")
        return ValidationResult(is_valid=not errors, errors=errors)

    def register_rule(self, rule: ValidationRule) -> None:
        self._rules.append(rule)

    def get_rules(self) -> list[ValidationRule]:
        return list(self._rules)


class DefaultRequestTransformer(RequestTransformer):
    """Transform validated raw input into domain request and context objects."""

    def to_task_request(
        self, raw_input: dict[str, Any], session_id: str
    ) -> TaskRequest:
        priority_value = raw_input.get("priority", TaskPriority.NORMAL.value)
        priority = (
            priority_value
            if isinstance(priority_value, TaskPriority)
            else TaskPriority(str(priority_value))
        )
        metadata = dict(raw_input.get("metadata", {}))
        metadata.setdefault("submitted_at", utcnow().isoformat())
        return TaskRequest(
            task_id=str(raw_input.get("task_id", new_id())),
            session_id=session_id,
            task_type=str(raw_input["task_type"]),
            payload=dict(raw_input.get("payload", {})),
            metadata=metadata,
            priority=priority,
            timeout_seconds=raw_input.get("timeout_seconds"),
        )

    def to_task_context(self, task_request: TaskRequest) -> TaskContext:
        context = TaskContext(
            task_id=task_request.task_id,
            session_id=task_request.session_id,
        )
        context.add_attribute("task_type", task_request.task_type)
        context.add_attribute("priority", task_request.priority.value)
        context.add_attribute("request_metadata", dict(task_request.metadata))
        return context


class InMemorySessionManager(SessionManager):
    """Manage session lifecycle using in-memory storage."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create_session(self, metadata: dict[str, Any] | None = None) -> str:
        session_id = new_id()
        self._sessions[session_id] = Session(
            session_id=session_id,
            metadata=dict(metadata or {}),
        )
        return session_id

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, data: dict[str, Any]) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown session_id: {session_id}")
        session.metadata.update(data)
        session.updated_at = utcnow()

    def close_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown session_id: {session_id}")
        session.is_active = False
        session.updated_at = utcnow()

    def session_exists(self, session_id: str) -> bool:
        return session_id in self._sessions


class DefaultInterfaceManager(InterfaceManager):
    """Coordinate validation, session handling, transformation, and execution."""

    def __init__(
        self,
        request_validator: RequestValidator,
        session_manager: SessionManager,
        request_transformer: RequestTransformer,
        orchestrator: Orchestrator,
        state_manager: StateManager,
    ) -> None:
        self._request_validator = request_validator
        self._session_manager = session_manager
        self._request_transformer = request_transformer
        self._orchestrator = orchestrator
        self._state_manager = state_manager

    def submit_task(self, raw_input: dict[str, Any]) -> TaskResult:
        validation = self._request_validator.validate_request(raw_input)
        if not validation.is_valid:
            raise ValueError("; ".join(validation.errors))

        session_id = str(raw_input.get("session_id", ""))
        if session_id:
            if not self._session_manager.session_exists(session_id):
                raise ValueError(f"Unknown session_id: {session_id}")
        else:
            session_id = self._session_manager.create_session(
                metadata=dict(raw_input.get("metadata", {}))
            )

        task_request = self._request_transformer.to_task_request(raw_input, session_id)
        task_context = self._request_transformer.to_task_context(task_request)
        self._session_manager.update_session(
            session_id,
            {
                "last_task_id": task_request.task_id,
                "last_task_type": task_request.task_type,
            },
        )
        return self._orchestrator.execute_task(task_request, task_context)

    def get_task_status(self, task_id: str) -> TaskStatus:
        state = self._state_manager.get_state(task_id)
        if state is None:
            raise KeyError(f"Unknown task_id: {task_id}")
        return state.status

    def cancel_task(self, task_id: str) -> bool:
        state = self._state_manager.get_state(task_id)
        if state is None:
            return False
        if state.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
        }:
            return False
        state.transition_to(TaskStatus.CANCELLED)
        self._state_manager.save_state(state)
        cancel_method = getattr(self._orchestrator, "cancel_task", None)
        if callable(cancel_method):
            cancel_method(task_id)
        return True
