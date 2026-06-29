from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import ToolRequest, ToolResponse
from src.interfaces.interface_layer.models import ValidationResult
from src.interfaces.tools.base_tool import BaseTool


class ToolValidator(ABC):
    @abstractmethod
    def validate_request(
        self, request: ToolRequest, tool: BaseTool
    ) -> ValidationResult:
        raise NotImplementedError

    @abstractmethod
    def validate_response(self, response: ToolResponse, tool: BaseTool) -> bool:
        raise NotImplementedError
