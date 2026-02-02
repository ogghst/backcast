# Plan: EVM Foundation Implementation

**Created:** 2026-01-18
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 - Dedicated ProgressEntry Model with EVM Service

---

## Scope & Success Criteria

### Approved Approach Summary

**Selected Option:** Option 1 - Dedicated Progress Tracking Model with EVM Service

**Architecture:**
- New `ProgressEntry` model (versionable, not branchable) for tracking % complete over time
- New `ProgressEntryService` inheriting from `TemporalService[ProgressEntry]`
- New `EVMService` for orchestrating EVM metric calculations with time-travel support
- Extended `CostRegistrationService` with period-based aggregations
- API endpoints for progress CRUD and EVM metrics queries

**Key Stakeholder Decisions:**
1. **Progress Granularity**: Per cost element (leaf-level tracking)
2. **Progress Validation**: Can decrease but requires warning + justification before submit
3. **Progress Frequency**: Multiple times per day allowed (no restrictions)
4. **EVM Metric Behavior**: When no progress reported, return EV = 0 with warning message
5. **Cost Aggregation Periods**: All three (daily, weekly, monthly)
6. **Performance Optimization**: Database-level aggregations (custom SQL with GROUP BY)

### Success Criteria

**Functional Criteria:**

- [ ] Progress entry creation validates percentage is 0-100 range VERIFIED BY: Unit test with invalid inputs
- [ ] Progress can be updated (increased or decreased) with validation warnings VERIFIED BY: Integration test for progress updates
- [ ] Progress history is queryable via `get_progress_history()` VERIFIED BY: Integration test with multiple entries
- [ ] Progress queries support time-travel (`as_of` parameter) VERIFIED BY: Integration test with historical timestamps
- [ ] EVM metrics calculation returns BAC, PV, AC, EV, CV, SV, CPI, SPI VERIFIED BY: Unit test for complete metric set
- [ ] EVM metrics support time-travel queries (control_date parameter) VERIFIED BY: Integration test with historical dates
- [ ] EVM metrics return EV = 0 with warning when no progress reported VERIFIED BY: Unit test for null progress case
- [ ] Cost aggregations support daily, weekly, monthly periods VERIFIED BY: Unit test for each period type
- [ ] Cost aggregations respect time-travel (as_of parameter) VERIFIED BY: Integration test with control dates
- [ ] All progress and cost data respects bitemporal versioning VERIFIED BY: Integration test for version history

**Technical Criteria:**

- [ ] Performance: EVM calculations complete within 500ms for standard queries VERIFIED BY: Performance benchmark test
- [ ] Database: Progress entries table has proper indexes (cost_element_id, reported_date, progress_entry_id) VERIFIED BY: Migration inspection
- [ ] Database: GIST indexes for TSTZRANGE range queries VERIFIED BY: Migration inspection
- [ ] Code Quality: MyPy strict mode (zero errors) VERIFIED BY: CI pipeline
- [ ] Code Quality: Ruff linting (zero errors) VERIFIED BY: CI pipeline
- [ ] Test Coverage: 80%+ for all new services and models VERIFIED BY: Coverage report
- [ ] Async/await: All database operations use async session VERIFIED BY: Code review

**Business Criteria:**

- [ ] Project managers can track progress on cost elements VERIFIED BY: User acceptance test
- [ ] EVM metrics enable performance measurement (CPI, SPI) VERIFIED BY: User acceptance test
- [ ] Historical progress analysis supported via time-travel VERIFIED BY: User acceptance test
- [ ] Cost tracking supports cumulative and period-based views VERIFIED BY: User acceptance test

### Scope Boundaries

**In Scope:**

- ProgressEntry model with bitemporal versioning
- ProgressEntryService with CRUD and time-travel operations
- EVMService with metrics calculation (BAC, PV, AC, EV, CV, SV, CPI, SPI)
- Extended CostRegistrationService with period-based aggregations
- API endpoints for progress entries and EVM metrics
- Database migrations for progress_entries table
- Unit tests, integration tests, and API tests
- Documentation updates (API docs, architecture updates)

