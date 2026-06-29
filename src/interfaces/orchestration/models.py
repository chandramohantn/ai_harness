from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.enums import TaskStatus
from src.domain.models._serialization import utcnow


@dataclass
class WorkflowStep:
    step_id: str
    step_type: str
    tool_name: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None


@dataclass
class Workflow:
    workflow_id: str
    task_id: str
    steps: list[WorkflowStep]
    current_step_index: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=utcnow)

