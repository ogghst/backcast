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

from sqlalchemy import func, select, text
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
        # CRITICAL FIX: Capture the current lower bounds in Python before updating
        # SQLAlchemy's func.lower() doesn't work correctly with PostgreSQL ranges in UPDATE
        from sqlalchemy import text

        version_any = cast(Any, version)
        valid_lower = version_any.valid_time.lower
        tx_lower = version_any.transaction_time.lower

        # CRITICAL FIX: Generate closing timestamps in Python to avoid identical timestamps
        # When calling clock_timestamp() twice in SQL, PostgreSQL returns the same microsecond
        # value if both calls execute within the same microsecond, creating empty ranges [t, t)
        closing_timestamp = datetime.now(UTC)

        # Determine closing times
        # If control_date (close_at_valid_time) is provided, use it for valid_time.
        # Otherwise use the generated timestamp for both.
        if close_at_valid_time:
            valid_upper = close_at_valid_time
        else:
            valid_upper = closing_timestamp

        # Always use the same timestamp for transaction_time upper bound
        tx_upper = closing_timestamp

        # Use raw SQL to update the ranges with known lower bounds
        tablename = cast(str, self.entity_class.__tablename__)
        stmt = text(
            f"""
            UPDATE {tablename}
            SET
                valid_time = tstzrange(:valid_lower, :valid_upper, '[)'),
                transaction_time = tstzrange(:tx_lower, :tx_upper, '[)')
            WHERE id = :version_id
            """
        )
        await session.execute(stmt, {
            "valid_lower": valid_lower,
            "valid_upper": valid_upper,
            "tx_lower": tx_lower,
            "tx_upper": tx_upper,
            "version_id": version.id
        })

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
        # Use getattr to safely access __tablename__ from the protocol
        tablename = cast(str, self.entity_class.__tablename__)
        stmt = text(
            f"""
            UPDATE {tablename}
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

        # VALIDATION: Ensure control_date is not before current version's valid_time lower bound
        # This prevents PostgreSQL range constraint violations
        # NOTE: control_date can be equal to current_lower (Time Machine mode: updating at same timestamp)
        if self.control_date:
            current_lower = cast(Any, current).valid_time.lower

            # Validate control_date is >= lower bound (allowing equal for Time Machine updates)
            if self.control_date < current_lower:
                raise ValueError(
                    f"control_date ({self.control_date.isoformat()}) must be on or after "
                    f"the current version's valid_time lower bound ({current_lower.isoformat()}). "
                    f"This ensures bitemporal range constraints are satisfied."
                )

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
        # Use getattr to safely access __tablename__ from the protocol
        tablename = cast(str, self.entity_class.__tablename__)
        stmt_fix_time = text(
            f"""
            UPDATE {tablename}
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
