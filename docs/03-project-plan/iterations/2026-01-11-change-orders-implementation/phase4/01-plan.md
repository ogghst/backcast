# Plan: Phase 4 - Change Order Approval & Merge

**Created:** 2026-01-14
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 3 (Unified Change Order Modal with Workflow Stepper)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 3 - Unified Change Order Modal with Workflow Stepper
- **Architecture**: Single modal containing three sections (CO details, workflow stepper + action buttons, step details)
- **Key Decisions**:
  - Optional comment field for all status transitions (Submit, Approve, Reject, Merge)
  - Merge conflicts block merge and display conflicts to user
  - Approved → Implemented transition is automatic after successful merge
  - Toast notifications sufficient (no WebSocket required)
  - Modal opens on clicking Change Order in list (not separate page)

### Success Criteria

**Functional Criteria:**

- User clicks Change Order in list → modal opens VERIFIED BY: E2E test
- Modal displays CO details, workflow stepper, and action buttons VERIFIED BY: Component test
- User submits CO for review (Draft → Submitted) with optional comment VERIFIED BY: Integration test
- Branch locks automatically on submit VERIFIED BY: Backend unit test
- User approves/rejects submitted COs with optional comment VERIFIED BY: Integration test
- User merges approved COs to main VERIFIED BY: E2E test
- Merge checks for conflicts first and blocks if conflicts exist VERIFIED BY: Backend unit test
- Merge shows confirmation with impact summary VERIFIED BY: Component test
- Successful merge auto-transitions status to "Implemented" VERIFIED BY: Backend integration test
- Rejecting CO returns to Draft with unlock VERIFIED BY: Backend integration test
- Lock indicator visible when branch is locked VERIFIED BY: Component test
- Action buttons respect RBAC permissions VERIFIED BY: API test

**Technical Criteria:**

- Performance: Modal opens < 500ms VERIFIED BY: Browser dev tools measurement
- Security: All status transitions validated by backend workflow service VERIFIED BY: Code review + tests
- Code Quality:
  - Backend: MyPy strict mode (zero errors) VERIFIED BY: `uv run mypy app/`
  - Frontend: TypeScript strict mode (zero errors) VERIFIED BY: `npm run lint`
  - Backend: Ruff (zero errors) VERIFIED BY: `uv run ruff check .`
  - Test coverage: 80%+ for new code VERIFIED BY: `pytest --cov` / `npm run test:coverage`

**Business Criteria:**

- Full audit trail (who changed status, when, optional comment) VERIFIED BY: Database query verification
- Irreversible operations require confirmation VERIFIED BY: UI interaction test
- Workflow rules enforced server-side VERIFIED BY: API test with invalid transitions
- Branch isolation maintained during merge VERIFIED BY: Backend integration test
- Merge conflicts prevent merge until resolved VERIFIED BY: E2E test

### Scope Boundaries

**In Scope:**

- Unified ChangeOrderModal component with workflow stepper, action buttons, and step details
- WorkflowButtons component for status transitions (Submit, Approve, Reject, Merge)
- WorkflowTransitionModal for optional comment input during transitions
- MergeConfirmationModal with conflict display
- StepDetailsSection for dynamic content based on workflow status
- BranchLockIndicator visual component
- Backend: Merge conflict detection in `BranchableService.merge_branch()`
- Backend: Optional comment field for status transitions
- Backend: Conflict check endpoint (`GET /change-orders/{id}/merge-conflicts`)
- Integration with ChangeOrderList (modal opens on row click)
- Toast notifications for user feedback

**Out of Scope:**

- WebSocket/real-time notifications (toast notifications sufficient)
- Email notifications for status changes
- Advanced conflict resolution UI (manual conflict resolution outside scope)
- Bulk operations on multiple Change Orders
- Change Order templates
- Scheduling future merges
- Custom workflow states beyond defined state machine

---

## Work Decomposition

### Task Breakdown

