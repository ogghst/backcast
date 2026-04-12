# EVCS Implementation Guide

**Last Updated:** 2026-01-14
**Context:** [EVCS Core Architecture](architecture.md)

> **Note:** This document provides code patterns and implementation recipes for working with EVCS entities. For bitemporal query patterns and time travel semantics, see [Temporal Query Reference](../../../cross-cutting/temporal-query-reference.md). For choosing entity types, see [Entity Classification Guide](entity-classification.md).

---

## Overview

This guide provides practical **code patterns and implementation recipes** for working with EVCS (Entity Versioning Control System) entities.

**What This Document Covers:**

- Query patterns with full code examples
- CRUD operations (create, update, soft delete)
- Branching operations (create, merge, work on branches)
- Relationship patterns (same-branch, fallback)
- Revert patterns (undo changes)
- Performance considerations and indexing
- Service-level time travel methods

**What This Document Does NOT Cover:**

- Architecture and type system → See [EVCS Core Architecture](architecture.md)
- Query semantics and theory → See [Temporal Query Reference](../../../cross-cutting/temporal-query-reference.md)
- Choosing entity types → See [Entity Classification Guide](entity-classification.md)

---

## Query Patterns

### 1. Get Current Version

Retrieve the current active version of an entity:

```python
async def get_current(
    session: AsyncSession,
    entity_class: Type[T],
    root_id: UUID,
    branch: str = "main"
) -> T | None:
    """Get current version of entity in branch."""
    now = func.now()
    root_field = f"{entity_class.__name__.lower().removesuffix('version')}_id"

    stmt = (
        select(entity_class)
        .where(
            getattr(entity_class, root_field) == root_id,
            entity_class.branch == branch,
            entity_class.valid_time.op("@>")(now),
            entity_class.transaction_time.op("@>")(now),
            entity_class.deleted_at.is_(None),
        )
        .order_by(entity_class.valid_time.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

**SQL Equivalent:**

```sql
SELECT * FROM project_versions
WHERE project_id = :root_id
  AND branch = :branch
  AND valid_time @> NOW()
  AND transaction_time @> NOW()
  AND deleted_at IS NULL
