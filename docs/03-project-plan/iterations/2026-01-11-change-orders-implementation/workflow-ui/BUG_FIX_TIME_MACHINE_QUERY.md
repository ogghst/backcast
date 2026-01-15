# Bug Fix: Time Machine Query Mismatch in Change Order Update

**Date:** 2026-01-13
**Severity:** Critical
**Status:** Fixed

## Problem Description

When updating a Change Order from "Draft" to "Submitted for Approval" while using **Time Machine** mode (with a `control_date` set to a future date), the API returned a 404 error with message:

```
Change Order {id} not found or has been deleted
```

## Root Cause

The `update_change_order()` method in [`ChangeOrderService`](backend/app/services/change_order_service.py) was using `clock_timestamp()` to find the current version, regardless of whether a `control_date` was provided.

**The Issue:**
1. When Time Machine is enabled, `control_date` is set to a future date (e.g., `2026-05-10`)
2. The Change Order was created with `valid_time = [2026-05-10, ∞)`
3. The query to find the current version used `clock_timestamp()` which returns the **current time** (e.g., `2026-01-13`)
4. PostgreSQL's range operator `@>` checks if `valid_time` contains the query timestamp
5. `[2026-05-10, ∞)` does NOT contain `2026-01-13` (the range starts in the future)
6. Result: 404 Not Found

**Debug Logs Revealed:**
```
control_date=2026-05-10 05:49:24.467000+00:00  (Time Machine future date)
clock_timestamp=2026-01-13 22:06:25.388359+00:00 (current date)
```

## Solution

Modified [`update_change_order()`](backend/app/services/change_order_service.py#L191-L291) to use the `control_date` parameter for the query when it is provided:

```python
# CRITICAL FIX: When control_date is provided (Time Machine mode), use it instead of clock_timestamp()
# This ensures we find the Change Order that exists at the control_date, not at current time
query_timestamp = control_date if control_date else func.clock_timestamp()

stmt = sql_select(ChangeOrder).where(
    ChangeOrder.change_order_id == change_order_id,
    # Check if query_timestamp is within valid_time range
    cast(Any, ChangeOrder).valid_time.op("@>")(query_timestamp),
    cast(Any, ChangeOrder).deleted_at.is_(None),
    # ... rest of query
)
```

## Changes Made

### [`backend/app/services/change_order_service.py`](backend/app/services/change_order_service.py)

**Lines 217-253:** Fixed the query to use `control_date` when provided
- Added `query_timestamp` variable that uses `control_date` if provided, otherwise `clock_timestamp()`
- Updated the `valid_time` check to use `query_timestamp`
- Enhanced error logging to include `query_timestamp` for debugging

## Testing

1. **Manual Test:**
   - Enable Time Machine with a future date (e.g., May 2026)
   - Create a Change Order (it will have `valid_time` starting in the future)
   - Update the Change Order status from "Draft" to "Submitted for Approval"
   - **Expected:** Update succeeds without 404 error

2. **Debug Logs Verification:**
   - When update succeeds, logs should show:
     ```
     [DEBUG] update_change_order START - control_date=2026-05-10...
     [DEBUG] Current version found: True
     [DEBUG] Status transition: Draft -> Submitted for Approval
     [DEBUG] update_change_order END - returning updated_co id=...
     ```

3. **E2E Test:**
   - The [`change_order_workflow_transition.spec.ts`](frontend/tests/e2e/change_order_workflow_transition.spec.ts) test suite covers this scenario

## Additional Improvements

As part of debugging this issue, comprehensive logging was added:

1. **Service Layer Logging:**
   - `update_change_order()`: Detailed logs at each step
   - `get_current()`: Logs for FOUND/NOT FOUND cases
   - `_to_public()`: Logs for workflow metadata population

2. **API Layer Logging:**
   - `update_change_order()`: Request/response logging with context
   - Enhanced error messages including `change_order_id` and `user_id`

## Related Documentation

- [Time Machine Context](frontend/src/contexts/TimeMachineContext.tsx) - Frontend Time Machine state
- [Change Order Service](backend/app/services/change_order_service.py) - Backend service implementation
- [Bitemporal Versioning](backend/app/core/versioning/) - Core EVCS versioning logic

## Prevention

To prevent similar issues in the future:

1. **All queries that filter by `valid_time`** should use `control_date` when provided (Time Machine mode)
2. **Unit tests** should cover Time Machine scenarios with future/past dates
3. **Integration tests** should verify queries return correct results at different time points
4. **Documentation** should clearly state which methods support Time Machine mode

## Notes

- This fix only applies to `update_change_order()` which is the entry point for updates via the API
- `get_current()` and `get_current_by_code()` continue to use `clock_timestamp()` as they don't receive `control_date` parameters from the current API routes
- If those methods need to support Time Machine in the future, they should be updated with the same pattern
