from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import MemoryRequest, MemoryResponse


class MemoryService(ABC):
    @abstractmethod
    def store(self, request: MemoryRequest) -> MemoryResponse:
        raise NotImplementedError

    @abstractmethod
    def retrieve(self, request: MemoryRequest) -> MemoryResponse:
        raise NotImplementedError

    @abstractmethod
    def delete(self, request: MemoryRequest) -> MemoryResponse:
        raise NotImplementedError

    @abstractmethod
    def list_keys(self, namespace: str, session_id: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def clear_namespace(self, namespace: str, session_id: str) -> None:
        raise NotImplementedError

