from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.interfaces.observability.models import Span


class ExecutionTracer(ABC):
    @abstractmethod
    def start_trace(
        self, task_id: str, metadata: dict[str, Any] | None = None
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def start_span(
        self, trace_id: str, name: str, parent_span_id: str | None = None
    ) -> Span:
        raise NotImplementedError

    @abstractmethod
    def end_span(
        self,
        span: Span,
        status: str = "ok",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def end_trace(self, trace_id: str, status: str = "ok") -> None:
        raise NotImplementedError

    @abstractmethod
    def get_trace(self, trace_id: str) -> list[Span]:
        raise NotImplementedError

    @abstractmethod
    def add_span_attribute(self, span: Span, key: str, value: Any) -> None:
        raise NotImplementedError