| Task | Description                                       | Files                                                                          | Dependencies           | Success                                  | Est. Complexity |
| ---- | ------------------------------------------------- | ------------------------------------------------------------------------------ | ---------------------- | ---------------------------------------- | --------------- |
| 1    | Add merge conflict detection to BranchableService | `backend/app/core/branching/service.py`                                        | None                   | Conflicts detected when versions diverge | Medium          |
| 2    | Create MergeConflictError exception               | `backend/app/core/branching/exceptions.py`                                     | None                   | Exception raised with conflict details   | Low             |
| 3    | Add comment field to ChangeOrderUpdate schema     | `backend/app/api/models/change_orders.py`                                      | None                   | Schema accepts optional comment          | Low             |
| 4    | Store transition comments in audit trail          | `backend/app/services/change_order_service.py`                                 | Task 3                 | Comments persisted in audit_log table    | Medium          |
| 5    | Add conflict check endpoint                       | `backend/app/api/routes/change_orders.py`                                      | Task 1, 2              | GET endpoint returns conflicts           | Low             |
| 6    | Update merge endpoint for conflicts + comment     | `backend/app/api/routes/change_orders.py`                                      | Task 1, 2, 4           | Returns 409 on conflict, accepts comment | Medium          |
| 7    | Create WorkflowStepper component                  | `frontend/src/features/change-orders/components/WorkflowStepper.tsx`           | None                   | 5-step visual progress indicator         | Low             |
| 8    | Create BranchLockIndicator component              | `frontend/src/features/change-orders/components/BranchLockIndicator.tsx`       | None                   | Lock icon visible when locked            | Low             |
| 9    | Create useWorkflowActions hook                    | `frontend/src/features/change-orders/hooks/useWorkflowActions.ts`              | None                   | Hook exposes transition/merge mutations  | Medium          |
| 10   | Create WorkflowTransitionContent component        | `frontend/src/features/change-orders/components/WorkflowTransitionContent.tsx` | None                   | Comment input renders in modal           | Low             |
| 11   | Create MergeConfirmationContent component         | `frontend/src/features/change-orders/components/MergeConfirmationContent.tsx`  | None                   | Merge preview with impact summary        | Low             |
| 12   | Create MergeConflictsList component               | `frontend/src/features/change-orders/components/MergeConflictsList.tsx`        | None                   | Conflicts displayed in error modal       | Low             |
| 13   | Create StepDetailsSection component               | `frontend/src/features/change-orders/components/StepDetailsSection.tsx`        | Task 7                 | Dynamic content per workflow status      | Medium          |
| 14   | Create WorkflowButtons component                  | `frontend/src/features/change-orders/components/WorkflowButtons.tsx`           | Task 9, 10, 11, 12     | Action buttons for available transitions | High            |
| 15   | Create ChangeOrderDetailsSection component        | `frontend/src/features/change-orders/components/ChangeOrderDetailsSection.tsx` | None                   | CO metadata displayed                    | Low             |
| 16   | Create ChangeOrderModal component                 | `frontend/src/features/change-orders/components/ChangeOrderModal.tsx`          | Tasks 7, 8, 14, 15, 13 | Main modal with all sections             | High            |
| 17   | Update ChangeOrderList to open modal              | `frontend/src/features/change-orders/components/ChangeOrderList.tsx`           | Task 16                | Row click opens modal                    | Medium          |
| 18   | Add API types for comment and conflicts           | `frontend/src/api/types/change-orders.ts`                                      | Task 3, 6              | TypeScript types match backend           | Low             |
| 19   | Add checkMergeConflicts API function              | `frontend/src/api/change-orders.ts`                                            | Task 5                 | API function returns conflicts           | Low             |
| 20   | Add comment param to updateChangeOrder            | `frontend/src/api/change-orders.ts`                                            | Task 4                 | API function accepts comment             | Low             |
| 21   | Add comment param to mergeChangeOrder             | `frontend/src/api/change-orders.ts`                                            | Task 6                 | API function accepts comment             | Low             |

### File Change List