**Out of Scope:**

- Frontend UI components (deferred to future iteration)
- Advanced EVM features (forecasting, change order impact analysis)
- Automated progress calculation (manual entry only)
- Progress approval workflows
- Real-time EVM dashboard
- Cost registration modifications (CRUD already exists)
- Schedule baseline modifications (1:1 relationship already implemented)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                                 | Files                                                                                              | Dependencies     | Success Criteria                                                                                                                                                                                                                      | Complexity   |
| --- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| 1   | Create ProgressEntry domain model                                   | `backend/app/models/domain/progress_entry.py`                                                      | None             | Model compiles, has VersionableMixin, all fields defined (progress_entry_id, cost_element_id, progress_percentage, reported_date, reported_by_user_id, notes), proper constraints (0-100 range, required fields)                      | Low          |
| 2   | Create Alembic migration for progress_entries table                 | `backend/alembic/versions/YYYYMMDD_HHMMSS_create_progress_entries.py`                              | Task 1           | Migration applies successfully, table created with TSTZRANGE columns, indexes on cost_element_id, reported_date, progress_entry_id, GIST indexes for range queries                                                                      | Low          |
| 3   | Create ProgressEntry Pydantic schemas                               | `backend/app/models/schemas/progress_entry.py`                                                      | Task 1           | Schemas defined: ProgressEntryBase, ProgressEntryCreate, ProgressEntryUpdate, ProgressEntryRead, proper validation for progress_percentage (0-100), all fields included                                                             | Low          |
| 4   | Create ProgressEntryService with CRUD operations                    | `backend/app/services/progress_entry_service.py`                                                    | Task 1, 3        | Service inherits TemporalService[ProgressEntry], create() method with validation, get_latest_progress() method, get_progress_history() method, all methods async, proper error handling                                               | Medium       |
| 5   | Create progress entries API routes                                  | `backend/app/api/routes/progress_entries.py`                                                        | Task 3, 4        | Routes: POST /progress-entries, GET /progress-entries/{id}, GET /progress-entries, DELETE /progress-entries/{id}, proper dependency injection, request validation, response schemas                                                  | Medium       |
| 6   | Register progress routes in API router                              | `backend/app/api/routes/__init__.py`                                                                | Task 5           | Progress routes accessible via `/api/v1/progress-entries`, OpenAPI docs include new endpoints                                                                                                                                          | Low          |
| 7   | Write unit tests for ProgressEntry model                            | `backend/tests/unit/models/test_progress_entry.py`                                                  | Task 1           | Tests for field validation, constraints, defaults, model instantiation, test coverage ≥80%                                                                                                                                            | Low          |
| 8   | Write unit tests for ProgressEntryService                           | `backend/tests/unit/services/test_progress_entry_service.py`                                       | Task 4           | Tests for create() (happy path, invalid percentage, negative percentage >100), get_latest_progress() (with/without as_of), get_progress_history() (ordered by date), test coverage ≥80%                                            | Medium       |
| 9   | Write API integration tests for progress entries                    | `backend/tests/api/test_progress_entries.py`                                                        | Task 5, 6        | Tests for POST/GET/DELETE endpoints, validation error responses, time-travel queries, async operations, test coverage ≥80%                                                                                                           | Medium       |
| 10  | Write time-travel integration tests for progress                    | `backend/tests/integration/test_progress_time_travel.py`                                            | Task 4           | Tests for get_latest_progress() with historical as_of, version history queries, bitemporal filtering, transaction_time vs valid_time semantics                                                                                       | High         |
| 11  | Create EVMService orchestrator class                                | `backend/app/services/evm_service.py`                                                               | Task 4           | EVMService class with __init__ (injects all required services), calculate_evm_metrics() method signature, proper async/await, dependency injection for all services                                                                    | Medium       |
| 12  | Implement EVM metrics calculation core logic                        | `backend/app/services/evm_service.py` (extend)                                                      | Task 11          | _get_bac_as_of() returns cost_element.budget_amount, _get_pv_as_of() calls ScheduleBaselineService.get_for_cost_element() + progression strategy, _get_ac_as_of() calls CostRegistrationService.get_total_for_cost_element() | Medium       |
| 13  | Implement EV calculation with progress lookup                       | `backend/app/services/evm_service.py` (extend)                                                      | Task 12          | _get_ev_as_of() calls ProgressEntryService.get_latest_progress(), returns BAC × progress_percentage / 100, returns 0 with warning if no progress                                                                                       | Medium       |
| 14  | Implement variance and index calculations                           | `backend/app/services/evm_service.py` (extend)                                                      | Task 13          | _calculate_variances() returns CV = EV - AC, SV = EV - PV, _calculate_indices() returns CPI = EV / AC, SPI = EV / PV, handles division by zero (AC = 0 or PV = 0)                                                                      | Medium       |
| 15  | Create EVMMetricsRead schema                                       | `backend/app/models/schemas/evm.py`                                                                 | Task 11          | Schema with all EVM metrics (bac, pv, ac, ev, cv, sv, cpi, spi), metadata fields (control_date, version_ids, timestamps), proper Decimal types for currency                                                                       | Low          |
| 16  | Add EVM metrics endpoint to cost elements routes                    | `backend/app/api/routes/cost_elements.py` (extend)                                                  | Task 14, 15      | GET /cost-elements/{id}/evm endpoint, query params: control_date, branch, returns EVMMetricsRead, proper error handling                                                                                                               | Medium       |
| 17  | Write unit tests for EVMService                                    | `backend/tests/unit/services/test_evm_service.py`                                                   | Task 14          | Tests for BAC calculation, PV calculation with time-travel, AC calculation with time-travel, EV calculation (with/without progress), variance calculations (CV, SV), index calculations (CPI, SPI), division by zero handling, test coverage ≥80% | High         |
| 18  | Write API integration tests for EVM metrics                         | `backend/tests/api/test_evm_metrics.py`                                                             | Task 16          | Tests for GET /cost-elements/{id}/evm with various control dates, branch isolation, error handling (not found, no baseline), warning message when no progress, test coverage ≥80%                                                     | Medium       |
| 19  | Add period-based aggregation methods to CostRegistrationService     | `backend/app/services/cost_registration_service.py` (extend)                                        | None             | get_costs_by_period() method (daily/weekly/monthly), get_cumulative_costs() method, proper GROUP BY SQL queries, time-travel support (as_of parameter)                                                                                 | High         |
| 20  | Add cost aggregation endpoint to cost registrations routes          | `backend/app/api/routes/cost_registrations.py` (extend)                                             | Task 19          | GET /cost-registrations/aggregated endpoint, query params: cost_element_id, period, start_date, end_date, returns aggregated costs by period, proper validation                                                                         | Medium       |
| 21  | Write unit tests for cost aggregation                               | `backend/tests/unit/services/test_cost_aggregation.py`                                              | Task 19          | Tests for daily aggregation, weekly aggregation, monthly aggregation, time-travel filtering, empty results, period boundaries, test coverage ≥80%                                                                                       | Medium       |
| 22  | Write API integration tests for cost aggregation                   | `backend/tests/api/test_cost_aggregation.py`                                                        | Task 20          | Tests for GET /cost-registrations/aggregated endpoint, period validation, date range filtering, async operations, test coverage ≥80%                                                                                                   | Medium       |
| 23  | Update API documentation (OpenAPI)                                  | `backend/app/main.py` (update metadata if needed)                                                   | Task 16, 20      | All new endpoints documented in OpenAPI spec, proper descriptions, examples for control_date parameter                                                                                                                                  | Low          |
| 24  | Create EVM calculation guide documentation                          | `docs/02-architecture/evm-calculation-guide.md`                                                      | Task 14          | Document EVM formulas, time-travel usage, API examples, progress tracking workflow, cost aggregation examples                                                                                                                          | Low          |
| 25  | Run full quality check suite (MyPy, Ruff, pytest coverage)          | All files                                                                                            | All tasks        | MyPy strict mode: 0 errors, Ruff: 0 errors, pytest coverage: ≥80%, all tests pass                                                                                                                                                      | Medium       |

