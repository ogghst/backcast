# Plan: Prompt Caching Optimization (Static/Dynamic Boundary)

**Created:** 2026-04-03
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 3 -- Remove Dynamic Context from System Prompt Entirely

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 3 from analysis -- Remove all dynamic context from the system prompt
- **Architecture**: The system prompt becomes a pure static string (the `base_prompt` from assistant config, or `DEFAULT_SYSTEM_PROMPT`). The LLM discovers project scope by calling the existing `get_project_context` tool rather than being told via system prompt text.
- **Key Decisions**:
  1. Remove dynamic project context section from `_build_system_prompt()` entirely
  2. Simplify `_build_system_prompt()` to return `base_prompt` unconditionally (or eliminate it)
  3. Deduplicate `DEFAULT_SYSTEM_PROMPT` -- single canonical definition in one module, imported by both consumers
  4. LLM discovers project scope via `get_project_context` tool (already exists and works)

### Success Criteria

**Functional Criteria:**

- [ ] FC-1: `_build_system_prompt()` returns `base_prompt` unchanged regardless of `project_id`, `as_of`, `branch_name`, or `branch_mode` values VERIFIED BY: unit tests
- [ ] FC-2: System prompt is identical across all sessions using the same assistant config (same `system_prompt` field) VERIFIED BY: unit test comparing outputs with different project_id values
- [ ] FC-3: `_run_agent_graph()` inserts a `SystemMessage` containing only the static base prompt into conversation history VERIFIED BY: integration test
- [ ] FC-4: Graph cache key computation unchanged -- still hashes the base prompt from `assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT` VERIFIED BY: unit test
- [ ] FC-5: `DEFAULT_SYSTEM_PROMPT` exists in exactly one file, imported by both `agent_service.py` and `deep_agent_orchestrator.py` VERIFIED BY: grep + import inspection

**Technical Criteria:**

- [ ] TC-1: `ruff check .` passes with zero errors on modified files VERIFIED BY: ruff linter
- [ ] TC-2: `mypy app/` passes with zero errors on modified files (strict mode) VERIFIED BY: mypy type checker
- [ ] TC-3: All existing tests in `backend/tests/unit/ai/test_system_prompt.py` pass after updating assertions VERIFIED BY: pytest
- [ ] TC-4: All existing tests in `backend/tests/integration/ai/test_project_context_security.py` pass after updating assertions VERIFIED BY: pytest
- [ ] TC-5: Test coverage of modified code >= 80% VERIFIED BY: pytest --cov

**TDD Criteria:**

- [ ] Tests updated/created before implementation code
- [ ] Each test fails first (documented in DO phase log)
- [ ] Test coverage >= 80%
- [ ] Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- Simplify `_build_system_prompt()` in `agent_service.py` to remove dynamic context logic
- Remove unused parameters from `_build_system_prompt()` signature
- Deduplicate `DEFAULT_SYSTEM_PROMPT` into a single canonical location
- Update `_run_agent_graph()` call site to use simplified method (or inline the base prompt)
- Update `_create_deep_agent_graph()` to import `DEFAULT_SYSTEM_PROMPT` from canonical location
- Update `chat()` (non-streaming path, line ~490) to import from canonical location
- Update `DeepAgentOrchestrator` to import from canonical location
- Update all test files that assert on project context being present in system prompt
- Delete stale test file `backend/tests/ai/test_system_prompt.py` (legacy, superseded by `backend/tests/unit/ai/test_system_prompt.py`)

**Out of Scope:**

