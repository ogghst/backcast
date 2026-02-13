# Plan: Define Schedule Baselines with Progression Types

**Created:** 2026-01-16
**Based on:** [00-analysis.md](00-analysis.md)
**Approved Option:** Versioned & Branchable ScheduleBaseline with Pure Progression Functions

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option:** Versioned & Branchable ScheduleBaseline with Pure Progression Functions.
- **Architecture:**
  - **Backend:** `ScheduleBaseline` entity using `BranchableMixin` and `VersionableMixin`. Service layer uses `BranchableService`.
  - **Domain Logic:** Pure python classes for progression strategies (Linear, Gaussian, Logarithmic).
  - **PMI Compliance:** Enforced via branching (Change Orders) and S-curve support (Planned Value).
- **Key Decisions:**
  - Use `BranchableMixin` to support Change Order impact analysis.
  - Implement `GaussianProgression` using `math.erf` for standard S-curves.
  - PV Calculation: `PV = BAC * % Complete`.

### Success Criteria

**Functional Criteria:**

- Users can create, update, and soft-delete schedule baselines VERIFIED BY: `tests/integration/services/test_schedule_baseline_service.py`
- System supports Linear, Gaussian, and Logarithmic progression types VERIFIED BY: `tests/unit/domain/test_progression_functions.py`
- Planned Value (PV) calculations are accurate to 4 decimal places VERIFIED BY: `tests/unit/services/test_pv_calculation.py`
- Change Orders can have independent schedule baselines (branching) VERIFIED BY: `tests/integration/services/test_schedule_baseline_branching.py`

**Technical Criteria:**

- Performance: PV calculation < 50ms for single entity VERIFIED BY: Benchmark test in `tests/performance/test_pv_perf.py`
- Code Quality: 100% test coverage for progression logic VERIFIED BY: `pytest --cov`
- Type Safety: Full MyPy strict compliance VERIFIED BY: `mypy .`

**Business Criteria:**

- Enables EVM Schedule Performance Index (SPI) calculation VERIFIED BY: End-to-end flow validation

### Scope Boundaries

**In Scope:**

- Backend: `ScheduleBaseline` model, migration, service, API.
- Domain: Linear, Gaussian, Logarithmic progression logic.
- Frontend: Schedule tab in Cost Element Detail, Create/Edit Modal, Progression Preview Chart.

**Out of Scope:**

- Advanced custom progression types (User defined formulas).
- Bulk import of schedules (CSV/Excel).
- EVM Reporting Dashboards (handled in separate iteration).

---

## Work Decomposition

### Task Breakdown (Test-First)

| Task | Description              | Files                                                                                                       | Dependencies | Success                                   | Est. Complexity |
| ---- | ------------------------ | ----------------------------------------------------------------------------------------------------------- | ------------ | ----------------------------------------- | --------------- |
| 1    | **Progression Logic**    | `tests/unit/domain/test_progression.py`, `app/services/progression/*.py`                                    | None         | All curves pass mathematical verification | Low             |
| 2    | **Database Model**       | `tests/integration/models/test_schedule_baseline.py`, `app/models/domain/schedule_baseline.py`, Migration   | Task 1       | Table created, constraints enforced       | Low             |
| 3    | **Service Layer (CRUD)** | `tests/integration/services/test_schedule_baseline_service.py`, `app/services/schedule_baseline_service.py` | Task 2       | Full CRUD with Branching support          | Medium          |
| 4    | **PV Calculation**       | `tests/unit/services/test_pv_calculation.py`, `app/services/schedule_baseline_service.py`                   | Task 3       | PV = BAC \* Progress                      | Medium          |
| 5    | **API Endpoints**        | `tests/api/routes/test_schedule_baselines.py`, `app/api/routes/schedule_baselines.py`                       | Task 4       | Endpoints return correct schemas          | Low             |
| 6    | **Frontend UI**          | `src/features/schedule-baselines/...`                                                                       | Task 5       | User can manage baselines visually        | Medium          |

### Detailed Test-First Plan

#### Task 1: Progression Logic

