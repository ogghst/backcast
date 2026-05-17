# Analysis: Disable Parallel Tool Execution in LangGraph AI Agent

**Created:** 2026-05-17
**Request:** Implement defense-in-depth to prevent parallel tool execution by the LangGraph AI agent, eliminating DB pool exhaustion, race conditions in revenue allocation validation, and 100+ lines of defensive diagnostic code.

---

## Clarified Requirements

### Functional Requirements

- The LLM must emit at most one tool call per turn (Option A: `parallel_tool_calls=False`)
- Even if the model emits multiple tool calls despite Option A, they must execute sequentially, not via `asyncio.gather` (Option B: sequential ToolNode)
- Both the supervisor graph path (`SupervisorOrchestrator` via `langchain_create_agent`) and the fallback graph path (`create_graph` in `graph.py`) must be covered
- All existing tool execution behavior must remain unchanged (tools still work, RBAC still enforced, risk checking still applies)
- Existing E2E tests must pass without modification

### Non-Functional Requirements

- Zero DB connection pool exhaustion under heavy load (max 30 connections for pool_size=10 + max_overflow=20)
- No revenue allocation race conditions (two concurrent `create_wbe` calls must not both pass validation)
- Reduced defensive code complexity (100+ lines of pool monitoring, detached object re-querying, session cleanup can be simplified in follow-up)
- Deterministic execution order (predictable for debugging and auditing)

### Constraints

- Must work with DeepSeek models via `ChatDeepSeek` (OpenAI-compatible API)
- Must not change the monkey-patch pattern at `agent_service.py:77-95` that strips `tool_choice`
- Must not break the `RBACToolNode` or `InterruptNode` subclasses of `ToolNode`
- Must work with the `langchain_create_agent` factory (supervisor path) and the manual `StateGraph` (fallback path)
- LangGraph's `ToolNode._afunc` at line 854 uses `asyncio.gather(*coros)` -- this is the dispatch point that must be overridden

---

## Context Discovery

### Architecture Context

- **Bounded contexts involved:** AI Agent system (backend), Database session management
- **Existing patterns to follow:** Middleware pattern for `langchain_create_agent`, monkey-patching for `ChatDeepSeek`, ToolNode subclassing (RBACToolNode, InterruptNode)
- **Architectural constraints:** Single-server deployment (no Redis), in-memory event bus, async_scoped_session with asyncio.current_task

### Codebase Analysis

**Backend - Key files and their roles:**

1. **`agent_service.py:77-95`** -- `_patched_bind_tools` strips `tool_choice` for DeepSeek but passes `**kwargs` through. The `parallel_tool_calls=False` from middleware flows through this correctly for the supervisor path.

2. **`agent_service.py:128` (in `create_agent_node` via `graph.py:128`)** -- The fallback graph path calls `llm.bind_tools(tools)` WITHOUT `parallel_tool_calls=False`. This is a gap.

3. **`supervisor_orchestrator.py:316-325`** -- Uses `langchain_create_agent` with `build_backcast_middleware` which includes `SequentialToolCallsMiddleware`. The supervisor path already has Option A.

4. **`middleware/sequential_tool_calls.py`** -- ALREADY EXISTS. Injects `parallel_tool_calls=False` via `model_settings`. Only applies to agents created via `langchain_create_agent`.

5. **`graph.py:128`** -- `create_agent_node` calls `llm.bind_tools(tools)` directly. No middleware, no `parallel_tool_calls=False`.

6. **`langgraph/prebuilt/tool_node.py:854`** -- `outputs = await asyncio.gather(*coros)` dispatches all tool calls concurrently. Both `RBACToolNode` and `InterruptNode` inherit from `ToolNode` and inherit this behavior.

7. **`tools/rbac_tool_node.py`** -- Subclasses `ToolNode` with `awrap_tool_call=self._awrap_tool_call` but does NOT override `_afunc`. Parallel dispatch still applies.

8. **`db/session.py:40-43`** -- `tool_scoped_session_factory = async_scoped_session(async_session_maker, scopefunc=asyncio.current_task)`. Each concurrent asyncio Task gets its own session/connection. Under parallel tool execution, N tool calls = N connections checked out simultaneously.

9. **`services/wbe.py:39-114`** -- `_validate_revenue_allocation` reads SUM of allocations then checks against contract_value. Under parallel execution, two `create_wbe` calls both read the same SUM, both pass validation, combined allocation exceeds contract. Classic TOCTOU race condition.

