from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.models import ToolRequest, ToolResponse
from src.interfaces.interface_layer.models import ValidationResult


class BaseTool(ABC):
    @property
    def name(self) -> str:
        return self.get_name()

    @property
    def description(self) -> str:
        return self.get_description()

    @property
    def schema(self) -> dict[str, Any]:
        return self.get_schema()

    @abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def validate_input(self, parameters: dict[str, Any]) -> ValidationResult:
        raise NotImplementedError

    @abstractmethod
    def execute(self, request: ToolRequest) -> ToolResponse:
        raise NotImplementedError

    @abstractmethod
    def validate_output(self, output: Any) -> bool:
        raise NotImplementedError

