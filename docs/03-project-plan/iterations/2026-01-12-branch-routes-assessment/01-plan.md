# Plan: Branch Routes & Change Order Capabilities

## 1. Problem Statement

The `ChangeOrderService` supports advanced branching operations (`merge_branch`, `revert`), but these capabilities are not exposed in the API routes. Furthermore, the `ChangeOrder` list endpoint lacks standard filtering and searching capabilities compared to other entities like `WBE`, creating an inconsistent user and developer experience.

## 2. Success Criteria

**Functional Criteria:**

1.  **Merge Capability:** API users can merge a Change Order (branch) into `main` via a POST request.
2.  **Revert Capability:** API users can revert a Change Order branch to a previous state via a POST request.
3.  **List Parity:** The `/change-orders` endpoint supports:
    - `search` (by code/name)
    - `filters` (structured filtering string)
    - `sort_field` & `sort_order`
4.  **Security:** All new endpoints respect existing RBAC permissions.

**Technical Criteria:**

1.  Code follows existing conventions using `FilterParser` for dynamic filtering.
2.  Test coverage includes integration tests for the new endpoints.
3.  No regression in existing Change Order lifecycle operations.

## 3. Scope Definition

**In Scope:**

- Modify `backend/app/services/change_order_service.py`: Add filtering/sorting logic.
- Modify `backend/app/api/routes/change_orders.py`: Update GET params and add Merge/Revert POST routes.
- Add Integration Tests for the new routes.
- Update `backend/app/schemas/change_order.py` if needed (likely not needed for standard string/uuid inputs).

**Out of Scope:**

- Frontend implementation (backend only iteration).
- Refactoring `BranchableService` vs `TemporalService` inheritance structure (deferred tech debt).
- Modifying WBE implementation.

## 4. Implementation Options

The selected approach is **Option 1: Full Parity & Exposure** (as per Analysis).

| Aspect             | Details                                                                        |
| :----------------- | :----------------------------------------------------------------------------- |
| **Routes**         | Add `POST /{id}/merge`, `POST /{id}/revert`. Update `GET /`.                   |
| **Service**        | Update `get_change_orders` to use `FilterParser` and dynamic SQL construction. |
| **Design Pattern** | Command Pattern (existing) + Dynamic Filtering (existing).                     |
| **Pros**           | Consistent API, unlocks full feature set, minimal regression risk.             |
| **Cons**           | Slightly more verbose service queries.                                         |

## 5. Technical Design

### TDD Test Blueprint

**1. `tests/integration/api/test_change_order_filtering.py`**

- `test_search_change_orders`: Create COs, search by partial code/name, verify results.
- `test_filter_change_orders_by_status`: Create COs with different statuses, filter by status, verify.
- `test_sort_change_orders`: Create COs with explicit timestamps/codes, sort asc/desc, verify order.

**2. `tests/integration/api/test_change_order_branching.py`**

- `test_merge_change_order`:
  - Create CO (branch A).
  - Modify CO on branch A.
  - Call `POST /merge` to main.
  - Verify changes exist on main.
  - Verify old branch version is closed.
- `test_revert_change_order`:
  - Create CO, modify it.
  - Call `POST /revert`.
  - Verify state matches previous version.

### Implementation Strategy

1.  **Service Layer (`change_order_service.py`)**:

    - Update `get_change_orders` signature to accept `search`, `filters`, `sort_field`, `sort_order`.
    - Import `FilterParser`.
    - Construct dynamic `stmt` using `_apply_filters` helper logic (similar to WBE).

2.  **API Layer (`change_orders.py`)**:
    - Update `read_change_orders` dependency injection to match new service signature.
    - Implement `merge_change_order` route (calls `service.merge_branch`).
    - Implement `revert_change_order` route (calls `service.revert`).

## 6. Effort Estimation

- **Development**: 4 hours
- **Testing**: 2 hours
- **Review**: 1 hour
- **Total**: ~1 day

## 7. Prerequisites

- Existing `BranchableService` methods are verified (Command pattern logic).
- `FilterParser` is available in `app.core.filtering`.

## Links

- `backend/app/services/change_order_service.py`
- `backend/app/api/routes/change_orders.py`
- `backend/app/core/filtering.py`
