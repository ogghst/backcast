# Plan: Defense-in-Depth Sequential Tool Execution

**Created:** 2026-05-17
**Based on:** [00-analysis.md](00-analysis.md)
**Approved Option:** Option 1 (Defense-in-Depth) + specialist subgraph coverage

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 (Defense-in-Depth) -- fix Option A gap + implement Option B as safety net + cover specialist subgraphs
- **Architecture**: Two-layer defense. Layer 1 (Option A): `parallel_tool_calls=False` in all `bind_tools` calls. Layer 2 (Option B): `SequentialToolNode` overrides `ToolNode._afunc` to execute tools sequentially instead of via `asyncio.gather`
- **Key Decisions**:
  1. Specialists (via `langchain_create_agent`) use a global monkey-patch of `ToolNode._afunc` since the factory hardcodes `ToolNode` instantiation
  2. Log WARNING when multiple tool calls arrive in a single batch (indicates model ignored `parallel_tool_calls=False`)
  3. Do NOT simplify session management in this iteration (follow-up)
  4. Both fallback graph paths AND specialist subgraphs must be covered

### Success Criteria

**Functional Criteria:**

- [ ] AC-F1: `SequentialToolNode._afunc` executes tool calls sequentially (for-loop), not concurrently (asyncio.gather) VERIFIED BY: unit test with mocked tools that track call order
- [ ] AC-F2: When multiple tool calls arrive in a single batch, a WARNING is logged listing the tool names VERIFIED BY: unit test capturing log output
- [ ] AC-F3: `RBACToolNode` still enforces permission checks before tool execution after parent class change VERIFIED BY: existing unit test `test_rbac_tool_node.py` passes unchanged
- [ ] AC-F4: `InterruptNode` still sends approval requests and waits for approval after parent class change VERIFIED BY: existing unit test `test_interrupt_node_approval.py` passes unchanged
- [ ] AC-F5: Fallback graph's `create_agent_node` passes `parallel_tool_calls=False` to `bind_tools` VERIFIED BY: unit test or code inspection
- [ ] AC-F6: Plain `ToolNode(tools)` path in `create_graph` also uses `SequentialToolNode` VERIFIED BY: code inspection showing no bare `ToolNode` instantiation in `graph.py`
- [ ] AC-F7: Specialist subgraphs created via `langchain_create_agent` use sequential execution VERIFIED BY: unit test confirming `_afunc` monkey-patch is active
- [ ] AC-F8: Single tool call execution performance is unchanged (no overhead in the common case) VERIFIED BY: benchmark comparison or code review showing only a for-loop over 1 item

**Technical Criteria:**

- [ ] AC-T1: MyPy strict mode passes with zero errors VERIFIED BY: `uv run mypy app/`
- [ ] AC-T2: Ruff lint passes with zero errors VERIFIED BY: `uv run ruff check . && uv run ruff format --check .`
- [ ] AC-T3: All existing E2E tests pass without modification VERIFIED BY: E2E test suite
- [ ] AC-T4: All existing unit/integration tests for RBAC, tools, and AI pass unchanged VERIFIED BY: `uv run pytest tests/unit/ai/ tests/integration/ai/ tests/security/ai/`

**TDD Criteria:**

- [ ] AC-D1: All tests for `SequentialToolNode` are written before implementation code
- [ ] AC-D2: Each test fails first (documented in DO phase log)
- [ ] AC-D3: Test coverage for new file `sequential_tool_node.py` >= 90%

### Scope Boundaries

**In Scope:**

- Create `SequentialToolNode` class in `backend/app/ai/tools/sequential_tool_node.py`
- Change `RBACToolNode` parent class from `ToolNode` to `SequentialToolNode`
- Change `InterruptNode` parent class from `ToolNode` to `SequentialToolNode`
- Replace bare `ToolNode(tools)` in `graph.py` with `SequentialToolNode(tools)`
- Add `parallel_tool_calls=False` to `create_agent_node`'s `bind_tools` call in `graph.py`
- Monkey-patch `ToolNode._afunc` at application startup to cover specialist subgraphs
- Unit tests for `SequentialToolNode`
- Unit test verifying the monkey-patch is applied correctly
- Warning log when multiple tool calls arrive in a batch

**Out of Scope:**

