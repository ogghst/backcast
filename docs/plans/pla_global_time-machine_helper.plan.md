# Global Time-Machine Helper – Detailed Plan

**Status:** Planning
**Date:** 2025-11-15
**Scope:** Centralize control-date filtering across schedules, earned value, cost registrations (initial wave), and set the foundation for future event types.

---

## Objectives
1. Provide a single registry-based helper that maps event types to their control-date filter logic (registration date + created_at, etc.).
2. Update existing consumers (schedules, earned value, cost registrations, cost timeline/summary) to apply the helper rather than manual predicates.
3. Maintain TDD discipline: failing tests first for each consumer, then implementation.
4. Keep commits small (<100 LOC, ≤5 files).

---

## High-Level Design
- **Registry pattern:** In `app/services/time_machine.py`, introduce:
  - `TimeMachineEventType` enum (e.g., `SCHEDULE`, `EARNED_VALUE`, `COST_REGISTRATION`).
  - `VISIBILITY_FILTERS` dict mapping enum values to callables returning tuples of SQLAlchemy expressions.
  - `get_visibility_filters(event_type, control_date)` utility.
- **Query helper:** Provide `apply_time_machine_filters(statement, event_type, control_date)` that appends the filters to a SQLModel/SQLAlchemy Select. This keeps routers clean and makes future behavior changes centralized.
- **Extensibility:** Document how to register new event types and optionally pass custom filters (e.g., baseline-specific logic).

---

## Implementation Phases (TDD)

### Phase 1 – Infrastructure & Unit Tests
1. Update `time_machine.py`:
   - Define `TimeMachineEventType` and registry.
   - Move existing schedule/EV filters into registry entries.
   - Add cost registration filters (completion/registration/created_at).
   - Implement `get_visibility_filters` + `apply_time_machine_filters`.
2. Add unit tests for the helper (e.g., `tests/services/test_time_machine.py`) verifying:
   - Each event type returns expected expressions.
   - Applying filters produces combined predicates.
   - Unknown event types raise/detect errors.

### Phase 2 – Earned Value Refactor
1. Write failing tests (if needed) ensuring `apply_time_machine_filters` is invoked.
2. Update `earned_value.py` to call the new helper instead of importing event-specific functions.
3. Ensure service-level helper `_select_latest_entry_for_control_date` reuses `get_visibility_filters`.

### Phase 3 – Schedule Refactor
1. Identify all routers/services using `schedule_visibility_filters` (budget timeline, planned value, schedule CRUD, baseline log copy).
2. Write a targeted failing test (e.g., patch helper to ensure invocation) if practical.
3. Replace direct helper usage with `apply_time_machine_filters(..., TimeMachineEventType.SCHEDULE, control_date)` to demonstrate uniform pattern.

### Phase 4 – Cost Registration & Aggregations
1. Extend cost registration factories/tests to override `created_at` (from earlier analysis).
2. Write failing tests in `test_cost_registrations.py`, `test_cost_timeline.py`, `test_cost_summary.py` showing late-entered records still appear.
3. Update routers/services to call the centralized helper for `TimeMachineEventType.COST_REGISTRATION`.
4. Ensure cost summary/timeline queries share a helper or service for reuse.

### Phase 5 – Cleanup & Documentation
1. Remove any now-redundant helper imports.
2. Update developer docs (e.g., `docs/project_status.md` or a new section) explaining how to register new event types.
3. Re-run targeted pytest suites (`test_time_machine.py`, EV tests, schedule tests, cost registration/timeline/summary tests).
4. Optional: add a lint/test guard ensuring every event type has tests (e.g., `assert TimeMachineEventType` coverage).

---

## Testing Strategy
- **Unit tests:** `tests/services/test_time_machine.py` covering registry behavior.
- **API tests:** EV, schedule, cost registration endpoints for regression.
- **Service/aggregation tests:** cost timeline/summary, planned value, etc.
- **Optional integration:** Playwright tests to ensure UI reflects control-date filtering post-refactor.

---

## Risks & Mitigations
- **Missed touchpoints:** Keep a checklist of routes/services referencing `*_visibility_filters` or manual predicates; refactor each systematically.
- **Regression in query composition:** Ensure the helper returns expressions compatible with `.where(*filters)`; add type hints to catch misuse.
- **Complex event types:** For future events needing extra logic (e.g., baseline_id), allow routers to pass additional `.where(...)` after applying the helper.

---

## Next Steps
1. Execute Phase 1 (registry + helper + unit tests) with failing tests first.
2. Proceed event-by-event (EV → schedules → cost registrations) as separate incremental commits to keep diffs small.
