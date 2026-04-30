# Analysis: Migrate Briefing State to Dict-Only Representation

**Created:** 2026-04-29
**Request:** Remove `briefing: str` from `BackcastSupervisorState` and regenerate markdown on-demand from `briefing_data` at read sites.

---

## Clarified Requirements

### Functional Requirements

- Remove `briefing: str` field from `BackcastSupervisorState` TypedDict
- Remove `briefing: str` field from `_BriefingSupervisorState` subgraph state
- Change all read sites from `state.get("briefing", ...)` to derive markdown from `state.get("briefing_data", {})` via `BriefingDocument.model_validate(data).to_markdown()`
- Change all write sites to return only `briefing_data` (not both fields)
- Update `WSBriefingMessage.briefing` field consumption in `agent_service.py` to render from `chain_output["briefing_data"]` instead of `chain_output["briefing"]`
- Update `briefing_compiler.py` functions to return only `(dict, bool)` instead of `(str, dict, bool)`
- Maintain backward compatibility: no crashes if a stale checkpoint somehow contains `briefing` without `briefing_data`

### Non-Functional Requirements

- No measurable performance regression: `to_markdown()` is O(n) string concatenation on a ~500-700 token document, called at most 3-5 times per execution
- Simpler API surface: one field to understand and maintain instead of two
- Reduced checkpoint storage: `MemorySaver` stores half the briefing data

### Constraints

- The checkpointer is `MemorySaver` (in-memory), and `delete_thread()` is called before each execution. No database migration needed for checkpoint state.
- `WSBriefingMessage.briefing: str` is consumed by the frontend `BriefingPanel` as a markdown string. The WebSocket message must still contain a rendered markdown string -- this is a serialization boundary, not an internal state field.
- `_BriefingSupervisorState` must keep a `briefing`-like field so the `get_briefing` tool's `InjectedState` can access the data within the supervisor subgraph.

---

## Context Discovery

### Product Scope

- Active iteration: `2026-04-27-briefing-room-orchestration`
- This is a **technical debt reduction** request, not a user-facing feature
- Related issue log: IL-12 (briefing state sharing fix) established the current dual-field pattern
- Related enhancement: 2026-04-29 briefing enhancement added `TaskAssignment`, structured fields to `BriefingSection`, and the `parse_structured_findings()` parser

### Architecture Context

- **Bounded contexts involved:** AI Assistant (backend only -- no frontend state changes needed)
- **Existing patterns:** `BriefingDocument` is a pure Pydantic model with no framework dependencies. `briefing_compiler.py` provides pure functions with no side effects. The pattern is clean separation between data model and rendering.
- **Architectural constraints:** LangGraph state sharing requires matching keys between parent state (`BackcastSupervisorState`) and subgraph state (`_BriefingSupervisorState`). If we remove `briefing` from the parent, the subgraph cannot access it via `InjectedState`.

### Codebase Analysis

**Complete inventory of read and write sites (corrected from the original request):**

**Read sites (5 total, not 2):**

1. `supervisor_orchestrator.py:143` -- `get_briefing` tool returns `state.get("briefing", ...)`
2. `supervisor_orchestrator.py:413` -- specialist wrapper reads `state.get("briefing", "")` for isolated messages
3. `agent_service.py:1042` -- `_run_agent_graph` reads `chain_output.get("briefing", "")` for `WSBriefingMessage` publishing

**Write sites (3 total, not 3 distinct call sites -- 4 locations):**

4. `supervisor_orchestrator.py:281-285` -- `initialize_briefing_node` returns both fields
5. `handoff_tools.py:113-123` -- handoff tool returns both in `Command.update`
6. `supervisor_orchestrator.py:461-471` -- specialist error path returns both
7. `supervisor_orchestrator.py:499-525` -- specialist success path returns both

**Infrastructure (2 files):**

8. `supervisor_state.py` -- `BackcastSupervisorState` TypedDict defines `briefing: str` and `briefing_data: dict[str, Any]`
9. `supervisor_orchestrator.py:116-126` -- `_BriefingSupervisorState` subgraph state defines `briefing: str`

**Compiler (2 functions):**

10. `briefing_compiler.py:21-29` -- `initialize_briefing()` returns `(markdown, dict, bool)`
11. `briefing_compiler.py:32-66` -- `compile_specialist_output()` returns `(markdown, dict, bool)`

**Frontend (read-only consumer):**

12. `BriefingPanel.tsx` -- receives `briefing.markdown` string from `WSBriefingMessage.briefing`
13. `useStreamingChat.ts` -- passes `serverMessage.briefing` string to `onBriefingUpdate` callback