### Test-to-Requirement Traceability

| Acceptance Criterion                                        | Test ID                                                   | Test File                                                   | Expected Behavior                                                                                                                                                                                                                  |
| ----------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Progress entry creation validates 0-100 range               | T-001, T-002, T-003                                       | test_progress_entry_service.py                               | T-001: Accept 0, T-002: Accept 100, T-003: Reject -1 with error, T-004: Reject 101 with error                                                                                                                                      |
| Progress can increase                                       | T-005                                                     | test_progress_entry_service.py                               | Create progress at 50%, update to 75%, verify both versions exist in history                                                                                                                                                       |
| Progress can decrease with warning                          | T-006                                                     | test_progress_entry_service.py                               | Create progress at 75%, update to 50%, verify warning logged, both versions exist                                                                                                                                                  |
| Progress frequency: multiple times per day allowed          | T-007                                                     | test_progress_entry_service.py                               | Create progress entries at 9am, 2pm, 6pm same day, verify all recorded                                                                                                                                                             |
| Progress history queryable                                  | T-008                                                     | test_progress_entry_service.py                               | Create 5 progress entries, call get_progress_history(), verify returns 5 entries ordered by date                                                                                                                                   |
| Progress supports time-travel                               | T-009, T-010                                              | test_progress_time_travel.py                                | T-009: Create progress at 50% (Jan 1), update to 75% (Jan 15), query as_of Jan 10 returns 50%, T-010: Query as_of Jan 20 returns 75%                                                                                               |
| EVM metrics returns BAC, PV, AC, EV, CV, SV, CPI, SPI       | T-011                                                     | test_evm_service.py                                          | Calculate EVM with all data present, verify all 8 metrics returned with correct values                                                                                                                                            |
| EVM metrics support time-travel                             | T-012, T-013                                              | test_evm_service.py                                          | T-012: Query EVM with control_date in past returns historical values, T-013: BAC/PV respect cost element version as of control_date                                                                                                 |
| EVM returns EV = 0 with warning when no progress            | T-014                                                     | test_evm_service.py                                          | Calculate EVM without progress entries, verify EV = 0, warning message present                                                                                                                                                     |
| Cost aggregations support daily, weekly, monthly            | T-015, T-016, T-017                                       | test_cost_aggregation.py                                    | T-015: Daily aggregation returns one row per day, T-016: Weekly aggregation returns one row per week, T-017: Monthly aggregation returns one row per month                                                                          |
| Cost aggregations respect time-travel                       | T-018                                                     | test_cost_aggregation.py                                    | Create costs in Jan and Feb, query as_of Jan 31, verify only Jan costs included                                                                                                                                                   |
| All data respects bitemporal versioning                     | T-019, T-020                                              | test_progress_time_travel.py, test_evm_service.py           | T-019: Progress version history has correct valid_time and transaction_time, T-020: EVM metrics change when querying different control_dates                                                                                       |
| Performance: EVM calculations < 500ms                       | T-021                                                     | test_evm_service_performance.py (new)                       | Calculate EVM for 100 cost elements with full history, verify completion time < 500ms                                                                                                                                              |
| Database indexes exist                                      | T-022                                                     | test_migration_indexes.py (new)                             | Inspect progress_entries table, verify indexes on cost_element_id, reported_date, progress_entry_id, verify GIST indexes on TSTZRANGE columns                                                                                    |
| Progress decrease requires justification                    | T-023                                                     | test_progress_entry_service.py                              | Update progress from 80% to 60% without notes, verify validation error or warning, update with notes, verify success                                                                                                                |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests (tests/unit/)
│   ├── models/
│   │   └── test_progress_entry.py
│   └── services/
│       ├── test_progress_entry_service.py
│       ├── test_evm_service.py
│       └── test_cost_aggregation.py
├── Integration Tests (tests/integration/)
│   └── test_progress_time_travel.py
├── API Tests (tests/api/)
│   ├── test_progress_entries.py
│   ├── test_evm_metrics.py
│   └── test_cost_aggregation.py
└── Performance Tests (tests/performance/)
    └── test_evm_service_performance.py
