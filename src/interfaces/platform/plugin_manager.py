from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.interfaces.platform.models import PluginDescriptor


class PluginManager(ABC):
    @abstractmethod
    def discover(self, path: str) -> list[PluginDescriptor]:
        raise NotImplementedError

    @abstractmethod
    def load(self, descriptor: PluginDescriptor) -> Any:
        raise NotImplementedError

    @abstractmethod
    def register(self, name: str, plugin: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, name: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def list_plugins(self) -> list[PluginDescriptor]:
        raise NotImplementedError

    @abstractmethod
    def unload(self, name: str) -> None:
        raise NotImplementedError
