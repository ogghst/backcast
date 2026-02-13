# Analysis: Merge Branch Logic

## 1. Requirements Clarification

### User Intent

The goal is to finalize the lifecycle of a Change Order by implementing the "Merge" capability. This allows changes developed in an isolated branch (`BR-{id}`) to be applied to the target branch (usually `main`), updating the live project baseline. This is a critical feature for the Change Management module (Epic 6, Phase 4).

### Key Requirements

1. **Conflict Detection**: Before merging, the system must identify if any entities have been modified effectively in both branches since they diverged.
2. **Merge Logic**: If no blocking conflicts exist, apply changes from the source branch to the target branch.
    - **Create**: Entities new in source -> Create in target.
    - **Update**: Entities modified in source -> Update in target.
    - **Delete**: Entities soft-deleted in source -> Soft-delete in target.
3. **Workflow Integration**: The merge action is triggered from the "Approved" state and transitions the CO to "Implemented".
4. **Audit Trail**: The operation must be logged, and the source branch should be marked as merged (conceptually, though we might keep it for history).

## 2. Context Discovery

### Documentation

- **Functional Requirements**: Change Management User Stories (FR-8.4.12, 8.4.13) describe the merge process.
- **Architecture**: `BranchableService` already contains `_detect_merge_conflicts` and `merge_branch`.
- **Current State**:
  - `ChangeOrderService` has a `merge_change_order` method.
  - API route `POST /{id}/merge` exists but uses `ChangeOrderService.merge_change_order`.
  - Frontend `WorkflowButtons` has a `handleMerge` action.

### Codebase Analysis (Backend)

- `app/core/branching/commands/merge_branch_command.py` (Assuming existence based on service usages) seems to implement the low-level logic.
- `ChangeOrderService.merge_change_order` orchestrates the process.
- **Gap**: Tests for the specific API orchestration are missing (as identified in previous turn).
- **Gap**: Need to confirm `MergeBranchCommand` fully handles all entity types (WBE, CostElement, etc.) including recursive structures if needed, although `BranchableService` usually handles single-root aggregates. Since WBEs and CostElements are branchable roots themselves (or are they children?), we need to ensure the merge command handles them correctly.
  - _Correction_: Cost Elements and WBEs are `Branchable` roots in this architecture. A Change Order might touch multiple WBEs/CostElements.
  - _Crucial Detail_: The `MergeBranchCommand` in `BranchableService` seems to operate on a _single_ entity type (TBranchable). A Change Order might affect _many_ entities spanning different types.
  - _Hypothesis_: The current `merge_branch` in `BranchableService` might only merge _one_ specific entity (e.g., if I merge a Project, does it merge all children?).
  - _Refinement_: If WBEs and Cost Elements are separate aggregates, iterating over _all_ changed entities in a branch is required.
  - **Investigation**: Does `ChangeOrderService.merge_change_order` simply call `merge_branch` on the _Change Order_ entity? If so, that just merges the CO metadata. It does _not_ merge the content of the branch (the WBEs/CostElements).
  - **Major Gap Identification**: `ChangeOrderService.merge_change_order` must iterate over ALL changed entities in the `BR-{id}` branch and merge them to `main`. It cannot just merge the CO record itself.

### Codebase Analysis (Frontend)

- `WorkflowButtons` calls `merge` mutation.
- `MergeConflictsList` displays conflicts.
- This looks ready for the "happy path" assuming the backend does the heavy lifting.

## 3. Solution Design

### Option 1: Iterative Merge Service (Recommended)

Modify `ChangeOrderService.merge_change_order` to:

1. Identify all modified entities in the source branch (`BR-{code}`).
2. Iterate through them (Projects, WBEs, Cost Elements).
3. For each, invoke `BranchableService.merge_branch` (or equivalent command) to merge to `main`.
4. Update CO status to "Implemented".

**Pros**: Explicit control, uses existing granular merge commands.
**Cons**: Requires discovering all changed entities efficiently.

### Option 2: Database-Level Bulk Merge

Use a complex SQL query to merge everything in one go.

**Pros**: Performance.
**Cons**: Bypasses application logic/validation, harder to test, riskier.

### Option 3: Current Implementation Check

Check if `ChangeOrderService.merge_change_order` currently _only_ merges the CO entity itself. If so, it is incomplete.

**Action**: I need to check `app/services/change_order_service.py` again specifically for the merge logic implementation details.

## 4. Recommendation

Proceed with **Option 1**. The `ChangeOrderService` must orchestrate the merge of the _content_ of the branch, not just the CO entity.

## 5. Decision Questions

- Is the assumption that "Change Order = Branch Content" correct? (Yes, FR-8.1).
- Should we verify the "Find all changes" logic?

(Self-correction: I will assume Option 1 is the intended path and verify the current code during the Plan phase).
