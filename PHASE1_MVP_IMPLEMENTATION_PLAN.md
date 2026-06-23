# Phase 1 (MVP) Implementation Plan

## Goal

Build a **minimal but production-shaped AI harness** that can accept a task, create and track execution state, invoke registered tools through contracts, assemble context from memory, and emit observability events. The MVP should solve the basic end-to-end execution path without locking us into a rigid design.

## Core design principles

1. **Contracts first**: every layer depends on interfaces and shared request/response models, not concrete implementations.
2. **Composition over coupling**: orchestration coordinates services; services do not reach into each other directly.
3. **Plugins everywhere**: tools, memory backends, observers, and later LLM providers should be swappable.
4. **Single responsibility**: validation, routing, execution, persistence, and tracing stay in separate classes.
5. **Extensible defaults**: Phase 1 ships with simple in-memory/local implementations, but every boundary should support future replacement.

## Phase 1 scope

We should implement only the layers needed for a clean MVP:

- **Interface Layer**
- **Orchestration Layer**
- **Tool Layer**
- **Memory Layer**
- **Observability Layer**

We should **defer** advanced planning, human approval flows, evaluation, and complex policy engines until Phase 2+, while keeping interfaces ready for them.

## Recommended package structure

```text
ai_harness/
├── domain/
│   ├── models/
│   ├── requests/
│   ├── responses/
│   └── enums/
├── interfaces/
│   ├── interface_layer/
│   ├── orchestration/
│   ├── tools/
│   ├── memory/
│   └── observability/
├── application/
│   ├── interface_layer/
│   ├── orchestration/
│   ├── tools/
│   ├── memory/
│   └── observability/
├── infrastructure/
│   ├── memory/
│   ├── observability/
│   ├── config/
│   └── plugins/
├── bootstrap/
│   ├── container/
│   └── registry/
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

This keeps the system modular:

- **domain** = pure shared models
- **interfaces** = abstract contracts
- **application** = orchestration and business logic
- **infrastructure** = concrete adapters
- **bootstrap** = wiring and dependency registration

## Shared domain models to implement first

These should be framework-agnostic and imported by every layer:

- `TaskRequest`
- `TaskContext`
- `TaskResult`
- `ExecutionState`
- `ToolRequest`
- `ToolResponse`
- `MemoryRequest`
- `MemoryResponse`
- `ObservationEvent`
- `MetricRecord`

### Implementation guidance

- Use immutable request/response models where possible.
- Keep `TaskContext` mutable but controlled through methods such as `add_attribute()` and `get_attribute()`.
- Use enums for state/status values instead of raw strings.
- Keep serialization explicit so the same models can later support API, queue, or worker execution.

## Phase 1 implementation order

### 1. Contracts and domain foundation

Implement the shared models and abstract interfaces first.

**Priority classes/interfaces**

- `InterfaceManager`
- `RequestValidator`
- `SessionManager`
- `Orchestrator`
- `WorkflowManager`
- `StateManager`
- `BaseTool`
- `ToolRegistry`
- `ToolExecutor`
- `MemoryService`
- `SessionMemory`
- `ContextAssembler`
- `ObservationManager`
- `ExecutionTracer`
- `MetricsCollector`

**Why first**

This gives us stable contracts before any concrete storage, tool, or tracing implementation is added.

### 2. Interface layer

#### `InterfaceManager`

Responsibility:

- accept incoming task submissions
- delegate validation
- create/load session
- transform input into `TaskRequest` and `TaskContext`
- call `Orchestrator`

#### `RequestValidator`

Phase 1 should validate:

- required headers/metadata
- payload shape
- basic task submission rules

Keep validation isolated so later auth/authz policies can plug in without changing `InterfaceManager`.

#### `SessionManager`

Start with a simple session repository abstraction and an in-memory implementation. The interface should already support future persistence.

### 3. Orchestration layer

#### `Orchestrator`

This is the main application service for the MVP. It should:

1. initialize execution state
2. ask `ContextAssembler` for execution context
3. ask `WorkflowManager` for the next step(s)
4. invoke `ExecutionCoordinator` / `ToolExecutor`
5. persist state changes through `StateManager`
6. emit events through `ObservationManager`
7. return `TaskResult`

#### `WorkflowManager`

For Phase 1, keep workflow logic intentionally simple:

- one task
- one or more sequential executable steps
- deterministic transitions

Do **not** embed LLM reasoning here yet. Instead, model the workflow API so a planner can later supply steps without changing the orchestrator contract.

#### `StateManager`

Use a repository abstraction underneath it. Phase 1 can persist state in memory or a local store, but the public API must remain backend-neutral.

#### `RetryManager`

Even if retries stay simple in MVP, add the class now. It prevents retry logic from leaking into tool execution or orchestration later.

### 4. Tool layer

#### `BaseTool`

Every tool implementation should expose:

- metadata (`get_name`, `get_description`, `get_schema`)
- input validation
- execution
- output validation

#### `ToolRegistry`

Use registry-based discovery for the MVP. This gives us a clean path to dynamic plugin loading later.

#### `ToolExecutor`

It should own:

- sync execution
- async extension point
- error mapping
- result normalization

Do not let tools return arbitrary raw values. Always normalize into `ToolResponse`.

#### `ToolValidator` and `ToolPermissionManager`

Phase 1 can keep permission checks simple, but these responsibilities should remain separate from routing and execution.

#### Initial MVP tools

Start with a very small tool set:

- `FilesystemTool`
- `SearchTool`
- one mock/demo tool for deterministic testing

That is enough to prove the plugin model and end-to-end flow.

### 5. Memory layer

#### `MemoryService`

This should be the only orchestration-facing memory contract.

#### `WorkingMemory`

Use it for transient execution data per task run.

#### `SessionMemory`

Use it for short conversational/task history across a session.

#### `ContextAssembler`

This is one of the most important MVP classes. It should combine:

- request payload
- session history
- working memory
- recent tool results

The orchestration layer should depend on `ContextAssembler`, not on individual memory stores.

#### `MemoryBackend`

Introduce the abstraction in Phase 1 even if the first implementation is in-memory. That keeps Redis/Postgres/vector backends as drop-in infrastructure changes later.

### 6. Observability layer

#### `ObservationManager`

Make this the single entry point for recording events, metrics, traces, and errors.

#### `ExecutionTracer`

Represent task execution as trace/span style events from day one. Even simple local tracing will make future OpenTelemetry integration much easier.

#### `PromptTracer`

Define the contract now, even if prompt logging is minimal in Phase 1.

#### `MetricsCollector`

Start with:

- task success/failure
- execution latency
- tool call count
- retry count

#### `AuditLogger`

At minimum, log:

- task submitted
- tool executed
- task completed/failed

## Cross-cutting platform services

These should exist in MVP as light abstractions:

- `ConfigurationManager`
- `PluginManager`
- `DependencyContainer`

`SecretManager` can be defined as an interface now and implemented when external services are introduced.

## Suggested execution flow for Phase 1

```text
submit_task()
  -> RequestValidator.validate_request()
  -> SessionManager.create_session() / get_session()
  -> RequestTransformer.to_task_request()
  -> Orchestrator.execute_task()
      -> StateManager.save_state()
      -> ContextAssembler.assemble_context()
      -> WorkflowManager.start_workflow()
      -> ToolRouter.route_request()
      -> ToolExecutor.execute_tool()
      -> MemoryService.store()
      -> ObservationManager.record_event()/record_metric()
      -> WorkflowManager.complete_workflow()
      -> TaskResult
