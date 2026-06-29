from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.enums import MetricType
from src.domain.models._serialization import parse_datetime, utcnow


@dataclass(frozen=True)
class MetricRecord:
    metric_id: str
    name: str
    value: float
    metric_type: MetricType
    tags: dict[str, str] = field(default_factory=dict)
    task_id: str | None = None
    session_id: str | None = None
    timestamp: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, object]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "value": self.value,
            "metric_type": self.metric_type.value,
            "tags": dict(self.tags),
            "task_id": self.task_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "MetricRecord":
        return cls(
            metric_id=str(data["metric_id"]),
            name=str(data["name"]),
            value=float(data["value"]),
            metric_type=MetricType(str(data["metric_type"])),
            tags=dict(data.get("tags", {})),
            task_id=str(data["task_id"]) if data.get("task_id") is not None else None,
            session_id=(
                str(data["session_id"]) if data.get("session_id") is not None else None
            ),
            timestamp=parse_datetime(data.get("timestamp")) or utcnow(),
        )