ORDER BY valid_time DESC
LIMIT 1;
```

---

### 2. Time Travel Query

Query entity state at a specific point in time:

```python
async def get_at_time(
    session: AsyncSession,
    entity_class: Type[T],
    root_id: UUID,
    as_of: datetime,
    branch: str = "main"
) -> T | None:
    """Get entity version valid at specific time."""
    root_field = f"{entity_class.__name__.lower().removesuffix('version')}_id"

    stmt = (
        select(entity_class)
        .where(
            getattr(entity_class, root_field) == root_id,
            entity_class.branch == branch,
            entity_class.valid_time.op("@>")(as_of),
            entity_class.transaction_time.op("@>")(as_of),
            entity_class.deleted_at.is_(None),
        )
        .order_by(entity_class.valid_time.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

**Example Usage:**

```python
# Get project state as of last month
last_month = datetime(2025, 12, 1, tzinfo=UTC)
project = await get_at_time(session, ProjectVersion, project_id, last_month)
```

> **For more details on time travel semantics and standardized filters, see [Temporal Query Reference](../../../cross-cutting/temporal-query-reference.md).**

---

### 3. Version History

Get complete version history for an entity:

```python
async def get_history(
    session: AsyncSession,
    entity_class: Type[T],
    root_id: UUID,
    branch: str = "main",
    include_deleted: bool = False
) -> list[T]:
    """Get all versions in chronological order."""
    root_field = f"{entity_class.__name__.lower().removesuffix('version')}_id"

    filters = [
        getattr(entity_class, root_field) == root_id,
        entity_class.branch == branch,
    ]

    if not include_deleted:
        filters.append(entity_class.deleted_at.is_(None))

    stmt = (
        select(entity_class)
        .where(*filters)
        .order_by(entity_class.valid_time.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
```

---

### 4. List All Branches

Get all branches for an entity:

```python
async def list_branches(
    session: AsyncSession,
    entity_class: Type[T],
    root_id: UUID
) -> list[str]:
    """Get all branch names for entity."""
    root_field = f"{entity_class.__name__.lower().removesuffix('version')}_id"
    now = func.now()

    stmt = (
        select(entity_class.branch)
        .where(
            getattr(entity_class, root_field) == root_id,
            entity_class.valid_time.op("@>")(now),
            entity_class.deleted_at.is_(None),
        )
        .distinct()
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]
```

---

### 5. Compare Branches

Compare current state between two branches:

```python
async def compare_branches(
    session: AsyncSession,
    entity_class: Type[T],
    root_id: UUID,
    branch_a: str,
    branch_b: str
) -> dict[str, tuple[T | None, T | None]]:
    """Compare entity state between branches."""
    version_a = await get_current(session, entity_class, root_id, branch_a)
    version_b = await get_current(session, entity_class, root_id, branch_b)

    return {
        "branch_a": (branch_a, version_a),
        "branch_b": (branch_b, version_b),
    }
```

---

### 6. Service-Level Time Travel Methods

The following services expose `get_as_of` methods for single-entity time-travel queries:

| Service | Method | Branch Modes | Relations Included |
|---------|--------|--------------|-------------------|
| ProjectService | `get_project_as_of()` | STRICT, MERGE | - |
| WBEService | `get_wbe_as_of()` | STRICT, MERGE | - |
| CostElementService | `get_cost_element_as_of()` | STRICT, MERGE | parent_name, type_name |
| CostElementTypeService | `get_cost_element_type_as_of()` | STRICT, MERGE | - |
| DepartmentService | `get_department_as_of()` | STRICT, MERGE | - |
| UserService | `get_user_as_of()` | STRICT, MERGE | - |

**Usage Example:**

```python
from datetime import datetime
from app.services.project import ProjectService
from app.core.versioning.enums import BranchMode

service = ProjectService(session)

# Get project as of January 1st, 2026
as_of = datetime(2026, 1, 1, 12, 0, 0)
project = await service.get_project_as_of(
    project_id=project_id,
    as_of=as_of,
    branch="main",
)

# For change order preview, use MERGE mode
project = await service.get_project_as_of(
    project_id=project_id,
    as_of=as_of,
    branch="BR-123",
    branch_mode=BranchMode.MERGE,  # fall back to main
)
```

All these methods delegate to `TemporalService.get_as_of()` which implements full bitemporal filtering.

---

## CRUD Operation Patterns

### Create Entity

```python
# Create new project (branchable root)
root_id = uuid4()
service = ProjectService(session)
project = await service.create_root(
    root_id=root_id,
    actor_id=user_id,
    branch="main",
    name="New Project",
    description="Project description"
)
await session.commit()
```

### Update Entity

```python
# Update creates new version, closes old
project = await service.update(
    root_id=project_id,
    actor_id=user_id,
    updates={"name": "Updated Name", "description": "New desc"},
    branch="main"
)
await session.commit()
```

### Soft Delete

```python
# Soft delete (reversible)
deleted = await service.soft_delete(
    root_id=project_id,
    actor_id=user_id,
    branch="main"
)
await session.commit()

# Undelete
restored = await service.undelete(root_id=project_id, branch="main")
await session.commit()
```

---

## Branching Patterns

### Create Branch

```python
# Create change order branch from main
branched = await service.create_branch(
    root_id=project_id,
    actor_id=user_id,
    new_branch="BR-123",
    from_branch="main"
)
await session.commit()
```

### Work on Branch

```python
# Updates on branch don't affect main
await service.update(
    root_id=project_id,
    actor_id=user_id,
    updates={"budget": Decimal("150000")},
    branch="BR-123"
)
await session.commit()
```

### Merge Branch

```python
# Merge change order to main (overwrites main state)
merged = await service.merge_branch(
    root_id=project_id,
    actor_id=user_id,
    source_branch="BR-123",
    target_branch="main"
)
await session.commit()
```

---

## Branch Query Patterns

### Get Current Version on Branch

```python
# Get current version on specific branch
current = await service.get_current(
    root_id=project_id,
    branch="BR-123"
)
```

**SQL Equivalent:**
```sql
SELECT * FROM project_versions
WHERE project_id = :root_id
  AND branch = :branch
  AND valid_time @> NOW()
  AND deleted_at IS NULL
LIMIT 1;
```

### Time Travel on Branch

```python
from datetime import datetime

# Get entity state as of specific time on branch
as_of = datetime(2026, 1, 1, 12, 0, 0)
version = await service.get_as_of(
    root_id=project_id,
    as_of=as_of,
    branch="BR-123",
    branch_mode=BranchMode.STRICT  # Only search in this branch
)
```

### Branch Fallback (MERGE mode)

```python
# Get version from branch, falling back to main if not found
version = await service.get_as_of(
    root_id=project_id,
    as_of=as_of,
    branch="BR-123",
    branch_mode=BranchMode.MERGE  # Fall back to main if not found
)
```

This is useful for "what-if" analysis - show base project with change order changes overlaid.

> **For query semantics and branch mode theory, see [Temporal Query Reference](../../../cross-cutting/temporal-query-reference.md#branch-mode-behavior).**

---

## Relationship Patterns

### One-to-Many with Same Branch

For parent-child relationships where children should stay on same branch:

```python
class ProjectVersion(TemporalBase):
    __tablename__ = "project_versions"

    project_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Strict same-branch relationship
    wbes: Mapped[list["WBEVersion"]] = relationship(
        "WBEVersion",
        primaryjoin="and_("
            "WBEVersion.project_id == ProjectVersion.project_id, "
            "WBEVersion.branch == ProjectVersion.branch, "
            "WBEVersion.valid_time.op('@>')(func.now()), "
            "WBEVersion.deleted_at.is_(None)"
        ")",
        viewonly=True,
        lazy="selectin"
    )
```

### Fallback to Main Branch

For relationships that should fall back to main if not found on branch:

```python
async def get_wbes_with_fallback(
    session: AsyncSession,
    project_id: UUID,
    branch: str
) -> list[WBEVersion]:
    """Get WBEs from branch, falling back to main if not present."""
    now = func.now()

    # Get WBEs on requested branch
    branch_wbes_result = await session.scalars(
        select(WBEVersion)
        .where(
            WBEVersion.project_id == project_id,
            WBEVersion.branch == branch,
            WBEVersion.valid_time.op("@>")(now),
            WBEVersion.deleted_at.is_(None),
        )
    )
    branch_wbes = branch_wbes_result.all()

    branch_wbe_ids = {w.wbe_id for w in branch_wbes}

    # Get main branch WBEs not on target branch
    main_fallback_result = await session.scalars(
        select(WBEVersion)
        .where(
            WBEVersion.project_id == project_id,
            WBEVersion.branch == "main",
            WBEVersion.valid_time.op("@>")(now),
            WBEVersion.deleted_at.is_(None),
            ~WBEVersion.wbe_id.in_(branch_wbe_ids),
        )
    )
    main_fallback = main_fallback_result.all()

    return list(branch_wbes) + list(main_fallback)
```

---

## Revert Patterns

### Revert to Previous Version

```python
# Revert to immediate parent
reverted = await service.revert(
    root_id=project_id,
    actor_id=user_id,
    branch="main"
)
await session.commit()
```

### Revert to Specific Version

```python
# Revert to specific historical version
reverted = await service.revert(
    root_id=project_id,
    actor_id=user_id,
    branch="main",
    to_version_id=target_version_id
)
await session.commit()
```

---

## Performance Considerations

### Query Optimization

1. **Always add branch filter** - Reduces result set significantly
2. **Use GIST indexes** - Essential for range operator performance
3. **Limit history queries** - Add pagination for large histories
4. **Eager load children** - Use `selectinload()` for relationships

### Index Usage

```sql
-- Ensure these indexes exist:
CREATE INDEX ix_versions_valid_gist ON versions USING GIST (valid_time);
CREATE INDEX ix_versions_branch ON versions (branch);
CREATE INDEX ix_versions_entity_id ON versions (entity_id);
```

### Avoiding N+1 Queries

```python
# Bad: N+1 queries
for project in projects:
    wbes = await project.awaitable_attrs.wbes  # Lazy load each (if async attrs enabled)

# Good: Eager loading
stmt = select(ProjectVersion).options(selectinload(ProjectVersion.wbes))
result = await session.execute(stmt)
projects = result.scalars().all()
```

---

## Non-Versioned Entity Patterns

For entities that don't require temporal versioning (preferences, configuration), use `SimpleEntityBase` and `SimpleService[T]` patterns.

### Basic CRUD Pattern

```python
class UserPreferencesService(SimpleService[UserPreferences]):
    """Service for non-versioned user preferences."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, UserPreferences)

    async def get_for_user(self, user_id: UUID) -> UserPreferences | None:
        return await self.session.scalar(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )

    async def upsert(self, user_id: UUID, **prefs) -> UserPreferences:
        existing = await self.get_for_user(user_id)
        if existing:
            return await self.update(existing.id, **prefs)
        return await self.create(user_id=user_id, **prefs)
```

### Service Comparison by Entity Type

| Entity Type       | Protocol               | Service                | Create               | Update                  | Delete      | Read                          |
| ----------------- | ---------------------- | ---------------------- | -------------------- | ----------------------- | ----------- | ----------------------------- |
| **Non-versioned** | `SimpleEntityProtocol` | `SimpleService[T]`     | INSERT               | UPDATE in place         | Hard DELETE | SELECT by ID                  |
| **Versioned**     | `VersionableProtocol`  | `TemporalService[T]`   | Version + valid_time | Close old + create new  | Soft delete | Filter by valid_time          |
| **Branchable**    | `BranchableProtocol`   | `BranchableService[T]` | Version + branch     | Close + clone on branch | Soft delete | Filter by valid_time + branch |

> **Note:** For complete type system details including Protocols and ABCs, see [Type System](architecture.md#type-system) in architecture.md.

---

## See Also

### Architecture & Design

- [EVCS Core Architecture](architecture.md) - Complete EVCS system architecture
- [Entity Classification Guide](entity-classification.md) - Choosing Simple/Versionable/Branchable entity types
- [ADR-005: Bitemporal Versioning](../../decisions/ADR-005-bitemporal-versioning.md) - Architecture decision record
- [ADR-006: Protocol-Based Type System](../../decisions/ADR-006-protocol-based-type-system.md) - Type system design

### Query References

- [Temporal Query Reference](../../../cross-cutting/temporal-query-reference.md) - Bitemporal queries and time travel semantics

### Database

- [Database Strategy](../../../cross-cutting/database-strategy.md) - TSTZRANGE usage and indexing

### Source Code

- [TemporalService Implementation](../../../../app/core/versioning/service.py) - Core service with temporal support
- [BranchableService Implementation](../../../../app/core/branching/service.py) - Branch-aware service operations