- Removing or simplifying `async_scoped_session`, `db.close()` workaround, or pool monitoring code (follow-up iteration)
- Modifying any existing `@ai_tool` decorated tool functions
- Changing the middleware chain or RBAC behavior
- Modifying `langchain_create_agent` or LangGraph library code
- Changing the DeepSeek `bind_tools` monkey-patch in `agent_service.py`

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                        | Files                                                                                         | Dependencies  | Success Criteria                                                                                           | Complexity |
| --- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------- | ---------- |
| 1   | Create `SequentialToolNode` class                           | `backend/app/ai/tools/sequential_tool_node.py` (NEW)                                          | None          | Class overrides `_afunc`; uses for-loop instead of `asyncio.gather`; logs WARNING on multiple tool calls   | Low        |
| 2   | Write unit tests for `SequentialToolNode`                   | `backend/tests/unit/ai/tools/test_sequential_tool_node.py` (NEW)                              | Task 1        | Tests cover: single call, multiple calls sequential, warning logged, preserves output format               | Medium     |
| 3   | Change `RBACToolNode` parent to `SequentialToolNode`        | `backend/app/ai/tools/rbac_tool_node.py`                                                      | Task 1        | Class inherits from `SequentialToolNode`; existing RBAC tests pass                                         | Low        |
| 4   | Change `InterruptNode` parent to `SequentialToolNode`       | `backend/app/ai/tools/interrupt_node.py`                                                      | Task 1        | Class inherits from `SequentialToolNode`; existing interrupt tests pass                                    | Low        |
| 5   | Fix fallback graph Option A gap + replace bare `ToolNode`   | `backend/app/ai/graph.py`                                                                     | Task 1        | `bind_tools` passes `parallel_tool_calls=False`; bare `ToolNode` replaced with `SequentialToolNode`        | Low        |
| 6   | Monkey-patch `ToolNode._afunc` for specialist subgraphs     | `backend/app/ai/tools/sequential_tool_node.py` (extend) + `backend/app/ai/agent_service.py`   | Task 1        | Patch applied at import/startup time; specialist ToolNode instances use sequential execution               | Medium     |
| 7   | Run full test verification                                   | All modified files + test suite                                                               | Tasks 2-6     | All unit, integration, security, E2E tests pass; mypy + ruff clean                                         | Low        |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File                                                | Expected Behavior                                                                               |
| -------------------- | ------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| AC-F1                | T-001   | `tests/unit/ai/tools/test_sequential_tool_node.py`       | SequentialToolNode executes 3 tool calls in order; no concurrent execution                      |
| AC-F2                | T-002   | `tests/unit/ai/tools/test_sequential_tool_node.py`       | WARNING logged with tool names when multiple calls arrive in one batch                          |
| AC-F3                | T-003   | `tests/unit/ai/tools/test_rbac_tool_node.py` (existing)  | Existing RBAC permission tests pass unchanged                                                   |
| AC-F4                | T-004   | `tests/ai/tools/test_interrupt_node_approval.py` (exist)  | Existing interrupt/approval tests pass unchanged                                                |
| AC-F5                | T-005   | `tests/unit/ai/tools/test_sequential_tool_node.py`       | Verify `create_agent_node` passes `parallel_tool_calls=False`                                   |
| AC-F6                | T-006   | Code inspection of `graph.py`                            | No bare `ToolNode` instantiation; all paths use `SequentialToolNode` or its subclasses          |
| AC-F7                | T-007   | `tests/unit/ai/tools/test_sequential_tool_node.py`       | After monkey-patch, a plain `ToolNode` instance executes tools sequentially                     |
| AC-F8                | T-008   | `tests/unit/ai/tools/test_sequential_tool_node.py`       | Single tool call performance unchanged; no unnecessary overhead                                 |
| AC-T1                | T-009   | CI pipeline                                              | `uv run mypy app/` passes with zero errors                                                      |
| AC-T2                | T-010   | CI pipeline                                              | `uv run ruff check . && uv run ruff format --check .` passes                                    |
| AC-T3                | T-011   | E2E test suite                                           | All E2E tests pass                                                                              |
| AC-T4                | T-012   | `uv run pytest`                                          | All unit/integration/security AI tests pass                                                     |

---

