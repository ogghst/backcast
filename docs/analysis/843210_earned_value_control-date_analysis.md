# 843210 Earned Value Control-Date Filtering – High-Level Analysis

**Task:** Align earned value (EV) selection with the time-machine control date so entries respect both their completion date and their registration/creation timestamp, consistent with PRD §12.2 and the Sprint 3 control-date mandate in `docs/project_status.md`.

**Status:** Analysis Phase
**Date:** 2025-11-15
**Current Time:** 16:13 CET (Europe/Rome)

---

## User Story
As a project controls lead auditing historical performance, I need earned value summaries to include only those earned value entries that were both completed **and** registered on or before my selected control date so that EV, CPI, and downstream metrics reflect what the organization actually knew at that point in time. Earned value entries capture two distinct timestamps—`registration_date` (user-supplied) and `created_at` (system)—and both must satisfy the control-date filter before an entry becomes visible.

---

## 1. Codebase Pattern Analysis

1. **Earned value router filters solely by completion date.** `_select_entry_for_cost_element` and `_get_entry_map` constrain `completion_date <= control_date` but never consider when the entry was registered/created, enabling backdated entries to appear in historical snapshots.

```118:155:backend/app/api/routes/earned_value.py
@router.get("/{project_id}/earned-value/cost-elements/{cost_element_id}")
def get_cost_element_earned_value(...):
    entry = _select_entry_for_cost_element(
        session, cost_element.cost_element_id, control_date
    )
...
def _select_entry_for_cost_element(...):
    statement = (
        select(EarnedValueEntry)
        .where(EarnedValueEntry.cost_element_id == cost_element_id)
        .where(EarnedValueEntry.completion_date <= control_date)
        .order_by(
            EarnedValueEntry.completion_date.desc(),
            EarnedValueEntry.created_at.desc(),
        )
    )
```

2. **Service helper mirrors the same single-axis filter.** `_select_latest_entry_for_control_date` in `app/services/earned_value.py` only filters by `completion_date`, though it already leverages `created_at` for tie-breakers, signalling an established sorting convention we can extend to also enforce `registration_date` and `created_at <= end_of_day(control_date)`.

```26:56:backend/app/services/earned_value.py
def _select_latest_entry_for_control_date(entries, control_date):
    valid_entries = [
        entry for entry in entries if entry.completion_date <= control_date
    ]
    ...
    valid_entries.sort(key=lambda e: (e.completion_date, e.created_at), reverse=True)
```

3. **Time-machine aware tests exist but lack dual-date coverage.** `test_get_earned_value_cost_element_uses_time_machine` validates control-date persistence yet doesn’t seed scenarios where `created_at > control_date`, leaving a gap for the new requirement.

```377:420:backend/tests/api/routes/test_earned_value.py
def test_get_earned_value_cost_element_uses_time_machine(...):
    control_date = date(2024, 2, 20)
    create_earned_value_entry(... completion_date=control_date ...)
    set_time_machine_date(client, superuser_token_headers, control_date)
    response = client.get(.../earned-value/cost-elements/...)
    assert response.status_code == 200
```

**Architectural layers to respect**
- FastAPI routers (`backend/app/api/routes/`) resolve control date via `get_time_machine_control_date`.
- Service/helper modules (`backend/app/services/earned_value.py`) encapsulate selection and aggregation logic.
- SQLModel schemas under `backend/app/models/` maintain Base/Create/Update/Public parity.
- Frontend EV summaries (`frontend/src/components/Projects/EarnedValueSummary.tsx`) expect backend-calculated values and should remain free of client-side filtering.

---

## 2. Integration Touchpoint Mapping

- **Backend**
  - `app/api/routes/earned_value.py`: add both `registration_date <= control_date` and `created_at <= end_of_day(control_date)` filters when selecting entries for cost elements, WBEs, and projects, ensuring late-entered entries only surface after their actual registration.
  - `app/services/earned_value.py`: update `_select_latest_entry_for_control_date` (used by unit tests and any future batch loaders) to mirror router behavior or delegate to a shared selector helper enforcing all three predicates.
  - `app/models/earned_value_entry.py`: document the dual-timestamp semantics (user-provided registration date vs. system `created_at`) to guide future contributors.
  - `tests/api/routes/test_earned_value.py` and `tests/services/test_earned_value.py`: introduce failing cases where completion date qualifies but `created_at` does not, ensuring TDD compliance.
  - `tests/utils/earned_value_entry.py`: may need optional override for `created_at` to simulate late entry creation.

- **Frontend**
  - `frontend/src/components/Projects/EarnedValueSummary.tsx` and related TanStack queries: no logic change anticipated, but update expectations in Unit/Playwright tests once backend responses shift.

