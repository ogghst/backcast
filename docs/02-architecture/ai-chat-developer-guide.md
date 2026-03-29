# AI Chat Developer Guide

Comprehensive reference for understanding, debugging, and extending the Backcast AI chat system.

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [WebSocket Connection Lifecycle](#2-websocket-connection-lifecycle)
3. [Starting a Conversation](#3-starting-a-conversation)
4. [Agent Setup & Orchestration](#4-agent-setup--orchestration)
5. [Decoupled Execution](#5-decoupled-execution)
6. [Reply Flow & Streaming](#6-reply-flow--streaming)
7. [Approval Flow (Human-in-the-Loop)](#7-approval-flow-human-in-the-loop)
8. [WebSocket Protocol Reference](#8-websocket-protocol-reference)
9. [Security Model](#9-security-model)
10. [Troubleshooting Guide](#10-troubleshooting-guide)
11. [Key Files Quick Reference](#11-key-files-quick-reference)

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
     |                                        | 7. LangChain agent plans (TodoListMiddleware)
     |  {type:"planning", steps:[...]}        |
     |<---------------------------------------|
     |                                        | 8. Delegates to subagent
     |  {type:"subagent", subagent:"evm_..."} |
     |<---------------------------------------|
     |  {type:"token", content:"Based on..."} |
     |<---------------------------------------| 9. Subagent streams tokens
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

### Two Execution Paths

| Path | When Used | Description |
|------|-----------|-------------|
| **LangChain Agent** (primary) | Default path | Multi-agent orchestration via `langchain.agents.create_agent()` with `task` delegation to 6 subagents |
| **StateGraph fallback** | Subagents disabled or no valid subagent tools | Direct LangGraph `StateGraph` with agent node, tool node, and conditional edges. Max 5 tool iterations. |

The primary path lives in `deep_agent_orchestrator.py` (`DeepAgentOrchestrator.create_agent()`), which wraps `langchain.agents.create_agent()` with Backcast config. The fallback path lives in `graph.py` (`create_graph()`).

### Core Components

```
ai_chat.py (WebSocket endpoint)
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
    +---> DeepAgentOrchestrator.create_agent()
    |         |
    |         +---> tools/__init__.py  (create_project_tools - All tools (69, 8 template packages))
    |         +---> subagents/__init__.py  (6 subagent configs)
    |         +---> middleware/
    |         |      +---> temporal_context.py   (inject as_of, branch)
    |         |      +---> backcast_security.py  (RBAC + approval)
    |         +---> langchain_create_agent()  (LangChain native)
    |
    +---> astream_events() loop
    |         |
    |         +---> on_chat_model_stream  --> WSTokenMessage
    |         +---> on_tool_start          --> WSToolCallMessage / WSSubagentMessage
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

---

## 2. WebSocket Connection Lifecycle

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
- `"chat"` (default) — processed via `agent_service.chat_stream()` as background task

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
# agent_service.py → config_service.create_session()
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

### Agent Creation Flow

File: `agent_service.py` (_create_deep_agent_graph) and `deep_agent_orchestrator.py` (create_agent)

```
1. create_project_tools(context)     → 69 LangChain BaseTool instances (8 template packages)
2. Filter by allowed_tools           → Assistant config whitelist
3. Filter by execution_mode          → Risk-level filtering (safe/standard/expert)
4. If subagents enabled:
   - Main agent gets NO Backcast tools (only task tool for delegation)
   - Subagents get filtered tool lists
5. Build middleware stack:
   - TemporalContextMiddleware(context)
   - BackcastSecurityMiddleware(context, tools=all_tools, interrupt_node)
6. Create SubAgent objects (6 subagents)
7. Build system prompt with delegation instructions
8. langchain_create_agent(model, tools, system_prompt, middleware)
9. Register InterruptNode for approval handling
```

### Graph Caching

Compiled agent graphs, LLM clients, and tool lists are cached and reused across requests. This avoids rebuilding the entire agent harness (~400ms) on every user prompt.

File: `graph_cache.py`

**What gets cached:**

| Layer | Cache Key | Scope |
|-------|-----------|-------|
| LLM client | `(model_name, temperature, max_tokens, base_url_hash)` | Application-wide |
| Tool list | Singleton (stateless — context injected via ContextVar) | Application-wide |
| Compiled graph | `GraphCacheKey(model_name, frozenset(allowed_tools), execution_mode, system_prompt_hash)` | Application-wide, LRU max 20 |
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

**Log markers:**

| Log | Meaning |
|-----|---------|
| `[GRAPH_CACHE_HIT]` | Reusing cached compiled graph |
| `[GRAPH_CREATION_START]` | Compiling new graph (cache miss) |
| `[GRAPH_CREATION_COMPLETE]` | Compilation finished (includes `duration_ms`) |
| `CompiledGraphCache hit` | LRU cache lookup succeeded |
| `CompiledGraphCache miss` | LRU cache lookup failed, compiling fresh |
| `LLMClientCache hit` | Reusing cached LLM client |
| `LLMClientCache miss` | Creating new LLM client |

### Subagents

6 specialized subagents defined in `subagents/__init__.py`:

| Subagent | Purpose | Key Tools |
|----------|---------|-----------|
| `project_manager` | Projects, WBEs, cost elements & cost registrations | `list_projects`, `get_project`, `create_project`, `update_project`, `list_wbes`, `get_wbe`, `create_wbe`, `list_cost_elements`, `get_cost_element`, `create_cost_element`, `update_cost_element`, `delete_cost_element`, `list_cost_element_types`, `get_cost_element_type`, `create_cost_element_type`, `update_cost_element_type`, `delete_cost_element_type`, `get_cost_element_summary`, `get_cost_registration`, `create_cost_registration`, `update_cost_registration`, `delete_cost_registration`, `list_cost_registrations`, `get_budget_status` |
| `evm_analyst` | EVM metrics & performance | `calculate_evm_metrics`, `get_evm_performance_summary`, `analyze_cost_variance`, `analyze_schedule_variance`, `get_project_kpis`, `assess_project_health`, `detect_evm_anomalies`, `generate_optimization_suggestions` |
| `change_order_manager` | Change order workflows | `list_change_orders`, `get_change_order`, `create_change_order`, `generate_change_order_draft`, `submit_change_order_for_approval`, `approve_change_order`, `reject_change_order`, `analyze_change_order_impact` |
| `user_admin` | User & department management | `list_users`, `get_user`, `create_user`, `update_user`, `delete_users`, `list_departments`, `get_department`, `create_department`, `update_department`, `delete_department` |
| `visualization_specialist` | Diagram generation | `generate_mermaid_diagram` |
| `forecast_manager` | Forecasts, cost tracking & schedule baselines | `get_forecast`, `create_forecast`, `update_forecast`, `compare_forecast_to_budget`, `get_budget_status`, `generate_project_forecast`, `compare_forecast_scenarios`, `get_forecast_accuracy`, `create_cost_registration`, `list_cost_registrations`, `get_cost_trends`, `get_cumulative_costs`, `get_latest_progress`, `create_progress_entry`, `get_progress_history`, `analyze_forecast_trends`, `get_schedule_baseline`, `update_schedule_baseline`, `delete_schedule_baseline` |

### Tool Filtering Pipeline

```
All tools (69, 8 template packages)
    │
    ▼ allowed_tools whitelist (assistant config)
Filtered to whitelist
    │
    ▼ filter_tools_by_execution_mode()
    │
    ├─ SAFE mode:    Keep only LOW risk tools
    ├─ STANDARD mode: Keep ALL tools (CRITICAL blocked later by BackcastSecurityMiddleware)
    └─ EXPERT mode:   Keep ALL tools (LOW + HIGH + CRITICAL)
```

Risk levels are set via the `@ai_tool` decorator:
- `LOW` — read-only operations (e.g., `list_projects`, `calculate_evm_metrics`)
- `HIGH` — modifies data with validation (e.g., `create_project`, `update_forecast`)
- `CRITICAL` — deletes data or bulk operations (e.g., `delete_cost_element`, `delete_users`)

### StateGraph Fallback

When subagents are disabled or no valid subagents after filtering, the system falls back to `graph.py:create_graph()`:

```
StateGraph(AgentState)
    entry_point → "agent"
    "agent" ──[has tool_calls]──→ "tools"
    "agent" ──[no tool_calls]──→ END
    "tools" ────────────────────→ "agent"  (loop back)

Max iterations: 5 (MAX_TOOL_ITERATIONS)

Returns: (compiled_graph, interrupt_node) tuple
```

Tool node selection:
- With context + websocket + session_id → `InterruptNode` (approval support)
- With context only → `RBACToolNode` (permission checks)
- No context → `ToolNode` (basic)

---

## 5. Decoupled Execution

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

### Core Components

#### AgentEventBus

File: `backend/app/ai/execution/agent_event_bus.py`

In-memory pub/sub event bus for a single agent execution. Features:

- **Bounded event log**: Fixed-size circular buffer (`collections.deque`, max 1000 events) retains recent events for replay
- **Subscriber queues**: Each subscriber gets its own `asyncio.Queue` for independent consumption
- **Replay support**: Late subscribers can replay events since a given sequence number
- **Completion tracking**: Marks bus as completed when terminal events (`complete`, `error`) are published

```python
# Create a bus for an execution
bus = AgentEventBus(execution_id="exec-123", max_log_size=1000)

# Subscribe to receive events
queue = bus.subscribe()

# Publish events (sequence numbers auto-assigned)
event = AgentEvent(event_type="token_batch", data={"tokens": "Hello"})
bus.publish(event)

# Replay events for reconnection
missed = bus.replay(since_sequence=50)
```

#### AgentRunnerManager

File: `backend/app/ai/execution/runner_manager.py`

Process-level singleton registry mapping execution IDs to event buses. Enables WebSocket handlers and REST endpoints to locate running executions.

```python
from app.ai.execution.runner_manager import runner_manager

# Create and register a bus
bus = runner_manager.create_bus("exec-123")

# Look up a running execution's bus
bus = runner_manager.get_bus("exec-123")
if bus:
    queue = bus.subscribe()

# Remove when execution completes
runner_manager.remove_bus("exec-123")
```

**Important**: This is an in-memory registry for single-server deployments. Executions are lost on server restart.

#### AIAgentExecution Model

File: `backend/app/models/domain/ai.py`

Database entity tracking agent executions with status lifecycle.

```python
class AIAgentExecution(SimpleEntityBase):
    session_id: UUID                    # FK to ai_conversation_sessions
    status: str                          # "pending" | "running" | "completed" | "error" | "awaiting_approval"
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    execution_mode: str                  # "safe" | "standard" | "expert"
    total_tokens: int = 0
    tool_calls_count: int = 0
```

Status lifecycle:
```
pending -> running -> [completed | error | awaiting_approval]
```

#### AIConversationSession.active_execution_id

File: `backend/app/models/domain/ai.py`

Optional field referencing the currently running agent execution. Used by frontend to auto-reconnect after network disruptions.

```python
active_execution_id: UUID | None  # Currently running or last execution
```

### AgentService._run_agent_graph()

File: `backend/app/ai/agent_service.py`

Decoupled variant of `chat_stream()` that publishes events to an `AgentEventBus` instead of sending WebSocket messages directly.

```python
async def _run_agent_graph(
    message: str,
    assistant_config: AIAssistantConfig,
    session_id: UUID,
    user_id: UUID,
    event_bus: AgentEventBus,  # Publish to this bus instead of WS
    project_id: UUID | None = None,
    ...
) -> None:
    # Build agent graph
    graph = await self._create_deep_agent_graph(...)

    # Stream events to bus
    async for event in graph.astream_events(...):
        await event_bus.publish(AgentEvent(
            event_type="token_batch",
            data={"tokens": "..."}
        ))
```

### AgentService.start_execution()

File: `backend/app/ai/agent_service.py`

Creates an independent agent execution with its own DB session and event bus. Runs as background task via `asyncio.create_task()`.

```python
execution_id = await agent_service.start_execution(
    message="Calculate EVM metrics",
    assistant_config=config,
    session_id=session_id,
    user_id=user_id,
    project_id=project_id,
)
```

Returns execution ID string. Execution status tracked in DB via `AIAgentExecution`.

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

File: `agent_service.py` (_consume_stream within chat_stream)

```python
async for event in graph.astream_events(
    {"messages": history, "tool_call_count": 0, "next": "agent"},
    config={"recursion_limit": recursion_limit, "configurable": {"thread_id": str(session_id)}},
    version="v1",
):
```

### Event Types

| LangGraph Event | WebSocket Message | Description |
|-----------------|-------------------|-------------|
| `on_chat_model_stream` | `WSTokenMessage` | Streaming token from LLM |
| `on_tool_start` (write_todos) | `WSPlanningMessage` | LangChain agent creating a plan |
| `on_tool_start` (task) | `WSSubagentMessage` | Delegating to subagent |
| `on_tool_start` (other) | `WSToolCallMessage` | Tool execution starting |
| `on_tool_end` (task) | `WSSubagentResultMessage` + `WSContentResetMessage` | Subagent completed |
| `on_tool_end` (other) | `WSToolResultMessage` | Tool execution result |
| `on_end` | `WSCompleteMessage` | Stream complete |
| `on_chat_model_stream` (batched) | `WSTokenBatchMessage` | Batched tokens via TokenBufferManager |
| `on_tool_end` (task) | `WSAgentCompleteMessage` | Subagent stream completed visually |
| `on_tool_end` (task) | `WSContentResetMessage` | Clear streaming buffer for new main agent bubble |

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

Handled inline in `agent_service.py:_consume_stream()` within the `on_tool_end` event handler.

When a subagent completes via the `task` tool:
1. Subagent content is extracted from the tool output (ToolMessage, Command, or dict)
2. Content is tracked in `subagent_messages_by_main_invocation` for ordered persistence
3. `WSSubagentResultMessage` is sent to the client (displayed in Activity Panel)
4. Subagent token buffer is flushed
5. `WSAgentCompleteMessage` is sent (completion indicator for UI)
6. `WSContentResetMessage` is sent to clear the streaming buffer
7. `accumulated_content` is NOT reset — main agent thoughts persist across subagent executions
8. A new `main_invocation_id` is generated for the next main agent bubble

Messages are persisted to DB in conversational order: main segment → subagents → next main segment.

### Token Buffering

File: `agent_service.py` (TokenBufferManager) and `token_buffer.py`

The stream uses a `TokenBufferManager` that batches individual LLM tokens before sending via WebSocket. Instead of one WS message per token, tokens are accumulated and flushed as `WSTokenBatchMessage` either:
- On buffer timeout (configurable interval)
- When buffer size exceeds threshold
- On explicit flush (before tool calls, on subagent transitions, on stream completion)

Configuration comes from `settings.AI_TOKEN_BUFFER_INTERVAL_MS`, `settings.AI_TOKEN_BUFFER_MAX_SIZE`, and `settings.AI_TOKEN_BUFFER_ENABLED`.

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
- **Max poll time**: 60 seconds (user has up to 60 seconds to approve)
- **Approval expiration**: 5 minutes (set in `InterruptNode`, safety net for stale approvals)
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

## 8. WebSocket Protocol Reference

### Client → Server Messages

#### Chat Request

```json
{
  "type": "chat",
  "message": "Calculate EVM metrics for project X",
  "session_id": null,
  "assistant_config_id": "a1b2c3d4-e89b-12d3-a456-426614174000",
  "title": "EVM Analysis",
  "project_id": "e5f6g7h8-e89b-12d3-a456-426614174000",
  "branch_id": null,
  "as_of": null,
  "branch_name": "main",
  "branch_mode": "merged",
  "execution_mode": "standard",
  "attachments": [],
  "images": []
}
```

#### Approval Response

```json
{
  "type": "approval_response",
  "approval_id": "550e8400-e29b-41d4-a716-446655440000",
  "approved": true,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-03-24T12:30:05Z"
}
```

#### Subscribe

```json
{
  "type": "subscribe",
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "last_seen_sequence": 42
}
```

Sent after WebSocket reconnection to resume receiving events from a running execution. The server replays all events with sequence number > `last_seen_sequence`, then subscribes to live events until completion.

### Server → Client Messages

#### Thinking

```json
{"type": "thinking"}
```

#### Token Stream

```json
{
  "type": "token",
  "content": "Based on the project data,",
  "session_id": "a1b2c3d4-e89b-12d3-a456-426614174000",
  "source": "main",
  "subagent_name": null
}
```

Subagent token:

```json
{
  "type": "token",
  "content": "The CPI for this project is",
  "session_id": "a1b2c3d4-e89b-12d3-a456-426614174000",
  "source": "subagent",
  "subagent_name": "evm_analyst"
}
```

#### Planning

```json
{
  "type": "planning",
  "plan": "Calculate EVM metrics for project X",
  "steps": [
    {"text": "Retrieve project data", "done": true},
    {"text": "Calculate CPI and SPI", "done": false},
    {"text": "Analyze variance trends", "done": false}
  ],
  "step_number": 1,
  "total_steps": 3
}
```

#### Tool Call

```json
{
  "type": "tool_call",
  "tool": "get_project",
  "args": {"project_id": "e5f6g7h8-..."},
  "step_number": 1,
  "total_steps": 3
}
```

#### Tool Result

```json
{
  "type": "tool_result",
  "tool": "get_project",
  "result": {
    "name": "Assembly Line A",
    "status": "ACT",
    "budget": 500000
  }
}
```

#### Subagent Delegation

```json
{
  "type": "subagent",
  "subagent": "evm_analyst",
  "message": "Calculating EVM metrics for project X",
  "step_number": 2,
  "total_steps": 3
}
```

#### Subagent Result

```json
{
  "type": "subagent_result",
  "subagent_name": "evm_analyst",
  "content": "## EVM Analysis Results\n\n**CPI:** 0.95\n**SPI:** 1.02\n..."
}
```

#### Content Reset

```json
{
  "type": "content_reset",
  "reason": "subagent_completed"
}
```

#### Agent Complete

```json
{
  "type": "agent_complete",
  "agent_type": "main",
  "invocation_id": "a1b2c3d4-...",
  "agent_name": "Assistant",
  "completed_at": "2026-03-24T12:30:15Z"
}
```

#### Token Batch

```json
{
  "type": "token_batch",
  "tokens": "Based on the project data, the CPI",
  "session_id": "a1b2c3d4-e89b-12d3-a456-426614174000",
  "source": "main",
  "subagent_name": null,
  "invocation_id": "a1b2c3d4-..."
}
```

#### Approval Request

```json
{
  "type": "approval_request",
  "approval_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "a1b2c3d4-e89b-12d3-a456-426614174000",
  "tool_name": "create_project",
  "tool_args": {"name": "New Project", "budget": 100000},
  "risk_level": "high",
  "expires_at": "2026-03-24T12:35:00Z"
}
```

#### Polling Heartbeat

```json
{
  "type": "polling_heartbeat",
  "approval_id": "550e8400-e29b-41d4-a716-446655440000",
  "elapsed_seconds": 5.0,
  "remaining_seconds": 295.0
}
```

#### Complete

```json
{
  "type": "complete",
  "session_id": "a1b2c3d4-e89b-12d3-a456-426614174000",
  "message_id": "b2c3d4e5-f90a-12d3-a456-426614174000"
}
```

#### Error

```json
{
  "type": "error",
  "message": "Session not found: a1b2c3d4-...",
  "code": 404
}
```

#### Execution Started

```json
{
  "type": "execution_started",
  "execution_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Sent immediately after an agent execution is created via REST endpoint or WebSocket. Provides the execution ID for tracking and reconnection.

#### Execution Status

```json
{
  "type": "execution_status",
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "awaiting_approval",
  "started_at": "2026-03-29T12:30:00Z",
  "total_tokens": 450,
  "tool_calls_count": 3
}
```

Sent when an agent execution changes status. Useful for tracking execution lifecycle without polling.

### Message Sequence: Full Conversation with Subagent + Approval

```
Client                                Server
  |                                     |
  |--- WSChatRequest (new session) ---->|
  |                                     |
  |<-- WSThinkingMessage ---------------|
  |<-- WSPlanningMessage ---------------|  (write_todos detected)
  |                                     |
  |<-- WSSubagentMessage (evm_analyst) -|  (task tool detected)
  |<-- WSTokenMessage (subagent) ------|  (subagent streams)
  |<-- WSTokenMessage (subagent) ------|
  |<-- WSSubagentResultMessage --------|  (subagent done)
  |<-- WSContentResetMessage ----------|  (clear buffer)
  |                                     |
  |<-- WSSubagentMessage (forecast_mgr)|  (second subagent)
  |<-- WSApprovalRequestMessage -------|  (HIGH risk tool!)
  |<-- WSPollingHeartbeatMessage ------|
  |--- WSApprovalResponse (approved) ->|
  |<-- WSToolResultMessage ------------|  (tool executed)
  |<-- WSSubagentResultMessage --------|  (subagent done)
  |<-- WSContentResetMessage ----------|
  |                                     |
  |<-- WSTokenMessage (main agent) ----|  (synthesis)
  |<-- WSTokenMessage (main agent) ----|
  |<-- WSCompleteMessage --------------|
```

---

## 9. Security Model

### Three-Tier Security

```
Tier 1: JWT Authentication
    ↓ (ai_chat.py - before websocket.accept)
Tier 2: RBAC Permission Checking (per-tool)
    ↓ (BackcastSecurityMiddleware._check_tool_permission)
Tier 3: Risk-Based Execution Modes
    ↓ (filter_tools_by_execution_mode + approval workflow)
```

### Execution Modes

| Mode | LOW (read) | HIGH (write) | CRITICAL (delete) | Approval? |
|------|------------|--------------|-------------------|-----------|
| `safe` | yes | no | no | N/A (tools not available) |
| `standard` | yes | yes (approval) | no (blocked by middleware) | Yes, for HIGH only |
| `expert` | yes | yes | yes | No |

### Temporal Context Injection

Temporal parameters are injected at the **middleware level**, not in the prompt. This is a security measure — the LLM cannot override them via prompt injection.

File: `middleware/temporal_context.py:40-93`

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

## 10. Troubleshooting Guide

### Log Markers

Search `backend/logs/app.log` for these markers to trace request flow:

| Log Marker | Location | What It Tells You |
|------------|----------|-------------------|
| `WebSocket chat connection established for user` | `ai_chat.py` | Connection accepted (auth passed) |
| `[AGENT_CREATION_START]` | `deep_agent_orchestrator.py` | Agent creation starting |
| `[TOOL_FILTERING]` | `deep_agent_orchestrator.py` | How many tools were filtered by execution mode |
| `Creating agent with subagents -` | `deep_agent_orchestrator.py` | Subagent mode active |
| `Compiled subagent '...' with N tools` | `deep_agent_orchestrator.py` | Subagent tool counts |
| `Agent created successfully` | `deep_agent_orchestrator.py` | Agent ready to use |
| `[CHAT_STREAM_ENTRY]` | `agent_service.py` | Chat stream starting |
| `[CHAT_STREAM_COMPLETE]` | `agent_service.py` | Chat stream finished |
| `on_chat_model_stream` | `agent_service.py` | Token streaming |
| `on_tool_start` | `agent_service.py` | Tool call beginning |
| `on_tool_end` | `agent_service.py` | Tool call complete |
| `APPROVAL_REQUEST_SENT:` | `interrupt_node.py` | Approval request sent to client |
| `[APPROVAL_GRANTED]` | `backcast_security.py` | User approved the tool |
| `[APPROVAL_TIMEOUT]` | `backcast_security.py` | Approval polling timed out (60s) |
| `[SUBAGENT_DELEGATION]` | `agent_service.py` | Subagent task started |
| `[GRAPH_CACHE_HIT]` | `agent_service.py` | Cached graph reused (fast path) |
| `[GRAPH_CREATION_START]` | `agent_service.py` | Compiling new graph (cache miss) |
| `[GRAPH_CREATION_COMPLETE]` | `agent_service.py` | Graph compilation finished with duration_ms |
| `CompiledGraphCache hit/miss` | `graph_cache.py` | LRU cache lookup result |
| `LLMClientCache hit/miss` | `graph_cache.py` | LLM client cache lookup result |

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
1. `assistant_config.allowed_tools` whitelist — tool must be listed
2. `execution_mode` — tool risk level must be compatible
3. Subagent mode — main agent has NO direct tools; it must delegate

#### Approval request never arrives at client

**Cause**: WebSocket disconnect during polling. The heartbeat mechanism (every 5s) should prevent this, but proxy timeouts can still occur. Check reverse proxy WebSocket timeout settings.

#### Subagent returns no results

**Cause**: Subagent has no valid tools after filtering. Check logs for `"has no valid tools after filtering - skipping"`.

#### Database session errors after tool execution

**Cause**: Unhandled exception in a tool left the DB session in a bad state. The system performs automatic rollback on tool errors (`agent_service.py:1016-1026`), but if you see cascading errors, check the tool implementation.

### Tracing a Request

1. **Find the session ID** from the frontend or from the initial `WSChatRequest`
2. **Search logs** for the session ID: `grep "<session_id>" backend/logs/app.log`
3. **Follow the markers**:
   - `[CHAT_STREAM_ENTRY]` → `[GRAPH_CACHE_HIT]` or `[GRAPH_CREATION_START]` → `[AGENT_CREATION_START]`
   - → `[TOOL_FILTERING]` → `Agent created successfully` (only on cache miss)
   - → `on_tool_start` → `[SUBAGENT_DELEGATION]` or `[APPROVAL_*]`
   - → `on_tool_end` → `on_chat_model_stream` → `[CHAT_STREAM_COMPLETE]`
4. **Check OpenTelemetry** if Jaeger is running (OTLP endpoint at `localhost:4317`)

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

-- Active assistant configs
SELECT id, name, model_id, is_active,
       array_length(allowed_tools, 1) as tool_count
FROM ai_assistant_configs
WHERE is_active = true;

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

### Telemetry Setup

For distributed tracing with Jaeger:

```bash
# Set environment variables
export OTLP_ENDPOINT=http://localhost:4317
export OTEL_CONSOLE_EXPORT=true  # Also log spans to console

# Ensure Jaeger is running
docker run -d --name jaeger \
  -p 4317:4317 \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest

# View traces at http://localhost:16686
```

---

## 11. Key Files Quick Reference

### Core

| File | Purpose |
|------|---------|
| `backend/app/api/routes/ai_chat.py` | WebSocket endpoint (`/stream`), REST endpoints (`/invoke`, `/executions/*`), auth, message dispatch, subscribe handling |
| `backend/app/ai/agent_service.py` | Main orchestration: `chat_stream()`, `chat()`, `_run_agent_graph()`, `start_execution()`, approval registration, history building |
| `backend/app/ai/deep_agent_orchestrator.py` | `DeepAgentOrchestrator.create_agent()` — wraps `langchain.agents.create_agent()` with Backcast config |
| `backend/app/ai/graph_cache.py` | Caching infrastructure: `LLMClientCache`, `CompiledGraphCache`, `GraphCacheKey`, `BackcastRuntimeContext`, shared checkpointer, ContextVar helpers |
| `backend/app/ai/graph.py` | `create_graph()` — StateGraph fallback (no subagents) |
| `backend/app/ai/state.py` | `AgentState` TypedDict (messages, tool_call_count, next) |

### Execution Architecture

| File | Purpose |
|------|---------|
| `backend/app/ai/execution/agent_event.py` | `AgentEvent` dataclass — immutable event structure for agent execution events |
| `backend/app/ai/execution/agent_event_bus.py` | `AgentEventBus` — in-memory pub/sub with bounded replay buffer for agent events |
| `backend/app/ai/execution/runner_manager.py` | `AgentRunnerManager` — process-level singleton registry mapping execution IDs to event buses |
| `backend/app/alembic/versions/6c93c299c703_add_ai_agent_executions_table.py` | Migration creating `ai_agent_executions` table for execution tracking |
| `backend/app/main.py` | Startup handler `_cleanup_orphaned_executions()` — marks orphaned executions as errored on server restart |

### Subagents

| File | Purpose |
|------|---------|
| `backend/app/ai/subagents/__init__.py` | 6 subagent configs: name, description, system_prompt, allowed_tools |

### Tools

| File | Purpose |
|------|---------|
| `backend/app/ai/tools/__init__.py` | `create_project_tools()` factory, `filter_tools_by_execution_mode()` |
| `backend/app/ai/tools/types.py` | `ToolContext`, `ToolMetadata`, `RiskLevel`, `ExecutionMode` |
| `backend/app/ai/tools/decorator.py` | `@ai_tool` decorator for tool registration with metadata |
| `backend/app/ai/tools/interrupt_node.py` | `InterruptNode` — approval request/response via WebSocket |
| `backend/app/ai/tools/rbac_tool_node.py` | `RBACToolNode` — permission-aware tool node (StateGraph path) |
| `backend/app/ai/tools/subagent_task.py` | `build_task_tool()`, `TASK_SYSTEM_PROMPT` — task tool for subagent delegation |
| `backend/app/ai/tools/session_manager.py` | `ToolSessionManager` — task-local DB sessions for concurrent tool execution |
| `backend/app/ai/tools/approval_audit.py` | Approval audit trail logging |
| `backend/app/ai/tools/risk_check_node.py` | Standalone risk checking node |
| `backend/app/ai/tools/project_tools.py` | Project and WBE tools |
| `backend/app/ai/tools/context_tools.py` | `get_temporal_context`, `get_project_context` |
| `backend/app/ai/tools/temporal_tools.py` | Temporal/bitemporal query tools |
| `backend/app/ai/tools/templates/` | Tool template modules (CRUD, EVM, change orders, forecasts, etc.) |

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
| `backend/app/models/schemas/ai.py` | All Pydantic schemas: `WSChatRequest`, `WSTokenMessage`, `WSApprovalRequestMessage`, `WSSubscribeMessage`, `WSExecutionStartedMessage`, `WSExecutionStatusMessage`, `AgentExecutionPublic`, `InvokeAgentRequest`, etc. |
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
