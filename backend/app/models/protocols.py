"""Protocol definitions for EVCS Core type system.

Defines the three-tier Protocol hierarchy for entity classification:
- Tier 0: EntityProtocol (base - all entities have UUID)
- Tier 1a: SimpleEntityProtocol (non-versioned with timestamps)
- Tier 1b: VersionableProtocol (temporal tracking)
- Tier 2: BranchableProtocol (full EVCS with branching)

See ADR-006 for detailed rationale and design decisions.
"""

from datetime import datetime
from typing import Any, Protocol, TypeVar, runtime_checkable
from uuid import UUID

# Note: TSTZRANGE is a PostgreSQL type represented in Python as a range object
# For type hints, we use Any since the actual type is database-specific


# ==============================================================================
# Protocol-Bound TypeVars
# ==============================================================================

# These TypeVars are bound to their respective protocols to ensure type safety
# in generic commands and services.

TSimple = TypeVar("TSimple", bound="SimpleEntityProtocol")
"""TypeVar bound to SimpleEntityProtocol for non-versioned entities."""

TVersionable = TypeVar("TVersionable", bound="VersionableProtocol")
"""TypeVar bound to VersionableProtocol for versioned (bitemporal) entities."""

TBranchable = TypeVar("TBranchable", bound="BranchableProtocol")
"""TypeVar bound to BranchableProtocol for full EVCS entities with branching."""


# ==============================================================================
# Tier 0: Base Protocol
# ==============================================================================


@runtime_checkable
class EntityProtocol(Protocol):
    """Base protocol - all entities have an ID."""

    id: UUID


# ==============================================================================
# Tier 1a: Simple (Non-Versioned)
# ==============================================================================


@runtime_checkable
class SimpleEntityProtocol(EntityProtocol, Protocol):
    """Non-versioned entities track creation and modification times.

    Use for: configuration, preferences, reference data, transient data.
    """

    created_at: datetime
    updated_at: datetime


# ==============================================================================
# Tier 1b: Versionable (Temporal)
# ==============================================================================


@runtime_checkable
class VersionableProtocol(EntityProtocol, Protocol):
    """Versioned entities use bitemporal ranges instead of mutable timestamps.

    Use for: audit logs, user profiles, departments - entities requiring
    temporal tracking but not branching.
    """

    valid_time: Any  # TSTZRANGE in PostgreSQL
    transaction_time: Any  # TSTZRANGE in PostgreSQL
    deleted_at: datetime | None
    created_by: UUID
    deleted_by: UUID | None

    @property
    def is_deleted(self) -> bool:
        """Check if this version is soft-deleted."""
        ...

    def soft_delete(self) -> None:
        """Mark this version as deleted (reversible)."""
        ...

    def undelete(self) -> None:
        """Restore a soft-deleted version."""
        ...

    def clone(self, **overrides: Any) -> "VersionableProtocol":
        """Clone this version for updates, branches, or merges."""
        ...


# ==============================================================================
# Tier 2: Branchable (Full EVCS)
# ==============================================================================


@runtime_checkable
class BranchableProtocol(VersionableProtocol, Protocol):
    """Full EVCS - versioning + branching.

    Use for: business entities requiring change orders, drafts, or parallel
    development (Projects, WBEs, Cost Elements).
    """

    branch: str
    parent_id: UUID | None
    merge_from_branch: str | None

    @property
    def is_current(self) -> bool:
        """Check if this is the current version (open-ended temporal ranges)."""
        ...
