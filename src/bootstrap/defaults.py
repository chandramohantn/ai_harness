"""Default bootstrap wiring for the AI harness.

This module assembles the in-memory MVP runtime and returns a ready-to-use
interface manager for local execution and testing.
"""

from __future__ import annotations

from pathlib import Path

from src.application.interface_layer import (
    DefaultInterfaceManager,
    DefaultRequestTransformer,
    DefaultRequestValidator,
    InMemorySessionManager,
)
from src.application.memory import (
    DefaultContextAssembler,
    DefaultMemoryService,
    DefaultSessionMemory,
    DefaultWorkingMemory,
    InMemoryMemoryBackend,
)
from src.application.observability import (
    DefaultObservationManager,
    InMemoryAuditLogger,
    InMemoryExecutionTracer,
    InMemoryMetricsCollector,
    InMemoryPromptTracer,
)
from src.application.orchestration import (
    DefaultOrchestrator,
    ExponentialBackoffRetryManager,
    InMemoryStateManager,
    SequentialWorkflowManager,
)
from src.application.platform import (
    DefaultPluginManager,
    InMemoryConfigurationManager,
    InMemorySecretManager,
    SimpleDependencyContainer,
)
from src.application.tools import (
    AllowAllToolPermissionManager,
    DefaultToolExecutor,
    DefaultToolRouter,
    DefaultToolValidator,
    EchoTool,
    FilesystemTool,
    InMemoryToolRegistry,
    SearchTool,
)


def build_default_harness(root_path: str | Path | None = None) -> DefaultInterfaceManager:
    """Build the default in-memory harness runtime.

    Args:
        root_path: Optional filesystem root used by file-based tools.

    Returns:
        A fully wired ``DefaultInterfaceManager`` instance.
    """

    backend = InMemoryMemoryBackend()
    working_memory = DefaultWorkingMemory(backend)
    session_memory = DefaultSessionMemory(backend)
    memory_service = DefaultMemoryService(working_memory, session_memory, backend)
    context_assembler = DefaultContextAssembler(
        working_memory,
        session_memory,
        memory_service,
    )

    execution_tracer = InMemoryExecutionTracer()
    metrics_collector = InMemoryMetricsCollector()
    audit_logger = InMemoryAuditLogger()
    _ = InMemoryPromptTracer()
    observation_manager = DefaultObservationManager(
        execution_tracer,
        metrics_collector,
        audit_logger,
    )

    tool_registry = InMemoryToolRegistry()
    tool_registry.register(EchoTool())
    tool_registry.register(FilesystemTool(root_path=root_path or "."))
    tool_registry.register(SearchTool(root_path=root_path or "."))
    tool_validator = DefaultToolValidator()
    tool_permission_manager = AllowAllToolPermissionManager()
    tool_executor = DefaultToolExecutor(
        tool_registry,
        tool_validator,
        tool_permission_manager,
        observation_manager,
    )
    _ = DefaultToolRouter(tool_registry, tool_executor, tool_permission_manager)

    state_manager = InMemoryStateManager()
    workflow_manager = SequentialWorkflowManager()
    retry_manager = ExponentialBackoffRetryManager()
    orchestrator = DefaultOrchestrator(
        state_manager=state_manager,
        context_assembler=context_assembler,
        workflow_manager=workflow_manager,
        tool_executor=tool_executor,
        memory_service=memory_service,
        observation_manager=observation_manager,
        retry_manager=retry_manager,
    )

    _ = InMemoryConfigurationManager()
    _ = DefaultPluginManager()
    _ = SimpleDependencyContainer()
    _ = InMemorySecretManager()

    return DefaultInterfaceManager(
        request_validator=DefaultRequestValidator(),
        session_manager=InMemorySessionManager(),
        request_transformer=DefaultRequestTransformer(),
        orchestrator=orchestrator,
        state_manager=state_manager,
    )
