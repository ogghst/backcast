# Plan: Migrate from DeepAgents SDK to Bare LangGraph

**Created:** 2026-03-25
**Based on:** `00-analysis.md`
**Approved Option:** Option A -- Use `langchain.agents.create_agent()` directly

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option:** Option A -- Replace `from deepagents import create_deep_agent` with `from langchain.agents import create_agent`, assembling only the middleware Backcast needs.
- **Architecture:** Direct call to `langchain.agents.create_agent()` (the same runtime that `create_deep_agent()` wraps internally). Custom `task` tool built using `StructuredTool.from_function()` + `ToolRuntime` pattern. `TodoListMiddleware` imported directly from `langchain.agents.middleware`. Subagent prompt instructions included in the main agent's `system_prompt` rather than via a middleware `awrap_model_call` hook.
- **Key Decisions:**
  1. Keep `TodoListMiddleware` from `langchain.agents.middleware` (not reimplemented) -- `agent_service.py` detects `tool_name == "write_todos"` and reads `data.input["plan"]` and `data.input["steps"]`.
  2. Build a custom `task` tool (`subagent_task.py`) using the same `StructuredTool.from_function()` + `ToolRuntime` pattern the SDK uses, so subagent state access and `Command` return work identically.
  3. Include `TASK_SYSTEM_PROMPT` content (when-to-use / when-not-to-use guidance) in the main agent's `system_prompt` instead of injecting it via a middleware `awrap_model_call` hook. Backcast already appends delegation instructions at lines 161-167 of `deep_agent_orchestrator.py`.
  4. Subagents do NOT need `TodoListMiddleware` -- `agent_service.py` only detects `write_todos` on the main agent.
  5. Do NOT add a `general-purpose` subagent -- Backcast's 7 domain subagents are the complete set.
  6. `recursion_limit` handled by `agent_service.py` (per-invoke config overrides `.with_config()`), no need to set it on the graph.

### Success Criteria

**Functional Criteria:**

- [ ] FC-1: `from deepagents import create_deep_agent` is absent from the entire codebase VERIFIED BY: `grep -r "deepagents" backend/app/` returns zero results
- [ ] FC-2: Main agent graph is constructed via `langchain.agents.create_agent()` with `TodoListMiddleware` and Backcast middleware VERIFIED BY: unit test inspecting the returned `CompiledStateGraph`
- [ ] FC-3: Custom `task` tool invokes subagent via `ainvoke()` and returns `Command(update={"messages": [ToolMessage(...)]})` VERIFIED BY: unit test with mock subagent
- [ ] FC-4: Subagent tokens stream through parent's `astream_events(version="v1")` VERIFIED BY: integration test observing `on_chat_model_stream` events during subagent execution
- [ ] FC-5: `write_todos` tool produces the same event structure (`on_tool_start` with `data.input["plan"]` and `data.input["steps"]`) VERIFIED BY: integration test
- [ ] FC-6: `agent_service.py` event detection for `write_todos` and `task` tools works identically VERIFIED BY: existing integration tests pass unchanged
- [ ] FC-7: WebSocket message protocol is unchanged -- frontend requires zero code changes VERIFIED BY: manual E2E test against running server

**Technical Criteria:**

- [ ] TC-1: MyPy strict mode -- zero errors on modified files VERIFIED BY: `uv run mypy app/ai/deep_agent_orchestrator.py app/ai/tools/subagent_task.py`
- [ ] TC-2: Ruff -- zero errors on modified files VERIFIED BY: `uv run ruff check app/ai/deep_agent_orchestrator.py app/ai/tools/subagent_task.py`
- [ ] TC-3: `deepagents` removed from `pyproject.toml` dependencies VERIFIED BY: `grep "deepagents" backend/pyproject.toml` returns zero results
- [ ] TC-4: Both middleware classes (`TemporalContextMiddleware`, `BackcastSecurityMiddleware`) require zero code changes VERIFIED BY: `git diff` shows no changes to those files
- [ ] TC-5: Test coverage for new `subagent_task.py` is >= 80% VERIFIED BY: `uv run pytest --cov=app/ai/tools/subagent_task.py`

**Business Criteria:**

- [ ] BC-1: All existing tests pass (with updated imports only) VERIFIED BY: `uv run pytest backend/tests/ai/`
- [ ] BC-2: No behavioral regression in agent conversations VERIFIED BY: manual E2E test with a multi-subagent query

### Scope Boundaries

**In Scope:**

- Rewriting `deep_agent_orchestrator.py` to use `langchain.agents.create_agent()` directly
- Creating new `backend/app/ai/tools/subagent_task.py` with the custom `task` tool
- Updating test file imports and adding tests for the new `task` tool
- Removing `deepagents` from `pyproject.toml` dependencies
- Updating `pyproject.toml` MyPy overrides to remove `deepagents.*` entry
- Updating module docstrings to remove "Deep Agents SDK" references

