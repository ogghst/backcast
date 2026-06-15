# ACT: P0 — Standardize, carry forward, close

**Iteration:** `2026-06-15-chat-scenario-gaps` · **Date:** 2026-06-15

P0 (G1) is **complete and verified** (`02-do.md`, `03-check.md`). This ACT captures what to standardize, what it unblocks, and what it surfaced for the remaining items.

---

## Standardize (apply the lesson across the codebase)

**Lesson:** AI tool functions that hand-build entity dicts drift out of sync with the model — fields exist in the DB and public schema but are silently invisible to the LLM. The `get_project`/`list_projects`/`get_project_context`/`get_project_structure` quartet each re-implemented project serialization and each independently omitted `contract_value`.

**Action — consistency sweep (small, defer-able but recommended):**
- Grep for other AI tools that build entity dicts from ORM objects (`backend/app/ai/tools/`) and confirm each surfaces the fields a specialist would plausibly be asked about (e.g. `WBSElement.budget_allocation` is surfaced; check `CostElement`, `WorkPackage`, `ControlAccount` for analogous omissions). Pattern to look for: `"budget": float(x.budget) …` style literals that hand-pick columns.
- Consider a shared `_project_to_dict(project)` helper in `project_tools.py` (or `temporal_logging.py` next to `add_temporal_metadata`) so all four call sites serialize identically. This was **not** done in P0 to keep the change surgical (per the "Simplicity First / Surgical Changes" guideline) — but if a 5th call site appears, refactor then.

**Action — already applied:**
- `contract_value` + `currency` now in all 4 project-serializing tools. Unit test guards regression.

## What P0 unblocks / de-risks

- **G5 (ask_user over-triggers) is largely mitigated for this class.** The Scenario-1 ask_user was a *symptom* of G1: the specialist asked the user to disambiguate a field that existed but was unsurfaced. With the field visible, no clarification fires. Remaining ask_user hygiene work (P5) is now lower priority — revisit only if a *different* ask_user over-trigger is observed.
- **Scenario 1 is a green regression baseline.** Future changes to project tooling can re-run it cheaply (now ~87s, 41k tokens) to catch regressions in financial-field surfacing.

## Carried forward (fed back into the plan)

| Observation from P0 work | Feeds | Note |
|--------------------------|-------|------|
| Log TZ is **launch-env-dependent** (old server local, restarted server UTC) | **P4 (G6) — already DONE in code** | `backend/app/core/logging.py:34` sets `formatter.converter = time.gmtime` (UTC) and `LOG_FORMAT` appends `Z`. The fix existed but the stale Jun-14 server (no `--reload`) never loaded it; my restart activated it. Verified live: log line `04:15:13Z` and DB `started_at=04:14:02Z` are both UTC → P4 acceptance met. **Recommend closing P4**; the only action was the server restart. |
| `[SUPERVISOR] Max iterations (5) reached, forcing END` + `No matching step found for 'project_manager'` warnings | **P1 (G2)** | Supervisor routing terminates via iteration cap rather than clean completion even on a trivial single-step plan. Relevant context for the replan/router spike. |
| Assistant correctly reports `budget=None` alongside `contract_value=€1M` | docs/seed-data | Confirms AAA First has cost-element budget = null (no WBS/costs). Reinforces the plan note to seed one fully-populated project for EVM/visualization scenarios (P2). |

## Process notes (how the iteration ran)

- **Server had to be restarted manually.** The dev server was running *without* `--reload`, so code edits did not hot-apply. Operational note: confirm `--reload` (or restart) after any backend edit before re-verifying. (The CLAUDE.md documented dev command includes `--reload`; the running instance did not.)
- **Modified-scope quality checks held.** Running MyPy/Ruff/pytest only on the touched files + new test kept the verify loop to seconds, consistent with the CLAUDE.md "test only the modified scope" guidance.

## Definition of Done (for P0)

- [x] Change implemented (4 dicts, surgical).
- [x] Unit test added and green (3 passed).
- [x] MyPy strict + Ruff clean on modified scope.
- [x] e2e Scenario 1 re-run: correct answer, no ask_user, no "not available".
- [x] DB row `status=completed`, `error_message=NULL`.
- [x] `02-do.md` / `03-check.md` / `04-act.md` written from the re-run.

**P0 status: ✅ CLOSED.** **P4 (G6) also effectively CLOSED** — the logging-UTC fix already lived in code; the server restart activated it (verified live). Remaining open: P1 (G2 replan), P2 (G3 planner collapse), P3 (G4 tokens), P5 (G5/G7 polish) — independently schedulable per `01-plan.md`. This iteration folder stays open until those are addressed (or formally descoped).
