# Analysis: Change Order Workflow Recovery

**Iteration**: 2026-02-06-change-order-workflow-recovery
**Date**: 2026-02-06
**Status**: ✅ Complete

## Problem Statement

Change orders can become stuck in the workflow when:
1. Impact analysis gets stuck in "in_progress" state indefinitely
2. No admin recovery mechanism exists to recover stuck workflows
3. Foreign key constraints use primary keys instead of business keys, causing bitemporal query issues
4. No timeout mechanism exists for long-running impact analysis

## Root Cause Analysis

### Immediate Causes

1. **Missing Impact Analysis Timeout**
   - `ImpactAnalysisService.analyze_impact()` runs indefinitely
   - No timeout mechanism to fail stuck analyses
   - Status remains "in_progress" forever

2. **Missing Admin Recovery Mechanism**
   - No API endpoint to recover stuck workflows
   - No UI for admins to intervene
   - Only option was manual database intervention

3. **Foreign Key Design Issue**
   - `ChangeOrder.assigned_approver_id` FK references `users(id)` (PK)
   - Should reference `users(user_id)` (business key)
   - PK changes across versions, business key is stable
   - Causes issues in bitemporal queries

### Contributing Factors

1. **Workflow Validation Gaps**
   - Submit transition doesn't validate impact analysis completion
   - No pre-submit checks for required fields

2. **Error Handling**
   - Impact analysis failures don't properly update status
   - No retry mechanism for transient failures

## Impact Assessment

### Severity: High

**Affected Areas**:
- Change Order workflow (blocker for approval)
- Admin productivity (requires manual DB intervention)
- Data integrity (FK reference issues)
- User experience (stuck COs with no recovery path)

**Business Impact**:
- Delayed project approvals
- Increased admin overhead
- Potential data inconsistency

## Success Criteria

1. ✅ Admin can recover stuck change orders via API
2. ✅ Admin can recover stuck change orders via UI
3. ✅ Impact analysis times out after 5 minutes
4. ✅ Technical debt documented for FK issue
5. ✅ All tests passing (backend + frontend)
6. ✅ Type checking passes (MyPy + TypeScript)

## Dependencies

### Internal
- `ChangeOrderService` - for recovery operations
- `ImpactAnalysisService` - for timeout implementation
- `RBACService` - for permission checks
- Frontend: `useWorkflowActions` hook

### External
- PostgreSQL: Async for timeout support
- React: Ant Design Modal components
- TanStack Query: for API mutations

## Analysis Complete

**Next Phase**: Planning (01-plan.md)
