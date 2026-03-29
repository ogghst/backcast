# Analysis: Decouple AI Agent Execution from WebSocket

**Created:** 2026-03-29
**Request:** Make agent task execution independent of the WebSocket connection lifecycle, enabling REST invocation, reconnection to running agents, and persistent execution tracking.

---

## Clarified Requirements

### Functional Requirements

1. **Agent execution survives WS disconnect** -- When a WebSocket connection drops, the running LangGraph agent continues executing to completion. Agent execution runs in an independent asyncio task, not tied to the WS handler lifecycle.
2. **REST API invocation** -- Agent can be invoked via a POST endpoint (e.g., `POST /api/v1/ai/chat/sessions/{id}/invoke`), not only through the WebSocket. This enables programmatic/CLI access and integration testing.
3. **Execution status tracking** -- A new "agent execution" concept is introduced with status lifecycle: `pending`, `running`, `completed`, `error`, `awaiting_approval`. Status is queryable via REST (`GET /api/v1/ai/executions/{id}/status`).
4. **Session-to-execution relationship** -- An `AIConversationSession` references the currently active execution (if any). The session list UI can show which sessions have running agents.
5. **WS reconnection to running agent** -- When a user reconnects to a session that has a running agent, the WebSocket subscribes to the ongoing execution's event stream and receives live progress (tokens, tool calls, approvals).
6. **Message persistence regardless of WS state** -- Assistant messages are persisted to the database even if no WebSocket is connected. Currently, persistence already happens post-stream but is guarded by WS connectivity checks that abort the stream early.

### Non-Functional Requirements

- **Latency**: Event delivery to WS should remain at current latency levels (sub-100ms for token batches)
- **Reliability**: Agent execution must complete even if no client is connected
- **Memory**: Bounded event log for replay should not grow unbounded (cap at reasonable size, e.g., last 1000 events)
- **Concurrency**: System must handle multiple concurrent executions per server process
- **Observability**: Existing OpenTelemetry tracing must continue working across the decoupled boundary

### Constraints

- **No external message broker** -- Redis/RabbitMQ are not in the stack. In-memory pub/sub only (single-server deployment model)
- **No database polling for real-time events** -- WebSocket streaming must remain push-based, not poll-based
- **Backward compatibility** -- Existing WebSocket protocol must continue working during migration
- **Approval flow must survive** -- Human-in-the-loop approval must work both via WS reconnection and REST endpoint
- **EVCS alignment** -- New database entities use `SimpleEntityBase` pattern (AI entities are non-versioned)

---

## Context Discovery

### Product Scope

- No existing user stories directly address agent resilience or REST invocation. The AI chat system was built as a real-time WebSocket feature.
- The functional requirements document focuses on EVM/budget management. The AI chat is an enhancement, not a core domain requirement.

### Architecture Context

**Bounded contexts involved:**
- **AI Chat Context** -- The primary context being modified. Contains agent orchestration, tools, middleware, streaming.
- **Authentication & Authorization** -- REST endpoints need JWT auth; approval via REST needs identity verification.

**Existing patterns to follow:**
- `SimpleEntityBase` for new database models (non-versioned entities, see `AIConversationSession` pattern)
- Layered architecture: API route -> Service -> Repository for new REST endpoints
- Pydantic schemas in `app/models/schemas/ai.py` for request/response validation
- ContextVar bridge for per-request context in cached graphs (established in `graph_cache.py`)

**Architectural constraints:**
- Single-process deployment (no distributed coordination needed)
- All AI entities use `SimpleEntityBase` (no EVCS bitemporal tracking needed for execution status)
- Existing graph caching (`CompiledGraphCache`, `LLMClientCache`) must continue working

### Codebase Analysis

**Backend coupling points (quantified):**

| File | Coupling | Count | Risk |
|------|----------|-------|------|
| `agent_service.py` | `_is_websocket_connected()` checks | 17 | High -- each one aborts the stream if WS is disconnected |
| `interrupt_node.py` | `_is_websocket_connected()` checks | 3 | High -- approval requests silently dropped if WS disconnected |
| `ai_chat.py` (route) | `websocket` param threaded into `agent_service.chat_stream()` | 1 | High -- WS lifecycle owns the task |
| `ai_chat.py` (finally block) | Cancels ALL background tasks on disconnect | 1 | Critical -- kills running agent on WS close |

