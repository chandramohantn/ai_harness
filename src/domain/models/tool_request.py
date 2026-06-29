from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.models._serialization import parse_datetime, serialize_value, utcnow


@dataclass(frozen=True)
class ToolRequest:
    request_id: str
    tool_name: str
    parameters: dict[str, Any]
    task_id: str
    session_id: str
    timeout_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "parameters": serialize_value(self.parameters),
            "task_id": self.task_id,
            "session_id": self.session_id,
            "timeout_seconds": self.timeout_seconds,
            "metadata": serialize_value(self.metadata),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolRequest":
        return cls(
            request_id=data["request_id"],
            tool_name=data["tool_name"],
            parameters=dict(data.get("parameters", {})),
            task_id=data["task_id"],
            session_id=data["session_id"],
            timeout_seconds=data.get("timeout_seconds"),
            metadata=dict(data.get("metadata", {})),
            created_at=parse_datetime(data.get("created_at")) or utcnow(),
        )

