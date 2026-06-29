from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class WorkingMemory(ABC):
    @abstractmethod
    def set(self, task_id: str, key: str, value: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, task_id: str, key: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def has(self, task_id: str, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(self, task_id: str, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_all(self, task_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def clear(self, task_id: str) -> None:
        raise NotImplementedError

