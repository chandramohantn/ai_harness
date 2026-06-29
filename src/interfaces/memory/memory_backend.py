from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryBackend(ABC):
    @abstractmethod
    def get(self, namespace: str, key: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def set(
        self, namespace: str, key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, namespace: str, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def exists(self, namespace: str, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_keys(self, namespace: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def clear(self, namespace: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def flush_all(self) -> None:
        raise NotImplementedError

