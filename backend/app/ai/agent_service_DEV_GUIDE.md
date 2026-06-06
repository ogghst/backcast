# Agent Service — Developer Guide

> **File:** `backend/app/ai/agent_service.py` (~2733 lines)
> **Purpose:** LangGraph agent orchestration — session management, graph compilation, stream processing, message persistence.

This guide maps the graph topology, control flow, exception paths, and calls out weak code for cleanup.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Graph Topology](#2-graph-topology)
3. [Execution Lifecycle](#3-execution-lifecycle)
4. [Stream Event Processing](#4-stream-event-processing)
5. [State Tracking (StreamState)](#5-state-tracking-streamstate)
6. [LLM Client & Caching](#6-llm-client--caching)
7. [Monkey-Patches](#7-monkey-patches)
8. [Approval / Interrupt Flow](#8-approval--interrupt-flow)
9. [Exception Flow](#9-exception-flow)
10. [Non-Standard Patterns & Improvement Points](#10-non-standard-patterns--improvement-points)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  Entry Points                                                       │
│  ┌─────────────┐    ┌──────────────────┐                            │
│  │  chat()     │    │  start_execution │  ← background runner       │
│  │  (sync)     │    │  (async/stream)  │                            │
│  └──────┬──────┘    └────────┬─────────┘                            │
│         │                    │                                       │
│         ▼                    ▼                                       │
│  ┌──────────────┐   ┌──────────────────┐                            │
│  │ _chat_impl   │   │ _run_agent_graph │  ← core orchestrator       │
│  └──────────────┘   └────────┬─────────┘                            │
│                              │                                       │
│           ┌──────────────────┼──────────────────┐                   │
│           ▼                  ▼                  ▼                   │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────────┐          │
│  │ _prepare_    │  │ _process_stream │  │ _persist_      │          │
│  │ graph_exec   │  │ _events         │  │ session_msgs   │          │
│  └──────────────┘  └─────────────────┘  └────────────────┘          │
└──────────────────────────────────────────────────────────────────────┘
```

**Two execution paths:**
- **`chat()`** (L607–863) — synchronous, uses `graph.ainvoke()`. Legacy path, simpler graph (`create_graph`).
- **`start_execution()`** (L1918–2115) — streaming, uses `graph.astream_events()`. Primary path, uses `SupervisorOrchestrator` graph with specialist delegation.

---

## 2. Graph Topology

### 2a. Simple Graph (`create_graph` — used by `chat()`)

```
START → agent ──has tool_calls?──→ tools ──→ agent (loop)
                │
                └── no tool_calls ──→ END
```

Defined in `app/ai/graph.py`. The `should_continue` router checks `tool_call_count < max_tool_iterations`.

### 2b. Supervisor Graph (`SupervisorOrchestrator` — used by `start_execution()`)

```
START → initialize_briefing → planner → supervisor ──handoff tool?──→ specialist_N
                   ▲                        │                              │
                   │                        │                     Command(goto=...)
                   │                        ▼                              │
                   │                        END (no handoff)              │
                   └──────────────────────────────────────────────────────┘
```

**Node definitions** (from `supervisor_orchestrator.py`):

| Node | Purpose |
|---|---|
| `initialize_briefing` | Seeds `briefing_data` state from user request |
| `planner` | LLM call → `PlanDocument` (assigns steps to specialists) |
| `supervisor` | Main agent with `handoff_to_{specialist}` tools |
| `specialist_*` | One node per specialist defined in DB. Each is a subgraph with its own LLM + tools |

**Routing:**
- `_make_supervisor_router()` checks if `AIMessage.tool_calls` contains a handoff tool → routes to the specialist node.
- Specialists return `Command(goto="supervisor")` or `Command(goto=END)`.
- When `requires_planning=True`, the supervisor iterates plan steps sequentially.

### 2c. Specialist Detection in Stream Processing

The set `_NON_SPECIALIST_NODES` (L270–280) is used to infer which graph nodes are specialists:

```python
_NON_SPECIALIST_NODES = frozenset({
    "__start__", "__end__", "agent",
    "initialize_briefing", "planner", "supervisor", "tools",
})
```

Any node name **not** in this set is treated as a specialist. This is brittle — see [§10](#10-non-standard-patterns--improvement-points).

---

## 3. Execution Lifecycle

### 3a. `start_execution()` (L1918–2115) — Step by Step

```
1. Create/reuse event_bus + execution_id
2. Open independent DB session (async_session_maker)
3. Create AIAgentExecution row (PK = execution_id)
4. Set session.active_execution_id
5. Release DB connection (db.close())  ← prevents pool hoarding
6. Call _run_agent_graph(GraphExecutionParams)
   ├── _prepare_graph_execution(params)
   │   ├── Build history + system prompt
   │   ├── Create LLM client (cached)
   │   ├── Create tools (role-filtered)
   │   ├── Compile supervisor graph
   │   └── Restore briefing from DB
   ├── StreamState initialization
   ├── Start periodic token flush task
   ├── _process_stream_events() ← main event loop
   ├── _persist_session_messages()
   └── _finalize_execution()
7. Update AIAgentExecution row with metrics
8. Clear active_execution_id on session
9. Cleanup: remove event_bus from runner_manager
```

### 3b. DB Connection Strategy

The `start_execution()` method deliberately **releases** the DB connection before entering the graph (L2020: `await db.close()`). The session object remains usable — it re-checkouts on next query. This prevents holding a pool connection for the full graph duration (minutes).

**⚠️ This causes detached SQLAlchemy objects.** All subsequent DB operations must re-query:
```python
# L2044–2048: re-query after db.close()
exec_stmt = select(AIAgentExecution).where(...)
exec_result = await db.execute(exec_stmt)
execution = exec_result.scalar_one()
```

---

## 4. Stream Event Processing

### 4a. Event Dispatch (`_process_stream_events`, L1537–1645)

The `astream_events()` loop yields LangGraph events. Each is dispatched by `event_type`:

| Event | Handler | Purpose |
|---|---|---|
| `on_chain_start` | `_handle_chain_start` (L1063) | Detect specialist entry, publish `AGENT_TRANSITION` |
| `on_chain_end` | `_handle_chain_end` (L1093) | Extract briefing, publish transition exit |
| `on_chat_model_start` | `_handle_chat_model_start` (L1167) | Track LLM call count/timing |
| `on_chat_model_stream` | `_handle_chat_model_stream` (L1187) | Accumulate tokens into buffer |
| `on_chat_model_end` | `_handle_chat_model_end` (L1236) | Capture token usage from API response |
| `on_tool_start` | `_handle_tool_start` (L1249) | Publish TOOL_CALL, detect task delegation |
| `on_tool_end` | `_handle_tool_end` (L1347) | Process results, publish TOOL_RESULT |
| `on_tool_error` | `_handle_tool_error` (L1475) | Record failure, clear subagent state |
| `on_end` | `_handle_graph_end` (L1513) | Extract final tool calls from output |

Events not in `_HANDLED_EVENTS` (L254–266) are skipped to reduce CPU overhead.

### 4b. Token Buffering

Tokens are NOT published individually. Instead:
1. `_handle_chat_model_stream` appends to `state.token_buffer[invocation_id]` (L1234)
2. A background task `_periodic_flush()` (L1845) flushes every `AI_TOKEN_BUFFER_INTERVAL_MS`
3. Tokens are flushed on specialist transitions, tool start, and stream end
4. Published as `"token_batch"` events (wire-level only, not in `AgentEventType`)

### 4c. Planner Token Suppression

When `planner` chain is active, `state.planner_active = True` (L1070). The `_handle_chat_model_stream` handler checks this flag and **returns early** (L1196–1197) to prevent plan JSON from leaking into the chat stream. Cleared in `_handle_chain_end` (L1164).

### 4d. Retry Logic (L1554–1644)

Transient stream errors trigger up to 2 retries with 2s delay:
```python
max_retries = 2
retry_delay = 2.0
```
`_is_transient_stream_error()` determines retryability. On retry, `token_buffer` is cleared and `events_processed` resets.

---

## 5. State Tracking (`StreamState`)

Defined in `graph_params.py` (L89–221). Key groupings:

| Category | Fields | Purpose |
|---|---|---|
| **Invocation tracking** | `main_invocation_id`, `current_invocation_id`, `current_subagent_name`, `last_entered_agent` | Correlate tokens/events to the right agent |
| **Content** | `main_agent_segments`, `token_buffer`, `subagent_messages`, `reasoning_content_value` | What the agents said |
| **Tools** | `all_tool_calls`, `all_tool_results`, `tool_calls_count` | Tool audit trail |
| **Planning** | `planner_active`, `current_step`, `estimated_total_steps` | Plan execution progress |
| **Persistence** | `briefing_persisted`, `last_persisted_message_id`, `graph_error` | DB write status |

**Invocation ID lifecycle:**
- `main_invocation_id` — created once at StreamState init, rotated after each `task` tool completion (L1410)
- `current_invocation_id` — created when entering a specialist or starting a `task` tool, cleared when specialist exits

---

## 6. LLM Client & Caching

Three cache layers (all module-level, shared across requests):

| Cache | Key | TTL | Location |
|---|---|---|---|
| `_llm_config_cache` | `model_id` | 300s | L286 |
| `_llm_cache` (LLMClientCache) | `(model, temp, tokens, base_url_hash, ...)` | None | L283 |
| `_user_role_cache` | `user_id` | 300s | L298 |

Invalidation: `invalidate_llm_config_cache()` (L290) clears both config and client caches.

**⚠️ Unbounded LLM instance cache:** `_llm_cache` has no TTL or size limit. Different `(model, temp, max_tokens, base_url)` tuples create new clients that are never evicted.

---

## 7. Monkey-Patches

Two patches applied at module load when DeepSeek is available:

### 7a. `reasoning_content` propagation (L48–69)
```python
_lc_openai_base._convert_message_to_dict = _patched_convert_message_to_dict
```
Patches LangChain's message serialization to include `reasoning_content` in `AIMessage` dicts. Required because langchain-deepseek receives but doesn't resend reasoning tokens.

### 7b. `bind_tools` tool_choice stripping (L73–93)
```python
ChatDeepSeek.bind_tools = _patched_bind_tools
```
DeepSeek-reasoner rejects `tool_choice` parameter. This patch strips it from all `bind_tools()` calls.

### 7c. Sequential tool execution (L170–171)
```python
if AI_SEQUENTIAL_TOOL_CALLS:
    patch_tool_node_for_sequential_execution()
```
Monkey-patches `ToolNode._afunc` globally to execute tool calls sequentially instead of in parallel. Defense against DB pool exhaustion.

**⚠️ All patches are global and irreversible.** They modify shared library classes at import time.

---

## 8. Approval / Interrupt Flow

For tools requiring human approval (e.g., destructive operations):

```
1. Tool execution hits InterruptNode
2. Graph pauses (LangGraph interrupt)
3. InterruptNode stored in _interrupt_nodes[session_id]
4. Frontend shows approval UI
5. User approves/rejects → register_approval_response()
6. resume_graph_after_approval() executes the tool
7. Result sent via WebSocket
```

**Storage:** Class variable `_interrupt_nodes` (L327) — shared across all `AgentService` instances. Max 20 entries with LRU eviction (L2588).

---

## 9. Exception Flow

### 9a. Stream Processing Errors

```
_process_stream_events
  ├── Transient error → retry (up to 2×)
  └── Non-transient or max retries exceeded
       ├── raise to _run_agent_graph
       ├── caught at L1858: state.graph_error = e
       ├── ERROR event published to event_bus
       └── finally block:
            ├── Cancel flush task
            ├── Flush remaining tokens
            ├── Clear request context
            ├── Unregister interrupt node
            ├── Commit tool session (ToolSessionManager.commit())
            └── Persist briefing (best-effort)
```

### 9b. Execution-Level Errors (start_execution)

```
Exception in start_execution()
  ├── Update AIAgentExecution row: status=ERROR, error_message=str(e)[:2000]
  ├── Clear active_execution_id on session
  ├── Publish EXECUTION_STATUS=ERROR to event_bus
  ├── Publish ERROR event to event_bus
  └── Re-raise
```

**⚠️ Error path re-queries DB** (L2063–2076) because `db.close()` at L2020 may have detached the execution object.

### 9c. Message Persistence Errors

`_persist_session_messages` (L1649) catches all exceptions, attempts `session.rollback()`, but **does not re-raise** — the error is logged and execution continues to `_finalize_execution`. This means the user sees a "completed" execution even if messages weren't saved.

---

## 10. Non-Standard Patterns & Improvement Points

### 🔴 Hardcoded Strings

| Location | Pattern | Risk |
|---|---|---|
| L258 `stream_chunk_timeout=300` | Hardcoded 5-minute timeout | Should be configurable |
| L1555 `max_retries = 2` | Hardcoded retry count | Should be configurable |
| L1556 `retry_delay = 2.0` | Hardcoded retry delay | Should be configurable |
| L287 `_LLM_CONFIG_TTL = 300` | Hardcoded 5-minute TTL | Not configurable |
| L299 `_USER_ROLE_TTL = 300` | Hardcoded 5-minute TTL | Not configurable |
| L2588 `_INTERRUPT_NODE_MAX = 20` | Hardcoded cap | Not configurable |
| L2570 `100_000` (100KB limit) | Magic number for JSON parse threshold | Not documented |

### 🔴 Global Mutable State

| Variable | Location | Issue |
|---|---|---|
| `_llm_config_cache` | L286 | Module-level dict, no size limit, no eviction |
| `_user_role_cache` | L298 | Module-level dict, no size limit |
| `_interrupt_nodes` | L327 (ClassVar) | Shared across instances, LRU eviction but unbounded between evictions |
| `_llm_cache` | L283 | No TTL — LLM instances live for process lifetime |

### 🟡 Specialist Detection via Set Difference

L270–280 + L1839–1842: Specialists are identified by taking the set difference of `graph.nodes` minus `_NON_SPECIALIST_NODES`. This is fragile — adding a new non-specialist node requires updating the frozenset.

```python
specialist_names=frozenset(
    n for n in ctx.graph.nodes if n not in _NON_SPECIALIST_NODES
),
```

**Improvement:** Nodes should declare their type (e.g., via metadata) rather than relying on set subtraction.

### 🟡 Duplicate Chain-End Logic

`_handle_chain_end` (L1093–1165) has three branches with overlapping concerns:
1. Specialist chain end (L1099)
2. Supervisor chain end (L1150)
3. Other non-specialist chain end (L1157)

Branches 2 and 3 both call `publish_briefing_update` with `"supervisor"` hardcoded as the chain_name even for non-supervisor nodes.

### 🟡 Commented-Out Documentation

L173–174: Comment says "No monkey-patches needed" but the file contains 3 active monkey-patches (L48–69, L73–93, L170–171):
```python
# NOTE: DeepSeek reasoning_content handling is now provided natively by
# langchain-deepseek package (ChatDeepSeek class). No monkey-patches needed.
```
This comment is misleading — the patches above it are still active.

### 🟡 `_resolve_context_names` Duplication

L2117–2270: Four near-identical branches for `project`, `wbe`, `cost_element`, `work_package`. Each branch repeats the same query pattern and parent project lookup. The `wbe`, `cost_element`, and `work_package` branches are copy-paste with only the model class and ID column name differing.

### 🟡 `_chat_impl` vs `_run_agent_graph` Divergence

The synchronous `chat()` → `_chat_impl()` path (L641–863) uses `create_graph()` directly and doesn't support specialists. The streaming `start_execution()` path uses `SupervisorOrchestrator`. These two paths share no code beyond LLM creation and history building. Bugs fixed in one path may not be fixed in the other.

### 🟡 `_handle_tool_start` Duplicate Branch

L1273–1305: The `TOOL_NAME_TASK` check appears twice — once at L1273 (sets tracking state) and again at L1308 (publishes event). These should be a single branch.

### 🟡 `_make_json_serializable` Recursive Parse

L2574–2581: Attempts `json.loads()` on any string starting with `{`, `[`, or `"`. This can unexpectedly deserialize tool output that happens to start with these characters. The 100KB guard at L2570 is a reasonable safety limit but the recursive JSON parsing is a hidden behavior.

### 🟡 f-string Logging

Multiple locations use f-strings in logging calls instead of lazy `%`-formatting:
- L559: `f"[GRAPH_COMPILE] Compiling new graph for session {session_id}"`
- L806: `f"Cleaned up task-local sessions..."`
- L1531: `f"Graph execution completed for execution event_bus {state.event_bus.execution_id}"`

This evaluates the f-string even when the log level is above the threshold.

### 🟢 Minor: Unreachable Code

L838: Comment "Note: Tool messages are not directly accessible from the result" followed by dead code in `_chat_impl` — the `tool_results` parameter is always `None`.

---

## Quick Reference: Key Line Numbers

| What | Lines |
|---|---|
| Module-level monkey-patches | 35–93 |
| `_HANDLED_EVENTS` filter set | 254–266 |
| `_NON_SPECIALIST_NODES` set | 270–280 |
| `AgentService.__init__` | 329–333 |
| `chat()` entry point | 607–639 |
| `_chat_impl()` sync execution | 641–863 |
| `_create_deep_agent_graph()` | 508–605 |
| `_prepare_graph_execution()` | 924–1059 |
| `_process_stream_events()` | 1537–1645 |
| `_run_agent_graph()` orchestrator | 1814–1900 |
| `start_execution()` background entry | 1918–2115 |
| `_persist_session_messages()` | 1649–1735 |
| `_finalize_execution()` | 1739–1810 |
| Interrupt node registry | 2588–2632 |
| Approval/resume flow | 2633–2732 |
