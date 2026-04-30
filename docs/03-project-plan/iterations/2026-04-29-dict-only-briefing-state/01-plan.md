# Plan: Migrate Briefing State to Dict-Only Representation

**Created:** 2026-04-29
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 (Direct Removal) -- drop markdown entirely.

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option:** Option 1 -- Direct Removal. Drop `briefing: str` from all state schemas and compiler return types.
- **Architecture:** Single source of truth (`briefing_data: dict`) in graph state. Markdown regenerated at read sites via `BriefingDocument.model_validate(data).to_markdown()`.
- **Key Decisions:**
  1. No helper function -- inline `model_validate()` + `to_markdown()` at each read site.
  2. `agent_service.py` renders from `chain_output["briefing_data"]` directly.
  3. `briefing_compiler.py` functions return `(dict, bool)` -- markdown removed from return tuples.

### Success Criteria

**Functional Criteria:**

- [ ] `BackcastSupervisorState` has no `briefing: str` field VERIFIED BY: unit test
- [ ] `_BriefingSupervisorState` has no `briefing: str` field VERIFIED BY: unit test
- [ ] `initialize_briefing()` returns `(dict, bool)` VERIFIED BY: unit test
- [ ] `compile_specialist_output()` returns `(dict, bool)` VERIFIED BY: unit test
- [ ] `get_briefing` tool reads from `briefing_data` and returns rendered markdown VERIFIED BY: unit test
- [ ] Specialist wrapper constructs isolated messages using rendered markdown from `briefing_data` VERIFIED BY: integration test
- [ ] `agent_service.py` publishes `WSBriefingMessage` with markdown rendered from `chain_output["briefing_data"]` VERIFIED BY: manual verification
- [ ] Handoff tool `Command.update` contains only `briefing_data` (no `briefing`) VERIFIED BY: unit test
- [ ] Specialist success/error return dicts contain only `briefing_data` VERIFIED BY: manual verification

**Technical Criteria:**

- [ ] MyPy strict mode zero errors VERIFIED BY: `uv run mypy app/`
- [ ] Ruff zero errors VERIFIED BY: `uv run ruff check .`
- [ ] All existing tests pass after refactoring VERIFIED BY: `uv run pytest tests/ai/test_briefing.py`
- [ ] No performance regression (>5ms overhead per execution) VERIFIED BY: `to_markdown()` is O(n) string concat, called 3-5 times

**Backward Compatibility:**

- [ ] Stale checkpoint with `briefing` field does not crash the graph VERIFIED BY: MemorySaver threads deleted before each execution, no migration needed

### Scope Boundaries

**In Scope:**

- `backend/app/ai/briefing_compiler.py` -- change return types
- `backend/app/ai/supervisor_state.py` -- remove `briefing: str` field
- `backend/app/ai/supervisor_orchestrator.py` -- update all read/write sites, subgraph state, `get_briefing` tool
- `backend/app/ai/handoff_tools.py` -- remove `briefing` from `Command.update`
- `backend/app/ai/agent_service.py` -- render from `chain_output["briefing_data"]`
- `backend/tests/ai/test_briefing.py` -- update compiler tests for new return types

**Out of Scope:**

- Frontend changes (no frontend state changes -- `WSBriefingMessage.briefing: str` still sends markdown string)
- `BriefingDocument` model changes (no changes to `to_markdown()`)
- `parse_structured_findings()` changes
- Database migrations (checkpointer is in-memory)

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|------------------|------------|
| 1 | Update `briefing_compiler.py` return types | `briefing_compiler.py` | none | `initialize_briefing()` returns `(dict, bool)`, `compile_specialist_output()` returns `(dict, bool)`, mypy clean | Low |
| 2 | Update compiler tests for new return types | `test_briefing.py` | task 1 | All `TestInitializeBriefing` and `TestCompileSpecialistOutput` tests updated and passing | Low |
| 3 | Remove `briefing: str` from `BackcastSupervisorState` | `supervisor_state.py` | none | TypedDict has no `briefing` field, mypy clean | Low |
| 4 | Update `_BriefingSupervisorState` and `get_briefing` tool | `supervisor_orchestrator.py` | task 3 | Subgraph state uses `briefing_data`, tool renders markdown inline | Low |
| 5 | Update `initialize_briefing_node` | `supervisor_orchestrator.py` | tasks 1, 3 | Returns only `briefing_data` (no `briefing` key) | Low |
| 6 | Update specialist wrapper (error + success paths) | `supervisor_orchestrator.py` | tasks 1, 3 | Reads `briefing_data`, renders markdown for messages, returns only `briefing_data` | Low |
| 7 | Update handoff tool `Command.update` | `handoff_tools.py` | tasks 1, 3 | `Command.update` contains only `briefing_data`, renders markdown for propagation to next node | Low |
| 8 | Update `agent_service.py` event listener | `agent_service.py` | task 3 | Reads `chain_output["briefing_data"]`, renders markdown for `WSBriefingMessage` | Low |
| 9 | Run quality gates | all | tasks 1-8 | `ruff check`, `mypy`, `pytest` all pass | Low |

