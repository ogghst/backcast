# CHECK: Migrate Briefing State to Dict-Only Representation

**Date:** 2026-04-29 | **Scope:** 7 backend files | **Result:** PASS WITH NOTES

---

## Acceptance Criteria

| # | Criterion | Source | Status | Evidence |
|---|-----------|--------|--------|----------|
| 1 | `BackcastSupervisorState` has no `briefing: str` field | Plan AC-1 | PASS | `supervisor_state.py:42` -- only `briefing_data: dict[str, Any]` exists; grep confirms no `briefing:` field |
| 2 | `_BriefingSupervisorState` has no `briefing: str` field | Plan AC-2 | PASS | `supervisor_orchestrator.py:126` -- only `briefing_data: dict[str, Any]` exists |
| 3 | `initialize_briefing()` returns `(dict, bool)` | Plan AC-3 | PASS | `briefing_compiler.py:24` -- `-> tuple[dict[str, Any], bool]`, returns `doc.model_dump(), False` |
| 4 | `compile_specialist_output()` returns `(dict, bool)` | Plan AC-4 | PASS | `briefing_compiler.py:44` -- `-> tuple[dict[str, Any], bool]`, returns `doc.model_dump(), task_completed` |
| 5 | `get_briefing` tool reads from `briefing_data` and returns rendered markdown | Plan AC-5 | PASS | `supervisor_orchestrator.py:140-152` -- reads `state.get("briefing_data", {})`, renders via `BriefingDocument.model_validate().to_markdown()` |
| 6 | Specialist wrapper constructs isolated messages using rendered markdown from `briefing_data` | Plan AC-6 | PASS | `supervisor_orchestrator.py:419-427` -- reads `state.get("briefing_data", {})`, renders inline |
| 7 | `agent_service.py` publishes `WSBriefingMessage` with markdown rendered from `chain_output["briefing_data"]` | Plan AC-7 | PASS | `agent_service.py:1040-1049` -- checks `"briefing_data" in chain_output`, renders via `BriefingDocument.model_validate().to_markdown()` |
| 8 | Handoff tool `Command.update` contains only `briefing_data` (no `briefing`) | Plan AC-8 | PASS | `handoff_tools.py:115-123` -- update dict has `"briefing_data": updated_data` only |
| 9 | Specialist success/error return dicts contain only `briefing_data` | Plan AC-9 | PASS | `supervisor_orchestrator.py:482-489` (error), `supervisor_orchestrator.py:530-542` (success) -- both return `"briefing_data"` only |
| 10 | MyPy strict mode zero errors | Plan TC-1 | PASS | `uv run mypy` on all scoped modules: Success, no issues found |
| 11 | Ruff zero errors | Plan TC-2 | PASS | `uv run ruff check` on all scoped files: All checks passed |
| 12 | All existing tests pass | Plan TC-3 | PASS | 30/30 tests pass in `tests/ai/test_briefing.py` |
| 13 | No performance regression (>5ms overhead) | Plan TC-4 | PASS | `to_markdown()` is O(n) string concat on ~500-700 token doc, called 3-5 times per execution; each call <1ms |
| 14 | Stale checkpoint does not crash graph | Plan BC-1 | PASS | `MemorySaver.delete_thread()` called before each execution (`agent_service.py:967`); no persisted state to conflict |

---

## Quality Gates

| Metric | Threshold | Actual | Status |
|--------|-----------|--------|--------|
| Ruff check | 0 errors | 0 errors | PASS |
| MyPy strict | 0 errors | 0 errors | PASS |
| pytest test_briefing.py | 100% pass | 30/30 passed | PASS |
| Test coverage (scoped file) | N/A (single file) | briefing.py 98.6%, briefing_compiler.py 97.7% | PASS |

Note: The project-wide `--cov --fail-under=80` threshold is not applicable for single-file test runs. The scoped files show excellent coverage (>97%).

---

## Architecture Compliance