## Test Specification

### Test Hierarchy

```
tests/
  unit/
    ai/
      tools/
        test_sequential_tool_node.py    (NEW - core class tests)
        test_rbac_tool_node.py          (EXISTING - must pass unchanged)
  integration/
    ai/
      tools/
        test_concurrent_tool_execution.py  (EXISTING - must pass unchanged)
  ai/
    tools/
      test_interrupt_node_approval.py  (EXISTING - must pass unchanged)
```

### Test Cases (first 5)

| Test ID | Test Name                                                      | Criterion | Type   | Verification                                                                              |
| ------- | -------------------------------------------------------------- | --------- | ------ | ----------------------------------------------------------------------------------------- |
| T-001   | `test_sequential_tool_node_executes_tools_in_order`            | AC-F1     | Unit   | 3 tool calls dispatched; each completes before next starts; execution order matches input |
| T-002   | `test_sequential_tool_node_logs_warning_on_multiple_calls`     | AC-F2     | Unit   | 2+ tool calls in one batch; WARNING log contains tool names                               |
| T-003   | `test_sequential_tool_node_single_call_no_warning`             | AC-F2     | Unit   | 1 tool call; no WARNING logged                                                            |
| T-004   | `test_sequential_tool_node_preserves_tool_message_format`      | AC-F8     | Unit   | Output format matches standard ToolNode for single and multiple calls                     |
| T-005   | `test_tool_node_monkey_patch_applied`                          | AC-F7     | Unit   | After import, `ToolNode._afunc` is patched; plain `ToolNode` instance uses sequential     |

### Test Infrastructure Needs

- **Fixtures needed**: Mock `BaseTool` instances that track call order (existing pattern from `test_rbac_tool_node.py`)
- **Mocks/stubs**: `caplog` fixture for WARNING log assertion; `AsyncMock` for tool execution
- **Database state**: None required (unit tests only; integration/E2E use existing fixtures)

---

## Risk Assessment

| Risk Type   | Description                                                                                      | Probability | Impact | Mitigation                                                                                       |
| ----------- | ------------------------------------------------------------------------------------------------ | ----------- | ------ | ------------------------------------------------------------------------------------------------ |
| Technical   | `_afunc` signature changes in future LangGraph upgrade breaks `SequentialToolNode` override       | Low         | High   | Override is ~10 lines; re-deriving from upstream is trivial; pin LangGraph version               |
| Technical   | Monkey-patching `ToolNode._afunc` globally affects all ToolNode instances in the process         | Medium      | Low    | This is the desired behavior; all Backcast tool execution should be sequential                   |
| Integration | `InterruptNode` or `RBACToolNode` `_awrap_tool_call` breaks after parent class change             | Low         | High   | Both subclasses use `super().__init__` with same args; MRO resolves correctly; existing tests    |
| Technical   | `_afunc` override breaks if LangGraph passes different `Runtime` kwargs in future                | Low         | High   | Override passes all args through unchanged; only changes gather -> for-loop                       |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Create SequentialToolNode class with _afunc override"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Write unit tests for SequentialToolNode"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Change RBACToolNode parent class to SequentialToolNode"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-004
    name: "Change InterruptNode parent class to SequentialToolNode"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-005
    name: "Fix fallback graph: parallel_tool_calls=False + replace bare ToolNode"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-006
    name: "Monkey-patch ToolNode._afunc for specialist subgraphs"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-007
    name: "Run full test verification (unit + integration + mypy + ruff)"
    agent: pdca-backend-do-executor
    dependencies: [BE-002, BE-003, BE-004, BE-005, BE-006]
    kind: test
