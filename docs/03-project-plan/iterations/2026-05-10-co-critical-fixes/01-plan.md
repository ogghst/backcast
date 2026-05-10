# Plan: Change Order Critical Fixes (Frontend Crash + User ID + Impact Analysis)

**Created:** 2026-05-10
**Based on:** User-reported issues from E2E testing
**Approved Option:** Architectural decision to standardize on `user_id` (EVCS root ID)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Standardize on `user_id` (EVCS root ID) as the system-wide user identifier
- **Architecture**: Fix frontend crash by adding missing query keys, resolve user ID inconsistency by adding `get_by_id` method to UserService, fix impact analysis by ensuring `branch_name` persistence, and improve error messages with context
- **Key Decisions**:
  1. All user references throughout the system must use `user_id` (root ID from EVCS), not `id` (database PK)
  2. UserService will expose both `get_by_root_id(user_id: str)` (EVCS standard) and `get_by_id(id: int)` (for legacy/internal use)
  3. Frontend query keys must include the `users` factory to prevent runtime crashes
  4. Impact analysis must run on all submissions, including empty branches
  5. Error messages must include actionable context (user, project, CO, action)

### Success Criteria

**Functional Criteria:**

- [ ] Priority 1: Change Order Recovery Dialog opens without `TypeError: queryKeys.users.list is not a function` VERIFIED BY: frontend unit test for query keys
- [ ] Priority 1: User dropdown populates with active users in the recovery dialog VERIFIED BY: manual verification + integration test
- [ ] Priority 1: No TypeScript errors in query keys file VERIFIED BY: `npm run typecheck` passes
- [ ] Priority 2: Admin can recover stuck change orders without "User does not have sufficient authority" errors VERIFIED BY: E2E test for admin recovery workflow
- [ ] Priority 2: Approvers can approve/reject change orders without user ID lookup errors VERIFIED BY: E2E test for approval workflow
- [ ] Priority 3: CO submission sets `branch_name` correctly and persists it VERIFIED BY: unit test verifying branch_name is not null after submit
- [ ] Priority 3: Impact analysis runs successfully for all submissions, including empty branches VERIFIED BY: unit test for impact analysis on empty branch
- [ ] Priority 3: `impact_level` is calculated and set correctly based on changes VERIFIED BY: unit test for impact level calculation
- [ ] Priority 3: `assigned_approver_id` is set based on impact level and approval matrix VERIFIED BY: unit test for approver assignment
- [ ] Priority 3: SLA deadline is calculated and stored VERIFIED BY: unit test for SLA deadline calculation
- [ ] Priority 3: Branch is locked after submission VERIFIED BY: unit test verifying branch lock status
- [ ] Priority 4: Error messages include user context (who, what, where) VERIFIED BY: unit tests for error message formatting

**Technical Criteria:**

- [ ] Performance: User lookup by root_id uses indexed query VERIFIED BY: EXPLAIN ANALYZE shows index scan
- [ ] Security: No regression in RBAC checks VERIFIED BY: existing RBAC test suite passes
- [ ] Code Quality: MyPy strict (zero errors), Ruff (zero errors), TypeScript strict (zero errors) VERIFIED BY: CI quality gates

### Scope Boundaries

**In Scope:**

- **Priority 1 (CRITICAL - Blocker):** Fix frontend crash in queryKeys.ts
- **Priority 2 (CRITICAL):** Fix user ID inconsistency between `user_id` (root ID) and `id` (PK)
- **Priority 3 (HIGH):** Fix impact analysis not running on submit
- **Priority 4 (MEDIUM):** Improve error messages with context

**Out of Scope:**

- E2E lifecycle bugs (BUG-1 through BUG-6) - tracked in `2026-05-10-co-e2e-bugfix`
- antd v6 deprecation warnings - cosmetic
- Frontend UI improvements beyond crash fixes
- Performance optimizations beyond ensuring indexed queries

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|------------------|------------|
| **Priority 1 (CRITICAL)** |
| 1 | Add missing `users` key factory to `queryKeys.ts` | `frontend/src/api/queryKeys.ts` | None | All user-related queries have valid query keys; no TypeScript errors | Low |
| 2 | Verify user dropdown hydration in Recovery Dialog | `frontend/src/features/change-orders/components/ChangeOrderRecoveryDialog.tsx` | Task 1 | Dropdown populates with active users; no runtime errors | Low |
| **Priority 2 (CRITICAL)** |
| 3 | Add `get_by_id` method to UserService for PK lookup | `backend/app/services/user.py` | None | Method returns User for valid PK, raises NotFound for invalid PK | Low |
| 4 | Standardize `user_id` usage in change_order_service.py | `backend/app/services/change_order_service.py` | Task 3 | All user lookups use consistent identifier; no mix of PK/root ID | Medium |
| 5 | Add unit tests for user ID resolution methods | `backend/tests/unit/services/test_user_service.py` | Task 3 | Tests cover both root_id and PK lookup paths | Low |
| **Priority 3 (HIGH)** |
| 6 | Ensure `branch_name` is set on CO submission | `backend/app/services/change_order_service.py` | None | `branch_name` field is persisted (not null) after submit | Medium |
| 7 | Add defensive checks for impact analysis on empty branches | `backend/app/services/change_order_service.py` | None | Impact analysis runs successfully even when branch has no changes | Medium |
| 8 | Add unit tests for impact analysis on submit | `backend/tests/unit/services/test_change_order_service.py` | Task 6, Task 7 | Tests verify impact_level, assigned_approver_id, SLA deadline, branch lock | Medium |
| **Priority 4 (MEDIUM)** |
| 9 | Improve error messages with user context | `backend/app/services/change_order_service.py` | None | Error messages include user, project, CO, and action context | Low |
| 10 | Add unit tests for error message context | `backend/tests/unit/services/test_change_order_service.py` | Task 9 | Tests verify error messages contain required context fields | Low |

### Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  # Priority 1 (CRITICAL) - Frontend Crash Fix
  - id: FE-001
    name: "Add missing users key factory to queryKeys.ts"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-002
    name: "Verify user dropdown hydration in Recovery Dialog"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  # Priority 2 (CRITICAL) - User ID Inconsistency
  - id: BE-001
    name: "Add get_by_id method to UserService for PK lookup"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Standardize user_id usage in change_order_service.py"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Add unit tests for user ID resolution methods"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]
    kind: test

  # Priority 3 (HIGH) - Impact Analysis Fix
  - id: BE-004
    name: "Ensure branch_name is set on CO submission"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-005
    name: "Add defensive checks for impact analysis on empty branches"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-006
    name: "Add unit tests for impact analysis on submit"
    agent: pdca-backend-do-executor
    dependencies: [BE-004, BE-005]
    kind: test

  # Priority 4 (MEDIUM) - Error Message Improvements
  - id: BE-007
    name: "Improve error messages with user context"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-008
    name: "Add unit tests for error message context"
    agent: pdca-backend-do-executor
    dependencies: [BE-007]
    kind: test
```

**Parallelization Opportunities:**
- FE-001, BE-001, BE-004, BE-005, BE-007 can all run in parallel (no dependencies)
- FE-002 depends on FE-001
- BE-002 depends on BE-001
- BE-003 depends on BE-001
- BE-006 depends on BE-004 and BE-005
- BE-008 depends on BE-007

---

## Test Specification

### Test Hierarchy

```
tests/
├── unit/
│   ├── services/
│   │   ├── test_user_service.py                    (Priority 2)
│   │   └── test_change_order_service.py            (Priority 3, 4)
├── integration/
│   └── test_change_order_recovery_workflow.py      (Priority 2)
└── frontend/
    └── api/
        └── __tests__/queryKeys.test.ts             (Priority 1)
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Expected Result |
|---------|-----------|-----------|------|-----------------|
| **Priority 1 Tests** |
| T-001 | `test_queryKeys_users_factory_exists` | Priority 1 | Frontend Unit | `queryKeys.users.list()` is callable and returns valid key structure |
| T-002 | `test_recovery_dialog_user_dropdown_populates` | Priority 1 | Frontend Integration | Dialog renders without error; dropdown contains active users |
| **Priority 2 Tests** |
| T-003 | `test_user_service_get_by_root_id` | Priority 2 | Backend Unit | `get_by_root_id(user_id)` returns User for valid EVCS root ID |
| T-004 | `test_user_service_get_by_id` | Priority 2 | Backend Unit | `get_by_id(id)` returns User for valid database PK |
| T-005 | `test_admin_recover_stuck_co_with_correct_user_id` | Priority 2 | Integration | Admin can recover CO without "insufficient authority" error |
| **Priority 3 Tests** |
| T-006 | `test_co_submit_sets_branch_name` | Priority 3 | Backend Unit | After `submit_change_order()`, `branch_name` is not null |
| T-007 | `test_impact_analysis_runs_on_empty_branch` | Priority 3 | Backend Unit | Impact analysis completes without error when branch has no changes |
| T-008 | `test_impact_level_calculated_correctly` | Priority 3 | Backend Unit | `impact_level` is set based on change severity (LOW/MEDIUM/HIGH) |
| T-009 | `test_assigned_approver_id_set_from_matrix` | Priority 3 | Backend Unit | `assigned_approver_id` matches approval matrix for impact level |
| T-010 | `test_sla_deadline_calculated_and_set` | Priority 3 | Backend Unit | `sla_due_date` is calculated from SLA policy and stored |
| T-011 | `test_branch_locked_after_submit` | Priority 3 | Backend Unit | Branch `is_locked` is True after successful submission |
| **Priority 4 Tests** |
| T-012 | `test_error_messages_include_user_context` | Priority 4 | Backend Unit | Error messages contain: user_id, project_id, change_order_id, action |
| T-013 | `test_error_messages_include_actionable_context` | Priority 4 | Backend Unit | Error messages explain what failed and suggested resolution |

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|-----------|-------------|-------------|--------|------------|
| **Technical** | Adding `get_by_id` to UserService may create confusion about when to use root_id vs PK | Medium | Medium | Document clearly in docstrings; add type hints to prevent misuse |
| **Technical** | Standardizing on `user_id` may break existing code that uses PK | Medium | High | Run full test suite; grep for all user.id usages and update systematically |
| **Integration** | Frontend query keys change may affect other components using user queries | Low | Medium | Verify all user query usages after adding users factory |
| **Regression** | Impact analysis defensive checks may hide actual bugs if too permissive | Low | Medium | Add logging when empty branch path is taken; alert for monitoring |
| **Data Integrity** | Setting `branch_name` on submit may fail if branch was already deleted | Low | Low | Add defensive check for branch existence before setting name |