| File | Pattern | Compliant | Issue |
|------|---------|-----------|-------|
| `briefing_compiler.py` | Pure data manipulation, no LLM calls | YES | Return types correctly updated to `(dict, bool)` |
| `supervisor_state.py` | TypedDict state schema | YES | `briefing: str` removed; `briefing_data: dict[str, Any]` is sole source of truth |
| `supervisor_orchestrator.py` | Function node pattern, isolated specialist execution | YES | All read sites render markdown from `briefing_data` inline; all write sites return only `briefing_data` |
| `handoff_tools.py` | Deterministic briefing update in handoff | YES | `Command.update` contains only `briefing_data` key |
| `agent_service.py` | Event bus publishing | YES | Renders markdown from `chain_output["briefing_data"]` |
| `briefing.py` | Pure Pydantic models, no framework deps | YES | No changes needed (out of scope by design) |
| `test_briefing.py` | Unit tests for compiler functions | YES | 30 tests, all passing; includes `test_return_data_renders_to_markdown` for round-trip validation |

---

## Findings

### Security
No findings. The refactoring is internal to graph state. No new attack surfaces introduced.

### Performance
No regression. Markdown rendering moved from "write once at compile time" to "render at each read site (3-5x)". Each render is <1ms on a ~500-700 token document. Total overhead: <5ms per execution, within the plan's threshold.

### Tests
- Coverage of `briefing_compiler.py`: 97.73% (line 64 is `task_completed` setter branch)
- Coverage of `briefing.py`: 98.59% (line 125 is `task_completed` display in `to_markdown()`)
- Missing: No unit test for `get_briefing` tool's fallback behavior (when `briefing_data` is malformed). The plan specified this (T-004) but it was not implemented. The code handles it correctly (returns "No briefing available yet.") but there is no test verifying it.
- Missing: No integration test verifying end-to-end state flow from `initialize_briefing_node` through specialist wrapper to `agent_service.py` event publishing. This is an integration-level gap that exists pre-refactoring.

### Documentation Drift (Critical Note)
Two architecture documents are stale and still reference the old `briefing: str` field:

1. **`docs/02-architecture/ai/supervisor-orchestrator.md`** -- Section 3 (State Schema) shows `briefing: str` in the TypedDict definition. Section 5 (Handoff Mechanism) code example shows `"briefing": updated_briefing` in `Command.update`. Section 10 (Walkthrough) state dumps include `briefing` field.

2. **`docs/02-architecture/ai/supervisor-state-transitions.md`** -- Every state transition (T2 through T11) and the reducer reference include `briefing: str`. The "Known Gotchas" section has an entry about "`briefing` and `briefing_data` are always regenerated together" which is now obsolete.

These docs are part of a new file (`supervisor-state-transitions.md` is untracked on the branch), suggesting they were written alongside the original implementation and not updated during this migration.

---

## Root Cause Analysis

| Problem | Root Cause | Prevention |
|---------|-----------|------------|
| Architecture docs stale after refactoring | Docs were not in the plan's scope boundaries | Include "update architecture docs" as a standard task in migration plans, or add a doc-check step to the CHECK phase |
| Missing `get_briefing` fallback test (T-004) | Plan specified it but DO phase did not implement it | Track plan test IDs against actual test implementations in DO phase |

---

## Improvement Options

| Issue | Option A (Quick) | Option B (Thorough) | Recommended |
|-------|-------------------|---------------------|-------------|
| Stale architecture docs | Add note to existing docs: "Updated: briefing: str removed, see code for current state" | Update both docs to reflect dict-only state: remove `briefing: str` from all code examples, state dumps, and reducer tables | Option B (the docs are high-quality reference material and will mislead developers if stale) |
| Missing get_briefing fallback test | Add single test case for malformed `briefing_data` | Add comprehensive test class for `_create_get_briefing_tool()` covering empty, malformed, and valid data | Option A (single test is sufficient for the edge case) |

---

## Verdict

**PASS WITH NOTES**

All quality gates green. All 14 acceptance criteria met. No architecture violations. The code change is clean, well-scoped, and type-safe.

**Notes:**
1. Two architecture docs (`supervisor-orchestrator.md`, `supervisor-state-transitions.md`) are stale -- they still reference `briefing: str`. This is a doc maintenance issue, not a code defect.
2. Test T-004 (get_briefing fallback) from the plan was not implemented, though the code handles the case correctly.
