# Plan: E06-U08 Delete/Archive Branches - Explicit Archive Action

**Created:** 2026-02-25
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 - Explicit Archive Action

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 - Explicit Archive Action from analysis
- **Architecture**: Add explicit "Archive Branch" button with confirmation modal, wired to existing backend service method
- **Key Decisions**:
  - User explicitly triggers archive after merge/rejection (no automatic behavior)
  - Follow existing confirmation modal pattern from Reject/Merge workflows
  - Archive button visible only for Implemented/Rejected status
  - Clear audit trail preserved via bitemporal soft-delete

### Success Criteria

**Functional Criteria:**

- [ ] Archive button appears in WorkflowButtons only when Change Order status is "Implemented" or "Rejected" VERIFIED BY: frontend unit test
- [ ] Clicking Archive button opens confirmation modal with warning message VERIFIED BY: frontend unit test
- [ ] Confirming archive calls backend endpoint and shows success toast VERIFIED BY: integration test
- [ ] Archived branch no longer appears in active branch selector VERIFIED BY: E2E test
- [ ] Backend rejects archive request for non-terminal status (Draft, Submitted, etc.) VERIFIED BY: backend unit test
- [ ] Archived branch remains visible in time-travel queries VERIFIED BY: existing integration test

**Technical Criteria:**

- [ ] Performance: Archive operation completes within 2 seconds VERIFIED BY: manual testing
- [ ] Security: Archive requires change-order-update permission VERIFIED BY: RBAC enforcement
- [ ] Code Quality: mypy strict + ruff clean VERIFIED BY: CI pipeline

**TDD Criteria:**

- [ ] All tests written before implementation code
- [ ] Each test failed first (documented in DO phase log)
- [ ] Test coverage >= 80%
- [ ] Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- Backend API endpoint `POST /{change_order_id}/archive-branch`
- Frontend mutation hook `useArchiveChangeOrder`
- Frontend workflow action `archive()` in `useWorkflowActions.ts`
- Archive button with confirmation modal in `WorkflowButtons.tsx`
- Unit tests for all new components
- Query invalidation after successful archive

**Out of Scope:**

- Automatic archival on merge (Option 2 from analysis)
- User preference settings for auto-archive (Option 3 from analysis)
- Restore/unarchive functionality
- Bulk archive operations
- Notification emails on archive

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|--------------|------------------|------------|
| 1 | Backend: Add `POST /{change_order_id}/archive-branch` API endpoint | `backend/app/api/routes/change_orders.py` | None | Endpoint returns 200 with updated ChangeOrderPublic; rejects non-terminal status with 400 | Low |
| 2 | Backend: Add unit tests for archive endpoint | `backend/tests/unit/routes/test_change_orders_archive.py` (new file) | Task 1 | Tests cover happy path, invalid status, not found scenarios | Low |
| 3 | Frontend: Add `useArchiveChangeOrder` mutation hook | `frontend/src/features/change-orders/api/useApprovals.ts` | None | Hook calls endpoint, invalidates queries, shows toast | Low |
| 4 | Frontend: Add `archive()` action to `useWorkflowActions.ts` | `frontend/src/features/change-orders/hooks/useWorkflowActions.ts` | Task 3 | Archive action available, integrates with mutation | Low |
| 5 | Frontend: Add Archive button to `WorkflowButtons.tsx` | `frontend/src/features/change-orders/components/WorkflowButtons.tsx` | Task 4 | Button appears for Implemented/Rejected status | Medium |
| 6 | Frontend: Add archive confirmation modal | `frontend/src/features/change-orders/components/WorkflowButtons.tsx` | Task 5 | Modal shows warning, comment input, confirm/cancel buttons | Medium |
| 7 | Frontend: Add unit tests for Archive button and modal | `frontend/src/features/change-orders/components/WorkflowButtons.test.tsx` | Task 5, 6 | Tests cover button visibility, modal interaction, action trigger | Medium |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|----------------------|---------|-----------|-------------------|
| Archive button appears for Implemented/Rejected | T-FE-001 | `WorkflowButtons.test.tsx` | Button rendered when status is terminal |
| Archive button hidden for non-terminal status | T-FE-002 | `WorkflowButtons.test.tsx` | Button not rendered for Draft/Submitted/Under Review |
| Confirmation modal displays warning | T-FE-003 | `WorkflowButtons.test.tsx` | Modal contains archival warning text |
| Backend rejects non-terminal status | T-BE-001 | `test_change_orders_archive.py` | Returns 400 with error message |
| Backend accepts terminal status | T-BE-002 | `test_change_orders_archive.py` | Returns 200 with updated CO |
| Archive mutation invalidates queries | T-FE-004 | `useApprovals.test.ts` (new) | Query invalidation called on success |
| Time-travel still shows archived branch | T-BE-003 | Existing: `test_change_order_branch_archive.py` | Branch visible via get_by_name_as_of |

---

## Test Specification

### Test Hierarchy