**Key insight**: The coupling is pervasive but follows a consistent pattern. Every streaming message send is guarded by `_is_websocket_connected()`, and the WS disconnect handler in `ai_chat.py` cancels all tasks. This means the architectural change requires:
1. Replacing the direct `websocket.send_json()` calls with an event publication mechanism
2. Preventing task cancellation on WS disconnect
3. Providing a mechanism for new WS connections to subscribe to ongoing event streams

**Current `AIConversationSession` model** (`backend/app/models/domain/ai.py`):
- Fields: `id`, `user_id`, `assistant_config_id`, `title`, `project_id`, `branch_id`, `created_at`, `updated_at`
- No `status` field, no execution tracking

**Current `InterruptNode`** (`backend/app/ai/tools/interrupt_node.py`):
- Takes `websocket: WebSocket` in constructor (line 92)
- Uses `websocket.send_json()` for approval requests and heartbeats
- Approval responses come through `register_approval_response()` which updates an in-memory dict

**Frontend** (`frontend/src/features/ai/chat/api/useStreamingChat.ts`):
- Manages WS lifecycle with reconnection (max 5 attempts, exponential backoff)
- On reconnect, creates a brand new WS connection -- no concept of "subscribing to running execution"
- Session list has no "running" indicator
- All streaming state (tokens, tool calls) is lost on disconnect

---

## Solution Options

### Option 1: In-Memory Event Bus with AgentRunner Registry (Full Decoupling)

**Architecture & Design:**

Introduces three new abstractions between the agent execution and the WebSocket:

1. **`AgentEventBus`** (in-memory, per-execution) -- An asyncio-based pub/sub channel. The agent publishes events (tokens, tool calls, approvals, completion). Subscribers (WS handler, REST SSE handler) come and go. Maintains a bounded circular buffer for replay to late subscribers.

2. **`AgentRunner`** -- Owns the graph execution asyncio task. Publishes to its event bus. Survives WS disconnect. Reports status to the `AIAgentExecution` DB record.

3. **`AgentRunnerManager`** (singleton registry) -- Tracks all running `AgentRunner` instances by execution_id. Used by WS/REST handlers to find and subscribe to running executions.

New database entity: `AIAgentExecution`
- `id`, `session_id` (FK to sessions), `status` (enum: pending/running/completed/error/awaiting_approval), `started_at`, `completed_at`, `error_message`, `execution_metadata` (JSONB)

Modified components:
- `InterruptNode` -- Takes `AgentEventBus` instead of `WebSocket`. Approval requests are published as events. Approval responses are registered via a method (same as current, no WS needed).
- `TokenBufferManager` -- Flush callback publishes to event bus instead of sending to WS.
- `_consume_stream()` in `agent_service.py` -- Replaces `websocket.send_json()` with `event_bus.publish()`. Removes all `_is_websocket_connected()` checks.
- `ai_chat.py` -- On new WS connection, checks if session has a running execution. If yes, subscribes to its event bus and replays buffered events. If no, creates a new execution via `AgentRunnerManager`.

New API endpoints:
- `POST /api/v1/ai/chat/sessions/{id}/invoke` -- Start agent execution (returns execution_id)
- `GET /api/v1/ai/executions/{id}` -- Get execution status
- `POST /api/v1/ai/executions/{id}/approve` -- Submit approval response via REST

WS protocol extension:
- New client message: `{ type: "subscribe", execution_id: "uuid" }` -- Reconnect to running execution

**UX Design:**
- Session list shows a "running" indicator for sessions with active executions
- When user opens a session with a running agent, frontend auto-subscribes and shows live progress
- Approval dialog appears normally regardless of whether it came via WS reconnection or REST

**Implementation:**

Key files to create:
- `backend/app/ai/execution/agent_event_bus.py` -- EventBus with subscriber management and bounded replay buffer
- `backend/app/ai/execution/agent_runner.py` -- Runner that wraps graph execution and publishes events
- `backend/app/ai/execution/runner_manager.py` -- Singleton registry for tracking runners
- `backend/app/models/domain/ai.py` -- Add `AIAgentExecution` model
- `backend/app/models/schemas/ai.py` -- Add execution-related schemas
- Alembic migration for new table