1.  **Test**: `tests/unit/domain/test_progression.py` -> Verify `calculate_progress(current, start, end)` returns 0.0 to 1.0. Check exact values for Linear (50% at midpoint), Gaussian (S-curve), Logarithmic (Front-loaded).
2.  **Implement**: `app/services/progression/{base,linear,gaussian,logarithmic}.py`

#### Task 2: Database Model

1.  **Test**: `tests/integration/models/test_schedule_baseline.py` -> Verify table creation, `BranchableMixin` fields (`branch`, `parent_id`), `VersionableMixin` fields (`valid_time`), and unique constraints.
2.  **Implement**: `app/models/domain/schedule_baseline.py` and Alembic migration.

#### Task 3: Service Layer

1.  **Test**: `tests/integration/services/test_schedule_baseline_service.py` -> Verify `create_version`, `update_version` (with branching), `delete_version` (soft delete). Verify isolation of branches.
2.  **Implement**: `app/services/schedule_baseline_service.py` inheriting `BranchableService`.

---

## Test Specification

### Test Hierarchy

```text
├── Unit Tests
│   ├── tests/unit/domain/test_progression.py (Core Logic)
│   └── tests/unit/services/test_pv_calculation.py (Math Logic)
├── Integration Tests
│   ├── tests/integration/models/test_schedule_baseline.py (DB Schema)
│   ├── tests/integration/services/test_schedule_baseline_service.py (Service CRUD)
│   └── tests/integration/services/test_schedule_baseline_branching.py (Branching)
└── API Tests
    └── tests/api/routes/test_schedule_baselines.py (Endpoints)
```

### Test Cases (Key Examples)

| Test ID | Description                               | Type | Verification                                                                   |
| ------- | ----------------------------------------- | ---- | ------------------------------------------------------------------------------ |
| T-001   | `test_linear_progression_midpoint`        | Unit | Input: 10 day duration, day 5. Expected: 0.5                                   |
| T-002   | `test_gaussian_progression_s_curve`       | Unit | Input: Midpoint. Expected: 0.5. Input: 1/4 time. Expected: < 0.25 (slow start) |
| T-003   | `test_baseline_creation_branch_isolation` | Int  | Create baseline on 'feature-branch'. Verify not visible on 'main'.             |
| T-004   | `test_pv_calculation_integration`         | Int  | BAC=1000, Progress=0.5. Expected PV=500.                                       |

### Test Infrastructure

- **Test Framework**: `pytest-asyncio`
- **Fixtures Needed**:
  - `schedule_baseline_factory`: Helper to create baselines in tests.
  - `cost_element_factory`: Prerequisite for baselines.
- **Mock Requirements**: None for core logic (pure functions).

---

## Risk Assessment

| Risk Type   | Description                  | Probability | Impact | Mitigation                                                                                |
| ----------- | ---------------------------- | ----------- | ------ | ----------------------------------------------------------------------------------------- |
| Technical   | Gaussian math accuracy       | Low         | Medium | Use `math.erf` standard implementation; validate against SciPy reference values in tests. |
| Performance | Slow PV calc for large lists | Low         | Low    | Implement `lru_cache` for progression functions; benchmarks.                              |
| Integration | Branching complexity         | Medium      | High   | Re-use existing `BranchableService` pattern which is already proven.                      |

---

## Documentation References

### Required Documentation

**Architecture & Standards:**

- Coding Standards: `docs/02-architecture/coding-standards.md`
- Bounded Context: `docs/02-architecture/01-bounded-contexts.md` (Context 6)

**Domain & Requirements:**

- User Story: E05-U04 (Schedule Baselines)

### Code References

**Pattern to Follow:**

- `CostElement` (Backend Model): `backend/app/models/domain/cost_element.py`
- `CostElementService` (Backend Service): `backend/app/services/cost_element_service.py`

**Database Schema:**

- Table: `schedule_baselines`
- FK: `cost_element_id` -> `cost_elements.id`

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [x] Database migrations applied (up to date)
- [x] Dependencies installed (`numpy`/`scipy` NOT needed, using `math` stdlib)

### Documentation Prerequisites

- [x] Analysis phase approved