```

### Test Cases (First 5)

| Test ID | Test Name                                                               | Criterion | Type           | Expected Result                                                                                                                                                                                                                            |
| ------- | ----------------------------------------------------------------------- | --------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| T-001   | test_progress_entry_create_with_valid_percentage_accepts_zero            | AC-1      | Unit           | Create ProgressEntry with progress_percentage=0, verify saves successfully                                                                                                                                                                 |
| T-002   | test_progress_entry_create_with_valid_percentage_accepts_hundred         | AC-1      | Unit           | Create ProgressEntry with progress_percentage=100, verify saves successfully                                                                                                                                                               |
| T-003   | test_progress_entry_create_with_negative_percentage_raises_validation_error | AC-1      | Unit           | Create ProgressEntry with progress_percentage=-1, verify raises ValueError with message "Progress percentage must be between 0 and 100"                                                                                                    |
| T-004   | test_progress_entry_create_with_percentage_over_hundred_raises_error     | AC-1      | Unit           | Create ProgressEntry with progress_percentage=101, verify raises ValueError with message "Progress percentage must be between 0 and 100"                                                                                                  |
| T-005   | test_progress_entry_create_increases_progress_successfully              | AC-2      | Integration    | Create progress at 50%, then update to 75%, verify get_latest_progress() returns 75%, verify get_progress_history() returns both entries in chronological order                                                                          |

### Test Infrastructure Needs

**Fixtures needed (from conftest.py):**
- `db_session` - AsyncSession for database operations
- `client` - AsyncClient for API testing
- `test_user` - User fixture for created_by fields

**New fixtures required:**
- `test_cost_element` - CostElement with schedule_baseline
- `test_schedule_baseline` - ScheduleBaseline with LINEAR progression
- `test_progress_entry` - ProgressEntry with valid percentage
- `test_cost_registration` - CostRegistration with amount

**Mocks/stubs:**
- Time-dependent logic: Use frozen datetime fixtures for time-travel tests
- External services: None (all services are internal)

**Database state:**
- Clean slate for each test (pytest-asyncio auto cleanup)
- Seed data for time-travel tests (create versions at different timestamps)
- Test isolation (rollback transactions after each test)

---

## Risk Assessment

| Risk Type   | Description                                                                 | Probability  | Impact       | Mitigation                                                                                                                                                                                                                              |
| ----------- | --------------------------------------------------------------------------- | ------------ | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Technical   | Progress validation conflicts with existing progress entries               | Low          | Medium       | Allow progress decreases with warning + justification field, document clearly in API spec                                                                                                                                               |
| Technical   | EVM calculation performance degrades with large datasets                    | Medium       | Medium       | Implement database-level aggregations with proper indexes, add query performance tests, consider caching for common control dates                                                                                                       |
| Integration | Time-travel semantics inconsistent across services                         | Medium       | High         | Reuse existing `_apply_bitemporal_filter_for_time_travel()` pattern, write comprehensive integration tests, document System Time Travel semantics clearly                                                                                |
| Integration | Cost aggregation period boundaries unclear (week start, month start)        | Low          | Low          | Use PostgreSQL date_trunc() function for consistency (week starts Monday, month starts 1st), document in API spec                                                                                                                      |
| Integration | Division by zero in CPI/SPI calculations when AC or PV is 0                 | Medium       | Medium       | Return null or 0 for indices when denominator is 0, add warning message, document behavior                                                                                                                                              |
| Data        | Progress entries become too numerous (multiple per day)                     | Medium       | Low          | No row limit in this iteration (foundation), add pagination in future iteration, add index on reported_date                                                                                                                            |
| Data        | Orphaned progress entries (cost element deleted)                            | Low          | Low          | Use soft delete (already in VersionableMixin), add cascade check in queries (filter by existing cost elements)                                                                                                                         |
| Testing     | Time-travel tests are complex and brittle                                   | High         | Medium       | Use frozen datetime fixtures, create helper methods for common time-travel scenarios, write clear test documentation, use transactions for rollback                                                                                     |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for EVM Foundation Iteration

tasks:
  # Phase 1: Progress Tracking Foundation
  - id: BE-001
    name: "Create ProgressEntry domain model"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Create Alembic migration for progress_entries table"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Create ProgressEntry Pydantic schemas"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-004
    name: "Create ProgressEntryService with CRUD operations"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-003]

  - id: BE-005
    name: "Create progress entries API routes"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-004]

  - id: BE-006
    name: "Register progress routes in API router"
    agent: pdca-backend-do-executor
    dependencies: [BE-005]

  - id: BE-007
    name: "Write unit tests for ProgressEntry model"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-008
    name: "Write unit tests for ProgressEntryService"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-009
    name: "Write API integration tests for progress entries"
    agent: pdca-backend-do-executor
    dependencies: [BE-005, BE-006]

  - id: BE-010
    name: "Write time-travel integration tests for progress"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  # Phase 2: EVM Calculation Service
  - id: BE-011
    name: "Create EVMService orchestrator class"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-012
    name: "Implement EVM metrics calculation core logic (BAC, PV, AC)"
    agent: pdca-backend-do-executor
    dependencies: [BE-011]

  - id: BE-013
    name: "Implement EV calculation with progress lookup"
    agent: pdca-backend-do-executor
    dependencies: [BE-012]

  - id: BE-014
    name: "Implement variance and index calculations (CV, SV, CPI, SPI)"
    agent: pdca-backend-do-executor
    dependencies: [BE-013]

  - id: BE-015
    name: "Create EVMMetricsRead schema"
    agent: pdca-backend-do-executor
    dependencies: [BE-011]

  - id: BE-016
    name: "Add EVM metrics endpoint to cost elements routes"
    agent: pdca-backend-do-executor
    dependencies: [BE-014, BE-015]

  - id: BE-017
    name: "Write unit tests for EVMService"
    agent: pdca-backend-do-executor
    dependencies: [BE-014]

  - id: BE-018
    name: "Write API integration tests for EVM metrics"
    agent: pdca-backend-do-executor
    dependencies: [BE-016]

  # Phase 3: Enhanced Cost Queries
  - id: BE-019
    name: "Add period-based aggregation methods to CostRegistrationService"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-020
    name: "Add cost aggregation endpoint to cost registrations routes"
    agent: pdca-backend-do-executor
    dependencies: [BE-019]

  - id: BE-021
    name: "Write unit tests for cost aggregation"
    agent: pdca-backend-do-executor
    dependencies: [BE-019]

  - id: BE-022
    name: "Write API integration tests for cost aggregation"
    agent: pdca-backend-do-executor
    dependencies: [BE-020]

  # Phase 4: Integration & Documentation
  - id: BE-023
    name: "Update API documentation (OpenAPI)"
    agent: pdca-backend-do-executor
    dependencies: [BE-016, BE-020]

  - id: BE-024
    name: "Create EVM calculation guide documentation"
    agent: pdca-backend-do-executor
    dependencies: [BE-014]

  - id: BE-025
    name: "Run full quality check suite (MyPy, Ruff, pytest coverage)"
    agent: pdca-backend-do-executor
    dependencies: [BE-018, BE-022, BE-023, BE-024]

# Parallel Execution Opportunities:
# - BE-001, BE-019 can run in parallel (independent foundation work)
# - BE-007, BE-021 can run in parallel after their dependencies
# - BE-010, BE-017 can run in parallel (different service tests)
```

