from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import MetricRecord


class MetricsCollector(ABC):
    @abstractmethod
    def increment(
        self, name: str, value: float = 1.0, tags: dict[str, str] | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def histogram(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def record(self, metric: MetricRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_metrics(self, name: str | None = None) -> list[MetricRecord]:
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError
