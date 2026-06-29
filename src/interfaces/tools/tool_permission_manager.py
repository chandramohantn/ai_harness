from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import TaskRequest
from src.interfaces.tools.models import ToolPolicy


class ToolPermissionManager(ABC):
    @abstractmethod
    def is_permitted(self, tool_name: str, task_request: TaskRequest) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_denied_reason(self, tool_name: str, task_request: TaskRequest) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def register_policy(self, policy: ToolPolicy) -> None:
        raise NotImplementedError
