from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.models import MetricRecord, ObservationEvent
from src.interfaces.observability.models import Span


class ObservationManager(ABC):
    @abstractmethod
    def record_event(self, event: ObservationEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def record_metric(self, metric: MetricRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def record_error(
        self, error: Exception, context: dict[str, Any] | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def start_span(
        self, name: str, task_id: str | None = None, parent_span_id: str | None = None
    ) -> Span:
        raise NotImplementedError

    @abstractmethod
    def end_span(self, span: Span, status: str = "ok") -> None:
        raise NotImplementedError

    @abstractmethod
    def flush(self) -> None:
        raise NotImplementedError