**Key finding:** The original request missed read site #3 (`agent_service.py:1042`). This is the WebSocket event publishing site that sends the briefing markdown to the frontend. It reads from `chain_output["briefing"]` (the specialist wrapper's return dict), not from `state["briefing"]`. This is the most critical read site because it crosses the backend-to-frontend serialization boundary.

---

## Solution Options

### Option 1: Direct Removal -- Drop `briefing` from State, Regenerate at Read Sites

**Architecture & Design:**

Remove `briefing: str` from `BackcastSupervisorState` and `_BriefingSupervisorState`. At every read site, reconstruct the markdown by calling `BriefingDocument.model_validate(state["briefing_data"]).to_markdown()`. Change compiler functions to return `(dict, bool)` instead of `(str, dict, bool)`.

The `get_briefing` tool must change its approach: since `InjectedState` inside the supervisor subgraph will no longer see a `briefing` key, the tool needs to read `briefing_data` instead and render markdown on the spot.

**Implementation:**

Key changes:

1. **`supervisor_state.py`**: Remove `briefing: str` field
2. **`supervisor_orchestrator.py` line 116-126**: Change `_BriefingSupervisorState.briefing: str` to `briefing_data: dict[str, Any]` (or add a helper method)
3. **`supervisor_orchestrator.py` line 140-143**: `get_briefing` tool reads `briefing_data`, calls `BriefingDocument.model_validate(data).to_markdown()`
4. **`supervisor_orchestrator.py` line 281-285**: `initialize_briefing_node` returns only `briefing_data`
5. **`supervisor_orchestrator.py` line 413**: Specialist wrapper reads `briefing_data` and renders markdown for the isolated message
6. **`supervisor_orchestrator.py` lines 461-525**: Specialist success/error returns drop `briefing`, keep `briefing_data`
7. **`handoff_tools.py` lines 113-123**: Handoff tool drops `briefing` from `Command.update`
8. **`agent_service.py` lines 1037-1060**: Render markdown from `chain_output["briefing_data"]` instead of `chain_output["briefing"]`
9. **`briefing_compiler.py`**: `initialize_briefing()` returns `(dict, bool)`, `compile_specialist_output()` returns `(dict, bool)`

**Trade-offs:**

| Aspect          | Assessment                                                        |
| --------------- | ----------------------------------------------------------------- |
| Pros            | Eliminates redundancy completely. Single source of truth. Half the briefing storage in checkpointer. |
| Cons            | Every read site pays `model_validate()` + `to_markdown()` cost. Two of the three read sites already have the `BriefingDocument` in scope (specialist wrapper, agent_service). The `get_briefing` tool is called by the LLM potentially multiple times per turn. |
| Complexity      | Low -- straightforward removal with mechanical substitutions     |
| Maintainability | Good -- one field instead of two, no sync risk                    |
| Performance     | Negligible regression. `model_validate()` on a ~500-700 token dict is <1ms. `to_markdown()` is string concatenation. Called 3-5 times per execution. Total overhead: <5ms per execution. |

---

### Option 2: Computed Property -- Replace `briefing` with a Helper Function

**Architecture & Design:**

Remove `briefing: str` from `BackcastSupervisorState` but introduce a module-level helper function `render_briefing_markdown(state: dict) -> str` that encapsulates the `model_validate()` + `to_markdown()` pattern. This gives a named abstraction for the conversion and makes read sites a single function call.

Keep `briefing_compiler.py` functions returning `(dict, bool)` only. The helper handles the common "I have state, I need markdown" pattern.

**Implementation:**

1. Add `render_briefing_markdown(state: dict[str, Any]) -> str` to `briefing_compiler.py`
2. Same file changes as Option 1, but read sites call `render_briefing_markdown(state)` instead of inlining the two-step conversion
3. `agent_service.py` read site needs special handling since it reads from `chain_output` (specialist wrapper return dict), not from graph state

**Trade-offs:**

| Aspect          | Assessment                                                        |
| --------------- | ----------------------------------------------------------------- |
| Pros            | Named abstraction for the conversion. Read sites are cleaner. Centralizes error handling for malformed `briefing_data`. |
| Cons            | Adds a thin wrapper that may obscure the actual operation. The `agent_service.py` site operates on a different dict shape (specialist return) than graph state, so the helper must accept generic dicts. |
| Complexity      | Low-Med -- same mechanical changes plus one new helper function  |
| Maintainability | Good -- clear named operation, but one more function to maintain  |
| Performance     | Identical to Option 1                                            |

