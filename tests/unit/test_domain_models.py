import pytest

from src.domain.enums import (
    MemoryOperation,
    MemoryStatus,
    TaskPriority,
    TaskStatus,
    ToolStatus,
)
from src.domain.models import (
    ExecutionState,
    MemoryRequest,
    MemoryResponse,
    TaskContext,
    TaskRequest,
    TaskResult,
    ToolResponse,
)


def test_task_request_round_trip() -> None:
    request = TaskRequest(
        task_id="task-1",
        session_id="session-1",
        task_type="demo",
        payload={"value": 1},
        metadata={"source": "test"},
        priority=TaskPriority.HIGH,
        timeout_seconds=30,
    )

    restored = TaskRequest.from_dict(request.to_dict())

    assert restored.task_id == request.task_id
    assert restored.priority == TaskPriority.HIGH
    assert restored.payload["value"] == 1


def test_task_context_mutation_and_serialization() -> None:
    tool_result = ToolResponse(
        request_id="request-1",
        tool_name="echo",
        status=ToolStatus.SUCCESS,
        output={"message": "ok"},
    )
    context = TaskContext(task_id="task-1", session_id="session-1")
    context.add_attribute("foo", "bar")
    context.append_history({"step": "submitted"})
    context.append_tool_result(tool_result)
    context.set_memory_snapshot({"seen": True})

    restored = TaskContext.from_dict(context.to_dict())

    assert restored.has_attribute("foo")
    assert restored.get_attribute("foo") == "bar"
    assert len(restored.history) == 1
    assert restored.tool_results[0].tool_name == "echo"


def test_execution_state_transitions_and_retry() -> None:
    state = ExecutionState(task_id="task-1", session_id="session-1", max_retries=1)

    state.transition_to(TaskStatus.RUNNING)
    state.mark_step_completed("step-1")
    assert state.increment_retry() is True
    state.transition_to(TaskStatus.RETRYING)
    state.transition_to(TaskStatus.RUNNING)
    state.add_error({"message": "boom"})
    state.transition_to(TaskStatus.FAILED)

    assert state.steps_completed == ["step-1"]
    assert state.retry_count == 1
    assert state.status == TaskStatus.FAILED
    assert state.increment_retry() is False


def test_invalid_execution_state_transition_raises() -> None:
    state = ExecutionState(task_id="task-1", session_id="session-1")

    with pytest.raises(ValueError, match="Invalid task status transition"):
        state.transition_to(TaskStatus.COMPLETED)


def test_task_result_and_memory_response_helpers() -> None:
    tool_response = ToolResponse(
        request_id="request-1",
        tool_name="echo",
        status=ToolStatus.SUCCESS,
        output="hello",
    )
    result = TaskResult(
        task_id="task-1",
        status=TaskStatus.COMPLETED,
        output="done",
        tool_calls=[tool_response],
    )
    memory_request = MemoryRequest(
        request_id="memory-1",
        operation=MemoryOperation.WRITE,
        namespace="working",
        key="a",
        value=1,
        session_id="session-1",
        task_id="task-1",
    )
    memory_response = MemoryResponse(
        request_id=memory_request.request_id,
        operation=MemoryOperation.WRITE,
        status=MemoryStatus.SUCCESS,
        value=1,
    )

    assert result.is_success() is True
    assert result.is_failure() is False
    assert memory_response.is_success() is True
