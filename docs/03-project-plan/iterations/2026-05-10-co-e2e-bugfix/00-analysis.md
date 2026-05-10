# Analysis: Change Order E2E Lifecycle Bug Fixes (Round 2)

**Created:** 2026-05-10
**Request:** Fix 8 issues (2 Critical, 1 High, 2 Medium, 3 Low/Cosmetic) found during E2E change order lifecycle testing covering bitemporal overlap on resubmission, empty range creation, RBAC approval matrix conflict, SLA field lifecycle, frontend stale cache, viewer permission toasts, antd deprecation warnings, and collapsed approval tab.

---

## Clarified Requirements

### Functional Requirements

**BUG-1 (CRITICAL): Bitemporal Version Overlap on Resubmission**
When resubmitting a Rejected CO (Rejected -> Submitted for Approval), the old version's `valid_time` upper bound is NOT properly closed. Two rows end up with `upper(valid_time) IS NULL` for the same root entity on the same branch. The `get_as_of` query returns the stale Rejected version because the "time travel" path (when `as_of` is provided) does not exclude empty ranges or apply proper ordering.

**BUG-2 (CRITICAL): Empty Valid Time Range Blocking Transitions**
After a rejection, the EVCS creates a version with `valid_time = empty`. PostgreSQL's GIST exclusion constraint considers empty ranges as overlapping with `[a, NULL)`, blocking subsequent transitions with "Overlapping version detected".

**BUG-3 (HIGH): RBAC Blocks Viewer Approval Despite Approval Matrix Assignment**
The approval matrix (`co_approval_rule_config`) assigns LOW-impact COs to viewer-level users, but viewers lack the `change-order-update` or `change-order-approve` permission. The PUT `/{id}` endpoint uses `change-order-update`, while approve/reject endpoints correctly use `change-order-approve`. Viewers have `change-order-read` only.

**BUG-4 (MEDIUM): SLA Fields Not Cleared on Implementation**
After merging (Approved -> Implemented), SLA fields (`sla_status`, `assigned_approver_id`, `sla_assigned_at`, `sla_due_date`) remain populated with pre-implementation values instead of being cleared or set to a terminal state.

**BUG-5 (MEDIUM): Frontend Stale Data After Status Transition**
After a workflow action (Submit, Approve, Reject), the CO detail card shows stale status while the workflow panel updates. Root cause: TanStack Query cache invalidation scope mismatch between the workflow mutation and the CO detail query key.

**BUG-6 (LOW): Viewer Permission Toasts on CO Pages**
Viewer users see "Insufficient permissions for project" toasts and UUID breadcrumb when navigating to CO pages. Parallel project-detail requests fail with 403.

**ISSUE-7 (LOW): antd v6 Deprecation Warnings**
Three deprecation warnings in browser console from antd v6 API changes.

**ISSUE-8 (COSMETIC): Approval Tab Initially Collapsed**
Approval Information card starts collapsed with no visible content.

### Non-Functional Requirements

- All fixes must preserve bitemporal data integrity across valid_time and transaction_time dimensions
- EVCS temporal queries must remain performant (GIST indexes, exclusion constraints)
- RBAC changes must not weaken security -- only add approval-specific permissions where the approval matrix authorizes them
- Frontend fixes must not break existing CO creation, submission, approval, or merge flows

### Constraints

- Changes build on top of the previous iteration's fixes (2026-05-09-co-lifecycle-bugfix)
- The `UpdateChangeOrderStatusCommand` in `app/core/versioning/commands.py` is the central command for all status transitions and must be the single point of fix for BUG-1 and BUG-2
- The RBAC permission model uses database-backed roles (`DatabaseRBACService`) with project-level role assignments, not the legacy `ProjectRole` enum
- Change Order approve/reject endpoints already use `change-order-approve` permission (correct). BUG-3 is specifically about the generic PUT endpoint using `change-order-update` which viewers lack

---

## Context Discovery

### Product Scope

- User stories: `docs/01-product-scope/change-management-user-stories.md`
  - Section 3.2: Approval workflow with role-based authority
  - Section 3.6: Merge to Implemented (terminal state)
  - Section 4: State machine -- Rejected allows resubmission to Draft or Submitted
- Business rule: LOW-impact COs should be approvable by viewer-level users per the configurable approval matrix

### Architecture Context