- No changes to `DeepAgentOrchestrator.create_agent()` method logic (prompt assembly at graph compile time is already static)
- No changes to `graph_cache.py` or cache key computation
- No changes to `_build_system_prompt_suffix()` in the orchestrator (it is already static at compile time)
- No changes to `TASK_SYSTEM_PROMPT` in `subagent_task.py`
- No changes to `get_project_context` tool (it already works correctly)
- No changes to frontend code
- No changes to the security model (enforcement remains at tool level via `ToolContext`)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                                 | Files                                                                                           | Dependencies | Success Criteria                                | Complexity |
| --- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------ | ----------------------------------------------- | ---------- |
| 1   | Deduplicate DEFAULT_SYSTEM_PROMPT to canonical location             | `backend/app/ai/constants.py` (new), `backend/app/ai/agent_service.py` (lines 142-159), `backend/app/ai/deep_agent_orchestrator.py` (lines 28-44) | none         | FC-5: single definition, both files import it   | Low        |
| 2   | Simplify `_build_system_prompt()` -- remove dynamic context         | `backend/app/ai/agent_service.py` (lines 1332-1380)                                            | none         | FC-1, FC-2: method returns base_prompt only     | Low        |
| 3   | Update `_run_agent_graph()` call site                               | `backend/app/ai/agent_service.py` (lines 648-656)                                              | task 2       | FC-3: SystemMessage contains only static prompt | Low        |
| 4   | Update other call sites (chat, _create_deep_agent_graph)            | `backend/app/ai/agent_service.py` (lines 349, 490)                                             | task 1       | FC-5: use canonical import                      | Low        |
| 5   | Update unit tests for `_build_system_prompt`                        | `backend/tests/unit/ai/test_system_prompt.py`                                                  | task 2       | TC-3: all unit tests pass                       | Low        |
| 6   | Update integration tests for project context                        | `backend/tests/integration/ai/test_project_context_security.py` (lines 310-347)                 | task 2       | TC-4: integration tests pass                    | Low        |
| 7   | Delete stale legacy test file                                       | `backend/tests/ai/test_system_prompt.py`                                                       | task 5       | No duplicate test class remains                 | Low        |
| 8   | Update performance benchmarks                                       | `backend/tests/ai/test_temporal_performance.py` (lines 97-170)                                 | task 2       | Benchmarks reflect simplified method            | Low        |
| 9   | Run quality gates (ruff, mypy, pytest)                              | All modified files                                                                              | tasks 1-8    | TC-1, TC-2, TC-3, TC-4, TC-5                   | Low        |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File                                          | Expected Behavior                                                         |
| -------------------- | ------- | -------------------------------------------------- | ------------------------------------------------------------------------- |
| FC-1                 | T-001   | `backend/tests/unit/ai/test_system_prompt.py`      | `_build_system_prompt(base_prompt, project_id=X)` returns exactly `base_prompt` |
| FC-1                 | T-002   | `backend/tests/unit/ai/test_system_prompt.py`      | `_build_system_prompt(base_prompt, as_of=Y)` returns exactly `base_prompt`     |
| FC-2                 | T-003   | `backend/tests/unit/ai/test_system_prompt.py`      | Two calls with different `project_id` produce identical output               |
| FC-3                 | T-004   | New test in `test_system_prompt.py`                | `_run_agent_graph` inserts `SystemMessage(content=base_prompt)` only          |
| FC-4                 | T-005   | Existing test in `test_system_prompt.py`           | Graph cache key unchanged by this refactor                                    |
| FC-5                 | T-006   | New test or grep verification                       | `DEFAULT_SYSTEM_PROMPT` defined in exactly one `.py` file                     |
| TC-1 through TC-5    | T-007   | CI quality gate                                    | ruff, mypy, pytest all pass                                                  |

---

## Test Specification

### Test Hierarchy

```text
tests/
├── unit/ai/
│   └── test_system_prompt.py         -- Primary: _build_system_prompt simplified behavior
├── integration/ai/
│   ├── test_project_context_security.py  -- Update: remove project_id-in-prompt assertion
│   └── test_temporal_security.py         -- Already correct (asserts NO temporal in prompt)
├── ai/
│   ├── test_system_prompt.py         -- DELETE: stale legacy file (duplicates unit tests)
│   └── test_temporal_performance.py  -- Update: simplify benchmark to match new method
```

### Test Cases

| Test ID | Test Name                                                         | Criterion | Type        | Verification                                                                 |
| ------- | ----------------------------------------------------------------- | --------- | ----------- | ---------------------------------------------------------------------------- |
| T-001   | `test_build_system_prompt_returns_base_prompt_with_project_id`    | FC-1      | Unit        | `assert result == base_prompt` when `project_id=UUID(...)`                   |
| T-002   | `test_build_system_prompt_returns_base_prompt_with_temporal_args` | FC-1      | Unit        | `assert result == base_prompt` when `as_of`, `branch_name`, `branch_mode` set |
| T-003   | `test_build_system_prompt_identical_across_sessions`              | FC-2      | Unit        | Call with `project_id=A` and `project_id=B`, assert outputs are equal        |
| T-004   | `test_run_agent_graph_system_message_is_static`                   | FC-3      | Integration | Mock history, verify `history[0].content == base_prompt` after call          |
| T-005   | `test_graph_cache_key_uses_base_prompt_hash`                      | FC-4      | Unit        | Verify cache key uses hash of base prompt, not of base+dynamic               |
| T-006   | `test_default_system_prompt_single_definition`                    | FC-5      | Unit/grep   | Assert `agent_service.DEFAULT_SYSTEM_PROMPT is orchestrator.DEFAULT_SYSTEM_PROMPT` (same import) |
| T-007   | `test_project_context_not_in_system_prompt`                       | FC-1      | Integration | Updated: assert `project_id` string NOT in system prompt output               |

