"""GanttService for aggregating schedule data for Gantt chart visualization.

Aggregates WBSElement hierarchy, work packages, and schedule baselines into a flat
list suitable for Gantt chart rendering, with branch and time-travel support.

After the ANSI-748 refactoring, the hierarchy is:
    WBSElement -> ControlAccount -> WorkPackage -> CostElement

Schedule baselines are linked to WorkPackages (not CostElements).
"""

import logging
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.domain.control_account import ControlAccount
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.domain.wbs_element import WBSElement
from app.models.domain.work_package import WorkPackage
from app.models.schemas.gantt import GanttDataResponse, GanttItem

logger = logging.getLogger(__name__)


class GanttService:
    """Service for aggregating Gantt chart data across WBSElements, work packages,
    and schedule baselines."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_gantt_data(
        self,
        project_id: UUID,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
        as_of: datetime | None = None,
    ) -> GanttDataResponse:
        """Get aggregated Gantt data for a project.

        Joins WBSElements, work packages, and schedule baselines in a single query
        with branch and version filtering.

        Args:
            project_id: Project root ID
            branch: Branch name (default: "main")
            branch_mode: Branch resolution mode
            as_of: Optional timestamp for time-travel queries

        Returns:
            GanttDataResponse with items sorted by WBSElement hierarchy
        """
        from datetime import UTC

        if as_of is None:
            as_of = datetime.now(tz=UTC)

        # Build WBSElement subquery with branch filtering
        wbe_sq = self._build_wbe_subquery(project_id, branch, branch_mode)

        # Build ControlAccount subquery linking WBE -> CA
        ca_sq = self._build_branch_aware_subquery(
            ControlAccount,
            "control_account_id",
            branch,
            branch_mode,
            extra_where=[ControlAccount.wbs_element_id.isnot(None)],
        )

        # Build WorkPackage subquery linking CA -> WP
        wp_sq = self._build_branch_aware_subquery(
            WorkPackage,
            "work_package_id",
            branch,
            branch_mode,
            extra_where=[WorkPackage.control_account_id.isnot(None)],
        )

        # Build ScheduleBaseline subquery
        sb_sq = self._build_branch_aware_subquery(
            ScheduleBaseline,
            "schedule_baseline_id",
            branch,
            branch_mode,
        )

        # Main query: WBE -> CA -> WP -> SB
        stmt = (
            select(
                wp_sq.c.work_package_id,
                wp_sq.c.code.label("wp_code"),
                wp_sq.c.name.label("wp_name"),
                wp_sq.c.budget_amount,
                wbe_sq.c.wbs_element_id,
                wbe_sq.c.code.label("wbe_code"),
                wbe_sq.c.name.label("wbe_name"),
                wbe_sq.c.level.label("wbe_level"),
                wbe_sq.c.parent_wbs_element_id,
                sb_sq.c.start_date,
                sb_sq.c.end_date,
                sb_sq.c.progression_type,
            )
            .select_from(wbe_sq)
            .outerjoin(ca_sq, wbe_sq.c.wbs_element_id == ca_sq.c.wbs_element_id)
            .outerjoin(wp_sq, ca_sq.c.control_account_id == wp_sq.c.control_account_id)
            .outerjoin(
                sb_sq,
                wp_sq.c.schedule_baseline_id == sb_sq.c.schedule_baseline_id,
            )
            .order_by(wbe_sq.c.level, wbe_sq.c.code, wp_sq.c.code)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        items: list[GanttItem] = []
        project_start: datetime | None = None
        project_end: datetime | None = None

        for row in rows:
            # Track project date range (only for rows with schedule data)
            if row.start_date is not None:
                if project_start is None or row.start_date < project_start:
                    project_start = row.start_date
            if row.end_date is not None:
                if project_end is None or row.end_date > project_end:
                    project_end = row.end_date

            # Include all WBSElements, even those without work packages
            items.append(
                GanttItem(
                    cost_element_id=row.work_package_id,
                    cost_element_code=row.wp_code,
                    cost_element_name=row.wp_name,
                    wbs_element_id=row.wbs_element_id,
                    wbe_code=row.wbe_code,
                    wbe_name=row.wbe_name,
                    wbe_level=row.wbe_level,
                    parent_wbs_element_id=row.parent_wbs_element_id,
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

    def _build_wbe_subquery(
        self,
        project_id: UUID,
        branch: str,
        branch_mode: BranchMode,
    ) -> Any:
        """Build WBSElement subquery with project filter and branch resolution."""
        if branch_mode == BranchMode.ISOLATED:
            return (
                select(
                    WBSElement.wbs_element_id,
                    WBSElement.project_id,
                    WBSElement.parent_wbs_element_id,
                    WBSElement.code,
                    WBSElement.name,
                    WBSElement.level,
                )
                .where(
                    WBSElement.project_id == project_id,
                    WBSElement.branch == branch,
                    WBSElement.deleted_at.is_(None),
                    func.upper(cast(Any, WBSElement).valid_time).is_(None),
                )
                .subquery("wbe_sq")
            )

        # MERGED mode: prefer branch versions, fallback to main
        wbe_prioritized = (
            select(
                WBSElement.wbs_element_id,
                WBSElement.project_id,
                WBSElement.parent_wbs_element_id,
                WBSElement.code,
                WBSElement.name,
                WBSElement.level,
                func.row_number()
                .over(
                    partition_by=WBSElement.wbs_element_id,
                    order_by=(
                        case(
                            (WBSElement.branch == branch, 0),
                            (WBSElement.branch == "main", 1),
                            else_=2,
                        )
                    ),
                )
                .label("rn"),
            )
            .where(
                WBSElement.project_id == project_id,
                WBSElement.branch.in_([branch, "main"]),
                WBSElement.deleted_at.is_(None),
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
            )
            .subquery("wbe_prioritized")
        )
        return (
            select(
                wbe_prioritized.c.wbs_element_id,
                wbe_prioritized.c.project_id,
                wbe_prioritized.c.parent_wbs_element_id,
                wbe_prioritized.c.code,
                wbe_prioritized.c.name,
                wbe_prioritized.c.level,
            )
            .where(wbe_prioritized.c.rn == 1)
            .subquery("wbe_sq")
        )

    def _build_branch_aware_subquery(
        self,
        model: Any,
        root_id_col: str,
        branch: str,
        branch_mode: BranchMode,
        extra_where: list[Any] | None = None,
    ) -> Any:
        """Build a branch-aware subquery for a branchable entity.

        Args:
            model: SQLAlchemy model class (must have branch column).
            root_id_col: Name of the root ID column (e.g. 'work_package_id').
            branch: Branch name to filter on.
            branch_mode: MERGED or ISOLATED.
            extra_where: Additional WHERE conditions.
        """
        base_conditions: list[Any] = [
            model.deleted_at.is_(None),
            func.upper(cast(Any, model).valid_time).is_(None),
        ]
        if extra_where:
            base_conditions.extend(extra_where)

        if branch_mode == BranchMode.ISOLATED:
            conditions = [*base_conditions, model.branch == branch]
            return (
                select(model).where(*conditions).subquery(f"{model.__tablename__}_sq")
            )

        # MERGED mode: prefer branch, fallback to main
        prioritized = (
            select(
                model,
                func.row_number()
                .over(
                    partition_by=getattr(model, root_id_col),
                    order_by=case(
                        (model.branch == branch, 0),
                        (model.branch == "main", 1),
                        else_=2,
                    ),
                )
                .label("rn"),
            )
            .where(
                model.branch.in_([branch, "main"]),
                *base_conditions,
            )
            .subquery(f"{model.__tablename__}_prioritized")
        )
        return (
            select(prioritized)
            .where(prioritized.c.rn == 1)
            .subquery(f"{model.__tablename__}_sq")
        )