- **Configuration & dependencies**
  - Time-machine persistence (per PLA-2) remains authoritative; new logic must continue using `TimeMachineControlDate` rather than ad-hoc query params.
  - Because `registration_date` and `created_at` are distinct, rewinding the control date should reveal late-entered EV records only after the control date surpasses both timestamps; earlier snapshots must hide them.

---

## 3. Abstraction Inventory

- **Time-machine DI:** `get_time_machine_control_date` already supplies the effective control date to every router—extend its use rather than introducing new parameters.
- **Selector helpers:** `_select_entry_for_cost_element`, `_get_entry_map`, and `_select_latest_entry_for_control_date` are natural homes for the dual-date predicate; we should avoid duplicating SQL fragments.
- **Testing utilities:** `set_time_machine_date` plus `create_earned_value_entry` expedite TDD, though we might need a helper to backfill `created_at` to simulate late registrations.
- **Frontend presentation layer:** `EarnedValueSummary` and aggregated cards reuse a single API client; keeping server-side enforcement prevents cascading UI changes.

---

## 4. Alternative Approaches

| Approach | Summary | Pros | Cons/Risks | Architectural Alignment | Est. Complexity |
| --- | --- | --- | --- | --- | --- |
| **A. Router-level triple filter (Recommended)** | Update earned value selectors to require `completion_date <= control_date`, `registration_date <= control_date`, **and** `created_at <= end_of_day(control_date)` before returning entries. | Minimal surface area, aligns with Cost Element Schedule precedent, limited to backend and tests. | Must audit every selector to prevent inconsistent behavior; needs data migration only if we discover missing timestamps. | High – mirrors PLA-1 schedule filtering strategy. | Medium |
| **B. Shared query helper/service** | Introduce a centralized helper (e.g., `select_latest_ev_entry(cost_element_id, control_date)`) that applies all three predicates and reuse it across routers and services. | Single source of truth, easier future reuse for CPI/SPI. | Requires refactoring existing helper call sites; potential churn if helper spans sync + async contexts. | High – encourages abstraction reuse. | Medium-High |
| **C. Historical snapshot table** | Persist per-control-date EV snapshots when users create entries, so runtime filtering becomes a simple lookup. | Guarantees historical fidelity, accelerates queries for dashboards. | Significant schema expansion, snapshot lifecycle complexity, violates “incremental change” agreement for current sprint. | Low – diverges from current just-in-time calculation model. | High |

---

## 5. Architectural Impact Assessment

- **Principles upheld:** Enforcing dual-date cutoffs reinforces the “time machine” architecture noted in `docs/project_status.md` (PLA-1) and honors PRD §12.2’s requirement for auditable EV metrics.
- **Potential violations:** If only the EV APIs adopt the filter while other EV consumers (future CPI/SPI services) remain untouched, we risk divergent results. Centralizing the filter or documenting the invariant is essential.
- **Maintenance considerations:** Approach B marginally increases upfront work but reduces drift risk. Regardless, document the dual-date rule in `EarnedValueEntry` schema docstrings and developer docs to guide future contributors.
- **Testing challenges:** We need fixtures that manipulate `completion_date`, `registration_date`, and `created_at` independently; ensuring deterministic timestamps in tests (e.g., via freezer or manual overrides) is crucial.

---

## Summary & Next Steps

- **What:** Bring earned value selection in line with time-machine expectations by ensuring entries must satisfy completion-date, registration-date, and created-at cutoffs before contributing to EV totals.
- **Why:** Prevents late-entered progress updates from retroactively changing historical CPI/SPI calculations, preserving the auditability promised in the PRD and sprint status documents.
- **Next Steps:**
  1. Draft failing tests covering late-registered entries (e.g., `registration_date` backdated but `created_at` after control date) at cost element, WBE, and project levels.
  2. Update factories/utilities so tests can override all three timestamps deterministically.
  3. Implement the triple-cutoff filter via either router hardening (Approach A) or a shared helper (Approach B), reusing PLA-1 time-machine utilities and guaranteeing rewinds surface late entries only after both timestamps.

---

## Risks, Unknowns, and Ambiguities

- **Registration date definition:** Confirmed that `registration_date` already exists and must remain distinct from `created_at`; both need enforcement.
- **Data backfill:** Existing entries created after their completion date will begin disappearing from historical snapshots once filters tighten—confirm whether this is acceptable or whether we need migration scripts to adjust timestamps.
- **Performance:** Additional predicates may require new composite indexes on `(cost_element_id, completion_date, created_at)` to keep aggregations responsive for large projects.
- **Downstream dependencies:** Upcoming EVM performance indices (E4-003/E4-004) will consume EV data; ensure their planned implementations anticipate the stricter selection logic.

---

**Pending Confirmation:** Clarifications captured—`registration_date` differs from `created_at`, and late-entered EV records should only appear once the control date advances past both timestamps. Proceeding to detailed planning with these invariants.
