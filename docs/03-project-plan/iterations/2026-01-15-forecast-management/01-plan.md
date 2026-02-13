# Plan: Forecast Management (EAC)

**Created:** 2026-01-16
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1: Versioned Forecast Entity (Branchable)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1: Versioned Forecast Entity (Branchable)
- **Architecture**:
  - **Entity**: `Forecast` extends `EntityBase` and `BranchableMixin` (supports versioning + branching).
  - **Service**: `ForecastService` extends `BranchableService[Forecast]`.
  - **Pattern**: Uses Command Pattern (`CreateVersionCommand`) and standard EVCS branching logic.
- **Key Decisions**:
  - **Branching**: Forecasts are **branchable** to enable "What-if" scenarios (e.g., Change Orders carrying specific EACs).
  - **Semantics**: `reason` field renamed to `basis_of_estimate`.
  - **Versioning**: Full bitemporal history (`valid_time`, `transaction_time`).

### Success Criteria

**Functional Criteria:**

- Users can create a Forecast for a Cost Element on a specific branch VERIFIED BY: Unit Test `test_create_forecast_on_branch`
- Users can view the latest Forecast for a Cost Element, respecting branch fallbacks (Main <- Feature) VERIFIED BY: Unit Test `test_get_latest_forecast_merge_logic`
- Comparison logic correctly calculates Variance at Complete (VAC = BAC - EAC) VERIFIED BY: Unit Test `test_forecast_comparison_calculations`
- Comparison logic correctly calculates Estimate to Complete (ETC = EAC - AC) VERIFIED BY: Unit Test `test_forecast_comparison_calculations`
- Historical queries (Time Travel) return correct forecast version for a given timestamp VERIFIED BY: Integration Test `test_forecast_time_travel`

**Technical Criteria:**

- **Performance**: Single forecast retrieval < 100ms VERIFIED BY: Integration Test with timing assertion
- **Type Safety**: strict Pydantic V2 schemas and MyPy compliance VERIFIED BY: `mypy .` check
- **Code Quality**: 100% test coverage for calculation logic VERIFIED BY: `pytest --cov`

**Business Criteria:**

- Project Managers can distinguish between "Official" (Main) and "Simulated" (Branch) forecasts VERIFIED BY: Functional Review (later phase)

### Scope Boundaries

**In Scope:**

- Backend: `Forecast` DB table (migration), Domain Model, Schemas.
- Backend: `ForecastService` with CRUD and Simulation (Branching) logic.
- Backend: Comparison logic (EAC vs BAC vs AC).
- Backend: API Routes for Forecasts.

**Out of Scope:**

- Frontend Implementation (Deferred to next set of tasks after Backend is solid).
- Complex automated forecasting (e.g., Regression Analysis) - currently manual entry or simple calculation.

---

## Work Decomposition

### Task Breakdown

| Task | Description                       | Files                                                 | Dependencies | Success                       | Est. Complexity |
| ---- | --------------------------------- | ----------------------------------------------------- | ------------ | ----------------------------- | --------------- |
| 1    | **Domain Model & Migration**      | `models/domain/forecast.py`, `alembic/versions/...`   | None         | `alembic upgrade head` passes | Low             |
| 2    | **Forecast Service (Basis)**      | `services/forecast_service.py`, `schemas/forecast.py` | Task 1       | Unit tests pass for CRUD      | Medium          |
| 3    | **Branching & Simulation Logic**  | `services/forecast_service.py`                        | Task 2       | Branch/Merge tests pass       | High            |
| 4    | **Comparison Logic (EAC/BAC/AC)** | `services/forecast_service.py`                        | Task 3       | Calculation tests pass        | Medium          |
| 5    | **API Endpoints**                 | `api/routes/forecasts.py`                             | Task 4       | API Integration tests pass    | Low             |

---

## Test Specification

### Test Hierarchy

```text
├── Unit Tests (backend/tests/unit/)
│   ├── services/
│   │   └── test_forecast_service.py      # Core CRUD, Branching Fallback, Calculations
│   └── api/
│       └── test_forecast_routes.py       # Input validation, Route wiring
├── Integration Tests (backend/tests/integration/)
│   └── repositories/
│       └── test_forecast_repository.py   # DB Persistence, Concurrent updates
```

### Test Cases (Test-First Implementation)

| Test ID   | Description                                  | Type | Verification                                                                                                                                                                                               |
| --------- | -------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **T-001** | `test_create_forecast_returns_forecast`      | Unit | Returns created object with correct `eac_amount` and `branch_id`.                                                                                                                                          |
| **T-002** | `test_get_forecast_respects_branch_fallback` | Unit | If no forecast on Feature Branch, returns Main Branch forecast (if strategy allows) OR None (if strict). _Requirement: Strict isolation for writes, fallback for reads? Check BranchableService standard._ |
| **T-003** | `test_calculate_vac_positive`                | Unit | Given BAC=100, EAC=80 -> Returns VAC=20 (Under Budget).                                                                                                                                                    |
| **T-004** | `test_calculate_vac_negative`                | Unit | Given BAC=100, EAC=120 -> Returns VAC=-20 (Over Budget).                                                                                                                                                   |
| **T-005** | `test_calculate_etc`                         | Unit | Given EAC=120, AC=50 -> Returns ETC=70.                                                                                                                                                                    |

### Test Infrastructure

- **Framework**: `pytest-asyncio`
- **Fixtures Needed**:
  - `cost_element_fixture`: Need a parent Cost Element to attach Forecast to.
  - `branch_fixtures`: Need Main Branch and a Feature Branch.

---

## Risk Assessment

| Risk Type          | Description                                                                                                          | Probability   | Impact | Mitigation                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------- | ------------- | ------ | -------------------------------------------------------------------------------------------------- |
| **Integration**    | Calculation logic depends on `CostElement` (BAC) and `CostRegistration` (AC). If those services change, calc breaks. | Medium        | High   | Defines strict interfaces/DTOs for fetching BAC/AC. Use Mocks in Unit Tests to isolate dependency. |
| **Interpretation** | Users confusing "Branch Forecast" with "Official Forecast".                                                          | Low (Backend) | High   | API response clearly indicates `source_branch` of the data.                                        |

---

## Documentation References

### Required Documentation

**Architecture & Standards:**

- Coding Standards: `docs/02-architecture/coding-standards.md`
- Bounded Contexts: `docs/02-architecture/01-bounded-contexts.md` (Context 6)

### Code References

**Existing Patterns:**

- `BranchableService`: See `backend/app/services/cost_element_service.py` for reference implementation of branching logic.
- `CostRegistration`: See `backend/app/models/domain/cost_registration.py` for financial field patterns.

**Database Schema:**

- New Table: `forecasts`
- FK: `cost_element_id` -> `cost_elements.cost_element_id`
- FK: `branch_id` -> `branches.branch_id`

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [x] Environment configured (Postgres running)
- [x] `CostElement` and `Branch` tables exist

### Documentation Prerequisites

- [x] Analysis phase approved (00-analysis.md)
