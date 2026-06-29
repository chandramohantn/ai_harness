from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.enums import MemoryOperation
from src.domain.models._serialization import serialize_value


@dataclass(frozen=True)
class MemoryRequest:
    request_id: str
    operation: MemoryOperation
    namespace: str
    key: str
    value: Any = None
    session_id: str = ""
    task_id: str | None = None
    ttl_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "operation": self.operation.value,
            "namespace": self.namespace,
            "key": self.key,
            "value": serialize_value(self.value),
            "session_id": self.session_id,
            "task_id": self.task_id,
            "ttl_seconds": self.ttl_seconds,
            "metadata": serialize_value(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryRequest":
        return cls(
            request_id=data["request_id"],
            operation=MemoryOperation(data["operation"]),
            namespace=data["namespace"],
            key=data["key"],
            value=data.get("value"),
            session_id=data.get("session_id", ""),
            task_id=data.get("task_id"),
            ttl_seconds=data.get("ttl_seconds"),
            metadata=dict(data.get("metadata", {})),
        )