```

### Execution Levels

```
Level 0 (parallel):  BE-001
Level 1 (parallel):  BE-002, BE-003, BE-004, BE-005, BE-006  (all depend on BE-001)
Level 2 (serial):    BE-007  (depends on all Level 1 tasks)
```

Note: BE-002 through BE-006 can theoretically run in parallel since they modify different files, but they should be grouped together as they are small, related changes best handled by a single agent session.

---

## Implementation Details per Task

### BE-001: Create SequentialToolNode class

**File:** `backend/app/ai/tools/sequential_tool_node.py` (NEW)

**What to create:**

1. A `SequentialToolNode` class that inherits from `ToolNode`
2. Override `_afunc` method (signature matches `ToolNode._afunc` at `tool_node.py:825-856`)
3. Replace `asyncio.gather(*coros)` with a sequential `for` loop: `for coro in coros: outputs.append(await coro)`
4. Log a WARNING via `logging.getLogger(__name__)` when `len(tool_calls) > 1`, including tool names
5. A `patch_tool_node_for_sequential_execution()` function that monkey-patches `ToolNode._afunc` globally
6. Preserve ALL existing behavior: `_parse_input`, `_extract_state`, `_combine_tool_outputs`, `ToolRuntime` construction

**Key implementation reference** -- the upstream `_afunc` at `langgraph/prebuilt/tool_node.py:825-856`:

```python
async def _afunc(self, input, config, runtime):
    tool_calls, input_type = self._parse_input(input)
    config_list = get_config_list(config, len(tool_calls))
    tool_runtimes = []
    for call, cfg in zip(tool_calls, config_list, strict=False):
        state = self._extract_state(input)
        tool_runtime = ToolRuntime(
            state=state,
            tool_call_id=call["id"],
            config=cfg,
            context=runtime.context,
            store=runtime.store,
            stream_writer=runtime.stream_writer,
            execution_info=runtime.execution_info,
            server_info=runtime.server_info,
        )
        tool_runtimes.append(tool_runtime)
    coros = []
    for call, tool_runtime in zip(tool_calls, tool_runtimes, strict=False):
        coros.append(self._arun_one(call, input_type, tool_runtime))
    outputs = await asyncio.gather(*coros)  # <-- THIS IS THE PROBLEM LINE
    return self._combine_tool_outputs(outputs, input_type)
