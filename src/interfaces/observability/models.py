from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.models._serialization import utcnow


@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_span_id: str | None
    name: str
    task_id: str | None = None
    start_time: datetime = field(default_factory=utcnow)
    end_time: datetime | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"


@dataclass
class PromptRecord:
    record_id: str
    task_id: str
    prompt: str
    response: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utcnow)


@dataclass
class AuditEntry:
    entry_id: str
    action: str
    actor: str
    task_id: str | None = None
    session_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utcnow)

