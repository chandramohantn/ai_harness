from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.models._serialization import parse_datetime, serialize_value, utcnow
from src.domain.models.tool_response import ToolResponse


@dataclass
class TaskContext:
    task_id: str
    session_id: str
    attributes: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[ToolResponse] = field(default_factory=list)
    memory_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)

    def add_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def get_attribute(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)

    def has_attribute(self, key: str) -> bool:
        return key in self.attributes

    def append_history(self, entry: dict[str, Any]) -> None:
        self.history.append(dict(entry))

    def append_tool_result(self, result: ToolResponse) -> None:
        self.tool_results.append(result)

    def set_memory_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.memory_snapshot = dict(snapshot)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "attributes": serialize_value(self.attributes),
            "history": serialize_value(self.history),
            "tool_results": [result.to_dict() for result in self.tool_results],
            "memory_snapshot": serialize_value(self.memory_snapshot),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskContext":
        return cls(
            task_id=data["task_id"],
            session_id=data["session_id"],
            attributes=dict(data.get("attributes", {})),
            history=list(data.get("history", [])),
            tool_results=[
                ToolResponse.from_dict(item) for item in data.get("tool_results", [])
            ],
            memory_snapshot=dict(data.get("memory_snapshot", {})),
            created_at=parse_datetime(data.get("created_at")) or utcnow(),
        )

