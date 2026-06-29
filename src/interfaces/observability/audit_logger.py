from __future__ import annotations

from abc import ABC, abstractmethod

from src.interfaces.observability.models import AuditEntry


class AuditLogger(ABC):
    @abstractmethod
    def log(self, entry: AuditEntry) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_audit_trail(self, task_id: str) -> list[AuditEntry]:
        raise NotImplementedError

    @abstractmethod
    def get_session_audit_trail(self, session_id: str) -> list[AuditEntry]:
        raise NotImplementedError