---

## Documentation References

### Required Reading

- Backend Coding Standards: `docs/02-architecture/backend/coding-standards.md`
- Frontend Coding Standards: `docs/02-architecture/frontend/coding-standards.md`
- EVCS Entity Classification: `docs/02-architecture/backend/contexts/evcs-core/entity-classification.md`
- Change Management User Stories: `docs/01-product-scope/change-management-user-stories.md`
- TanStack Query Patterns: `docs/02-architecture/frontend/state-management.md`

### Code References

- **Frontend Crash Fix:**
  - Query keys pattern: `frontend/src/api/queryKeys.ts` (see `projects`, `changeOrders` factories for reference)
  - Recovery Dialog: `frontend/src/features/change-orders/components/ChangeOrderRecoveryDialog.tsx`

- **User ID Standardization:**
  - UserService: `backend/app/services/user.py`
  - ChangeOrderService user lookups: `backend/app/services/change_order_service.py`
  - User model: `backend/app/models/user.py`

- **Impact Analysis Fix:**
  - CO submission: `backend/app/services/change_order_service.py` (submit method)
  - Impact analysis logic: `backend/app/services/change_order_service.py` (analyze_impact method)
  - Branch locking: `backend/app/core/branching/commands.py`

- **Error Message Pattern:**
  - Existing error handling: `backend/app/services/change_order_service.py` (see current error messages)
  - RBAC error examples: `backend/app/core/rbac.py`

---

## Prerequisites

### Technical

- [x] Database is running (PostgreSQL 15+)
- [x] Backend virtual environment activated (`source backend/.venv/bin/activate`)
- [x] Frontend dependencies installed (`cd frontend && npm install`)
- [ ] Current branch is `agent-architecture` (or latest)
- [ ] No uncommitted changes that would conflict with fixes

### Documentation

- [x] User requirements clarified (frontend crash, user ID inconsistency, impact analysis, error messages)
- [x] Architectural decision made (standardize on `user_id` / root ID)
- [ ] Review existing UserService implementation before adding `get_by_id`
- [ ] Review queryKeys.ts structure to understand factory pattern

---

## Effort Estimate

| Priority | Tasks | Estimated Time | Parallelizable |
|----------|-------|----------------|----------------|
| **Priority 1** | FE-001, FE-002 | 30 minutes | Sequential (FE-002 depends on FE-001) |
| **Priority 2** | BE-001, BE-002, BE-003 | 2 hours | Partial (BE-001 + others, BE-002/003 after BE-001) |
| **Priority 3** | BE-004, BE-005, BE-006 | 3 hours | Partial (BE-004/005 parallel, BE-006 after) |
| **Priority 4** | BE-007, BE-008 | 1 hour | Partial (BE-007 + BE-008 after) |
| **Testing** | All test verification | 2 hours | Sequential (database shared) |
| **Total** | | **~8.5 hours** | |

**Critical Path:** Priority 1 (30m) → Priority 2 (2h) → Priority 3 (3h) → Priority 4 (1h) = ~6.5 hours sequential
**With Parallelization:** ~4-5 hours (FE + BE work can run in parallel)

---

## Notes

1. **Frontend Crash (Priority 1)** is the immediate blocker - must be fixed first to unblock testing
2. **User ID Standardization (Priority 2)** affects multiple workflows - comprehensive testing required
3. **Impact Analysis (Priority 3)** is the most complex - requires understanding of branch state and approval matrix
4. **Error Messages (Priority 4)** can be done incrementally - start with most common errors
5. All backend changes must maintain backward compatibility during the transition period
6. Consider adding a deprecation warning for old PK-based lookups before removing them entirely
