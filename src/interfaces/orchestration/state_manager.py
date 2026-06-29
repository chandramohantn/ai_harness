from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import ExecutionState


class StateManager(ABC):
    @abstractmethod
    def create_state(self, task_id: str, session_id: str) -> ExecutionState:
        raise NotImplementedError

    @abstractmethod
    def get_state(self, task_id: str) -> ExecutionState | None:
        raise NotImplementedError

    @abstractmethod
    def save_state(self, state: ExecutionState) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_state(self, task_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_states(self, session_id: str) -> list[ExecutionState]:
        raise NotImplementedError