### Execution Order

Tasks 1, 2, 3 can run in parallel (independent changes). Tasks 4-8 depend on tasks 1 and 3 being complete. Task 9 is final verification.

```
Task 1 (compiler) ──┐
Task 3 (state)    ──┼── Task 4 (subgraph + tool)
                    ├── Task 5 (init node)
                    ├── Task 6 (specialist wrapper)
                    ├── Task 7 (handoff)
                    └── Task 8 (agent_service)
                         └── Task 9 (quality gates)
Task 2 (tests) ────────── Task 9 (quality gates)
```

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---------------------|--------|-----------|-------------------|
| AC-1: compiler returns (dict, bool) | T-001 | `test_briefing.py::TestInitializeBriefing` | `initialize_briefing("x")` returns 2-tuple `(dict, bool)` |
| AC-2: compiler returns (dict, bool) | T-002 | `test_briefing.py::TestCompileSpecialistOutput` | `compile_specialist_output(...)` returns 2-tuple `(dict, bool)` |
| AC-3: get_briefing renders from data | T-003 | `test_briefing.py` (new test) | Tool returns markdown when given `briefing_data` in state |
| AC-4: state has no briefing field | T-004 | manual/mypy | MyPy catches any remaining `state["briefing"]` reads |
| AC-5: handoff drops briefing | T-005 | manual/visual | `Command.update` dict has no `"briefing"` key |
| AC-6: agent_service renders from data | T-006 | manual/visual | `chain_output["briefing_data"]` used to render markdown |

---

## Test Specification

### Test Hierarchy

```
tests/ai/test_briefing.py
├── TestInitializeBriefing (update return type expectations)
├── TestCompileSpecialistOutput (update return type expectations)
└── TestGetBriefingTool (new: verify inline rendering from briefing_data)
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Verification |
|---------|-----------|-----------|------|-------------|
| T-001 | `test_creates_valid_briefing` returns 2-tuple | AC-1 | Unit | `initialize_briefing("x")` returns `(dict, bool)` with 2 elements |
| T-002 | `test_appends_section` returns 2-tuple | AC-2 | Unit | `compile_specialist_output(...)` returns `(dict, bool)` with 2 elements |
| T-003 | `test_get_briefing_renders_from_data` | AC-3 | Unit | Tool function returns markdown when state contains `briefing_data` |
| T-004 | `test_get_briefing_handles_empty_data` | AC-3 | Unit | Tool returns fallback string when `briefing_data` is missing/empty |

### Test Infrastructure Needs

- **No new fixtures** required -- existing `BriefingDocument` and compiler tests cover the data layer
- **No mocks** -- `get_briefing` tool is a pure function wrapping `model_validate()` + `to_markdown()`
- **No database** -- all changes are to in-memory state and pure functions

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|-----------|-------------|------------|--------|------------|
| Technical | LangGraph state key mismatch: removing `briefing` from `_BriefingSupervisorState` could break `InjectedState` access | Low | High | Test subgraph state sharing by changing field to `briefing_data: dict` |
| Technical | `agent_service.py` reads from specialist return dict, not graph state -- return dict shape must include `briefing_data` | Low | Med | Specialist wrapper already returns `briefing_data`; verify chain_output contains it |
| Technical | Compiler test changes are mechanical but numerous (13 test methods) | Low | Low | Update tests task-by-task, run after each compiler change |

---

## Documentation References

### Code References

- `backend/app/ai/briefing_compiler.py` -- compiler functions to update
- `backend/app/ai/supervisor_state.py` -- state TypedDict to update
- `backend/app/ai/supervisor_orchestrator.py` -- orchestrator read/write sites
- `backend/app/ai/handoff_tools.py` -- handoff Command.update
- `backend/app/ai/agent_service.py:1032-1060` -- event listener
- `backend/tests/ai/test_briefing.py` -- existing test suite
- `backend/app/ai/briefing.py` -- BriefingDocument (no changes needed)

### Related Iteration Context

- `docs/03-project-plan/iterations/2026-04-27-briefing-room-orchestration/issue-log.md` -- IL-12 context

---

## Prerequisites

### Technical

- [x] No database migrations needed (in-memory checkpointer)
- [x] No dependency changes needed
- [x] No environment changes needed

### Documentation

- [x] Analysis phase approved with Option 1 selected
- [x] All read/write sites inventoried in analysis
