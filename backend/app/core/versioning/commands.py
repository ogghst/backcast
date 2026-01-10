"""Generic commands for versioned entities.

Provides Protocol-bound command ABCs and concrete implementations:
- VersionedCommandABC: For VersionableProtocol entities
- Concrete commands: Create, Update, SoftDelete

Note: Branching commands have been moved to app.core.branching.commands.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
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

    actor_id: UUID

    def __init__(
        self, entity_class: type[TVersionable], root_id: UUID, actor_id: UUID
    ) -> None:
        self.entity_class = entity_class
        self.root_id = root_id
        self.actor_id = actor_id

    @abstractmethod
    async def execute(self, session: AsyncSession) -> TVersionable | None:
        """Execute the command and return the result."""
        ...

    def _root_field_name(self) -> str:
        """Derive root field name from entity class name."""
        # e.g., UserVersion -> user_id
        import re

        class_name = self.entity_class.__name__
        if class_name.endswith("Version"):
            class_name = class_name[:-7]  # Remove "version" suffix

        # CamelCase to snake_case
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", class_name)
        snake_name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        return f"{snake_name}_id"

    async def _close_version(
        self,
        session: AsyncSession,
        version: TVersionable,
        close_at_valid_time: datetime | None = None
    ) -> None:
        """Close a version by setting upper bound on BOTH temporal dimensions.
        
        CRITICAL: Bitemporal correctness requires closing BOTH:
        - valid_time: When data stopped being valid (close_at_valid_time or clock_timestamp)
        - transaction_time: When it was recorded in database (clock_timestamp)
        """
        # Determine closing time for valid_time
        # If control_date (close_at_valid_time) is provided, use it.
        # Otherwise use clock_timestamp() (actual now)
        valid_upper = close_at_valid_time if close_at_valid_time else func.clock_timestamp()

        stmt = (
            update(self.entity_class)
            .where(cast(Any, self.entity_class).id == version.id)
            .values(
                # Close valid_time
                valid_time=func.tstzrange(
                    func.lower(cast(Any, self.entity_class).valid_time),
                    valid_upper,
                    "[)",
                ),
                # Close transaction_time to now - marks when superseded
                transaction_time=func.tstzrange(
                    func.lower(cast(Any, self.entity_class).transaction_time),
                    func.clock_timestamp(),
                    "[)",
                ),
            )
        )

        result = await session.execute(stmt)

        if cast(Any, result).rowcount == 0:
            raise RuntimeError(
                f"Concurrency Error: Failed to close version {version.id}. Row not updated."
            )

        await session.flush()
        session.expire(version)


class CreateVersionCommand(VersionedCommandABC[TVersionable]):
    """Create initial version of a versioned entity."""

    def __init__(
        self,
        entity_class: type[TVersionable],
        root_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
        **fields: Any,
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.fields = fields
        self.control_date = control_date or datetime.now(UTC)

    async def execute(self, session: AsyncSession) -> TVersionable:
        """Create new version with valid_time set to control_date (or now).
        
        CRITICAL: Uses clock_timestamp() for transaction_time to ensure uniqueness
        and current recording time, while allowing valid_time to be backdated/future-dated
        via control_date.
        """
        version = cast(Any, self.entity_class)(
            created_by=self.actor_id, **self.fields
        )  # Model should handle TSTZRANGE defaults with now()
        session.add(version)
        await session.flush()  # Get ID assigned

        # Set valid_time to control_date, transaction_time to clock_timestamp()
        stmt = text(
            f"""
            UPDATE {self.entity_class.__tablename__}
            SET 
                valid_time = tstzrange(:control_date, NULL, '[]'),
                transaction_time = tstzrange(clock_timestamp(), NULL, '[]')
            WHERE id = :version_id
            """
        )
        await session.execute(stmt, {
            "control_date": self.control_date,
            "version_id": version.id
        })
        await session.flush()
        await session.refresh(version)
        return cast(TVersionable, version)


class UpdateVersionCommand(VersionedCommandABC[TVersionable]):
    """Update versioned entity - closes current, creates new."""

    def __init__(
        self,
        entity_class: type[TVersionable],
        root_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
        **updates: Any,
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.updates = updates
        self.control_date = control_date or datetime.now(UTC)

    async def execute(self, session: AsyncSession) -> TVersionable:
        """Close current version and create new with updates.
        
        CRITICAL: Uses clock_timestamp() for new version to ensure bitemporal
        correctness. PostgreSQL's now()/current_timestamp() is transaction-scoped
        and returns the same value throughout the transaction.
        """
        # Get current version
        current = await self._get_current(session)
        if not current:
            raise ValueError(f"No active version found for {self.root_id}")

        # Clone and apply updates (must happen before close due to expire)
        new_version = cast(
            TVersionable,
            current.clone(created_by=self.actor_id, **self.updates),
        )

        # Close current - this sets upper bounds using control_date (for valid_time)
        await self._close_version(session, current, close_at_valid_time=self.control_date)

        # CRITICAL: Set transaction_time explicitly using clock_timestamp()
        # to ensure the new version's lower bound is AFTER the closed version's upper bound
        from sqlalchemy import text
        session.add(new_version)
        await session.flush()  # Flush to get the ID

        # Set valid_time to control_date, transaction_time to clock_timestamp()
        stmt_fix_time = text(
            f"""
            UPDATE {self.entity_class.__tablename__}
            SET 
                valid_time = tstzrange(:control_date, NULL, '[]'),
                transaction_time = tstzrange(clock_timestamp(), NULL, '[]')
            WHERE id = :version_id
            """
        )
        await session.execute(stmt_fix_time, {
            "control_date": self.control_date,
            "version_id": new_version.id
        })
        await session.flush()
        await session.refresh(new_version)

        return new_version

    async def _get_current(self, session: AsyncSession) -> TVersionable | None:
        """Get current active version (HEAD)."""
        stmt = (
            select(self.entity_class)
            .where(
                getattr(
                    self.entity_class,
                    self._root_field_name(),
                )
                == self.root_id,
                func.upper(cast(Any, self.entity_class).valid_time).is_(None),  # Use open-ended check
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .order_by(cast(Any, self.entity_class).valid_time.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()



class SoftDeleteCommand(VersionedCommandABC[TVersionable]):
    """Soft delete a versioned entity."""

    def __init__(
        self,
        entity_class: type[TVersionable],
        root_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.control_date = control_date or datetime.now(UTC)

    async def execute(self, session: AsyncSession) -> TVersionable:
        """Mark current version as deleted."""
        current = await self._get_current(session)
        if not current:
            raise ValueError(f"No active version found for {self.root_id}")

        current.deleted_at = self.control_date  # Use control_date
        current.deleted_by = self.actor_id  # type: ignore[attr-defined]
        await session.flush()
        return current

    async def _get_current(self, session: AsyncSession) -> TVersionable | None:
        """Get current active version."""
        # Use more robust check for current version (open-ended valid_time)
        # Consistent with TemporalService.get_all
        stmt = (
            select(self.entity_class)
            .where(
                getattr(
                    self.entity_class,
                    self._root_field_name(),
                )
                == self.root_id,
                func.upper(cast(Any, self.entity_class).valid_time).is_(None),
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .order_by(cast(Any, self.entity_class).valid_time.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
