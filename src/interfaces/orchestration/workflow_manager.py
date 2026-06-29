from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.models import TaskContext, TaskRequest
from src.interfaces.orchestration.models import Workflow, WorkflowStep


class WorkflowManager(ABC):
    @abstractmethod
    def start_workflow(self, task_request: TaskRequest, context: TaskContext) -> Workflow:
        raise NotImplementedError

    @abstractmethod
    def get_next_step(self, workflow: Workflow) -> WorkflowStep | None:
        raise NotImplementedError

    @abstractmethod
    def complete_step(self, workflow: Workflow, step_id: str, result: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def fail_step(self, workflow: Workflow, step_id: str, error: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def complete_workflow(self, workflow: Workflow) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_complete(self, workflow: Workflow) -> bool:
        raise NotImplementedError
