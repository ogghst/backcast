# Technical Debt Register

**Last Updated:** 2026-04-26
**Total Open Items:** 5
**Total Estimated Effort:** ~6 days

---

This file tracks active technical debt items. For completed/closed debt, see [technical-debt-archive.md](./technical-debt-archive.md).

---

## High Severity (P0 - P1)

### [TD-084] Decompose `_run_agent_graph` Method

- **Source:** Code review `/simplify` pass on `backend/app/ai/agent_service.py`
- **Description:** `_run_agent_graph` is ~800 lines with deep nesting (try/try/try/except/finally), handling graph setup, event processing, error handling, token batching, and message persistence in a single method. The event processing loop contains 15+ state tracking variables that could be grouped into a dataclass.
- **Impact:** Hard to test, maintain, and reason about. Any change to streaming, persistence, or event handling risks regressions across all concerns.
- **Estimated Effort:** 2 days
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Extract into focused methods: `_init_execution_state()`, `_setup_graph()`, `_process_stream_events()`, `_cleanup_execution()`, `_persist_results()`. Group the 15+ tracking variables into an `ExecutionState` dataclass.

---

### [TD-085] Migrate `astream_events` from v1 to v2

- **Source:** LangGraph best practices review (Context7 docs)
- **Description:** `_run_agent_graph` uses `graph.astream_events(..., version="v1")`. LangGraph recommends `version="v2"` which changes the event format and provides cleaner stream modes (`updates`, `custom`, `messages`). The v1 API is legacy and may be deprecated. Migration requires updating all event type handling in the 400+ line event loop.
- **Impact:** Stuck on deprecated API; v2 offers `stream_mode=["updates", "custom"]` which could replace manual event bus publishing and simplify token streaming via `get_stream_writer()`.
- **Estimated Effort:** 2 days
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Migrate event loop to v2 format first (no behavior change), then evaluate replacing manual `_publish` / `_token_accumulator` with LangGraph's `get_stream_writer()` and `stream_mode=["updates", "custom", "messages"]`.

---

## Medium Severity (P2 - P3)

### [TD-016] Performance Optimization (Large Projects)

- **Source:** Hierarchical Nav ACT phase
- **Description:** `useWBEs` fetches full list. Needs pagination or server-side tree loading.
- **Impact:** Slow load times for large datasets
- **Estimated Effort:** 3 hours
- **Status:** ⏸️ Deferred (2026-04-23)
- **Owner:** Full Stack Developer

### [TD-086] Stringly-Typed Event Types and Tool Names

- **Source:** Code review `/simplify` pass on `backend/app/ai/agent_service.py`
- **Description:** Event types (`"thinking"`, `"tool_call"`, `"subagent"`, `"complete"`, etc.), tool names (`"task"`, `"write_todos"`), and execution statuses (`"running"`, `"completed"`, `"error"`) are raw strings scattered across `_run_agent_graph`. These are also referenced by the frontend, so changes must be coordinated. Hardcoded strings risk typos and make refactoring error-prone.
- **Impact:** No compile-time safety; renaming an event type requires finding all string literals across backend and frontend.
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Create `AgentEventType` and `ExecutionStatus` enums in backend. Export as constants that frontend can import via shared types or OpenAPI spec.

### [TD-087] Parameter Sprawl in Graph Creation Methods

- **Source:** Code review `/simplify` pass on `backend/app/ai/agent_service.py`
- **Description:** `_create_deep_agent_graph` takes 12 parameters and `_run_agent_graph` takes 13. Many are optional with complex interdependencies (e.g., `websocket` is only needed when `interrupt_node` is used). The parameter lists make callers hard to read and error-prone to extend.
- **Impact:** Adding new graph configuration (e.g., supervisor mode toggles, new middleware) requires modifying long parameter lists in multiple methods.
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Group parameters into TypedDicts/dataclasses: `GraphCreationConfig` (llm, tool_context, assistant_config), `GraphExecutionParams` (message, session_id, user_id, project_id, temporal params), `StreamConfig` (event_bus, execution_mode).

---

## Summary

| Priority | Count | Total Effort |
|----------|-------|--------------|
| High (P0-P1) | 2 | ~4 days |
| Medium (P2-P3) | 3 | ~1.5 days |
| Low (P4+) | 0 | 0 hours |
| **Total** | **5** | **~5.5 days** |

---

## Links

- [Technical Debt Archive](./technical-debt-archive.md) - Completed debt items (35 items)
- [Sprint Backlog](./sprint-backlog.md) - Current iteration
- [Product Backlog](./product-backlog.md) - All pending work