---

## Documentation References

### Required Reading

**Coding Standards:**
- `docs/00-meta/coding_standards.md` - Python formatting, type hints, async patterns

**Architecture Decisions:**
- `docs/02-architecture/decisions/adr-005-bitemporal-versioning.md` - TSTZRANGE usage, time-travel semantics
- `docs/02-architecture/01-bounded-contexts.md` - Cost Element & Financial Tracking context
- `docs/02-architecture/00-system-map.md` - Layered architecture overview

**Product Scope:**
- EVM formulas: `docs/03-project-plan/iterations/2026-01-18-evm-foundation/00-analysis.md` (Section: EVM References)

### Code References

**Backend Patterns to Follow:**

**Model Pattern:**
- `backend/app/models/domain/cost_registration.py` - VersionableMixin usage (lines 1-60)
- Field definitions, ForeignKey relationships, docstring format

**Service Pattern:**
- `backend/app/services/cost_registration_service.py` - TemporalService inheritance (lines 1-50)
- `get_total_for_cost_element()` method - time-travel filtering (lines 232-280)
- Validation patterns, error handling

**Time-Travel Pattern:**
- `backend/app/core/versioning/service.py` - TemporalService.get_as_of() (lines 142-197)
- `_apply_bitemporal_filter_for_time_travel()` - System Time Travel semantics (lines 344-377)

