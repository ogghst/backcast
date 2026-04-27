"""Progress Entry Service - versionable progress tracking management."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
)
from app.core.versioning.enums import BranchMode
from app.core.versioning.service import TemporalService
from app.models.domain.progress_entry import ProgressEntry


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

    async def create(
        self,
        actor_id: UUID,
        root_id: UUID | None = None,
        control_date: datetime | None = None,
        progress_in: Any = None,
        **fields: Any,
    ) -> ProgressEntry:
        """Create new progress entry using CreateVersionCommand.

        Args:
            progress_in: The progress entry data (including optional control_date)
            actor_id: The user creating the progress entry
            control_date: Optional control date for valid_time (defaults to now)
        """
        # Support kwargs override for progress_in
        if progress_in is None:
            progress_in = fields.pop("progress_in", None)

        if actor_id is None:
            actor_id = fields.pop("actor_id", None)
            if actor_id is None:
                raise ValueError("actor_id is required")

        # Extract control_date from schema if not provided
        if control_date is None and progress_in:
            control_date = getattr(progress_in, "control_date", None)
        if progress_in is None:
            # Try to build from fields if possible
            if not fields:
                raise ValueError("Either progress_in or fields must be provided")
            progress_data = fields.copy()
            cost_element_id = fields.get("cost_element_id")
            if not cost_element_id:
                raise ValueError("cost_element_id is required")
        else:
            progress_data = progress_in.model_dump(exclude_unset=True)
            cost_element_id = progress_in.cost_element_id

        # Use root_id if provided, then check progress_data, then generate new one
        if root_id is None:
            root_id = progress_data.get("progress_entry_id") or uuid4()

        progress_data["progress_entry_id"] = root_id

        # Validate progress_percentage is 0-100 (already validated by Pydantic schema)
        # But we add an additional check here for safety
        progress_percentage = progress_data.get("progress_percentage", 0)
        if progress_percentage < 0 or progress_percentage > 100:
            raise ValueError("Progress percentage must be between 0 and 100")

        # If control_date is still None, default to now
        if control_date is None:
            control_date = datetime.now(tz=UTC)

        # Remove control_date from progress_data if present to avoid duplicate kwarg error
        progress_data.pop("control_date", None)

        # 1. Validate Cost Element existence (Application-level Integrity)
        from app.models.domain.cost_element import CostElement

        ce_exists = await self.session.execute(
            select(CostElement.id)
            .where(
                CostElement.cost_element_id == cost_element_id,
                # Progress entries are global, check main branch
                CostElement.branch == "main",
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .limit(1)
        )
        if not ce_exists.scalar_one_or_none():
            # Fallback: check any branch? No, progress is usually reported against main.
            # Actually, if we are in a branch, we might report progress on a branched CE.
            # But ProgressEntry is NOT branchable. This is a slight mismatch in architecture
            # but consistent with "progress is a fact".
            # We check main first, then any? Better to check if ANY version exists.
            ce_any_exists = await self.session.execute(
                select(CostElement.id)
                .where(
                    CostElement.cost_element_id == cost_element_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
                .limit(1)
            )
            if not ce_any_exists.scalar_one_or_none():
                raise ValueError(f"Cost Element {cost_element_id} not found")

        cmd = CreateVersionCommand(
            entity_class=ProgressEntry,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **progress_data,
        )
        return await cmd.execute(self.session)

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

        # Order by valid_time descending (most recent first)
        # Use lower() to get the start of the valid_time range
        stmt = stmt.order_by(func.lower(ProgressEntry.valid_time).desc()).limit(1)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_progress_history(
        self,
        cost_element_id: UUID | None = None,
        wbe_id: UUID | None = None,
        project_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
        as_of: datetime | None = None,
    ) -> tuple[list[ProgressEntry], int]:
        """Get progress entries with optional scope filtering.

        At least one filter should be provided to scope the query.
        Filters are mutually exclusive priority: cost_element_id > wbe_id > project_id.

        Args:
            cost_element_id: Filter by specific cost element (direct filter)
            wbe_id: Filter by WBE (joins through cost_element)
            project_id: Filter by project (joins through cost_element -> wbe)
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Tuple of (progress entries list, total count)
        """
        from sqlalchemy import func

        from app.models.domain.cost_element import CostElement
        from app.models.domain.wbe import WBE

        # Build query for progress entries
        stmt = select(ProgressEntry)

        # Apply scope filters (priority: cost_element_id > wbe_id > project_id)
        if cost_element_id is not None:
            stmt = stmt.where(
                ProgressEntry.cost_element_id == cost_element_id,
            )
        elif wbe_id is not None:
            ce_subq = (
                select(CostElement.cost_element_id)
                .where(
                    CostElement.wbe_id == wbe_id,
                    CostElement.deleted_at.is_(None),
                )
                .correlate(ProgressEntry)
            )
            stmt = stmt.where(
                ProgressEntry.cost_element_id.in_(ce_subq),
            )
        elif project_id is not None:
            ce_subq = (
                select(CostElement.cost_element_id)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.deleted_at.is_(None),
                    WBE.deleted_at.is_(None),
                )
                .correlate(ProgressEntry)
            )
            stmt = stmt.where(
                ProgressEntry.cost_element_id.in_(ce_subq),
            )

        # Apply temporal filter based on as_of parameter
        if as_of is not None:
            # Time-travel query: apply standardized bitemporal filter
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            # Current versions only (not deleted)
            stmt = stmt.where(ProgressEntry.deleted_at.is_(None))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply sorting by valid_time descending (most recent first) and pagination
        stmt = stmt.order_by(func.lower(ProgressEntry.valid_time).desc())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_progress_history_batch(
        self,
        cost_element_ids: list[UUID],
        as_of: datetime | None = None,
    ) -> dict[UUID, list[ProgressEntry]]:
        """Get progress history for multiple cost elements in a single query.

        Eliminates N+1 queries when building EVM timeseries for multiple
        cost elements by fetching all progress entries in one round-trip.

        Args:
            cost_element_ids: List of cost element UUIDs to fetch history for
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Dictionary mapping cost_element_id to list of ProgressEntry records,
            ordered by valid_time descending (most recent first)
        """
        if not cost_element_ids:
            return {}

        stmt = select(ProgressEntry).where(
            ProgressEntry.cost_element_id.in_(cost_element_ids),
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(ProgressEntry.deleted_at.is_(None))

        stmt = stmt.order_by(
            ProgressEntry.cost_element_id,
            func.lower(ProgressEntry.valid_time).desc(),
        )

        result = await self.session.execute(stmt)

        grouped: dict[UUID, list[ProgressEntry]] = {}
        for entry in result.scalars().all():
            grouped.setdefault(entry.cost_element_id, []).append(entry)

        return grouped

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

    async def get_latest_progress_for_cost_elements(
        self,
        cost_element_ids: list[UUID],
        as_of: datetime | None = None,
    ) -> dict[UUID, ProgressEntry]:
        """Get latest progress entry for multiple cost elements efficiently.

        Args:
            cost_element_ids: List of cost element UUIDs
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Dictionary mapping cost_element_id to latest ProgressEntry
        """
        if not cost_element_ids:
            return {}

        from sqlalchemy import func

        stmt = (
            select(ProgressEntry)
            .distinct(ProgressEntry.cost_element_id)
            .where(ProgressEntry.cost_element_id.in_(cost_element_ids))
            .order_by(
                ProgressEntry.cost_element_id,
                func.lower(ProgressEntry.valid_time).desc(),
            )
        )

        # Apply time-travel filter
        if as_of is not None:
            # Time-travel query: apply standardized bitemporal filter
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            # Current versions only (open-ended valid_time and not deleted)
            stmt = stmt.where(
                func.upper(ProgressEntry.valid_time).is_(None),
                ProgressEntry.deleted_at.is_(None),
            )

        result = await self.session.execute(stmt)

        progress_entries = {}
        for entry in result.scalars().all():
            progress_entries[entry.cost_element_id] = entry

        return progress_entries
