from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.enums import TaskPriority
from src.domain.models._serialization import parse_datetime, serialize_value, utcnow


@dataclass(frozen=True)
class TaskRequest:
    task_id: str
    session_id: str
    task_type: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=utcnow)
    timeout_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "task_type": self.task_type,
            "payload": serialize_value(self.payload),
            "metadata": serialize_value(self.metadata),
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskRequest":
        return cls(
            task_id=data["task_id"],
            session_id=data["session_id"],
            task_type=data["task_type"],
            payload=dict(data.get("payload", {})),
            metadata=dict(data.get("metadata", {})),
            priority=TaskPriority(data.get("priority", TaskPriority.NORMAL.value)),
            created_at=parse_datetime(data.get("created_at")) or utcnow(),
            timeout_seconds=data.get("timeout_seconds"),
        )

