# TD-057: MERGE Mode Branch Deletion Detection Fix

**Date:** 2026-01-27
**Status:** ✅ Completed
**Effort:** 2 hours

## Problem Description

The MERGE mode in `get_as_of()` was incorrectly falling back to the main branch even when an entity was deleted on the requested branch. The `_is_deleted_on_branch()` method was checking if ANY deleted version existed on the branch, but it wasn't considering the **temporal aspect** - whether the deletion happened **before or after** the query timestamp.

### Root Cause

Two locations had the same bug:

1. **`TemporalService._is_deleted_on_branch()`** (line 400-420)
   - Only checked `deleted_at IS NOT NULL`
   - Didn't check `deleted_at <= as_of`

2. **`BranchableService.get_as_of()`** (line 543-555)
   - Only checked `deleted_at IS NOT NULL`
   - Didn't check `deleted_at <= as_of`

### Impact

**Before Fix:**
- Querying at T=5 for an entity deleted at T=10 would incorrectly return `None`
- The entity was considered "deleted" even though the deletion happened AFTER the query time
- This broke time-travel semantics and prevented valid queries from seeing historical states

**After Fix:**
- Querying at T=5 for an entity deleted at T=10 correctly falls back to main
- Querying at T=15 for an entity deleted at T=10 correctly returns `None` (zombie check)
- Time-travel semantics are properly preserved

## Solution

Added temporal check `deleted_at <= as_of` to both methods:

### 1. TemporalService Fix

```python
async def _is_deleted_on_branch(
    self, entity_id: UUID, as_of: datetime, branch: str
) -> bool:
    """Check if entity was explicitly deleted on branch at timestamp.

    CRITICAL: Must check temporal aspect - only returns True if deleted_at <= as_of.
    This prevents incorrect fallback prevention when entity is deleted AFTER the query time.
    """
    # Cast as_of to TIMESTAMP(timezone=True) for proper comparison
    as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))

    # Check for deleted version on this branch at or before as_of timestamp
    stmt = select(self.entity_class).where(
        getattr(self.entity_class, root_field) == entity_id,
        cast(Any, self.entity_class).deleted_at.is_not(None),
        cast(Any, self.entity_class).deleted_at <= as_of_tstz,  # Temporal check
    )
```

### 2. BranchableService Fix

```python
# No result on requested branch - check if entity was deleted on this branch
# If deleted, don't fall back to main (respect the deletion)
# CRITICAL: Must check temporal aspect - only consider deleted if deleted_at <= as_of
deleted_check = (
    select(self.entity_class)
    .where(
        getattr(self.entity_class, root_field) == entity_id,
        cast(Any, self.entity_class).branch == branch,
        cast(Any, self.entity_class).deleted_at.is_not(None),
        cast(Any, self.entity_class).deleted_at <= as_of,  # Temporal check
    )
    .limit(1)
)
```

## Testing

### Test Files Added

1. **`tests/unit/test_td57_deletion_detection.py`**
   - `test_td57_deleted_after_as_of_should_fallback`: Verifies entities deleted AFTER query time DO fall back to main
   - `test_td57_deleted_before_as_of_no_fallback`: Verifies entities deleted BEFORE query time DON'T fall back to main

2. **Existing Tests Verified**
   - `test_wbe_zombie_check_merge_mode_no_fallback`: Original zombie check test (now passes)
   - `test_project_zombie_check_deleted_not_visible`: Project zombie check
   - `test_wbe_zombie_check_deleted_not_visible`: WBE zombie check
   - All WBE service branch mode tests
   - All versioning core tests

### Test Results

All tests pass:
```
tests/unit/test_zombie_checks.py::test_project_zombie_check_deleted_not_visible PASSED
tests/unit/test_zombie_checks.py::test_wbe_zombie_check_deleted_not_visible PASSED
tests/unit/test_zombie_checks.py::test_wbe_zombie_check_merge_mode_no_fallback PASSED
tests/unit/test_td57_deletion_detection.py::test_td57_deleted_after_as_of_should_fallback PASSED
tests/unit/test_td57_deletion_detection.py::test_td57_deleted_before_as_of_no_fallback PASSED
tests/unit/core/versioning/test_*.py - 24 tests PASSED
tests/unit/services/test_wbe_service_branch_mode.py - 4 tests PASSED
```

## Code Quality

- **Ruff:** ✅ All checks pass
- **MyPy:** ⚠️ Pre-existing errors (not related to this fix)
- **Coverage:** Tests added for the specific edge cases

## Files Modified

1. `backend/app/core/versioning/service.py` - Fixed `_is_deleted_on_branch()` method
2. `backend/app/core/branching/service.py` - Fixed MERGE mode deletion detection
3. `backend/tests/unit/test_td57_deletion_detection.py` - New comprehensive tests
4. `docs/03-project-plan/technical-debt-register.md` - Marked TD-057 as completed

## Documentation References

- [EVCS Implementation Guide](../../../02-architecture/backend/contexts/evcs-core/evcs-implementation-guide.md)
- [Temporal Query Reference](../../../02-architecture/cross-cutting/temporal-query-reference.md)

## Key Insights

1. **Temporal Semantics Matter:** In bitemporal systems, checking "is deleted" is not enough - you must check "was deleted at or before the query time"

2. **MERGE Mode Nuance:** MERGE mode should fall back to main only when the entity doesn't exist on the branch OR when the entity was deleted AFTER the query time

3. **Zombie Check Pattern:** The fix ensures proper zombie behavior - entities disappear after their deletion timestamp but remain visible before it

## Related Technical Debt

- TD-057 is now **completed** ✅
- TD-063 (Add Zombie Check Tests for All Versioned Entities) - partially addressed with this fix
