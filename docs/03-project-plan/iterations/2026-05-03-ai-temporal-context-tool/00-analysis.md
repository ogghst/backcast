# Analysis: AI Chat Temporal Context Tool

**Created:** 2026-05-03
**Request:** Add AI chat tools that allow the AI assistant to change temporal context (as_of date, branch, branch_mode) during a conversation. Currently these are managed frontend-side only.

---

## Clarified Requirements

The AI assistant should be able to change the user's temporal view context (as_of date, branch name, branch mode) during a conversation via a new backend tool, with changes propagating to the frontend Time Machine store through a WebSocket event.

### Functional Requirements

- FR-1: New `set_temporal_context` backend tool that accepts optional `as_of`, `branch_name`, and `branch_mode` parameters
- FR-2: Tool must validate branch existence against the database when `branch_name` is provided and a project context exists
- FR-3: Tool must update the shared `ToolContext` instance so subsequent tool calls in the same execution use the new temporal parameters
- FR-4: Tool must publish a `temporal_context_change` event via the `AgentEventBus` to notify the frontend
- FR-5: Frontend must receive the `temporal_context_change` WebSocket message and update the TimeMachine store
- FR-6: When no project context exists, the tool must inform the LLM that temporal context requires project scope (skip store update, skip branch validation)
- FR-7: Risk level: LOW (this is a view-context change, not data modification)

### Non-Functional Requirements

- NFR-1: Branch validation must query the database (BranchService.list_branches_as_of) to confirm the branch exists for the project
- NFR-2: Event propagation latency should be under 100ms (in-memory event bus, single-server deployment)
- NFR-3: Tool must be compatible with all execution modes (safe, standard, expert) since it is LOW risk
- NFR-4: No breaking changes to existing WS protocol or message types

### Constraints

- Single-server deployment (in-memory AgentEventBus, no Redis)
- ToolContext is a mutable dataclass shared across all tool calls in one execution
- Tools are cached singletons in `create_project_tools()` -- context is injected at runtime via context variables, not construction
- The TimeMachine store requires `currentProjectId` to be set before accepting updates
- Tool result is returned to the LLM; the WS event is a side-channel to the frontend

---

## Context Discovery

### Product Scope

- Temporal context (as_of, branch, branch_mode) is core to the EVCS bitemporal versioning system
- The Time Machine UI component currently owns temporal context selection exclusively
- This feature adds an AI-driven path for temporal context changes, enabling conversational time-travel

### Architecture Context

- **Bounded contexts involved:** AI Chat, EVCS Core (temporal queries)
- **Existing patterns to follow:**
  - `get_temporal_context` tool (read-only, LOW risk, no permissions)
  - `context_tools.py` pattern for read-only context tools
  - `AgentEventBus.publish()` + `forward_bus_events()` for WS event delivery
  - `WSServerMessage` discriminated union + type guards for frontend message handling
- **Architectural constraints:**
  - Tools access context via context variables (`get_context()`), not direct injection
  - The `@ai_tool` decorator wraps functions and retrieves context from `_current_context` ContextVar
  - Event bus is not currently accessible from within tool functions

### Codebase Analysis

**Backend:**

- `backend/app/ai/tools/types.py` -- `ToolContext` mutable dataclass with `as_of`, `branch_name`, `branch_mode` fields. No `_event_bus` field currently.
- `backend/app/ai/tools/temporal_tools.py` -- Existing `get_temporal_context` (read-only). This file is the natural home for `set_temporal_context`.
- `backend/app/ai/tools/decorator.py` -- `@ai_tool` decorator. Retrieves context via `get_context()` context variable. Wraps execution with session commit/rollback.
- `backend/app/ai/tools/__init__.py` -- `create_project_tools()` caches tool singletons. New tool must be registered here.
- `backend/app/ai/execution/agent_event_bus.py` -- `AgentEventBus.publish(AgentEvent)` with bounded log and subscriber fan-out.
- `backend/app/ai/execution/agent_event.py` -- `AgentEvent(event_type, data, timestamp, execution_id, sequence)`. Frozen dataclass.
- `backend/app/ai/agent_service.py` -- Creates `ToolContext` at line ~960, creates event bus, passes event bus to graph creation. Event bus is accessible in `_stream_agent_response` via closure (`_publish` helper), but NOT passed to individual tools.
- `backend/app/ai/middleware/backcast_security.py` -- `get_context()` returns ToolContext from ContextVar. `_current_context.set(ctx)` at line ~161.
- `backend/app/api/routes/ai_chat.py` -- `forward_bus_events()` at line ~58. Subscribes to bus, sends `{**event.data, "type": event.event_type}` as JSON to WebSocket.
- `backend/app/services/branch_service.py` -- `list_branches_as_of(project_id, as_of)` for branch validation.