```
tests/
├── Backend Unit Tests
│   └── test_change_orders_archive.py (new)
│       ├── test_archive_implemented_change_order_success
│       ├── test_archive_rejected_change_order_success
│       ├── test_archive_active_change_order_fails
│       └── test_archive_nonexistent_change_order_fails
├── Backend Integration Tests
│   └── test_change_order_branch_archive.py (existing)
│       ├── test_archive_implemented_change_order
│       └── test_archive_active_change_order_fails
├── Frontend Unit Tests
│   ├── WorkflowButtons.test.tsx (extended)
│   │   ├── Archive button visibility tests
│   │   └── Archive modal interaction tests
│   └── useWorkflowActions.test.tsx (extended)
│       └── archive action tests
└── E2E Tests (optional, manual verification)
    └── Archive workflow verification
```

### Test Cases (first 5-7)

| Test ID | Test Name | Criterion | Type | Verification |
|---------|-----------|-----------|------|--------------|
| T-BE-001 | `test_archive_implemented_change_order_success` | AC-5 | Backend Unit | Returns 200, branch soft-deleted |
| T-BE-002 | `test_archive_rejected_change_order_success` | AC-5 | Backend Unit | Returns 200, branch soft-deleted |
| T-BE-003 | `test_archive_active_change_order_fails` | AC-5 | Backend Unit | Returns 400 with "Cannot archive active" |
| T-BE-004 | `test_archive_nonexistent_change_order_fails` | AC-5 | Backend Unit | Returns 404 |
| T-FE-001 | `test archive button shows for implemented status` | AC-1 | Frontend Unit | Button in document |
| T-FE-002 | `test archive button shows for rejected status` | AC-1 | Frontend Unit | Button in document |
| T-FE-003 | `test archive button hidden for draft status` | AC-1 | Frontend Unit | Button not in document |
| T-FE-004 | `test archive modal opens on click` | AC-2 | Frontend Unit | Modal visible after click |
| T-FE-005 | `test archive action called on confirm` | AC-3 | Frontend Unit | archive() mock called |

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|-----------|-------------|-------------|--------|------------|
| Technical | Service method signature mismatch | Low | Low | Review existing `archive_change_order_branch()` before implementation |
| Integration | Query cache not invalidated properly | Medium | Medium | Follow existing invalidation pattern from reject/approve mutations |
| UX | User confusion about archive vs delete | Low | Low | Clear warning text in confirmation modal |
| Regression | Existing tests may need updates | Low | Low | Run full test suite before/after changes |

---

## Documentation References

### Required Reading

- Coding Standards: `docs/02-architecture/coding-standards.md`
- User Story: `docs/01-product-scope/epic-06-change-orders.md` (E06-U08)
- Existing Tests: `backend/tests/integration/test_change_order_branch_archive.py`

### Code References

- Backend pattern (approve endpoint): `/home/nicola/dev/backcast_evs/backend/app/api/routes/change_orders.py` (lines 705-739)
- Backend service method: `/home/nicola/dev/backcast_evs/backend/app/services/change_order_service.py` (lines 448-502)
- Frontend mutation pattern: `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/api/useApprovals.ts`
- Frontend workflow actions: `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/hooks/useWorkflowActions.ts`
- Frontend confirmation modal: `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/components/WorkflowButtons.tsx` (lines 149-168 for reject modal)

---

## Prerequisites

### Technical

- [x] Backend service method `archive_change_order_branch()` exists and is tested
- [x] Database migrations applied (no new migrations needed)
- [x] Dependencies installed
- [x] Environment configured

### Documentation

- [x] Analysis phase approved (Option 1 selected)
- [x] Architecture docs reviewed
- [x] Existing confirmation modal patterns understood

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for E06-U08 Delete/Archive Branches
# Enables parallel execution by orchestrator with multiple agents

