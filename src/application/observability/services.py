"""Concrete observability services for the MVP runtime.

The module includes in-memory tracing, prompt recording, metrics collection,
audit logging, and a central observation manager.
"""

from __future__ import annotations

from typing import Any

from src.domain.enums import EventSeverity, EventType, MetricType
from src.domain.models import MetricRecord, ObservationEvent
from src.domain.models._serialization import new_id, utcnow
from src.interfaces.observability import (
    AuditEntry,
    AuditLogger,
    ExecutionTracer,
    MetricsCollector,
    ObservationManager,
    PromptRecord,
    PromptTracer,
    Span,
)


class InMemoryExecutionTracer(ExecutionTracer):
    """Track traces and spans in process memory."""

    def __init__(self) -> None:
        self._traces: dict[str, list[Span]] = {}
        self._trace_status: dict[str, str] = {}
        self._trace_tasks: dict[str, str] = {}

    def start_trace(self, task_id: str, metadata: dict[str, Any] | None = None) -> str:
        trace_id = new_id()
        self._traces[trace_id] = []
        self._trace_status[trace_id] = "running"
        self._trace_tasks[trace_id] = task_id
        return trace_id

    def start_span(
        self, trace_id: str, name: str, parent_span_id: str | None = None
    ) -> Span:
        span = Span(
            span_id=new_id(),
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            task_id=self._trace_tasks.get(trace_id),
        )
        self._traces.setdefault(trace_id, []).append(span)
        return span

    def end_span(
        self,
        span: Span,
        status: str = "ok",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        span.status = status
        span.end_time = utcnow()
        if attributes:
            span.attributes.update(attributes)

    def end_trace(self, trace_id: str, status: str = "ok") -> None:
        self._trace_status[trace_id] = status

    def get_trace(self, trace_id: str) -> list[Span]:
        return list(self._traces.get(trace_id, []))

    def add_span_attribute(self, span: Span, key: str, value: Any) -> None:
        span.attributes[key] = value


class InMemoryPromptTracer(PromptTracer):
    """Store prompt and response history in process memory."""

    def __init__(self) -> None:
        self._records: dict[str, PromptRecord] = {}

    def record_prompt(
        self, task_id: str, prompt: str, metadata: dict[str, Any] | None = None
    ) -> str:
        record = PromptRecord(
            record_id=new_id(),
            task_id=task_id,
            prompt=prompt,
            metadata=dict(metadata or {}),
        )
        self._records[record.record_id] = record
        return record.record_id

    def record_response(
        self,
        prompt_record_id: str,
        response: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        record = self._records[prompt_record_id]
        record.response = response
        if metadata:
            record.metadata.update(metadata)

    def get_prompt_history(self, task_id: str) -> list[PromptRecord]:
        return [record for record in self._records.values() if record.task_id == task_id]


class InMemoryMetricsCollector(MetricsCollector):
    """Collect metric records in process memory."""

    def __init__(self) -> None:
        self._metrics: list[MetricRecord] = []

    def increment(
        self, name: str, value: float = 1.0, tags: dict[str, str] | None = None
    ) -> None:
        self.record(
            MetricRecord(
                metric_id=new_id(),
                name=name,
                value=value,
                metric_type=MetricType.COUNTER,
                tags=dict(tags or {}),
            )
        )

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self.record(
            MetricRecord(
                metric_id=new_id(),
                name=name,
                value=value,
                metric_type=MetricType.GAUGE,
                tags=dict(tags or {}),
            )
        )

    def histogram(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        self.record(
            MetricRecord(
                metric_id=new_id(),
                name=name,
                value=value,
                metric_type=MetricType.HISTOGRAM,
                tags=dict(tags or {}),
            )
        )

    def record(self, metric: MetricRecord) -> None:
        self._metrics.append(metric)

    def get_metrics(self, name: str | None = None) -> list[MetricRecord]:
        if name is None:
            return list(self._metrics)
        return [metric for metric in self._metrics if metric.name == name]

    def reset(self) -> None:
        self._metrics.clear()


class InMemoryAuditLogger(AuditLogger):
    """Record audit entries in process memory."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def log(self, entry: AuditEntry) -> None:
        self._entries.append(entry)

    def get_audit_trail(self, task_id: str) -> list[AuditEntry]:
        return [entry for entry in self._entries if entry.task_id == task_id]

    def get_session_audit_trail(self, session_id: str) -> list[AuditEntry]:
        return [entry for entry in self._entries if entry.session_id == session_id]


class DefaultObservationManager(ObservationManager):
    """Provide a single entry point for events, metrics, traces, and errors."""

    def __init__(
        self,
        execution_tracer: ExecutionTracer,
        metrics_collector: MetricsCollector,
        audit_logger: AuditLogger,
    ) -> None:
        self._execution_tracer = execution_tracer
        self._metrics_collector = metrics_collector
        self._audit_logger = audit_logger
        self._events: list[ObservationEvent] = []
        self._active_traces_by_task: dict[str, str] = {}

    @property
    def events(self) -> list[ObservationEvent]:
        return list(self._events)

    def record_event(self, event: ObservationEvent) -> None:
        self._events.append(event)
        self._audit_logger.log(
            AuditEntry(
                entry_id=new_id(),
                action=event.event_type.value.lower(),
                actor=event.source,
                task_id=event.task_id,
                session_id=event.session_id,
                details=event.data,
            )
        )

    def record_metric(self, metric: MetricRecord) -> None:
        self._metrics_collector.record(metric)

    def record_error(
        self, error: Exception, context: dict[str, Any] | None = None
    ) -> None:
        payload = dict(context or {})
        event = ObservationEvent(
            event_id=new_id(),
            event_type=EventType.ERROR_OCCURRED,
            source="observation_manager",
            severity=EventSeverity.ERROR,
            message=str(error),
            data=payload,
            task_id=payload.get("task_id"),
            session_id=payload.get("session_id"),
        )
        self.record_event(event)

    def start_span(
        self, name: str, task_id: str | None = None, parent_span_id: str | None = None
    ) -> Span:
        if task_id is None:
            trace_id = new_id()
            self._execution_tracer.start_trace(trace_id)
        else:
            trace_id = self._active_traces_by_task.get(task_id)
            if trace_id is None:
                trace_id = self._execution_tracer.start_trace(task_id)
                self._active_traces_by_task[task_id] = trace_id
        return self._execution_tracer.start_span(trace_id, name, parent_span_id)

    def end_span(self, span: Span, status: str = "ok") -> None:
        self._execution_tracer.end_span(span, status=status)
        if span.task_id and span.parent_span_id is None:
            self._execution_tracer.end_trace(span.trace_id, status=status)

    def flush(self) -> None:
        return None


def build_metric(
    name: str,
    value: float,
    metric_type: MetricType,
    task_id: str | None = None,
    session_id: str | None = None,
    tags: dict[str, str] | None = None,
) -> MetricRecord:
    """Build a normalized metric record.

    Args:
        name: Metric name.
        value: Numeric value to record.
        metric_type: Metric type enum.
        task_id: Optional task identifier.
        session_id: Optional session identifier.
        tags: Optional metric tags.

    Returns:
        A populated ``MetricRecord`` instance.
    """

    return MetricRecord(
        metric_id=new_id(),
        name=name,
        value=value,
        metric_type=metric_type,
        tags=dict(tags or {}),
        task_id=task_id,
        session_id=session_id,
    )
