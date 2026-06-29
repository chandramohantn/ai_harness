from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.enums import ToolStatus
from src.domain.models._serialization import parse_datetime, serialize_value, utcnow


@dataclass(frozen=True)
class ToolResponse:
    request_id: str
    tool_name: str
    status: ToolStatus
    output: Any = None
    error: str | None = None
    error_code: str | None = None
    execution_duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=utcnow)

    def is_success(self) -> bool:
        return self.status == ToolStatus.SUCCESS

    def is_failure(self) -> bool:
        return not self.is_success()

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "output": serialize_value(self.output),
            "error": self.error,
            "error_code": self.error_code,
            "execution_duration_ms": self.execution_duration_ms,
            "metadata": serialize_value(self.metadata),
            "completed_at": self.completed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolResponse":
        return cls(
            request_id=data["request_id"],
            tool_name=data["tool_name"],
            status=ToolStatus(data["status"]),
            output=data.get("output"),
            error=data.get("error"),
            error_code=data.get("error_code"),
            execution_duration_ms=int(data.get("execution_duration_ms", 0)),
            metadata=dict(data.get("metadata", {})),
            completed_at=parse_datetime(data.get("completed_at")) or utcnow(),
        )

