from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import ExecutionState


class RetryManager(ABC):
    @abstractmethod
    def should_retry(self, state: ExecutionState, error: Exception) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_retry_delay(self, state: ExecutionState) -> float:
        raise NotImplementedError

    @abstractmethod
    def record_retry(self, state: ExecutionState) -> ExecutionState:
        raise NotImplementedError

