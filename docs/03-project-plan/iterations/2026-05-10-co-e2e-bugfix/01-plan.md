# Plan: Change Order E2E Lifecycle Bug Fixes (Round 2)

**Created:** 2026-05-10
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 2 (Root Cause Fix)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 2 -- Root Cause Fix (Systematic Correction)
- **Architecture**: Fix each bug at the architectural level, consolidating versioning logic for bitemporal overlap prevention, atomic SLA cleanup, and RBAC permission alignment. No refactoring beyond what is needed to address root causes.
- **Key Decisions**:
  1. BUG-1 + BUG-2 share a root cause in `UpdateChangeOrderStatusCommand` -- fix them together at the command layer
  2. BUG-3: Add `change-order-approve` to the viewer role in RBAC seed data (pragmatic sub-option (a)), since the approval matrix already validates authority at service level
  3. BUG-4: Clear SLA fields atomically via `additional_updates` in the status command, avoiding an extra version
  4. BUG-5: Verify TanStack Query cache invalidation scope and add explicit detail query invalidation
  5. BUG-6: Suppress 403 error toasts for viewer users via `meta: { suppressToast: true }` pattern

### Success Criteria

**Functional Criteria:**

- [ ] BUG-1: Resubmitting a Rejected CO (Rejected -> Submitted) creates exactly one current version with `upper(valid_time) IS NULL`, no overlaps VERIFIED BY: unit test in `test_change_order_workflow_service.py`
- [ ] BUG-2: No empty valid_time ranges are created during any status transition VERIFIED BY: unit test verifying `NOT isempty(valid_time)` for all versions after rejection + resubmission
- [ ] BUG-3: Viewer-level users assigned by the approval matrix can approve LOW-impact COs without permission errors VERIFIED BY: unit test verifying viewer has `change-order-approve` permission
- [ ] BUG-4: After Approved -> Implemented transition, all SLA fields are cleared atomically in a single version VERIFIED BY: unit test verifying SLA fields are None/completed post-merge
- [ ] BUG-5: After any workflow action, both the CO detail card and workflow panel show the updated status VERIFIED BY: manual E2E verification + frontend unit test for cache invalidation
- [ ] BUG-6: Viewer users navigating to CO pages see no "Insufficient permissions" toasts VERIFIED BY: manual verification

**Technical Criteria:**

- [ ] Performance: `NOT isempty(valid_time)` WHERE clause does not degrade temporal queries VERIFIED BY: existing test suite timing (no regression >5%)
- [ ] Security: RBAC change adds permission only; does not remove or weaken existing permissions VERIFIED BY: existing RBAC test suite passes
- [ ] Code Quality: MyPy strict (zero errors), Ruff (zero errors) on changed files VERIFIED BY: `ruff check` + `mypy` on modified files

### Scope Boundaries

**In Scope:**

- BUG-1: Bitemporal version overlap on resubmission (backend, `UpdateChangeOrderStatusCommand`)
- BUG-2: Empty valid_time range blocking transitions (backend, `UpdateChangeOrderStatusCommand`)
- BUG-3: RBAC permission for viewer approval (backend, RBAC seed/config)
- BUG-4: SLA field cleanup on implementation (backend, `merge_change_order`)
- BUG-5: Frontend stale data after status transition (frontend, TanStack Query)
- BUG-6: Viewer permission toasts on CO pages (frontend, error handling)

**Out of Scope:**

- ISSUE-7 (antd v6 deprecation warnings) -- cosmetic, tracked separately
- ISSUE-8 (Approval tab initially collapsed) -- cosmetic, tracked separately
- System-wide EVCS framework hardening (Option 3 from analysis)
- Frontend UI issues from the previous iteration (tracked in `2026-05-09-co-lifecycle-bugfix`)

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|------------------|------------|
| 1 | BUG-1+BUG-2: Fix bitemporal overlap and empty range in `UpdateChangeOrderStatusCommand` | `app/core/versioning/commands.py`, `app/core/branching/service.py` | None | Resubmission creates exactly one current version; no empty ranges | High |
| 2 | BUG-1+BUG-2: Add `NOT isempty(valid_time)` to `get_as_of` time-travel path | `app/core/branching/service.py` | None | Time-travel queries exclude empty ranges | Medium |
| 3 | BUG-1+BUG-2: Unit tests for resubmission + empty range scenarios | `tests/unit/services/test_change_order_workflow_service.py`, `tests/unit/core/test_branchable_service.py` | Task 1, Task 2 | Tests pass for rejection->resubmission lifecycle; empty range never created | Medium |
| 4 | BUG-3: Add `change-order-approve` to viewer role in RBAC config | `app/core/enums.py`, `app/core/rbac.py` or DB seed | None | Viewer role includes `change-order-approve`; existing tests pass | Low |
| 5 | BUG-3: Unit test for viewer approval permission | `tests/unit/services/test_change_order_workflow_service.py` or RBAC test file | Task 4 | Viewer can approve LOW-impact COs per approval matrix | Low |
| 6 | BUG-4: Clear SLA fields atomically in `merge_change_order` via `additional_updates` | `app/services/change_order_service.py` | None | SLA fields cleared in same version as status transition | Medium |
| 7 | BUG-4: Unit test for SLA cleanup on implementation | `tests/unit/services/test_change_order_workflow_service.py` or merge test | Task 6 | SLA fields verified as None/completed post-merge | Low |
| 8 | BUG-5: Fix TanStack Query cache invalidation for CO detail | `frontend/src/features/change-orders/api/useChangeOrders.ts`, `frontend/src/pages/projects/change-orders/ChangeOrderUnifiedPage.tsx` | None | Both detail card and workflow panel update after workflow action | Medium |
| 9 | BUG-6: Suppress 403 error toasts for viewer users on CO pages | `frontend/src/pages/projects/change-orders/ChangeOrderUnifiedPage.tsx` | None | No permission toasts for viewer users | Low |

