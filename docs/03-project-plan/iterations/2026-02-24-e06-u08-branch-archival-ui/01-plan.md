# Plan: Epic 6 - Branch Archival UI (E06-U08 Finalization)

**Created:** 2026-02-25  
**Based on:** [Link to 00-analysis.md](./00-analysis.md)  
**Approved Option:** Option 2 (Action Button within Change Order Detail Page)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 2 (Action Button within Change Order Detail Page)
- **Architecture**: Create an API endpoint to expose the backend's existing `archive_change_order_branch` service method. Add a UI button in the `WorkflowActions` area of the Change Order Detail page.
- **Key Decisions**:
  - The feature is exposed _only_ in the detail view.
  - The "Archive Branch" button is visibly **disabled** if the Change Order has not reached a final end state ("Implemented" or "Rejected") instead of being completely hidden, to increase discoverability.

### Success Criteria

**Functional Criteria:**

- [ ] Users can trigger the archival of a Change Order via a `POST /api/v1/change-orders/{id}/archive` endpoint. VERIFIED BY: Integration Test.
- [ ] Users see an "Archive Branch" button in the Change Order details page. VERIFIED BY: Component Test / Manual UI Test.
- [ ] The "Archive Branch" button is disabled if the Change Order status is not `IMPLEMENTED` or `REJECTED`. VERIFIED BY: Component Test / Manual UI Test.
- [ ] Clicking the "Archive Branch" button asks for confirmation, and upon success, redirects the user to the Change Orders list and invalidates the cache. VERIFIED BY: Component Test / Manual UI Test.

**Technical Criteria:**

- [ ] Performance: Endpoint returns < 200ms. VERIFIED BY: Automated test logic or API tooling.
- [ ] Security: Only authorized users can archive branches (role-based access). VERIFIED BY: Backend Unit Tests.
- [ ] Code Quality: mypy strict + ruff clean VERIFIED BY: CI pipeline

**Business Criteria:**

- [ ] Users can easily clean up their active project landscape by soft-deleting completed Change Order branches without navigating complex UI menus. VERIFIED BY: Product review.

### Scope Boundaries

**In Scope:**

- Modifying `backend/app/api/routes/change_orders.py` to add the archive route.
- Re-generating frontend API client (`npm run generate-client`).
- Creating a `useArchiveChangeOrder.ts` hook.
- Modifying `frontend/src/features/change-orders/components/WorkflowActions.tsx` (or similar detail actions component).

**Out of Scope:**

- Archiving WBEs or Projects (only Change Orders).
- Bulk archival capabilities from the list view.

---

## Work Decomposition

### Task Breakdown

| #   | Task                    | Files                                                                                       | Dependencies | Success Criteria                                                  | Complexity |
| --- | ----------------------- | ------------------------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------- | ---------- |
| 1   | Add Backend Route       | `backend/app/api/routes/change_orders.py`, `backend/tests/api/routes/test_change_orders.py` | None         | New archive POST endpoint exists and passes tests                 | Low        |
| 2   | Regenerate OpenAPI      | `frontend/src/api/generated/*`                                                              | Task 1       | Client code updated with new endpoint                             | Low        |
| 3   | Frontend Hook           | `frontend/src/features/change-orders/api/useArchiveChangeOrder.ts`                          | Task 2       | React Query mutation successfully calls endpoint                  | Low        |
| 4   | Frontend UI Integration | `frontend/src/features/change-orders/components/WorkflowActions.tsx`                        | Task 3       | Button appears, respects disabled state, and redirects on success | Medium     |

### Test-to-Requirement Traceability

| Acceptance Criterion     | Test ID | Test File                                | Expected Behavior                                             |
| ------------------------ | ------- | ---------------------------------------- | ------------------------------------------------------------- |
| API endpoint functional  | T-001   | `tests/api/routes/test_change_orders.py` | POST request successfully archives the branch and returns 200 |
| Button disabled safely   | T-002   | `WorkflowActions.test.tsx` (or Manual)   | Button is disabled when status is `DRAFT` or `SUBMITTED`      |
| Button triggers archival | T-003   | `WorkflowActions.test.tsx` (or Manual)   | Clicking calls the mutation and triggers redirection          |

---

## Test Specification

### Test Hierarchy

```
├── Backend Tests
│   └── tests/api/routes/test_change_orders.py (New test cases)
├── Frontend Tests
│   └── src/features/change-orders/components/WorkflowActions.test.tsx
```

### Test Cases (first 3-5)

| Test ID | Test Name                                 | Criterion | Type | Verification                               |
| ------- | ----------------------------------------- | --------- | ---- | ------------------------------------------ |
| T-001   | `test_archive_change_order_endpoint`      | AC-1      | API  | 200 OK, branch no longer in active list    |
| T-002   | `test_archive_change_order_unauthorized`  | AC-1      | API  | 403/401 Forbidden when lacking permissions |
| T-003   | `test_archive_change_order_invalid_state` | AC-1      | API  | 409/400 Error when CO is in `DRAFT`        |

---

## Risk Assessment

| Risk Type   | Description                                                    | Probability | Impact | Mitigation                                                                                                                               |
| ----------- | -------------------------------------------------------------- | ----------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Integration | Frontend hook attempts to fetch a branch that was just deleted | Low         | Medium | Make sure we redirect immediately to the list page (`/change-orders`) before react-query attempts a re-fetch of the now-archived entity. |
| Technical   | OpenAPI regeneration overwritting manual fixes                 | Low         | Low    | Use the standard `npm run generate-client` command, ensuring the backend server is running.                                              |

---

## Prerequisites

### Technical

- [x] Database migrations applied (not needed for this specific change)
- [ ] Dependencies installed
- [ ] Environment configured (Backend running for OpenAPI generation)

### Documentation

- [x] Analysis phase approved
- [ ] Architecture docs reviewed