### Test Infrastructure Needs

- **Fixtures needed**: Existing `db_session` fixture from conftest; `AsyncMock` for integration tests
- **Mocks/stubs**: `AsyncMock` for `AgentService.config_service` when testing in isolation
- **Database state**: No database seed data required -- changes are to prompt assembly, not data queries

---

## Detailed Change Specification

### Task 1: Deduplicate DEFAULT_SYSTEM_PROMPT

**New file: `backend/app/ai/constants.py`**

Create a new module containing the single canonical `DEFAULT_SYSTEM_PROMPT` constant.

Content: Move the exact string currently at `agent_service.py` lines 142-159 into this new file.

**Modify: `backend/app/ai/agent_service.py`**

- Remove lines 142-159 (the `DEFAULT_SYSTEM_PROMPT` constant definition)
- Add import at top of file: `from app.ai.constants import DEFAULT_SYSTEM_PROMPT`

**Modify: `backend/app/ai/deep_agent_orchestrator.py`**

- Remove lines 28-44 (the `DEFAULT_SYSTEM_PROMPT` constant definition)
- Add import: `from app.ai.constants import DEFAULT_SYSTEM_PROMPT`

### Task 2: Simplify `_build_system_prompt()`

**Modify: `backend/app/ai/agent_service.py`, lines 1332-1380**

Replace the entire method body. The new method:

```python
def _build_system_prompt(self, base_prompt: str) -> str:
    """Return the base system prompt unchanged.

    Context: Project and temporal context are enforced at the tool level
    via ToolContext, not in the system prompt. This keeps the system prompt
    fully static across all sessions, enabling LLM provider prompt caching.

    The LLM discovers project scope by calling get_project_context.

    Args:
        base_prompt: Base system prompt from assistant configuration.

    Returns:
        The base_prompt unchanged.
    """
    return base_prompt
```

Key changes:
- Remove parameters: `project_id`, `as_of`, `branch_name`, `branch_mode`
- Remove the `context_sections` list and project context append logic
- Return `base_prompt` unconditionally

### Task 3: Update `_run_agent_graph()` call site

**Modify: `backend/app/ai/agent_service.py`, lines 648-656**

Change from:

```python
system_prompt = self._build_system_prompt(
    base_prompt=base_prompt,
    project_id=project_id,
    as_of=as_of,
    branch_name=branch_name,
    branch_mode=branch_mode,
)
history.insert(0, SystemMessage(content=system_prompt))
```

To:

```python
system_prompt = self._build_system_prompt(base_prompt=base_prompt)
history.insert(0, SystemMessage(content=system_prompt))
```

The `project_id`, `as_of`, `branch_name`, `branch_mode` are no longer passed to `_build_system_prompt`. They are still used elsewhere in `_run_agent_graph()` for `ToolContext` construction, so they remain as method parameters.

### Task 4: Update other call sites

**Modify: `backend/app/ai/agent_service.py`, line 349**

In `_create_deep_agent_graph()`:
```python
system_prompt = assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT
```
No functional change needed here (already imports from canonical location after Task 1).

**Modify: `backend/app/ai/agent_service.py`, line 490**

In `chat()`:
```python
system_prompt = assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT
```
No functional change needed here (already imports from canonical location after Task 1).

### Task 5: Update unit tests

**Modify: `backend/tests/unit/ai/test_system_prompt.py`**

Update existing tests to remove `project_id`, `as_of`, `branch_name`, `branch_mode` arguments from `_build_system_prompt()` calls. Update assertions:

- Remove assertions that check for `"[TEMPORAL CONTEXT]"` not in result (still valid, but the test no longer needs temporal parameters)
- Remove assertions that check for branch names not in result (no longer relevant since those parameters do not exist)
- Add new test `test_build_system_prompt_returns_base_prompt_with_project_id` -- calls the simplified method and asserts `result == base_prompt`
- Add new test `test_build_system_prompt_identical_across_sessions` -- calls method twice with different conceptual "sessions" (different base_prompts would differ, same base_prompt is identical)

### Task 6: Update integration tests

**Modify: `backend/tests/integration/ai/test_project_context_security.py`, lines 310-347**

The test `test_system_prompt_includes_project_context` currently asserts that `project_id` appears in the system prompt. After the change, it must assert the opposite:

- Rename test to `test_system_prompt_excludes_project_context`
- Change assertions from `assert str(test_project_id) in prompt_with_project` to `assert str(test_project_id) not in prompt_with_project`
- Remove assertion that `"get_project_context"` is in the prompt (it is no longer mentioned there)
- Add assertion: `assert prompt_with_project == base_prompt`
- Update docstring to reflect the new expected behavior

### Task 7: Delete stale legacy test file

**Delete: `backend/tests/ai/test_system_prompt.py`**

This file contains `TestSystemPromptTemporalContext` class with tests that assert `[TEMPORAL CONTEXT]` IS in the prompt (lines 15, 36). These tests are from an older design where temporal context was added to the system prompt. They contradict the current `backend/tests/unit/ai/test_system_prompt.py` which correctly asserts NO temporal context. After the simplification, these tests would fail. Delete the entire file.

### Task 8: Update performance benchmarks

**Modify: `backend/tests/ai/test_temporal_performance.py`, lines 97-170**

Update `test_build_system_prompt_with_temporal_context_benchmark` and `test_build_system_prompt_without_temporal_context_benchmark`:

- Both benchmarks simulate the old `_build_system_prompt` logic with temporal context assembly. After the change, the method is a simple identity function (`return base_prompt`).
- Simplify both benchmarks to measure the trivial `return base_prompt` path.
- Update assertions: remove checks for `[TEMPORAL CONTEXT]`, `branch 'feature-branch'`, etc.
- The benchmark should now measure that the method completes in < 0.01ms (trivial identity).

---

## Risk Assessment

| Risk Type   | Description                                                                                           | Probability | Impact | Mitigation                                                                                      |
| ----------- | ----------------------------------------------------------------------------------------------------- | ----------- | ------ | ----------------------------------------------------------------------------------------------- |
| Technical   | LLM first-turn response may lack project awareness, producing generic greeting without tool call      | Medium      | Low    | The LLM has `get_project_context` tool available and will call it when needed; subagents already have direct tool access with project context in `ToolContext` |
| Technical   | Removing `project_id` parameter from `_build_system_prompt` breaks unknown callers                    | Low         | Low    | grep confirms only 1 call site (`_run_agent_graph` line 649) and tests use the method directly |
| Integration | Stale test `test_system_prompt.py` in `backend/tests/ai/` conflicts with unit test if not deleted     | High        | Medium | Explicitly delete the file in Task 7                                                            |
| Technical   | New `constants.py` module not discovered by importers                                                 | Low         | Low    | Both consumer files are explicitly modified to import from it                                   |
| Integration | `test_project_context_security.py` assertions fail after change                                       | High        | Low    | Explicitly update assertions in Task 6                                                          |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Deduplicate DEFAULT_SYSTEM_PROMPT to canonical constants module"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Simplify _build_system_prompt() -- remove dynamic context logic"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-003
    name: "Update _run_agent_graph() call site and other references"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002]

  - id: BE-004
    name: "Update unit tests for simplified _build_system_prompt"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-005
    name: "Update integration tests for project context security"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-006
    name: "Delete stale legacy test file and update benchmarks"
    agent: pdca-backend-do-executor
    dependencies: [BE-004, BE-005]

  - id: BE-007
    name: "Run quality gates (ruff, mypy, pytest) on modified scope"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-006]
    kind: test
```

---

## Documentation References

### Required Reading

- Analysis: `docs/03-project-plan/iterations/2026-04-03-prompt-caching-optimization/00-analysis.md`
- AI Chat Developer Guide: `docs/02-architecture/ai-chat-developer-guide.md`

### Code References

- System prompt builder: `backend/app/ai/agent_service.py` line 1332
- Agent graph runner: `backend/app/ai/agent_service.py` line 607
- Deep agent orchestrator: `backend/app/ai/deep_agent_orchestrator.py` line 28 (duplicate constant), line 85 (`create_agent`)
- Graph cache key: `backend/app/ai/graph_cache.py` line 46
- Existing unit tests: `backend/tests/unit/ai/test_system_prompt.py`
- Legacy tests to delete: `backend/tests/ai/test_system_prompt.py`
- Project context security tests: `backend/tests/integration/ai/test_project_context_security.py` line 310
- Temporal performance benchmarks: `backend/tests/ai/test_temporal_performance.py` line 97

---

## Prerequisites

### Technical

- [x] No database migrations needed (no schema changes)
- [x] No new dependencies needed
- [x] Backend virtual environment available

### Documentation

- [x] Analysis phase approved (Option 3 selected)
- [x] Architecture docs reviewed (security model confirmed at tool level)
