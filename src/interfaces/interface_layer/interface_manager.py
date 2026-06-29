from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.enums import TaskStatus
from src.domain.models import TaskResult


class InterfaceManager(ABC):
    @abstractmethod
    def submit_task(self, raw_input: dict[str, Any]) -> TaskResult:
        raise NotImplementedError

    @abstractmethod
    def get_task_status(self, task_id: str) -> TaskStatus:
        raise NotImplementedError

    @abstractmethod
    def cancel_task(self, task_id: str) -> bool:
        raise NotImplementedError

