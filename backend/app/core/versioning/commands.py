"""Generic commands for versioned entities.

Provides Protocol-bound command ABCs and concrete implementations:
- VersionedCommandABC: For VersionableProtocol entities
- Concrete commands: Create, Update, SoftDelete

Note: Branching commands have been moved to app.core.branching.commands.
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar, cast
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protocols import VersionableProtocol

TVersionable = TypeVar("TVersionable", bound=VersionableProtocol)


# ==============================================================================
# Versioned Entity Commands (Temporal, No Branching)
# ==============================================================================


class VersionedCommandABC[TVersionable: VersionableProtocol](ABC):
    """ABC for versioned entity commands (no branching).

    Type parameter TVersionable must satisfy VersionableProtocol.
    """

    entity_class: type[TVersionable]
    root_id: UUID

    def __init__(self, entity_class: type[TVersionable], root_id: UUID) -> None:
        self.entity_class = entity_class
        self.root_id = root_id

    @abstractmethod
    async def execute(self, session: AsyncSession) -> TVersionable | None:
        """Execute the command and return the result."""
        ...

    def _root_field_name(self) -> str:
        """Derive root field name from entity class name."""
        # e.g., UserVersion -> user_id
        class_name = self.entity_class.__name__.lower()
        if class_name.endswith("version"):
            class_name = class_name[:-7]  # Remove "version" suffix
        return f"{class_name}_id"

    async def _close_version(
        self, session: AsyncSession, version: TVersionable
    ) -> None:
        """Close a version by setting upper bound on valid_time."""
        # CRITICAL FIX: PostgreSQL creates EMPTY range if lower >= upper
        # Solution: Ensure upper is always > lower using GREATEST
        # Use SQLAlchemy ORM with PostgreSQL-specific functions

        stmt = (
            update(self.entity_class)
            .where(cast(Any, self.entity_class).id == version.id)
            .values(
                valid_time=func.tstzrange(
                    func.lower(cast(Any, self.entity_class).valid_time),
                    func.greatest(
                        func.lower(cast(Any, self.entity_class).valid_time) + text("interval '1 microsecond'"),
                        func.current_timestamp()
                    ),
                    "[)"
                )
            )
        )

        result = await session.execute(stmt)

        if result.rowcount == 0:
            raise RuntimeError(f"Concurrency Error: Failed to close version {version.id}. Row not updated.")

        await session.flush()
        session.expire(version)


class CreateVersionCommand(VersionedCommandABC[TVersionable]):
    """Create initial version of a versioned entity."""

    def __init__(
        self, entity_class: type[TVersionable], root_id: UUID, **fields: Any
    ) -> None:
        self.entity_class = entity_class
        self.root_id = root_id
        self.fields = fields

    async def execute(self, session: AsyncSession) -> TVersionable:
        """Create new version with open-ended valid_time."""
        version = self.entity_class(
            **self.fields
        )  # Model should handle TSTZRANGE defaults
        session.add(version)
        await session.flush()
        await session.refresh(version)
        return version


class UpdateVersionCommand(VersionedCommandABC[TVersionable]):
    """Update versioned entity - closes current, creates new."""

    def __init__(
        self, entity_class: type[TVersionable], root_id: UUID, **updates: Any
    ) -> None:
        self.entity_class = entity_class
        self.root_id = root_id
        self.updates = updates

    async def execute(self, session: AsyncSession) -> TVersionable:
        """Close current version and create new with updates."""
        # Get current version
        current = await self._get_current(session)
        if not current:
            raise ValueError(f"No active version found for {self.root_id}")

        # Clone and apply updates (must happen before close due to expire)
        new_version = cast(TVersionable, current.clone(**self.updates))

        # Close current
        await self._close_version(session, current)

        session.add(new_version)
        await session.flush()
        return new_version

    async def _get_current(self, session: AsyncSession) -> TVersionable | None:
        """Get current active version."""
        stmt = (
            select(self.entity_class)
            .where(
                getattr(
                    self.entity_class,
                    self._root_field_name(),
                )
                == self.root_id,
                cast(Any, self.entity_class).valid_time.op("@>")(func.current_timestamp()),
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .order_by(cast(Any, self.entity_class).valid_time.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()




class SoftDeleteCommand(VersionedCommandABC[TVersionable]):
    """Soft delete a versioned entity."""

    async def execute(self, session: AsyncSession) -> TVersionable | None:
        """Mark current version as deleted."""
        current = await self._get_current(session)
        if current:
            current.soft_delete()
            await session.flush()
        return current

    async def _get_current(self, session: AsyncSession) -> TVersionable | None:
        """Get current active version."""
        stmt = (
            select(self.entity_class)
            .where(
                getattr(
                    self.entity_class,
                    self._root_field_name(),
                )
                == self.root_id,
                cast(Any, self.entity_class).valid_time.op("@>")(func.current_timestamp()),
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .order_by(cast(Any, self.entity_class).valid_time.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