**Test Pattern:**
- `backend/tests/unit/services/test_schedule_baseline_service.py` - Arrange-Act-Assert structure (lines 28-80)
- Async test pattern with db_session fixture
- Time-travel test patterns (use frozen datetime fixtures)

**API Route Pattern:**
- `backend/app/api/routes/cost_elements.py` - FastAPI route definitions
- Dependency injection via `Depends()`, Pydantic validation

**Progression Strategy Pattern:**
- `backend/app/services/progression/` - Strategy pattern for PV calculation
- `ProgressionStrategy.calculate_progress()` interface

---

## Prerequisites

### Technical Prerequisites

- [x] PostgreSQL 15+ with TSTZRANGE support installed and running
- [x] Python 3.12+ environment configured
- [x] All backend dependencies installed (`uv sync`)
- [x] Test database configured in settings
- [x] Alembic migrations system initialized
- [ ] Database migrations applied (`uv run alembic upgrade head`)
- [ ] Existing cost_elements, schedule_baselines, cost_registrations tables present
- [ ] Pytest, pytest-asyncio installed and configured

### Documentation Prerequisites

- [x] Analysis phase approved (00-analysis.md)
- [ ] Architecture docs reviewed (ADR-005, Bounded Contexts)
- [ ] Existing code patterns reviewed (CostRegistrationService, ScheduleBaselineService)
- [ ] EVM formulas understood (BAC, PV, AC, EV, CV, SV, CPI, SPI)

