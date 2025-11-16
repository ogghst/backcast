# 572184 Cost Registration Time-Machine Filtering – High-Level Analysis

**Task:** Extend the global time-machine rules (control date + dual timestamps) to cost registrations so historical cost reports only surface transactions the organization had actually recorded at that time, consistent with PRD §6.2 and the PLA-1 control-date mandate.

**Status:** Analysis Phase
**Date:** 2025-11-15
**Current Time:** 17:05 CET (Europe/Rome)

---

## User Story
As a project controller reviewing historical cost performance, I need cost registrations, cost summaries, and cost timelines to exclude any transactions entered after my selected control date—unless the records were already registered (both operationally and in the system) by that date—so Actual Cost, CV, CPI, and downstream analytics remain historically accurate.

---

## 1. Codebase Pattern Analysis

1. **Cost registration listing endpoint (`/cost-registrations/`).** Currently filters only by `registration_date <= control_date` when fetching/paginating records; `created_at` is ignored, meaning late-entered costs with backdated registration dates still appear in historical snapshots.

```152:199:backend/app/api/routes/cost_registrations.py
statement = (
    select(CostRegistration)
    .where(CostRegistration.registration_date <= control_date)
    .order_by(...)
)
```

2. **Cost timeline & summary routes.** Endpoints such as `cost_timeline.py` and `cost_summary.py` aggregate Actual Cost for charts/cards but rely on the same registration-date-only filter before rolling up amounts; they do not clamp by `created_at`, leaving the same loophole.

3. **Shared time-machine helpers exist.** `app/services/time_machine.py` already exposes `schedule_visibility_filters` plus the new `earned_value_visibility_filters`; this is the natural place to define a `cost_registration_visibility_filters` helper so routers/services stay consistent.

**Architectural layers to respect**
- FastAPI routers in `backend/app/api/routes/` orchestrate dependencies and use `get_time_machine_control_date`.
- Service/helper utilities (time_machine module, potential cost aggregation helpers) encapsulate common predicates.
- SQLModel schemas keep Base/Create/Update/Public parity; no schema change needed because CostRegistration already stores `registration_date` and timestamps.
- Frontend components fetch server-filtered data; no client-side date filtering should creep in.

---

## 2. Integration Touchpoint Mapping

- **Backend routers & services**
  - `app/api/routes/cost_registrations.py`: list endpoint, detail fetches, and any new helper functions should reuse a shared filter ensuring `registration_date <= control_date` **and** `created_at <= end_of_day(control_date)`.
  - `app/api/routes/cost_timeline.py`, `cost_summary.py`, `cost_history` components: update underlying queries to include the same predicate before aggregating amounts.
  - `app/services/cost_summary.py` (if present) and any `crud` helpers touching cost registrations should compose the shared filter to prevent drift.
  - `app/tests/...`: extend pytest coverage in `test_cost_registrations.py`, `test_cost_timeline.py`, and `test_cost_summary.py` with scenarios where registration_date passes but created_at fails (and vice versa).

- **Frontend**
  - Should not require changes if backend enforces filtering, but update Playwright regression (e.g., `project-cost-element-tabs.spec.ts`) if assertions depend on total counts.

- **Config/DI**
  - Keep using `TimeMachineControlDate`; no new query params. Consider factoring additional helpers into `time_machine.py` for other entry types later (quality events, forecasts).

---

## 3. Abstraction Inventory

- **Existing helpers:** `schedule_visibility_filters` and `earned_value_visibility_filters` illustrate the pattern—centralized predicate builder returning SQLAlchemy filters for routers to splat into queries.
- **Time-machine dependency injection:** `get_time_machine_control_date` ensures every route receives the control date implicitly, so adding helpers won’t change signatures.
- **Testing utilities:** `tests/utils/cost_registration.py` already lets us create registrations with arbitrary `registration_date`; we can extend it to override `created_at` for deterministic late-entry scenarios.
- **Aggregators:** Cost summary/timeline services already abstract some logic; aligning them to a shared helper reduces duplication.

---

## 4. Alternative Approaches

| Approach | Summary | Pros | Cons/Risks | Architectural Alignment | Est. Complexity |
| --- | --- | --- | --- | --- | --- |
| **A. Router/service hardening (Recommended)** | Introduce `cost_registration_visibility_filters` mirroring the EV helper and apply it everywhere cost registrations are queried/aggregated. | Minimal surgery; consistent with PLA-1 pattern; no schema change. | Must audit all endpoints to avoid missing a path; requires test updates across cost timeline/summary suites. | High – reuse existing helper architecture. | Medium |
| **B. Centralized materialized view** | Create a DB view exposing only control-date-compliant cost registrations and point all queries at it. | Single source inside DB; potential perf gain. | Requires per-control-date parameterization (hard in Postgres views), complicates migrations and tests. | Low – deviates from code-level filtering pattern. | High |
| **C. Event snapshotting** | Persist control-date snapshots of Actual Cost whenever costs change. | Fast reads, historical immutability. | Significant scope creep: new tables, snapshot lifecycle, heavy migrations. | Low – beyond current sprint goals. | Very High |

---

## 5. Architectural Impact Assessment

- **Principles upheld:** Approach A keeps the “shared helper per event type” rule, reinforcing architectural consistency and minimizing duplicated SQL fragments.
- **Potential violations:** Partial rollout (e.g., only list endpoint updated) would create inconsistent totals across reports; thorough test coverage plus helper reuse mitigates this.
- **Maintenance burden:** Adding the helper now makes it easier to onboard future event types (quality events, forecasts). Documenting the triad (business date + system timestamp) in developer docs will guide other teams.
- **Testing challenges:** Need deterministic creation timestamps in tests; may require manual overrides or a helper to update `created_at` post-insert.

---

## Summary & Next Steps

- **What:** Enforce both registration date and system creation timestamp cutoffs for all cost registration reads/aggregations so Actual Cost respects the time machine.
- **Why:** Prevents late-entered costs from polluting historical metrics, keeping AC, CV, CPI, and quality-cost analytics trustworthy.
- **Next Steps:**
  1. Update `tests/utils/cost_registration.py` to override `created_at`.
  2. Write failing tests in `test_cost_registrations.py`, `test_cost_timeline.py`, and `test_cost_summary.py` that demonstrate current leakage.
  3. Add `cost_registration_visibility_filters` to `time_machine.py` and apply it across routers/services.
  4. Rerun targeted pytest suites and Playwright regression if applicable.

---

## Risks & Unknowns

- **Performance:** Additional predicates may require an index on `(cost_element_id, registration_date, created_at)`; evaluate once implemented.
- **Backfill:** Existing data already has both dates, but some legacy records may have identical timestamps; confirm we don’t need data cleanup.
- **Other event types:** Quality events/forecasts still lack helper coverage; consider planning follow-up analyses to extend the pattern further.

---

## Pending Confirmation
- None currently; requirements align with PRD §6.2 and prior PLA guidance. Will proceed to detailed planning once this analysis is approved.
