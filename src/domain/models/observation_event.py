from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.enums import EventSeverity, EventType
from src.domain.models._serialization import parse_datetime, serialize_value, utcnow


@dataclass(frozen=True)
class ObservationEvent:
    event_id: str
    event_type: EventType
    source: str
    task_id: str | None = None
    session_id: str | None = None
    severity: EventSeverity = EventSeverity.INFO
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utcnow)
    trace_id: str | None = None
    span_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "severity": self.severity.value,
            "message": self.message,
            "data": serialize_value(self.data),
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "span_id": self.span_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObservationEvent":
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            source=data["source"],
            task_id=data.get("task_id"),
            session_id=data.get("session_id"),
            severity=EventSeverity(data.get("severity", EventSeverity.INFO.value)),
            message=data.get("message", ""),
            data=dict(data.get("data", {})),
            timestamp=parse_datetime(data.get("timestamp")) or utcnow(),
            trace_id=data.get("trace_id"),
            span_id=data.get("span_id"),
        )

