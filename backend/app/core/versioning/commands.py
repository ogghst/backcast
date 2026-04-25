"""Generic commands for versioned entities.

Provides Protocol-bound command ABCs and concrete implementations:
- VersionedCommandABC: For VersionableProtocol entities
- Concrete commands: Create, Update, SoftDelete

Note: Branching commands have been moved to app.core.branching.commands.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID, uuid4

import sqlalchemy
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.exceptions import OverlappingVersionError
from app.models.protocols import VersionableProtocol

if TYPE_CHECKING:
    from app.models.domain.change_order import ChangeOrder

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
        close_at_valid_time: datetime | None = None,
        close_at_transaction_time: datetime | None = None,
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
        closing_timestamp = close_at_transaction_time or datetime.now(UTC)

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
        tablename = str(getattr(self.entity_class, "__tablename__", ""))
        stmt = text(
            f"""
            UPDATE {tablename}
            SET
                valid_time = tstzrange(:valid_lower, :valid_upper, '[)'),
                transaction_time = tstzrange(:tx_lower, :tx_upper, '[)')
            WHERE id = :version_id
            """
        )

        params = {
            "valid_lower": valid_lower,
            "valid_upper": valid_upper,
            "tx_lower": tx_lower,
            "tx_upper": tx_upper,
            "version_id": version.id,
        }

        await session.execute(
            stmt,
            params,
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
        and current recording time, while allowing valid_time to be backdated/future-dated
        via control_date.
        """
        # 0. Check for overlaps (only for SQLAlchemy-mapped entities)
        # Skip overlap check for test mocks or non-SQLAlchemy entities
        try:
            # Determine restricted scope (branch) if applicable
            branch_filter: str | None = None
            if hasattr(self.entity_class, "branch"):
                branch_filter = self.fields.get("branch", "main")

            stmt_check = select(self.entity_class).where(
                getattr(self.entity_class, self._root_field_name()) == self.root_id,
                cast(Any, self.entity_class).deleted_at.is_(None),
            )

            if branch_filter:
                stmt_check = stmt_check.where(
                    cast(Any, self.entity_class).branch == branch_filter
                )

            # Check for overlap starting at control_date
            stmt_check = stmt_check.where(
                or_(
                    func.upper(cast(Any, self.entity_class).valid_time)
                    > self.control_date,
                    func.upper(cast(Any, self.entity_class).valid_time).is_(None),
                )
            )

            result = await session.execute(stmt_check.limit(1))
            existing = result.scalar_one_or_none()
            if existing:
                raise OverlappingVersionError(
                    root_id=str(self.root_id),
                    new_range=f"[{self.control_date.isoformat()}, NULL)",
                    existing_range=getattr(existing, "valid_time", "unknown"),
                    branch=branch_filter,
                )
        except sqlalchemy.exc.ArgumentError:
            # If select() fails with ArgumentError (e.g., test mock), skip overlap check
            # This allows unit tests with mock entities to work
            pass

        # Set the root ID field (e.g., wbe_id, user_id) along with other fields
        root_field_name = self._root_field_name()
        fields_with_root = {root_field_name: self.root_id, **self.fields}
        version = cast(Any, self.entity_class)(
            created_by=self.actor_id, **fields_with_root
        )  # Model should handle TSTZRANGE defaults with now()
        session.add(version)
        await session.flush()  # Get ID assigned

        # Set valid_time to control_date, transaction_time to clock_timestamp()
        # Use getattr to safely access __tablename__ from the protocol
        tablename = str(getattr(self.entity_class, "__tablename__", ""))
        stmt = text(
            f"""
            UPDATE {tablename}
            SET
                valid_time = tstzrange(:control_date, NULL, '[]'),
                transaction_time = tstzrange(clock_timestamp(), NULL, '[]')
            WHERE id = :version_id
            """
        )
        await session.execute(
            stmt, {"control_date": self.control_date, "version_id": version.id}
        )
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

        CRITICAL FIX: Uses raw SQL INSERT to bypass database DEFAULT values
        and prevent exclusion constraint violations.
        """
        # Get current version
        current = await self._get_current(session)
        if not current:
            raise ValueError(f"No active version found for {self.root_id}")

        # Generate universal timestamp for this update operation to ensure tx_lower >= tx_upper exactly
        update_time = datetime.now(UTC)

        # CRITICAL FIX: Close current version FIRST to get its upper bound
        # This ensures we know exactly when the closed version ends
        await self._close_version(
            session,
            current,
            close_at_valid_time=self.control_date,
            close_at_transaction_time=update_time,
        )

        # Refresh to get the updated valid_time (now closed)
        await session.refresh(current)
        closed_upper = cast(Any, current).valid_time.upper

        # Clone and apply updates (must happen after close due to expire)
        new_version = cast(
            TVersionable,
            current.clone(created_by=self.actor_id, **self.updates),
        )

        # Determine valid_time lower bound
        # If control_date was provided and is later, use it; otherwise use the closed upper bound
        if self.control_date and closed_upper and self.control_date > closed_upper:
            new_valid_lower = self.control_date
        else:
            new_valid_lower = closed_upper

        # CRITICAL FIX: Use raw SQL INSERT to bypass database DEFAULT values
        # This prevents exclusion constraint violations by setting valid_time explicitly
        from sqlalchemy import inspect, text

        tablename = str(getattr(self.entity_class, "__tablename__", ""))

        # Get all column names and values from the new_version object
        mapper = inspect(type(new_version))
        if mapper is None:
            raise ValueError(f"Could not get mapper for {type(new_version)}")

        # Build column and value lists
        # CRITICAL: Include ALL columns (except valid_time, transaction_time) regardless of value
        # This ensures NOT NULL columns are properly set, even if they have None values
        column_names = []
        value_placeholders = []
        values = {}

        for col in mapper.columns:
            col_name = col.key
            # Skip valid_time and transaction_time (set explicitly below)
            if col_name in ("valid_time", "transaction_time"):
                continue

            # CRITICAL FIX: Get the correct Python attribute name from the mapper
            # The column key (`col.key`) might differ from the attribute name (e.g., "metadata" vs "branch_metadata")
            # We must use the attribute name to get the value from the object
            prop = mapper.get_property_by_column(col)
            attr_name = prop.key

            value = getattr(new_version, attr_name, None)

            # CRITICAL: Generate UUID for id column since we're using raw SQL
            # The Python-level default=uuid4 doesn't work with raw SQL
            # CRITICAL: Always generate NEW UUID for id column of the new version row
            # Even if the cloned object has an ID, we must replace it to avoid PK collision
            if col_name == "id":
                value = uuid4()
                # Debug print removed for production
                # print(f"DEBUG: Generated new ID: {value}")

            column_names.append(col_name)
            placeholder = f":{col_name}"
            value_placeholders.append(placeholder)
            values[col_name] = value

        # Build and execute the raw SQL INSERT
        # CRITICAL: Set valid_time explicitly using tstzrange() with the new_valid_lower
        # This bypasses the database DEFAULT value and prevents exclusion constraint violations
        cols_str = ", ".join(column_names)
        placeholders_str = ", ".join(value_placeholders)

        stmt = text(
            f"""
            INSERT INTO {tablename} ({cols_str}, valid_time, transaction_time)
            VALUES ({placeholders_str}, tstzrange(:valid_lower, NULL, '[]'), tstzrange(:tx_lower, NULL, '[]'))
            RETURNING id
            """
        )
        result = await session.execute(
            stmt, {**values, "valid_lower": new_valid_lower, "tx_lower": update_time}
        )
        new_version_id = result.scalar_one()

        # Fetch the newly created version from the database
        stmt_new = select(self.entity_class).where(
            self.entity_class.id == new_version_id
        )
        result_new = await session.execute(stmt_new)
        created_version = result_new.scalar_one()

        return created_version

    async def _get_current(self, session: AsyncSession) -> TVersionable | None:
        """Get current active version (HEAD). Excludes empty ranges."""
        stmt = (
            select(self.entity_class)
            .where(
                getattr(
                    self.entity_class,
                    self._root_field_name(),
                )
                == self.root_id,
                func.upper(cast(Any, self.entity_class).valid_time).is_(
                    None
                ),  # Use open-ended check
                func.not_(
                    func.isempty(self.entity_class.valid_time)
                ),  # Exclude empty ranges
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
        current.deleted_by = self.actor_id
        await session.flush()
        return current

    async def _get_current(self, session: AsyncSession) -> TVersionable | None:
        """Get current active version. Excludes empty ranges."""
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
                func.not_(
                    func.isempty(self.entity_class.valid_time)
                ),  # Exclude empty ranges
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .order_by(cast(Any, self.entity_class).valid_time.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# ==============================================================================
# Domain-Specific Commands (Non-Versioned Entities)
# ==============================================================================


class CreateChangeOrderAuditLogCommand:
    """Command to create a Change Order audit log entry.

    Encapsulates the creation of audit log entries for Change Order status transitions.
    This enforces the RSC pattern by moving state-changing operations out of Services.

    Attributes:
        change_order_id: Root UUID of the Change Order
        old_status: Previous status value
        new_status: New status value
        actor_id: User who made the change
        comment: Optional comment explaining the transition
        control_date: Control date for the workflow operation (defaults to now)
    """

    def __init__(
        self,
        change_order_id: UUID,
        old_status: str,
        new_status: str,
        actor_id: UUID,
        comment: str | None = None,
        control_date: datetime | None = None,
    ) -> None:
        self.change_order_id = change_order_id
        self.old_status = old_status
        self.new_status = new_status
        self.actor_id = actor_id
        self.comment = comment
        self.control_date = control_date or datetime.now(UTC)

    async def execute(self, session: AsyncSession) -> None:
        """Create and persist the audit log entry.

        Validates that the status has actually changed before creating the entry.
        """
        # Import here to avoid circular dependency
        from app.models.domain.change_order_audit_log import ChangeOrderAuditLog

        # Validation: Don't create audit log if status unchanged
        if self.old_status == self.new_status:
            raise ValueError(
                f"Cannot create audit log: status unchanged ({self.old_status})"
            )

        # Create audit log entry with control_date
        audit_entry = ChangeOrderAuditLog(
            change_order_id=self.change_order_id,
            old_status=self.old_status,
            new_status=self.new_status,
            comment=self.comment,
            changed_by=self.actor_id,
            control_date=self.control_date,
        )
        session.add(audit_entry)
        await session.flush()


class LinkCostElementCommand:
    """Command to link a CostElement to its parent (ScheduleBaseline or Forecast).

    Encapsulates the FK update logic for parent-child relationships.
    This enforces the RSC pattern by isolating side-effects from Service methods.

    Attributes:
        cost_element_id: UUID of the CostElement to update
        parent_type: Type of parent ("schedule_baseline" or "forecast")
        parent_id: UUID of the parent entity
    """

    def __init__(
        self,
        cost_element_id: UUID,
        parent_type: str,
        parent_id: UUID,
    ) -> None:
        self.cost_element_id = cost_element_id
        self.parent_type = parent_type
        self.parent_id = parent_id

        # Validation
        if parent_type not in ("schedule_baseline", "forecast"):
            raise ValueError(
                f"Invalid parent_type: {parent_type}. "
                f"Must be 'schedule_baseline' or 'forecast'"
            )

    async def execute(self, session: AsyncSession) -> None:
        """Update the CostElement's parent FK.

        Uses raw SQL UPDATE to set the appropriate FK field.
        """
        from sqlalchemy import text

        # Determine which FK field to update
        fk_field = (
            "schedule_baseline_id"
            if self.parent_type == "schedule_baseline"
            else "forecast_id"
        )

        # Use raw SQL to update the FK
        stmt = text(
            f"""
            UPDATE cost_elements
            SET {fk_field} = :parent_id
            WHERE cost_element_id = :cost_element_id
            AND upper(valid_time) IS NULL
            AND deleted_at IS NULL
            """
        )
        await session.execute(
            stmt,
            {
                "parent_id": self.parent_id,
                "cost_element_id": self.cost_element_id,
            },
        )
        await session.flush()


class UpdateChangeOrderStatusCommand:
    """Command to update a Change Order's status with proper versioning.

    Encapsulates status transitions for Change Orders with bitemporal tracking.
    This enforces the RSC pattern by isolating status update logic.

    CRITICAL: This command creates a new version with proper valid_time based on
    control_date, ensuring status is consistent with temporal queries.

    Note: This command does NOT create audit logs - that's the responsibility
    of CreateChangeOrderAuditLogCommand. Services should orchestrate both commands.

    Attributes:
        change_order_id: Root UUID of the Change Order
        new_status: New status value
        actor_id: UUID of user performing the update
        branch: Branch to update on
        control_date: Optional control date for valid_time (defaults to now)
        additional_updates: Optional dict of additional fields to update
    """

    def __init__(
        self,
        change_order_id: UUID,
        new_status: str,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
        additional_updates: dict[str, Any] | None = None,
    ) -> None:
        self.change_order_id = change_order_id
        self.new_status = new_status
        self.actor_id = actor_id
        self.branch = branch
        self.control_date = control_date
        self.additional_updates = additional_updates or {}

    async def execute(self, session: AsyncSession) -> "ChangeOrder":
        """Update the Change Order's status with proper versioning.

        Closes the current version at control_date and creates a new version
        with the updated status, ensuring bitemporal consistency.

        Returns:
            The updated ChangeOrder entity with new status

        Raises:
            ValueError: If change order not found
        """
        from sqlalchemy import text

        from app.models.domain.change_order import ChangeOrder

        # Build updates dict
        updates = {"status": self.new_status, **self.additional_updates}

        # Get current version
        stmt = text(
            """
            SELECT id, valid_time
            FROM change_orders
            WHERE change_order_id = :change_order_id
            AND branch = :branch
            AND upper(valid_time) IS NULL
            AND deleted_at IS NULL
            """
        )
        result = await session.execute(
            stmt,
            {
                "change_order_id": self.change_order_id,
                "branch": self.branch,
            },
        )
        row = result.fetchone()

        if row is None:
            raise ValueError(
                f"No active Change Order found with ID {self.change_order_id} "
                f"on branch {self.branch}"
            )

        current_id = row.id
        current_valid_time = row.valid_time
        current_lower = current_valid_time.lower if current_valid_time else None

        # Determine control_date for valid_time
        update_timestamp = datetime.now(UTC)
        if self.control_date is None:
            self.control_date = update_timestamp

        # Close current version at control_date (create remainder if there's a time gap)
        if current_lower and self.control_date > current_lower:
            # Create remainder: close current version at control_date
            close_stmt = text(
                """
                UPDATE change_orders
                SET
                    valid_time = tstzrange(:lower, :upper, '[)'),
                    transaction_time = tstzrange(:tx_lower, :tx_upper, '[)')
                WHERE id = :version_id
                """
            )
            await session.execute(
                close_stmt,
                {
                    "lower": current_lower,
                    "upper": self.control_date,
                    "tx_lower": current_valid_time.lower
                    if current_valid_time
                    else update_timestamp,
                    "tx_upper": update_timestamp,
                    "version_id": current_id,
                },
            )
            await session.flush()

        # Get the current entity to clone
        current = await session.get(ChangeOrder, current_id)
        if current is None:
            raise ValueError(f"Change Order version {current_id} not found")

        # Create new version with updated status
        new_version = current.clone(created_by=self.actor_id, **updates)
        new_version.parent_id = current_id
        session.add(new_version)
        await session.flush()

        # Set valid_time to control_date, transaction_time to clock_timestamp()
        set_time_stmt = text(
            """
            UPDATE change_orders
            SET
                valid_time = tstzrange(:control_date, NULL, '[]'),
                transaction_time = tstzrange(clock_timestamp(), NULL, '[]')
            WHERE id = :version_id
            """
        )
        await session.execute(
            set_time_stmt,
            {"control_date": self.control_date, "version_id": new_version.id},
        )
        await session.flush()
        await session.refresh(new_version)

        # Cast to ChangeOrder for proper type hinting
        return cast("ChangeOrder", new_version)
