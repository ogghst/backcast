"""Mixins for versioned and branchable entities.

Provides:
- VersionableMixin: Bitemporal versioning with TSTZRANGE
- BranchableMixin: Branching support for full EVCS entities
"""

from datetime import UTC, datetime
from typing import Any, Self
from uuid import UUID

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import TSTZRANGE as PG_TSTZRANGE
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class VersionableMixin:
    """Mixin for temporal versioning - compose with EntityBase.

    When composed with EntityBase, satisfies: VersionableProtocol

    Provides bitemporal tracking:
    - valid_time: When the data is/was effective (business time)
    - transaction_time: When the record was created/modified (system time)
    - deleted_at: Soft delete timestamp (recoverable)
    """

    valid_time: Mapped[PG_TSTZRANGE] = mapped_column(
        PG_TSTZRANGE,
        nullable=False,
        server_default=func.tstzrange(func.now(), None, "[]"),
    )

    transaction_time: Mapped[PG_TSTZRANGE] = mapped_column(
        PG_TSTZRANGE,
        nullable=False,
        server_default=func.tstzrange(func.now(), None, "[]"),
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Audit Trail
    created_by: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)
    deleted_by: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True)

    @property
    def is_deleted(self) -> bool:
        """Check if this version is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark this version as deleted (reversible)."""
        self.deleted_at = datetime.now(UTC)

    def undelete(self) -> None:
        """Restore a soft-deleted version."""
        self.deleted_at = None

    def clone(self, **overrides: Any) -> Self:
        """Clone this version for updates, branches, or merges."""
        from sqlalchemy import inspect
        
        mapper = inspect(self.__class__)
        data = {}
        
        # Iterate over all mapped columns to get the correct Python attribute names
        for prop in mapper.attrs:
            # We only want column-mapped properties (not relationships)
            if hasattr(prop, "columns"):
                pk_name = prop.key
                data[pk_name] = getattr(self, pk_name)

        data.update(overrides)
        data.pop("id", None)  # New version gets new ID
        data.pop("valid_time", None)  # Let DB generate new range
        data.pop("transaction_time", None)  # Let DB generate new range
        return self.__class__(**data)


class BranchableMixin:
    """Mixin for branching - compose with VersionableMixin.

    When composed with EntityBase + VersionableMixin, satisfies: BranchableProtocol

    Provides branching capabilities:
    - branch: Branch name (default: "main")
    - parent_id: Previous version in DAG chain
    - merge_from_branch: Track merge source
    """

    branch: Mapped[str] = mapped_column(String(80), default="main")
    parent_id: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True)
    merge_from_branch: Mapped[str | None] = mapped_column(String(80), nullable=True)

    @property
    def is_current(self) -> bool:
        """Check if this is the current version (open-ended temporal ranges)."""
        return (
            self.valid_time.upper is None  # type: ignore
            and self.transaction_time.upper is None  # type: ignore
            and not self.is_deleted  # type: ignore
        )
