"""Progress Entry Service - versionable progress tracking management."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.enums import BranchMode
from app.core.versioning.service import TemporalService
from app.models.domain.progress_entry import ProgressEntry
from app.models.schemas.progress_entry import (
    ProgressEntryCreate,
    ProgressEntryUpdate,
)


class ProgressEntryService(TemporalService[ProgressEntry]):  # type: ignore[type-var,unused-ignore]
    """Service for Progress Entry management (versionable, not branchable).

    Progress entries track work completion percentage for cost elements.
    They are versionable (NOT branchable) - progress is global facts.
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(ProgressEntry, db)

    async def create(  # type: ignore[override]
        self, progress_in: ProgressEntryCreate, actor_id: UUID, control_date: datetime | None = None
    ) -> ProgressEntry:
        """Create new progress entry using CreateVersionCommand.

        Args:
            progress_in: The progress entry data
            actor_id: The user creating the progress entry
            control_date: Optional control date for valid_time (defaults to now).
                          Use this for testing time-travel scenarios or data seeding.
        """
        progress_data = progress_in.model_dump(exclude_unset=True)

        # Use provided progress_entry_id (for seeding) or generate new one
        root_id = progress_in.progress_entry_id or uuid4()
        progress_data["progress_entry_id"] = root_id

        # Validate progress_percentage is 0-100 (already validated by Pydantic schema)
        # But we add an additional check here for safety
        progress_percentage = progress_data.get("progress_percentage", 0)
        if progress_percentage < 0 or progress_percentage > 100:
            raise ValueError("Progress percentage must be between 0 and 100")

        # CRITICAL: Use control_date for valid_time (defaults to now for production)
        # reported_date is a business field and should NOT affect valid_time
        # This ensures time-travel queries work correctly with as_of parameter
        actual_control_date = control_date if control_date is not None else datetime.now()

        cmd = CreateVersionCommand(
            entity_class=ProgressEntry,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=actual_control_date,
            **progress_data,
        )
        return await cmd.execute(self.session)

    async def update(  # type: ignore[override]
        self,
        progress_entry_id: UUID,
        progress_in: ProgressEntryUpdate,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> ProgressEntry:
        """Update progress entry using UpdateVersionCommand.

        Args:
            progress_entry_id: The progress entry to update
            progress_in: The update data
            actor_id: The user making the update
            control_date: Optional control date for valid_time (defaults to now)
        """
        update_data = progress_in.model_dump(exclude_unset=True)

        # Validate progress_percentage if provided
        if "progress_percentage" in update_data:
            progress_percentage = update_data["progress_percentage"]
            if progress_percentage is not None and (progress_percentage < 0 or progress_percentage > 100):
                raise ValueError("Progress percentage must be between 0 and 100")

        # Custom command class to handle multi-word entity name
        class ProgressEntryUpdateCommand(UpdateVersionCommand[ProgressEntry]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "progress_entry_id"

        cmd = ProgressEntryUpdateCommand(
            entity_class=ProgressEntry,  # type: ignore[type-var,unused-ignore]
            root_id=progress_entry_id,
            actor_id=actor_id,
            control_date=control_date,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def soft_delete(
        self,
        progress_entry_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        """Soft delete progress entry using SoftDeleteCommand."""

        class ProgressEntrySoftDeleteCommand(SoftDeleteCommand[ProgressEntry]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "progress_entry_id"

        cmd = ProgressEntrySoftDeleteCommand(
            entity_class=ProgressEntry,  # type: ignore[type-var,unused-ignore]
            root_id=progress_entry_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        await cmd.execute(self.session)

    async def get_by_id(self, progress_entry_id: UUID) -> ProgressEntry | None:
        """Get current progress entry by root ID."""
        stmt = (
            select(ProgressEntry)
            .where(
                ProgressEntry.progress_entry_id == progress_entry_id,
                ProgressEntry.deleted_at.is_(None),
            )
            .order_by(ProgressEntry.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_progress(
        self, cost_element_id: UUID, as_of: datetime | None = None
    ) -> ProgressEntry | None:
        """Get the latest progress entry for a cost element.

        Args:
            cost_element_id: The cost element to get progress for
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Latest ProgressEntry for the cost element, or None if no progress reported
        """
        from sqlalchemy import func

        # Build base query
        stmt = select(ProgressEntry).where(
            ProgressEntry.cost_element_id == cost_element_id
        )

        # Use standardized bitemporal filter for time-travel support
        if as_of is not None:
            # Apply standardized filter (Valid Time Travel semantics)
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            # Current versions only (open-ended valid_time and not deleted)
            stmt = stmt.where(
                func.upper(ProgressEntry.valid_time).is_(None),
                ProgressEntry.deleted_at.is_(None),
            )

        # Order by reported_date descending (most recent first)
        stmt = stmt.order_by(ProgressEntry.reported_date.desc()).limit(1)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_progress_history(
        self, cost_element_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[ProgressEntry], int]:
        """Get all progress entries for a cost element (for charts).

        Args:
            cost_element_id: The cost element to get progress history for
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            Tuple of (progress entries list, total count)
        """
        from sqlalchemy import func

        # Build query for all progress entries (not deleted)
        stmt = select(ProgressEntry).where(
            ProgressEntry.cost_element_id == cost_element_id,
            ProgressEntry.deleted_at.is_(None),
        )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply sorting by reported_date descending and pagination
        stmt = stmt.order_by(ProgressEntry.reported_date.desc())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_progress_entry_as_of(
        self,
        progress_entry_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> ProgressEntry | None:
        """Get progress entry as it was at specific timestamp.

        Provides Business Time Travel semantics (valid_time only) for progress entries.
        Uses standardized bitemporal filter for temporal queries.

        Args:
            progress_entry_id: The unique identifier of the progress entry
            as_of: Timestamp to query (historical state based on valid_time)
            branch: Branch name to query (always "main" for non-branchable entities)
            branch_mode: Resolution mode for branches (not applicable, kept for interface consistency)

        Returns:
            ProgressEntry if found at the specified timestamp, None otherwise
        """
        # Build base query
        stmt = select(ProgressEntry).where(
            ProgressEntry.progress_entry_id == progress_entry_id,
        )

        # Apply standardized bitemporal filter (Valid Time Travel semantics)
        stmt = self._apply_bitemporal_filter(stmt, as_of)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
