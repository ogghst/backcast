# PLA-1 Earned Value Control-Date Filtering – Detailed Plan

**Status:** Planning
**Date:** 2025-11-15
**Control Date Context:** Time-machine dependent (session-level per PLA-2)
**Related Analysis:** `docs/analysis/843210_earned_value_control-date_analysis.md`

---

## Objective
Ensure earned value (EV) calculations respect the global time-machine control date by requiring every EarnedValueEntry included in aggregates to satisfy **three** cutoffs:

1. `completion_date <= control_date`
2. `registration_date <= control_date` (user-entered timestamp)
3. `created_at <= end_of_day(control_date)` (system registration timestamp)

Late-entered entries should appear only after the control date surpasses *both* registration markers, preserving historical fidelity for CPI/SPI and downstream EVM metrics.

---

## Scope & Non-Goals
- **In scope:** Backend EV selection logic, supporting helpers, factories/test utilities, automated tests (API + service-level).
- **Out of scope:** Frontend changes (responses should naturally reflect backend updates), CPI/SPI calculations (future epics), database migrations (existing fields suffice).

---

## Assumptions & Open Questions
- `registration_date` already exists on `EarnedValueEntry` (user-provided) and differs from `created_at`.
- No need to expose additional query params; control date remains implicit via `TimeMachineControlDate` dependency.
- Rewinding the control date should reveal late-entered EV entries only after both timestamps are within the cutoffs; no special override for “show future registrations”.

---

## Architectural Alignment
- Mirrors PLA-1 schedule filtering approach by sharing helper utilities (likely via `app/services/time_machine.py` or a new EV-specific selector) to avoid duplication.
- Maintains FastAPI DI for control date, SQLModel patterns for querying, and existing aggregation flow (cost element → WBE → project).
- Upholds TDD, incremental change (<100 LOC, ≤5 files per commit), and ensures any production code change is paired with tests.

---

## Implementation Phases (TDD)

### Phase 1 – Test Fixtures & Utilities
1. Extend `tests/utils/earned_value_entry.py` to optionally override `registration_date` and `created_at`.
2. Add helper for freezing `created_at` deterministically (e.g., manual assignment post-creation with session refresh or patching default).
3. No production changes yet; ensure tests can craft late-entered entries.

### Phase 2 – API-Level Failing Tests
1. Update `backend/tests/api/routes/test_earned_value.py` with scenarios:
   - Entry with `completion_date` & `registration_date` ≤ control date but `created_at` after control date → should be excluded.
   - Entry with `completion_date` ≤ control date but `registration_date` after control date (even if `created_at` earlier) → excluded.
   - Entry with all three ≤ control date → included (control case).
2. Cover cost-element endpoint plus aggregated WBE/project responses to ensure rollups respect filtering.
3. Run tests; confirm failures (RED).

### Phase 3 – Service-Level Failing Tests (Optional if covered)
1. If `app/services/earned_value.py` helpers are unit tested separately, add failing tests to `backend/tests/services/test_earned_value.py` verifying `_select_latest_entry_for_control_date` enforces the triple cutoff when supplied with entries containing the new fields.
2. If not previously present, create targeted tests around the helper to guide refactor.

### Phase 4 – Production Implementation
1. Introduce shared predicate builder (either extend `app/services/time_machine.py` or add EV-specific helper) returning SQLAlchemy filters:
   - `EarnedValueEntry.registration_date <= control_date`
   - `EarnedValueEntry.created_at <= end_of_day(control_date)`
2. Update `_select_entry_for_cost_element` and `_get_entry_map` in `app/api/routes/earned_value.py` to apply new filters.
3. Update `_select_latest_entry_for_control_date` in `app/services/earned_value.py` to enforce the same rules when filtering in Python.
4. Document the invariant in `EarnedValueEntryBase` docstring if needed.

### Phase 5 – Test Pass & Cleanup
1. Re-run relevant pytest suites (targeted files first, then broader if feasible).
2. Verify no regressions, lints, or formatting issues.
3. Update documentation/changelog if required (e.g., note in `docs/project_status.md` or PLA-1 completion log).
4. Remove any temporary helpers introduced solely for testing if unnecessary.

---

## Testing Strategy
- **Unit Tests:**
  - New scenarios in `test_earned_value.py` covering cost-element/WBE/project endpoints.
  - Helper/service tests verifying selection behavior for mixed timestamp combinations.
- **Integration Tests:** Existing API tests act as integration coverage; ensure time-machine fixtures are employed.
- **Regression:** Run `python -m pytest backend/tests/api/routes/test_earned_value.py backend/tests/services/test_earned_value.py`.
- **Manual sanity (if needed):** Hit EV endpoints with crafted data to ensure time-machine filtering works, though automated tests should suffice.

---

## Risks & Mitigations
- **Complex timestamp manipulation in tests:** Use explicit datetime assignments to avoid timezone flakiness; rely on UTC-aware datetimes.
- **Performance impact from extra filters:** Evaluate query plans; add composite index if profiling reveals regressions (future work).
- **Partial adoption risk:** Ensure every EV selector (cost element, WBE, project) uses the shared helper to prevent drift; add tests covering each aggregation level.

---

## Exit Criteria
- All new tests (API + service) pass and fail appropriately before implementation.
- Earned value endpoints exclude entries violating any of the three cutoffs.
- Documentation updated (analysis linked to plan completion in project status if needed).

---

**Next Action:** Execute Phase 1 by updating test utilities and writing failing tests (RED) before touching production code, adhering to the working agreements.
