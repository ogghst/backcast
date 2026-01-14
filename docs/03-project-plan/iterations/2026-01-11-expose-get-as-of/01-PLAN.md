# Implementation Plan: Expose get_as_of in Service Interfaces

**Date:** 2026-01-11
**Status:** Ready for Implementation
**Related Analysis:** [00-ANALYSIS.md](./00-ANALYSIS.md)
**Related Technical Debt:** [TD-026](../../technical-debt-register.md#td-026-expose-get_as_of-in-service-interfaces)

---

## Executive Summary

This plan implements **Option 1 (Thin Wrapper Pattern)** to expose `TemporalService.get_as_of()` in all services that extend `TemporalService`. The implementation follows the existing `get_{entity}_history()` wrapper pattern used throughout the codebase.

**Scope:**
- Add `get_{entity}_as_of()` methods to 6 services
- Add service-level tests with zombie check TDD pattern
- Update documentation to reflect new capabilities
- Run full backend and frontend test suites

**Estimated Effort:** 1 hour (matches TD-026 estimate)

---

## Implementation Tasks

### Task 1: Add BranchMode Enum Import to Services

**Priority:** HIGH (required before adding methods)

**Files to Modify:**
1. `backend/app/services/project.py`
2. `backend/app/services/wbe.py`
3. `backend/app/services/cost_element_service.py`
4. `backend/app/services/cost_element_type_service.py`
5. `backend/app/services/department.py`
6. `backend/app/services/user.py`

**Changes:**
Add import statement:
```python
from app.core.versioning.enums import BranchMode
```

**Location:** After existing imports from `app.core.versioning.commands`

---

### Task 2: Add get_{entity}_as_of Methods

**Priority:** HIGH

**Template Method Signature:**

```python
async def get_{entity}_as_of(
    self,
    {entity_id}: UUID,
    as_of: datetime,
    branch: str = "main",
    branch_mode: BranchMode | None = None,
) -> {Entity} | None:
    """Get {entity} as it was at specific timestamp.

    Provides System Time Travel semantics for single-entity queries.
    Uses STRICT mode by default (only searches in specified branch).
    Use BranchMode.MERGE to fall back to main branch if not found.

    Args:
        {entity_id}: The unique identifier of the {entity}
        as_of: Timestamp to query (historical state)
        branch: Branch name to query (default: "main")
        branch_mode: Resolution mode for branches
            - None/STRICT: Only return from specified branch (default)
            - MERGE: Fall back to main if not found on branch

    Returns:
        {Entity} if found at the specified timestamp, None otherwise

    Example:
        >>> # Get project as of January 1st
        >>> from datetime import datetime
        >>> as_of = datetime(2026, 1, 1, 12, 0, 0)
        >>> project = await service.get_project_as_of(
        ...     project_id=uuid,
        ...     as_of=as_of
        ... )
    """
    return await self.get_as_of({entity_id}, as_of, branch, branch_mode)
```

**Per-Service Implementation Details:**

| Service | Method Name | Entity ID Param | Return Type | Location |
|---------|-------------|-----------------|-------------|----------|
| ProjectService | `get_project_as_of` | `project_id` | `Project \| None` | After `get_project_history` |
| WBEService | `get_wbe_as_of` | `wbe_id` | `WBE \| None` | After `get_wbe_history` |
| CostElementService | `get_cost_element_as_of` | `cost_element_id` | `CostElement \| None` | After `get_history` |
| CostElementTypeService | `get_cost_element_type_as_of` | `cost_element_type_id` | `CostElementType \| None` | After `list` (end of class) |
| DepartmentService | `get_department_as_of` | `department_id` | `Department \| None` | After `get_department_history` |
| UserService | `get_user_as_of` | `user_id` | `User \| None` | After `get_user_history` |

**Special Note for CostElementService:**
The method must include `parent_name` and type relations. Use `_get_base_stmt()` to ensure joins are included:

```python
async def get_cost_element_as_of(
    self,
    cost_element_id: UUID,
    as_of: datetime,
    branch: str = "main",
    branch_mode: BranchMode | None = None,
) -> CostElement | None:
    """Get cost element as it was at specific timestamp.

    Includes parent_name and cost_element_type_name relations.
    """
    from typing import Any, cast

    # Use base statement with parent name join
    stmt = self._get_base_stmt(as_of=as_of).where(
        CostElement.cost_element_id == cost_element_id,
        CostElement.branch == branch,
    )

    # Apply time-travel filter
    stmt = self._apply_bitemporal_filter_for_time_travel(stmt, as_of)

    stmt = stmt.limit(1)
    result = await self.session.execute(stmt)
    resolved = await self._resolve_relations(result.all())
    return resolved[0] if resolved else None
```

---

### Task 3: Add Service-Level Tests

**Priority:** HIGH

**Test File Locations:**
Create new test files:
1. `backend/tests/unit/services/test_project_service_temporal.py`
2. `backend/tests/unit/services/test_wbe_service_temporal.py`
3. `backend/tests/unit/services/test_cost_element_service_temporal.py`
4. `backend/tests/unit/services/test_cost_element_type_service_temporal.py`
5. `backend/tests/unit/services/test_department_service_temporal.py`
6. `backend/tests/unit/services/test_user_service_temporal.py`

**Test Template:**

```python
"""Tests for {Entity}Service time-travel methods (get_{entity}_as_of)."""

from datetime import datetime, UTC
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.services.{service_module} import {Entity}Service


@pytest.mark.asyncio
async def test_{entity_snake}_as_of_returns_current_version(
    session: AsyncSession, admin_user, {entity_snake}_factory
):
    """Should return current version when querying current time."""
    service = {Entity}Service(session)

    # Create entity
    {entity} = await {entity_snake}_factory()
    created_at = {entity}.transaction_time.lower

    # Query as of current time
    result = await service.get_{entity_snake}_as_of(
        {entity_id}={entity}.{entity_id}_attr,
        as_of=datetime.now(UTC),
    )

    assert result is not None
    assert result.{entity_id}_attr == {entity}.{entity_id}_attr


@pytest.mark.asyncio
async def test_{entity_snake}_as_of_zombie_check(
    session: AsyncSession, admin_user, {entity_snake}_factory
):
    """Verify deleted entities respect time travel boundaries.

    Pattern: Create -> Delete -> Query Past -> Query Future
    """
    service = {Entity}Service(session)

    # 1. Create entity at T1
    control_date_t1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    {entity} = await {entity_snake}_factory(control_date=control_date_t1)

    # 2. Delete entity at T3
    control_date_t3 = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    await service.soft_delete(
        {entity_id}={entity}.{entity_id}_attr,
        actor_id=admin_user.user_id,
        control_date=control_date_t3,
    )

    # 3. Query at T2 (before deletion) - should return entity
    as_of_t2 = datetime(2026, 1, 5, 12, 0, 0, tzinfo=UTC)
    result = await service.get_{entity_snake}_as_of(
        {entity_id}={entity}.{entity_id}_attr,
        as_of=as_of_t2,
    )
    assert result is not None, "Entity should be visible before deletion"

    # 4. Query at T4 (after deletion) - should NOT return entity
    as_of_t4 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    result = await service.get_{entity_snake}_as_of(
        {entity_id}={entity}.{entity_id}_attr,
        as_of=as_of_t4,
    )
    assert result is None, "Entity should NOT be visible after deletion"


@pytest.mark.asyncio
async def test_{entity_snake}_as_of_strict_mode(
    session: AsyncSession, {entity_snake}_factory
):
    """Should return None when entity not found in specified branch (STRICT mode)."""
    service = {Entity}Service(session)

    # Create entity in main branch
    {entity} = await {entity_snake}_factory(branch="main")

    # Query in non-existent branch with STRICT mode (default)
    result = await service.get_{entity_snake}_as_of(
        {entity_id}={entity}.{entity_id}_attr,
        as_of=datetime.now(UTC),
        branch="non-existent-branch",
    )

    assert result is None


@pytest.mark.asyncio
async def test_{entity_snake}_as_of_merge_mode(
    session: AsyncSession, {entity_snake}_factory
):
    """Should fall back to main branch when using MERGE mode."""
    service = {Entity}Service(session)

    # Create entity in main branch
    {entity} = await {entity_snake}_factory(branch="main")

    # Query in non-existent branch with MERGE mode
    result = await service.get_{entity_snake}_as_of(
        {entity_id}={entity}.{entity_id}_attr,
        as_of=datetime.now(UTC),
        branch="non-existent-branch",
        branch_mode=BranchMode.MERGE,
    )

    assert result is not None
    assert result.{entity_id}_attr == {entity}.{entity_id}_attr
```

**Fixture Requirements:**
- Use existing `admin_user` fixture from `conftest.py`
- May need to add `control_date` parameter to existing factory fixtures
- If factories don't exist, use direct service creation

---

### Task 4: Update Documentation

**Priority:** MEDIUM

**File:** `docs/02-architecture/cross-cutting/temporal-query-reference.md`

**Section:** Add new subsection after "Zombie Check Tests" (around line 320)

**Content to Add:**

```markdown
### Service-Level Time Travel Support

The following services expose `get_as_of` methods for single-entity time-travel queries:

| Service | Method | Branch Modes | Zombie Check |
|---------|--------|--------------|--------------|
| ProjectService | `get_project_as_of()` | STRICT, MERGE | ✅ |
| WBEService | `get_wbe_as_of()` | STRICT, MERGE | ✅ |
| CostElementService | `get_cost_element_as_of()` | STRICT, MERGE | ✅ |
| CostElementTypeService | `get_cost_element_type_as_of()` | STRICT, MERGE | ✅ |
| DepartmentService | `get_department_as_of()` | STRICT, MERGE | ✅ |
| UserService | `get_user_as_of()` | STRICT, MERGE | ✅ |

**Usage Example:**

```python
from datetime import datetime
from app.services.project import ProjectService

service = ProjectService(session)

# Get project as of January 1st, 2026
as_of = datetime(2026, 1, 1, 12, 0, 0)
project = await service.get_project_as_of(
    project_id=project_id,
    as_of=as_of,
    branch="main",
    branch_mode=BranchMode.STRICT,  # default
)

# For change order preview, use MERGE mode
project = await service.get_project_as_of(
    project_id=project_id,
    as_of=as_of,
    branch="co-123",
    branch_mode=BranchMode.MERGE,  # fall back to main
)
```

**Implementation:** All methods delegate to `TemporalService.get_as_of()` which implements full bitemporal filtering with System Time Travel semantics. See [`TemporalService.get_as_of()`](../../../backend/app/core/versioning/service.py) for implementation details.
```

**Also Update:**
- Remove the "Workaround" note from the "Implementation Notes" section
- Update TD-026 status to "Complete" in `technical-debt-register.md`

---

## Verification Checklist

### Code Quality

- [ ] MyPy strict mode passes with zero errors
- [ ] Ruff linting passes with zero errors
- [ ] All new methods have Google-style docstrings
- [ ] All methods have 100% type hint coverage

### Testing

- [ ] All new unit tests pass (6 test files, ~4 tests each = 24 tests)
- [ ] Existing tests still pass (no regressions)
- [ ] Test coverage ≥80% (target: 85%+ for services)
- [ ] Zombie check tests verify deleted entities respect temporal boundaries

### Documentation

- [ ] `temporal-query-reference.md` updated with service support table
- [ ] TD-026 marked as complete in technical debt register
- [ ] All docstrings follow Google style with Args/Returns/Example sections

### Integration

- [ ] API routes can optionally use service methods (not breaking existing direct usage)
- [ ] Branch mode logic works as expected (STRICT vs MERGE)
- [ ] Time-travel queries return correct historical state

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing API routes | LOW | HIGH | Additive only, no changes to existing methods |
| Type annotation errors | LOW | MEDIUM | MyPy strict mode will catch before commit |
| Test fixture dependencies | MEDIUM | MEDIUM | Use existing fixtures, add `control_date` param if needed |
| Performance regression | LOW | LOW | Direct delegation, no additional queries |

---

## Rollback Plan

If issues arise:
1. Revert service changes (remove added methods)
2. Revert documentation updates
3. Revert TD-026 status change
4. Existing API routes continue using base class method directly (no functional impact)

---

## Completion Criteria

1. ✅ All 6 services have `get_{entity}_as_of()` methods
2. ✅ All methods delegate to `TemporalService.get_as_of()`
3. ✅ All service methods have proper type hints and docstrings
4. ✅ All 6 test files created with zombie check TDD pattern tests
5. ✅ Full backend test suite passes (≥198 tests)
6. ✅ MyPy strict mode passes (zero errors)
7. ✅ Ruff linting passes (zero errors)
8. ✅ Documentation updated (temporal-query-reference.md)
9. ✅ TD-026 marked as complete

---

## Post-Implementation

After completing CHECK phase:
1. Update TD-026 with actual effort and completion date
2. Add iteration summary to technical debt register
3. Consider adding time-travel queries to frontend API client for single-entity endpoints