tasks:
  # Backend Tasks (can start immediately)
  - id: BE-001
    name: "Add POST /{change_order_id}/archive-branch API endpoint"
    agent: pdca-backend-do-executor
    files:
      - "backend/app/api/routes/change_orders.py"
    dependencies: []
    description: |
      Add new endpoint that calls existing ChangeOrderService.archive_change_order_branch().
      Follow pattern from approve/reject endpoints.
      Return ChangeOrderPublic on success.

  - id: BE-002
    name: "Add unit tests for archive endpoint"
    agent: pdca-backend-do-executor
    files:
      - "backend/tests/unit/routes/test_change_orders_archive.py"
    dependencies: [BE-001]
    kind: test
    description: |
      Test cases:
      - test_archive_implemented_change_order_success
      - test_archive_rejected_change_order_success
      - test_archive_active_change_order_fails
      - test_archive_nonexistent_change_order_fails

  # Frontend Tasks (can start immediately - no API dependency for structure)
  - id: FE-001
    name: "Add useArchiveChangeOrder mutation hook"
    agent: pdca-frontend-do-executor
    files:
      - "frontend/src/features/change-orders/api/useApprovals.ts"
    dependencies: []
    description: |
      Add mutation hook following useRejectChangeOrder pattern.
      Call POST /{id}/archive-branch endpoint.
      Invalidate changeOrders and branches queries on success.
      Show success/error toasts.

  - id: FE-002
    name: "Add archive() action to useWorkflowActions"
    agent: pdca-frontend-do-executor
    files:
      - "frontend/src/features/change-orders/hooks/useWorkflowActions.ts"
    dependencies: [FE-001]
    description: |
      Add ARCHIVE action to WORKFLOW_ACTIONS constant.
      Add archive() callback using useArchiveChangeOrder mutation.
      Add isArchived helper if needed.

  - id: FE-003
    name: "Add Archive button and confirmation modal to WorkflowButtons"
    agent: pdca-frontend-do-executor
    files:
      - "frontend/src/features/change-orders/components/WorkflowButtons.tsx"
    dependencies: [FE-002]
    description: |
      Add Archive button visible only when status is Implemented or Rejected.
      Add confirmation modal with warning text.
      Wire button to archive action via modal confirmation.

  - id: FE-004
    name: "Add unit tests for Archive button and modal"
    agent: pdca-frontend-do-executor
    files:
      - "frontend/src/features/change-orders/components/WorkflowButtons.test.tsx"
      - "frontend/src/features/change-orders/hooks/useWorkflowActions.test.tsx"
    dependencies: [FE-003]
    kind: test
    description: |
      Extend existing test files with Archive button tests:
      - Button visibility for Implemented/Rejected status
      - Button hidden for Draft/Submitted status
      - Modal opens on click
      - Archive action called on confirm

  # Integration Tests (must run after all implementation)
  - id: TEST-001
    name: "Run backend tests and verify coverage"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]
    kind: test
    description: |
      Run: cd backend && uv run pytest tests/unit/routes/test_change_orders_archive.py -v
      Verify all tests pass and coverage meets threshold.

  - id: TEST-002
    name: "Run frontend tests and verify coverage"
    agent: pdca-frontend-do-executor
    dependencies: [FE-004]
    kind: test
    description: |
      Run: cd frontend && npm test -- --grep Archive
      Verify all Archive-related tests pass.

  # Quality Gates
  - id: QA-001
    name: "Backend code quality check"
    agent: pdca-backend-do-executor
    dependencies: [TEST-001]
    description: |
      Run: cd backend && uv run ruff check . && uv run mypy app/
      Verify zero errors.

  - id: QA-002
    name: "Frontend code quality check"
    agent: pdca-frontend-do-executor
    dependencies: [TEST-002]
    description: |
      Run: cd frontend && npm run lint
      Verify zero errors.
```

---

## Rollback Plan

### If Backend Changes Need Reversion

1. Remove the new endpoint from `backend/app/api/routes/change_orders.py`
2. Delete test file `backend/tests/unit/routes/test_change_orders_archive.py`
3. No database migration to revert (no schema changes)

### If Frontend Changes Need Reversion

1. Revert changes to `frontend/src/features/change-orders/api/useApprovals.ts`
2. Revert changes to `frontend/src/features/change-orders/hooks/useWorkflowActions.ts`
3. Revert changes to `frontend/src/features/change-orders/components/WorkflowButtons.tsx`
4. Revert changes to test files

### Data Integrity

- No data migration involved
- Archive operation is reversible via time-travel queries (EVCS design)
- Soft-delete preserves all historical data

---

## Implementation Notes

### Backend Endpoint Specification

```python
@router.post(
    "/{change_order_id}/archive-branch",
    response_model=ChangeOrderPublic,
    operation_id="archive_change_order_branch",
    dependencies=[Depends(RoleChecker(required_permission="change-order-update"))],
)
async def archive_change_order_branch(
    change_order_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderPublic:
    """Archive (soft-delete) a Change Order's branch.

    Only allowed for Change Orders in "Implemented" or "Rejected" status.
    Hides the branch from active lists while preserving history.

    Requires update permission.
    """
    try:
        await service.archive_change_order_branch(
            change_order_id=change_order_id,
            actor_id=current_user.user_id,
        )
        # Return updated CO
        co = await service.get_current(change_order_id)
        if not co:
            raise HTTPException(status_code=404, detail="Change Order not found")
        return await service._to_public(co)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
```

### Frontend Mutation Hook Pattern

```typescript
export const useArchiveChangeOrder = (
  mutationOptions?: Omit<
    UseMutationOptions<ChangeOrderPublic, Error, { id: string }>,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id }: { id: string }) => {
      return __request(OpenAPI, {
        method: "POST",
        url: `/api/v1/change-orders/${id}/archive-branch`,
      }) as Promise<ChangeOrderPublic>;
    },
    onSuccess: async (data, ...args) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.all,
      });
      await queryClient.invalidateQueries({
        queryKey: queryKeys.projects.branches(data.project_id.toString()),
      });
      toast.success(`Branch BR-${data.code} archived successfully`);
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error archiving branch: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};
```

### Confirmation Modal Content

```
Title: "Archive Branch"
Warning: "This will hide branch BR-{code} from the active branch list.
The branch data will be preserved for historical reference and can be
viewed using time-travel queries."

Action: [Cancel] [Archive Branch]
```
