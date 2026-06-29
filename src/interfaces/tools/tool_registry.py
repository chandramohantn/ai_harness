from __future__ import annotations

from abc import ABC, abstractmethod

from src.interfaces.tools.base_tool import BaseTool


class ToolRegistry(ABC):
    @abstractmethod
    def register(self, tool: BaseTool) -> None:
        raise NotImplementedError

    @abstractmethod
    def unregister(self, tool_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_tool(self, tool_name: str) -> BaseTool | None:
        raise NotImplementedError

    @abstractmethod
    def list_tools(self) -> list[BaseTool]:
        raise NotImplementedError

    @abstractmethod
    def has_tool(self, tool_name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_tool_schemas(self) -> dict[str, dict[str, object]]:
        raise NotImplementedError
