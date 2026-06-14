# AI Chat Developer Guide

**Last Updated:** 2026-06-14
**Status:** Active (canonical — kept by design)

End-to-end integration reference for the Backcast AI chat system: connection lifecycle, decoupled execution, approval / human-in-the-loop flow, sequence diagrams, and debugging.

> **Topic boundaries.** This doc covers the *integration* and *lifecycle* view.
> For related topics use the canonical siblings:
>
> - **Supervisor orchestration / handoffs** → [`ai/supervisor-orchestrator.md`](ai/supervisor-orchestrator.md)
> - **Request flow, tool filtering, security model, event bus** → [`ai/agent-common-concepts.md`](ai/agent-common-concepts.md)
> - **WebSocket protocol, message catalog, & reconnection flow** → [`backend/contexts/ai/message-types.md`](backend/contexts/ai/message-types.md) (the single canonical WS reference; not duplicated here)
> - **Prompt assembly** → [`ai-prompt-context-guide.md`](ai-prompt-context-guide.md)
> - **Tools** → [`ai/tool-development-guide.md`](ai/tool-development-guide.md)
> - **MCP** → [`mcp-developer-guide.md`](mcp-developer-guide.md)

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [WebSocket Connection Lifecycle](#2-websocket-connection-lifecycle)
3. [Starting a Conversation](#3-starting-a-conversation)
4. [Agent Setup & Orchestration](#4-agent-setup--orchestration)
5. [Decoupled Execution](#5-decoupled-execution)
6. [Reply Flow & Streaming](#6-reply-flow--streaming)
7. [Approval Flow (Human-in-the-Loop)](#7-approval-flow-human-in-the-loop)
8. [Security Model](#8-security-model)
9. [Integration & Debugging](#9-integration--debugging)
10. [Key Files Quick Reference](#10-key-files-quick-reference)

**Subsection index:**
- Section 2: [Error Recovery & Reconnection](#error-recovery--reconnection)
- Section 6: [Transient Error Handling](#transient-error-handling) | [Error Persistence](#error-persistence)
- Section 9: [Sequence Diagrams](#sequence-diagrams) | [Database Queries](#database-queries-for-debugging) | [Telemetry](#telemetry-phoenix)

---

## 1. Architecture Overview

### High-Level Flow

```
Browser (React)                          Backend (FastAPI)
     |                                        |
     |  ws://host/api/v1/ai/chat/stream       |
     |  ?token=<JWT>                          |
     |--------------------------------------->|
     |                                        | 1. JWT validation (BEFORE accept)
     |                                        | 2. User lookup + RBAC check
     |  101 Switching Protocols               |
     |<---------------------------------------|
     |                                        |
     |  {type:"chat", message:"...", ...}      |
     |--------------------------------------->|
     |                                        | 3. Session create/retrieve
     |                                        | 4. Build ToolContext
     |                                        | 5. Look up cached graph (or compile new)
     |                                        | 6. Set per-request ContextVars
     |  {type:"thinking"}                     |
     |<---------------------------------------|
     |                                        | 7. Agent emits plan via write_todos tool
     |  {type:"planning", steps:[...]}        |
     |<---------------------------------------|
     |                                        | 8. Delegates to specialist (handoff)
     |  {type:"subagent", subagent:"evm_..."} |
     |<---------------------------------------|
     |  {type:"token", content:"Based on..."} |
     |<---------------------------------------| 9. Specialist streams tokens
     |  ...more tokens...                     |
     |  {type:"subagent_result", ...}         |
     |<---------------------------------------|
     |  {type:"content_reset"}                |
     |<---------------------------------------| 10. Main agent synthesizes
     |  {type:"token", content:"The project"} |
     |<---------------------------------------|
     |  {type:"complete", session_id:"..."}   |
     |<---------------------------------------|
```

### Graph Construction

| Path | When Used | Description |
|------|-----------|-------------|
| **Supervisor Orchestrator** (primary) | Default path | Parent `StateGraph(BackcastSupervisorState)` built by `SupervisorOrchestrator.create_supervisor_graph()`: supervisor node + specialist function nodes + handoff tools. Main agents can use configured `direct_tools` directly. |
| **StateGraph fallback** | Supervisor unavailable (e.g. import error) or no specialists | Direct LangGraph `StateGraph(AgentState)` with agent node, tool node, and conditional edges. Iteration cap is `max_tool_iterations` in agent state (docstring example default 5). |

The primary path is created in `agent_service._create_deep_agent_graph()` (`agent_service.py:557`), which delegates graph compilation to `SupervisorOrchestrator.create_supervisor_graph()` (`supervisor_orchestrator.py:323`). On `ImportError` or other compile failure it falls back to `graph.create_graph()` (`graph.py:148`). Specialist graphs are compiled by `compile_subagents()` in `app/ai/subagent_compiler.py:98`.

### Core Components

```
ai_chat.py (WebSocket endpoint: chat_stream() @ /stream)
    |
    v
agent_service.py (orchestration)
    |
    +---> graph_cache.py (caching layer)
    |         |
    |         +---> LLMClientCache (thread-safe LLM client cache)
    |         +---> CompiledGraphCache (LRU graph cache, max 20)
    |         +---> set_request_context() / clear_request_context() (ContextVar bridge)
    |
    +---> _create_deep_agent_graph() -> SupervisorOrchestrator.create_supervisor_graph()
    |         |
    |         +---> subagents/db_loader.py  (load_specialists_from_db — TTL-cached DB specialist loading)
    |         +---> tools/__init__.py       (create_project_tools — dynamic tool count)
    |         +---> subagent_compiler.py    (compile_subagents — shared specialist graph compilation)
    |         +---> middleware/
    |         |      +---> temporal_context.py   (inject as_of, branch)
    |         |      +---> backcast_security.py  (RBAC + approval)
    |         +---> langchain_create_agent()  (LangChain native)
    |
    +---> _process_stream_events()  (astream_events loop with retry)
    |         |
    |         +---> on_chat_model_stream  --> WSTokenMessage / WSTokenBatchMessage
    |         +---> on_tool_start          --> WSToolCallMessage / WSSubagentMessage / WSPlanningMessage
    |         +---> on_tool_end            --> WSToolResultMessage / WSSubagentResultMessage
    |         +---> on_end                 --> WSCompleteMessage
    |
    +---> InterruptNode (approval polling)
              |
              +---> WSApprovalRequestMessage  --> client
              +---> WSApprovalResponseMessage <-- client
    |
    +---> TokenBufferManager (batched token sending)
              |
              +---> WSTokenBatchMessage  --> client (reduces WS overhead)
```

---

## 2. WebSocket Connection Lifecycle

> **WS protocol & message catalog.** The complete client/server message reference
> (all `type` fields, schemas, and the full message-flow sequence diagram) lives in
> [`backend/contexts/ai/message-types.md`](backend/contexts/ai/message-types.md).
> This section covers only the *lifecycle* perspective relevant to integration.

### Endpoint

```
ws://localhost:8020/api/v1/ai/chat/stream?token=<JWT_BEARER_TOKEN>
```

### Connection Sequence

Authentication happens **before** `websocket.accept()`. If auth fails, the connection is closed with a specific code — the client never gets a working connection.

```
1. Client sends WebSocket upgrade with JWT in query param
2. Server decodes JWT → failure → close(4008) if expired, close(1008) otherwise
3. Server looks up user by email from JWT subject → not found → close(1008)
4. Server checks RBAC: has_permission(user.role, "ai-chat") → denied → close(1008)
5. Server calls websocket.accept()
6. Server starts message_handler() as asyncio background task
7. Message loop: receive JSON → dispatch by type
```

### Close Codes

| Code | Meaning | Client Action |
|------|---------|---------------|
| `4008` | Token expired | Refresh token, reconnect |
| `1008` | Policy violation (bad token, no permission, user not found) | Do NOT reconnect — user must re-authenticate |
| `1000` | Normal closure | Reconnect if needed |

### Message Handler Loop

File: `ai_chat.py`

The handler runs as `asyncio.create_task(message_handler())`. Three message types are dispatched:

- `"subscribe"` — reconnect to a running execution by execution ID, replay missed events
- `"approval_response"` — handled immediately, non-blocking (updates `pending_approvals` dict)
- `"chat"` (default) — processed via `agent_service.start_execution()` as background task

Chat messages are processed as concurrent background tasks via `asyncio.create_task()`. Multiple chat streams can run simultaneously on the same WebSocket connection.

### Subscribe Message (Reconnection)

After WebSocket connection, the client can send a subscribe message to rejoin a running execution:

```json
{
  "type": "subscribe",
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "last_seen_sequence": 42
}
```

**Server behavior:**

1. Looks up event bus via `runner_manager.get_bus(execution_id)`
2. If not found, returns error: `{"type":"error", "message":"Execution not found or already completed", "code":404}`
3. If found, replays all events with sequence > `last_seen_sequence`
4. If execution is still running (`!bus.is_completed`), subscribes to live events
5. Live events forwarded until terminal event (`complete` or `error`)

**Frontend auto-subscribe:**

The `useStreamingChat` hook automatically sends subscribe messages on reconnection if `activeExecutionIdRef` is set. This enables seamless reconnection to running agents.

### Error Recovery & Reconnection

When the backend returns a 500 error during streaming, the frontend force-closes the WebSocket (`ws.close()`, `wsRef.current = null`). This triggers the `close` event handler which calls `scheduleReconnect()` with exponential backoff:

- **Max reconnect attempts:** 5
- **Base delay:** 1000ms (doubles each attempt: 1s, 2s, 4s, 8s, 16s)
- **Auto-subscribe:** On successful reconnection, the frontend automatically sends a subscribe message for any running execution tracked in `activeExecutionIdRef`
- **Pending message queue:** If `sendMessage()` is called while the connection is not OPEN, the message is stored in `pendingMessageRef` and sent after reconnection completes. Any stale non-OPEN connection is force-closed first to trigger a clean reconnect cycle.

The `sendMessage()` function handles non-OPEN states by force-closing stale connections (`ws.readyState !== WebSocket.CONNECTING`) and triggering a fresh connection via `connectRef.current()`.

> See [`backend/contexts/ai/message-types.md`](backend/contexts/ai/message-types.md) (Reconnection Flow section) for the full reconnect strategy and close-code semantics.

---

## 3. Starting a Conversation

### Client Request Payload

```json
{
  "type": "chat",
  "message": "What is the CPI for project X?",
  "session_id": null,
  "assistant_config_id": "a1b2c3d4-...",
  "title": "EVM Analysis Session",
  "project_id": "e5f6g7h8-...",
  "branch_id": null,
  "as_of": null,
  "branch_name": "main",
  "branch_mode": "merged",
  "execution_mode": "standard",
  "attachments": [],
  "images": []
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | yes | Always `"chat"` |
| `message` | string | yes | User message (1–10000 chars) |
| `session_id` | UUID/null | no | `null` for new session, UUID to continue existing |
| `assistant_config_id` | UUID | yes (new session) | Which assistant config to use |
| `title` | string/null | no | Session title (new sessions only) |
| `project_id` | UUID/null | no | Scopes tools to this project |
| `branch_id` | UUID/null | no | Branch/change order context |
| `as_of` | datetime/null | no | Historical date for temporal queries |
| `branch_name` | string | no | `"main"` default |
| `branch_mode` | string | no | `"merged"` or `"isolated"` |
| `execution_mode` | string | no | `"safe"`, `"standard"` (default), or `"expert"` |

### Session Creation

**New session** (`session_id: null`):

```python
# agent_service.py -> config_service.create_session()
AIConversationSession(
    user_id=user_id,
    assistant_config_id=assistant_config.id,
    title=title,          # Optional
    project_id=project_id, # Optional
    branch_id=branch_id,   # Optional
)
```

The `session_holder.value` is updated so approval responses can reference the correct session.

**Existing session** (`session_id: <UUID>`):

Fetched from DB. Server validates the session exists and belongs to the user.

### Context Establishment

After session creation, a `ToolContext` is built and passed to all tools:

```python
ToolContext(
    session=db_session,
    user_id=str(user_id),
    user_role=user_role,            # e.g., "admin", "manager"
    project_id=str(project_id),     # Optional project scope
    branch_id=str(branch_id),       # Optional branch scope
    as_of=as_of,                    # Optional historical date
    branch_name=branch_name,        # "main", "BR-001", etc.
    branch_mode=branch_mode,        # "merged" or "isolated"
    execution_mode=execution_mode,  # Tool filtering
)
```

This context flows through middleware to every tool call — the LLM cannot override it.

### REST Endpoint for Starting Executions

Alternative to WebSocket chat messages, agents can be invoked via REST:

```http
POST /api/v1/ai/chat/sessions/{session_id}/invoke
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "message": "What is the CPI for project X?",
  "project_id": null,
  "branch_id": null,
  "as_of": null,
  "branch_name": "main",
  "branch_mode": "merged",
  "execution_mode": "standard",
  "attachments": [],
  "images": []
}
```

**Response:** `AgentExecutionPublic`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "a1b2c3d4-e89b-12d3-a456-426614174000",
  "status": "running",
  "started_at": "2026-03-29T12:30:00Z",
  "completed_at": null,
  "error_message": null,
  "execution_mode": "standard",
  "total_tokens": 0,
  "tool_calls_count": 0,
  "created_at": "2026-03-29T12:30:00Z",
  "updated_at": "2026-03-29T12:30:00Z"
}
```

Returns immediately with execution ID. Agent runs in background. Can then:

- Subscribe via WebSocket with `{"type":"subscribe", "execution_id":"..."}`
- Poll status via `GET /api/v1/ai/chat/executions/{execution_id}/status`
- Approve tools via `POST /api/v1/ai/chat/executions/{execution_id}/approve`

### Execution Status Polling

```http
GET /api/v1/ai/chat/executions/{execution_id}/status
Authorization: Bearer <JWT>
```

**Response:** `AgentExecutionPublic` with current status, token counts, and error message if failed.

---

## 4. Agent Setup & Orchestration

> **Orchestration deep-dive.** For the supervisor state schema, handoff-tool construction,
> briefing-document accumulation, and the full `create_supervisor_graph()` internals, see
> [`ai/supervisor-orchestrator.md`](ai/supervisor-orchestrator.md). For the shared
> request-flow, tool-filtering pipeline, and security/event-bus concepts, see
> [`ai/agent-common-concepts.md`](ai/agent-common-concepts.md).

### Agent Creation Flow

Graph creation lives in:

- `agent_service._create_deep_agent_graph()` (`agent_service.py:557`) — entry point per request; builds the `InterruptNode`, resolves the system prompt, constructs `AgentConfig`, instantiates `SupervisorOrchestrator`, and calls `create_supervisor_graph()`.
- `SupervisorOrchestrator.create_supervisor_graph()` (`supervisor_orchestrator.py:323`) — compiles the parent `StateGraph(BackcastSupervisorState)` with supervisor node, specialist function nodes, and handoff tools.
- `compile_subagents()` (`app/ai/subagent_compiler.py:98`) — shared compilation logic for individual specialist graphs.

### Orchestration Pattern

The system uses a single orchestration pattern:

| Pattern | Orchestrator | Delegation Mechanism | Context Sharing |
|---------|-------------|---------------------|-----------------|
| **Supervisor** | `SupervisorOrchestrator` | Handoff-based — supervisor transfers control via `Command(goto=...)` handoff tools + optional direct tools | Shared state — briefing document accumulates specialist findings |

**SupervisorOrchestrator** (`supervisor_orchestrator.py`): Builds a parent `StateGraph(BackcastSupervisorState)` where the supervisor routes to specialist agents via handoff tools (`handoff_to_{agent_name}`). Each specialist is a function node that runs in isolation with the compiled briefing document. The supervisor can also use configured **direct tools** from the main agent's `delegation_config.direct_tools` (e.g., `get_temporal_context`, `set_temporal_context`, `global_search`).

Specialists are loaded from the database (`ai_assistant_configs` where `agent_type='specialist'`) via `subagents/db_loader.py:load_specialists_from_db()` with a TTL cache. There is **no hardcoded fallback config**: if the DB returns no specialists (or all are filtered out), the system falls back to the StateGraph path.

```
1. create_project_tools(context)     -> dynamic tool list (12 template modules + _pagination)
2. Filter by assistant RBAC role     -> ai-viewer/ai-manager/ai-admin (via default_role)
3. Filter by user RBAC role          -> User's role permissions
4. Filter by execution_mode          -> Risk-level filtering (safe/standard/expert)
5. Load specialists from DB          -> load_specialists_from_db() (TTL cache)
6. If delegation_config.allowed_specialists set, filter to only those specialists
7. compile_subagents()               -> compile specialist graphs (subagent_compiler.py)
8. Main agent gets: get_briefing + handoff tools + direct_tools from delegation_config
9. Specialists get: their filtered tool lists from allowed_tools
10. Build middleware stack:
    - TemporalContextMiddleware(context)
    - BackcastSecurityMiddleware(context, tools=all_tools, interrupt_node)
11. Build supervisor system prompt (conditional: with/without direct tools)
12. langchain_create_agent(model, tools, system_prompt, middleware)
13. Register InterruptNode for approval handling
```

### Graph Caching

Compiled agent graphs, LLM clients, and tool lists are cached and reused across requests. This avoids rebuilding the entire agent harness (~400ms) on every user prompt.

File: `graph_cache.py`

**What gets cached:**

| Layer | Cache Key | Scope |
|-------|-----------|-------|
| LLM client | `(model_name, temperature, max_tokens, base_url_hash)` | Application-wide |
| Tool list | Singleton (stateless — context injected via ContextVar) | Application-wide |
| Compiled graph | `GraphCacheKey(model_name, frozenset(tool_names), execution_mode, system_prompt_hash, assistant_role_hash)` | Application-wide, LRU max 20 |
| Checkpointer | Single shared `MemorySaver` | Application-wide |

**Per-request context (not cached):**

| What | How |
|------|-----|
| `ToolContext` (db_session, user_id, etc.) | Set via `set_request_context()` ContextVar before graph invocation |
| `InterruptNode` (WebSocket, session_id) | Set via ContextVar, created fresh per request |
| `thread_id` | Unique per conversation session via `config={"configurable": {"thread_id": ...}}` |

**How middleware reads fresh context in cached graphs:**

```python
# In BackcastSecurityMiddleware / TemporalContextMiddleware
ctx = get_request_tool_context() or self.context  # ContextVar takes priority
```

This means middleware baked into a cached graph at compile time still gets fresh per-request context via the ContextVar bridge.

**Log markers (real):**

| Log | Source | Meaning |
|-----|--------|---------|
| `[GRAPH_COMPILE] Compiling new graph for session ...` | `agent_service.py` | Compiling a new graph (cache miss) |
| `[GRAPH_CREATION_COMPLETE] _create_deep_agent_graph \| duration_ms=...` | `agent_service.py` | Compilation finished (includes `duration_ms`, `graph_type`) |
| `Compiled <label> '<name>' with <N> tools` | `subagent_compiler.py:225` | Specialist graph compiled with N tools |
| `[SUPERVISOR] DB specialist loading failed: ...` | `supervisor_orchestrator.py:344` | DB specialist load error |
| `Building fallback graph with direct tool access` | `supervisor_orchestrator.py:1206` | Supervisor unavailable; falling back |

> **Note:** `CompiledGraphCache hit/miss` and `LLMClientCache hit/miss` are conceptual labels for the LRU lookups inside `graph_cache.py`; check that module for the actual log strings.

### Specialists (DB-Configurable)

Specialists are stored in `ai_assistant_configs` with `agent_type='specialist'` and loaded via `subagents/db_loader.py:load_specialists_from_db()`. The set is fully DB-driven (seeded from `backend/seed/ai_specialist_configs.json`); there is no hardcoded specialist list in code. Typical seeded specialists:

| Specialist | Purpose | Key Tools |
|----------|---------|-----------|
| `project_manager` | Projects, WBEs, cost elements & cost registrations | Full project CRUD |
| `evm_analyst` | EVM metrics & performance | `calculate_evm_metrics`, `get_evm_performance_summary`, `analyze_cost_variance`, etc. |
| `change_order_manager` | Change order workflows | `list_change_orders`, `create_change_order`, `analyze_change_order_impact`, etc. |
| `user_admin` | User & department management | `list_users`, `create_user`, `list_departments`, etc. |
| `visualization_specialist` | Diagram generation | `generate_mermaid_diagram` |
| `forecast_manager` | Forecasts, cost tracking & schedule baselines | `get_forecast`, `create_forecast`, `compare_forecast_scenarios`, etc. |
| `general_purpose` | Fallback for cross-cutting requests | All tools |

### Main Agents (DB-Configurable)

Main agents are stored in `ai_assistant_configs` with `agent_type='main'`. Only main agents appear in the chat assistant selector:

| Main Agent | Default Role | Direct Tools |
|-----------|-------------|-------------|
| `Friendly Project Analyzer` | `ai-viewer` | `get_temporal_context`, `set_temporal_context`, `global_search` |
| `Senior Project Manager` | `ai-manager` | `get_temporal_context`, `set_temporal_context`, `global_search` |
| `System Manager` | `ai-admin` | `get_temporal_context`, `set_temporal_context`, `global_search` |

Direct tools are configured via `delegation_config.direct_tools` on each main agent and are fully admin-configurable. When direct tools are present, the supervisor can execute lightweight operations (e.g., changing the as-of date) without delegation overhead.

#### Structured Output for Subagents

Subagents can return typed Pydantic models via LangGraph's `with_structured_output()` pattern. This ensures type preservation and numeric precision (e.g., CPI as float instead of string).

**Configuration:** Each subagent config includes an optional `structured_output_schema` field:

```python
EVM_ANALYST_SUBAGENT: dict[str, Any] = {
    "name": "evm_analyst",
    "description": "Specialist for earned value management calculations and performance analysis",
    "system_prompt": "...",
    "structured_output_schema": EVMMetricsRead,  # Returns typed EVM metrics
}
```

**Schema mappings:**

| Subagent | Schema | Source |
|----------|--------|--------|
| `evm_analyst` | `EVMMetricsRead` | `app.models.schemas.evm` |
| `forecast_manager` | `ForecastRead` | `app.models.schemas.forecast` |
| `change_order_manager` | `ImpactAnalysisResponse` | `app.models.schemas.impact_analysis` |

**Implementation:**

1. **Compilation** (`subagent_compiler.py:compile_subagents`):
   - When `structured_output_schema` is defined, applies `.with_structured_output(schema)` wrapper
   - Wrapped subagent returns Pydantic model instances instead of text

2. **Result handling** (`subagent_task.py:_return_command_with_state_update`):
   - Detects Pydantic model in subagent content
   - Generates human-readable summary via `_summarize_structured_output()`
   - Stores structured data in `ToolMessage.additional_kwargs["structured_output"]` as JSON
   - Preserves type information for downstream processing

**Benefits:**

- **Type preservation**: Numeric values (CPI=0.25) returned as float, not "0.25" as string
- **Schema reuse**: Leverages existing Pydantic schemas from `app.models.schemas.*`
- **Human-readable**: Automatic summary generation for chat display
- **Structured storage**: JSON data attached to messages for programmatic access

### Tool Filtering Pipeline

```
create_project_tools(context)  ->  dynamic tool list
    |                                  (12 functional template modules + _pagination;
    |                                   MCP tools appended at runtime;
    |                                   exact count is dynamic — logged on cache fill)
    |
    v filter_tools_by_role(assistant_role)
    |
    v filter_tools_by_role(user_role)
    |
    v filter_tools_by_execution_mode()
    |
    +-- SAFE mode:    Keep only LOW risk tools
    +-- STANDARD mode: Keep ALL tools (CRITICAL blocked later by BackcastSecurityMiddleware)
    +-- EXPERT mode:   Keep ALL tools (LOW + HIGH + CRITICAL)
```

The number of tools produced by `create_project_tools()` is **dynamic** — it is logged at cache-fill time (`Created and cached <N> tools for AI chat`) rather than hardcoded. It grows when MCP servers are registered. The role-count splits in `filter_tools_by_role` are likewise data-driven, so do not treat any specific count as a constant.

Risk levels are set via the `@ai_tool` decorator:
- `LOW` — read-only operations (e.g., `list_projects`, `calculate_evm_metrics`)
- `HIGH` — modifies data with validation (e.g., `create_project`, `update_forecast`)
- `CRITICAL` — deletes data or bulk operations (e.g., `delete_cost_element`, `delete_users`)

**AI RBAC Roles:**

Three AI-specific roles control tool access:

| Role | Permissions | Use Case |
|------|-------------|----------|
| `ai-viewer` | project:read, forecast:read, evm:read | Read-only assistants for data exploration |
| `ai-manager` | project:write, change_order:write, forecast:write | Day-to-day project management assistants |
| `ai-admin` | user:write, department:write, cost_element_type:write | System administration assistants |

The assistant's `default_role` field determines which role is used for filtering. This role is applied AFTER execution mode filtering and BEFORE subagent compilation, so subagents also inherit the role restriction.

### StateGraph Fallback

When the supervisor path is unavailable (import error, no specialists compiled, or all filtered out), the system falls back to `graph.py:create_graph()`:

```
StateGraph(AgentState)
    entry_point -> "agent"
    "agent" --[has tool_calls]--> "tools"
    "agent" --[no tool_calls]--> END
    "tools" --------------------> "agent"  (loop back)

Iteration cap: max_tool_iterations (agent state field; docstring example default 5)

Returns: (compiled_graph, interrupt_node) tuple
```

Tool node selection:
- With context + websocket + session_id -> `InterruptNode` (approval support)
- With context only -> `RBACToolNode` (permission checks)
- No context -> `ToolNode` (basic)

> **Recursion limit.** The per-request `recursion_limit` passed to `astream_events`
> defaults to **25** (`agent_service.py:860-862`) and is configurable per assistant via
> `assistant_config.recursion_limit`. This is distinct from the StateGraph-fallback
> `max_tool_iterations` state field.

---

## 5. Decoupled Execution

> **Event bus deep-dive.** `AgentEventBus`, `AgentRunnerManager`, and the decoupled-execution
> primitives are covered as shared concepts in [`ai/agent-common-concepts.md`](ai/agent-common-concepts.md).
> This section focuses on how the WebSocket/REST entry points drive an execution lifecycle.

### Architecture Overview

Agent execution is decoupled from WebSocket connections via an event bus architecture. This enables agents to continue running independently of network disruptions and supports multiple consumers (WebSocket, REST polling, test harnesses).

```
WebSocket Handler              Agent Execution               REST Endpoint
     |                               |                              |
     |---> POST /invoke -----------> |                              |
     |                               |                              |
     |                               |  Creates AIAgentExecution    |
     |                               |  (DB: status="running")      |
     |                               |                              |
     |<-- WSExecutionStartedMessage -|                              |
     |    {execution_id}             |                              |
     |                               |                              |
     |---> WS:subscribe ------------>|                              |
     |    {execution_id,             |                              |
     |     last_seen_sequence:0}     |                              |
     |                               |                              |
     |                               |  AgentEventBus publishes     |
     |<------------------------------|-------------------------------|
     |    events (tokens, tools)     |  AgentEventBus.publish()     |
     |                               |                              |
     |                               |  On complete/error:          |
     |<------------------------------|  status="completed"/"error"  |
     |    WSCompleteMessage          |                              |
     |                               |                              |
GET /executions/{id}/status -------->|                              |
     |                               |                              |
     |<------------------------------|  Return AgentExecutionPublic |
```

### AgentService.start_execution()

File: `backend/app/ai/agent_service.py` (`start_execution`, line 2001)

Entry point invoked by both the WebSocket `chat` handler and the REST `POST /invoke` endpoint. Creates an independent agent execution with its own DB session and event bus, then runs the graph as a background task via `asyncio.create_task()`.

```python
execution_id = await agent_service.start_execution(
    message="Calculate EVM metrics",
    assistant_config=config,
    session_id=session,
    user_id=user_id,
    project_id=project_id,
)
```

Returns execution ID string. Execution status tracked in DB via `AIAgentExecution`.

### AgentService._run_agent_graph()

File: `backend/app/ai/agent_service.py` (`_run_agent_graph`, line 1722)

Builds the agent graph and streams events to the event bus. Internally calls `_process_stream_events()` (line 1412), which runs the `astream_events()` loop with transient-error retry logic.

```python
async def _run_agent_graph(self, ctx: GraphContext) -> None:
    ...
    graph, interrupt_node = await self._create_deep_agent_graph(params)
    ...
    await self._process_stream_events(ctx)  # publishes AgentEvents to ctx.event_bus
```

### AIAgentExecution Model

File: `backend/app/models/domain/ai.py`

Database entity tracking agent executions with status lifecycle.

```python
class AIAgentExecution(SimpleEntityBase):
    session_id: UUID                    # FK to ai_conversation_sessions
    status: str                          # "pending" | "running" | "completed" | "error" | "awaiting_approval" | "stopped"
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    execution_mode: str                  # "safe" | "standard" | "expert"
    total_tokens: int = 0
    tool_calls_count: int = 0
```

Status lifecycle:
```
pending -> running -> [completed | error | awaiting_approval | stopped]
```

#### AIConversationSession.active_execution_id

File: `backend/app/models/domain/ai.py`

Optional field referencing the currently running agent execution. Used by frontend to auto-reconnect after network disruptions.

```python
active_execution_id: UUID | None  # Currently running or last execution
```

### Startup Cleanup Handler

File: `backend/app/main.py` (`_cleanup_orphaned_executions`)

On server startup, marks orphaned executions as errored:

- Finds executions with status `running`, `pending`, or `awaiting_approval`
- Updates status to `error` with message "Server restarted during execution"
- Clears `active_execution_id` on sessions referencing orphaned executions

This prevents stale references after in-memory event buses are destroyed.

### Reconnection Flow

When a WebSocket reconnects:

1. Frontend checks `activeExecutionIdRef` from previous connection
2. Sends subscribe message: `{"type":"subscribe", "execution_id":"...", "last_seen_sequence":N}`
3. Server looks up bus via `runner_manager.get_bus()`
4. If bus exists:
   - Replays events since `last_seen_sequence`
   - Subscribes to live events until completion
5. If bus not found (execution completed or server restarted):
   - Returns error message, client can poll `/executions/{id}/status` instead

---

## 6. Reply Flow & Streaming

### Event Streaming

File: `agent_service.py` (`_process_stream_events`, line 1412)

```python
async for event in ctx.graph.astream_events(
    {"messages": history, "tool_call_count": 0, "next": "agent"},
    config={"recursion_limit": ctx.recursion_limit, "configurable": {"thread_id": str(ctx.session_id)}},
    version="v1",
):
```

### Event Handling

The stream is processed by dedicated handlers on `AgentService`:

| Handler | LangGraph Event(s) | WS Message(s) |
|---------|--------------------|---------------|
| `_handle_chat_model_stream` | `on_chat_model_stream` | `WSTokenMessage` / `WSTokenBatchMessage` (via TokenBufferManager) |
| `_handle_tool_start` | `on_tool_start` | `WSPlanningMessage` (write_todos), `WSSubagentMessage` (task), `WSToolCallMessage` (other) |
| `_handle_tool_end` | `on_tool_end` | `WSToolResultMessage`, `WSSubagentResultMessage` + `WSContentResetMessage`, `WSAgentCompleteMessage` (task) |
| `_handle_graph_end` | `on_end` | `WSCompleteMessage` |

> Planning events are emitted by detecting the `write_todos` tool name (`TOOL_NAME_WRITE_TODOS` in `event_types.py:43`) inside `_handle_tool_start` — there is no dedicated middleware class.

### Step Tracking

The stream maintains a step counter and estimated total:

```python
current_step = 0
estimated_total_steps = None

# When write_todos is detected:
estimated_total_steps = len(plan_steps)

# When any tool is called:
current_step += 1
```

Every `WSToolCallMessage`, `WSSubagentMessage`, and `WSPlanningMessage` includes `step_number` and `total_steps`.

### Subagent Result Handling

Handled inline in `agent_service.py:_handle_tool_end()` when a subagent completes via the `task` tool:

1. **Content extraction**: Subagent content is extracted from the tool output (ToolMessage, Command, or dict)
2. **Structured output detection** (`subagent_task.py:_return_command_with_state_update`):
   - If the subagent has a `structured_output_schema`, content is checked for a Pydantic model instance
   - When detected, structured data is extracted and serialized to JSON
   - Human-readable summary is generated via `_summarize_structured_output()`
   - Structured data is attached to `ToolMessage.additional_kwargs["structured_output"]`
   - Preserves type information (e.g., CPI=0.25 as float, not "0.25" as string)
3. **Persistence**: Content is tracked in `subagent_messages_by_main_invocation` for ordered persistence
4. **Client notification**: `WSSubagentResultMessage` is sent (displayed in Activity Panel)
5. **Buffer flush**: Subagent token buffer is flushed
6. **Completion**: `WSAgentCompleteMessage` is sent (completion indicator for UI)
7. **Reset**: `WSContentResetMessage` is sent to clear the streaming buffer
8. **State preservation**: `accumulated_content` is NOT reset — main agent thoughts persist across subagent executions
9. **Next invocation**: A new `main_invocation_id` is generated for the next main agent bubble

Messages are persisted to DB in conversational order: main segment -> subagents -> next main segment.

**Structured output schemas** and their summaries:

- `EVMMetricsRead`: EVM metrics (CPI, SPI, CV, SV, EAC, ETC) with status indicators
- `ForecastRead`: Forecast projections with budget variance and basis of estimate
- `ImpactAnalysisResponse`: Change order impact with KPI scorecard and entity changes

### Token Buffering

File: `agent_service.py` (`TokenBufferManager`) and `token_buffer.py`

The stream uses a `TokenBufferManager` that batches individual LLM tokens before sending via WebSocket. Instead of one WS message per token, tokens are accumulated and flushed as `WSTokenBatchMessage` either:
- On buffer timeout (configurable interval)
- When buffer size exceeds threshold
- On explicit flush (before tool calls, on subagent transitions, on stream completion)

Configuration comes from `settings.AI_TOKEN_BUFFER_INTERVAL_MS`, `settings.AI_TOKEN_BUFFER_MAX_SIZE`, and `settings.AI_TOKEN_BUFFER_ENABLED`.

### Transient Error Handling

Long-running agent executions (5+ minutes) may encounter transient network errors such as `httpcore.ReadError` or `httpx.RemoteProtocolError` during LLM streaming. The `_process_stream_events()` `astream_events()` loop is wrapped in a retry mechanism:

- **Max retries:** 2 (total of 3 attempts)
- **Delay between retries:** 2 seconds
- **Transient error detection:** Catches `ConnectionResetError`, `OSError`, and inspects exception type/module for `httpcore.ReadError` and `httpx.RemoteProtocolError` (without hard imports)
- **Non-transient errors propagate immediately** — only network-level errors trigger retries
- **`stream_chunk_timeout`** is set to 300 seconds on the LLM client to prevent LangChain's internal timeout during long executions
- **Checkpoint resilience:** Tool calls that completed before the error are preserved because the graph resumes from its checkpoint state on retry
- **Final failure:** If all retries are exhausted, the exception is captured and an error event is published to the event bus

### Error Persistence

When graph execution fails, the exception is captured in `graph_error` and persisted to the session as an assistant message:

```python
AIConversationMessage(
    role="assistant",
    content="I encountered an error while processing your request: <error>. The work completed before the error has been saved.",
    metadata={"error": True, "error_type": "ReadError"},
)
```

This ensures users see what went wrong when reopening the session, rather than a blank response. Previously committed messages (subagent results, main agent segments) are preserved because they are persisted in a separate loop before the error message is written.

---

## 7. Approval Flow (Human-in-the-Loop)

### When Approval is Required

```
Tool risk_level == HIGH
    AND execution_mode == STANDARD
    AND InterruptNode is available
```

Note: CRITICAL tools in STANDARD mode are **blocked entirely** by `BackcastSecurityMiddleware._check_risk_level()` — they never reach the approval flow. Only HIGH-risk tools go through approval in standard mode.

| Execution Mode | LOW tools | HIGH tools | CRITICAL tools |
|---------------|-----------|------------|----------------|
| `safe` | Allowed | Blocked | Blocked |
| `standard` | Allowed | Approval required | Blocked |
| `expert` | Allowed | Allowed | Allowed |

### Approval Sequence

```
Server                              Client (Browser)
  |                                     |
  | Tool call detected (HIGH risk)      |
  |                                     |
  | WSApprovalRequestMessage            |
  | {type:"approval_request",           |
  |  approval_id:"uuid",                |
  |  tool_name:"create_project",        |
  |  tool_args:{...},                   |
  |  risk_level:"high",                 |
  |  expires_at:"2026-03-24T12:35:00Z"} |
  |------------------------------------>|
  |                                     | Show approval dialog
  |                                     |
  | WSPollingHeartbeatMessage (every 5s)|
  | {type:"polling_heartbeat",          |
  |  approval_id:"uuid",                |
  |  elapsed_seconds:5,                 |
  |  remaining_seconds:295}             |
  |------------------------------------>|
  |                                     |
  | WSApprovalResponseMessage           |
  | {type:"approval_response",          |
  |  approval_id:"uuid",                |
  |  approved:true,                     |
  |  user_id:"uuid",                    |
  |  timestamp:"2026-03-24T12:30:05Z"}  |
  |<------------------------------------|
  |                                     |
  | [Tool executes if approved]         |
  | [Error returned if rejected/timeout]|
```

### Polling Details

- **Poll interval**: 200ms
- **Max poll time**: governed by `settings.AI_APPROVAL_TIMEOUT_SECONDS`
- **Approval expiration**: safety net for stale approvals (set in `InterruptNode`)
- **Heartbeat interval**: Every 5 seconds during polling
- **On timeout**: Error message returned to client, tool not executed

### Registration Flow

1. `InterruptNode._send_approval_request()` creates UUID, stores in `pending_approvals` dict
2. Client receives `WSApprovalRequestMessage`
3. Client sends `WSApprovalResponseMessage` via WebSocket
4. `ai_chat.py:message_handler()` dispatches to `AgentService.register_approval_response()`
5. Updates `pending_approvals[approval_id]["approved"]`
6. Polling loop in `BackcastSecurityMiddleware._check_risk_level_with_approval()` detects the update

---

## 8. Security Model

> **Shared concepts.** Tool filtering, RBAC, and the middleware stack are covered in
> [`ai/agent-common-concepts.md`](ai/agent-common-concepts.md).

### Three-Tier Security

```
Tier 1: JWT Authentication
    v (ai_chat.py - before websocket.accept)
Tier 2: RBAC Permission Checking (per-tool)
    v (BackcastSecurityMiddleware._check_tool_permission)
Tier 3: Risk-Based Execution Modes
    v (filter_tools_by_execution_mode + approval workflow)
```

### Execution Modes

| Mode | LOW (read) | HIGH (write) | CRITICAL (delete) | Approval? |
|------|------------|--------------|-------------------|-----------|
| `safe` | yes | no | no | N/A (tools not available) |
| `standard` | yes | yes (approval) | no (blocked by middleware) | Yes, for HIGH only |
| `expert` | yes | yes | yes | No |

### Temporal Context Injection

Temporal parameters are injected at the **middleware level**, not in the prompt. This is a security measure — the LLM cannot override them via prompt injection.

File: `middleware/temporal_context.py`

```python
# LLM might request: {"as_of": "2025-01-01", "project_id": "other-id"}
# Middleware overrides to: {"as_of": "2024-06-01", "project_id": "locked-id"}
```

Injected parameters: `as_of`, `branch_name`, `branch_mode`, `project_id`.

### Tool Permission Checking

Each tool declares required permissions via the `@ai_tool` decorator:

```python
@ai_tool(
    permissions=["project:read"],
    risk_level=RiskLevel.LOW,
    category="projects",
)
async def list_projects(context: InjectedToolArg[ToolContext], ...) -> ...:
    ...
```

`BackcastSecurityMiddleware._check_tool_permission()` extracts the metadata and checks each permission via `ToolContext.check_permission()`.

---

## 9. Integration & Debugging

This section consolidates the parts of this doc that are genuinely *integration-specific* (not duplicated in the sibling references): sequence diagrams, troubleshooting, SQL queries, and telemetry.

### Log Markers (Real)

Search `backend/logs/app.log` for these markers to trace request flow. Only markers that actually exist in source are listed:

| Log Marker | Location | What It Tells You |
|------------|----------|-------------------|
| `WebSocket chat connection established for user` | `ai_chat.py` | Connection accepted (auth passed) |
| `[GRAPH_COMPILE] Compiling new graph for session ...` | `agent_service.py` | Graph compilation starting (cache miss) |
| `[GRAPH_CREATION_COMPLETE] _create_deep_agent_graph \| duration_ms=...` | `agent_service.py` | Graph compilation finished |
| `Compiled <label> '<name>' with <N> tools` | `subagent_compiler.py` | Specialist graph compiled with N tools |
| `[SUPERVISOR] DB specialist loading failed: ...` | `supervisor_orchestrator.py` | DB specialist load error |
| `Building fallback graph with direct tool access` | `supervisor_orchestrator.py` | Supervisor unavailable; fallback path |
| `Filtered <N> tools down to <M> for execution_mode=...` | `tools/__init__.py` | Execution-mode tool filtering |
| `Filtered <N> tools down to <M> for role=...` | `tools/__init__.py` | RBAC tool filtering |
| `Created and cached <N> tools for AI chat` | `tools/__init__.py` | Tool list built & cached |
| `on_chat_model_stream` / `on_tool_start` / `on_tool_end` | `agent_service.py` | LangGraph event handler dispatched |
| `APPROVAL_REQUEST_SENT: approval_id=..., tool='...'` | `interrupt_node.py` | Approval request sent to client |
| `[APPROVAL_GRANTED] _poll_for_approval \| ...` | `backcast_security.py` | User approved the tool |
| `[APPROVAL_TIMEOUT] _poll_for_approval \| ...` | `backcast_security.py` | Approval polling timed out |

> The old markers `[AGENT_CREATION_START]`, `[TOOL_FILTERING]`, `Creating agent with subagents`,
> `Compiled subagent '...'`, `Agent created successfully`, `[CHAT_STREAM_ENTRY]`,
> `[CHAT_STREAM_COMPLETE]`, `[GRAPH_CACHE_HIT]`, `[GRAPH_CREATION_START]`, and
> `[SUBAGENT_DELEGATION]` **no longer exist in source** — they referenced the removed
> `deep_agent_orchestrator.py` and an older logging scheme.

### Common Issues

#### Connection closes immediately with code 1008

**Cause**: Auth failure. Check:
1. JWT token is valid and not expired
2. Token subject contains a valid user email
3. User exists in the database
4. User's role has `ai-chat` permission

#### Connection closes with code 4008

**Cause**: JWT token expired. Client should refresh and reconnect.

#### "Session not found" error

**Cause**: Invalid `session_id` in chat request. The session either doesn't exist or belongs to a different user.

#### Tools not available to agent

**Cause**: Tool filtering. Check:
1. `assistant_config.default_role` — assistant's RBAC role must have permission for the tool
2. User's RBAC role — user must have the required permissions
3. `execution_mode` — tool risk level must be compatible
4. Supervisor mode — main agent has NO direct tools (except `delegation_config.direct_tools`); it must delegate

#### Approval request never arrives at client

**Cause**: WebSocket disconnect during polling. The heartbeat mechanism (every 5s) should prevent this, but proxy timeouts can still occur. Check reverse proxy WebSocket timeout settings.

#### Subagent returns no results

**Cause**: Subagent has no valid tools after filtering. Check logs for `"has no valid tools after filtering - skipping"`.

#### Database session errors after tool execution

**Cause**: Unhandled exception in a tool left the DB session in a bad state. The system performs automatic rollback on tool errors, but if you see cascading errors, check the tool implementation.

#### `Chat error: Error 500` during long execution

**Cause**: LLM API stream dropped by network intermediary. The system auto-retries up to 2 times. If persistent, check `app.log` for `Transient stream error` entries. The `stream_chunk_timeout` (300s) should prevent most premature timeouts.

#### Follow-up message stuck "generating" after error

**Cause**: WebSocket did not reconnect cleanly after a 500 error. The frontend now force-closes stale connections and triggers exponential backoff reconnection. If still stuck, refresh the page and check the browser console for WebSocket state.

#### Missing subagent output after error

**Cause**: Stream interrupted mid-subagent response. Partial results are persisted to the database before the error occurs. Check session messages via `GET /api/v1/ai/sessions/{id}/messages` to see what was saved.

#### `httpcore.ReadError` in app.log

**Cause**: Network timeout during long LLM streaming. Normal behavior — the retry mechanism handles this automatically (2 retries, 2-second delay). If frequent, consider increasing `stream_chunk_timeout` beyond 300 seconds or investigate network stability between the server and LLM provider.

### Tracing a Request

1. **Find the session ID** from the frontend or from the initial chat request
2. **Search logs** for the session ID: `grep "<session_id>" backend/logs/app.log`
3. **Follow the markers**:
   - `[GRAPH_COMPILE]` -> `[GRAPH_CREATION_COMPLETE]` (only on cache miss)
   - -> `Filtered ... tools down to ...` -> `Compiled '<name>' with N tools`
   - -> `on_tool_start` -> `APPROVAL_REQUEST_SENT` (if HIGH-risk approval) / `[APPROVAL_GRANTED]` / `[APPROVAL_TIMEOUT]`
   - -> `on_tool_end` -> `on_chat_model_stream` -> `complete`
4. **Check OpenTelemetry** if Phoenix is running (OTLP endpoint at `localhost:6006`)

### Sequence Diagrams

#### Full Conversation: Specialist Delegation + Approval

This combined diagram shows a typical multi-specialist flow that also hits the approval path. It is the unique integration sequence for this doc (the per-message field reference lives in `message-types.md`).

```
Client                                Server
  |                                     |
  |--- WSChatRequest (new session) ---->|
  |                                     |
  |<-- WSThinkingMessage ---------------|
  |<-- WSPlanningMessage ---------------|  (write_todos tool detected)
  |                                     |
  |<-- WSSubagentMessage (evm_analyst) -|  (task/handoff tool detected)
  |<-- WSTokenMessage (subagent) ------|  (specialist streams)
  |<-- WSTokenMessage (subagent) ------|
  |<-- WSSubagentResultMessage --------|  (specialist done)
  |<-- WSContentResetMessage ----------|  (clear buffer)
  |                                     |
  |<-- WSSubagentMessage (forecast_mgr)|  (second specialist)
  |<-- WSApprovalRequestMessage -------|  (HIGH risk tool!)
  |<-- WSPollingHeartbeatMessage ------|
  |--- WSApprovalResponse (approved) ->|
  |<-- WSToolResultMessage ------------|  (tool executed)
  |<-- WSSubagentResultMessage --------|  (specialist done)
  |<-- WSContentResetMessage ----------|
  |                                     |
  |<-- WSTokenMessage (main agent) ----|  (synthesis)
  |<-- WSTokenMessage (main agent) ----|
  |<-- WSCompleteMessage --------------|
```

### Database Queries for Debugging

```sql
-- List recent AI chat sessions
SELECT id, user_id, title, project_id, created_at, updated_at
FROM ai_conversation_sessions
ORDER BY created_at DESC
LIMIT 20;

-- Get messages for a session
SELECT id, role, content, created_at,
       tool_calls IS NOT NULL as has_tool_calls,
       tool_results IS NOT NULL as has_tool_results
FROM ai_conversation_messages
WHERE session_id = '<session_uuid>'
ORDER BY created_at;

-- Check tool calls and results (JSONB fields)
SELECT role, tool_calls, tool_results
FROM ai_conversation_messages
WHERE session_id = '<session_uuid>'
  AND role = 'assistant'
ORDER BY created_at DESC
LIMIT 5;

-- Active assistant configs (with agent type)
SELECT id, name, model_id, is_active, default_role, agent_type,
       delegation_config->'direct_tools' as direct_tools
FROM ai_assistant_configs
WHERE is_active = true
ORDER BY agent_type, name;

-- List agent executions for a session
SELECT id, session_id, status, started_at, completed_at,
       execution_mode, total_tokens, tool_calls_count, error_message
FROM ai_agent_executions
WHERE session_id = '<session_uuid>'
ORDER BY started_at DESC;

-- Find sessions with active/running executions
SELECT s.id, s.title, s.active_execution_id, e.status, e.started_at
FROM ai_conversation_sessions s
LEFT JOIN ai_agent_executions e ON s.active_execution_id = e.id
WHERE s.user_id = '<user_uuid>'
ORDER BY s.updated_at DESC;
```

### Telemetry: Phoenix

For AI observability with Arize Phoenix (file: `backend/app/ai/telemetry.py` — `initialize_telemetry()`, `trace_context()`, `trace_subagent_delegation()`):

```bash
# Set environment variables
export OTEL_ENABLED=true
export OTLP_ENDPOINT=http://localhost:6006/v1/traces
export OTEL_CONSOLE_EXPORT=true  # Also log spans to console

# Start Phoenix
docker compose -f backend/docker/phoenix.docker-compose.yml up -d

# View traces at http://localhost:6006
```

---

## 10. Key Files Quick Reference

### Core

| File | Purpose |
|------|---------|
| `backend/app/api/routes/ai_chat.py` | WebSocket endpoint `chat_stream()` at `/stream`, REST endpoints (`/invoke`, `/executions/*`), auth, message dispatch, subscribe handling |
| `backend/app/ai/agent_service.py` | Main orchestration: `_create_deep_agent_graph()` (557), `_run_agent_graph()` (1722), `_process_stream_events()` (1412), `start_execution()` (2001), approval registration, history building |
| `backend/app/ai/supervisor_orchestrator.py` | `SupervisorOrchestrator` — handoff-based delegation via parent StateGraph with direct tool support and DB specialist loading |
| `backend/app/ai/supervisor_state.py` | `BackcastSupervisorState` — shared state schema for supervisor graph (messages, active_agent, tool_call_count) |
| `backend/app/ai/handoff_tools.py` | `create_handoff_tool()` / `create_all_handoff_tools()` — handoff tools using `Command(goto=...)` for specialist routing |
| `backend/app/ai/graph_cache.py` | Caching infrastructure: `LLMClientCache`, `CompiledGraphCache`, `GraphCacheKey`, `BackcastRuntimeContext`, shared checkpointer, ContextVar helpers |
| `backend/app/ai/graph.py` | `create_graph()` — StateGraph fallback (no specialists) |
| `backend/app/ai/state.py` | `AgentState` TypedDict (messages, tool_call_count, max_tool_iterations, next) |

### Execution Architecture

| File | Purpose |
|------|---------|
| `backend/app/ai/execution/agent_event.py` | `AgentEvent` dataclass — immutable event structure for agent execution events |
| `backend/app/ai/execution/agent_event_bus.py` | `AgentEventBus` — in-memory pub/sub with bounded replay buffer for agent events |
| `backend/app/ai/execution/runner_manager.py` | `AgentRunnerManager` — process-level singleton registry mapping execution IDs to event buses |
| `backend/app/ai/event_types.py` | `ExecutionStatus` enum, `AgentEventType` enum, `TOOL_NAME_WRITE_TODOS` / `TOOL_NAME_TASK` constants |
| `backend/app/alembic/versions/6c93c299c703_add_ai_agent_executions_table.py` | Migration creating `ai_agent_executions` table for execution tracking |
| `backend/app/main.py` | Startup handler `_cleanup_orphaned_executions()` — marks orphaned executions as errored on server restart |

### Specialists

| File | Purpose |
|------|---------|
| `backend/app/ai/subagents/__init__.py` | Re-export of `load_specialists_from_db` / `invalidate_cache` (DB-driven; no hardcoded configs) |
| `backend/app/ai/subagents/db_loader.py` | `load_specialists_from_db()`, `assistant_config_to_specialist_dict()`: TTL-cached DB specialist loading |
| `backend/app/ai/subagent_compiler.py` | `compile_subagents()` (98): shared compilation logic for specialist graphs |
| `backend/app/ai/tools/subagent_task.py` | `build_task_tool()`, `_return_command_with_state_update()`, `_summarize_structured_output()` — structured output handling |

### Tools

| File | Purpose |
|------|---------|
| `backend/app/ai/tools/__init__.py` | `create_project_tools()` factory (dynamic tool count), `filter_tools_by_execution_mode()`, `filter_tools_by_role()` |
| `backend/app/ai/tools/types.py` | `ToolContext`, `ToolMetadata`, `RiskLevel`, `ExecutionMode` |
| `backend/app/ai/tools/decorator.py` | `@ai_tool` decorator for tool registration with metadata |
| `backend/app/ai/tools/interrupt_node.py` | `InterruptNode` — approval request/response via WebSocket |
| `backend/app/ai/tools/rbac_tool_node.py` | `RBACToolNode` — permission-aware tool node (StateGraph path) |
| `backend/app/ai/tools/subagent_task.py` | `build_task_tool()`, `TASK_SYSTEM_PROMPT` — task tool for subagent delegation |
| `backend/app/ai/tools/session_manager.py` | `ToolSessionManager` — task-local DB sessions for concurrent tool execution |
| `backend/app/ai/tools/approval_audit.py` | Approval audit trail logging |
| `backend/app/ai/tools/risk_check_node.py` | Standalone risk checking node |
| `backend/app/ai/tools/templates/` | Tool template modules: 12 functional templates (project, wbe, cost_element, cost_event, cost_event_type, change_order, forecast_cost_progress, control_account, work_package, analysis, advanced_analysis, diagram) + `_pagination` shared helper |

### Middleware

| File | Purpose |
|------|---------|
| `backend/app/ai/middleware/backcast_security.py` | RBAC checks + risk-based approval via `InterruptNode` |
| `backend/app/ai/middleware/temporal_context.py` | Injects `as_of`, `branch_name`, `branch_mode`, `project_id` into tool args |

### Streaming

| File | Purpose |
|------|---------|
| `backend/app/ai/token_buffer.py` | `TokenBuffer`, `TokenBufferManager` — batched token sending to reduce WebSocket overhead |

### Schemas & Models

| File | Purpose |
|------|---------|
| `backend/app/models/schemas/ai.py` | All Pydantic WS schemas: `WSChatRequest`, `WSTokenMessage`, `WSApprovalRequestMessage`, `WSSubscribeMessage`, `WSExecutionStartedMessage`, `WSExecutionStatusMessage`, `AgentExecutionPublic`, `InvokeAgentRequest`, etc. (canonical protocol reference in [`backend/contexts/ai/message-types.md`](backend/contexts/ai/message-types.md)) |
| `backend/app/models/schemas/evm.py` | `EVMMetricsRead` — structured output schema for EVM analyst subagent |
| `backend/app/models/schemas/forecast.py` | `ForecastRead` — structured output schema for forecast manager subagent |
| `backend/app/models/schemas/impact_analysis.py` | `ImpactAnalysisResponse` — structured output schema for change order manager subagent |
| `backend/app/models/domain/ai.py` | SQLAlchemy models: `AIConversationSession`, `AIConversationMessage`, `AIAgentExecution` |

### Services

| File | Purpose |
|------|---------|
| `backend/app/services/ai_config_service.py` | Session CRUD, message CRUD, assistant config management |

### Observability

| File | Purpose |
|------|---------|
| `backend/app/ai/telemetry.py` | OpenTelemetry setup: `initialize_telemetry()`, `trace_context()`, `trace_subagent_delegation()` |
| `backend/app/ai/monitoring.py` | Monitoring and metrics collection |
