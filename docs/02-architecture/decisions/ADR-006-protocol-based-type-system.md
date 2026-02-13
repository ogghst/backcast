# ADR-006: Protocol-Based Type System for EVCS Core

## Status

✅ Accepted (2026-01-02)

**Extends:** [ADR-005: Bitemporal Versioning Pattern](ADR-005-bitemporal-versioning.md)

## Context

Following ADR-005's adoption of bitemporal versioning with generic commands and services, we needed to strengthen type safety and provide clearer entity classification. The original implementation used generic `T` TypeVars without Protocol constraints, which:

- Did not enforce structural requirements at the type level
- Made it unclear which commands/services apply to which entity types
- Lacked compile-time verification that entities satisfy expected interfaces
- Did not distinguish between non-versioned (config), versioned (temporal), and branchable (full EVCS) entities

Python's structural typing via Protocols (PEP 544) provides a way to:

- Define entity categories through structural interfaces
- Bind generic TypeVars to specific Protocol contracts
- Enable MyPy to verify type compatibility at compile time
- Self-document entity requirements through Protocol definitions

## Decision

Adopt a **three-tier Protocol-based type system** for EVCS Core entities:

### Protocol Hierarchy

```python
from typing import Protocol, TypeVar
from datetime import datetime
from uuid import UUID

# Tier 0: Base
class EntityProtocol(Protocol):
    """Base protocol - all entities have an ID."""
    id: UUID

# Tier 1a: Simple (Non-Versioned)
class SimpleEntityProtocol(EntityProtocol, Protocol):
    """For configuration and preferences - timestamps only."""
    created_at: datetime
    updated_at: datetime

# Tier 1b: Versionable (Temporal)
class VersionableProtocol(EntityProtocol, Protocol):
    """For entities requiring temporal tracking."""
    valid_time: TSTZRANGE
    transaction_time: TSTZRANGE
    deleted_at: datetime | None

    def soft_delete(self) -> None: ...
    def undelete(self) -> None: ...

# Tier 2: Branchable (Full EVCS)
class BranchableProtocol(VersionableProtocol, Protocol):
    """For entities requiring branching support."""
    branch: str
    parent_id: UUID | None
    merge_from_branch: str | None

    def clone(self, **overrides: Any) -> Self: ...
```

### Bound TypeVars

Replace generic `T` with Protocol-bound TypeVars:

```python
TSimple = TypeVar('TSimple', bound=SimpleEntityProtocol)
TVersionable = TypeVar('TVersionable', bound=VersionableProtocol)
TBranchable = TypeVar('TBranchable', bound=BranchableProtocol)
```

### Command and Service Type Constraint

Commands and services specify their supported entity tier:

```python
# Simple entity commands (config, preferences)
class SimpleCommandABC(ABC, Generic[TSimple]):
    entity_class: type[TSimple]
    def execute(self, session: Session) -> TSimple: ...

# Versioned entity commands (temporal tracking)
class VersionedCommandABC(ABC, Generic[TVersionable]):
    entity_class: type[TVersionable]
    root_id: UUID
    def execute(self, session: Session) -> TVersionable: ...

# Branchable entity commands (full EVCS)
class BranchCommandABC(VersionedCommandABC[TBranchable]):
    branch: str = "main"
```

Services follow the same pattern:

```python
class SimpleService(Generic[TSimple]): ...
class TemporalService(Generic[TVersionable]): ...
class BranchableService(Generic[TBranchable]): ...
```

### ABC Implementations

Provide mixins/base classes that satisfy Protocols:

```python
# Simple entities
class SimpleEntityBase(EntityBase):
    __abstract__ = True
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

# Versioned entities
class VersionableMixin(ABC):
    valid_time: Mapped[TSTZRANGE]
    transaction_time: Mapped[TSTZRANGE]
    deleted_at: Mapped[datetime | None]
    # ... methods

# Branchable entities
class BranchableMixin(ABC):
    branch: Mapped[str]
    parent_id: Mapped[UUID | None]
    merge_from_branch: Mapped[str | None]
    # ... methods

# Composition
class ProjectVersion(EntityBase, VersionableMixin, BranchableMixin):
    """Satisfies BranchableProtocol"""
    ...
```

## Consequences

### Positive

- **Compile-Time Type Safety:** MyPy verifies entities satisfy Protocol contracts
- **Clear Entity Categories:** Three-tier hierarchy makes design intent explicit
- **Self-Documenting:** Protocol definitions serve as living documentation
- **Prevent Misuse:** Can't use `BranchCommandABC` on a `SimpleEntityProtocol`
- **IDE Support:** Better autocomplete and type hints
- **Aligned with Python Standards:** Follows PEP 544 structural typing
- **No Runtime Overhead:** Protocols are type-checking only

### Negative

- **Learning Curve:** Developers must understand Protocols vs. ABCs
- **More TypeVars:** `TSimple`/`TVersionable`/`TBranchable` vs. single `T`
- **Migration Needed:** Existing code using generic `T` must be updated
- **MyPy Required:** Type safety only enforced with static type checker

### Neutral

- **Documentation Alignment:** Requires updating all architecture docs
- **Code Organization:** Protocols defined separately from implementations

## Alternatives Considered

### Alternative 1: Keep Generic T

Continue using unbounded `TypeVar('T')`.

- **Pros:** Simple, no migration needed
- **Cons:** No compile-time verification, unclear entity requirements
- **Rejected:** Does not provide desired type safety

### Alternative 2: ABC-Only Approach

Use only Abstract Base Classes without Protocols.

- **Pros:** Familiar to Python developers, runtime checks
- **Cons:** Requires inheritance, no structural typing, couples interface to implementation
- **Rejected:** Protocols provide better separation of concerns

### Alternative 3: Four-Tier Hierarchy

Add separate tier for "Temporal non-branchable" entities.

- **Pros:** More granular classification
- **Cons:** Complexity outweighs benefit, most temporal entities should support branching
- **Rejected:** Three tiers sufficient for current needs

## Implementation Notes

### Entity Classification Decision Tree

Developers choose entity type based on requirements:

```
START
  ↓
  Does entity need version history?
  ├─ NO → SimpleEntityProtocol
  │        (config, preferences, transient data)
  │        Use: SimpleEntityBase
  │
  └─ YES → Does entity need branching?
           ├─ NO → VersionableProtocol
           │        (audit logs, minimal temporal tracking)
           │        Use: EntityBase + VersionableMixin
           │
           └─ YES → BranchableProtocol
                    (business entities, change orders)
                    Use: EntityBase + VersionableMixin + BranchableMixin
```

### File Organization

```
app/models/
├── protocols.py          # Protocol definitions
├── mixins.py            # VersionableMixin, BranchableMixin
├── domain/
│   └── base.py          # EntityBase, SimpleEntityBase
│
app/core/versioning/
├── commands.py          # Command ABCs with bound TypeVars
└── services.py          # Service classes with bound TypeVars
```

### Migration Path

1. ✅ Define Protocols in `app/models/protocols.py`
2. ✅ Update documentation with Protocol-based architecture
3. ⏳ Update existing commands/services to use bound TypeVars
4. ⏳ Add MyPy strict checks to CI/CD
5. ⏳ Migrate existing entities to satisfy Protocols

## Related Documentation

- [EVCS Core Architecture](../backend/contexts/evcs-core/architecture.md)
- [Entity Classification Guide](../backend/contexts/evcs-core/entity-classification.md)
- [Coding Standards: Type Safety](../../00-meta/coding_standards.md#12-type-safety-mypy)
- [ADR-005: Bitemporal Versioning Pattern](ADR-005-bitemporal-versioning.md)
