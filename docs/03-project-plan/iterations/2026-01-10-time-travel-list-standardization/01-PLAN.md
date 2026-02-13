# PLAN: Standardize Bitemporal List Operations

**Date:** 2026-01-10
**Status:** Approved (Option 2 Selected)
**Approver:** User

## Phase 1: Context Analysis

### Documentation Review

- **Product Scope**: Time Travel is a core feature (Vision). Users need to see the "state of the world" at any past point.
- **Architecture**: We follow strict typing and bitemporal data modeling using `valid_time` and `transaction_time`.
- **Project Plan**: We are iterating on "Time Machine Production Hardening".

### Codebase Analysis

- **Current Pattern**: `WbEsService` implements `as_of` logic. `ProjectsService` and `CostElementsService` may have partial or inconsistent implementations.
- **Tools**: `GenericTemporalService` exists but needs to be leveraged consistently for list filtering.

## Phase 2: Problem Definition

### 1. Problem Statement

- **What**: List operations for versioned entities (Projects, Cost Elements) do not consistently support or enforce bitemporal "as of" queries.
- **Why**: This leads to inconsistent user experience and potential data correctness issues when viewing history.
- **Impact**: Users cannot reliably use the "Time Machine" feature for these entities.

### 2. Success Criteria

**Functional:**

- `GET /projects?as_of={timestamp}` returns projects valid at `timestamp`.
- `GET /cost_elements?as_of={timestamp}` returns cost elements valid at `timestamp`.
- Deleted items appear if `as_of` is before deletion.
- Future items (created after `as_of`) do not appear.

**Technical:**

- Strict bitemporal logic applied: `valid_from <= as_of < valid_to` AND `transaction_from <= as_of < transaction_to`.
- 100% Type safety in backend services.

## Phase 3: Implementation Options

| Aspect      | Option A (Ad-hoc)                                        | Option B (Standardized - Selected)                                                               | Option C (Complex Joins)                                 |
| :---------- | :------------------------------------------------------- | :----------------------------------------------------------------------------------------------- | :------------------------------------------------------- |
| **Summary** | Implement `as_of` logic manually in each service method. | Define a standard pattern/helper in `GenericTemporalService` and enforce it across all services. | Re-architect for complex temporal joins across entities. |
| **Pros**    | Flexible, quick for one-off.                             | Consistent, maintainable, reduces bug risk.                                                      | Most robust for deep queries.                            |
| **Cons**    | Code duplication, risk of inconsistency.                 | Requires refactoring existing services.                                                          | Over-engineering for current needs.                      |
| **Risk**    | High (inconsistency).                                    | Low.                                                                                             | High (complexity).                                       |

**Selected**: **Option 2 (Standardized)**. This balances consistency with current requirements, keeping the architecture open for Option 3 later.

## Phase 4: Technical Design

### TDD Test Blueprint

1.  **Unit Tests (Backend `tests/unit/test_services.py`)**

    - `test_get_projects_as_of_past`: Create project, update it, check `as_of` before update, `as_of` after update.
    - `test_get_cost_elements_as_of_deleted`: Create item, delete it, check `as_of` (should exist) vs current (should not).
    - `test_get_projects_future_as_of`: Query with `as_of` in future (should return current valid?). _Correction_: `as_of` strictly filters. If `as_of` is > `valid_to`, it returns nothing unless `valid_to` is infinity.

2.  **Integration Tests (Backend `tests/integration/api/test_routes.py`)**
    - Verify API endpoint correctly parses `as_of` query param and passes it to service.

### Implementation Strategy

1.  **Refactor `GenericTemporalService` (if needed)**: Ensure a public helper `build_bitemporal_filter(as_of, model)` is available.
2.  **Update `ProjectsService`**:
    - Modify `get_projects` to accept `as_of`.
    - Apply bitemporal filter if `as_of` is present.
3.  **Update `CostElementsService`**:
    - Modify `get_cost_elements` to accept `as_of`.
    - Apply bitemporal filter.
4.  **Update API Routers**:
    - Add `as_of: datetime | None = None` to query params.

## Phase 5: Risk Assessment

| Risk Type       | Description                                                   | Probability             | Impact | Mitigation                                               |
| :-------------- | :------------------------------------------------------------ | :---------------------- | :----- | :------------------------------------------------------- |
| **Performance** | Bitemporal queries on large datasets can be slow.             | Low (current data size) | Medium | Ensure GiST indexes on range columns (already standard). |
| **Correctness** | "Zombie" records (deleted but showing up) or missing records. | Medium                  | High   | Comprehensive TDD with deletion scenarios.               |

## Phase 6: Effort Estimation

- **Development**: 4 hours
- **Testing**: 2 hours
- **Total**: ~1 day