| File Path                                                                      | Action | Purpose                                                                  |
| ------------------------------------------------------------------------------ | ------ | ------------------------------------------------------------------------ |
| `backend/app/core/branching/service.py`                                        | Modify | Add `_detect_merge_conflicts()` method, raise `MergeConflictError`       |
| `backend/app/core/branching/exceptions.py`                                     | Create | Define `MergeConflictError` with conflict details                        |
| `backend/app/api/models/change_orders.py`                                      | Modify | Add `comment` field to `ChangeOrderUpdate`, create `MergeRequest` schema |
| `backend/app/services/change_order_service.py`                                 | Modify | Store audit comments, handle merge conflicts                             |
| `backend/app/api/routes/change_orders.py`                                      | Modify | Add `/merge-conflicts` endpoint, update merge endpoint                   |
| `frontend/src/features/change-orders/components/ChangeOrderModal.tsx`          | Create | Main modal container with tabs/sections                                  |
| `frontend/src/features/change-orders/components/WorkflowStepper.tsx`           | Create | Visual workflow progress indicator                                       |
| `frontend/src/features/change-orders/components/WorkflowButtons.tsx`           | Create | Encapsulated action buttons component                                    |
| `frontend/src/features/change-orders/components/WorkflowTransitionContent.tsx` | Create | Comment input for status transitions                                     |
| `frontend/src/features/change-orders/components/MergeConfirmationContent.tsx`  | Create | Merge confirmation with conflict display                                 |
| `frontend/src/features/change-orders/components/MergeConflictsList.tsx`        | Create | Display merge conflicts in error modal                                   |
| `frontend/src/features/change-orders/components/ChangeOrderDetailsSection.tsx` | Create | CO metadata display                                                      |
| `frontend/src/features/change-orders/components/StepDetailsSection.tsx`        | Create | Dynamic step content renderer                                            |
| `frontend/src/features/change-orders/components/BranchLockIndicator.tsx`       | Create | Visual lock status indicator                                             |
| `frontend/src/features/change-orders/hooks/useWorkflowActions.ts`              | Create | Hook for workflow operations                                             |
| `frontend/src/features/change-orders/components/ChangeOrderList.tsx`           | Modify | Add modal state, onRow click handler                                     |
| `frontend/src/api/types/change-orders.ts`                                      | Modify | Add `MergeConflict`, `MergeRequest` types                                |
| `frontend/src/api/change-orders.ts`                                            | Modify | Add `checkMergeConflicts()`, update signatures for comment               |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests (Backend)
│   ├── MergeConflictError exception
│   ├── BranchableService._detect_merge_conflicts()
│   ├── ChangeOrderWorkflowService transitions with comments
│   └── ChangeOrderService.merge_change_order() conflict handling
├── Integration Tests (Backend)
│   ├── POST /change-orders/{id}/merge with conflicts
│   ├── GET /change-orders/{id}/merge-conflicts
│   └── PUT /change-orders/{id} with comment storage
├── Unit Tests (Frontend)
│   ├── WorkflowStepper renders correct step
│   ├── BranchLockIndicator shows/hides based on prop
│   ├── WorkflowTransitionContent comment handling
│   ├── MergeConfirmationContent renders impact summary
│   └── useWorkflowActions mutations
├── Component Tests (Frontend)
│   ├── WorkflowButtons shows correct actions per status
│   ├── WorkflowButtons merge with conflicts
│   ├── ChangeOrderModal layout and tabs
│   └── StepDetailsSection content per status
└── E2E Tests (Playwright)
    ├── Full workflow: Draft → Submit → Approve → Merge
    ├── Merge blocked by conflicts
    ├── Reject with comment
    └── Branch lock indicator visibility
