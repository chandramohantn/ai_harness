from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import ToolRequest, ToolResponse


class ToolRouter(ABC):
    @abstractmethod
    def route_request(self, request: ToolRequest) -> ToolResponse:
        raise NotImplementedError

