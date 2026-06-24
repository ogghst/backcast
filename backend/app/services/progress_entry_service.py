"""Progress Entry Service - versionable progress tracking management.

Progress entries track work completion percentage for work packages.
They are versionable (NOT branchable) - progress is global facts.
"""

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
from app.models.domain.work_package import WorkPackage


class ProgressEntryService(TemporalService[ProgressEntry]):  # type: ignore[type-var,unused-ignore]
    """Service for Progress Entry management (versionable, not branchable).

    Progress entries track work completion percentage for work packages.
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
            actor_id: The user creating the progress entry
            root_id: Optional root ID for the entry
            control_date: Optional control date for valid_time (defaults to now)
            progress_in: The progress entry data (including optional control_date)
            **fields: Alternative kwargs for building progress entry
        """
        if progress_in is None:
            progress_in = fields.pop("progress_in", None)

        if actor_id is None:
            actor_id = fields.pop("actor_id", None)
            if actor_id is None:
                raise ValueError("actor_id is required")

        if control_date is None and progress_in:
            control_date = getattr(progress_in, "control_date", None)
        if progress_in is None:
            if not fields:
                raise ValueError("Either progress_in or fields must be provided")
            progress_data = fields.copy()
            work_package_id = fields.get("work_package_id")
            if not work_package_id:
                raise ValueError("work_package_id is required")
        else:
            progress_data = progress_in.model_dump(exclude_unset=True)
            work_package_id = progress_in.work_package_id

        if root_id is None:
            root_id = progress_data.get("progress_entry_id") or uuid4()

        progress_data["progress_entry_id"] = root_id

        progress_percentage = progress_data.get("progress_percentage", 0)
        if progress_percentage < 0 or progress_percentage > 100:
            raise ValueError("Progress percentage must be between 0 and 100")

        if control_date is None:
            control_date = datetime.now(tz=UTC)

        progress_data.pop("control_date", None)

        # Validate Work Package existence (Application-level Integrity)
        wp_exists = await self.session.execute(
            select(WorkPackage.id)
            .where(
                WorkPackage.work_package_id == work_package_id,
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
            .limit(1)
        )
        if not wp_exists.scalar_one_or_none():
            raise ValueError(f"Work Package {work_package_id} not found")

        cmd = CreateVersionCommand(
            entity_class=ProgressEntry,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **progress_data,
        )
        return await cmd.execute(self.session)

    async def get_by_id(self, progress_entry_id: UUID) -> ProgressEntry | None:
        """Get current progress entry by root ID with creator name."""
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )

        stmt = (
            select(
                ProgressEntry,
                creator_subq.c.full_name.label("created_by_name"),
            )
            .outerjoin(
                creator_subq,
                ProgressEntry.created_by == creator_subq.c.user_id,
            )
            .where(
                ProgressEntry.progress_entry_id == progress_entry_id,
                ProgressEntry.deleted_at.is_(None),
            )
            .order_by(ProgressEntry.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        entity = row[0]
        entity.created_by_name = row[1]
        return entity

    async def get_latest_progress(
        self, work_package_id: UUID, as_of: datetime | None = None
    ) -> ProgressEntry | None:
        """Get the latest progress entry for a work package.

        Args:
            work_package_id: The work package to get progress for
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Latest ProgressEntry for the work package, or None if no progress reported
        """
        stmt = select(ProgressEntry).where(
            ProgressEntry.work_package_id == work_package_id
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(
                func.upper(ProgressEntry.valid_time).is_(None),
                ProgressEntry.deleted_at.is_(None),
            )

        stmt = stmt.order_by(func.lower(ProgressEntry.valid_time).desc()).limit(1)

        # Add creator-name join for the single returned row.
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )
        fetch_stmt = stmt.with_only_columns(
            ProgressEntry,
            creator_subq.c.full_name.label("created_by_name"),
        ).outerjoin(
            creator_subq,
            ProgressEntry.created_by == creator_subq.c.user_id,
        )

        result = await self.session.execute(fetch_stmt)
        row = result.first()
        if row is None:
            return None
        entity = row[0]
        entity.created_by_name = row[1]
        return entity

    async def get_progress_history(
        self,
        work_package_id: UUID | None = None,
        wbs_element_id: UUID | None = None,
        project_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
        as_of: datetime | None = None,
    ) -> tuple[list[ProgressEntry], int]:
        """Get progress entries with optional scope filtering.

        At least one filter should be provided to scope the query.
        Filters are mutually exclusive priority: work_package_id > wbs_element_id > project_id.

        Args:
            work_package_id: Filter by specific work package (direct filter)
            wbs_element_id: Filter by WBS Element (joins through work_package -> control_account)
            project_id: Filter by project (joins through work_package -> control_account -> wbs_element -> project)
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Tuple of (progress entries list, total count)
        """
        from app.models.domain.control_account import ControlAccount
        from app.models.domain.wbs_element import WBSElement

        stmt = select(ProgressEntry)

        if work_package_id is not None:
            stmt = stmt.where(
                ProgressEntry.work_package_id == work_package_id,
            )
        elif wbs_element_id is not None:
            wp_subq = (
                select(WorkPackage.work_package_id)
                .join(
                    ControlAccount,
                    WorkPackage.control_account_id == ControlAccount.control_account_id,
                )
                .where(
                    ControlAccount.wbs_element_id == wbs_element_id,
                    cast(Any, WorkPackage).deleted_at.is_(None),
                    cast(Any, ControlAccount).deleted_at.is_(None),
                )
                .correlate(ProgressEntry)
            )
            stmt = stmt.where(
                ProgressEntry.work_package_id.in_(wp_subq),
            )
        elif project_id is not None:
            wp_subq = (
                select(WorkPackage.work_package_id)
                .join(
                    ControlAccount,
                    WorkPackage.control_account_id == ControlAccount.control_account_id,
                )
                .join(
                    WBSElement,
                    ControlAccount.wbs_element_id == WBSElement.wbs_element_id,
                )
                .where(
                    WBSElement.project_id == project_id,
                    cast(Any, WorkPackage).deleted_at.is_(None),
                    cast(Any, ControlAccount).deleted_at.is_(None),
                    cast(Any, WBSElement).deleted_at.is_(None),
                )
                .correlate(ProgressEntry)
            )
            stmt = stmt.where(
                ProgressEntry.work_package_id.in_(wp_subq),
            )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(ProgressEntry.deleted_at.is_(None))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(func.lower(ProgressEntry.valid_time).desc())
        stmt = stmt.offset(skip).limit(limit)

        # Build a separate fetch statement with creator-name outerjoin so the
        # count above is unaffected and created_by_name is populated per row.
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )
        fetch_stmt = stmt.with_only_columns(
            ProgressEntry,
            creator_subq.c.full_name.label("created_by_name"),
        ).outerjoin(
            creator_subq,
            ProgressEntry.created_by == creator_subq.c.user_id,
        )

        result = await self.session.execute(fetch_stmt)
        items: list[ProgressEntry] = []
        for row in result.all():
            entity = row[0]
            entity.created_by_name = row[1]
            items.append(entity)
        return items, total

    async def get_progress_history_batch(
        self,
        work_package_ids: list[UUID],
        as_of: datetime | None = None,
    ) -> dict[UUID, list[ProgressEntry]]:
        """Get progress history for multiple work packages in a single query.

        Args:
            work_package_ids: List of work package UUIDs to fetch history for
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Dictionary mapping work_package_id to list of ProgressEntry records,
            ordered by valid_time descending (most recent first)
        """
        if not work_package_ids:
            return {}

        stmt = select(ProgressEntry).where(
            ProgressEntry.work_package_id.in_(work_package_ids),
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(ProgressEntry.deleted_at.is_(None))

        stmt = stmt.order_by(
            ProgressEntry.work_package_id,
            func.lower(ProgressEntry.valid_time).desc(),
        )

        result = await self.session.execute(stmt)

        grouped: dict[UUID, list[ProgressEntry]] = {}
        for entry in result.scalars().all():
            grouped.setdefault(entry.work_package_id, []).append(entry)

        return grouped

    async def get_progress_entry_as_of(
        self,
        progress_entry_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> ProgressEntry | None:
        """Get progress entry as it was at specific timestamp.

        Args:
            progress_entry_id: The unique identifier of the progress entry
            as_of: Timestamp to query (historical state based on valid_time)
            branch: Branch name (not applicable for non-branchable entities)
            branch_mode: Resolution mode (not applicable, kept for interface consistency)

        Returns:
            ProgressEntry if found at the specified timestamp, None otherwise
        """
        stmt = select(ProgressEntry).where(
            ProgressEntry.progress_entry_id == progress_entry_id,
        )
        stmt = self._apply_bitemporal_filter(stmt, as_of)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_progress_for_work_packages(
        self,
        work_package_ids: list[UUID],
        as_of: datetime | None = None,
    ) -> dict[UUID, ProgressEntry]:
        """Get latest progress entry for multiple work packages efficiently.

        Args:
            work_package_ids: List of work package UUIDs
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Dictionary mapping work_package_id to latest ProgressEntry
        """
        if not work_package_ids:
            return {}

        stmt = (
            select(ProgressEntry)
            .distinct(ProgressEntry.work_package_id)
            .where(ProgressEntry.work_package_id.in_(work_package_ids))
            .order_by(
                ProgressEntry.work_package_id,
                func.lower(ProgressEntry.valid_time).desc(),
            )
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(
                func.upper(ProgressEntry.valid_time).is_(None),
                ProgressEntry.deleted_at.is_(None),
            )

        result = await self.session.execute(stmt)

        progress_entries = {}
        for entry in result.scalars().all():
            progress_entries[entry.work_package_id] = entry

        return progress_entries

    # --- Backward-compatible aliases ---

    async def get_latest_progress_for_cost_elements(
        self,
        cost_element_ids: list[UUID],
        as_of: datetime | None = None,
    ) -> dict[UUID, ProgressEntry]:
        """Backward-compatible alias for get_latest_progress_for_work_packages()."""
        return await self.get_latest_progress_for_work_packages(
            cost_element_ids, as_of=as_of
        )
