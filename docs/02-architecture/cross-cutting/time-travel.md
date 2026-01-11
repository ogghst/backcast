# Time Travel Architecture

**Last Updated:** 2026-01-11
**Related ADRs:** [ADR-005: Bitemporal Versioning](../decisions/ADR-005-bitemporal-versioning.md)

## Overview

This project uses a **Bitemporal Data Model** to track history through the EVCS (Entity Version Control System). This document explains the semantics used for "Time Travel" queries, the standard filter pattern, and TDD practices for temporal features.

---

## Bitemporal Fundamentals

### Two Time Dimensions

| Dimension         | Purpose                                         | Example                                                      |
| ----------------- | ----------------------------------------------- | ------------------------------------------------------------ |
| **Valid Time**    | When the fact was true in the real world        | A project budget was valid from Jan 1 to Mar 31              |
| **Transaction Time** | When the fact was recorded in the database | The budget was entered on Feb 15, then corrected on Feb 20 |

**Implementation:** PostgreSQL `TSTZRANGE` types for both dimensions.

### Key Concepts

- **Append-Only:** Updates create new versions with new `transaction_time` ranges
- **Soft Delete:** `deleted_at` timestamp marks removal (reversible)
- **Branch Isolation:** Each branch (e.g., change orders) maintains separate timelines

---

## Two Types of Time Travel

### 1. Valid Time Travel (Current Knowledge)

**Use Case:** "Show me the list of projects as they were valid on Jan 1st, based on what we know _today_."
**Context:** List views, reports, history browsing.

**Semantics:**

- `valid_time` must contain the target `as_of` timestamp
- `transaction_time` is **current** (i.e., we use the latest record version that covers that valid time)
- `deleted_at`: If the entity was logically deleted _after_ `as_of`, it should appear. If deleted _before_ `as_of`, it should not.

**Why This Matters:**

If we discovered on Feb 20 that a project's budget was wrong, we issue a correction. With **Current Knowledge**, querying "as of Jan 15" shows the corrected value, not the erroneous original value. This is typically what users want for reports and analysis.

### 2. System Time Travel (Audit / Reproducibility)

**Use Case:** "Show me exactly what the system returned on Jan 1st at 12:00 PM." (Undoing a mistake, debugging a past bug).
**Context:** Audit logs, debugging, strict reproducibility.

**Semantics:**

- `valid_time` must contain `as_of`
- `transaction_time` must contain `as_of` (ignores corrections made after the fact)

**Why This Matters:**

For audit compliance, you may need to prove what the system actually showed at a specific moment, regardless of later corrections.

---

## Standardized Filter Pattern

### `_apply_bitemporal_filter` Method

All list endpoints supporting `as_of` MUST use `TemporalService._apply_bitemporal_filter()`.

**Location:** [backend/app/core/versioning/service.py](../../../backend/app/core/versioning/service.py)

**Implementation:**

```python
def _apply_bitemporal_filter(self, stmt: Any, as_of: datetime) -> Any:
    """Apply standardized bitemporal WHERE clauses to a statement.

    Filters for:
    - valid_time contains as_of
    - transaction_time upper bound IS NULL (current knowledge)
    - deleted_at IS NULL OR deleted_at > as_of
    """
    return stmt.where(
        # Check as_of is within valid_time range
        self.entity_class.valid_time.op("@>")(as_of),
        # CRITICAL: Also check as_of >= lower bound (entity existed)
        func.lower(self.entity_class.valid_time) <= as_of,

        # TRANSACTION TIME: Current Knowledge semantics for lists.
        # We want the latest "truth" about the 'as_of' time.
        # So we check that the row has not been superseded (transaction_time upper bound is NULL).
        func.upper(self.entity_class.transaction_time).is_(None),

        # TEMPORAL DELETE CHECK: Entity visible if not deleted, or deleted AFTER as_of
        or_(
            self.entity_class.deleted_at.is_(None),
            self.entity_class.deleted_at > as_of,
        ),
    )
```

### List Endpoint Pattern

**Example from `ProjectService`:**

```python
async def get_projects(
    self,
    skip: int = 0,
    limit: int = 100,
    as_of: datetime | None = None,
    branch: str = "main",
) -> tuple[Sequence[Project], int]:
    """Get projects with optional time travel."""
    stmt = select(Project).where(Project.branch == branch)

    if as_of:
        # Use standardized bitemporal filter
        stmt = self._apply_bitemporal_filter(stmt, as_of)
    else:
        # Standard "Current" Filter
        stmt = stmt.where(
            func.upper(Project.valid_time).is_(None),
            Project.deleted_at.is_(None)
        )

    # Apply pagination and execute...
```

### Service Integration with `TemporalService[T]`

When implementing a versioned entity service, inherit from `TemporalService`:

