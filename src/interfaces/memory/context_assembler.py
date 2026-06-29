from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import TaskContext, TaskRequest, ToolResponse


class ContextAssembler(ABC):
    @abstractmethod
    def assemble_context(self, task_request: TaskRequest, session_id: str) -> TaskContext:
        raise NotImplementedError

    @abstractmethod
    def update_context(self, context: TaskContext, tool_result: ToolResponse) -> TaskContext:
        raise NotImplementedError

    @abstractmethod
    def finalize_context(self, context: TaskContext) -> TaskContext:
        raise NotImplementedError

