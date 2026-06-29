from __future__ import annotations

from abc import ABC, abstractmethod


class SecretManager(ABC):
    @abstractmethod
    def get_secret(self, key: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def has_secret(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def set_secret(self, key: str, value: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_secret(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_keys(self) -> list[str]:
        raise NotImplementedError
