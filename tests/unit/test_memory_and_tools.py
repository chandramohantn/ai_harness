from pathlib import Path

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
)
from src.application.tools import (
    AllowAllToolPermissionManager,
    DefaultToolExecutor,
    DefaultToolValidator,
    EchoTool,
    FilesystemTool,
    InMemoryToolRegistry,
    SearchTool,
)
from src.domain.enums import MemoryOperation, MemoryStatus, ToolStatus
from src.domain.models import MemoryRequest, TaskRequest, ToolRequest
from src.domain.models._serialization import new_id


def build_memory_stack() -> tuple[
    InMemoryMemoryBackend,
    DefaultWorkingMemory,
    DefaultSessionMemory,
    DefaultMemoryService,
]:
    backend = InMemoryMemoryBackend()
    working_memory = DefaultWorkingMemory(backend)
    session_memory = DefaultSessionMemory(backend)
    memory_service = DefaultMemoryService(
        working_memory,
        session_memory,
        backend,
    )
    return backend, working_memory, session_memory, memory_service


def test_memory_service_routes_working_and_session_memory() -> None:
    _, _, session_memory, memory_service = build_memory_stack()
    write_response = memory_service.store(
        MemoryRequest(
            request_id=new_id(),
            operation=MemoryOperation.WRITE,
            namespace="working",
            key="result",
            value={"ok": True},
            session_id="session-1",
            task_id="task-1",
        )
    )
    session_response = memory_service.store(
        MemoryRequest(
            request_id=new_id(),
            operation=MemoryOperation.WRITE,
            namespace="session",
            key="entry-1",
            value={"message": "hello"},
            session_id="session-1",
            task_id="task-1",
        )
    )
    read_response = memory_service.retrieve(
        MemoryRequest(
            request_id=new_id(),
            operation=MemoryOperation.READ,
            namespace="working",
            key="result",
            session_id="session-1",
            task_id="task-1",
        )
    )

    assert write_response.status == MemoryStatus.SUCCESS
    assert session_response.status == MemoryStatus.SUCCESS
    assert read_response.value == {"ok": True}
    assert len(session_memory.get_history("session-1")) == 1


def test_context_assembler_combines_history_and_working_memory() -> None:
    _, working_memory, session_memory, memory_service = build_memory_stack()
    working_memory.set("task-1", "cached", 123)
    session_memory.add_entry("session-1", {"entry_id": "h1", "message": "seen"})
    assembler = DefaultContextAssembler(
        working_memory,
        session_memory,
        memory_service,
    )
    task_request = TaskRequest(
        task_id="task-1",
        session_id="session-1",
        task_type="demo",
        payload={"value": 1},
    )

    context = assembler.assemble_context(task_request, "session-1")

    assert context.memory_snapshot["cached"] == 123
    assert context.history[0]["message"] == "seen"
    assert context.get_attribute("task_type") == "demo"


def test_tool_executor_runs_echo_filesystem_and_search_tools(tmp_path: Path) -> None:
    observation_manager = DefaultObservationManager(
        InMemoryExecutionTracer(),
        InMemoryMetricsCollector(),
        InMemoryAuditLogger(),
    )
    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    registry.register(FilesystemTool(tmp_path))
    registry.register(SearchTool(tmp_path))
    executor = DefaultToolExecutor(
        registry,
        DefaultToolValidator(),
        AllowAllToolPermissionManager(),
        observation_manager,
    )

    write_response = executor.execute(
        ToolRequest(
            request_id=new_id(),
            tool_name="filesystem",
            parameters={"action": "write", "path": "notes.txt", "content": "hello world"},
            task_id="task-1",
            session_id="session-1",
        )
    )
    search_response = executor.execute(
        ToolRequest(
            request_id=new_id(),
            tool_name="search",
            parameters={"query": "hello"},
            task_id="task-1",
            session_id="session-1",
        )
    )
    echo_response = executor.execute(
        ToolRequest(
            request_id=new_id(),
            tool_name="echo",
            parameters={"value": {"answer": 42}},
            task_id="task-1",
            session_id="session-1",
        )
    )

    assert write_response.status == ToolStatus.SUCCESS
    assert search_response.status == ToolStatus.SUCCESS
    assert search_response.output[0]["path"] == "notes.txt"
    assert echo_response.output["answer"] == 42


def test_tool_executor_returns_validation_error_for_invalid_request() -> None:
    observation_manager = DefaultObservationManager(
        InMemoryExecutionTracer(),
        InMemoryMetricsCollector(),
        InMemoryAuditLogger(),
    )
    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    executor = DefaultToolExecutor(
        registry,
        DefaultToolValidator(),
        AllowAllToolPermissionManager(),
        observation_manager,
    )

    response = executor.execute(
        ToolRequest(
            request_id=new_id(),
            tool_name="echo",
            parameters={},
            task_id="task-1",
            session_id="session-1",
        )
    )

    assert response.status == ToolStatus.VALIDATION_ERROR
