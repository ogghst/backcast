"""Impact Analysis Service for Change Order Comparison.

This service provides financial and schedule impact analysis
between main branch and change order branches.

Per Phase 3 Plan:
- KPI Comparison: BAC, Budget Delta, Gross Margin
- Entity Changes: Added/Modified/Removed WBEs and Cost Elements
- Waterfall Chart: Cost bridge visualization
- Time Series: Weekly S-curve data for budget comparison
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.impact_analysis import (
    EntityChange,
    EntityChangeType,
    EntityChanges,
    ImpactAnalysisResponse,
    KPIMetric,
    KPIScorecard,
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
        self, change_order_id: UUID, branch_id: int
    ) -> ImpactAnalysisResponse:
        """Analyze impact of a change order by comparing branches.

        Args:
            change_order_id: UUID of the change order
            branch_id: ID of the branch to compare against main

        Returns:
            ImpactAnalysisResponse with complete comparison data

        Raises:
            ValueError: If change order not found or branch invalid
        """
        # TODO: Implement in GREEN phase
        raise NotImplementedError("analyze_impact not yet implemented")

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
        self, project_id: UUID, branch_id: int
    ) -> EntityChanges:
        """Compare entities between main and change branch.

        Args:
            project_id: UUID of the project
            branch_id: ID of the change branch

        Returns:
            EntityChanges with added/modified/removed WBEs and Cost Elements
        """
        # TODO: Implement in GREEN phase
        raise NotImplementedError("_compare_entities not yet implemented")

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
        self, project_id: UUID, branch_id: int
    ) -> list[TimeSeriesPoint]:
        """Generate weekly time-series data.

        Args:
            project_id: UUID of the project
            branch_id: ID of the change branch

        Returns:
            List of weekly TimeSeriesPoint objects
        """
        # TODO: Implement in GREEN phase
        raise NotImplementedError("_generate_time_series not yet implemented")
