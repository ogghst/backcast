"""Quality Event Service - versionable quality event management."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.enums import BranchMode
from app.core.versioning.service import TemporalService
from app.models.domain.cost_element import CostElement
from app.models.domain.quality_event import QualityEvent
from app.models.domain.wbe import WBE
from app.models.schemas.quality_event import (
    QualityEventCreate,
    QualityEventUpdate,
)


class QualityEventService(TemporalService[QualityEvent]):  # type: ignore[type-var,unused-ignore]
    """Service for Quality Event management (versionable, not branchable).

    Quality events track rework costs and quality issues against cost elements.
    They are versionable (NOT branchable) - quality events are global facts.
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(QualityEvent, db)

    async def create_quality_event(
        self,
        event_in: QualityEventCreate,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> QualityEvent:
        """Create new quality event using CreateVersionCommand.

        Args:
            event_in: The quality event data
            actor_id: The user creating the event
            branch: Branch to check cost element against (defaults to "main").
                    Quality events are global, but CE validation needs a context.
            control_date: Optional control date for valid_time (defaults to now).
                          Use this for testing time-travel scenarios or data seeding.
        """
        # Extract control_date from schema if not provided
        if control_date is None:
            control_date = getattr(event_in, "control_date", None)

        # Dump event data and exclude control_date (not a model field)
        event_data = event_in.model_dump(
            exclude_unset=True,
            exclude={"control_date"},  # Exclude from entity fields
        )

        # Use provided quality_event_id (for seeding) or generate new one
        root_id = event_in.quality_event_id or uuid4()
        event_data["quality_event_id"] = root_id

        # Default event_date to current datetime (control date) if not provided
        if "event_date" not in event_data or event_data["event_date"] is None:
            event_data["event_date"] = datetime.now(tz=UTC)

        # CRITICAL: Use control_date for valid_time (defaults to now for production)
        # event_date is a business field and should NOT affect valid_time
        # This ensures time-travel queries work correctly with as_of parameter
        actual_control_date = control_date

        # Validate Cost Element existence (Application-level Integrity)
        ce_exists = await self.session.execute(
            select(CostElement.id)
            .where(
                CostElement.cost_element_id == event_in.cost_element_id,
                CostElement.branch == branch,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .limit(1)
        )
        if not ce_exists.scalar_one_or_none():
            # Fallback to main branch
            ce_exists_main = await self.session.execute(
                select(CostElement.id)
                .where(
                    CostElement.cost_element_id == event_in.cost_element_id,
                    CostElement.branch == "main",
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
                .limit(1)
            )
            if not ce_exists_main.scalar_one_or_none():
                raise ValueError(
                    f"Cost Element {event_in.cost_element_id} not found on branch {branch} or main"
                )

        # Create the quality event
        cmd = CreateVersionCommand(
            entity_class=QualityEvent,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=actual_control_date,
            **event_data,
        )
        return await cmd.execute(self.session)

    async def update_quality_event(
        self,
        quality_event_id: UUID,
        event_in: QualityEventUpdate,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> QualityEvent:
        """Update quality event using UpdateVersionCommand.

        Args:
            quality_event_id: The quality event to update
            event_in: The update data
            actor_id: The user making the update
            control_date: Optional control date for valid_time (defaults to now)
        """
        # Extract control_date from schema if not provided
        if control_date is None:
            control_date = getattr(event_in, "control_date", None)

        # Dump update data and exclude control_date (not a model field)
        update_data = event_in.model_dump(
            exclude_unset=True,
            exclude={"control_date"},  # Exclude from entity fields
        )

        # Custom command class to handle multi-word entity name
        class QualityEventUpdateCommand(UpdateVersionCommand[QualityEvent]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "quality_event_id"

        cmd = QualityEventUpdateCommand(
            entity_class=QualityEvent,  # type: ignore[type-var,unused-ignore]
            root_id=quality_event_id,
            actor_id=actor_id,
            control_date=control_date,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def soft_delete(
        self,
        quality_event_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        """Soft delete quality event using SoftDeleteCommand."""

        class QualityEventSoftDeleteCommand(SoftDeleteCommand[QualityEvent]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "quality_event_id"

        cmd = QualityEventSoftDeleteCommand(
            entity_class=QualityEvent,  # type: ignore[type-var,unused-ignore]
            root_id=quality_event_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        await cmd.execute(self.session)

    async def get_by_id(self, quality_event_id: UUID) -> QualityEvent | None:
        """Get current quality event by root ID."""
        stmt = (
            select(QualityEvent)
            .where(
                QualityEvent.quality_event_id == quality_event_id,
                func.upper(QualityEvent.valid_time).is_(None),
                QualityEvent.deleted_at.is_(None),
            )
            .order_by(QualityEvent.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_quality_events(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100,
        as_of: datetime | None = None,
        wbe_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> tuple[list[QualityEvent], int]:
        """Get quality events with filtering, pagination, and time-travel support.

        Args:
            filters: Optional filters dict (e.g., {"cost_element_id": UUID, "event_type": str})
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            as_of: Optional timestamp for time-travel query (Valid Time Travel semantics)
            wbe_id: Optional WBE root ID to filter by (joins through CostElement)
            project_id: Optional Project root ID to filter by (joins through CostElement -> WBE)

        Returns:
            Tuple of (list of quality events, total count)
        """
        # Build base query
        stmt = select(QualityEvent).where(QualityEvent.cost_element_id.isnot(None))

        # Apply bitemporal filter for time-travel support
        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(QualityEvent.valid_time).is_(None))
            stmt = stmt.where(QualityEvent.deleted_at.is_(None))

        # Apply filters
        if filters:
            if "cost_element_id" in filters:
                stmt = stmt.where(
                    QualityEvent.cost_element_id == filters["cost_element_id"]
                )
            if "event_type" in filters:
                stmt = stmt.where(QualityEvent.event_type == filters["event_type"])
            if "severity" in filters:
                stmt = stmt.where(QualityEvent.severity == filters["severity"])

        # Join through CostElement to filter by WBE
        if wbe_id is not None:
            ce_subq = (
                select(CostElement.cost_element_id)
                .where(
                    CostElement.wbe_id == wbe_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
                .correlate(QualityEvent)
            )
            stmt = stmt.where(QualityEvent.cost_element_id.in_(ce_subq))

        # Join through CostElement -> WBE to filter by Project
        if project_id is not None:
            wbe_subq = (
                select(CostElement.cost_element_id)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                )
                .correlate(QualityEvent)
            )
            stmt = stmt.where(QualityEvent.cost_element_id.in_(wbe_subq))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply default sorting and pagination
        stmt = stmt.order_by(QualityEvent.event_date.desc())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_quality_event_as_of(
        self,
        quality_event_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> QualityEvent | None:
        """Get quality event as it was at specific timestamp.

        Provides Business Time Travel semantics (valid_time only) for quality events.
        Uses standardized bitemporal filter for temporal queries.

        Args:
            quality_event_id: The unique identifier of the quality event
            as_of: Timestamp to query (historical state based on valid_time)
            branch: Branch name to query (always "main" for non-branchable entities)
            branch_mode: Resolution mode for branches (not applicable, kept for interface consistency)

        Returns:
            QualityEvent if found at the specified timestamp, None otherwise
        """
        # Build base query
        stmt = select(QualityEvent).where(
            QualityEvent.quality_event_id == quality_event_id,
        )

        # Apply standardized bitemporal filter (Valid Time Travel semantics)
        stmt = self._apply_bitemporal_filter(stmt, as_of)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_total_for_cost_element(
        self, cost_element_id: UUID, as_of: datetime | None = None
    ) -> Any:  # Return Decimal for sum
        """Calculate total quality event costs for a cost element (time-travel aware).

        Args:
            cost_element_id: The cost element to sum quality costs for
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Sum of all quality event cost_impact for the cost element

        Example:
            >>> # Get current total
            >>> total = await service.get_total_for_cost_element(cost_element_id)
            >>>
            >>> # Get total as of specific date
            >>> from datetime import datetime
            >>> as_of = datetime(2026, 1, 1, 12, 0, 0)
            >>> historical_total = await service.get_total_for_cost_element(
            ...     cost_element_id, as_of=as_of
            ... )
        """
        # Build query for time-travel support
        stmt = select(func.sum(QualityEvent.cost_impact)).where(
            QualityEvent.cost_element_id == cost_element_id,
        )

        # Apply bitemporal filter
        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(QualityEvent.valid_time).is_(None))
            stmt = stmt.where(QualityEvent.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_quality_events_by_period(
        self,
        cost_element_id: UUID,
        period: str,  # "daily", "weekly", "monthly"
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get quality event aggregations by time period.

        Args:
            cost_element_id: The cost element to aggregate quality events for
            period: Period type ("daily", "weekly", "monthly")
            start_date: Start date for aggregation
            end_date: End date for aggregation (defaults to now)
            as_of: Optional timestamp for time-travel query

        Returns:
            List of dicts with period_start and total_cost_impact

        Example:
            >>> events = await service.get_quality_events_by_period(
            ...     cost_element_id,
            ...     period="weekly",
            ...     start_date=datetime(2026, 1, 1),
            ...     end_date=datetime(2026, 1, 31)
            ... )
            >>> # Returns: [
            ... #   {"period_start": "2026-01-01", "total_cost_impact": 1500.00},
            ... #   {"period_start": "2026-01-08", "total_cost_impact": 2000.00},
            ... #   ...
            ... # ]
        """
        if end_date is None:
            end_date = datetime.now(tz=UTC)

        # Map API period names to PostgreSQL date_trunc units
        # API uses: "daily", "weekly", "monthly"
        # PostgreSQL expects: "day", "week", "month"
        period_mapping = {
            "daily": "day",
            "weekly": "week",
            "monthly": "month",
        }
        pg_period = period_mapping.get(period, period)

        # Build base query with time-travel support
        stmt = select(
            func.date_trunc(pg_period, QualityEvent.event_date).label("period_start"),
            func.sum(QualityEvent.cost_impact).label("total_cost_impact"),
        ).where(
            QualityEvent.cost_element_id == cost_element_id,
            QualityEvent.event_date >= start_date,
            QualityEvent.event_date <= end_date,
        )

        # Apply bitemporal filter
        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(QualityEvent.valid_time).is_(None))
            stmt = stmt.where(QualityEvent.deleted_at.is_(None))

        # Group by period and order
        stmt = stmt.group_by("period_start").order_by("period_start")

        result = await self.session.execute(stmt)
        return [
            {
                "period_start": row.period_start.isoformat(),
                "total_cost_impact": float(row.total_cost_impact),
            }
            for row in result.all()
        ]