**Bounded contexts involved:**
- EVCS Core (bitemporal versioning, branch isolation)
- Change Management (CO lifecycle, approval matrix, SLA tracking)
- Auth/RBAC (role-based permissions, project membership)

**Existing patterns to follow:**
- `UpdateChangeOrderStatusCommand` handles all status transitions with raw SQL for temporal correctness
- `BranchableService.get_as_of()` provides two paths: "current version" (no `as_of`) and "time travel" (with `as_of`)
- RBAC `RoleChecker` dependency enforces permission checks on API routes
- TanStack Query `queryKeys.changeOrders.*` manages cache scoping

**Architectural constraints:**
- PostgreSQL TSTZRANGE with GIST indexes -- empty ranges must be prevented, not just handled in queries
- Bitemporal correctness: `valid_time` tracks business validity, `transaction_time` tracks recording time
- No repository pattern -- services access DB directly via `AsyncSession`

### Codebase Analysis

**Backend:**

Key files analyzed:
- `backend/app/core/branching/service.py` -- `BranchableService.get_as_of()` lines 483-607
- `backend/app/core/branching/commands.py` -- `UpdateCommand`, `MergeBranchCommand`
- `backend/app/core/versioning/commands.py` -- `UpdateChangeOrderStatusCommand` lines 574-748
- `backend/app/services/change_order_service.py` -- `reject_change_order()` lines 1336-1473, `merge_change_order()` lines 782-971
- `backend/app/api/routes/change_orders.py` -- route-level RBAC, approve/reject at lines 772-869
- `backend/app/api/dependencies/auth.py` -- `RoleChecker` lines 65-131
- `backend/app/core/rbac.py` -- permission map lines 44-77 (hardcoded fallback)
- `backend/app/core/enums.py` -- project role permissions lines 88-136
- `backend/app/services/approval_matrix_service.py` -- authority validation lines 92-133

**Frontend:**

Key files analyzed:
- `frontend/src/pages/projects/change-orders/ChangeOrderUnifiedPage.tsx` -- page layout, query usage
- `frontend/src/features/change-orders/api/useChangeOrders.ts` -- hooks, mutation cache handling
- `frontend/src/features/change-orders/components/ApprovalInfo.tsx` -- approval display
- `frontend/src/features/change-orders/components/ChangeOrderSummaryCard.tsx` -- detail card

---

## Solution Options

### Option 1: Surgical Fix (Minimum Viable Correction)

Fix each bug at its exact root cause with the smallest possible change. No refactoring, no architectural improvement.

**BUG-1 Fix:** In `UpdateChangeOrderStatusCommand.execute()`, add `NOT isempty(valid_time)` to the current-version lookup query (line ~637). This mirrors the fix already applied to `get_as_of` for the no-`as_of` path.

**BUG-2 Fix:** In `UpdateChangeOrderStatusCommand.execute()`, add a guard after closing the old version: if the resulting range would be empty (valid_lower == control_date == valid_upper), use a microsecond-offset instead of creating a zero-length range. Alternatively, handle the `current_lower == control_date` path by ensuring `upper > lower` strictly.

**BUG-3 Fix:** Add `change-order-approve` permission to the `viewer` role in the RBAC database seed/migration. This is the minimum change -- the approval matrix already validates that only assigned approvers with sufficient authority can approve, so adding the route-level permission is just removing the gatekeeping mismatch.

**BUG-4 Fix:** In `merge_change_order()`, after the status command sets "Implemented", add an explicit update to clear SLA fields (`sla_status = 'completed'`, `assigned_approver_id = None`, etc.).

**BUG-5 Fix:** In `ChangeOrderUnifiedPage.tsx`, the workflow section already calls `queryClient.invalidateQueries({ queryKey: queryKeys.changeOrders.all })` via `onActionSuccess`. The issue is the detail query uses a different key structure. Change the `onActionSuccess` callback to also invalidate the specific detail query, or use `queryKeys.changeOrders.all` which should cover it. Verify the `queryKeys.changeOrders.detail()` key is included in the `all` pattern.

**BUG-6 Fix:** In `ChangeOrderUnifiedPage.tsx`, wrap the `useProject` call with `enabled: false` for viewer users, or handle 403 gracefully by catching the error and using the project ID as fallback for the breadcrumb.

**ISSUE-7 Fix:** Search-and-replace the three deprecated API usages.

**ISSUE-8 Fix:** Set `collapsed={false}` (already done based on code review -- the issue may be a default state issue with `CollapsibleCard`).

