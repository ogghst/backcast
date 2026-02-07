# Plan: Change Order Workflow Recovery

**Iteration**: 2026-02-06-change-order-workflow-recovery
**Date**: 2026-02-06
**Status**: ✅ Approved

## Overview

Implement admin recovery mechanism for stuck change orders and add timeout to impact analysis.

## Implementation Tasks

### Task 1: Backend - Add Recovery Schema

**File**: `backend/app/models/schemas/change_order.py`
**Action**: Add `ChangeOrderRecoveryRequest` schema
**Effort**: 30 minutes
**Dependencies**: None

**Fields**:
- `impact_level`: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
- `assigned_approver_id`: UUID
- `skip_impact_analysis`: bool = True
- `recovery_reason`: str (10-500 chars)

### Task 2: Backend - Add Recovery Service Method

**File**: `backend/app/services/change_order_service.py`
**Action**: Add `recover_change_order()` method
**Effort**: 2 hours
**Dependencies**: Task 1

**Logic**:
1. Validate change order is stuck (no available transitions)
2. Validate impact level
3. Validate approver exists
4. Update CO with provided values
5. Transition to "Under Review" status
6. Create audit log entry
7. Commit and return updated CO

### Task 3: Backend - Add Recovery API Endpoint

**File**: `backend/app/api/routes/change_orders.py`
**Action**: Add `POST /api/v1/change-orders/{id}/recover` endpoint
**Effort**: 1 hour
**Dependencies**: Task 1, Task 2

**Logic**:
1. Check RBAC permission (`change-order-recover`)
2. Call service recovery method
3. Return updated CO as `ChangeOrderPublic`
4. Handle errors with appropriate HTTP status codes

### Task 4: Backend - Add RBAC Permission

**File**: `backend/config/rbac.json`
**Action**: Add `change-order-recover` to admin role
**Effort**: 15 minutes
**Dependencies**: None

### Task 5: Backend - Add Impact Analysis Timeout

**File**: `backend/app/services/impact_analysis_service.py`
**Action**: Add timeout support to `analyze_impact()`
**Effort**: 2 hours
**Dependencies**: None

**Implementation**:
1. Extract analysis logic to `_perform_analysis()` method
2. Wrap call in `asyncio.wait_for()` with 300s timeout
3. On timeout: set status to "failed", log error
4. On success: set status to "completed"

### Task 6: Frontend - Create Recovery Dialog Component

**File**: `frontend/src/features/change-orders/components/ChangeOrderRecoveryDialog.tsx`
**Action**: Create new component
**Effort**: 2 hours
**Dependencies**: Task 3

**Features**:
- Impact level selector (LOW/MEDIUM/HIGH/CRITICAL)
- Approver selector (fetch from API)
- Recovery reason textarea (10-500 chars, required)
- Submit button with loading state
- RBAC-gated (`<Can permission="change-order-recover">`)

### Task 7: Frontend - Update Workflow Section

**File**: `frontend/src/features/change-orders/components/ChangeOrderWorkflowSection.tsx`
**Action**: Add "Recover Workflow" button
**Effort**: 1 hour
**Dependencies**: Task 6

**Logic**:
1. Detect stuck state: `status === "Submitted for Approval" && available_transitions.length === 0`
2. Show "Recover Workflow" button when stuck
3. Open recovery dialog on click
4. Refresh data after successful recovery

### Task 8: Documentation - Add Technical Debt Entry

**File**: `docs/03-project-plan/technical-debt.md`
**Action**: Document FK constraint issue
**Effort**: 30 minutes
**Dependencies**: None

**Content**:
- Issue description
- Root cause analysis
- Solution options
- Impact assessment
- Action items

### Task 9: Testing - Backend Tests

**File**: `backend/tests/unit/services/test_change_order_service.py`
**Action**: Add tests for recovery method
**Effort**: 2 hours
**Dependencies**: Task 2

**Test Cases**:
- Successfully recover stuck CO
- Reject recovery for non-stuck CO
- Reject invalid impact level
- Reject non-existent approver
- Verify audit log entry created

### Task 10: Testing - Frontend Tests

**File**: `frontend/src/features/change-orders/components/ChangeOrderRecoveryDialog.test.tsx`
**Action**: Add component tests
**Effort**: 1.5 hours
**Dependencies**: Task 6

**Test Cases**:
- Dialog renders correctly
- Form validation works
- Submit calls API correctly
- Success/error handling works
- RBAC gating works

## Test Strategy

### Backend Tests
- Unit tests for `recover_change_order()` method
- Integration tests for `/recover` endpoint
- RBAC permission tests
- Timeout tests for impact analysis

### Frontend Tests
- Component tests for recovery dialog
- Integration tests for workflow section
- E2E tests for complete recovery flow

### Manual Testing
1. Create stuck change order (simulate timeout)
2. Verify "Recover Workflow" button appears
3. Submit recovery with valid data
4. Verify CO transitions to "Under Review"
5. Verify approval works after recovery

## Quality Gates

### Backend
```bash
cd backend
uv run ruff check app tests --fix
uv run mypy app --strict
uv run pytest --cov=app
```

### Frontend
```bash
cd frontend
npm run lint
npm run type-check
npm test
npm run test:coverage
```

**Criteria**: All tests pass, 80%+ coverage, zero type errors

## Rollback Plan

If issues arise:
1. Revert API endpoint addition
2. Revert frontend changes
3. Keep technical debt documentation
4. Document issues for next iteration

## Success Metrics

1. ✅ Admin can recover stuck CO in < 2 minutes
2. ✅ Impact analysis times out after 5 minutes
3. ✅ All tests passing with 80%+ coverage
4. ✅ Technical debt documented with action items
5. ✅ No regressions in existing functionality

## Timeline Estimate

**Total Effort**: ~12.5 hours
**Development**: 10.5 hours
**Testing**: 2 hours
**Documentation**: Included in tasks

**Suggested Schedule**:
- Day 1: Tasks 1-5 (Backend)
- Day 2: Tasks 6-7 (Frontend)
- Day 3: Tasks 8-10 (Testing + Docs)

## Plan Approved

**Next Phase**: Do (02-do.md)