### Dependency Graph

```
Task 1 (BUG-1+2 commands fix) ──┐
Task 2 (BUG-1+2 get_as_of fix) ──┤
                                  ├──> Task 3 (BUG-1+2 tests)
                                  │
Task 4 (BUG-3 RBAC config) ──────┴──> Task 5 (BUG-3 test)
Task 6 (BUG-4 SLA cleanup) ──────────> Task 7 (BUG-4 test)
Task 8 (BUG-5 cache fix)     [independent]
Task 9 (BUG-6 toast fix)     [independent]
```

**Parallelization:** Tasks 1+2, 4, 6, 8, 9 are all independent and can run in parallel. Task 3 depends on 1+2; Task 5 depends on 4; Task 7 depends on 6.

---

## Test Specification

### Test Hierarchy

```
tests/
├── unit/
│   ├── services/
│   │   ├── test_change_order_workflow_service.py    (BUG-1, BUG-2, BUG-4)
│   │   └── test_change_order_merge_orchestration.py (BUG-4 SLA)
│   └── core/
│       └── test_branchable_service.py               (BUG-1+2 get_as_of)
├── unit/ (RBAC)
│   └── test_rbac_viewer_approval.py                 (BUG-3)
└── frontend/
    └── features/change-orders/
        └── __tests__/                               (BUG-5, BUG-6)
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Verification |
|---------|-----------|-----------|------|-------------|
| T-001 | `test_resubmission_creates_single_current_version` | BUG-1 | Unit | After Rejected->Submitted, exactly one row has `upper(valid_time) IS NULL` for the entity on the branch |
| T-002 | `test_no_empty_valid_time_after_rejection_resubmission` | BUG-2 | Unit | After full Reject->Resubmit cycle, `NOT isempty(valid_time)` for all versions |
| T-003 | `test_get_as_of_excludes_empty_ranges` | BUG-1 | Unit | `get_as_of` with `as_of` date never returns a version with empty valid_time |
| T-004 | `test_viewer_has_approve_permission` | BUG-3 | Unit | Viewer role includes `change-order-approve` in permission set |
| T-005 | `test_sla_fields_cleared_on_implementation` | BUG-4 | Unit | After merge to Implemented, `sla_status='completed'`, `assigned_approver_id=None`, `sla_assigned_at=None`, `sla_due_date=None` |
| T-006 | `test_sla_cleanup_atomic_single_version` | BUG-4 | Unit | SLA cleanup creates zero additional versions beyond the status transition version |
| T-007 | `test_cache_invalidated_after_workflow_action` | BUG-5 | Unit (frontend) | After mutation success, both `queryKeys.changeOrders.all` and `queryKeys.changeOrders.detail()` are invalidated |

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|-----------|-------------|-------------|--------|------------|
| Technical | BUG-1+2 fix in `UpdateChangeOrderStatusCommand` may affect other entities using the same command | Medium | High | Run existing unit tests for all entities that use `UpdateChangeOrderStatusCommand`; only Change Orders use it currently |
| Technical | Adding `NOT isempty(valid_time)` to queries may change semantics for entities with legitimately empty ranges | Low | Medium | Verify no existing entities have empty ranges via DB query before deploying |
| Integration | RBAC permission addition may conflict with existing permission tests that assert exact viewer permission sets | Low | Low | Update viewer permission assertions in existing tests if needed |
| Regression | BUG-5 cache invalidation fix may over-invalidate, causing excessive refetches | Low | Low | Verify with browser dev tools that invalidation is scoped correctly |

---

## Documentation References

### Required Reading

- Backend Coding Standards: `docs/02-architecture/backend/coding-standards.md`
- EVCS Entity Classification: `docs/02-architecture/backend/contexts/evcs-core/entity-classification.md`
- Change Management User Stories: `docs/01-product-scope/change-management-user-stories.md`
- Previous Iteration: `docs/03-project-plan/iterations/2026-05-09-co-lifecycle-bugfix/`

### Code References

- `UpdateChangeOrderStatusCommand`: `app/core/versioning/commands.py` lines 574-748
- `BranchableService.get_as_of()`: `app/core/branching/service.py` lines 483-607
- `merge_change_order()`: `app/services/change_order_service.py` lines 782-971
- `reject_change_order()`: `app/services/change_order_service.py` lines 1336-1473
- RBAC permission map: `app/core/enums.py` lines 88-136
- `RoleChecker`: `app/api/dependencies/auth.py` lines 65-131
- TanStack Query keys: `frontend/src/features/change-orders/api/useChangeOrders.ts`
- CO Unified Page: `frontend/src/pages/projects/change-orders/ChangeOrderUnifiedPage.tsx`

---

## Prerequisites

### Technical

- [x] Database is running (PostgreSQL 15+)
- [x] Backend virtual environment activated
- [x] Previous iteration patches applied (branch `agent-architecture`)
- [ ] Existing tests pass on current branch before starting

### Documentation

- [x] Analysis phase approved (Option 2 selected)
- [x] Architecture docs reviewed
