from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.interfaces.interface_layer.models import Session


class SessionManager(ABC):
    @abstractmethod
    def create_session(self, metadata: dict[str, Any] | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_session(self, session_id: str) -> Session | None:
        raise NotImplementedError

    @abstractmethod
    def update_session(self, session_id: str, data: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def close_session(self, session_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def session_exists(self, session_id: str) -> bool:
        raise NotImplementedError