| Aspect          | Assessment                                 |
| --------------- | ------------------------------------------ |
| Pros            | Minimal code changes, low regression risk  |
| Cons            | Does not address systemic EVCS issues; BUG-1/BUG-2 are symptoms of deeper versioning logic |
| Complexity      | Low                                        |
| Maintainability | Fair -- patches on patches                 |
| Performance     | No impact                                  |

---

### Option 2: Root Cause Fix (Systematic Correction)

Address each bug at the architectural level, consolidating versioning logic and creating a coherent solution for the bitemporal overlap problem.

**BUG-1 + BUG-2 Combined Fix:** The root cause is that `UpdateChangeOrderStatusCommand` manages version closing and creation with raw SQL but has a subtle race condition when `control_date == current_lower` (resubmission scenario). The fix:

1. Unify the version-closing logic in `_close_version()` to always ensure `upper > lower` strictly (never empty)
2. Add `NOT isempty(valid_time)` to ALL current-version lookup queries, not just the `get_as_of` no-`as_of` path
3. In the "time travel" path of `get_as_of` (line 515-530), add `NOT isempty(valid_time)` as a WHERE condition
4. In `UpdateChangeOrderStatusCommand.execute()`, the `elif current_lower:` branch (line 691-717) closes at `update_timestamp` which is `datetime.now(UTC)`. When the resubmission happens in the same microsecond as the rejection, `update_timestamp` can equal `current_lower`, creating an empty range. Fix: use `update_timestamp + timedelta(microseconds=1)` for the upper bound when it would otherwise equal the lower bound.

**BUG-3 Fix:** Create a dedicated `change-order-approve` permission that is granted to any role authorized by the approval matrix. The approve/reject endpoints already use this permission. The issue is that the generic PUT endpoint (`PUT /{id}`) uses `change-order-update` which viewers lack. Two sub-options:
- (a) Add `change-order-approve` to the viewer role in the RBAC seed data
- (b) Split the PUT endpoint so status-only transitions use `change-order-approve` while metadata edits use `change-order-update`

Sub-option (b) is more architecturally correct but requires more changes. Sub-option (a) is the pragmatic choice since the approval matrix already validates authority at the service level.

**BUG-4 Fix:** In `merge_change_order()`, add SLA cleanup as `additional_updates` to the `UpdateChangeOrderStatusCommand` call, so it happens atomically with the status transition:
```python
status_cmd = UpdateChangeOrderStatusCommand(
    ...,
    additional_updates={
        "sla_status": "completed",
        "assigned_approver_id": None,
        "sla_assigned_at": None,
        "sla_due_date": None,
    },
)
```
This is better than the surgical fix because it avoids creating an extra version just to clear SLA fields.

**BUG-5 Fix:** The workflow section's `onActionSuccess` already invalidates `queryKeys.changeOrders.all`. Verify that `queryKeys.changeOrders.all` uses a prefix match that covers `queryKeys.changeOrders.detail(id, opts)`. If the detail key is `["change-orders", "detail", id, opts]` and `all` is `["change-orders"]`, the invalidation should work. If not, add explicit detail invalidation. Also add `queryClient.invalidateQueries({ queryKey: queryKeys.changeOrders.detail(changeOrderId!) })` in the `onActionSuccess` callback on `ChangeOrderUnifiedPage.tsx`.

**BUG-6 Fix:** In `ChangeOrderUnifiedPage.tsx`, use `useProject` with `{ retry: false }` option and render the breadcrumb with `project?.code || projectId` gracefully (already done in code). The issue is the error toasts from 403. Wrap the project query with error suppression or use a conditional query that skips for viewers. Better: add `useQuery({ ... , throwOnError: false, meta: { suppressToast: true } })` pattern.

**ISSUE-7 + ISSUE-8:** Same as Option 1.

| Aspect          | Assessment                                              |
| --------------- | ------------------------------------------------------- |
| Pros            | Addresses root causes; reduces future regression risk   |
| Cons            | More changes; touches core EVCS versioning code         |
| Complexity      | Medium                                                  |
| Maintainability | Good -- consolidates version-closing logic patterns     |
| Performance     | No negative impact; may improve by reducing empty ranges |

---

### Option 3: EVCS Framework Hardening (Comprehensive)

In addition to Option 2, refactor the EVCS command layer to prevent empty ranges and overlap issues system-wide, not just for Change Orders.

