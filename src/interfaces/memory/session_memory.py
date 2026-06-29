from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SessionMemory(ABC):
    @abstractmethod
    def add_entry(self, session_id: str, entry: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_history(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_entry(self, session_id: str, entry_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def clear_history(self, session_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_summary(self, session_id: str) -> dict[str, Any]:
        raise NotImplementedError

