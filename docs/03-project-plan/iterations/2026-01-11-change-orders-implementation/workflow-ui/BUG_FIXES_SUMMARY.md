# Bug Fixes Summary - Change Order Workflow UI Integration

**Date:** 2026-01-13
**Iteration:** Workflow UI - Time Machine & Status Transitions

## Overview

Three critical bugs were identified and fixed during the Change Order workflow transition testing:

1. **Time Machine Query Mismatch** - Query used wrong timestamp when control_date was provided
2. **Operator Precedence Bug** - Edit permission check had incorrect logic
3. **Strict Inequality Bug** - Validation rejected equal timestamps (Time Machine mode)

---

## Bug #1: Time Machine Query Mismatch

**Location:** [`backend/app/services/change_order_service.py:L209`](backend/app/services/change_order_service.py#L209)

**Problem:**
When using Time Machine with a future `control_date`, the query to find the current Change Order used `clock_timestamp()` instead of the provided `control_date`, causing a 404 error.

```python
# BEFORE: Always used current time
stmt = stmt.where(
    cast(Any, ChangeOrder).valid_time.op("@>")(func.clock_timestamp()),
    ...
)

# AFTER: Use control_date when provided
query_timestamp = control_date if control_date else func.clock_timestamp()
stmt = stmt.where(
    cast(Any, ChangeOrder).valid_time.op("@>")(query_timestamp),
    ...
)
```

**Error Observed:**
```
Change Order not found. DB times:
- clock_timestamp=2026-01-13 22:06:25
- control_date=2026-05-10 05:49:24 (Time Machine future date)
```

The Change Order's `valid_time = [2026-05-10, ∞)` did not contain `clock_timestamp() = 2026-01-13`.

**Impact:**
- Change Orders could not be updated in Time Machine mode
- All update operations returned 404 Not Found

---

## Bug #2: Operator Precedence in Edit Permission Check

**Location:** [`backend/app/services/change_order_service.py:L271`](backend/app/services/change_order_service.py#L271)

**Problem:**
The condition for checking edit permission had incorrect operator precedence due to missing parentheses.

```python
# WRONG: Evaluates as (title) OR (description AND not can_edit)
if update_data.get("title") or update_data.get("description") and not can_edit:
    raise ValueError(...)

# CORRECT: Evaluates as (title OR description) AND (not can_edit)
has_title = "title" in update_data
has_description = "description" in update_data
if (has_title or has_description) and not can_edit:
    raise ValueError(...)
```

**Error Observed:**
```
Cannot edit Change Order details in status: Draft
```

This error was incorrectly raised even when editing in "Draft" status (which is editable) because:
- `update_data.get("title")` returned a truthy value (the title string)
- `truthy OR anything` = `True`
- The condition passed regardless of `can_edit`

**Impact:**
- All Change Order updates were blocked when title/description fields had values
- Only status-only updates worked

---

## Bug #3: Strict Inequality in Time Machine Validation

**Locations:**
1. [`backend/app/core/versioning/commands.py:L196`](backend/app/core/versioning/commands.py#L196)
2. [`backend/app/core/branching/commands.py:L136`](backend/app/core/branching/commands.py#L136)

**Problem:**
The `UpdateVersionCommand` and `UpdateCommand` required `control_date` to be **strictly greater than** the current version's `valid_time.lower`, but in Time Machine mode they are equal when updating at the same timestamp.

```python
# BEFORE: Rejected equal timestamps
if self.control_date <= current_lower:
    raise ValueError(
        f"control_date must be after valid_time lower bound"
    )

# AFTER: Allow equal timestamps for Time Machine
if self.control_date < current_lower:
    raise ValueError(
        f"control_date must be on or after valid_time lower bound"
    )
```

**Error Observed:**
```
control_date (2026-05-10T05:49:24.467000+00:00) must be after
valid_time lower bound (2026-05-10T05:49:24.467000+00:00)
```

When a Change Order was created at `2026-05-10 05:49:24` and then updated at the same Time Machine timestamp, the validation failed because `control_date == current_lower`.

**Impact:**
- Change Orders could not be updated in Time Machine mode
- Users had to manually advance time between updates

---

## Files Modified

| File | Changes |
|------|---------|
| `backend/app/services/change_order_service.py` | Fixed Time Machine query (L209), fixed operator precedence (L271), added debug logging |
| `backend/app/core/versioning/commands.py` | Fixed validation from `<=` to `<` (L196) |
| `backend/app/core/branching/commands.py` | Fixed validation from `<=` to `<` (L136) |
| `backend/app/api/routes/change_orders.py` | Added debug logging, enhanced error messages |
| `frontend/tests/e2e/change_order_workflow_transition.spec.ts` | New comprehensive E2E test suite |

---

## Debug Logging Added

Comprehensive logging was added to assist with debugging:

### Service Layer (`change_order_service.py`)
- `update_change_order()`: Logs start/end, query parameters, found version details
- `get_current()`: Logs query parameters and FOUND/NOT FOUND results
- `_to_public()`: Logs workflow metadata population

### API Layer (`change_orders.py`)
- Request start with `change_order_id` and `user_id`
- Success with updated `change_order_id`
- Error details with context for correlation

---

## Testing

### E2E Test Suite Created
[`frontend/tests/e2e/change_order_workflow_transition.spec.ts`](frontend/tests/e2e/change_order_workflow_transition.spec.ts)

Tests cover:
1. Draft → Submitted for Approval transition
2. Locked branch warning display
3. Rejected CO resubmission
4. Create mode Draft-only options
5. Invalid transition prevention
6. Backend debug info verification

### Manual Test Procedure
1. Enable Time Machine with a future date (e.g., May 2026)
2. Create a Change Order (it will have `valid_time` starting in the future)
3. Update the Change Order status from "Draft" to "Submitted for Approval"
4. **Expected:** Update succeeds without errors

---

## Prevention

To prevent similar issues in the future:

1. **All queries filtering by `valid_time`** should use `control_date` when provided (Time Machine mode)
2. **Complex boolean expressions** should always use parentheses to make precedence explicit
3. **Time Machine timestamp comparisons** should use `>=` instead of `>` to allow updates at the same timestamp
4. **Unit tests** should cover Time Machine scenarios with future/past dates
5. **Integration tests** should verify queries return correct results at different time points

---

## Related Documentation

- [Bug Fix: Time Machine Query](BUG_FIX_TIME_MACHINE_QUERY.md) - Detailed analysis of Bug #1
- [01-plan.md](01-plan.md) - Original implementation plan
- [02-do.md](02-do.md) - Implementation documentation
