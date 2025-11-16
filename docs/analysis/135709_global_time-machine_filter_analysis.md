# 135709 Global Time-Machine Filtering Helper – High-Level Analysis

**Task:** Consolidate all control-date filtering logic (schedules, earned value, cost registrations, and future event types) behind a single set of reusable helpers so we can adjust time-machine behavior centrally without touching every router/service.

**Status:** Analysis Phase
**Date:** 2025-11-15
**Current Time:** 17:18 CET (Europe/Rome)

---

## User Story
As a platform maintainer responsible for the time-machine feature, I need a centralized way to apply control-date visibility rules to any event/query so that when requirements evolve (e.g., adding “show future entries” or softening cutoffs), I can update one place and have the entire application respect the new behavior automatically.

---

## 1. Codebase Pattern Analysis

1. **Current helpers live in `app/services/time_machine.py`.** We already have `schedule_visibility_filters` and `earned_value_visibility_filters`, and we just proposed `cost_registration_visibility_filters`. Each returns a tuple of SQLAlchemy expressions, but routers manually splat them into queries, leading to boilerplate.

2. **Routers/services apply filters ad hoc.** Examples:
   - `budget_timeline.py`, `planned_value.py`, `cost_element_schedules.py` call `schedule_visibility_filters`.
   - `earned_value.py` now imports `earned_value_visibility_filters`.
   - Cost-related routes still inline `registration_date <= control_date`.
   This patchwork increases the chance of missing a query and makes behavior changes tedious.

3. **No shared “query decorator.”** Beyond returning tuples, nothing enforces their usage or makes it easy to compose additional behaviors (e.g., auditing, logging, future toggles).

**Architectural layers to respect**
- FastAPI routers + service modules should remain thin and declare intent, not reimplement filtering.
- SQLModel/SQLAlchemy queries must stay composable; helpers should return expression lists or callables we can pass to `.where(...)`.
- Test suites rely on deterministic filtering; centralizing must preserve testability (e.g., ability to patch helper functions).

---

## 2. Integration Touchpoint Mapping

- **Backend modules needing the helper abstraction**
  - `app/api/routes/*`: cost registrations, cost timeline, cost summary, earned value, planned value, baseline log creation, etc.
  - `app/services/*`: PV/EV services, timeline builders, summary aggregators.
  - Future event modules (quality events, forecasts, change orders) will benefit from a pluggable approach.

- **Infrastructure**
  - `app/services/time_machine.py`: ideal home for a small utility (e.g., `def visibility_filters(model: type[BaseModel])`) and/or wrappers that accept a SQLModel class + control date and return expressions.
  - Consider a higher-level helper like `apply_time_machine_filters(query, event_kind, control_date)` to avoid repeating `.where(*filters)` everywhere.

- **Testing**
  - Unit tests should patch the helper to assert routes use it. Integration tests verify behavior by setting control dates and seeding data with mismatched timestamps.

---

## 3. Abstraction Inventory

- **Current building blocks:** Tuple-based filter helpers already exist for specific models; we can generalize them via:
  - An enum or string key (`"schedule"`, `"earned_value"`, `"cost_registration"`) mapping to filter factories.
  - A `TimeMachineFilter` protocol encapsulating `filters(control_date)` + optional `order_by` hints.
- **Shared dependencies:** `get_time_machine_control_date`, `end_of_day()` utilities.
- **Testing utilities:** Factories across tests (schedule, EV, cost registration) already let us override timestamps—critical for verifying central helper usage.

---

## 4. Alternative Approaches

| Approach | Summary | Pros | Cons/Risks | Alignment | Complexity |
| --- | --- | --- | --- | --- | --- |
| **A. Central registry (Recommended)** | Define a registry/dict that maps event types to filter factories; expose helper functions like `apply_time_machine_filters(query, event_type, control_date)`. | Keeps logic DRY; adding new event types is trivial; routers stay declarative. | Need disciplined naming; risk of over-abstracting if not documented. | High – extends existing helper module cleanly. | Medium |
| **B. Decorator/middleware layer** | Wrap DB calls via context managers that automatically inject filters based on model metadata. | Very DRY; minimal router changes once set up. | Harder to reason about; may conflict with complex queries or joins; debugging more difficult. | Medium – novel pattern, might surprise devs. | Medium-High |
| **C. ORM mixins** | Add mixins/SQLModel base classes that automatically include filters when queried. | Model-driven approach. | SQLModel doesn’t easily support per-query auto-filtering without custom session instrumentation; high risk. | Low – deviates from current query patterns. | High |

---

## 5. Architectural Impact Assessment

- **Principles upheld:** Approach A keeps the architecture predictable, respects TDD, and promotes reuse. Routers/services remain slim and express filtering intent via a single call.
- **Future adjustments:** Want to allow “include future entries” for certain role? Flip logic inside one registry function. Need to track audit logs? Wrap `apply_time_machine_filters` to log event types used.
- **Testing & maintainability:** Registry makes it easy to stub out specific event-type filters for tests. Risk is forgetting to register a new event type—mitigated by requiring explicit event keys and adding linter/test coverage.

---

## Summary & Next Steps

- **What:** Introduce a centralized time-machine filter registry + helper function to apply filters uniformly across routers/services.
- **Why:** Adjusting historical visibility should be a one-line change, not a repo-wide refactor; ensures consistent behavior for all event types.
- **Next Steps:**
  1. Design registry interface (`Enum` or literal strings + typed factory functions).
  2. Update `time_machine.py` to expose `apply_time_machine_filters(query, event_type, control_date)` plus existing filter builders migrated into the registry.
  3. Refactor key routers/services (schedules, EV, cost registrations, cost timeline/summary) to use the helper.
  4. Add regression tests verifying helper invocation and behavior.

---

## Risks & Unknowns

- **Refactor scope:** Touches multiple routers; should plan incremental commits per event type to avoid huge diffs.
- **Event-specific nuances:** Some modules may need additional predicates (e.g., baseline_id null checks); helper must allow extra `.where(...)` chaining.
- **Documentation:** Need to document the registry pattern in developer docs so new contributors register their event type filters.

---

## Pending Confirmation
- None; concept aligns with existing architecture and the request to make time-machine adjustments easier. Ready to move into detailed planning when you give the go-ahead.