**Out of Scope:**

- Changes to `agent_service.py` (consumes `astream_events` -- no change needed)
- Changes to `TemporalContextMiddleware` or `BackcastSecurityMiddleware` (same `AgentMiddleware` interface)
- Changes to WebSocket protocol or frontend components
- Changes to `app/ai/subagents/__init__.py` (plain dicts -- unchanged)
- Changes to `app/ai/token_buffer.py` (independent of agent construction)
- Adding new features, new middleware, or new subagents
- Implementing `Option B` (raw LangGraph StateGraph from scratch)
- Keeping `Option C` (partial `deepagents` dependency)

---

## Work Decomposition

### Task Breakdown

| #  | Task | Files | Dependencies | Success Criteria | Complexity |
| -- | ---- | ----- | ------------ | ---------------- | ---------- |
| 1 | Create `subagent_task.py` with `build_task_tool()` function | `backend/app/ai/tools/subagent_task.py` (new) | None | Module imports successfully; `build_task_tool()` accepts a dict of compiled runnables and returns a `StructuredTool` named `"task"` with `description` and `subagent_type` args | High |
| 2 | Rewrite `deep_agent_orchestrator.py` to use `langchain.agents.create_agent()` | `backend/app/ai/deep_agent_orchestrator.py` | Task 1 | Module imports successfully (no `deepagents` import); `create_agent()` method returns a `CompiledStateGraph`; subagent construction uses `create_agent()` with Backcast middleware only | High |
| 3 | Update `pyproject.toml` to remove `deepagents` dependency | `backend/pyproject.toml` | Task 2 | `grep "deepagents"` returns zero results; MyPy overrides entry removed; `uv sync` completes without error | Low |
| 4 | Update existing tests and add new tests for `subagent_task.py` | `backend/tests/ai/test_deep_agents_integration.py` | Task 2 | All existing tests pass with updated imports; new tests cover `build_task_tool()` happy path, invalid subagent_type, `Command` return, and `ToolRuntime` state access | Medium |
| 5 | Run full quality gate on modified scope | All modified files | Tasks 3-4 | `uv run ruff check` + `uv run mypy app/` + `uv run pytest backend/tests/ai/` all pass with zero errors | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| -------------------- | ------- | --------- | ----------------- |
| FC-1 (no deepagents import) | T-001 | `tests/ai/test_deep_agents_integration.py` | No test imports from `deepagents`; `grep -r "from deepagents" backend/app/` returns nothing |
| FC-2 (agent via create_agent) | T-002 | `tests/ai/test_deep_agents_integration.py` | `orchestrator.create_agent()` returns a `CompiledStateGraph` (inspect `type(result).__name__`) |
| FC-3 (task tool returns Command) | T-003 | `tests/ai/test_subagent_task.py` (new) | `build_task_tool()` with a mock subagent; calling the tool returns `Command` with `update.messages` containing a `ToolMessage` |
| FC-4 (subagent token streaming) | T-004 | `tests/ai/test_deep_agents_integration.py` | `astream_events(version="v1")` yields `on_chat_model_stream` events from subagent during `task` tool execution |
| FC-5 (write_todos event structure) | T-005 | `tests/ai/test_deep_agents_integration.py` | `on_tool_start` event for `write_todos` contains `data.input["plan"]` and `data.input["steps"]` |
| FC-6 (agent_service event detection) | T-006 | `tests/ai/test_deep_agents_integration.py` | Existing `_consume_stream` logic detects `task` and `write_todos` tool names correctly (regression guard) |
| FC-7 (WebSocket protocol unchanged) | T-007 | Manual E2E | WebSocket sends/receives `WSPlanningMessage`, `WSSubagentMessage`, `WSSubagentResultMessage` with same schema |
| TC-1/TC-2 (quality gate) | T-008 | CI | `uv run mypy` + `uv run ruff check` pass with zero errors |
| TC-5 (coverage) | T-009 | CI | `pytest --cov` for `subagent_task.py` >= 80% |

---

## Test Specification

### Test Hierarchy

