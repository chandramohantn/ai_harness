from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.models import TaskRequest


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str | None = None


class ToolPolicy(ABC):
    @abstractmethod
    def evaluate(self, tool_name: str, task_request: TaskRequest) -> PermissionDecision:
        raise NotImplementedError

