# Analysis: E06-U08 Delete/Archive Branches

**Created:** 2026-02-25
**Request:** Implement the ability to delete or archive Change Order branches after successful merge or rejection, with confirmation workflow and historical reference preservation.

---

## Clarified Requirements

This user story addresses the need to clean up completed Change Order branches from the active branch list while preserving them for historical reference. After a Change Order is merged (status: Implemented) or rejected (status: Rejected), users should be able to archive or delete the associated branch.

### Functional Requirements

1. **Delete branch after successful merge**: Allow users to delete the `BR-{code}` branch after the Change Order reaches "Implemented" status via merge
2. **Archive option for historical reference**: Soft-delete (archive) the branch, hiding it from active lists but preserving it for time-travel queries
3. **Confirmation before deletion**: Require explicit user confirmation before performing archive/delete action
4. **Status-based restriction**: Only allow archival for branches with Change Orders in "Implemented" or "Rejected" status
5. **Automatic archival option**: Optionally trigger automatic archival after successful merge

### Non-Functional Requirements

1. **Performance**: Archive operation should complete within 2 seconds
2. **Auditability**: All archive/delete actions must be logged with actor and timestamp
3. **Reversibility**: Archived branches should be recoverable via time-travel queries (EVCS design)
4. **RBAC**: Archive/delete operations require appropriate permissions

### Constraints

1. Must integrate with existing EVCS bitemporal versioning system
2. Must preserve branch data for time-travel queries
3. Must follow existing confirmation modal patterns in the frontend
4. Backend service method `archive_change_order_branch` already exists but lacks API endpoint

---

## Context Discovery

### Product Scope

- **User Story**: E06-U08 - Delete/Archive Branches
- **Business Goal**: Keep the branch list clean while maintaining complete audit trail
- **Workflow Context**: Final step after merge (Implemented) or rejection (Rejected)

### Architecture Context

- **Bounded Contexts**: Change Order Management, Branch Management
- **Existing Patterns**:
  - TemporalService provides `soft_delete()` for bitemporal entities
  - BranchService inherits from TemporalService with `soft_delete()` capability
  - Frontend uses confirmation modals for destructive actions (reject, merge)

### Codebase Analysis

**Backend - Already Implemented:**

1. **Service Method**: `ChangeOrderService.archive_change_order_branch()`
   - Location: `/home/nicola/dev/backcast_evs/backend/app/services/change_order_service.py` (lines 448-502)
   - Validates status is "Implemented" or "Rejected"
   - Uses `BranchService.soft_delete()` internally
   - Already tested in integration tests

2. **Integration Tests**: `backend/tests/integration/test_change_order_branch_archive.py`
   - Tests archive for implemented CO
   - Tests rejection of archive for active (Draft) CO
   - Verifies time-travel visibility after archive

3. **BranchService**: Inherits `soft_delete()` from `TemporalService`
   - Location: `/home/nicola/dev/backcast_evs/backend/app/services/branch_service.py`

**Backend - Missing:**

1. **API Endpoint**: No route exposes `archive_change_order_branch` functionality
2. **Response Schema**: No dedicated response schema for archive confirmation

**Frontend - Current State:**

1. **Mutations** (`useChangeOrders.ts`): Has create, update, delete, merge - NO archive mutation
2. **Workflow Buttons** (`WorkflowButtons.tsx`): Has Submit, Approve, Reject, Merge - NO Archive button
3. **Workflow Actions** (`useWorkflowActions.ts`): No archive action defined
4. **Confirmation Pattern**: Exists for Reject and Merge operations using Ant Design Modal

---

## Solution Options

### Option 1: Explicit Archive Action (Recommended)

**Architecture & Design:**
Add a new "Archive" action button that appears after merge (Implemented) or rejection. This provides explicit user control over when branches are archived.

**UX Design:**
- Add "Archive Branch" button to WorkflowButtons component
- Button appears only when status is "Implemented" or "Rejected"
- Confirmation modal with warning about branch visibility
- Success toast: "Branch BR-{code} archived successfully"
- Archived branches disappear from active branch selector

**Implementation:**

Backend:
1. Add `POST /api/v1/change-orders/{change_order_id}/archive-branch` endpoint
2. Endpoint calls existing `ChangeOrderService.archive_change_order_branch()`
3. Returns updated ChangeOrderPublic with branch status indicator

Frontend:
1. Add `useArchiveChangeOrder` mutation hook in `useChangeOrders.ts`
2. Add `archive` action to `useWorkflowActions.ts`
3. Add Archive button to `WorkflowButtons.tsx` with confirmation modal
4. Invalidate branch queries after successful archive

**Trade-offs:**

| Aspect          | Assessment                                      |
| --------------- | ----------------------------------------------- |
| Pros            | - Explicit user control<br>- Clear audit trail<br>- Matches existing workflow patterns<br>- No automatic behavior surprises |
| Cons            | - Requires manual action<br>- One more button in UI |
| Complexity      | Low - service method exists, just needs API/UI wiring |
| Maintainability | Good - follows established patterns             |
| Performance     | Excellent - single soft-delete operation        |

---

### Option 2: Automatic Archive on Merge

