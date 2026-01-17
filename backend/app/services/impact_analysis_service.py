"""Impact Analysis Service for Change Order Comparison.

This service provides financial and schedule impact analysis
between main branch and change order branches.

Per Phase 3 Plan:
- KPI Comparison: BAC, Budget Delta, Gross Margin
- Entity Changes: Added/Modified/Removed WBEs and Cost Elements
- Waterfall Chart: Cost bridge visualization
- Time Series: Weekly S-curve data for budget comparison
"""

from datetime import date
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.models.domain.cost_element import CostElement
from app.models.domain.wbe import WBE
from app.models.schemas.impact_analysis import (
    EntityChange,
    EntityChanges,
    ImpactAnalysisResponse,
    KPIMetric,
    KPIScorecard,
    TimeSeriesData,
    TimeSeriesPoint,
    WaterfallSegment,
)


class ImpactAnalysisService:
    """Service for analyzing change order impact between branches.

    This service compares data between a main branch and a change order branch
    to produce comprehensive impact analysis including KPIs, entity changes,
    waterfall charts, and time-series data.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service with a database session.

        Args:
            db_session: Async database session for queries
        """
        self._db = db_session

    async def analyze_impact(
        self, change_order_id: UUID, branch_name: str
    ) -> ImpactAnalysisResponse:
        """Analyze impact of a change order by comparing branches.

        Args:
            change_order_id: UUID of the change order
            branch_name: Name of the change branch (e.g., "co-CO-2026-001")

        Returns:
            ImpactAnalysisResponse with complete comparison data

        Raises:
            ValueError: If change order not found or branch invalid
        """
        # Get change order to retrieve project_id
        co_stmt = (
            select(ChangeOrder)
            .where(
                ChangeOrder.change_order_id == change_order_id,
                ChangeOrder.branch
                == "main",  # Get the change order definition from main
                func.upper(cast(Any, ChangeOrder).valid_time).is_(None),
                cast(Any, ChangeOrder).deleted_at.is_(None),
            )
            .order_by(cast(Any, ChangeOrder).valid_time.desc())
            .limit(1)
        )
        co_result = await self._db.execute(co_stmt)
        change_order = co_result.scalar_one_or_none()

        if change_order is None:
            raise ValueError(f"Change order {change_order_id} not found")

        project_id = change_order.project_id

        # Calculate KPIs from main branch
        main_bac_stmt = select(func.sum(WBE.budget_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == "main",
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )
        main_bac_result = await self._db.execute(main_bac_stmt)
        main_bac = main_bac_result.scalar() or Decimal("0")

        # Calculate KPIs from change branch
        change_bac_stmt = select(func.sum(WBE.budget_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == branch_name,
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )
        change_bac_result = await self._db.execute(change_bac_stmt)
        change_bac = change_bac_result.scalar() or Decimal("0")

        # For simplicity, budget_total = bac (total WBE budget allocation)
        main_budget_total = main_bac
        change_budget_total = change_bac

        # Gross margin calculation (simplified: 20% of budget as margin)
        # In production, this would come from actual cost/revenue data
        main_gross_margin = main_budget_total * Decimal("0.2")
        change_gross_margin = change_budget_total * Decimal("0.2")

        # Compare KPIs
        kpi_scorecard = self._compare_kpis(
            main_bac=main_bac,
            change_bac=change_bac,
            main_budget_total=main_budget_total,
            change_budget_total=change_budget_total,
            main_gross_margin=main_gross_margin,
            change_gross_margin=change_gross_margin,
        )

        # Compare entities
        entity_changes = await self._compare_entities(project_id, branch_name)

        # Build waterfall chart
        margin_delta = change_gross_margin - main_gross_margin
        waterfall = self._build_waterfall(main_gross_margin, margin_delta)

        # Generate time-series data
        time_series_points = await self._generate_time_series(project_id, branch_name)

        # Format time-series data
        time_series = [
            TimeSeriesData(
                metric_name="budget",
                data_points=time_series_points,
            )
        ]

        return ImpactAnalysisResponse(
            change_order_id=change_order_id,
            branch_name=branch_name,
            main_branch_name="main",
            kpi_scorecard=kpi_scorecard,
            entity_changes=entity_changes,
            waterfall=waterfall,
            time_series=time_series,
        )

    def _compare_kpis(
        self,
        main_bac: Decimal,
        change_bac: Decimal,
        main_budget_total: Decimal,
        change_budget_total: Decimal,
        main_gross_margin: Decimal,
        change_gross_margin: Decimal,
    ) -> KPIScorecard:
        """Compare KPIs between main and change branch.

        Args:
            main_bac: BAC in main branch
            change_bac: BAC in change branch
            main_budget_total: Total budget in main branch
            change_budget_total: Total budget in change branch
            main_gross_margin: Gross margin in main branch
            change_gross_margin: Gross margin in change branch

        Returns:
            KPIScorecard with all comparisons
        """

        # Helper function to calculate delta and percent
        def _calculate_metric(main: Decimal, change: Decimal) -> KPIMetric:
            delta = change - main
            # Calculate percent: return 0.0 if delta is 0, None if main is 0
            if delta == 0:
                delta_percent = 0.0
            elif main == 0:
                delta_percent = None
            else:
                delta_percent = float(delta / main * 100)
            return KPIMetric(
                main_value=main,
                change_value=change,
                delta=delta,
                delta_percent=delta_percent,
            )

        return KPIScorecard(
            bac=_calculate_metric(main_bac, change_bac),
            budget_delta=_calculate_metric(main_budget_total, change_budget_total),
            gross_margin=_calculate_metric(main_gross_margin, change_gross_margin),
        )

    async def _compare_entities(
        self, project_id: UUID, branch_name: str
    ) -> EntityChanges:
        """Compare entities between main and change branch.

        Args:
            project_id: UUID of the project
            branch_name: Name of the change branch (e.g., "co-CO-2026-001")

        Returns:
            EntityChanges with added/modified/removed WBEs and Cost Elements
        """
        # Get current WBEs from main branch
        main_wbes_stmt = (
            select(WBE)
            .where(
                WBE.project_id == project_id,
                WBE.branch == "main",
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .order_by(cast(Any, WBE).valid_time.desc())
        )
        main_wbes_result = await self._db.execute(main_wbes_stmt)
        main_wbes = main_wbes_result.scalars().all()

        # Get current WBEs from change branch
        change_wbes_stmt = (
            select(WBE)
            .where(
                WBE.project_id == project_id,
                WBE.branch == branch_name,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .order_by(cast(Any, WBE).valid_time.desc())
        )
        change_wbes_result = await self._db.execute(change_wbes_stmt)
        change_wbes = change_wbes_result.scalars().all()

        # Compare WBEs
        wbe_changes = self._compare_wbe_lists(list(main_wbes), list(change_wbes))

        # Get current Cost Elements from main branch
        main_ce_stmt = (
            select(CostElement)
            .join(WBE, CostElement.wbe_id == WBE.wbe_id)
            .where(
                WBE.project_id == project_id,
                CostElement.branch == "main",
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .order_by(cast(Any, CostElement).valid_time.desc())
        )
        main_ce_result = await self._db.execute(main_ce_stmt)
        main_cost_elements = main_ce_result.scalars().all()

        # Get current Cost Elements from change branch
        change_ce_stmt = (
            select(CostElement)
            .join(WBE, CostElement.wbe_id == WBE.wbe_id)
            .where(
                WBE.project_id == project_id,
                CostElement.branch == branch_name,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .order_by(cast(Any, CostElement).valid_time.desc())
        )
        change_ce_result = await self._db.execute(change_ce_stmt)
        change_cost_elements = change_ce_result.scalars().all()

        # Compare Cost Elements
        ce_changes = self._compare_cost_element_lists(
            list(main_cost_elements), list(change_cost_elements)
        )

        return EntityChanges(wbes=wbe_changes, cost_elements=ce_changes)

    def _compare_wbe_lists(
        self, main_wbes: list[WBE], change_wbes: list[WBE]
    ) -> list[EntityChange]:
        """Compare two lists of WBEs and identify changes.

        Args:
            main_wbes: WBEs from main branch
            change_wbes: WBEs from change branch

        Returns:
            List of EntityChange objects
        """
        # Create lookup maps by root ID
        main_wbe_map = {wbe.wbe_id: wbe for wbe in main_wbes}
        change_wbe_map = {wbe.wbe_id: wbe for wbe in change_wbes}

        changes: list[EntityChange] = []
        all_root_ids = set(main_wbe_map.keys()) | set(change_wbe_map.keys())

        for root_id in all_root_ids:
            main_wbe = main_wbe_map.get(root_id)
            change_wbe = change_wbe_map.get(root_id)

            if main_wbe is None:
                # Added in change branch
                assert (
                    change_wbe is not None
                )  # Logically: root_id in union but not in main
                changes.append(
                    EntityChange(
                        id=int(root_id.int >> 96),  # Simplified ID conversion
                        name=change_wbe.name,
                        change_type="added",
                        budget_delta=None,
                        revenue_delta=None,
                        cost_delta=None,
                    )
                )
            elif change_wbe is None:
                # Removed in change branch (deleted or not created)
                changes.append(
                    EntityChange(
                        id=int(root_id.int >> 96),
                        name=main_wbe.name,
                        change_type="removed",
                        budget_delta=-main_wbe.budget_allocation,  # Negative impact
                        revenue_delta=None,
                        cost_delta=None,
                    )
                )
            else:
                # Exists in both - check for modifications
                budget_delta = change_wbe.budget_allocation - main_wbe.budget_allocation
                if budget_delta != 0:
                    changes.append(
                        EntityChange(
                            id=int(root_id.int >> 96),
                            name=change_wbe.name,
                            change_type="modified",
                            budget_delta=budget_delta,
                            revenue_delta=None,
                            cost_delta=None,
                        )
                    )

        return changes

    def _compare_cost_element_lists(
        self, main_ces: list[CostElement], change_ces: list[CostElement]
    ) -> list[EntityChange]:
        """Compare two lists of Cost Elements and identify changes.

        Args:
            main_ces: Cost Elements from main branch
            change_ces: Cost Elements from change branch

        Returns:
            List of EntityChange objects
        """
        # Create lookup maps by root ID
        main_ce_map = {ce.cost_element_id: ce for ce in main_ces}
        change_ce_map = {ce.cost_element_id: ce for ce in change_ces}

        changes: list[EntityChange] = []
        all_root_ids = set(main_ce_map.keys()) | set(change_ce_map.keys())

        for root_id in all_root_ids:
            main_ce = main_ce_map.get(root_id)
            change_ce = change_ce_map.get(root_id)

            if main_ce is None:
                # Added in change branch
                assert (
                    change_ce is not None
                )  # Logically: root_id in union but not in main
                changes.append(
                    EntityChange(
                        id=int(root_id.int >> 96),
                        name=change_ce.name,
                        change_type="added",
                        budget_delta=None,
                        revenue_delta=None,
                        cost_delta=None,
                    )
                )
            elif change_ce is None:
                # Removed in change branch
                changes.append(
                    EntityChange(
                        id=int(root_id.int >> 96),
                        name=main_ce.name,
                        change_type="removed",
                        budget_delta=-main_ce.budget_amount,
                        revenue_delta=None,
                        cost_delta=None,
                    )
                )
            else:
                # Exists in both - check for modifications
                budget_delta = change_ce.budget_amount - main_ce.budget_amount
                if budget_delta != 0:
                    changes.append(
                        EntityChange(
                            id=int(root_id.int >> 96),
                            name=change_ce.name,
                            change_type="modified",
                            budget_delta=budget_delta,
                            revenue_delta=None,
                            cost_delta=None,
                        )
                    )

        return changes

    def _build_waterfall(
        self, current_margin: Decimal, margin_delta: Decimal
    ) -> list[WaterfallSegment]:
        """Build waterfall chart data.

        Args:
            current_margin: Current gross margin
            margin_delta: Change in margin

        Returns:
            List of WaterfallSegment objects for visualization
        """
        new_margin = current_margin + margin_delta

        return [
            WaterfallSegment(
                name="Current Margin",
                value=current_margin,
                is_delta=False,
            ),
            WaterfallSegment(
                name="Change Impact",
                value=margin_delta,
                is_delta=True,
            ),
            WaterfallSegment(
                name="New Margin",
                value=new_margin,
                is_delta=False,
            ),
        ]

    async def _generate_time_series(
        self, project_id: UUID, branch_name: str
    ) -> list[TimeSeriesPoint]:
        """Generate weekly time-series data.

        Args:
            project_id: UUID of the project
            branch_name: Name of the change branch

        Returns:
            List of weekly TimeSeriesPoint objects
        """
        # Get total budget from main branch
        main_budget_stmt = select(func.sum(WBE.budget_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == "main",
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )
        main_budget_result = await self._db.execute(main_budget_stmt)
        main_total = main_budget_result.scalar() or Decimal("0")

        # Get total budget from change branch
        change_budget_stmt = select(func.sum(WBE.budget_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == branch_name,
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )
        change_budget_result = await self._db.execute(change_budget_stmt)
        change_total = change_budget_result.scalar() or Decimal("0")

        # Return as a single time point (current week)
        # Note: Full implementation would aggregate historical data by week
        # For now, we return current budget totals as the latest time point
        current_week_start = date.today().replace(
            day=1
        )  # First of current month as approximation

        return [
            TimeSeriesPoint(
                week_start=current_week_start,
                main_value=main_total,
                change_value=change_total,
            )
        ]
