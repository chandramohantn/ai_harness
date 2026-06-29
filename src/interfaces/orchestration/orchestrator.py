from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import TaskContext, TaskRequest, TaskResult


class Orchestrator(ABC):
    @abstractmethod
    def execute_task(
        self, task_request: TaskRequest, task_context: TaskContext
    ) -> TaskResult:
        raise NotImplementedError

