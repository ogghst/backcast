# Assessment: Branch Routes & Service vs WBE Implementation

## Request Analysis: Assessment of Branch/ChangeOrder Implementation

### Clarified Requirements

The user requests an assessment of the "Branch" (implemented as Change Order) routes, command, and service implementation, comparing them against the "WBE" implementation. Both entities share the same underlying versioning patterns (Event Sourcing / Command Pattern).

**Goals:**

1. Compare the implementation of `ChangeOrderService` (Branching) vs `WBEService` (Temporal).
2. Compare the API Routes (`/change-orders` vs `/wbes`).
3. Identify gaps, inconsistencies, or missing features in the Branch/ChangeOrder implementation relative to the WBE baseline.
4. Propose solutions to harmonize and complete the implementation.

### Context Discovery Findings

**Product Scope:**

- **WBEs**: Core structural entities. High volume, hierarchical, read-heavy. Need complex filtering and tree navigation.
- **Change Orders (Branches)**: Workflow entities. Represent a parallel timeline. Manage the lifecycle of a "Branch".
- **Shared Pattern**: Both use the `core.versioning` Command Pattern (`CreateVersionCommand`, `UpdateVersionCommand`, `SoftDeleteCommand`) and Bitemporal Data Model (`valid_time`, `transaction_time`).

**Architecture Context:**

- **WBE Service**: Inherits from `TemporalService`. Optimized for **Branch Consumption** (reading/writing data _on_ a specific branch). Handles recursion (parents/children).
- **Change Order Service**: Inherits from `BranchableService` (which extends `BranchableProtocol`). Optimized for **Branch Production** (creating, merging, reverting branches).
- **Core Discrepancy**: `TemporalService` and `BranchableService` appear to be parallel base classes. `BranchableService` re-implements some retrieval logic (`get_current`) found in `TemporalService`.

**Codebase Analysis (Comparison):**

| Feature              | WBE Implementation (`wbe.py`, `wbes.py`)                                     | Change Order Implementation (`change_order_service.py`, `change_orders.py`)                     |
| :------------------- | :--------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------- |
| **Service Base**     | `TemporalService`                                                            | `BranchableService`                                                                             |
| **Branching Role**   | **Consumer**: Lives on a branch.                                             | **Producer**: Defines/Manages a branch (`BR-{code}`).                                           |
| **Filtering (List)** | **Rich**: Parsing `filters` string, `project_id`, `parent_wbe_id`, `search`. | **Basic**: Only `project_id` and `branch`. Missing generic search/filter.                       |
| **Sorting**          | **Dynamic**: `sort_field`, `sort_order`.                                     | **Fixed**: Implicitly by time (desc) in service queries? (Query hardcodes `valid_time.desc()`). |
| **Branch Ops**       | Read/Write on active branch.                                                 | `create_branch` (auto), `merge_branch`, `revert`.                                               |
| **Route Exposure**   | CRUD + Breadcrumb + History.                                                 | CRUD + `by-code` + History. **MISSING**: Merge/Revert endpoints.                                |
| **Response Type**    | `PaginatedResponse` (for list) & List (for hierarchy).                       | `PaginatedResponse` (for list).                                                                 |

### Key Gaps Identified

1. **Missing Endpoint Exposure**: `ChangeOrderService` supports `merge_branch` and `revert`, but the `change_orders.py` router **does not expose** these capabilities. Users cannot currently merge a Change Order via API.
2. **Limited List Capabilities**: Change Order list endpoint lacks the standard filtering, searching, and sorting capabilities present in WBEs (`FilterParser` integration is missing).
3. **Code Duplication**: `BranchableService` re-implements `get_current` and `get_by_id` which likely exist in `TemporalService`.

---

## Solution Options

### Option 1: Full Parity & Exposure (Recommended)

Bring Change Order routes to full parity with WBE standards and expose the unique Branching capabilities.

**Architecture & Design:**

- **Routes**: Add `POST /{id}/merge` and `POST /{id}/revert` endpoints to `change_orders.py`.
- **List Ops**: Update `get_change_orders` to support `search`, `filters`, `sort_field`, `sort_order` using the `FilterParser` (matching WBE pattern).
- **Service**: Update `ChangeOrderService.get_change_orders` to apply dynamic filters.

**UX Design:**

- Users can search for COs by code/name.
- Users can sort COs by status/date.
- Frontend can implement "Merge" button triggered via API.

**Trade-offs:**

- **Pros**: Consistent API experience. Unlocks Merge functionality.
- **Cons**: higher effort than doing nothing.
- **Complexity**: Medium.

### Option 2: Minimal "Merge" Exposure

Only add the missing Merge/Revert endpoints, ignoring the List/Filter disparities.

**Architecture & Design:**

- **Routes**: Add `POST /{id}/merge`.
- **Ignore**: List filtering/sorting (keep as is).

**Trade-offs:**

- **Pros**: Quick win. Unlocks core workflow.
- **Cons**: List view remains inferior to WBE. Inconsistent developer experience (pagination/filtering differs).
- **Complexity**: Low.

### Option 3: Service Refactoring & Unification

Refactor `BranchableService` to inherit from `TemporalService` to remove duplication, then apply Option 1.

**Architecture & Design:**

- **Core**: Refactor `BranchableService(TemporalService)`.
- **Cleanup**: Remove duplicate `get_current` logic.
- **Routes**: Implement Option 1.

**Trade-offs:**

- **Pros**: Better code quality and maintainability ("DRY").
- **Cons**: Higher risk of regression in Core. High effort.
- **Complexity**: High.

---

## Comparison Summary

| Criteria         | Option 1 (Full Parity) | Option 2 (Merge Only) | Option 3 (Refactor) |
| :--------------- | :--------------------- | :-------------------- | :------------------ |
| **Completeness** | High                   | Medium                | High                |
| **Consistency**  | High                   | Low                   | Very High           |
| **Effort**       | Medium                 | Low                   | High                |
| **Risk**         | Low                    | Low                   | Medium              |

## Recommendation

**I recommend Option 1 (Full Parity & Exposure).**

**Rationale:**

1. The primary purpose of Change Orders is to manage the branching lifecycle. Without `merge` endpoints, the feature is incomplete.
2. WBEs set the standard for List operations (Filtering/Sorting). Change Orders should match this standard to ensure a consistent Frontend capability (Search/Sort).
3. Refactoring (Option 3) is desirable but can be done as a separate technical debt task; it shouldn't block the feature completion.

**Action Plan:**

1. Update `ChangeOrderService` to accept `search`, `filters`, `sort` arguments.
2. Update `change_orders.py` router to accept these parameters and pass them.
3. Add `POST /{change_order_id}/merge` endpoint to `change_orders.py`.
4. Add `POST /{change_order_id}/revert` endpoint to `change_orders.py` (if needed by UI).

## Output file

Created: 2026-01-12
Links:

- `backend/app/api/routes/wbes.py`
- `backend/app/api/routes/change_orders.py`
- `backend/app/services/wbe.py`
- `backend/app/services/change_order_service.py`
