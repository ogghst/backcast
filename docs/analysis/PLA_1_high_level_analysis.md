# PLA-1 Cost Element Schedule Control-Date Filtering – High-Level Analysis

**Task:** Align cost element schedule visibility with the global time-machine control date **and** ensure ordering respects both `registration_date` and `created_at`.

**Status:** Analysis Phase
**Date:** 2025-11-15
**Current Time:** 15:16 CET (Europe/Rome)

---

## User Story
As a project controls lead reviewing historical progress, I need cost element schedules to respect the selected control date so that only registrations created on or before that date (and whose effective registration dates are also ≤ control date) participate in downstream metrics such as Budget Timeline and Planned Value.

---

## 1. Codebase Pattern Analysis

1. **Time-machine filtered read endpoints (Projects/WBEs/Cost Elements/Budget Timeline).** Current routers resolve `control_date` via `TimeMachineControlDate` and use `_end_of_day(control_date)` to clamp entity `created_at` plus schedule `registration_date`/`created_at` ordering when fetching per-cost-element schedules.

```71:125:backend/app/api/routes/budget_timeline.py
    statement = select(CostElement).where(
        CostElement.wbe_id.in_(wbe_ids_from_project),
        CostElement.created_at <= _end_of_day(control_date),
    )
    ...
            select(CostElementSchedule)
            .where(
                CostElementSchedule.cost_element_id == ce.cost_element_id,
                CostElementSchedule.registration_date <= control_date,
            )
            .order_by(
                CostElementSchedule.registration_date.desc(),
                CostElementSchedule.created_at.desc(),
            )
```

2. **Schedule selection helpers.** Dedicated helper functions retrieve “latest operational schedule” by ordering on `registration_date` then `created_at`, ensuring deterministic fallback when multiple registrations share the same effective date. These helpers already live within the cost element schedule router and planned value service, establishing a namespace for reusable selection logic.

```22:48:backend/app/api/routes/cost_element_schedules.py
def _select_latest_operational_schedule(...):
    statement = (
        select(CostElementSchedule)
        .where(CostElementSchedule.cost_element_id == cost_element_id)
        .where(CostElementSchedule.baseline_id.is_(None))
        .order_by(
            CostElementSchedule.registration_date.desc(),
            CostElementSchedule.created_at.desc(),
        )
    )
```

3. **Test coverage enforcing control-date behavior.** Pytest suites such as `test_budget_timeline_respects_control_date` already freeze the time-machine date before hitting APIs, confirming both entity-level cutoff (`created_at`) and transactional dates (`registration_date` for schedules, `registration_date` for cost registrations) are enforced.

```162:210:backend/tests/api/routes/test_budget_timeline.py
def test_budget_timeline_respects_control_date(...):
    control_date = date(2024, 2, 1)
    ...
    set_time_machine_date(client, superuser_token_headers, control_date)
    response = client.get(...)
    assert all(schedule["registration_date"] <= control_date.isoformat() for schedule in data)
```

**Architectural layers to respect**
- *FastAPI routers* under `backend/app/api/routes/` orchestrate dependencies and HTTP contracts.
- *Service/helper layer* (e.g., `_select_latest_operational_schedule`, planned value helpers) encapsulates query semantics.
- *SQLModel models/schemas* within `backend/app/models/` maintain Base/Create/Update/Public parity and enforce field availability.
- *Frontend components + TanStack Query* rely on generated client services and expect the backend to honor server-side filtering, minimizing client-side date logic.

---

## 2. Integration Touchpoint Mapping

- **Backend dependencies/config**
  - `backend/app/api/deps.py`: Confirm `TimeMachineControlDate` dependency stays authoritative; consider extending shared utility (e.g., `_end_of_day`) for reuse across schedule-specific routers.
  - `backend/app/api/routes/budget_timeline.py` & `planned_value.py`: Update schedule selection blocks to clamp by both `created_at` and `registration_date` (current logic only guards registration date).
  - `backend/app/api/routes/cost_element_schedules.py`: Introduce shared query builder or filter mixin so standalone schedule endpoints enforce the same `control_date` semantics when invoked through aggregated services.
  - `backend/app/models/cost_element_schedule.py`: No schema change expected, but docstrings and validations should emphasize dual-date filtering.
  - `backend/tests/...`: Expand regression coverage in budget timeline, planned value, and cost element schedule history tests to cover cases where `created_at` is after control date but `registration_date` is before (and vice versa).

- **Frontend touchpoints**
  - `frontend/src/components/Projects/BudgetTimeline.tsx` & associated filter components: No direct change anticipated if backend enforces filtering, but update TypeScript expectations/tests to assert that future-dated schedules are omitted without extra client logic.
  - Playwright spec `frontend/tests/project-cost-element-tabs.spec.ts`: Extend assertions ensuring timeline tab hides schedules outside control date when time machine context (once UI exists) is rewound.

- **Configuration**
  - Time-machine preference persistence (per PLA-2) will reside server-side; ensure any new router dependency introduced for schedule filtering reuses that configuration rather than new query params.

---

## 3. Abstraction Inventory

