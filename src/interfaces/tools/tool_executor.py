from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import ToolRequest, ToolResponse


class ToolExecutor(ABC):
    @abstractmethod
    def execute(self, request: ToolRequest) -> ToolResponse:
        raise NotImplementedError

    @abstractmethod
    async def execute_async(self, request: ToolRequest) -> ToolResponse:
        raise NotImplementedError