**Frontend:**

- `frontend/src/features/ai/chat/types.ts` -- `WSServerMessage` discriminated union with ~20 message types. All have `type` field. Type guards defined for each.
- `frontend/src/features/ai/chat/api/useStreamingChat.ts` -- `handleMessage` routes all WS messages to callbacks. New message type needs routing.
- `frontend/src/features/ai/chat/components/ChatInterface.tsx` -- Wires streaming callbacks at line ~720. New callback needs wiring.
- `frontend/src/stores/useTimeMachineStore.ts` -- Zustand store with `selectTime()`, `selectBranch()`, `selectViewMode()`. All require `currentProjectId`.

---

## Solution Options

### Option 1: Add `_event_bus` to ToolContext (Proposed Plan)

**Architecture & Design:**

Add an optional `_event_bus: AgentEventBus | None` field to the `ToolContext` dataclass. The `set_temporal_context` tool accesses the bus through the context and publishes a `temporal_context_change` event. The event propagates through the existing `forward_bus_events()` pipeline to the frontend WebSocket.

**UX Design:**

User asks "Show me the project as of January 15" or "Switch to the BR-001 change order branch". The AI calls `set_temporal_context(as_of="2026-01-15")`, the Time Machine UI updates, and the AI confirms the change. The user sees the Time Machine component reflect the new temporal context.

**Implementation:**

1. Backend: Add `_event_bus: AgentEventBus | None = None` field to `ToolContext.__init__()` and dataclass
2. Backend: Pass `event_bus=event_bus` when constructing `ToolContext` in `agent_service.py` (~line 960)
3. Backend: Add `set_temporal_context` tool in `temporal_tools.py`:
   - Accept optional `as_of`, `branch_name`, `branch_mode` parameters
   - Validate branch via `BranchService.list_branches_as_of()` if `branch_name` provided and `project_id` set
   - Mutate `context.as_of`, `context.branch_name`, `context.branch_mode` directly (shared mutable reference)
   - Publish `AgentEvent(event_type="temporal_context_change", data={...})` via `context._event_bus`
   - Return confirmation with old and new values
4. Backend: Register tool in `__init__.py` `create_project_tools()`
5. Frontend: Add `WSTemporalContextChangeMessage` type and type guard in `types.ts`
6. Frontend: Add `onTemporalContextChange` callback to `UseStreamingChatConfig`, route in `handleMessage`
7. Frontend: Wire callback in `ChatInterface.tsx` to call `useTimeMachineStore` actions

**Trade-offs:**

| Aspect          | Assessment                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------ |
| Pros            | Minimal changes to existing architecture; ToolContext already mutable; event bus pipeline proven  |
| Cons            | Couples event bus into ToolContext (context now has infrastructure concern); tool singleton cannot be type-checked for event_bus at creation time |
| Complexity      | Low -- 7 files touched, each with small, focused changes                                        |
| Maintainability | Good -- follows existing patterns; no new infrastructure                                        |
| Performance     | Excellent -- in-memory mutation + in-memory event bus                                           |

---

### Option 2: Add Event Bus as Context Variable

**Architecture & Design:**

Instead of putting `_event_bus` on ToolContext, create a new `ContextVar[AgentEventBus | None]` in the middleware module. The `set_temporal_context` tool imports `get_event_bus()` and publishes directly. This keeps ToolContext as a pure domain object (session, user, temporal state) without infrastructure coupling.

**UX Design:**

Identical to Option 1.