Key files to modify:
- `backend/app/ai/agent_service.py` -- Replace WS sends with event bus publishes, remove WS dependency
- `backend/app/ai/tools/interrupt_node.py` -- Accept event bus instead of WS
- `backend/app/ai/token_buffer.py` -- Publish to event bus
- `backend/app/api/routes/ai_chat.py` -- Add subscribe logic, prevent task cancellation on disconnect
- `frontend/src/features/ai/chat/api/useStreamingChat.ts` -- Add subscribe message on reconnect
- `frontend/src/features/ai/chat/types.ts` -- Add subscribe message types

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Complete decoupling; agent survives disconnect; REST invocation; proper execution status tracking; bounded replay enables late subscription |
| Cons            | Significant refactoring of agent_service.py (17 WS checks to replace); new database table; in-memory state is lost on server restart (running agents would be orphaned); increased complexity |
| Complexity      | High |
| Maintainability | Good -- clean separation of concerns; event bus pattern is well-understood |
| Performance     | Negligible overhead -- asyncio queue operations are sub-microsecond; bounded buffer is memory-efficient |

---

### Option 2: Minimal Decoupling -- Cancel Guard + DB-Persisted Progress

**Architecture & Design:**

A lighter approach that avoids the full event bus pattern:

1. **Cancel Guard** -- Modify `ai_chat.py` to NOT cancel agent tasks on WS disconnect. Instead, let them run to completion. Agent continues publishing messages to DB.

2. **WS Reconnection via DB Replay** -- When a user reconnects, load messages created since disconnect from DB, then attach to the running asyncio task's output stream.

3. **Execution Status in Session** -- Add a `status` column to `AIConversationSession` instead of creating a new `AIAgentExecution` table. Simpler but couples execution state to the session.

Modified components:
- `ai_chat.py` -- Remove task cancellation from finally block. Track running tasks in a module-level dict.
- `agent_service.py` -- Replace `_is_websocket_connected()` checks with try/except (attempt send, ignore failure). Continue execution regardless.
- `AIConversationSession` -- Add `status` field (idle/running/error)
- `InterruptNode` -- Make WS optional. If WS is disconnected, approval request is persisted to DB and client polls for it.

No new API endpoints for invocation (keeps WS-only for now).

**UX Design:**
- Session list shows running indicator via session status field
- On reconnect, frontend loads missed messages from REST API, then attaches to live stream
- Approval flow falls back to polling if WS is disconnected during approval

**Implementation:**

Key files to modify:
- `backend/app/api/routes/ai_chat.py` -- Remove task cancellation, add running task registry
- `backend/app/ai/agent_service.py` -- Replace WS checks with try/except sends
- `backend/app/ai/tools/interrupt_node.py` -- Make WS optional
- `backend/app/models/domain/ai.py` -- Add status to AIConversationSession
- Alembic migration for status column

No new files needed.

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Minimal changes; no new abstractions; no new tables; fast to implement |
| Cons            | No REST invocation capability; reconnection relies on DB polling (not real-time for in-progress tokens); no execution-level status tracking; approval during disconnect requires DB polling; session model overloaded with execution state |
| Complexity      | Low |
| Maintainability | Fair -- WS dependency is "softened" but not cleanly removed; future work needed for REST invocation |
| Performance     | DB polling on reconnect adds latency; missed tokens during disconnect are not recoverable in real-time |

---

### Option 3: Hybrid -- Event Bus for Streaming + DB for Approval

**Architecture & Design:**

Combines elements of Options 1 and 2:

1. **AgentEventBus** for real-time event streaming (same as Option 1, but lighter)
2. **No AIAgentExecution table** -- Use session status field for tracking (same as Option 2)
3. **DB-persisted approvals** -- Approval requests are stored in a new `pending_approvals` table, not just in memory. Enables REST approval endpoints without the full execution model.

This avoids the full execution tracking model while still getting event bus benefits for streaming.

Modified components:
- Same event bus as Option 1 for streaming
- New `AIPendingApproval` table for approval persistence
- Session gets `status` field (no new execution table)
- `InterruptNode` publishes approval requests to both event bus and DB

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Real-time streaming works with event bus; approvals survive server restart; REST approval endpoint; no full execution model needed |
| Cons            | Split responsibility (event bus for streaming, DB for approvals) adds conceptual complexity; no execution-level tracking for observability; still requires significant agent_service.py refactoring |
| Complexity      | Medium |
| Maintainability | Fair -- two mechanisms for two concerns, but no unified execution concept |
| Performance     | Good -- event bus for streaming, DB only for approval persistence |