```

## Implementation milestones

### Milestone 1: Foundation

- create package structure
- define domain models
- define abstract interfaces
- wire dependency container

### Milestone 2: Runnable orchestration

- implement `InterfaceManager`
- implement `Orchestrator`
- implement `WorkflowManager`
- implement `StateManager`
- support single-task sequential execution

### Milestone 3: Tool plugin system

- implement `BaseTool`
- implement `ToolRegistry`
- implement `ToolExecutor`
- register 2-3 MVP tools

### Milestone 4: Memory and context

- implement `WorkingMemory`
- implement `SessionMemory`
- implement `MemoryService`
- implement `ContextAssembler`

### Milestone 5: Observability

- implement `ObservationManager`
- implement tracing/metrics/audit logging
- expose basic run diagnostics

### Milestone 6: End-to-end hardening

- add integration tests for full task flow
- verify failure handling and retries
- validate extensibility seams

## Extensibility requirements we should preserve

The MVP should be written so the following can be added without breaking public contracts:

1. planner-backed workflows
2. multiple LLM providers
3. persistent state stores
4. vector/graph memory backends
5. human approval checkpoints
6. evaluation/scoring services
7. multi-agent coordination
8. async/distributed execution

## Testing strategy

### Unit tests

- domain model behavior
- request validation
- tool registration and execution
- state transitions
- context assembly

### Integration tests

- task submission to result
- tool execution with stored state
- memory + observability interaction
- retry/failure paths

### Contract tests

- every `BaseTool` implementation follows schema and response contracts
- every `MemoryBackend` implementation satisfies read/write/delete expectations

## MVP acceptance criteria

Phase 1 is complete when the harness can:

1. accept a normalized task request
2. create and track execution state
3. route and execute registered tools via contracts
4. store/retrieve session and working memory
5. assemble execution context cleanly
6. return a structured `TaskResult`
7. emit basic events, traces, and metrics
8. add a new tool or memory backend without changing orchestrator logic

## Recommended implementation mindset

Build **small concrete implementations behind stable abstractions**. The MVP should be intentionally simple in behavior, but strong in boundaries. If we keep contracts clean now, Phase 2 can add planners, policies, approvals, richer memory, evaluation, and distributed execution without rewriting the core harness.