10. **`agent_service.py:1963`** -- `await db.close()` releases the connection back to pool before graph execution. After graph completes, must re-query because objects are detached. This workaround exists solely because parallel tool execution holds connections for the entire graph duration.

**Current state of Option A:**

- Supervisor graph: COVERED. `SequentialToolCallsMiddleware` is in the middleware stack.
- Fallback graph (create_graph): NOT COVERED. `create_agent_node` calls `bind_tools` without `parallel_tool_calls=False`.
- Non-DeepSeek models (ChatOpenAI): The middleware sets `parallel_tool_calls=False` in `model_settings` which flows to `bind_tools(**model_settings)`. ChatOpenAI's `bind_tools` accepts this parameter. COVERED.

**Current state of Option B:**

- NOT IMPLEMENTED anywhere. `ToolNode._afunc` always uses `asyncio.gather`.
- Both `RBACToolNode` and `InterruptNode` inherit parallel execution.

---

## Solution Options

### Option 1: Defense-in-Depth (Option A Gap Fix + Option B Sequential ToolNode)

**Architecture & Design:**

Two changes, each addressing a different layer:

**Layer 1 - Fix Option A gap in fallback graph:**
Add `parallel_tool_calls=False` to `create_agent_node` in `graph.py`. The fallback graph's `agent_node` calls `llm.bind_tools(tools)` directly -- pass `parallel_tool_calls=False` here. This mirrors what `SequentialToolCallsMiddleware` does for the supervisor path.

**Layer 2 - Implement Option B as a SequentialToolNode subclass:**
Create `SequentialToolNode` that overrides `_afunc` to execute tools sequentially (for-loop instead of asyncio.gather). Both `RBACToolNode` and `InterruptNode` should inherit from `SequentialToolNode` instead of `ToolNode`. This guarantees sequential execution even if the model ignores `parallel_tool_calls=False`.

**Implementation:**

- Modify `graph.py:128` to pass `parallel_tool_calls=False` in `bind_tools` call
- Create `app/ai/tools/sequential_tool_node.py` with a class that overrides `_afunc`
- Change `RBACToolNode` parent class from `ToolNode` to `SequentialToolNode`
- Change `InterruptNode` parent class from `ToolNode` to `SequentialToolNode`
- The `_afunc` override replaces `asyncio.gather(*coros)` with a sequential for loop
- Preserve all existing `_awrap_tool_call`, permission checking, risk checking, and interrupt behavior

**Trade-offs:**

| Aspect          | Assessment                                                                                                     |
| --------------- | -------------------------------------------------------------------------------------------------------------- |
| Pros            | Defense-in-depth: two independent safety layers; eliminates root cause (parallel calls) and symptom (gather)   |
| Cons            | Slightly slower when model genuinely emits multiple calls (sequential vs parallel); two files to maintain      |
| Complexity      | Low. _afunc override is ~10 lines; bind_tools change is 1 parameter                                            |
| Maintainability | Good. Clear single-responsibility; easy to verify both layers work independently                               |
| Performance     | Negligible impact. Tools rarely emit in parallel after Option A; sequential execution adds ~0ms per tool call  |

---

### Option 2: Option B Only (Sequential ToolNode, no parallel_tool_calls change)

**Architecture & Design:**

Rely solely on overriding `ToolNode._afunc` to execute tools sequentially. Do not change `parallel_tool_calls` settings. The model may still emit multiple tool calls, but they will always execute one at a time.

**Implementation:**

- Create `SequentialToolNode` as described in Option 1 Layer 2
- Change `RBACToolNode` and `InterruptNode` parent classes
- No changes to `graph.py` or middleware

**Trade-offs:**

| Aspect          | Assessment                                                                                                     |
| --------------- | -------------------------------------------------------------------------------------------------------------- |
| Pros            | Single change point; simpler; works regardless of model compliance with parallel_tool_calls                    |
| Cons            | Model still wastes API round-trips by emitting multiple tool calls; each wasted call incurs latency and tokens  |
| Complexity      | Low. Only one new file                                                                                         |
| Maintainability | Good. Single mechanism to understand                                                                           |
| Performance     | Moderate waste. Model may emit 2-3 parallel calls that get serialized anyway; extra LLM round-trip overhead    |

---