**Additional work beyond Option 2:**
1. Add a `validate_temporal_range()` method to `VersionedCommandABC` that checks for empty ranges before any UPDATE or INSERT
2. Add `NOT isempty(valid_time)` to all `_get_current` and `_get_current_on_branch` queries across the codebase
3. Add integration tests that exercise every CO lifecycle transition (Draft -> Submitted -> Rejected -> Submitted -> Approved -> Implemented) and verify temporal correctness at each step
4. Create a dedicated EVCS health-check query that detects overlapping/empty ranges for any entity

| Aspect          | Assessment                                          |
| --------------- | --------------------------------------------------- |
| Pros            | System-wide protection; future-proof                |
| Cons            | Large scope; higher regression risk; more testing   |
| Complexity      | High                                                |
| Maintainability | Good if done well; but high upfront cost            |
| Performance     | Negligible -- additional checks are simple WHERE conditions |

---

## Comparison Summary

| Criteria           | Option 1: Surgical    | Option 2: Root Cause  | Option 3: EVCS Hardening |
| ------------------ | --------------------- | --------------------- | ------------------------ |
| Development Effort | 2-3 hours             | 4-6 hours             | 8-12 hours               |
| Regression Risk    | Low                   | Medium                | High                     |
| Long-term Value    | Low                   | High                  | Very High                |
| Test Coverage      | Existing + 2-3 tests  | Existing + 5-8 tests  | Full integration suite   |
| Best For           | Hotfix/unblock        | Iteration delivery    | Architecture sprint      |

---

## Recommendation

**I recommend Option 2 (Root Cause Fix) because:**

1. BUG-1 and BUG-2 share a common root cause in `UpdateChangeOrderStatusCommand` -- fixing them together in the command layer prevents future occurrences for any entity type that uses this command
2. The SLA field cleanup (BUG-4) is best done atomically via `additional_updates` in the status command, avoiding an extra version
3. BUG-3 requires only a database seed update to add `change-order-approve` to the viewer role -- the approval matrix already validates authority at the service level
4. BUG-5 is a straightforward cache invalidation scope issue that can be verified and fixed in the frontend query hooks
5. The total effort (4-6 hours) is reasonable for an iteration and provides lasting value

**Alternative consideration:** If the CO lifecycle must be unblocked immediately (production issue), use Option 1 for BUG-1/BUG-2 as a hotfix, then follow up with Option 2 in the next iteration.

---

## Dependency Map

```
BUG-1 + BUG-2 (shared root cause in UpdateChangeOrderStatusCommand)
  |
  +--> Must be fixed first (critical, blocks resubmission workflow)
  |
BUG-3 (independent, RBAC config)
  |
BUG-4 (independent, SLA lifecycle)
  |
BUG-5 (independent, frontend cache)
  |
BUG-6 (independent, frontend error handling)
  |
ISSUE-7 + ISSUE-8 (independent, cosmetic)
```

**Recommended implementation order:**
1. BUG-1 + BUG-2: Backend EVCS temporal fix + test coverage
2. BUG-3: RBAC permission update + test
3. BUG-4: SLA cleanup in merge_change_order + test
4. BUG-5: Frontend query invalidation fix
5. BUG-6: Frontend error suppression
6. ISSUE-7 + ISSUE-8: Frontend cosmetic fixes

---

## Decision Questions

1. For BUG-3, should we add `change-order-approve` to the viewer role system-wide, or should the approval matrix dynamically grant approval permissions per-CO based on impact level assignment? The former is simpler but broader; the latter is more secure but requires custom RBAC middleware.

2. For BUG-1/BUG-2, should the empty-range prevention be implemented in `_close_version()` (affecting all entities) or only in `UpdateChangeOrderStatusCommand` (CO-specific)? The former is safer but requires regression testing across all entity types.

3. Should BUG-4 clear SLA fields entirely (`sla_status = None`) or set them to a terminal state (`sla_status = 'completed'`)? The latter preserves audit trail but requires frontend handling of the `completed` state.

---

## References

- [EVCS Entity Classification](../../../02-architecture/backend/contexts/evcs-core/entity-classification.md)
- [Change Management User Stories](../../../01-product-scope/change-management-user-stories.md)
- [Previous Iteration Analysis](../2026-05-09-co-lifecycle-bugfix/00-analysis.md)
- [Backend Coding Standards](../../../02-architecture/backend/coding-standards.md)
- [Frontend Coding Standards](../../../02-architecture/frontend/coding-standards.md)
