from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.enums import TaskStatus
from src.domain.models._serialization import parse_datetime, serialize_value, utcnow
from src.domain.models.tool_response import ToolResponse


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    status: TaskStatus
    output: Any = None
    error: str | None = None
    error_code: str | None = None
    tool_calls: list[ToolResponse] = field(default_factory=list)
    execution_duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=utcnow)

    def is_success(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    def is_failure(self) -> bool:
        return self.status in {
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "output": serialize_value(self.output),
            "error": self.error,
            "error_code": self.error_code,
            "tool_calls": [tool_call.to_dict() for tool_call in self.tool_calls],
            "execution_duration_ms": self.execution_duration_ms,
            "metadata": serialize_value(self.metadata),
            "completed_at": self.completed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskResult":
        return cls(
            task_id=data["task_id"],
            status=TaskStatus(data["status"]),
            output=data.get("output"),
            error=data.get("error"),
            error_code=data.get("error_code"),
            tool_calls=[
                ToolResponse.from_dict(item) for item in data.get("tool_calls", [])
            ],
            execution_duration_ms=int(data.get("execution_duration_ms", 0)),
            metadata=dict(data.get("metadata", {})),
            completed_at=parse_datetime(data.get("completed_at")) or utcnow(),
        )