- **Time-machine dependency injection.** `get_time_machine_control_date` already exemplifies FastAPI DI best practices (per FastAPI docs) for injecting shared request-scoped state, matching the recommended `Depends()` patterns provided by FastAPI’s reference material.
- **Schedule selection helpers.** `_select_latest_operational_schedule`, `_select_operational_schedule_history`, and planned value helper `_select_latest_schedule_for_control_date` encapsulate ordering logic; they should be composed instead of duplicating SQL ordering clauses.
- **End-of-day utility.** `_end_of_day(control_date)` exists in multiple routers; factoring it into a shared module (e.g., `app.services.time_machine`) would enforce consistent datetime truncation.
- **Testing utilities.** `set_time_machine_date` fixture plus model factories (projects/WBEs/cost elements) offer reusable building blocks to craft failing tests before implementation.
- **Frontend data hooks.** TanStack Query keys already include filter objects; once the navbar time-machine control ships, those keys will naturally segregate cache entries per control date without extra plumbing.

---

## 4. Alternative Approaches

| Approach | Summary | Pros | Cons/Risks | Architectural Alignment | Complexity |
| --- | --- | --- | --- | --- | --- |
| **A. Router-level hardening (Recommended)** | Update every schedule-consuming route to add `created_at <= control_date_end_of_day` alongside existing `registration_date <= control_date`, keeping order_by as `(registration_date DESC, created_at DESC)`. | Minimal schema impact; reuses existing DI & helpers; full server-side enforcement. | Requires auditing all endpoints; risk of missing hidden access paths. | High – extends current router/service patterns; honors TDD/TimeMachine architecture. | Medium (backend-only changes + tests). |
| **B. Centralized schedule query helper** | Introduce a new helper (e.g., `select_latest_schedule_before(control_date)`) returning subqueries filtered by both timestamps; update routers/services to call it. | Single source of truth; easier future enforcement; sharable across Budget Timeline, PV, EV. | Needs refactor of existing helper call sites; risk of regressions if not integrated everywhere. | High – promotes abstraction reuse. | Medium-High (refactor + adoption). |
| **C. Database view/materialized view** | Create a SQL view exposing “control-date-effective schedules” with computed `effective_datetime = LEAST(created_at, registration_date)` and query the view. | Pushes logic into DB, simplifying application queries; potential performance boost. | Increases schema complexity; view must parameterize control date (requiring session variables) which PostgreSQL cannot do per request without temp tables; complicates migrations/tests. | Low – deviates from current model-first approach. | High (migrations + DB logic + testing). |

---

## 5. Architectural Impact Assessment

- **Principles upheld:** Strengthens consistency and historical accuracy mandates behind the time-machine feature set, leveraging FastAPI DI and SQLModel layering per existing architecture. Using helper abstractions keeps logic DRY and respects the “architectural respect” working agreement.
- **Potential violations:** If only selective endpoints are updated, the system risks split-brain behavior where some pages obey the new rule while others leak future schedules. A thorough audit or shared helper is critical to avoid this maintainability trap.
- **Future maintenance:** Centralized helper (Approach B) minimizes future drift; router-by-router patches (Approach A) demand regression tests to guard against regressions. Consider documenting the dual-date invariant in `CostElementSchedule` schema docstrings and developer docs.
- **Testing challenges:** Need synthetic data where `registration_date <= control_date < created_at` (e.g., retroactively entered schedules) to prove the new filters behave as expected. Frontend e2e tests must coordinate with time-machine context once implemented to assert UI parity.

---

## Risks, Unknowns, and Ambiguities

- **Data semantics ambiguity:** Requirement states “filter by creation date but also registration date.” Need clarity on precedence when one timestamp passes and the other fails. Proposed interpretation: both must be ≤ control date to consider a schedule active.
- **Backfill considerations:** Historical schedules entered late will now be hidden unless we treat `registration_date` as the controlling field for historical inclusion. Confirm with stakeholders whether late-entered but backdated schedules should appear when rewinding to the registration date.
- **Performance impact:** Additional filter clauses may benefit from composite indexes on `(cost_element_id, registration_date, created_at)`; need to assess query plans on large datasets.
- **Baseline linkage:** Baseline snapshots clone schedules irrespective of control date; ensure new logic excludes baseline-backed schedules from operational queries as it does today.

---

## Summary & Next Steps

- **What:** Enforce dual-date (created and registered) cutoffs for all cost element schedule reads so historical views remain truthful under the time-machine paradigm.
- **Why:** Prevents future-entered or late-created schedules from polluting historical metrics, aligning with EVM auditability requirements documented in `project_status.md`.
- **Next Steps:** Await stakeholder feedback on ambiguities above, then proceed to detailed planning (TDD) focusing first on a failing regression test (e.g., Budget Timeline API skipping schedules created after control date even if registration date is earlier).

---

**Pending Confirmation:** Please review and confirm (1) whether both timestamps must satisfy the cutoff, and (2) if any endpoints should intentionally expose future schedules regardless of control date. Once confirmed, I will prepare the detailed plan and failing tests per our working agreements.

---

## Decision Log (2025-11-15)

1. Implemented shared helper module `backend/app/services/time_machine.py` providing `end_of_day()` and `schedule_visibility_filters()` so routers/services reuse identical cutoff logic.
2. Budget Timeline, Planned Value, and Cost Element Schedule routers now rely exclusively on these helpers, removing bespoke `_end_of_day` copies and fallback schedule selection that previously surfaced future registrations.
3. Added targeted regression tests covering budget timeline responses, planned value calculation, and cost element schedule endpoints to confirm both `registration_date` and `created_at` must be ≤ control date; these tests guide the new filtering behavior.
