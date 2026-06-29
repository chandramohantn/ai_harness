from pathlib import Path

from src.application.observability import (
    DefaultObservationManager,
    InMemoryAuditLogger,
    InMemoryExecutionTracer,
    InMemoryMetricsCollector,
    InMemoryPromptTracer,
)
from src.application.platform import (
    DefaultPluginManager,
    InMemoryConfigurationManager,
    InMemorySecretManager,
    SimpleDependencyContainer,
)
from src.domain.enums import EventSeverity, EventType, MetricType
from src.domain.models import MetricRecord, ObservationEvent
from src.domain.models._serialization import new_id


def test_configuration_container_and_secrets() -> None:
    config = InMemoryConfigurationManager()
    config.set("app.name", "ai-harness")
    config.set("app.debug", True)
    container = SimpleDependencyContainer()
    container.register(InMemoryConfigurationManager, config)
    secrets = InMemorySecretManager()
    secrets.set_secret("api-key", "secret")

    assert config.has("app.name")
    assert config.get_section("app")["app.name"] == "ai-harness"
    assert container.resolve(InMemoryConfigurationManager) is config
    assert secrets.get_secret("api-key") == "secret"


def test_plugin_manager_discovers_and_loads_python_file(tmp_path: Path) -> None:
    plugin_path = tmp_path / "demo_plugin.py"
    plugin_path.write_text("VALUE = 123\n")
    manager = DefaultPluginManager()

    descriptors = manager.discover(str(tmp_path))
    plugin = manager.load(descriptors[0])

    assert descriptors[0].name == "demo_plugin"
    assert plugin.VALUE == 123


def test_observation_manager_records_events_metrics_and_traces() -> None:
    tracer = InMemoryExecutionTracer()
    metrics = InMemoryMetricsCollector()
    audit = InMemoryAuditLogger()
    prompts = InMemoryPromptTracer()
    manager = DefaultObservationManager(tracer, metrics, audit)

    prompt_id = prompts.record_prompt("task-1", "hello")
    prompts.record_response(prompt_id, "world")
    span = manager.start_span("task-run", task_id="task-1")
    manager.record_event(
        ObservationEvent(
            event_id=new_id(),
            event_type=EventType.TASK_STARTED,
            source="test",
            task_id="task-1",
            session_id="session-1",
            severity=EventSeverity.INFO,
            message="started",
        )
    )
    manager.record_metric(
        MetricRecord(
            metric_id=new_id(),
            name="task.execution.duration_ms",
            value=10.0,
            metric_type=MetricType.HISTOGRAM,
            task_id="task-1",
        )
    )
    manager.end_span(span)

    assert len(manager.events) == 1
    assert len(metrics.get_metrics("task.execution.duration_ms")) == 1
    assert len(audit.get_audit_trail("task-1")) == 1
    assert len(tracer.get_trace(span.trace_id)) == 1
    assert prompts.get_prompt_history("task-1")[0].response == "world"