```

### Test Cases

| Test ID | Description                                          | Type        | Verification                                        |
| ------- | ---------------------------------------------------- | ----------- | --------------------------------------------------- |
| T-001   | Detect merge conflicts when diverged versions        | Unit        | `_detect_merge_conflicts()` returns conflict list   |
| T-002   | Raise MergeConflictError on conflict                 | Unit        | Exception raised with conflict details              |
| T-003   | Store optional comment in audit trail                | Integration | Audit log entry contains comment                    |
| T-004   | GET /merge-conflicts returns empty when no conflicts | Integration | Response is empty array                             |
| T-005   | GET /merge-conflicts returns conflicts when present  | Integration | Response contains conflict details                  |
| T-006   | POST /merge returns 409 when conflicts exist         | Integration | HTTP 409 with conflict details in body              |
| T-007   | POST /merge succeeds with comment                    | Integration | Status transitions to Implemented, comment stored   |
| T-008   | WorkflowStepper highlights current status            | Component   | Current step has `process` status                   |
| T-009   | WorkflowButtons shows available transitions          | Component   | Buttons match `available_transitions`               |
| T-010   | WorkflowButtons shows Merge button when Approved     | Component   | Single "Merge to Main" button shown                 |
| T-011   | WorkflowTransitionContent captures comment           | Component   | TextArea value updates state                        |
| T-012   | useWorkflowActions transition calls API with comment | Unit        | Mutation called with comment param                  |
| T-013   | ChangeOrderList row click opens modal                | E2E         | Modal visible with correct CO data                  |
| T-014   | Submit with optional comment succeeds                | E2E         | Status changes to Submitted, comment in audit trail |
| T-015   | Merge blocked when conflicts detected                | E2E         | Error modal shown, status unchanged                 |
| T-016   | Full workflow Draft → Implemented                    | E2E         | All steps complete, status = Implemented            |

### Test Infrastructure

- **Backend Virtual Environment**: uv
- **Backend Test Framework**: pytest with pytest-asyncio (strict mode)
- **Frontend Test Framework**: Vitest for unit/component tests
- **E2E Test Framework**: Playwright
- **Fixtures Needed**:
  - Backend: `change_order_fixture`, `conflicted_change_order_fixture`, `test_user_fixture`
  - Frontend: `mockChangeOrder`, `mockUseWorkflowActions`
- **Mock Requirements**:
  - API responses: `/change-orders/:id`, `/change-orders/:id/merge-conflicts`, `/change-orders/:id/merge`
  - TanStack Query mutations for transition and merge

---

## Risk Assessment

| Risk Type   | Description                                   | Probability | Impact | Mitigation                                            |
| ----------- | --------------------------------------------- | ----------- | ------ | ----------------------------------------------------- |
| Technical   | Merge conflict detection logic has edge cases | Medium      | Medium | Extensive unit tests for version comparison scenarios |
| Technical   | Modal state management becomes complex        | Medium      | Low    | Keep modal state minimal, use TanStack Query for data |
| Integration | Frontend-backend type mismatch for new fields | Low         | Medium | Generate OpenAPI client after backend changes         |
| Integration | Audit trail storage requires schema migration | Low         | Medium | Create Alembic migration for comment column           |
| UX          | Modal becomes too large/overwhelming          | Medium      | Low    | Use tabs for step details, keep layout clean          |
| Schedule    | Component dependencies cause delays           | Low         | Low    | Implement components in dependency order              |

---

## Documentation References

### Required Documentation

**Architecture & Standards:**

- Coding Standards: `docs/00-meta/coding_standards.md`
- Bounded Context E006: `docs/02-architecture/01-bounded-contexts.md`
- ADR - Temporal Versioning: `docs/02-architecture/decisions/001-temporal-versioning.md`
- ADR - Change Order Workflow: `docs/02-architecture/decisions/006-change-order-workflow.md`

**Domain & Requirements:**

- Change Management User Stories: `docs/01-product-scope/change-management-user-stories.md`
- Product Backlog: `docs/03-project-plan/product-backlog.md`
- Phase 3 Analysis: `docs/03-project-plan/iterations/2026-01-11-change-orders-implementation/phase3/00-analysis.md`

**Project Context:**

- Current Iteration: `docs/03-project-plan/current-iteration.md`
- Phase 3 ACT: `docs/03-project-plan/iterations/2026-01-11-change-orders-implementation/phase3/04-act.md`

### Code References

**Existing Patterns:**

- Backend: `ChangeOrderWorkflowService` in `backend/app/services/change_order_workflow_service.py` (state machine pattern)
- Backend: `BranchableService.merge_branch()` in `backend/app/core/branching/service.py` (merge pattern)
- Frontend: `useChangeOrders` hook in `frontend/src/features/change-orders/hooks/useChangeOrders.ts` (TanStack Query pattern)
- Frontend: `ChangeOrderList` component in `frontend/src/features/change-orders/components/ChangeOrderList.tsx` (table pattern)

**Database Schema:**

- Tables: `change_orders`, `change_order_audit_log`, `versions`
- Relationships: Change Order → Versions (1:N) via branch_name
- Indexes: GIST indexes on valid_time/transaction_time ranges
- Migration needed: Add `comment` column to `change_order_audit_log` (nullable text)

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [x] Phase 3 (Impact Analysis) completed
- [x] `ChangeOrderWorkflowService` implemented
- [x] Branch locking logic in place
- [ ] Database migration for audit_log.comment column
- [ ] Dependencies installed (backend: `uv sync`, frontend: `npm install`)
- [ ] PostgreSQL running (`docker-compose up -d postgres`)
- [ ] Backend migrations applied (`uv run alembic upgrade head`)

### Documentation Prerequisites

- [x] Analysis phase approved
- [x] Architecture docs reviewed
- [x] Related ADRs understood (workflow service, versioning)

---

## Implementation Order

### Phase 1: Backend Foundation (Tasks 1-6)

1. Create `MergeConflictError` exception
2. Add conflict detection to `BranchableService`
3. Add comment field to `ChangeOrderUpdate` schema
4. Update audit trail storage for comments
5. Add conflict check endpoint
6. Update merge endpoint

### Phase 2: Frontend Infrastructure (Tasks 18-21)

1. Add TypeScript types for conflicts and comment
2. Update API functions (checkMergeConflicts, add comment params)

### Phase 3: Frontend Components (Tasks 7-8, 10-13, 15)

1. Create simple components (WorkflowStepper, BranchLockIndicator, content components)
2. Create hook (useWorkflowActions)

### Phase 4: Frontend Integration (Tasks 14, 16-17)

1. Create WorkflowButtons (depends on hook and content components)
2. Create ChangeOrderModal (main integration)
3. Update ChangeOrderList to open modal

### Phase 5: Testing (All tasks)

1. Write unit tests alongside implementation (TDD)
2. Integration tests for API endpoints
3. Component tests for React components
4. E2E tests for full workflow

---

**Document Status:** Ready for Implementation
**Next Steps:** Begin with Task 1 (Merge conflict detection)