```python
from app.core.versioning.service import TemporalService

class ProjectService(TemporalService[Project]):
    """Service for Project entities with bitemporal support."""

    async def get_projects(self, as_of: datetime | None = None, ...):
        # _apply_bitemporal_filter is inherited
        # Use it for any list/search with as_of parameter
        ...
```

---

## Zombie Check TDD Pattern

### Purpose

The "Zombie Check" verifies that soft-deleted entities correctly disappear from time-travel queries _after_ their deletion timestamp, but remain visible for queries _before_ deletion.

### Pattern: "Create → Delete → Query Past"

**Test Structure:**

```python
@pytest.mark.asyncio
async def test_project_zombie_check(session: AsyncSession):
    """Verify deleted entities respect time travel boundaries.

    Pattern: Create -> Delete -> Query Past
    """
    # 1. Create entity at T1
    control_date_t1 = datetime(2026, 1, 1, 12, 0, 0)
    project = await service.create(
        project_in=ProjectCreate(code="P001", name="Test Project"),
        actor_id=admin_user.user_id,
        control_date=control_date_t1,
    )

    # 2. Delete entity at T3
    control_date_t3 = datetime(2026, 1, 10, 12, 0, 0)
    await service.soft_delete(
        entity_id=project.project_id,
        actor_id=admin_user.user_id,
        control_date=control_date_t3,
    )

    # 3. Query at T2 (before deletion) - should return entity
    as_of_t2 = datetime(2026, 1, 5, 12, 0, 0)
    result = await service.get_as_of(
        entity_id=project.project_id,
        as_of=as_of_t2,
    )
    assert result is not None, "Entity should be visible before deletion"
    assert result.code == "P001"

    # 4. Query at T4 (after deletion) - should NOT return entity
    as_of_t4 = datetime(2026, 1, 15, 12, 0, 0)
    result = await service.get_as_of(
        entity_id=project.project_id,
        as_of=as_of_t4,
    )
    assert result is None, "Entity should NOT be visible after deletion"
```

### Why This Matters

Without proper `deleted_at` handling in `_apply_bitemporal_filter`, soft-deleted entities would either:

- **Always disappear** (missing the `deleted_at > as_of` condition)
- **Never disappear** (missing the `deleted_at` check entirely)

The Zombie Check ensures correct temporal boundaries for deletion.

---

## Branch Mode Behavior

### STRICT Mode (Default)

```python
result = await service.get_as_of(
    entity_id=project_id,
    as_of=some_date,
    branch="feature-branch-123",
    branch_mode=BranchMode.STRICT,  # Only search in this branch
)
```

**Behavior:** Returns `None` if entity not found on specified branch.

**Use Case:** Change order preview - see only what's changed in this CO.

### MERGE Mode

```python
result = await service.get_as_of(
    entity_id=project_id,
    as_of=some_date,
    branch="feature-branch-123",
    branch_mode=BranchMode.MERGE,  # Fall back to main if not found
)
```

**Behavior:** Falls back to `main` branch if not found in specified branch.

**Use Case:** "What-if" analysis - show base project with CO changes overlaid.

---

## Common Pitfalls

### 1. Using `@>` Operator Alone

```python
# ❌ Wrong: @> treats NULL upper bound as infinity
stmt.where(entity.valid_time.op("@>")(as_of))

# ✅ Correct: Also check lower bound
stmt.where(
    entity.valid_time.op("@>")(as_of),
    func.lower(entity.valid_time) <= as_of,
)
```

### 2. Forgetting `deleted_at` in Time Travel

```python
# ❌ Wrong: Deleted entities invisible in ALL time travel queries
stmt.where(
    entity.valid_time.op("@>")(as_of),
    entity.deleted_at.is_(None),  # Too restrictive!
)

# ✅ Correct: Respect deletion timing
stmt.where(
    entity.valid_time.op("@>")(as_of),
    or_(
        entity.deleted_at.is_(None),
        entity.deleted_at > as_of,  # Zombie protection
    ),
)
```

### 3. Ad-Hoc Filter Implementations

```python
# ❌ Wrong: Custom filter logic in each service
if as_of:
    stmt = stmt.where(
        and_(
            entity.valid_time.contains(as_of),
            entity.deleted_at.is_(None),
        )
    )

# ✅ Correct: Use standardized method
stmt = self._apply_bitemporal_filter(stmt, as_of)
```

---

## Related Documentation

- [ADR-005: Bitemporal Versioning](../decisions/ADR-005-bitemporal-versioning.md) - Architecture decision record
- [TemporalService Implementation](../../../backend/app/core/versioning/service.py) - Source code
- [Branching Requirements](./branching-requirements.md) - Change order isolation
- [API Response Patterns](./api-response-patterns.md) - Filter and pagination standards