### Environment Setup

```bash
# Apply database migrations
cd backend
uv run alembic upgrade head

# Verify test database is accessible
uv run pytest --collect-only

# Run existing tests to ensure baseline
uv run pytest tests/unit/services/test_cost_registration_service.py -v
```

---

## Key Principles

1. **Define WHAT, not HOW**: This plan specifies test cases and acceptance criteria, NOT implementation code. The DO phase will write the actual Python code following TDD RED-GREEN-REFACTOR.

2. **Measurable Success Criteria**: All acceptance criteria are objectively verifiable through tests, code quality checks, or performance benchmarks.

3. **Sequential Task Dependencies**: Tasks are ordered with clear dependencies (e.g., migration before API routes, service before tests). The dependency graph enables parallel execution where possible.

4. **Test-to-Requirement Traceability**: Every acceptance criterion maps to one or more test specifications (T-001, T-002, etc.). Tests verify functional, technical, and business criteria.

5. **Follows Established Patterns**: All implementations must reuse existing EVCS patterns (TemporalService, VersionableMixin, bitemporal filtering, async/await).

6. **Quality Gates**: Zero tolerance for MyPy/Ruff errors, 80%+ test coverage required, all tests must pass before merging.

---

## Output

**File**: `docs/03-project-plan/iterations/2026-01-18-evm-foundation/01-plan.md`

**Next Phase**: DO Phase execution by pdca-backend-do-executor agent (implementation following TDD)

**Success Metrics**:
- All 25 tasks completed
- 100% of acceptance criteria verified by tests
- MyPy strict mode: 0 errors
- Ruff linting: 0 errors
- Test coverage: ≥80%
- EVM calculations: < 500ms performance
- All database migrations applied successfully
