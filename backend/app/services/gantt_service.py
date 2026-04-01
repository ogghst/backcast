"""GanttService for aggregating schedule data for Gantt chart visualization.

Aggregates WBE hierarchy, cost elements, and schedule baselines into a flat
list suitable for Gantt chart rendering, with branch and time-travel support.
"""

import logging
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.domain.cost_element import CostElement
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.domain.wbe import WBE
from app.models.schemas.gantt import GanttDataResponse, GanttItem

logger = logging.getLogger(__name__)


class GanttService:
    """Service for aggregating Gantt chart data across WBEs, cost elements,
    and schedule baselines."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_gantt_data(
        self,
        project_id: UUID,
        branch: str = "main",
        mode: str = "merged",
        as_of: datetime | None = None,
    ) -> GanttDataResponse:
        """Get aggregated Gantt data for a project.

        Joins WBEs, cost elements, and schedule baselines in a single query
        with branch and version filtering.

        Args:
            project_id: Project root ID
            branch: Branch name (default: "main")
            mode: Branch mode ("merged" or "isolated")
            as_of: Optional timestamp for time-travel queries

        Returns:
            GanttDataResponse with items sorted by WBE hierarchy
        """
        from datetime import UTC

        branch_mode = BranchMode.MERGE if mode == "merged" else BranchMode.STRICT
        if as_of is None:
            as_of = datetime.now(tz=UTC)

        # Build WBE subquery: current versions filtered by branch/mode
        wbe_sq = (
            select(WBE)
            .where(
                WBE.project_id == project_id,
                WBE.deleted_at.is_(None),
                func.upper(cast(Any, WBE).valid_time).is_(None),
            )
            .subquery("wbe_sq")
        )

        # Apply branch filtering
        if branch_mode == BranchMode.STRICT:
            wbe_sq = (
                select(WBE)
                .where(
                    WBE.project_id == project_id,
                    WBE.branch == branch,
                    WBE.deleted_at.is_(None),
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                )
                .subquery("wbe_sq")
            )
        else:
            # MERGE mode: prefer branch versions, fallback to main
            wpe_prioritized = (
                select(
                    WBE,
                    func.row_number()
                    .over(
                        partition_by=WBE.wbe_id,
                        order_by=(
                            case(
                                (WBE.branch == branch, 0),
                                (WBE.branch == "main", 1),
                                else_=2,
                            )
                        ),
                    )
                    .label("rn"),
                )
                .where(
                    WBE.project_id == project_id,
                    WBE.branch.in_([branch, "main"]),
                    WBE.deleted_at.is_(None),
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                )
                .subquery("wbe_prioritized")
            )
            wbe_sq = (
                select(
                    wpe_prioritized.c.id,
                    wpe_prioritized.c.wbe_id,
                    wpe_prioritized.c.project_id,
                    wpe_prioritized.c.parent_wbe_id,
                    wpe_prioritized.c.code,
                    wpe_prioritized.c.name,
                    wpe_prioritized.c.level,
                    wpe_prioritized.c.revenue_allocation,
                    wpe_prioritized.c.description,
                    wpe_prioritized.c.branch,
                    wpe_prioritized.c.valid_time,
                    wpe_prioritized.c.transaction_time,
                    wpe_prioritized.c.deleted_at,
                    wpe_prioritized.c.created_by,
                    wpe_prioritized.c.deleted_by,
                    wpe_prioritized.c.parent_id,
                    wpe_prioritized.c.merge_from_branch,
                )
                .where(wpe_prioritized.c.rn == 1)
                .subquery("wbe_sq")
            )

        # Build cost element subquery with same branch logic
        if branch_mode == BranchMode.STRICT:
            ce_sq = (
                select(CostElement)
                .where(
                    CostElement.branch == branch,
                    CostElement.deleted_at.is_(None),
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                )
                .subquery("ce_sq")
            )
        else:
            ce_prioritized = (
                select(
                    CostElement,
                    func.row_number()
                    .over(
                        partition_by=CostElement.cost_element_id,
                        order_by=(
                            case(
                                (CostElement.branch == branch, 0),
                                (CostElement.branch == "main", 1),
                                else_=2,
                            )
                        ),
                    )
                    .label("rn"),
                )
                .where(
                    CostElement.branch.in_([branch, "main"]),
                    CostElement.deleted_at.is_(None),
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                )
                .subquery("ce_prioritized")
            )
            ce_sq = (
                select(
                    ce_prioritized.c.id,
                    ce_prioritized.c.cost_element_id,
                    ce_prioritized.c.wbe_id,
                    ce_prioritized.c.cost_element_type_id,
                    ce_prioritized.c.code,
                    ce_prioritized.c.name,
                    ce_prioritized.c.budget_amount,
                    ce_prioritized.c.schedule_baseline_id,
                    ce_prioritized.c.forecast_id,
                    ce_prioritized.c.description,
                    ce_prioritized.c.branch,
                    ce_prioritized.c.valid_time,
                    ce_prioritized.c.transaction_time,
                    ce_prioritized.c.deleted_at,
                    ce_prioritized.c.created_by,
                    ce_prioritized.c.deleted_by,
                    ce_prioritized.c.parent_id,
                    ce_prioritized.c.merge_from_branch,
                )
                .where(ce_prioritized.c.rn == 1)
                .subquery("ce_sq")
            )

        # Build schedule baseline subquery
        if branch_mode == BranchMode.STRICT:
            sb_sq = (
                select(ScheduleBaseline)
                .where(
                    ScheduleBaseline.branch == branch,
                    ScheduleBaseline.deleted_at.is_(None),
                    func.upper(cast(Any, ScheduleBaseline).valid_time).is_(None),
                )
                .subquery("sb_sq")
            )
        else:
            sb_prioritized = (
                select(
                    ScheduleBaseline,
                    func.row_number()
                    .over(
                        partition_by=ScheduleBaseline.schedule_baseline_id,
                        order_by=(
                            case(
                                (ScheduleBaseline.branch == branch, 0),
                                (ScheduleBaseline.branch == "main", 1),
                                else_=2,
                            )
                        ),
                    )
                    .label("rn"),
                )
                .where(
                    ScheduleBaseline.branch.in_([branch, "main"]),
                    ScheduleBaseline.deleted_at.is_(None),
                    func.upper(cast(Any, ScheduleBaseline).valid_time).is_(None),
                )
                .subquery("sb_prioritized")
            )
            sb_sq = (
                select(
                    sb_prioritized.c.id,
                    sb_prioritized.c.schedule_baseline_id,
                    sb_prioritized.c.cost_element_id,
                    sb_prioritized.c.name,
                    sb_prioritized.c.start_date,
                    sb_prioritized.c.end_date,
                    sb_prioritized.c.progression_type,
                    sb_prioritized.c.description,
                    sb_prioritized.c.branch,
                    sb_prioritized.c.valid_time,
                    sb_prioritized.c.transaction_time,
                    sb_prioritized.c.deleted_at,
                    sb_prioritized.c.created_by,
                    sb_prioritized.c.deleted_by,
                    sb_prioritized.c.parent_id,
                    sb_prioritized.c.merge_from_branch,
                )
                .where(sb_prioritized.c.rn == 1)
                .subquery("sb_sq")
            )

        # Main query: WBEs LEFT JOIN cost elements LEFT JOIN schedule baselines
        stmt = (
            select(
                ce_sq.c.cost_element_id,
                ce_sq.c.code.label("cost_element_code"),
                ce_sq.c.name.label("cost_element_name"),
                wbe_sq.c.wbe_id,
                wbe_sq.c.code.label("wbe_code"),
                wbe_sq.c.name.label("wbe_name"),
                wbe_sq.c.level.label("wbe_level"),
                wbe_sq.c.parent_wbe_id,
                ce_sq.c.budget_amount,
                sb_sq.c.start_date,
                sb_sq.c.end_date,
                sb_sq.c.progression_type,
            )
            .select_from(wbe_sq)
            .outerjoin(ce_sq, wbe_sq.c.wbe_id == ce_sq.c.wbe_id)
            .outerjoin(
                sb_sq,
                ce_sq.c.schedule_baseline_id == sb_sq.c.schedule_baseline_id,
            )
            .order_by(wbe_sq.c.level, wbe_sq.c.code, ce_sq.c.code)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        items: list[GanttItem] = []
        project_start: datetime | None = None
        project_end: datetime | None = None

        for row in rows:
            # Skip WBE rows without cost elements
            if row.cost_element_id is None:
                continue

            # Track project date range
            if row.start_date is not None:
                if project_start is None or row.start_date < project_start:
                    project_start = row.start_date
            if row.end_date is not None:
                if project_end is None or row.end_date > project_end:
                    project_end = row.end_date

            items.append(
                GanttItem(
                    cost_element_id=row.cost_element_id,
                    cost_element_code=row.cost_element_code,
                    cost_element_name=row.cost_element_name,
                    wbe_id=row.wbe_id,
                    wbe_code=row.wbe_code,
                    wbe_name=row.wbe_name,
                    wbe_level=row.wbe_level,
                    parent_wbe_id=row.parent_wbe_id,
                    budget_amount=row.budget_amount,
                    start_date=row.start_date,
                    end_date=row.end_date,
                    progression_type=row.progression_type,
                )
            )

        return GanttDataResponse(
            items=items,
            project_start=project_start,
            project_end=project_end,
        )
