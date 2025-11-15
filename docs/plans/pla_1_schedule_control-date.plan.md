# PLA-1: Cost Element Schedule Control-Date Filtering – Detailed Plan

**Objective:** Ensure every API that surfaces operational (non-baseline) cost element schedules respects both `registration_date` and `created_at` relative to the active time-machine control date so historical views stay authoritative.

**Working Agreements:** TDD (failing tests first), incremental commits (<100 LOC, <5 files), reuse existing abstractions, backend + test changes in same commit whenever production code changes.

**Assumptions to Validate Before Coding**
1. A schedule is eligible only when **both** `registration_date ≤ control_date` and `created_at ≤ end_of_day(control_date)` (late-entered backdated registrations should be hidden when rewinding).
2. Baseline-linked schedules (`baseline_id IS NOT NULL`) remain excluded from operational endpoints; no change required.
3. No UI component should display future schedules once backend filtering is in place; no new frontend state is needed for this story.

If any assumption is rejected, revise plan before proceeding.

---

## Phase 0 – Discovery & Test Data Enhancements (Failing Tests First)

**Goal:** Capture the regression via new/updated tests that currently fail because schedules created after the control date still leak through when their registration date is earlier.

**Target Files**
- `backend/tests/api/routes/test_budget_timeline.py`
- `backend/tests/services/test_planned_value.py`
- `backend/tests/api/routes/test_cost_element_schedules.py` (history endpoint)

**Commits**
1. **Commit 0.1 – Budget Timeline regression test**
   - Add fixture data where `schedule.registration_date` is before control date but `created_at` is after.
   - Extend `test_budget_timeline_respects_control_date` (or add new test) asserting schedule payloads are empty for that element.
   - Expect failure (current API still returns the schedule).

2. **Commit 0.2 – Planned Value regression test**
   - In `test_planned_value_selects_latest_schedule_for_control_date`, include a schedule with `registration_date <= control_date < created_at`.
   - Assert `_select_latest_schedule_for_control_date` ignores it.
   - Test should fail until service logic clamps `created_at`.

3. **Commit 0.3 – Cost element schedule history regression test**
   - Add test covering `GET /cost-element-schedules/history` when latest schedule’s `created_at` is > control date (should be hidden once dependency added).
   - Temporarily mark `xfail` if dependency work happens later in plan; remove once filtering implemented.

---

## Phase 1 – Shared Filtering Utilities

**Goal:** Prevent duplicated logic by centralizing the dual-date cutoff calculation.

**Target Files**
- `backend/app/api/deps.py` (export `_end_of_day` or new helper)
- `backend/app/services/time_machine.py` (new helper module) – optional

**Commits**
1. **Commit 1.1 – Introduce helper**
   - Create `app/services/time_machine.py` with `end_of_day(control_date: date) -> datetime` and `schedule_cutoff_filters(query, control_date)` returning SQLAlchemy expressions for `(registration_date <= control_date)` and `(created_at <= end_of_day(control_date))`.
   - Add unit tests if helper has logic beyond simple combine.

2. **Commit 1.2 – Update imports**
   - Replace duplicated `_end_of_day` definitions in affected routers with the shared helper (no behavioral change yet).
   - Run tests to ensure no regressions before applying new filtering.

---

## Phase 2 – API Filter Enforcement

**Goal:** Apply dual-date clamps everywhere operational schedules are queried.

**Target Files**
- `backend/app/api/routes/budget_timeline.py`
- `backend/app/api/routes/planned_value.py`
- `backend/app/api/routes/cost_element_schedules.py` (history + latest read)
- `backend/app/api/routes/baseline_logs.py` helper `_select_latest_cost_element_schedule_before_date` (if reused)

**Commits**
1. **Commit 2.1 – Budget Timeline route**
   - Update schedule subquery to add `CostElementSchedule.created_at <= end_of_day(control_date)`.
   - Ensure ordering stays `(registration_date DESC, created_at DESC)`.
   - Keep modifications within 2–3 files (router + helper + tests). Tests from Phase 0 should start passing here.

2. **Commit 2.2 – Planned Value service**
   - Apply same filter inside `_select_latest_schedule_for_control_date` (and map helper usage).
   - Update service tests (Phase 0) should pass now.

3. **Commit 2.3 – Cost Element Schedule router**
   - Inject `TimeMachineControlDate` into `/` and `/history` endpoints, enforcing filters so schedule modal mirrors other APIs.
   - Update tests accordingly.

4. **Commit 2.4 – Baseline helpers (if needed)**
   - For helper functions invoked during baseline creation (e.g., `create_latest_schedule_snapshot`) ensure they still look at operational schedules irrespective of control date. If not impacted, document reason and skip.

---

## Phase 3 – Documentation & Developer Notes

**Goal:** Capture the dual-date rule for future contributors.

**Target Files**
- `docs/analysis/PLA_1_high_level_analysis.md` (append “Decision Log” section)
- `docs/project_status.md` (Sprint notes under PLA-1)
- `docs/plans/...` (this file) – update status after implementation

**Commit 3.1 – Docs update**
- Summarize final rule (both timestamps must be ≤ control date) and mention helper location.
- Keep commit under 100 lines (likely 2 docs).

---

## Phase 4 – Verification

**Goal:** Ensure regressions are fully covered.

**Commands**
1. `cd /home/nicola/dev/pesta/backend && source .venv/bin/activate`
2. `python -m pytest backend/tests/api/routes/test_budget_timeline.py backend/tests/api/routes/test_cost_element_schedules.py backend/tests/services/test_planned_value.py`

If additional files touched, expand pytest scope accordingly. Capture results in final summary.

---

## Deliverables Checklist (Status: 2025-11-15)
- [x] Failing tests demonstrating issue (Phase 0) – added coverage in budget timeline, planned value, and cost element schedule suites.
- [x] Shared helper for consistent filtering (Phase 1) – `backend/app/services/time_machine.py`.
- [x] Updated routers/services respecting both timestamps (Phase 2) – budget timeline, planned value, cost element schedules, and baseline logs now reuse the helper.
- [x] Documentation and status updates (Phase 3) – analysis doc annotated with decision log; plan updated.
- [x] Passing targeted pytest suites (Phase 4) – `python -m pytest tests/api/routes/test_budget_timeline.py::test_budget_timeline_hides_schedules_created_after_control_date_even_if_backdated tests/api/routes/test_planned_value.py::test_cost_element_planned_value_ignores_schedules_created_after_control_date tests/api/routes/test_cost_element_schedules.py::test_get_schedule_respects_control_date_created_at_filter tests/api/routes/test_cost_element_schedules.py::test_schedule_history_respects_control_date_filters`

Proceed only after stakeholder confirms assumptions or provides alternate rules. Once confirmed, follow the phase order strictly (no skipping to implementation ahead of failing tests).