```
backend/tests/ai/
  test_deep_agents_integration.py   (existing -- update imports, verify regression)
  test_subagent_task.py             (new -- unit tests for build_task_tool)
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Verification |
| ------- | --------- | --------- | ---- | ------------ |
| T-001 | `test_no_deepagents_imports_in_app_code` | FC-1 | Unit | `grep` for `deepagents` in `backend/app/` returns empty |
| T-002 | `test_orchestrator_creates_agent_via_langchain` | FC-2 | Unit | `orchestrator.create_agent()` returns non-None `CompiledStateGraph` |
| T-003 | `test_build_task_tool_returns_structured_tool` | FC-3 | Unit | `build_task_tool({"mock": mock_runnable})` returns `StructuredTool` with `name == "task"`, args include `description` and `subagent_type` |
| T-004 | `test_build_task_tool_invalid_subagent_returns_error_string` | FC-3 | Unit | Calling tool with `subagent_type="nonexistent"` returns error string (not `Command`) |
| T-005 | `test_build_task_tool_valid_invocation_returns_command` | FC-3 | Unit | Calling tool with valid subagent returns `Command` with `update["messages"]` containing `ToolMessage` |
| T-006 | `test_build_task_tool_async_invocation` | FC-3 | Unit | Async `atask` function calls `subagent.ainvoke()` and returns `Command` |
| T-007 | `test_build_task_tool_excludes_state_keys` | FC-3 | Unit | State passed to subagent excludes `messages`, `todos`, `structured_response` keys |
| T-008 | `test_write_todos_tool_present_in_main_agent` | FC-5 | Unit | Main agent's tool list includes a tool named `"write_todos"` (from `TodoListMiddleware`) |
| T-009 | `test_existing_middleware_tests_pass_unchanged` | BC-1 | Unit | All `test_backcast_security_middleware_*` and `test_temporal_context_middleware_*` tests pass without modification |
| T-010 | `test_subagent_dicts_built_correctly` | FC-2 | Unit | `_build_subagent_dicts()` produces dicts with `name`, `description`, `system_prompt`, `tools`, `middleware` keys; no `TodoListMiddleware` in subagent middleware stacks |

### Test Infrastructure Needs

- **Fixtures needed**: Existing `model_string`, `mock_session`, `tool_context` fixtures from `test_deep_agents_integration.py`
- **Mocks/stubs**: Mock `BaseChatModel` for subagent compilation tests (avoid real API calls); mock `Runnable` for `build_task_tool` unit tests
- **Database state**: None required (pure unit tests for this migration)

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --------- | ----------- | ----------- | ------ | ---------- |
| Technical | `Command` return from custom `task` tool may not be handled correctly by `create_agent()`'s `ToolNode` | Low | High | Test T-005 explicitly verifies `Command` return. The SDK's `_build_task_tool()` uses the identical pattern, and `create_agent()` is the same underlying factory. |
| Technical | Subagent token streaming may not propagate through parent's `astream_events` | Medium | High | Test T-004 verifies event propagation. The SDK uses `ainvoke()` inside the tool function and events still bubble up through LangGraph's event mechanism. Our implementation uses the same pattern. |
| Technical | `TodoListMiddleware` import path or API may differ between `deepagents` and `langchain.agents.middleware` | Low | Medium | The SDK imports `from langchain.agents.middleware import TodoListMiddleware` -- same path we will use. Verify by checking installed package. |
| Integration | `agent_service.py` `_consume_stream()` expects specific event data shapes for `task` tool completion (reads `data.get("output")` and handles `Command` type) | Low | Medium | The `_consume_stream` code at line 1023 already handles `Command` objects. Since we use the same `create_agent()` factory, event shapes are identical. |
| Regression | Middleware chaining order may produce different behavior | Low | Medium | `create_agent()` chains `awrap_tool_call` handlers in the order middleware is provided. We provide the same `[TemporalContextMiddleware, BackcastSecurityMiddleware]` order. |

---

## Prerequisites

### Technical

- [x] `langchain.agents.create_agent` is already installed (it is a dependency of `deepagents`)
- [x] `langchain.agents.middleware.TodoListMiddleware` is available for direct import
- [x] `langchain.tools.ToolRuntime` and `langchain_core.tools.StructuredTool` are available
- [ ] `deepagents` removal from `pyproject.toml` must happen last (after code changes are verified)

### Documentation

- [x] Analysis phase approved (`00-analysis.md` complete)
- [x] SDK source code reviewed (`deepagents/graph.py`, `deepagents/middleware/subagents.py`)
- [x] `agent_service.py` event handling reviewed (lines 790-1100)

---

## Code References

### Key SDK Implementation Details

These are the critical patterns from the SDK that must be replicated:

**1. Task tool signature (from `deepagents/middleware/subagents.py` lines 430-446):**
- Parameters: `description: str`, `subagent_type: str`, `runtime: ToolRuntime`
- Validates `subagent_type` against `subagent_graphs` dict
- Validates `runtime.tool_call_id` is present
- Prepares state by excluding `_EXCLUDED_STATE_KEYS` from `runtime.state`
- Invokes subagent via `subagent.ainvoke(subagent_state)`
- Returns `Command(update={"messages": [ToolMessage(...)]})`

**2. Excluded state keys (from `deepagents/middleware/subagents.py` line 127):**
```python
_EXCLUDED_STATE_KEYS = {"messages", "todos", "structured_response", "skills_metadata", "memory_contents"}
```

**3. Task tool description template (from `deepagents/middleware/subagents.py` lines 129-237):**
- Uses `{available_agents}` placeholder for subagent listing
- Contains usage notes and examples for when to use/not use the tool

**4. TASK_SYSTEM_PROMPT (from `deepagents/middleware/subagents.py` lines 239-265):**
- "When to use" and "when NOT to use" guidance for the task tool
- Must be appended to main agent's `system_prompt`

### Files That Must NOT Change

- `backend/app/ai/middleware/temporal_context.py` -- imports from `langchain.agents.middleware.types` (not deepagents)
- `backend/app/ai/middleware/backcast_security.py` -- imports from `langchain.agents.middleware.types` (not deepagents)
- `backend/app/ai/agent_service.py` -- consumes `astream_events(v1)`, no import from deepagents
- `backend/app/ai/subagents/__init__.py` -- plain dicts, no deepagents dependency
- `backend/app/ai/token_buffer.py` -- independent of agent construction
- `frontend/src/features/ai/chat/` -- WebSocket protocol unchanged

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Create subagent_task.py with build_task_tool() function"
    agent: pdca-backend-do-executor
    dependencies: []
    description: "Create new file backend/app/ai/tools/subagent_task.py implementing build_task_tool() that creates a StructuredTool named 'task' using StructuredTool.from_function() + ToolRuntime pattern. Must replicate SDK's _build_task_tool() behavior: accepts description + subagent_type + runtime params, validates subagent_type, invokes subagent via ainvoke(), returns Command(update=...). Include TASK_TOOL_DESCRIPTION template and TASK_SYSTEM_PROMPT constant."

  - id: BE-002
    name: "Rewrite deep_agent_orchestrator.py to use langchain.agents.create_agent()"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]
    description: "Replace 'from deepagents import create_deep_agent' with 'from langchain.agents import create_agent' and 'from langchain.agents.middleware import TodoListMiddleware'. Update create_agent() method to call create_agent() directly with: TodoListMiddleware + Backcast middleware stack, custom task tool from build_task_tool(), TASK_SYSTEM_PROMPT appended to system_prompt, subagent construction via create_agent() with Backcast middleware only (no TodoListMiddleware for subagents). Remove _build_context_schema() method (unused). Update module docstring."

  - id: BE-003
    name: "Remove deepagents from pyproject.toml and clean up MyPy overrides"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]
    description: "Remove 'deepagents>=0.4.0' from pyproject.toml dependencies. Remove 'deepagents.*' from mypy overrides module list. Run 'uv sync' to verify no broken dependencies."

  - id: BE-004
    name: "Update existing tests and add new subagent_task tests"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]
    group: tests
    kind: test
    description: "Update test_deep_agents_integration.py: remove any deepagents imports, update module docstring. Add test_subagent_task.py with unit tests: test_build_task_tool_returns_structured_tool, test_build_task_tool_invalid_subagent_returns_error_string, test_build_task_tool_valid_invocation_returns_command, test_build_task_tool_async_invocation, test_build_task_tool_excludes_state_keys. Update orchestrator tests to verify no deepagents import. Ensure all existing middleware tests pass unchanged."

  - id: BE-005
    name: "Run full quality gate on modified scope"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-004]
    group: tests
    kind: test
    description: "Run 'uv run ruff check' + 'uv run mypy app/' + 'uv run pytest backend/tests/ai/' on the modified scope. All must pass with zero errors. Verify coverage for subagent_task.py >= 80%."
```

---

## Documentation References

### Required Reading

- Analysis output: `docs/03-project-plan/iterations/2026-03-25-deepagents-to-langgraph-migration/00-analysis.md`
- SDK `create_deep_agent` implementation: `backend/.venv/lib/python3.12/site-packages/deepagents/graph.py`
- SDK `SubAgentMiddleware` and `_build_task_tool`: `backend/.venv/lib/python3.12/site-packages/deepagents/middleware/subagents.py`
- Backcast orchestrator: `backend/app/ai/deep_agent_orchestrator.py`
- Event handling in agent_service: `backend/app/ai/agent_service.py` (lines 790-1100)

### Code References

- Middleware pattern: `backend/app/ai/middleware/temporal_context.py` (shows `AgentMiddleware` usage)
- Security middleware: `backend/app/ai/middleware/backcast_security.py` (shows `awrap_tool_call` pattern)
- Existing test pattern: `backend/tests/ai/test_deep_agents_integration.py`
- Subagent configs: `backend/app/ai/subagents/__init__.py`