### Option 3: Option A Only (Fix parallel_tool_calls everywhere, keep parallel ToolNode)

**Architecture & Design:**

Fix the Option A gap in the fallback graph path. Do not implement Option B. Trust that `parallel_tool_calls=False` will prevent the model from emitting multiple tool calls.

**Implementation:**

- Modify `graph.py:128` to pass `parallel_tool_calls=False`
- No ToolNode changes

**Trade-offs:**

| Aspect          | Assessment                                                                                                     |
| --------------- | -------------------------------------------------------------------------------------------------------------- |
| Pros            | Minimal code change; fastest to implement; addresses the source directly                                       |
| Cons            | Single point of failure. Model non-compliance or API bugs could emit multiple calls; no safety net             |
| Complexity      | Low. One parameter change                                                                                      |
| Maintainability | Fair. Relies on external API behavior; if DeepSeek changes, protection vanishes silently                       |
| Performance     | Best. No overhead from sequential for-loop; model emits single calls                                           |

---

## Comparison Summary

| Criteria           | Option 1 (Defense-in-Depth) | Option 2 (Option B Only)  | Option 3 (Option A Only)  |
| ------------------ | --------------------------- | ------------------------- | ------------------------- |
| Development Effort | ~2-3 hours                  | ~1-2 hours                | ~0.5 hours                |
| Reliability        | Highest (two layers)        | High (runtime guarantee)  | Medium (API-dependent)    |
| Complexity         | Low                         | Low                       | Lowest                    |
| Performance        | Good                        | Moderate (wasted calls)   | Best                      |
| Best For           | Production safety           | Quick reliable fix        | Trusted environments      |

---

## Recommendation

**I recommend Option 1 (Defense-in-Depth) because:**

1. The current production system has already suffered DB pool exhaustion (31 leaked connections, specialist crashes). A single-layer fix risks recurrence.
2. The two layers are independent -- Option A fails silently (model ignores `parallel_tool_calls=False`), Option B catches it at runtime.
3. The existing `SequentialToolCallsMiddleware` already implements Option A for the supervisor path. Option 1 simply extends this to the fallback path and adds the runtime safety net.
4. Implementation effort is minimal (~10 lines of new code for the `_afunc` override, 1 parameter for `bind_tools`, 2 parent class changes).

**Alternative consideration:** Option 2 is acceptable if the goal is fastest possible fix. Option 3 is NOT recommended given the production incidents already observed.

---

## Decision Questions

1. Should the `SequentialToolNode` also be applied to the supervisor's internal agent (specialist subgraphs)? These are created via `langchain_create_agent` which uses `langchain.agents.factory` ToolNode internally, not Backcast's `RBACToolNode`. The `parallel_tool_calls=False` middleware already applies, but the `_afunc` safety net would not.

2. In the follow-up iteration, should we simplify the session management (remove `async_scoped_session`, remove `await db.close()` workaround, remove pool monitoring) immediately after this change, or in a separate iteration?

3. Should `SequentialToolNode` log a warning when it encounters multiple tool calls (indicating the model ignored `parallel_tool_calls=False`)?

---

## References

- `backend/app/ai/agent_service.py` -- bind_tools patch (lines 77-95), graph invocation, start_execution
- `backend/app/ai/graph.py` -- create_graph, create_agent_node (line 128)
- `backend/app/ai/tools/rbac_tool_node.py` -- RBACToolNode subclassing ToolNode
- `backend/app/ai/tools/interrupt_node.py` -- InterruptNode subclassing ToolNode
- `backend/app/ai/middleware/sequential_tool_calls.py` -- existing middleware (already in supervisor stack)
- `backend/app/ai/subagent_compiler.py` -- build_backcast_middleware (includes SequentialToolCallsMiddleware)
- `backend/app/ai/supervisor_orchestrator.py` -- supervisor graph creation
- `backend/app/db/session.py` -- tool_scoped_session_factory, pool monitoring
- `backend/app/ai/tools/session_manager.py` -- ToolSessionManager commit/rollback
- `backend/app/ai/tools/decorator.py` -- @ai_tool session lifecycle
- `backend/app/services/wbe.py` -- revenue allocation race condition (lines 39-114)
- `langgraph/prebuilt/tool_node.py` -- _afunc with asyncio.gather (line 854)
- `langchain_deepseek/chat_models.py` -- parallel_tool_calls parameter (line 379)