**Architecture & Design:**
Automatically archive the branch immediately after successful merge operation. No user action required.

**UX Design:**
- No additional button needed
- After merge success, show toast: "Change Order merged and branch archived"
- Branch automatically disappears from selector

**Implementation:**

Backend:
1. Modify `ChangeOrderService.merge_change_order()` to call `archive_change_order_branch()` after successful merge
2. Wrap both operations in transaction for atomicity
3. Return flag in response indicating branch was archived

Frontend:
1. Update merge success toast to mention archival
2. No new mutations or components needed

**Trade-offs:**

| Aspect          | Assessment                                      |
| --------------- | ----------------------------------------------- |
| Pros            | - Zero user friction<br>- Automatic cleanup<br>- Simpler UI (no new button) |
| Cons            | - No user choice in timing<br>- May surprise users expecting branch to remain visible<br>- Cannot postpone archival |
| Complexity      | Very Low - single line addition to merge method |
| Maintainability | Good - but couples merge and archive concerns   |
| Performance     | Excellent - same transaction as merge           |

---

### Option 3: Hybrid - Automatic with Override

**Architecture & Design:**
Combine automatic archival with a grace period or user preference. Allow configuration at project or user level.

**UX Design:**
- Settings toggle: "Auto-archive branches after merge"
- When enabled: Same as Option 2
- When disabled: Same as Option 1
- "Undo" option within 24-hour grace period

**Implementation:**

Backend:
1. Add `auto_archive_branches` flag to Project or User settings
2. Conditional logic in merge endpoint
3. Add "restore branch" endpoint for grace period recovery

Frontend:
1. Settings UI for auto-archive preference
2. Conditional toast messages
3. "Restore" button in Change Order detail for recently archived

**Trade-offs:**

| Aspect          | Assessment                                      |
| --------------- | ----------------------------------------------- |
| Pros            | - Maximum flexibility<br>- Supports different workflows<br>- Grace period safety net |
| Cons            | - Higher complexity<br>- More settings to manage<br>- Potential confusion about behavior |
| Complexity      | Medium - requires settings storage and conditional logic |
| Maintainability | Fair - more moving parts to maintain            |
| Performance     | Good - slight overhead from settings lookup     |

---

## Comparison Summary

| Criteria           | Option 1 (Explicit) | Option 2 (Automatic) | Option 3 (Hybrid)    |
| ------------------ | ------------------- | -------------------- | -------------------- |
| Development Effort | Low (~4 hours)      | Very Low (~1 hour)   | Medium (~8 hours)    |
| UX Quality         | High (explicit)     | Medium (no control)  | High (flexible)      |
| Flexibility        | High                | Low                  | Very High            |
| Best For           | Audit-focused teams | Speed-focused teams  | Mixed team needs     |

---

## Recommendation

**I recommend Option 1: Explicit Archive Action** because:

1. **Preserves User Intent**: Users explicitly confirm archival, maintaining clear audit trail
2. **Matches Existing Patterns**: Follows the same confirmation modal pattern as Reject and Merge
3. **Minimal Implementation Risk**: Service method exists and is tested; only API/UI wiring needed
4. **No Hidden Behavior**: Users understand exactly when and why branches disappear
5. **Future-Proof**: Can be extended with Option 3 features later if needed

**Implementation Scope:**

Backend (2-3 hours):
- Add `POST /change-orders/{id}/archive-branch` endpoint
- Add OpenAPI response documentation
- Add unit tests for new endpoint

Frontend (2-3 hours):
- Add `useArchiveChangeOrder` mutation hook
- Add `archive` action to `useWorkflowActions.ts`
- Add Archive button with confirmation modal to `WorkflowButtons.tsx`
- Update query invalidation logic

**Alternative consideration:** Choose Option 2 if the team prefers zero-friction workflows and branch visibility after merge is not a business requirement. This can be implemented in minutes by adding a single line to the merge method.

---

## Decision Questions

1. **Should archive be automatic after merge, or require explicit user action?** (affects choice between Option 1 and 2)
2. **Should rejected Change Orders also auto-archive, or only merged ones?** (affects scope of Option 2)
3. **Is there a need to restore archived branches?** (would add complexity to any option)
4. **Should the Archive button appear in the workflow buttons row or as a separate action menu item?** (UX detail)

---

## References

- [Change Order Service](/home/nicola/dev/backcast_evs/backend/app/services/change_order_service.py) - Contains `archive_change_order_branch()` method
- [Integration Tests](/home/nicola/dev/backcast_evs/backend/tests/integration/test_change_order_branch_archive.py) - Existing test coverage
- [Branch Service](/home/nicola/dev/backcast_evs/backend/app/services/branch_service.py) - `soft_delete()` inherited from TemporalService
- [API Routes](/home/nicola/dev/backcast_evs/backend/app/api/routes/change_orders.py) - Where new endpoint would be added
- [Workflow Buttons](/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/components/WorkflowButtons.tsx) - Where Archive button would be added
- [Workflow Actions Hook](/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/hooks/useWorkflowActions.ts) - Where archive action would be defined
- [Change Orders API Hook](/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/api/useChangeOrders.ts) - Where mutation hook would be added