---

## Comparison Summary

| Criteria           | Option 1 (Full Event Bus)   | Option 2 (Minimal Guard)   | Option 3 (Hybrid)            |
| ------------------ | --------------------------- | -------------------------- | ---------------------------- |
| Development Effort | High (3-5 days)             | Low (1-2 days)             | Medium (2-3 days)            |
| UX Quality         | Excellent                   | Fair                       | Good                         |
| Flexibility        | Excellent (REST + WS + SSE) | Poor (WS only)             | Good (REST approval + WS)    |
| Best For           | Production-grade resilience | Quick fix for disconnects  | Balanced improvement         |
| Risk               | Moderate (new abstractions) | Low (minimal changes)      | Low-Moderate                 |
| Token Replay       | Yes (bounded buffer)        | No (DB only, after stream) | Yes (bounded buffer)         |
| REST Invocation    | Yes                         | No                         | Partial (approval only)      |
| Server Restart     | Running agents lost         | Running agents lost        | Approvals survive, agents lost |

---

## Recommendation

**I recommend Option 1 (Full Event Bus with AgentRunner Registry)** because:

1. **It solves the stated requirements completely.** Every requirement (REST invocation, reconnection, execution status, persistent messages) is addressed by the architecture.

2. **The coupling points are well-defined and mechanical to refactor.** The 17 `_is_websocket_connected()` checks in `agent_service.py` follow a consistent pattern -- each one wraps a `websocket.send_json()` call. Replacing these with `event_bus.publish()` is a systematic transformation, not an architectural gamble.

3. **The event bus pattern is the right abstraction.** It cleanly separates the producer (agent execution) from consumers (WebSocket handlers, future SSE handlers, test harnesses). This matches the project's layered architecture philosophy.

4. **The `AIAgentExecution` model provides observability** that the project will need as the AI chat matures. Being able to query execution status, see error details, and track duration is valuable for debugging and monitoring.

**Alternative consideration:** Choose Option 2 if the timeline is constrained to under 2 days and REST invocation is not immediately needed. Option 2 can be delivered incrementally, with Option 1 following in a subsequent iteration. However, this creates technical debt since the WS checks will need to be refactored again when moving to Option 1.

---

## Decision Questions

1. **Is REST invocation needed in the first iteration, or is WS reconnection the priority?** If REST is not urgent, Option 2 could serve as a stepping stone.

2. **What should happen to running agents on server restart?** All three options lose in-memory state on restart. Is this acceptable, or should the agent execution be designed to be resumable from a checkpoint? (LangGraph's `MemorySaver` checkpointer already persists state, but re-attaching a running asyncio task after restart is not feasible.)

3. **Should the bounded replay buffer also persist missed tokens to DB in real-time, or only at stream completion (current behavior)?** Real-time DB persistence would allow full message recovery after server restart but adds write overhead during streaming.

4. **What is the expected concurrency?** Is this a single-user or multi-user system? The in-memory event bus scales well for dozens of concurrent executions but is not suitable for distributed deployments. If horizontal scaling is planned, the event bus abstraction would need a Redis backing.

---

## References

- Architecture: `/home/nicola/dev/backcast/docs/02-architecture/ai-chat-developer-guide.md`
- Agent service (primary refactoring target): `/home/nicola/dev/backcast/backend/app/ai/agent_service.py`
- WS route (disconnect handler): `/home/nicola/dev/backcast/backend/app/api/routes/ai_chat.py`
- Interrupt node (approval coupling): `/home/nicola/dev/backcast/backend/app/ai/tools/interrupt_node.py`
- Security middleware (approval polling): `/home/nicola/dev/backcast/backend/app/ai/middleware/backcast_security.py`
- AI domain models: `/home/nicola/dev/backcast/backend/app/models/domain/ai.py`
- Frontend streaming hook: `/home/nicola/dev/backcast/frontend/src/features/ai/chat/api/useStreamingChat.ts`
- Graph caching (ContextVar bridge pattern): `/home/nicola/dev/backcast/backend/app/ai/graph_cache.py`
- Bounded contexts: `/home/nicola/dev/backcast/docs/02-architecture/01-bounded-contexts.md`
