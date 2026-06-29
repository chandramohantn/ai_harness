from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.models import TaskContext, TaskRequest


class RequestTransformer(ABC):
    @abstractmethod
    def to_task_request(
        self, raw_input: dict[str, Any], session_id: str
    ) -> TaskRequest:
        raise NotImplementedError

    @abstractmethod
    def to_task_context(self, task_request: TaskRequest) -> TaskContext:
        raise NotImplementedError

