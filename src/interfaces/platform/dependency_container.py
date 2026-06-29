from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class DependencyContainer(ABC):
    @abstractmethod
    def register(self, interface: type, implementation: Any, singleton: bool = True) -> None:
        raise NotImplementedError

    @abstractmethod
    def resolve(self, interface: type) -> Any:
        raise NotImplementedError

    @abstractmethod
    def has(self, interface: type) -> bool:
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def register_factory(
        self, interface: type, factory: Callable[[], Any], singleton: bool = True
    ) -> None:
        raise NotImplementedError

