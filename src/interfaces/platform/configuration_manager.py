from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ConfigurationManager(ABC):
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        raise NotImplementedError

    @abstractmethod
    def get_required(self, key: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def has(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_section(self, prefix: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def load(self, source: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def reload(self) -> None:
        raise NotImplementedError

