from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.enums import TaskStatus
from src.domain.models._serialization import parse_datetime, serialize_value, utcnow


VALID_TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {
        TaskStatus.WAITING,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.RETRYING,
        TaskStatus.CANCELLED,
        TaskStatus.TIMED_OUT,
    },
    TaskStatus.WAITING: {
        TaskStatus.RUNNING,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.TIMED_OUT,
    },
    TaskStatus.RETRYING: {
        TaskStatus.RUNNING,
        TaskStatus.FAILED,
        TaskStatus.TIMED_OUT,
    },
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
    TaskStatus.TIMED_OUT: set(),
}


@dataclass
class ExecutionState:
    task_id: str
    session_id: str
    status: TaskStatus = TaskStatus.PENDING
    current_step: str | None = None
    steps_completed: list[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 0
    error_history: list[dict[str, Any]] = field(default_factory=list)
    state_data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def transition_to(self, status: TaskStatus) -> None:
        if status == self.status:
            self.updated_at = utcnow()
            return
        allowed = VALID_TASK_TRANSITIONS.get(self.status, set())
        if status not in allowed:
            raise ValueError(
                f"Invalid task status transition from {self.status.value} to {status.value}"
            )
        self.status = status
        self.updated_at = utcnow()

    def mark_step_completed(self, step_id: str) -> None:
        if step_id not in self.steps_completed:
            self.steps_completed.append(step_id)
        self.current_step = None
        self.updated_at = utcnow()

    def increment_retry(self) -> bool:
        if self.retry_count >= self.max_retries:
            return False
        self.retry_count += 1
        self.updated_at = utcnow()
        return True

    def add_error(self, error: dict[str, Any]) -> None:
        self.error_history.append(dict(error))
        self.updated_at = utcnow()

    def set_data(self, key: str, value: Any) -> None:
        self.state_data[key] = value
        self.updated_at = utcnow()

    def get_data(self, key: str, default: Any = None) -> Any:
        return self.state_data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "current_step": self.current_step,
            "steps_completed": list(self.steps_completed),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_history": serialize_value(self.error_history),
            "state_data": serialize_value(self.state_data),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionState":
        return cls(
            task_id=data["task_id"],
            session_id=data["session_id"],
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            current_step=data.get("current_step"),
            steps_completed=list(data.get("steps_completed", [])),
            retry_count=int(data.get("retry_count", 0)),
            max_retries=int(data.get("max_retries", 0)),
            error_history=list(data.get("error_history", [])),
            state_data=dict(data.get("state_data", {})),
            created_at=parse_datetime(data.get("created_at")) or utcnow(),
            updated_at=parse_datetime(data.get("updated_at")) or utcnow(),
        )