**Implementation:**

1. Backend: Add `_current_event_bus: ContextVar[AgentEventBus | None]` to `backcast_security.py`
2. Backend: Add `get_event_bus()` and `set_request_context()` update to set the ContextVar alongside ToolContext
3. Backend: Set the ContextVar in `agent_service.py` when setting up tool context (~line 987)
4. Backend: Add `set_temporal_context` tool that calls `get_context()` for ToolContext AND `get_event_bus()` for bus
5. Backend: Register tool in `__init__.py`
6. Frontend: Same changes as Option 1 (steps 5-7)

**Trade-offs:**

| Aspect          | Assessment                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------ |
| Pros            | Clean separation -- ToolContext stays domain-only; follows existing ContextVar pattern            |
| Cons            | Two context variables to manage; tools need two imports; slightly more indirection                |
| Complexity      | Low-Med -- 8 files touched; new ContextVar lifecycle to manage                                   |
| Maintainability | Good -- better separation of concerns at cost of one more ContextVar                              |
| Performance     | Excellent -- same in-memory path                                                                  |

---

### Option 3: Tool Returns Event Data, Agent Service Publishes

**Architecture & Design:**

The tool mutates ToolContext and returns event data in its result dict with a sentinel key (e.g., `_emit_temporal_context_change`). The `@ai_tool` decorator or the agent execution loop detects this key and publishes the event on behalf of the tool. Tools never touch the event bus.

**UX Design:**

Identical to Option 1.

**Implementation:**

1. Backend: Add `set_temporal_context` tool that mutates ToolContext and returns `{"status": "ok", "_emit": {"event_type": "temporal_context_change", "data": {...}}}`
2. Backend: Modify `@ai_tool` decorator in `decorator.py` to check result for `_emit` key and publish via context variable
3. Backend: Add `_current_event_bus` ContextVar for the decorator to access
4. Backend: Set ContextVar in agent_service.py
5. Backend: Register tool in `__init__.py`
6. Frontend: Same changes as Option 1 (steps 5-7)

**Trade-offs:**

| Aspect          | Assessment                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------ |
| Pros            | Tools remain pure functions (mutate context + return data); decorator handles infrastructure; reusable pattern for future event-emitting tools |
| Cons            | Adds complexity to decorator; sentinel key is an implicit contract; more files changed            |
| Complexity      | Medium -- decorator modification is sensitive; more risk of regression                           |
| Maintainability | Fair -- implicit sentinel key contract is fragile; decorator is already complex                   |
| Performance     | Excellent -- same in-memory path                                                                  |

---

## Comparison Summary

| Criteria           | Option 1 (Field on ToolContext) | Option 2 (ContextVar)     | Option 3 (Decorator emit) |
| ------------------ | ------------------------------- | ------------------------- | ------------------------- |
| Development Effort | Small (7 files, ~120 lines)     | Small (8 files, ~140 lines)| Medium (8 files, ~180 lines)|
| Separation of Concerns | Fair (ToolContext gains infrastructure field) | Good (domain stays clean) | Good (tool is pure)       |
| Risk of Regression | Low                             | Low                       | Medium (decorator changes)|
| Future Extensibility | Fair (more fields on ToolContext) | Good (new ContextVars)  | Good (any tool can emit)  |
| Best For           | Quick, minimal change           | Clean architecture        | Reusable event pattern    |

---

## Recommendation

**I recommend Option 1 because:** it is the simplest approach with the fewest moving parts. The `_event_bus` field on ToolContext is a pragmatic compromise -- ToolContext is already an infrastructure-adjacent object (it holds AsyncSession, RBAC cache). Adding an optional event bus reference is consistent with its current design. The implementation is straightforward, touches the fewest critical paths, and the existing integration test file (`test_temporal_context_integration.py`) already has a placeholder test at line 234 (`test_temporal_context_changes_via_websocket`) that can be adapted.

**However, I flag one architectural concern:** ToolContext currently has no optional infrastructure fields. Adding `_event_bus` sets a precedent. If this pattern grows (e.g., tools need access to the WebSocket directly, or to a logger context), ToolContext could become a grab-bag. For this single feature, the pragmatic trade-off is acceptable. If a second infrastructure dependency is needed later, consider migrating to Option 2 at that point.

