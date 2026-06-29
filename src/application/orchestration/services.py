"""Concrete orchestration services for the MVP runtime.

The implementations coordinate task state, workflow progression, retry logic,
memory updates, tool execution, and observability.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from src.application.observability import build_metric
from src.domain.enums import EventSeverity, EventType, MemoryOperation, MetricType, TaskStatus
from src.domain.models import ExecutionState, MemoryRequest, ObservationEvent, TaskContext, TaskRequest, TaskResult, ToolRequest, ToolResponse
from src.domain.models._serialization import new_id, utcnow
from src.interfaces.memory import ContextAssembler, MemoryService
from src.interfaces.observability import ObservationManager
from src.interfaces.orchestration import (
    Orchestrator,
    RetryManager,
    StateManager,
    Workflow,
    WorkflowManager,
    WorkflowStep,
)
from src.interfaces.tools import ToolExecutor


class InMemoryStateManager(StateManager):
    """Persist execution state in process memory."""

    def __init__(self) -> None:
        self._states: dict[str, ExecutionState] = {}

    def create_state(self, task_id: str, session_id: str) -> ExecutionState:
        state = ExecutionState(task_id=task_id, session_id=session_id)
        self._states[task_id] = state
        return state

    def get_state(self, task_id: str) -> ExecutionState | None:
        return self._states.get(task_id)

    def save_state(self, state: ExecutionState) -> None:
        self._states[state.task_id] = state

    def delete_state(self, task_id: str) -> None:
        self._states.pop(task_id, None)

    def list_states(self, session_id: str) -> list[ExecutionState]:
        return [state for state in self._states.values() if state.session_id == session_id]


class SequentialWorkflowManager(WorkflowManager):
    """Execute a simple sequential workflow for Phase 1."""

    def start_workflow(self, task_request: TaskRequest, context: TaskContext) -> Workflow:
        raw_steps = task_request.payload.get("steps")
        steps: list[WorkflowStep] = []
        if isinstance(raw_steps, list) and raw_steps:
            for index, step in enumerate(raw_steps, start=1):
                step_data = dict(step)
                steps.append(
                    WorkflowStep(
                        step_id=str(step_data.get("step_id", f"step-{index}")),
                        step_type=str(step_data.get("step_type", "tool_call")),
                        tool_name=step_data.get("tool_name"),
                        parameters=dict(step_data.get("parameters", {})),
                    )
                )
        elif "tool_name" in task_request.payload:
            steps.append(
                WorkflowStep(
                    step_id="step-1",
                    step_type="tool_call",
                    tool_name=str(task_request.payload["tool_name"]),
                    parameters=dict(task_request.payload.get("parameters", {})),
                )
            )
        else:
            steps.append(
                WorkflowStep(
                    step_id="step-1",
                    step_type="return_payload",
                    parameters={"output": dict(task_request.payload)},
                )
            )
        workflow = Workflow(
            workflow_id=new_id(),
            task_id=task_request.task_id,
            steps=steps,
            status=TaskStatus.RUNNING,
        )
        return workflow

    def get_next_step(self, workflow: Workflow) -> WorkflowStep | None:
        while workflow.current_step_index < len(workflow.steps):
            step = workflow.steps[workflow.current_step_index]
            if step.status == TaskStatus.PENDING:
                step.status = TaskStatus.RUNNING
                return step
            workflow.current_step_index += 1
        return None

    def complete_step(self, workflow: Workflow, step_id: str, result: Any) -> None:
        for index, step in enumerate(workflow.steps):
            if step.step_id == step_id:
                step.result = result
                step.status = TaskStatus.COMPLETED
                workflow.current_step_index = index + 1
                return
        raise KeyError(f"Unknown step_id: {step_id}")

    def fail_step(self, workflow: Workflow, step_id: str, error: str) -> None:
        for step in workflow.steps:
            if step.step_id == step_id:
                step.result = {"error": error}
                step.status = TaskStatus.FAILED
                workflow.status = TaskStatus.FAILED
                return
        raise KeyError(f"Unknown step_id: {step_id}")

    def complete_workflow(self, workflow: Workflow) -> None:
        workflow.status = TaskStatus.COMPLETED

    def is_complete(self, workflow: Workflow) -> bool:
        return all(step.status == TaskStatus.COMPLETED for step in workflow.steps)


class ExponentialBackoffRetryManager(RetryManager):
    """Apply exponential backoff semantics to task retries."""

    def __init__(self, base_delay_seconds: float = 0.0) -> None:
        self._base_delay_seconds = base_delay_seconds

    def should_retry(self, state: ExecutionState, error: Exception) -> bool:
        return state.retry_count < state.max_retries and state.status != TaskStatus.CANCELLED

    def get_retry_delay(self, state: ExecutionState) -> float:
        return self._base_delay_seconds * (2 ** state.retry_count)

    def record_retry(self, state: ExecutionState) -> ExecutionState:
        if not state.increment_retry():
            raise RuntimeError("Retry limit reached")
        state.transition_to(TaskStatus.RETRYING)
        return state


class DefaultOrchestrator(Orchestrator):
    """Run a task end-to-end using the configured runtime services."""

    def __init__(
        self,
        state_manager: StateManager,
        context_assembler: ContextAssembler,
        workflow_manager: WorkflowManager,
        tool_executor: ToolExecutor,
        memory_service: MemoryService,
        observation_manager: ObservationManager,
        retry_manager: RetryManager | None = None,
    ) -> None:
        self._state_manager = state_manager
        self._context_assembler = context_assembler
        self._workflow_manager = workflow_manager
        self._tool_executor = tool_executor
        self._memory_service = memory_service
        self._observation_manager = observation_manager
        self._retry_manager = retry_manager or ExponentialBackoffRetryManager()
        self._cancelled_tasks: set[str] = set()

    def cancel_task(self, task_id: str) -> None:
        self._cancelled_tasks.add(task_id)

    def execute_task(
        self, task_request: TaskRequest, task_context: TaskContext
    ) -> TaskResult:
        started = perf_counter()
        state = self._state_manager.get_state(task_request.task_id) or self._state_manager.create_state(
            task_request.task_id,
            task_request.session_id,
        )
        state.max_retries = int(task_request.metadata.get("max_retries", 0))
        self._state_manager.save_state(state)
        span = self._observation_manager.start_span(
            name=f"task:{task_request.task_type}",
            task_id=task_request.task_id,
        )

        self._observation_manager.record_event(
            ObservationEvent(
                event_id=new_id(),
                event_type=EventType.TASK_STARTED,
                source="orchestrator",
                task_id=task_request.task_id,
                session_id=task_request.session_id,
                severity=EventSeverity.INFO,
                message=f"Task {task_request.task_id} started",
            )
        )
        self._observation_manager.record_metric(
            build_metric(
                name="task.submitted",
                value=1.0,
                metric_type=MetricType.COUNTER,
                task_id=task_request.task_id,
                session_id=task_request.session_id,
            )
        )

        attempt = 0
        while True:
            try:
                state.transition_to(TaskStatus.RUNNING)
                self._state_manager.save_state(state)
                context = self._context_assembler.assemble_context(
                    task_request, task_request.session_id
                )
                context.attributes.update(task_context.attributes)
                for entry in task_context.history:
                    context.append_history(entry)

                workflow = self._workflow_manager.start_workflow(task_request, context)
                final_output: Any = None

                while True:
                    if task_request.task_id in self._cancelled_tasks:
                        state.transition_to(TaskStatus.CANCELLED)
                        self._state_manager.save_state(state)
                        return TaskResult(
                            task_id=task_request.task_id,
                            status=TaskStatus.CANCELLED,
                            error="Task was cancelled",
                            execution_duration_ms=int((perf_counter() - started) * 1000),
                        )

                    step = self._workflow_manager.get_next_step(workflow)
                    if step is None:
                        break

                    state.current_step = step.step_id
                    self._state_manager.save_state(state)

                    if step.step_type == "tool_call":
                        if not step.tool_name:
                            raise ValueError(f"Workflow step {step.step_id} missing tool_name")
                        tool_request = ToolRequest(
                            request_id=new_id(),
                            tool_name=step.tool_name,
                            parameters=step.parameters,
                            task_id=task_request.task_id,
                            session_id=task_request.session_id,
                            timeout_seconds=task_request.timeout_seconds,
                            metadata={"task_request": task_request.to_dict(), "step_id": step.step_id},
                        )
                        tool_result = self._tool_executor.execute(tool_request)
                        self._observation_manager.record_metric(
                            build_metric(
                                name="tool.call.count",
                                value=1.0,
                                metric_type=MetricType.COUNTER,
                                task_id=task_request.task_id,
                                session_id=task_request.session_id,
                                tags={"tool_name": step.tool_name},
                            )
                        )
                        self._observation_manager.record_metric(
                            build_metric(
                                name="tool.call.duration_ms",
                                value=float(tool_result.execution_duration_ms),
                                metric_type=MetricType.HISTOGRAM,
                                task_id=task_request.task_id,
                                session_id=task_request.session_id,
                                tags={"tool_name": step.tool_name},
                            )
                        )
                        context = self._context_assembler.update_context(context, tool_result)
                        self._store_runtime_memory(task_request, step, tool_result)
                        if not tool_result.is_success():
                            self._observation_manager.record_metric(
                                build_metric(
                                    name="tool.call.failed",
                                    value=1.0,
                                    metric_type=MetricType.COUNTER,
                                    task_id=task_request.task_id,
                                    session_id=task_request.session_id,
                                    tags={"tool_name": step.tool_name},
                                )
                            )
                            self._workflow_manager.fail_step(
                                workflow, step.step_id, tool_result.error or "Tool failed"
                            )
                            raise RuntimeError(tool_result.error or "Tool failed")
                        self._workflow_manager.complete_step(
                            workflow, step.step_id, tool_result.output
                        )
                        state.mark_step_completed(step.step_id)
                        final_output = tool_result.output
                    elif step.step_type == "return_payload":
                        final_output = step.parameters.get("output")
                        self._workflow_manager.complete_step(
                            workflow, step.step_id, final_output
                        )
                        state.mark_step_completed(step.step_id)
                    else:
                        raise ValueError(f"Unsupported workflow step_type: {step.step_type}")

                self._workflow_manager.complete_workflow(workflow)
                self._context_assembler.finalize_context(context)
                state.transition_to(TaskStatus.COMPLETED)
                self._state_manager.save_state(state)
                duration_ms = int((perf_counter() - started) * 1000)
                self._observation_manager.record_event(
                    ObservationEvent(
                        event_id=new_id(),
                        event_type=EventType.TASK_COMPLETED,
                        source="orchestrator",
                        task_id=task_request.task_id,
                        session_id=task_request.session_id,
                        severity=EventSeverity.INFO,
                        message=f"Task {task_request.task_id} completed",
                        data={"duration_ms": duration_ms},
                    )
                )
                self._observation_manager.record_metric(
                    build_metric(
                        name="task.completed",
                        value=1.0,
                        metric_type=MetricType.COUNTER,
                        task_id=task_request.task_id,
                        session_id=task_request.session_id,
                    )
                )
                self._observation_manager.record_metric(
                    build_metric(
                        name="task.execution.duration_ms",
                        value=float(duration_ms),
                        metric_type=MetricType.HISTOGRAM,
                        task_id=task_request.task_id,
                        session_id=task_request.session_id,
                    )
                )
                self._observation_manager.end_span(span, status="ok")
                return TaskResult(
                    task_id=task_request.task_id,
                    status=TaskStatus.COMPLETED,
                    output=final_output,
                    tool_calls=list(context.tool_results),
                    execution_duration_ms=duration_ms,
                    metadata={"steps_completed": list(state.steps_completed)},
                )
            except Exception as error:
                state.add_error({"error": str(error), "attempt": attempt + 1})
                if self._retry_manager.should_retry(state, error):
                    self._retry_manager.record_retry(state)
                    self._state_manager.save_state(state)
                    self._observation_manager.record_event(
                        ObservationEvent(
                            event_id=new_id(),
                            event_type=EventType.RETRY_ATTEMPTED,
                            source="orchestrator",
                            task_id=task_request.task_id,
                            session_id=task_request.session_id,
                            severity=EventSeverity.WARNING,
                            message=f"Retrying task {task_request.task_id}",
                            data={"retry_count": state.retry_count},
                        )
                    )
                    self._observation_manager.record_metric(
                        build_metric(
                            name="retry.count",
                            value=1.0,
                            metric_type=MetricType.COUNTER,
                            task_id=task_request.task_id,
                            session_id=task_request.session_id,
                        )
                    )
                    attempt += 1
                    continue

                state.transition_to(TaskStatus.FAILED)
                self._state_manager.save_state(state)
                duration_ms = int((perf_counter() - started) * 1000)
                self._observation_manager.record_event(
                    ObservationEvent(
                        event_id=new_id(),
                        event_type=EventType.TASK_FAILED,
                        source="orchestrator",
                        task_id=task_request.task_id,
                        session_id=task_request.session_id,
                        severity=EventSeverity.ERROR,
                        message=f"Task {task_request.task_id} failed",
                        data={"error": str(error), "duration_ms": duration_ms},
                    )
                )
                self._observation_manager.record_metric(
                    build_metric(
                        name="task.failed",
                        value=1.0,
                        metric_type=MetricType.COUNTER,
                        task_id=task_request.task_id,
                        session_id=task_request.session_id,
                    )
                )
                self._observation_manager.end_span(span, status="error")
                return TaskResult(
                    task_id=task_request.task_id,
                    status=TaskStatus.FAILED,
                    error=str(error),
                    tool_calls=[],
                    execution_duration_ms=duration_ms,
                )

    def _store_runtime_memory(
        self, task_request: TaskRequest, step: WorkflowStep, tool_result: ToolResponse
    ) -> None:
        self._memory_service.store(
            MemoryRequest(
                request_id=new_id(),
                operation=MemoryOperation.WRITE,
                namespace="working",
                key=step.step_id,
                value=tool_result.to_dict(),
                session_id=task_request.session_id,
                task_id=task_request.task_id,
            )
        )
        self._memory_service.store(
            MemoryRequest(
                request_id=new_id(),
                operation=MemoryOperation.WRITE,
                namespace="session",
                key=new_id(),
                value={
                    "task_id": task_request.task_id,
                    "step_id": step.step_id,
                    "tool_name": tool_result.tool_name,
                    "status": tool_result.status.value,
                    "output": tool_result.output,
                },
                session_id=task_request.session_id,
                task_id=task_request.task_id,
            )
        )
