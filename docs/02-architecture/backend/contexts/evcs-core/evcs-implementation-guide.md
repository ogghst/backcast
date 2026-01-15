# EVCS Implementation Guide

**Last Updated:** 2026-01-14
**Context:** [EVCS Core Architecture](architecture.md)

> **Note:** This document provides code patterns and implementation recipes for working with EVCS entities. For bitemporal query patterns and time travel semantics, see [Temporal Query Reference](../../../cross-cutting/temporal-query-reference.md). For choosing entity types, see [Entity Classification Guide](entity-classification.md).

---

## Overview

This guide provides practical code patterns for implementing EVCS (Entity Versioning Control System) features:

- **Query Patterns:** Get current, time travel, version history
- **CRUD Patterns:** Create, update, soft delete operations
- **Branching Patterns:** Create branches, work on branches, merge
- **Relationship Patterns:** Same-branch and fallback relationships
- **Revert Patterns:** Undo changes by reverting to previous versions
- **Performance:** Query optimization and indexing strategies

---

## Query Patterns

### 1. Get Current Version

Retrieve the current active version of an entity:

```python
def get_current(
    session: Session,
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
    result = session.execute(stmt)
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
def get_at_time(
    session: Session,
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
    result = session.execute(stmt)
    return result.scalar_one_or_none()
```

**Example Usage:**

```python
# Get project state as of last month
last_month = datetime(2025, 12, 1, tzinfo=UTC)
project = get_at_time(session, ProjectVersion, project_id, last_month)
```

> **For more details on time travel semantics and standardized filters, see [Temporal Query Reference](../../../cross-cutting/temporal-query-reference.md).**

---

### 3. Version History

Get complete version history for an entity:

```python
def get_history(
    session: Session,
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
    result = session.execute(stmt)
    return list(result.scalars().all())
```

---

### 4. List All Branches

Get all branches for an entity:

```python
def list_branches(
    session: Session,
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
    result = session.execute(stmt)
    return [row[0] for row in result.all()]
```

---

### 5. Compare Branches

Compare current state between two branches:

```python
def compare_branches(
    session: Session,
    entity_class: Type[T],
    root_id: UUID,
    branch_a: str,
    branch_b: str
) -> dict[str, tuple[T | None, T | None]]:
    """Compare entity state between branches."""
    version_a = get_current(session, entity_class, root_id, branch_a)
    version_b = get_current(session, entity_class, root_id, branch_b)

    return {
        "branch_a": (branch_a, version_a),
        "branch_b": (branch_b, version_b),
    }
```

---

## CRUD Operation Patterns

### Create Entity

```python
# Create new project
root_id = uuid4()
service = ProjectService(session)
project = service.create(
    root_id=root_id,
    branch="main",
    name="New Project",
    description="Project description"
)
session.commit()
```

### Update Entity

```python
# Update creates new version, closes old
project = service.update(
    root_id=project_id,
    updates={"name": "Updated Name", "description": "New desc"},
    branch="main"
)
session.commit()
```

### Soft Delete

```python
# Soft delete (reversible)
deleted = service.soft_delete(root_id=project_id, branch="main")
session.commit()

# Undelete
restored = service.undelete(root_id=project_id, branch="main")
session.commit()
```

---

## Branching Patterns

### Create Branch

```python
# Create change order branch from main
branched = service.create_branch(
    root_id=project_id,
    new_branch="co-123",
    from_branch="main"
)
session.commit()
```

### Work on Branch

```python
# Updates on branch don't affect main
service.update(
    root_id=project_id,
    updates={"budget": Decimal("150000")},
    branch="co-123"
)
session.commit()
```

### Merge Branch

```python
# Merge change order to main (overwrites main state)
merged = service.merge_branch(
    root_id=project_id,
    source_branch="co-123",
    target_branch="main"
)
session.commit()
```

> **For complete branching documentation (branch types, operations, locking), see [Temporal Query Reference](../../../cross-cutting/temporal-query-reference.md#branch-mode-behavior).**

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
def get_wbes_with_fallback(
    session: Session,
    project_id: UUID,
    branch: str
) -> list[WBEVersion]:
    """Get WBEs from branch, falling back to main if not present."""
    now = func.now()

    # Get WBEs on requested branch
    branch_wbes = session.scalars(
        select(WBEVersion)
        .where(
            WBEVersion.project_id == project_id,
            WBEVersion.branch == branch,
            WBEVersion.valid_time.op("@>")(now),
            WBEVersion.deleted_at.is_(None),
        )
    ).all()

    branch_wbe_ids = {w.wbe_id for w in branch_wbes}

    # Get main branch WBEs not on target branch
    main_fallback = session.scalars(
        select(WBEVersion)
        .where(
            WBEVersion.project_id == project_id,
            WBEVersion.branch == "main",
            WBEVersion.valid_time.op("@>")(now),
            WBEVersion.deleted_at.is_(None),
            ~WBEVersion.wbe_id.in_(branch_wbe_ids),
        )
    ).all()

    return list(branch_wbes) + list(main_fallback)
```

---

## Revert Patterns

### Revert to Previous Version

```python
# Revert to immediate parent
reverted = service.revert(root_id=project_id, branch="main")
session.commit()
```

### Revert to Specific Version

```python
# Revert to specific historical version
reverted = service.revert(
    root_id=project_id,
    branch="main",
    to_version_id=target_version_id
)
session.commit()
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
    wbes = project.wbes  # Lazy load each

# Good: Eager loading
stmt = select(ProjectVersion).options(selectinload(ProjectVersion.wbes))
projects = session.execute(stmt).scalars().all()
```

---

## Non-Versioned Entity Patterns

For entities that don't require temporal versioning (preferences, configuration), use `SimpleEntityBase` and `SimpleService[T]` patterns.

### Basic CRUD Pattern

```python
class UserPreferencesService(SimpleService[UserPreferences]):
    """Service for non-versioned user preferences."""

    def __init__(self, session: Session):
        super().__init__(session, UserPreferences)

    def get_for_user(self, user_id: UUID) -> UserPreferences | None:
        return self.session.scalar(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )

    def upsert(self, user_id: UUID, **prefs) -> UserPreferences:
        existing = self.get_for_user(user_id)
        if existing:
            return self.update(existing.id, **prefs)
        return self.create(user_id=user_id, **prefs)
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