```

The override changes only the dispatch line: `outputs = await asyncio.gather(*coros)` becomes a sequential for-loop.

**Success:** Class defined; imports cleanly; mypy passes.

---

### BE-002: Write unit tests for SequentialToolNode

**File:** `backend/tests/unit/ai/tools/test_sequential_tool_node.py` (NEW)

**Test specifications:**

1. `test_sequential_tool_node_executes_tools_in_order` -- Create 3 mock tools with different execution times. Pass 3 tool calls. Verify execution was sequential (tool 2 started after tool 1 finished, etc.)
2. `test_sequential_tool_node_logs_warning_on_multiple_calls` -- Pass 2+ tool calls. Assert WARNING log message containing tool names
3. `test_sequential_tool_node_single_call_no_warning` -- Pass 1 tool call. Assert no WARNING logged
4. `test_sequential_tool_node_preserves_tool_message_format` -- Verify output matches `ToolNode` format (list of `ToolMessage`)
5. `test_tool_node_monkey_patch_applied` -- After calling `patch_tool_node_for_sequential_execution()`, create a plain `ToolNode` instance and verify it executes sequentially

**Success:** All 5 tests pass; coverage >= 90% for `sequential_tool_node.py`.

---

### BE-003: Change RBACToolNode parent class

**File:** `backend/app/ai/tools/rbac_tool_node.py`

**Changes:**

1. Line 12: Change `from langgraph.prebuilt import ToolNode` to `from app.ai.tools.sequential_tool_node import SequentialToolNode`
2. Line 18: Change `class RBACToolNode(ToolNode):` to `class RBACToolNode(SequentialToolNode):`
3. No other changes needed -- `super().__init__(tools, awrap_tool_call=self._awrap_tool_call)` works correctly with MRO

**Success:** `RBACToolNode` MRO is `RBACToolNode -> SequentialToolNode -> ToolNode`; existing tests pass.

---

### BE-004: Change InterruptNode parent class

**File:** `backend/app/ai/tools/interrupt_node.py`

**Changes:**

1. Line 18: Change `from langgraph.prebuilt import ToolNode` to `from app.ai.tools.sequential_tool_node import SequentialToolNode`
2. Line 52: Change `class InterruptNode(ToolNode):` to `class InterruptNode(SequentialToolNode):`
3. No other changes needed -- `super().__init__(tools, awrap_tool_call=self._awrap_tool_call)` works correctly with MRO

**Success:** `InterruptNode` MRO is `InterruptNode -> SequentialToolNode -> ToolNode`; existing tests pass.

---

### BE-005: Fix fallback graph Option A gap + replace bare ToolNode

**File:** `backend/app/ai/graph.py`

**Changes:**

1. Line 18: Remove `from langgraph.prebuilt import ToolNode` (no longer used)
2. Add `from app.ai.tools.sequential_tool_node import SequentialToolNode`
3. Line 128: Change `llm_with_tools = llm.bind_tools(tools)` to `llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)`
4. Line 209: Change `tool_node = ToolNode(tools)` to `tool_node = SequentialToolNode(tools)`

**Success:** Fallback graph passes `parallel_tool_calls=False`; no bare `ToolNode` in file; existing graph tests pass.

---

### BE-006: Monkey-patch ToolNode._afunc for specialist subgraphs

**Files:**
- `backend/app/ai/tools/sequential_tool_node.py` (extend with `patch_tool_node_for_sequential_execution()` function)
- `backend/app/ai/agent_service.py` (call the patch function at module level, near the existing `ChatDeepSeek.bind_tools` monkey-patch)

**Changes:**

1. In `sequential_tool_node.py`: Add a module-level function `patch_tool_node_for_sequential_execution()` that replaces `ToolNode._afunc` with `SequentialToolNode._afunc` (unbound method). This function is idempotent (checks if already patched).
2. In `agent_service.py`: Import and call `patch_tool_node_for_sequential_execution()` at module level, near the existing `ChatDeepSeek.bind_tools` monkey-patch (around line 95). This ensures it runs at import time before any specialist agents are compiled.
3. Log an INFO message when the patch is applied: `"ToolNode._afunc patched for sequential execution"`

**Rationale for monkey-patching:** The `langchain_create_agent` factory (at `langchain/agents/factory.py:932`) hardcodes `ToolNode(tools=..., ...)` with no option to provide a custom class. The middleware system provides `awrap_tool_call` wrapping but the `_afunc` dispatch still uses `asyncio.gather` before any wrapper runs. A global monkey-patch is the only way to make specialist subgraphs use sequential execution without forking LangChain.

**Success:** After import, any `ToolNode` instance (including those created by `langchain_create_agent`) uses sequential execution.

---

### BE-007: Run full test verification

**What to run:**

1. `cd backend && source .venv/bin/activate && uv run ruff check . && uv run ruff format --check .`
2. `uv run mypy app/`
3. `uv run pytest tests/unit/ai/tools/test_sequential_tool_node.py -v` (new tests)
4. `uv run pytest tests/unit/ai/tools/test_rbac_tool_node.py -v` (existing, must pass)
5. `uv run pytest tests/ai/tools/test_interrupt_node_approval.py -v` (existing, must pass)
6. `uv run pytest tests/unit/ai/ tests/integration/ai/ tests/security/ai/ -v` (broader AI test scope)
7. E2E tests (if available in current environment)

**Success:** All checks pass with zero errors.

---

## Documentation References

### Required Reading

- Upstream `_afunc`: `backend/.venv/lib/python3.12/site-packages/langgraph/prebuilt/tool_node.py` (lines 825-856)
- Agent factory ToolNode creation: `backend/.venv/lib/python3.12/site-packages/langchain/agents/factory.py` (line 932)
- Existing middleware: `backend/app/ai/middleware/sequential_tool_calls.py`
- DeepSeek bind_tools patch: `backend/app/ai/agent_service.py` (lines 77-95)

### Code References

- `RBACToolNode` pattern: `backend/app/ai/tools/rbac_tool_node.py` (subclassing + `super().__init__` pattern)
- `InterruptNode` pattern: `backend/app/ai/tools/interrupt_node.py` (same pattern)
- Fallback graph: `backend/app/ai/graph.py` (lines 128, 209)
- Subagent compilation: `backend/app/ai/subagent_compiler.py` (lines 99-182)

---

## Prerequisites

### Technical

- [x] No database migrations required (code-only change)
- [x] No new dependencies required (uses existing `asyncio`, `logging`, `langgraph`)
- [x] LangGraph version pinned (no breaking `_afunc` signature changes expected)

### Documentation

- [x] Analysis phase approved (00-analysis.md)
- [x] LangGraph `ToolNode._afunc` source reviewed
- [x] LangChain agent factory source reviewed
