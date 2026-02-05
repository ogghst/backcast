"""Impact Analysis Service for Change Order Comparison.

This service provides financial and schedule impact analysis
between main branch and change order branches.

Per Phase 3 Plan:
- KPI Comparison: BAC, Budget Delta, Gross Margin, Actual Costs
- Entity Changes: Added/Modified/Removed WBEs, Cost Elements, and Cost Registrations
- Waterfall Chart: Cost bridge visualization
- Time Series: Weekly S-curve data for budget comparison

Per Phase 5 Plan:
- Schedule Implication Analysis: Compare schedule baselines
- EVM Performance Index Projections: CPI, SPI, TCPI, EAC
- VAC Projections: Variance at Completion
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.wbe import WBE
from app.models.schemas.impact_analysis import (
    EntityChange,
    EntityChanges,
    EVMMetricsComparison,
    ImpactAnalysisResponse,
    KPIMetric,
    KPIScorecard,
    ScheduleBaselineComparison,
    TimeSeriesData,
    TimeSeriesPoint,
    VACComparison,
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

        # Calculate revenue from main branch
        main_revenue_stmt = select(func.sum(WBE.revenue_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == "main",
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )
        main_revenue_result = await self._db.execute(main_revenue_stmt)
        main_revenue = main_revenue_result.scalar() or Decimal("0")

        # Calculate revenue from change branch
        change_revenue_stmt = select(func.sum(WBE.revenue_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == branch_name,
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )
        change_revenue_result = await self._db.execute(change_revenue_stmt)
        change_revenue = change_revenue_result.scalar() or Decimal("0")

        # For simplicity, budget_total = bac (total WBE budget allocation)
        main_budget_total = main_bac
        change_budget_total = change_bac

        # Calculate actual costs from CostRegistrations
        main_actual_costs_stmt = (
            select(func.sum(CostRegistration.amount))
            .join(CostElement, CostRegistration.cost_element_id == CostElement.cost_element_id)
            .join(WBE, CostElement.wbe_id == WBE.wbe_id)
            .where(
                WBE.project_id == project_id,
                CostRegistration.deleted_at.is_(None),
                func.upper(CostRegistration.valid_time).is_(None),
            )
        )
        main_actual_costs_result = await self._db.execute(main_actual_costs_stmt)
        main_actual_costs = main_actual_costs_result.scalar() or Decimal("0")

        # For change branch, we'd need to filter by branch-specific cost registrations
        # Since CostRegistration is NOT branchable, we use the same query for now
        # In a full implementation, cost registrations would be associated with branches
        # via the cost elements they reference
        change_actual_costs = main_actual_costs  # Placeholder until branch filtering is implemented

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
            main_actual_costs=main_actual_costs,
            change_actual_costs=change_actual_costs,
            main_revenue_total=main_revenue,
            change_revenue_total=change_revenue,
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
        main_actual_costs: Decimal,
        change_actual_costs: Decimal,
        main_revenue_total: Decimal,
        change_revenue_total: Decimal,
    ) -> KPIScorecard:
        """Compare KPIs between main and change branch.

        Args:
            main_bac: BAC in main branch
            change_bac: BAC in change branch
            main_budget_total: Total budget in main branch
            change_budget_total: Total budget in change branch
            main_gross_margin: Gross margin in main branch
            change_gross_margin: Gross margin in change branch
            main_actual_costs: Actual costs (AC) in main branch
            change_actual_costs: Actual costs (AC) in change branch
            main_revenue_total: Total revenue in main branch
            change_revenue_total: Total revenue in change branch

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
            actual_costs=_calculate_metric(main_actual_costs, change_actual_costs),
            revenue_delta=_calculate_metric(main_revenue_total, change_revenue_total),
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

        # Compare Cost Registrations (actual costs)
        main_cr_stmt = (
            select(CostRegistration)
            .join(CostElement, CostRegistration.cost_element_id == CostElement.cost_element_id)
            .join(WBE, CostElement.wbe_id == WBE.wbe_id)
            .where(
                WBE.project_id == project_id,
                CostRegistration.deleted_at.is_(None),
                func.upper(CostRegistration.valid_time).is_(None),
            )
            .order_by(CostRegistration.valid_time.desc())
        )
        main_cr_result = await self._db.execute(main_cr_stmt)
        main_cost_registrations = main_cr_result.scalars().all()

        # Get current Cost Registrations from change branch
        change_cr_stmt = (
            select(CostRegistration)
            .join(CostElement, CostRegistration.cost_element_id == CostElement.cost_element_id)
            .join(WBE, CostElement.wbe_id == WBE.wbe_id)
            .where(
                WBE.project_id == project_id,
                CostRegistration.deleted_at.is_(None),
                func.upper(CostRegistration.valid_time).is_(None),
            )
        )
        # Note: CostRegistration is versionable but NOT branchable, so we need to filter by project via WBE/CostElement
        # The change branch would have different CostRegistrations if new costs were added in the branch
        # For now, we'll compare registrations that exist in the main branch context vs change branch context
        change_cr_result = await self._db.execute(change_cr_stmt)
        change_cost_registrations = change_cr_result.scalars().all()

        # Compare Cost Registrations
        cr_changes = self._compare_cost_registration_lists(
            list(main_cost_registrations), list(change_cost_registrations)
        )

        return EntityChanges(wbes=wbe_changes, cost_elements=ce_changes, cost_registrations=cr_changes)

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
                main_revenue = main_wbe.revenue_allocation or Decimal("0")
                changes.append(
                    EntityChange(
                        id=int(root_id.int >> 96),
                        name=main_wbe.name,
                        change_type="removed",
                        budget_delta=-main_wbe.budget_allocation,  # Negative impact
                        revenue_delta=-main_revenue,  # Negative revenue impact
                        cost_delta=None,
                    )
                )
            else:
                # Exists in both - check for modifications
                budget_delta = change_wbe.budget_allocation - main_wbe.budget_allocation
                main_revenue = main_wbe.revenue_allocation or Decimal("0")
                change_revenue = change_wbe.revenue_allocation or Decimal("0")
                revenue_delta = change_revenue - main_revenue

                if budget_delta != 0 or revenue_delta != 0:
                    changes.append(
                        EntityChange(
                            id=int(root_id.int >> 96),
                            name=change_wbe.name,
                            change_type="modified",
                            budget_delta=budget_delta if budget_delta != 0 else None,
                            revenue_delta=revenue_delta if revenue_delta != 0 else None,
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

    def _compare_cost_registration_lists(
        self, main_crs: list[CostRegistration], change_crs: list[CostRegistration]
    ) -> list[EntityChange]:
        """Compare two lists of Cost Registrations and identify changes.

        Args:
            main_crs: Cost Registrations from main branch
            change_crs: Cost Registrations from change branch

        Returns:
            List of EntityChange objects
        """
        # Create lookup maps by root ID
        main_cr_map = {cr.cost_registration_id: cr for cr in main_crs}
        change_cr_map = {cr.cost_registration_id: cr for cr in change_crs}

        changes: list[EntityChange] = []
        all_root_ids = set(main_cr_map.keys()) | set(change_cr_map.keys())

        for root_id in all_root_ids:
            main_cr = main_cr_map.get(root_id)
            change_cr = change_cr_map.get(root_id)

            # Use a descriptive name for the cost registration
            if main_cr:
                name = f"Cost: {main_cr.description or 'No description'}"
            elif change_cr:
                name = f"Cost: {change_cr.description or 'No description'}"
            else:
                name = "Unknown Cost"

            if main_cr is None:
                # Added in change branch
                assert (
                    change_cr is not None
                )  # Logically: root_id in union but not in main
                changes.append(
                    EntityChange(
                        id=int(root_id.int >> 96),  # Simplified ID conversion
                        name=name,
                        change_type="added",
                        budget_delta=None,
                        revenue_delta=None,
                        cost_delta=change_cr.amount,  # Positive impact (new cost added)
                    )
                )
            elif change_cr is None:
                # Removed in change branch (deleted or not created)
                changes.append(
                    EntityChange(
                        id=int(root_id.int >> 96),
                        name=name,
                        change_type="removed",
                        budget_delta=None,
                        revenue_delta=None,
                        cost_delta=-main_cr.amount,  # Negative impact (cost removed)
                    )
                )
            else:
                # Exists in both - check for modifications
                cost_delta = change_cr.amount - main_cr.amount
                if cost_delta != 0:
                    changes.append(
                        EntityChange(
                            id=int(root_id.int >> 96),
                            name=name,
                            change_type="modified",
                            budget_delta=None,
                            revenue_delta=None,
                            cost_delta=cost_delta,
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

    def _compare_schedule_baselines(
        self,
        main_start_date: datetime,
        main_end_date: datetime,
        main_duration: int,
        main_progression_type: str,
        change_start_date: datetime,
        change_end_date: datetime,
        change_duration: int,
        change_progression_type: str,
    ) -> ScheduleBaselineComparison:
        """Compare schedule baselines between main and change branches.

        Calculates deltas for start date, end date, duration, and detects
        progression type changes.

        Context: Used by analyze_impact() to provide schedule implication
        analysis for change orders. Helps project managers understand timeline
        impacts of proposed changes.

        Args:
            main_start_date: Schedule start date in main branch
            main_end_date: Schedule end date in main branch
            main_duration: Schedule duration in days (main branch)
            main_progression_type: Progression type in main branch (LINEAR/GAUSSIAN/LOGARITHMIC)
            change_start_date: Schedule start date in change branch
            change_end_date: Schedule end date in change branch
            change_duration: Schedule duration in days (change branch)
            change_progression_type: Progression type in change branch

        Returns:
            ScheduleBaselineComparison with deltas and progression change flag

        Example:
            >>> main_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
            >>> main_end = datetime(2026, 6, 30, tzinfo=timezone.utc)
            >>> result = service._compare_schedule_baselines(
            ...     main_start_date=main_start,
            ...     main_end_date=main_end,
            ...     main_duration=180,
            ...     main_progression_type="LINEAR",
            ...     change_start_date=main_start,
            ...     change_end_date=main_end,
            ...     change_duration=180,
            ...     change_progression_type="GAUSSIAN",
            ... )
            >>> result["progression_changed"]
            True
        """
        # Calculate date deltas (in days)
        start_delta = (change_start_date - main_start_date).days
        end_delta = (change_end_date - main_end_date).days
        duration_delta = change_duration - main_duration

        # Detect progression type change
        progression_changed = main_progression_type != change_progression_type

        return ScheduleBaselineComparison(
            start_delta_days=start_delta,
            end_delta_days=end_delta,
            duration_delta_days=duration_delta,
            progression_changed=progression_changed,
            main_progression_type=main_progression_type,
            change_progression_type=change_progression_type,
        )

    def _compare_evm_metrics(
        self,
        main_cpi: Decimal,
        change_cpi: Decimal,
        main_spi: Decimal,
        change_spi: Decimal,
        main_tcpi: Decimal,
        change_tcpi: Decimal,
        main_eac: Decimal,
        change_eac: Decimal,
    ) -> EVMMetricsComparison:
        """Compare EVM performance metrics between main and change branches.

        Calculates deltas for CPI, SPI, TCPI, and EAC to understand
        performance implications of change orders.

        Context: Used by analyze_impact() to provide EVM performance
        projections. Helps project managers understand efficiency and
        cost implications of proposed changes.

        Args:
            main_cpi: Cost Performance Index in main branch (EV/AC)
            change_cpi: Cost Performance Index in change branch
            main_spi: Schedule Performance Index in main branch (EV/PV)
            change_spi: Schedule Performance Index in change branch
            main_tcpi: To-Complete Performance Index in main branch
            change_tcpi: To-Complete Performance Index in change branch
            main_eac: Estimate at Completion in main branch
            change_eac: Estimate at Completion in change branch

        Returns:
            EVMMetricsComparison with deltas for all metrics

        Example:
            >>> result = service._compare_evm_metrics(
            ...     main_cpi=Decimal("1.0"),
            ...     change_cpi=Decimal("0.85"),
            ...     main_spi=Decimal("1.0"),
            ...     change_spi=Decimal("0.90"),
            ...     main_tcpi=Decimal("1.0"),
            ...     change_tcpi=Decimal("1.15"),
            ...     main_eac=Decimal("100000.00"),
            ...     change_eac=Decimal("120000.00"),
            ... )
            >>> result["cpi_delta"]
            Decimal("-0.15")  # Cost performance degraded
        """
        # Calculate deltas (change - main)
        cpi_delta = change_cpi - main_cpi
        spi_delta = change_spi - main_spi
        tcpi_delta = change_tcpi - main_tcpi
        eac_delta = change_eac - main_eac

        return EVMMetricsComparison(
            cpi_delta=cpi_delta,
            spi_delta=spi_delta,
            tcpi_delta=tcpi_delta,
            eac_delta=eac_delta,
        )

    def _compare_vac(
        self,
        main_vac: Decimal,
        change_vac: Decimal,
    ) -> VACComparison:
        """Compare Variance at Completion (VAC) between main and change branches.

        VAC = BAC - EAC (Budget at Completion - Estimate at Completion)
        - Positive VAC: Under budget (favorable)
        - Negative VAC: Over budget (unfavorable)
        - Zero VAC: On budget

        Context: Used by analyze_impact() to provide VAC projections.
        Helps project managers understand final cost variance implications
        of proposed changes.

        Args:
            main_vac: Variance at Completion in main branch (BAC - EAC)
            change_vac: Variance at Completion in change branch (BAC - EAC)

        Returns:
            VACComparison with delta and both VAC values

        Example:
            >>> # Main branch: $100k BAC, $100k EAC = $0 VAC (on budget)
            >>> # Change branch: $120k BAC, $130k EAC = -$10k VAC (over budget)
            >>> result = service._compare_vac(
            ...     main_vac=Decimal("0"),
            ...     change_vac=Decimal("-10000.00"),
            ... )
            >>> result["vac_delta"]
            Decimal("-10000.00")  # $10k worse than main
        """
        # Calculate delta (change - main)
        vac_delta = change_vac - main_vac

        return VACComparison(
            vac_delta=vac_delta,
            main_vac=main_vac,
            change_vac=change_vac,
        )