---

### Option 3: Keep Dict-Only in State, Add Markdown to Specialist Return Dicts Only

**Architecture & Design:**

Remove `briefing: str` from `BackcastSupervisorState` and `_BriefingSupervisorState`. Keep `briefing_compiler.py` functions returning `(str, dict, bool)` -- but only use the markdown string in the specialist wrapper's return dict (which is not persisted by the checkpointer, only passed as a transient `on_chain_end` event output to `agent_service.py`).

The `get_briefing` tool and specialist wrapper both render markdown from `briefing_data` on demand. But the specialist wrapper includes a computed `briefing` key in its return dict for backward compatibility with `agent_service.py`'s event listener. This return dict is ephemeral -- not part of graph state.

**Implementation:**

1. Same state schema changes as Option 1
2. `briefing_compiler.py` keeps current return signature `(str, dict, bool)` -- no API change
3. Specialist wrapper returns both `"briefing": markdown` and `"briefing_data": dict` in its return dict (but only `"briefing_data"` goes into state updates)
4. `agent_service.py` continues to read `chain_output["briefing"]` -- no change needed there
5. `get_briefing` tool and specialist message construction render from `briefing_data`

**Trade-offs:**

| Aspect          | Assessment                                                        |
| --------------- | ----------------------------------------------------------------- |
| Pros            | Minimal change to `agent_service.py` (the most complex file). No change to compiler function signatures. Frontend contract preserved without any change. |
| Cons            | Specialist wrapper still returns both fields in its dict (ephemeral, not in state). The "dual representation" is not fully eliminated -- it moves from state to return values. |
| Complexity      | Low -- fewer total changes than Option 1                          |
| Maintainability | Fair -- the pattern is cleaner but the dual return in specialist wrapper is a subtle nuance that could confuse future developers |
| Performance     | Identical to Option 1 (same number of `to_markdown()` calls)     |

---

## Comparison Summary

| Criteria           | Option 1: Direct Removal | Option 2: Helper Function | Option 3: Ephemeral Markdown |
| ------------------ | ------------------------ | ------------------------- | ---------------------------- |
| Development Effort | S (2h)                   | S (2.5h)                  | S (1.5h)                     |
| Simplicity         | High                     | Medium                    | Medium                        |
| Flexibility        | Low (rigid)              | Medium (extensible)       | Low (backward-compat hack)   |
| Best For           | Maximum clarity, full cleanup | Future-proofed read pattern | Minimal diff, safe refactor  |

---

## Recommendation

**I recommend Option 1 (Direct Removal) because:**

1. It fully eliminates the redundancy -- there is exactly one source of truth for briefing data in graph state.
2. The performance cost is negligible (<5ms total per execution for 3-5 render calls).
3. The read sites are few and well-contained. The `model_validate() + to_markdown()` pattern is obvious and self-documenting.
4. It produces the smallest long-term maintenance surface.
5. The checkpointer is in-memory and threads are deleted before each execution, so there is zero backward compatibility risk with persisted state.

**Alternative consideration:** Option 3 is worth considering if you want to minimize the diff in `agent_service.py` (the most complex file in the AI module). It achieves the same state-level cleanup while keeping the `agent_service.py` event listener unchanged.

---

## Decisions

**Chosen: Option 1 (Direct Removal)** -- drop markdown entirely from state and compiler returns.

1. `get_briefing` tool renders markdown from `briefing_data` inline (no helper function).
2. `agent_service.py` renders markdown from `chain_output["briefing_data"]` directly -- no ephemeral `briefing` key in specialist wrapper return dicts.
3. `briefing_compiler.py` functions drop markdown from return tuples entirely: `(dict, bool)` instead of `(str, dict, bool)`.

---

## References

- `backend/app/ai/supervisor_state.py` -- state schema
- `backend/app/ai/supervisor_orchestrator.py` -- read/write sites, subgraph state
- `backend/app/ai/handoff_tools.py` -- write site (Command.update)
- `backend/app/ai/briefing_compiler.py` -- compiler functions
- `backend/app/ai/briefing.py` -- BriefingDocument model (to_markdown)
- `backend/app/ai/agent_service.py` -- WebSocket event publishing (read site)
- `backend/app/ai/graph_cache.py` -- MemorySaver checkpointer
- `backend/tests/ai/test_briefing.py` -- existing tests
- `docs/03-project-plan/iterations/2026-04-27-briefing-room-orchestration/issue-log.md` -- IL-12 context
