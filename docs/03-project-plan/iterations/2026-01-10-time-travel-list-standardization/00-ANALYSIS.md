# Analysis: Standardize Bitemporal List Operations

## 1. Context & Problem Statement

We have implemented a "Time Machine" feature that allows users to view the system state as of a specific point in time. While this is implemented for specific entities (e.g., WBEs), we need to ensure this capability is standardized and strictly enforced across all versioned entities (Projects, WBEs, Cost Elements).

Currently, there may be inconsistencies in how different services handle the `as_of` parameter for list operations, potentially leading to incorrect bitemporal states (e.g., "zombie" records appearing, or missing records that should be valid).

## 2. Requirements (From User)

1.  **Standardize List Operations**: All versioned entities must expose and handle the `as_of` parameter in their list endpoints/services in a consistent manner.
2.  **Strict Bitemporal Correctness**: The system must enforce correct bitemporal filtering:
    - `valid_from <= as_of < valid_to`
    - `transaction_from <= as_of < transaction_to` (if applicable/present)
    - Handling logical deletions correctly.
3.  **Future-Proofing**: The architecture must remain open for custom joins in the future (e.g., joining Cost Elements with their valid WBE parent at time `t`), but no specific join requirements are mandated for this iteration.

## 3. Scope

**Entities to Standardize:**

- **Projects**: `ProjectService.get_projects`
- **WBEs**: `WbEsService.get_wbes` (Review and refine)
- **Cost Elements**: `CostElementService.get_cost_elements`
- **Cost Element Types**: `CostElementTypesService.get_cost_element_types` (if versioned)
- Verify other potential entities (Departments, Users - likely not versioned yet, but check).

## 4. Technical Analysis

### 4.1. Current State

- **TemporalMixin**: Likely provides the model fields (`valid_time`, `transaction_time`).
- **GenericTemporalService**: Likely contains `_get_base_stmt` or similar query builders.

### 4.2. Pattern to Enforce

We will adopt "Option 2":

- **Service Layer**: All `list` methods accept `as_of: datetime | None`.
- **Query Construction**:
  - If `as_of` is None -> Return "Current" state (only currently valid records).
  - If `as_of` is Set -> Return state at that exact timestamp.
- **Filtering Logic**:
  - Must filter where `as_of` is contained within the `valid_time` range.
  - Must filter where `as_of` is contained within the `transaction_time` range (if we strictly follow bitemporality, though often `transaction_time` is just for audit, `valid_time` is for business logic. We need to confirm if we travel by `valid_time` or `transaction_time` or both. Usually "Time Travel" implies "System Time" (Transaction Time) or "Valid Time". The user said "Strictly enforce Bitemporal Correctness", which implies dealing with 2 dimensions. However, usually for a user-facing "As Of" view, we mean "Valid At". _Correction_: If we are reconstructing history, we usually mean "what was the truth at time X". If our system is APPEND-ONLY and uses ranges, we filter by the range.
  - **Decision**: We will assume standard range filtering on the active history table/model.

### 4.3. Joining Strategy

- Queries will be kept simple (single entity fetch) where possible.
- If joins are needed (e.g. parent WBE filtering), strictly apply the time filter to the _related_ entity as well?
  - _Decision_: For now, "no specific join requirements". We will focus on the primary entity list.

## 5. Plan Outline

1.  **Audit**: Check `list` method of Project, WBE, CostElement services.
2.  **Refactor**: Apply standard `as_of` handling using a shared query generator or consistent pattern.
3.  **Verify**: Test with specific timestamps to ensure deleted items appear if they were valid at `t`, and created items don't appear if created after `t`.
