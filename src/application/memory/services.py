"""Concrete memory services for the MVP runtime.

The implementations in this module provide an in-memory backend plus working
memory, session memory, a unified memory service, and context assembly logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from src.domain.enums import MemoryOperation, MemoryStatus
from src.domain.models import MemoryRequest, MemoryResponse, TaskContext, TaskRequest, ToolResponse
from src.domain.models._serialization import new_id, utcnow
from src.interfaces.memory import (
    ContextAssembler,
    MemoryBackend,
    MemoryService,
    SessionMemory,
    WorkingMemory,
)


@dataclass
class _StoredValue:
    value: Any
    expires_at: datetime | None = None

    def is_expired(self) -> bool:
        return self.expires_at is not None and utcnow() >= self.expires_at


class InMemoryMemoryBackend(MemoryBackend):
    """Store namespaced key-value memory records in process memory."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, _StoredValue]] = {}

    def _get_namespace(self, namespace: str) -> dict[str, _StoredValue]:
        return self._data.setdefault(namespace, {})

    def _purge_expired(self, namespace: str) -> None:
        bucket = self._data.get(namespace, {})
        expired = [key for key, stored in bucket.items() if stored.is_expired()]
        for key in expired:
            del bucket[key]

    def get(self, namespace: str, key: str) -> Any | None:
        self._purge_expired(namespace)
        stored = self._data.get(namespace, {}).get(key)
        return None if stored is None else stored.value

    def set(
        self, namespace: str, key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        expires_at = (
            utcnow() + timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None
        )
        self._get_namespace(namespace)[key] = _StoredValue(value=value, expires_at=expires_at)

    def delete(self, namespace: str, key: str) -> bool:
        self._purge_expired(namespace)
        bucket = self._data.get(namespace, {})
        if key not in bucket:
            return False
        del bucket[key]
        return True

    def exists(self, namespace: str, key: str) -> bool:
        self._purge_expired(namespace)
        return key in self._data.get(namespace, {})

    def list_keys(self, namespace: str) -> list[str]:
        self._purge_expired(namespace)
        return sorted(self._data.get(namespace, {}).keys())

    def clear(self, namespace: str) -> None:
        self._data.pop(namespace, None)

    def flush_all(self) -> None:
        self._data.clear()


class DefaultWorkingMemory(WorkingMemory):
    """Manage task-scoped transient memory on top of the backend."""

    def __init__(self, backend: MemoryBackend) -> None:
        self._backend = backend

    @staticmethod
    def _namespace(task_id: str) -> str:
        return f"working:{task_id}"

    def set(self, task_id: str, key: str, value: Any) -> None:
        self._backend.set(self._namespace(task_id), key, value)

    def get(self, task_id: str, key: str) -> Any | None:
        return self._backend.get(self._namespace(task_id), key)

    def has(self, task_id: str, key: str) -> bool:
        return self._backend.exists(self._namespace(task_id), key)

    def delete(self, task_id: str, key: str) -> None:
        self._backend.delete(self._namespace(task_id), key)

    def get_all(self, task_id: str) -> dict[str, Any]:
        namespace = self._namespace(task_id)
        return {key: self._backend.get(namespace, key) for key in self._backend.list_keys(namespace)}

    def clear(self, task_id: str) -> None:
        self._backend.clear(self._namespace(task_id))


class DefaultSessionMemory(SessionMemory):
    """Manage session-scoped history entries on top of the backend."""

    def __init__(self, backend: MemoryBackend) -> None:
        self._backend = backend

    @staticmethod
    def _namespace(session_id: str) -> str:
        return f"session:{session_id}:history"

    def add_entry(self, session_id: str, entry: dict[str, Any]) -> None:
        stored_entry = dict(entry)
        stored_entry.setdefault("entry_id", new_id())
        stored_entry.setdefault("timestamp", utcnow().isoformat())
        self._backend.set(self._namespace(session_id), stored_entry["entry_id"], stored_entry)

    def get_history(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        namespace = self._namespace(session_id)
        entries = [
            dict(self._backend.get(namespace, key))
            for key in self._backend.list_keys(namespace)
            if self._backend.get(namespace, key) is not None
        ]
        entries.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
        return entries[:limit] if limit is not None else entries

    def get_entry(self, session_id: str, entry_id: str) -> dict[str, Any] | None:
        entry = self._backend.get(self._namespace(session_id), entry_id)
        return None if entry is None else dict(entry)

    def clear_history(self, session_id: str) -> None:
        self._backend.clear(self._namespace(session_id))

    def get_summary(self, session_id: str) -> dict[str, Any]:
        history = self.get_history(session_id)
        return {
            "session_id": session_id,
            "entry_count": len(history),
            "last_activity": history[0]["timestamp"] if history else None,
        }


class DefaultMemoryService(MemoryService):
    """Expose a unified orchestration-facing memory API."""

    def __init__(
        self,
        working_memory: WorkingMemory,
        session_memory: SessionMemory,
        backend: MemoryBackend,
    ) -> None:
        self._working_memory = working_memory
        self._session_memory = session_memory
        self._backend = backend

    def _scoped_namespace(self, namespace: str, session_id: str) -> str:
        return f"{namespace}:{session_id}"

    def store(self, request: MemoryRequest) -> MemoryResponse:
        try:
            if request.namespace == "working":
                if request.task_id is None:
                    raise ValueError("working namespace requires task_id")
                self._working_memory.set(request.task_id, request.key, request.value)
            elif request.namespace == "session":
                payload = request.value if isinstance(request.value, dict) else {"value": request.value}
                payload.setdefault("entry_id", request.key)
                self._session_memory.add_entry(request.session_id, payload)
            else:
                self._backend.set(
                    self._scoped_namespace(request.namespace, request.session_id),
                    request.key,
                    request.value,
                    request.ttl_seconds,
                )
            return MemoryResponse(
                request_id=request.request_id,
                operation=MemoryOperation.WRITE,
                status=MemoryStatus.SUCCESS,
                value=request.value,
            )
        except Exception as error:
            return MemoryResponse(
                request_id=request.request_id,
                operation=MemoryOperation.WRITE,
                status=MemoryStatus.FAILED,
                error=str(error),
            )

    def retrieve(self, request: MemoryRequest) -> MemoryResponse:
        try:
            value: Any | None
            if request.namespace == "working":
                if request.task_id is None:
                    raise ValueError("working namespace requires task_id")
                value = self._working_memory.get(request.task_id, request.key)
            elif request.namespace == "session":
                value = self._session_memory.get_entry(request.session_id, request.key)
            else:
                value = self._backend.get(
                    self._scoped_namespace(request.namespace, request.session_id), request.key
                )
            status = MemoryStatus.SUCCESS if value is not None else MemoryStatus.NOT_FOUND
            return MemoryResponse(
                request_id=request.request_id,
                operation=MemoryOperation.READ,
                status=status,
                value=value,
            )
        except Exception as error:
            return MemoryResponse(
                request_id=request.request_id,
                operation=MemoryOperation.READ,
                status=MemoryStatus.FAILED,
                error=str(error),
            )

    def delete(self, request: MemoryRequest) -> MemoryResponse:
        try:
            deleted = False
            if request.namespace == "working":
                if request.task_id is None:
                    raise ValueError("working namespace requires task_id")
                deleted = self._working_memory.has(request.task_id, request.key)
                self._working_memory.delete(request.task_id, request.key)
            elif request.namespace == "session":
                deleted = self._backend.delete(
                    DefaultSessionMemory._namespace(request.session_id), request.key
                )
            else:
                deleted = self._backend.delete(
                    self._scoped_namespace(request.namespace, request.session_id),
                    request.key,
                )
            return MemoryResponse(
                request_id=request.request_id,
                operation=MemoryOperation.DELETE,
                status=MemoryStatus.SUCCESS if deleted else MemoryStatus.NOT_FOUND,
            )
        except Exception as error:
            return MemoryResponse(
                request_id=request.request_id,
                operation=MemoryOperation.DELETE,
                status=MemoryStatus.FAILED,
                error=str(error),
            )

    def list_keys(self, namespace: str, session_id: str) -> list[str]:
        if namespace == "session":
            return [entry["entry_id"] for entry in self._session_memory.get_history(session_id)]
        return self._backend.list_keys(self._scoped_namespace(namespace, session_id))

    def clear_namespace(self, namespace: str, session_id: str) -> None:
        if namespace == "session":
            self._session_memory.clear_history(session_id)
        else:
            self._backend.clear(self._scoped_namespace(namespace, session_id))


class DefaultContextAssembler(ContextAssembler):
    """Build and update task execution context from memory sources."""

    def __init__(
        self,
        working_memory: WorkingMemory,
        session_memory: SessionMemory,
        memory_service: MemoryService,
    ) -> None:
        self._working_memory = working_memory
        self._session_memory = session_memory
        self._memory_service = memory_service

    def assemble_context(self, task_request: TaskRequest, session_id: str) -> TaskContext:
        context = TaskContext(task_id=task_request.task_id, session_id=session_id)
        context.add_attribute("task_type", task_request.task_type)
        context.add_attribute("payload", dict(task_request.payload))
        context.add_attribute("metadata", dict(task_request.metadata))
        for entry in self._session_memory.get_history(session_id):
            context.append_history(entry)
        context.set_memory_snapshot(self._working_memory.get_all(task_request.task_id))
        return context

    def update_context(self, context: TaskContext, tool_result: ToolResponse) -> TaskContext:
        context.append_tool_result(tool_result)
        context.add_attribute("last_tool_name", tool_result.tool_name)
        context.add_attribute("last_tool_status", tool_result.status.value)
        snapshot = dict(context.memory_snapshot)
        snapshot[f"tool_result:{tool_result.request_id}"] = tool_result.to_dict()
        context.set_memory_snapshot(snapshot)
        return context

    def finalize_context(self, context: TaskContext) -> TaskContext:
        snapshot = dict(context.memory_snapshot)
        snapshot["finalized_at"] = utcnow().isoformat()
        context.set_memory_snapshot(snapshot)
        return context