**Alternative consideration:** Choose Option 2 if you want to maintain strict domain purity in ToolContext from the start. The cost is one additional ContextVar to manage, which is minor.

---

## Key Risks and Edge Cases

### Risk 1: ToolContext Mutation Race Condition

ToolContext is mutable and shared across concurrent tool calls within a single execution. If the LLM calls `set_temporal_context` and another tool concurrently, the other tool may see a partially-updated context.

**Mitigation:** LangGraph executes tools sequentially within a single agent step by default. Concurrent tool execution only occurs when tools are explicitly bound with parallel invocation. The current codebase does not use parallel tool invocation. This risk is theoretical for now.

### Risk 2: Branch Validation Failure

If the LLM provides a branch name that does not exist for the project, the tool should return an error listing valid branches rather than silently falling back to "main".

**Mitigation:** The tool should call `BranchService.list_branches_as_of(project_id, as_of)` and check if the provided branch is in the result. If not, return an error with available branches so the LLM can self-correct.

### Risk 3: Frontend Store Without Project Context

The TimeMachine store requires `currentProjectId` to be set. If the user is in global chat (no project), the store update would silently fail.

**Mitigation:** The `onTemporalContextChange` callback should check `useTimeMachineStore.getState().currentProjectId` before calling store actions. If null, skip the update. The tool on the backend should also handle this case: if `context.project_id` is None, skip branch validation and inform the LLM that temporal context changes require a project scope.

### Risk 4: Event Bus is None

If `ToolContext._event_bus` is None (e.g., tool called outside of streaming execution context), the tool must not crash.

**Mitigation:** The tool should check `context._event_bus is not None` before publishing. If None, still mutate the context and return success, but note that no event was propagated.

### Risk 5: Tool Singleton Cache and Event Bus Lifetime

Tools are cached singletons in `create_project_tools()`. The event bus is per-execution. The event bus reference must be set on ToolContext (which is per-execution), not on the tool itself.

**Mitigation:** This is already the design -- the tool accesses context via `get_context()` ContextVar, which returns the per-execution ToolContext with its per-execution event bus reference. No conflict with the singleton cache.

---

## Decision Questions

1. **Should the tool accept all three parameters at once, or should each be a separate tool?** The proposed design uses one tool with optional params. Three tools would be more granular but adds LLM cognitive load for a simple context change. Do you agree with the combined approach?

2. **Should the tool reset unset parameters to defaults?** If the LLM calls `set_temporal_context(as_of="2026-01-15")` without specifying branch/mode, should branch and mode remain unchanged (current behavior) or reset to defaults ("main", "merged")? I recommend "remain unchanged" -- only mutate what is explicitly provided.

3. **Should the frontend show a visual indicator when AI changes temporal context?** The Time Machine UI already updates when the store changes. Should there be an additional toast notification or is the Time Machine update sufficient feedback?

4. **Option 1 vs Option 2 preference?** Do you accept the pragmatic `_event_bus` field on ToolContext (Option 1), or do you prefer the cleaner ContextVar separation (Option 2)?

---

## References

- `backend/app/ai/tools/types.py` -- ToolContext dataclass
- `backend/app/ai/tools/temporal_tools.py` -- Existing `get_temporal_context` tool
- `backend/app/ai/tools/__init__.py` -- Tool registration and caching
- `backend/app/ai/execution/agent_event_bus.py` -- Event bus pub/sub
- `backend/app/ai/agent_service.py` -- ToolContext creation (~line 960), event bus creation
- `backend/app/ai/middleware/backcast_security.py` -- Context variable management
- `backend/app/services/branch_service.py` -- Branch validation
- `backend/tests/integration/ai/test_temporal_context_integration.py` -- Existing integration tests
- `frontend/src/features/ai/chat/types.ts` -- WS message types
- `frontend/src/features/ai/chat/api/useStreamingChat.ts` -- WS message routing
- `frontend/src/stores/useTimeMachineStore.ts` -- TimeMachine Zustand store
