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

import asyncio
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.domain.change_order import ChangeOrder
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.forecast import Forecast
from app.models.domain.project import Project
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.domain.wbe import WBE
from app.models.schemas.evm import EntityType

if TYPE_CHECKING:
    from app.models.domain.progress_entry import ProgressEntry
from app.models.schemas.forecast import ForecastRead
from app.models.schemas.impact_analysis import (
    EntityChange,
    EntityChanges,
    EVMMetricsComparison,
    ForecastChanges,
    ForecastComparison,
    ImpactAnalysisResponse,
    KPIMetric,
    KPIScorecard,
    ScheduleBaselineComparison,
    TimeSeriesData,
    TimeSeriesPoint,
    VACComparison,
    WaterfallSegment,
)

logger = logging.getLogger(__name__)


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

        # Import EVMService lazily to avoid circular import
        from app.services.evm_service import EVMService

        self._evm_service = EVMService(db_session)

    @staticmethod
    def _get_progress_as_of(
        progress_entries: list["ProgressEntry"],
        as_of_date: datetime,
    ) -> Decimal:
        """Get progress percentage as of a specific date.

        Finds the most recent progress entry that was recorded on or before
        the as_of_date. This ensures historical EV calculations use progress
        as it was known at that point in time, not future progress.

        Args:
            progress_entries: List of ProgressEntry objects for a cost element
            as_of_date: The date to get progress as of (typically week_mid)

        Returns:
            Progress percentage (0-100) as of the date, or 0 if no valid entries
        """
        # Filter entries with valid_time.lower <= as_of_date (recorded on or before)
        valid_entries = [
            pe
            for pe in progress_entries
            if pe.valid_time and pe.valid_time.lower <= as_of_date
        ]

        if not valid_entries:
            return Decimal("0")

        # Return the most recent valid entry (highest valid_time.lower)
        latest = max(valid_entries, key=lambda pe: pe.valid_time.lower)
        return latest.progress_percentage

    async def analyze_impact(
        self,
        change_order_id: UUID,
        branch_name: str,
        branch_mode: BranchMode = BranchMode.MERGE,
        timeout_seconds: int = 300,
        include_evm_metrics: bool = True,
        as_of: datetime | None = None,
    ) -> ImpactAnalysisResponse:
        """Analyze impact of a change order by comparing branches.

        Context: Compares financial and schedule metrics between main branch
        and change order branch to show the delta impact or merged result.

        Branch Mode:
        - MERGE mode: Shows merged result (main + change delta) - most intuitive for users
        - STRICT mode: Shows isolated comparison (delta only) - for detailed analysis

        Time Machine (as_of):
        - When as_of is provided, filters all temporal data to include only entities
          with valid_time starting before or at the as_of timestamp
        - When as_of is None, returns current state (no temporal filtering)
        - Edge case: as_of after current date behaves same as as_of=None (all current data)

        CostRegistration Note: CostRegistrations are NOT branchable (global facts).
        When joining CostRegistration → CostElement, we must filter by branch to
        ensure we count costs against the correct branch's CostElements. A single
        CostRegistration can be joined with either main or branch CostElements
        (both satisfy the FK), so explicit branch filtering is required.

        Args:
            change_order_id: UUID of the change order
            branch_name: Name of the change branch (e.g., "BR-CO-2026-001")
            branch_mode: MERGE (default) shows merged result, STRICT shows isolated comparison
            timeout_seconds: Timeout in seconds (default: 300 = 5 minutes)
            include_evm_metrics: Whether to include expensive EVM metrics (CPI, SPI, etc.)
            as_of: Time travel timestamp (None = current, past = historical point)

        Returns:
            ImpactAnalysisResponse with complete comparison data

        Raises:
            ValueError: If timeout occurs, change order not found, or branch invalid
        """
        # Get change order to retrieve project_id and update status
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

        # Set status to in_progress
        change_order.impact_analysis_status = "in_progress"
        await self._db.commit()

        try:
            # Create analysis task with timeout
            analysis_task = asyncio.create_task(
                self._perform_analysis(
                    change_order_id,
                    branch_name,
                    branch_mode,
                    include_evm_metrics,
                    as_of,
                )
            )

            # Wait with timeout
            result = await asyncio.wait_for(analysis_task, timeout=timeout_seconds)

            # Update status to completed
            change_order.impact_analysis_status = "completed"
            await self._db.commit()

            return result

        except TimeoutError:
            # Update status to failed
            change_order.impact_analysis_status = "failed"
            await self._db.commit()

            logger.error(
                f"Impact analysis timed out after {timeout_seconds}s "
                f"for change order {change_order_id}"
            )

            raise ValueError(
                f"Impact analysis timed out after {timeout_seconds} seconds. "
                f"Please use admin recovery to proceed."
            ) from None
        except Exception as e:
            # Update status to failed on other errors
            change_order.impact_analysis_status = "failed"
            await self._db.commit()

            logger.error(f"Impact analysis failed for CO {change_order_id}: {e}")
            raise

    async def _perform_analysis(
        self,
        change_order_id: UUID,
        branch_name: str,
        branch_mode: BranchMode,
        include_evm_metrics: bool = True,
        as_of: datetime | None = None,
    ) -> ImpactAnalysisResponse:
        """Perform the actual impact analysis.

        Contains all the core analysis logic without timeout handling.
        This method is called by analyze_impact() within a timeout context.

        Args:
            change_order_id: UUID of the change order
            branch_name: Name of the change branch (e.g., "BR-CO-2026-001")
            branch_mode: MERGE mode calculates merged values, STRICT mode calculates isolated values
            include_evm_metrics: Whether to include expensive EVM metrics
            as_of: Time travel timestamp (None = current, past = historical point)

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

        # Calculate KPIs from main branch with temporal filtering
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            main_ce_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == "main",
                    or_(
                        cast(Any, WBE).deleted_at.is_(None),
                        cast(Any, WBE).deleted_at > as_of,
                    ),
                    WBE.valid_time.op("@>")(as_of_tstz),
                    func.lower(WBE.valid_time) <= as_of_tstz,
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                )
            )
            branch_ce_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == branch_name,
                    or_(
                        cast(Any, WBE).deleted_at.is_(None),
                        cast(Any, WBE).deleted_at > as_of,
                    ),
                    WBE.valid_time.op("@>")(as_of_tstz),
                    func.lower(WBE.valid_time) <= as_of_tstz,
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                )
            )
            main_revenue_stmt = select(func.sum(WBE.revenue_allocation)).where(
                WBE.project_id == project_id,
                WBE.branch == "main",
                or_(
                    cast(Any, WBE).deleted_at.is_(None),
                    cast(Any, WBE).deleted_at > as_of,
                ),
                WBE.valid_time.op("@>")(as_of_tstz),
                func.lower(WBE.valid_time) <= as_of_tstz,
            )
            main_wbes_stmt = select(WBE).where(
                WBE.project_id == project_id,
                WBE.branch == "main",
                or_(
                    cast(Any, WBE).deleted_at.is_(None),
                    cast(Any, WBE).deleted_at > as_of,
                ),
                WBE.valid_time.op("@>")(as_of_tstz),
                func.lower(WBE.valid_time) <= as_of_tstz,
            )
            branch_wbes_stmt = select(WBE).where(
                WBE.project_id == project_id,
                WBE.branch == branch_name,
                or_(
                    cast(Any, WBE).deleted_at.is_(None),
                    cast(Any, WBE).deleted_at > as_of,
                ),
                WBE.valid_time.op("@>")(as_of_tstz),
                func.lower(WBE.valid_time) <= as_of_tstz,
            )
        else:
            main_ce_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == "main",
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
            )
            branch_ce_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == branch_name,
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
            )
            main_revenue_stmt = select(func.sum(WBE.revenue_allocation)).where(
                WBE.project_id == project_id,
                WBE.branch == "main",
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            main_wbes_stmt = select(WBE).where(
                WBE.project_id == project_id,
                WBE.branch == "main",
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            branch_wbes_stmt = select(WBE).where(
                WBE.project_id == project_id,
                WBE.branch == branch_name,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )

        # Execute CE queries for BAC calculation
        main_ces_result = await self._db.execute(main_ce_stmt)
        main_ces = {ce.cost_element_id: ce for ce in main_ces_result.scalars().all()}

        branch_ces_result = await self._db.execute(branch_ce_stmt)
        branch_ces = {
            ce.cost_element_id: ce for ce in branch_ces_result.scalars().all()
        }

        main_bac = sum(
            (ce.budget_amount or Decimal("0") for ce in main_ces.values()), Decimal("0")
        )

        # Calculate revenue from main branch
        main_revenue_result = await self._db.execute(main_revenue_stmt)
        main_revenue = main_revenue_result.scalar() or Decimal("0")

        # Execute WBE queries
        main_wbes_result = await self._db.execute(main_wbes_stmt)
        main_wbes = {wbe.wbe_id: wbe for wbe in main_wbes_result.scalars().all()}

        branch_wbes_result = await self._db.execute(branch_wbes_stmt)
        branch_wbes = {wbe.wbe_id: wbe for wbe in branch_wbes_result.scalars().all()}

        # Step 3: Build merged view and calculate KPIs
        merged_bac = Decimal("0")
        merged_revenue = Decimal("0")

        # Include all main CEs, using branch override if exists
        for ce_id, main_ce in main_ces.items():
            if ce_id in branch_ces:
                merged_bac += branch_ces[ce_id].budget_amount or Decimal("0")
            else:
                merged_bac += main_ce.budget_amount or Decimal("0")

        # Include CEs that exist only on branch
        for ce_id, branch_ce in branch_ces.items():
            if ce_id not in main_ces:
                merged_bac += branch_ce.budget_amount or Decimal("0")

        # Calculate merged revenue from WBEs
        for wbe_id, main_wbe in main_wbes.items():
            if wbe_id in branch_wbes:
                merged_revenue += branch_wbes[wbe_id].revenue_allocation or Decimal("0")
            else:
                merged_revenue += main_wbe.revenue_allocation or Decimal("0")

        for wbe_id, branch_wbe in branch_wbes.items():
            if wbe_id not in main_wbes:
                merged_revenue += branch_wbe.revenue_allocation or Decimal("0")

        change_bac = merged_bac
        change_revenue = merged_revenue

        # For simplicity, budget_total = bac (total WBE budget allocation)
        main_budget_total = main_bac
        change_budget_total = change_bac

        # Calculate actual costs from CostRegistrations with temporal filtering
        # CRITICAL: Filter CostElement by branch because CostRegistration is NOT branchable
        # Without this filter, the join could match CostElements from any branch, causing
        # incorrect cost aggregation and FK violations
        # Also apply temporal filtering for WBE, CostElement, and CostRegistration
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            main_actual_costs_stmt = (
                select(func.sum(CostRegistration.amount))
                .join(
                    CostElement,
                    CostRegistration.cost_element_id == CostElement.cost_element_id,
                )
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch
                    == "main",  # STRICT: Only count costs against main branch CostElements
                    # Zombie protection for WBE
                    or_(
                        cast(Any, WBE).deleted_at.is_(None),
                        cast(Any, WBE).deleted_at > as_of,
                    ),
                    # Time travel for WBE
                    WBE.valid_time.op("@>")(as_of_tstz),
                    func.lower(WBE.valid_time) <= as_of_tstz,
                    # Zombie protection for CostElement
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    # Time travel for CostElement
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                    # Zombie protection for CostRegistration
                    or_(
                        CostRegistration.deleted_at.is_(None),
                        CostRegistration.deleted_at > as_of,
                    ),
                    # Time travel for CostRegistration
                    CostRegistration.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostRegistration.valid_time) <= as_of_tstz,
                )
            )
        else:
            # Current version query
            main_actual_costs_stmt = (
                select(func.sum(CostRegistration.amount))
                .join(
                    CostElement,
                    CostRegistration.cost_element_id == CostElement.cost_element_id,
                )
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch
                    == "main",  # STRICT: Only count costs against main branch CostElements
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                    CostRegistration.deleted_at.is_(None),
                    func.upper(CostRegistration.valid_time).is_(None),
                )
            )
        main_actual_costs_result = await self._db.execute(main_actual_costs_stmt)
        main_actual_costs = main_actual_costs_result.scalar() or Decimal("0")

        # For change branch actual costs, we use the same value as main for now
        # because CostRegistration is NOT branchable. In the future, if CostRegistrations
        # become branchable or we add branch-context tracking, we'd filter those here too.
        change_actual_costs = (
            main_actual_costs  # Placeholder until branch filtering is implemented
        )

        # Gross margin calculation (simplified: 20% of budget as margin)
        # In production, this would come from actual cost/revenue data
        main_gross_margin = main_budget_total * Decimal("0.2")
        change_gross_margin = change_budget_total * Decimal("0.2")

        # Compare KPIs (basic financial metrics)
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
            branch_mode=branch_mode,
        )

        # Phase 5: Compare schedule baselines
        schedule_comparison = await self._fetch_and_compare_schedule_baselines(
            project_id=project_id,
            branch_name=branch_name,
            branch_mode=branch_mode,
            as_of=as_of,
        )
        kpi_scorecard.schedule_start_date = schedule_comparison["schedule_start_date"]
        kpi_scorecard.schedule_end_date = schedule_comparison["schedule_end_date"]
        kpi_scorecard.schedule_duration = schedule_comparison["schedule_duration"]

        # Phase 5: Compare EVM metrics
        if include_evm_metrics:
            evm_comparison = await self._fetch_and_compare_evm_metrics(
                project_id=project_id,
                branch_name=branch_name,
                branch_mode=branch_mode,
                as_of=as_of,
            )
            kpi_scorecard.cpi = evm_comparison["cpi"]
            kpi_scorecard.spi = evm_comparison["spi"]
            kpi_scorecard.tcpi = evm_comparison["tcpi"]
            kpi_scorecard.eac = evm_comparison["eac"]
            kpi_scorecard.vac = evm_comparison["vac"]
        else:
            # Skip expensive calculation if not requested
            kpi_scorecard.cpi = None
            kpi_scorecard.spi = None
            kpi_scorecard.tcpi = None
            kpi_scorecard.eac = None
            kpi_scorecard.vac = None

        # Compare entities
        entity_changes = await self._compare_entities(project_id, branch_name, as_of)

        # Compare forecasts
        forecast_changes = await self._compare_forecasts(project_id, branch_name, as_of)

        # Build waterfall chart
        margin_delta = change_gross_margin - main_gross_margin
        waterfall = self._build_waterfall(main_gross_margin, margin_delta)

        # Generate time-series data (returns 4 metrics: budget, pv, ev, ac)
        time_series = await self._generate_time_series(project_id, branch_name, as_of)

        return ImpactAnalysisResponse(
            change_order_id=change_order_id,
            branch_name=branch_name,
            main_branch_name="main",
            kpi_scorecard=kpi_scorecard,
            entity_changes=entity_changes,
            waterfall=waterfall,
            time_series=time_series,
            forecast_changes=forecast_changes,
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
        branch_mode: BranchMode = BranchMode.MERGE,
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
            branch_mode: MERGE mode calculates merged values, STRICT mode calculates isolated values

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

            # Calculate merged value when in MERGE mode
            merged_value = None
            if branch_mode == BranchMode.MERGE:
                # If change branch is empty (0), it means "no changes", not "delete everything"
                # In this case, merged value should equal main value
                if change == 0 and main > 0:
                    merged_value = main  # No changes - merged equals main
                else:
                    merged_value = main + delta  # Normal merge calculation

            return KPIMetric(
                main_value=main,
                change_value=change,
                merged_value=merged_value,
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
        self, project_id: UUID, branch_name: str, as_of: datetime | None = None
    ) -> EntityChanges:
        """Compare entities between main and merged (main + branch) view.

        Uses MERGE mode semantics per temporal-query-reference.md:
        - Main branch: All entities on "main"
        - Merged view: Branch entities override main entities with same ID,
          main entities without branch override remain as-is

        This ensures "what-if" analysis shows the complete picture: base project
        with change order modifications overlaid.

        Args:
            project_id: UUID of the project
            branch_name: Name of the change branch (e.g., "BR-CO-2026-001")
            as_of: Time travel timestamp (None = current, past = historical point)

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
        main_wbes = list(main_wbes_result.scalars().all())

        # Get WBEs from change branch (branch-specific entities only)
        branch_wbes_stmt = (
            select(WBE)
            .where(
                WBE.project_id == project_id,
                WBE.branch == branch_name,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .order_by(cast(Any, WBE).valid_time.desc())
        )
        branch_wbes_result = await self._db.execute(branch_wbes_stmt)
        branch_wbes = list(branch_wbes_result.scalars().all())

        # MERGE MODE: Build merged WBE view (branch overrides main)
        main_wbe_map = {wbe.wbe_id: wbe for wbe in main_wbes}
        branch_wbe_map = {wbe.wbe_id: wbe for wbe in branch_wbes}

        # Merged view: start with main, overlay branch entities
        merged_wbes: list[WBE] = []
        for wbe_id, main_wbe in main_wbe_map.items():
            if wbe_id in branch_wbe_map:
                # Branch has override for this entity
                merged_wbes.append(branch_wbe_map[wbe_id])
            else:
                # No branch override - use main (unchanged)
                merged_wbes.append(main_wbe)

        # Add any WBEs that exist only on branch (new entities)
        for wbe_id, branch_wbe in branch_wbe_map.items():
            if wbe_id not in main_wbe_map:
                merged_wbes.append(branch_wbe)

        # We will compare WBEs after gathering Cost Elements so we can aggregate budgets.

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
        main_cost_elements = list(main_ce_result.scalars().all())

        # Get Cost Elements from change branch (branch-specific only)
        branch_ce_stmt = (
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
        branch_ce_result = await self._db.execute(branch_ce_stmt)
        branch_cost_elements = list(branch_ce_result.scalars().all())

        # MERGE MODE: Build merged CostElement view (branch overrides main)
        main_ce_map = {ce.cost_element_id: ce for ce in main_cost_elements}
        branch_ce_map = {ce.cost_element_id: ce for ce in branch_cost_elements}

        merged_cost_elements: list[CostElement] = []
        for ce_id, main_ce in main_ce_map.items():
            if ce_id in branch_ce_map:
                merged_cost_elements.append(branch_ce_map[ce_id])
            else:
                merged_cost_elements.append(main_ce)

        for ce_id, branch_ce in branch_ce_map.items():
            if ce_id not in main_ce_map:
                merged_cost_elements.append(branch_ce)

        # Compare Cost Elements: main vs merged view
        ce_changes = self._compare_cost_element_lists(
            main_cost_elements, merged_cost_elements
        )

        # Aggregate Cost Element budgets by WBE root ID
        main_wbe_budgets: dict[UUID, Decimal] = defaultdict(Decimal)
        for ce in main_cost_elements:
            main_wbe_budgets[ce.wbe_id] += ce.budget_amount or Decimal("0")

        merged_wbe_budgets: dict[UUID, Decimal] = defaultdict(Decimal)
        for ce in merged_cost_elements:
            merged_wbe_budgets[ce.wbe_id] += ce.budget_amount or Decimal("0")

        # Compare WBEs: main vs merged view using aggregated Cost Element budgets
        wbe_changes = self._compare_wbe_lists(
            main_wbes, merged_wbes, main_wbe_budgets, merged_wbe_budgets
        )

        # Compare Cost Registrations (actual costs)
        # CRITICAL: Filter CostElement by branch because CostRegistration is NOT branchable
        # CRITICAL: Apply temporal filtering to all entities (WBE, CostElement, CostRegistration)
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            main_cr_stmt = (
                select(CostRegistration)
                .join(
                    CostElement,
                    CostRegistration.cost_element_id == CostElement.cost_element_id,
                )
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch
                    == "main",  # STRICT: Only match main branch CostElements
                    # Zombie protection for WBE
                    or_(
                        cast(Any, WBE).deleted_at.is_(None),
                        cast(Any, WBE).deleted_at > as_of,
                    ),
                    # Time travel for WBE
                    WBE.valid_time.op("@>")(as_of_tstz),
                    func.lower(WBE.valid_time) <= as_of_tstz,
                    # Zombie protection for CostElement
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    # Time travel for CostElement
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                    # Zombie protection for CostRegistration
                    or_(
                        CostRegistration.deleted_at.is_(None),
                        CostRegistration.deleted_at > as_of,
                    ),
                    # Time travel for CostRegistration
                    CostRegistration.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostRegistration.valid_time) <= as_of_tstz,
                )
                .order_by(CostRegistration.valid_time.desc())
            )
        else:
            # Current version query
            main_cr_stmt = (
                select(CostRegistration)
                .join(
                    CostElement,
                    CostRegistration.cost_element_id == CostElement.cost_element_id,
                )
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch
                    == "main",  # STRICT: Only match main branch CostElements
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                    CostRegistration.deleted_at.is_(None),
                    func.upper(CostRegistration.valid_time).is_(None),
                )
                .order_by(CostRegistration.valid_time.desc())
            )
        main_cr_result = await self._db.execute(main_cr_stmt)
        main_cost_registrations = list(main_cr_result.scalars().all())

        # Get Cost Registrations linked to branch CostElements
        # CRITICAL: Filter CostElement by branch because CostRegistration is NOT branchable
        # CRITICAL: Apply temporal filtering to all entities (WBE, CostElement, CostRegistration)
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            branch_cr_stmt = (
                select(CostRegistration)
                .join(
                    CostElement,
                    CostRegistration.cost_element_id == CostElement.cost_element_id,
                )
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == branch_name,  # Branch-specific CostElements
                    # Zombie protection for WBE
                    or_(
                        cast(Any, WBE).deleted_at.is_(None),
                        cast(Any, WBE).deleted_at > as_of,
                    ),
                    # Time travel for WBE
                    WBE.valid_time.op("@>")(as_of_tstz),
                    func.lower(WBE.valid_time) <= as_of_tstz,
                    # Zombie protection for CostElement
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    # Time travel for CostElement
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                    # Zombie protection for CostRegistration
                    or_(
                        CostRegistration.deleted_at.is_(None),
                        CostRegistration.deleted_at > as_of,
                    ),
                    # Time travel for CostRegistration
                    CostRegistration.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostRegistration.valid_time) <= as_of_tstz,
                )
                .order_by(CostRegistration.valid_time.desc())
            )
        else:
            # Current version query
            branch_cr_stmt = (
                select(CostRegistration)
                .join(
                    CostElement,
                    CostRegistration.cost_element_id == CostElement.cost_element_id,
                )
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == branch_name,  # Branch-specific CostElements
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                    CostRegistration.deleted_at.is_(None),
                    func.upper(CostRegistration.valid_time).is_(None),
                )
                .order_by(CostRegistration.valid_time.desc())
            )
        branch_cr_result = await self._db.execute(branch_cr_stmt)
        branch_cost_registrations = list(branch_cr_result.scalars().all())

        # MERGE MODE: Build merged CostRegistration view
        # Note: CostRegistration is NOT branchable - it's linked to CostElements
        # We merge by looking at which CostElements are in the merged view
        merged_ce_ids = {ce.cost_element_id for ce in merged_cost_elements}

        # For CRs, we include:
        # - CRs linked to main CostElements that are NOT overridden by branch
        # - CRs linked to branch CostElements
        main_cr_map = {cr.cost_registration_id: cr for cr in main_cost_registrations}
        branch_cr_map = {
            cr.cost_registration_id: cr for cr in branch_cost_registrations
        }

        merged_cost_registrations: list[CostRegistration] = []
        # CRITICAL: Only include registrations linked to CostElements in the merged view
        # This reflects MERGE mode semantics for actual costs
        for _cr_id, _main_cr in main_cr_map.items():
            if _main_cr.cost_element_id in merged_ce_ids:
                if _cr_id in branch_cr_map:
                    merged_cost_registrations.append(branch_cr_map[_cr_id])
                else:
                    merged_cost_registrations.append(_main_cr)

        for _cr_id, _branch_cr in branch_cr_map.items():
            if _cr_id not in main_cr_map:
                if _branch_cr.cost_element_id in merged_ce_ids:
                    merged_cost_registrations.append(_branch_cr)

        # Compare Cost Registrations: main vs merged view
        cr_changes = self._compare_cost_registration_lists(
            main_cost_registrations, merged_cost_registrations
        )

        # Aggregate cost deltas by WBE and Cost Element for enriched entity changes
        # Map of root_id -> total cost delta
        wbe_cost_deltas: dict[UUID, Decimal] = {}
        ce_cost_deltas: dict[UUID, Decimal] = {}

        # Build cost delta maps directly from CR lists
        merged_cr_map = {
            cr.cost_registration_id: cr for cr in merged_cost_registrations
        }
        all_cr_ids = set(main_cr_map.keys()) | set(merged_cr_map.keys())

        for cr_id in all_cr_ids:
            main_cr: CostRegistration | None = main_cr_map.get(cr_id)
            merged_cr: CostRegistration | None = merged_cr_map.get(cr_id)

            delta = Decimal("0")
            ref_cr: CostRegistration | None = None

            if main_cr is None and merged_cr is not None:
                # Added in branch
                delta = merged_cr.amount
                ref_cr = merged_cr
            elif merged_cr is None and main_cr is not None:
                # Removed in branch
                delta = -main_cr.amount
                ref_cr = main_cr
            elif main_cr is not None and merged_cr is not None:
                ref_cr = merged_cr

            if delta != 0 and ref_cr:
                # Link to CostElement
                ce_id = ref_cr.cost_element_id
                ce_cost_deltas[ce_id] = ce_cost_deltas.get(ce_id, Decimal("0")) + delta

                # We need to find the WBE for this CE to aggregate up
                # Optimization: we have merged_cost_elements list
                pass

        # Map CE -> WBE for aggregation
        ce_to_wbe_map: dict[UUID, UUID] = {}
        for ce in merged_cost_elements:
            ce_to_wbe_map[ce.cost_element_id] = ce.wbe_id
        for ce in main_cost_elements:
            if ce.cost_element_id not in ce_to_wbe_map:
                ce_to_wbe_map[ce.cost_element_id] = ce.wbe_id

        # Aggregate CE cost deltas into WBE cost deltas
        for ce_id, delta in ce_cost_deltas.items():
            _wbe_id: UUID | None = ce_to_wbe_map.get(ce_id)
            if _wbe_id:
                wbe_cost_deltas[_wbe_id] = (
                    wbe_cost_deltas.get(_wbe_id, Decimal("0")) + delta
                )

        # Compare WBEs: main vs merged view with cost deltas
        wbe_changes = self._compare_wbe_lists(main_wbes, merged_wbes, wbe_cost_deltas)

        # Compare Cost Elements: main vs merged view with cost deltas
        ce_changes = self._compare_cost_element_lists(
            main_cost_elements, merged_cost_elements, ce_cost_deltas
        )

        return EntityChanges(
            wbes=wbe_changes, cost_elements=ce_changes, cost_registrations=cr_changes
        )

    def _compare_wbe_lists(
        self,
        main_wbes: list[WBE],
        change_wbes: list[WBE],
        main_budgets: dict[UUID, Decimal] | None = None,
        change_budgets: dict[UUID, Decimal] | None = None,
        cost_deltas: dict[UUID, Decimal] | None = None,
    ) -> list[EntityChange]:
        """Compare two lists of WBEs and identify changes.

        Args:
            main_wbes: WBEs from main branch
            change_wbes: WBEs from change branch (merged view)
            main_budgets: Optional map of wbe_id -> aggregated cost element budget (main)
            change_budgets: Optional map of wbe_id -> aggregated cost element budget (merged)
            cost_deltas: Optional map of wbe_id -> aggregated cost delta

        Returns:
            List of EntityChange objects
        """
        # Create lookup maps by root ID
        main_wbe_map = {wbe.wbe_id: wbe for wbe in main_wbes}
        change_wbe_map = {wbe.wbe_id: wbe for wbe in change_wbes}

        changes: list[EntityChange] = []
        all_root_ids = set(main_wbe_map.keys()) | set(change_wbe_map.keys())
        cost_deltas = cost_deltas or {}
        main_budgets = main_budgets or {}
        change_budgets = change_budgets or {}

        for root_id in all_root_ids:
            main_wbe = main_wbe_map.get(root_id)
            change_wbe = change_wbe_map.get(root_id)
            cost_delta = cost_deltas.get(root_id)

            if main_wbe is None:
                # Added in change branch
                assert (
                    change_wbe is not None
                )  # Logically: root_id in union but not in main

                # For added entities, we show the full value as the delta
                changes.append(
                    EntityChange(
                        id=int(root_id.int >> 96),  # Simplified ID conversion
                        name=change_wbe.name,
                        change_type="added",
                        budget_delta=change_budgets.get(root_id, Decimal("0")),
                        revenue_delta=change_wbe.revenue_allocation,
                        cost_delta=cost_delta,
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
                        budget_delta=-main_budgets.get(
                            root_id, Decimal("0")
                        ),  # Negative impact
                        revenue_delta=-main_revenue,  # Negative revenue impact
                        cost_delta=cost_delta,
                    )
                )
            else:
                # Exists in both - check for modifications
                budget_delta = change_budgets.get(
                    root_id, Decimal("0")
                ) - main_budgets.get(root_id, Decimal("0"))
                main_revenue = main_wbe.revenue_allocation or Decimal("0")
                change_revenue = change_wbe.revenue_allocation or Decimal("0")
                revenue_delta = change_revenue - main_revenue

                if budget_delta != 0 or revenue_delta != 0 or cost_delta:
                    changes.append(
                        EntityChange(
                            id=int(root_id.int >> 96),
                            name=change_wbe.name,
                            change_type="modified",
                            budget_delta=budget_delta if budget_delta != 0 else None,
                            revenue_delta=revenue_delta if revenue_delta != 0 else None,
                            cost_delta=cost_delta,
                        )
                    )

        return changes

    def _compare_cost_element_lists(
        self,
        main_ces: list[CostElement],
        change_ces: list[CostElement],
        cost_deltas: dict[UUID, Decimal] | None = None,
    ) -> list[EntityChange]:
        """Compare two lists of Cost Elements and identify changes.

        Args:
            main_ces: Cost Elements from main branch
            change_ces: Cost Elements from change branch (merged view)
            cost_deltas: Optional map of cost_element_id -> aggregated cost delta

        Returns:
            List of EntityChange objects
        """
        # Create lookup maps by root ID
        main_ce_map = {ce.cost_element_id: ce for ce in main_ces}
        change_ce_map = {ce.cost_element_id: ce for ce in change_ces}

        changes: list[EntityChange] = []
        all_root_ids = set(main_ce_map.keys()) | set(change_ce_map.keys())
        cost_deltas = cost_deltas or {}

        for root_id in all_root_ids:
            main_ce = main_ce_map.get(root_id)
            change_ce = change_ce_map.get(root_id)
            cost_delta = cost_deltas.get(root_id)

            if main_ce is None:
                # Added in change branch
                assert (
                    change_ce is not None
                )  # Logically: root_id in union but not in main

                # For added entities, show full value as delta
                changes.append(
                    EntityChange(
                        id=int(root_id.int >> 96),
                        name=change_ce.name,
                        change_type="added",
                        budget_delta=change_ce.budget_amount,
                        revenue_delta=None,
                        cost_delta=cost_delta,
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
                        cost_delta=cost_delta,
                    )
                )
            else:
                # Exists in both - check for modifications
                budget_delta = change_ce.budget_amount - main_ce.budget_amount
                if budget_delta != 0 or cost_delta:
                    changes.append(
                        EntityChange(
                            id=int(root_id.int >> 96),
                            name=change_ce.name,
                            change_type="modified",
                            budget_delta=budget_delta if budget_delta != 0 else None,
                            revenue_delta=None,
                            cost_delta=cost_delta,
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
        self, project_id: UUID, branch_name: str, as_of: datetime | None = None
    ) -> list[TimeSeriesData]:
        """Generate 4 time-series datasets for EVM S-curve visualization.

        Context: Generates weekly cumulative values for Budget, Planned Value (PV),
        Earned Value (EV), and Actual Cost (AC) across the project duration.
        Used by the S-Curve Comparison tab in impact analysis to show full EVM
        visibility with MERGE mode comparison between main and change branch.

        Time Machine (as_of):
        - When as_of is provided, filters all temporal data (ProgressEntry, CostRegistration,
          CostElement, ScheduleBaseline, WBE) to include only entities with valid_time
          starting before or at the as_of timestamp
        - When as_of is None, returns current state (no temporal filtering)
        - Edge case: as_of after current date behaves same as as_of=None (all current data)

        Metrics:
        - budget: Cumulative budget allocation (same as PV)
        - pv: Planned Value from schedule baselines (BAC × scheduled %)
        - ev: Earned Value from progress entries (BAC × actual %)
        - ac: Actual Cost from cost registrations (cumulative spend)

        Args:
            project_id: UUID of the project
            branch_name: Name of the change branch (e.g., "BR-CO-2026-001")
            as_of: Time travel timestamp (None = current, past = historical point)

        Returns:
            List of 4 TimeSeriesData objects with metric_names:
            - "budget": Cumulative budget allocation
            - "pv": Planned Value (scheduled work)
            - "ev": Earned Value (completed work)
            - "ac": Actual Cost (incurred costs)

            Returns empty list if no schedule baselines found.
        """
        from app.models.domain.progress_entry import ProgressEntry
        from app.services.progression import get_progression_strategy

        # ========================================================================
        # STEP 1: Get project date range from schedule baselines
        # ========================================================================
        # Query all schedule baselines for cost elements in this project (both branches)
        # CRITICAL: We must join WBE with branch matching CostElement.branch to ensure
        # we get the correct budget_allocation for each branch's WBE version

        # Apply temporal filtering if as_of is specified
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            schedule_stmt = (
                select(ScheduleBaseline, CostElement, WBE)
                .join(
                    CostElement,
                    ScheduleBaseline.schedule_baseline_id
                    == CostElement.schedule_baseline_id,
                )
                .join(
                    WBE,
                    and_(
                        CostElement.wbe_id == WBE.wbe_id,
                        WBE.branch == CostElement.branch,
                    ),
                )
                .where(
                    WBE.project_id == project_id,
                    # ZOMBIE PROTECTION for ScheduleBaseline
                    or_(
                        cast(Any, ScheduleBaseline).deleted_at.is_(None),
                        cast(Any, ScheduleBaseline).deleted_at > as_of,
                    ),
                    # Time machine: Only include schedules/WBEs/CostElements valid at as_of
                    ScheduleBaseline.valid_time.op("@>")(as_of_tstz),
                    func.lower(ScheduleBaseline.valid_time) <= as_of_tstz,
                    # ZOMBIE PROTECTION for WBE
                    or_(
                        cast(Any, WBE).deleted_at.is_(None),
                        cast(Any, WBE).deleted_at > as_of,
                    ),
                    WBE.valid_time.op("@>")(as_of_tstz),
                    func.lower(WBE.valid_time) <= as_of_tstz,
                    # ZOMBIE PROTECTION for CostElement
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                )
            )
        else:
            # No time filtering - get current schedules
            schedule_stmt = (
                select(ScheduleBaseline, CostElement, WBE)
                .join(
                    CostElement,
                    ScheduleBaseline.schedule_baseline_id
                    == CostElement.schedule_baseline_id,
                )
                .join(
                    WBE,
                    and_(
                        CostElement.wbe_id == WBE.wbe_id,
                        WBE.branch == CostElement.branch,
                    ),
                )
                .where(
                    WBE.project_id == project_id,
                    ScheduleBaseline.deleted_at.is_(None),
                    func.upper(ScheduleBaseline.valid_time).is_(None),
                    WBE.deleted_at.is_(None),
                    func.upper(WBE.valid_time).is_(None),
                    CostElement.deleted_at.is_(None),
                    func.upper(CostElement.valid_time).is_(None),
                )
            )

        schedule_result = await self._db.execute(schedule_stmt)
        schedules = schedule_result.all()

        if not schedules:
            # Fallback: If no schedules exist, use simple WBE-based budget calculation
            # This handles projects that haven't set up schedule baselines yet
            return await self._generate_simple_budget_series(
                project_id, branch_name, as_of
            )

        # Separate by CostElement branch (not ScheduleBaseline.branch)
        # ScheduleBaselines are shared across branches (they're in main), but CostElements
        # determine which branch the schedule belongs to for comparison purposes
        main_schedules = [s for s in schedules if s[1].branch == "main"]
        change_schedules = [s for s in schedules if s[1].branch == branch_name]

        if not main_schedules:
            # Fallback: If no main schedules exist, use simple WBE-based budget calculation
            return await self._generate_simple_budget_series(
                project_id, branch_name, as_of
            )

        # ========================================================================
        # STEP 1b: Determine date range for S-curve
        # ========================================================================
        # Prefer project-level dates over schedule baseline dates

        # First, filter valid schedules (needed later in the code)
        valid_main_schedules = [
            s
            for s in main_schedules
            if s[0].start_date is not None and s[0].end_date is not None
        ]

        # Fetch the project's start_date and end_date from the main branch
        project_result = await self._db.execute(
            select(Project).where(
                Project.project_id == project_id,
                Project.branch == "main",
                Project.deleted_at.is_(None),
            )
        )
        project = project_result.scalar_one_or_none()

        # Use project dates if available, otherwise fall back to schedule baseline dates
        if project and project.start_date and project.end_date:
            min_start = project.start_date
            max_end = project.end_date
        else:
            # Fallback to schedule baseline dates
            if not valid_main_schedules:
                return []

            min_start = min(s[0].start_date for s in valid_main_schedules)
            max_end = max(s[0].end_date for s in valid_main_schedules)

        # Cap the time series at the control date (defaults to now when as_of is None)
        control_date = as_of if as_of is not None else datetime.now(UTC)
        max_end = min(max_end, control_date)

        # ========================================================================
        # STEP 2: Batch fetch all required data for EVM calculations
        # ========================================================================
        # Get all cost element IDs for this project (both branches)
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            all_cost_elements_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch.in_(["main", branch_name]),
                    # ZOMBIE PROTECTION for CostElement
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    # Time machine: Only include cost elements valid at as_of
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                )
            )
        else:
            # No time filtering - get current cost elements
            all_cost_elements_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch.in_(["main", branch_name]),
                    func.upper(CostElement.valid_time).is_(None),
                    CostElement.deleted_at.is_(None),
                )
            )
        ce_result = await self._db.execute(all_cost_elements_stmt)
        all_cost_elements = ce_result.scalars().all()

        # Build cost element lookup by (cost_element_id, branch)
        ce_lookup: dict[tuple[UUID, str], CostElement] = {}
        for ce in all_cost_elements:
            ce_lookup[(ce.cost_element_id, ce.branch)] = ce

        # ========================================================================
        # STEP 3: Batch fetch ProgressEntry data for EV calculation
        # ========================================================================
        # ProgressEntry is NOT branchable - need to filter by CostElement.branch
        # We need to join with CostElement to know which branch the progress applies to
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            progress_stmt = (
                select(ProgressEntry, CostElement)
                .join(
                    CostElement,
                    ProgressEntry.cost_element_id == CostElement.cost_element_id,
                )
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch.in_(["main", branch_name]),
                    # ZOMBIE PROTECTION for ProgressEntry
                    or_(
                        ProgressEntry.deleted_at.is_(None),
                        ProgressEntry.deleted_at > as_of,
                    ),
                    # Time machine: Only include progress entries valid at as_of
                    ProgressEntry.valid_time.op("@>")(as_of_tstz),
                    func.lower(ProgressEntry.valid_time) <= as_of_tstz,
                )
            ).order_by(
                CostElement.branch,
                CostElement.cost_element_id,
                func.lower(ProgressEntry.valid_time).desc(),
            )
        else:
            # No time filtering - get current progress entries
            progress_stmt = (
                select(ProgressEntry, CostElement)
                .join(
                    CostElement,
                    ProgressEntry.cost_element_id == CostElement.cost_element_id,
                )
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch.in_(["main", branch_name]),
                    ProgressEntry.deleted_at.is_(None),
                    func.upper(ProgressEntry.valid_time).is_(None),
                )
            ).order_by(
                CostElement.branch,
                CostElement.cost_element_id,
                func.lower(ProgressEntry.valid_time).desc(),
            )

        progress_result = await self._db.execute(progress_stmt)
        progress_rows = progress_result.all()

        # Build progress lookup: (cost_element_id, branch) -> list of ProgressEntry
        # Store ALL progress entries (not just latest) to enable date-based filtering
        # during weekly aggregation, similar to how AC handles cost registrations.
        progress_lookup: dict[tuple[UUID, str], list[ProgressEntry]] = defaultdict(list)
        for pe, ce in progress_rows:
            key = (ce.cost_element_id, ce.branch)
            progress_lookup[key].append(pe)

        # ========================================================================
        # STEP 4: Batch fetch CostRegistration data for AC calculation
        # ========================================================================
        # CostRegistration is NOT branchable - need to filter by CostElement.branch
        # We fetch all registrations and will filter by CostElement.branch when aggregating
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            cost_reg_stmt = (
                select(CostRegistration, CostElement)
                .join(
                    CostElement,
                    CostRegistration.cost_element_id == CostElement.cost_element_id,
                )
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch.in_(["main", branch_name]),
                    # ZOMBIE PROTECTION for CostRegistration
                    or_(
                        CostRegistration.deleted_at.is_(None),
                        CostRegistration.deleted_at > as_of,
                    ),
                    # Time machine: Only include cost registrations valid at as_of
                    CostRegistration.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostRegistration.valid_time) <= as_of_tstz,
                )
            ).order_by(CostRegistration.registration_date)
        else:
            # No time filtering - get current cost registrations
            cost_reg_stmt = (
                select(CostRegistration, CostElement)
                .join(
                    CostElement,
                    CostRegistration.cost_element_id == CostElement.cost_element_id,
                )
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch.in_(["main", branch_name]),
                    CostRegistration.deleted_at.is_(None),
                    func.upper(CostRegistration.valid_time).is_(None),
                )
            ).order_by(CostRegistration.registration_date)

        cost_reg_result = await self._db.execute(cost_reg_stmt)
        cost_reg_rows = cost_reg_result.all()

        # Build cost registration lookup: (cost_element_id, branch) -> list of registrations
        cost_reg_lookup: dict[tuple[UUID, str], list[CostRegistration]] = defaultdict(
            list
        )
        for cr, ce in cost_reg_rows:
            cost_reg_lookup[(ce.cost_element_id, ce.branch)].append(cr)

        # ========================================================================
        # STEP 5: Generate weekly intervals
        # ========================================================================
        weekly_periods = []
        current_week_start = min_start.replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Safety: Limit to 520 weeks (10 years) to prevent performance issues
        max_weeks = 520
        week_count = 0

        while current_week_start <= max_end and week_count < max_weeks:
            week_end = current_week_start + timedelta(days=6)
            weekly_periods.append(
                {"week_start": current_week_start, "week_end": min(week_end, max_end)}
            )
            current_week_start = week_end + timedelta(days=1)
            week_count += 1

        # ========================================================================
        # STEP 6: Calculate metrics for each week
        # ========================================================================
        # We'll calculate all 4 metrics in a single pass through the schedules

        # Initialize time series data for each metric
        budget_series: list[TimeSeriesPoint] = []
        pv_series: list[TimeSeriesPoint] = []
        ev_series: list[TimeSeriesPoint] = []
        ac_series: list[TimeSeriesPoint] = []

        # Pre-group schedules by branch for efficient iteration
        valid_change_schedules = [
            s
            for s in change_schedules
            if s[0].start_date is not None and s[0].end_date is not None
        ]

        # Build WBE ID sets for MERGE mode logic
        main_wbe_ids = {s[2].wbe_id for s in valid_main_schedules}
        change_wbe_ids = {s[2].wbe_id for s in valid_change_schedules}
        only_in_main = main_wbe_ids - change_wbe_ids

        for period in weekly_periods:
            week_start = period["week_start"]
            week_mid = period["week_start"] + timedelta(days=3)
            week_start_date = week_start.date()

            # Initialize accumulators for this week
            main_budget = Decimal("0")
            main_pv = Decimal("0")
            main_ev = Decimal("0")
            main_ac = Decimal("0")

            change_budget = Decimal("0")
            change_pv = Decimal("0")
            change_ev = Decimal("0")
            change_ac = Decimal("0")

            # ------------------------------------------------------------
            # Calculate main branch metrics
            # ------------------------------------------------------------
            for schedule, ce, _wbe in valid_main_schedules:
                budget = ce.budget_amount or Decimal("0")
                if not (schedule.start_date and schedule.end_date):
                    continue

                try:
                    # Budget/PV: Use progression strategy
                    strategy = get_progression_strategy(schedule.progression_type)
                    progress = strategy.calculate_progress(
                        week_mid, schedule.start_date, schedule.end_date
                    )
                    budget_pv = Decimal(str(progress)) * budget

                    main_budget += budget_pv
                    main_pv += budget_pv

                    # EV: Use progress entries (as of week_mid for historical accuracy)
                    progress_entries = progress_lookup.get(
                        (ce.cost_element_id, "main"), []
                    )
                    progress_pct = self._get_progress_as_of(progress_entries, week_mid)
                    ev = budget * progress_pct / Decimal("100")
                    main_ev += ev

                    # AC: Use cost registrations (cumulative up to week_mid)
                    registrations = cost_reg_lookup.get(
                        (ce.cost_element_id, "main"), []
                    )
                    for cr in registrations:
                        if cr.registration_date and cr.registration_date <= week_mid:
                            main_ac += cr.amount

                except ValueError:
                    # Skip invalid date ranges
                    pass

            # ------------------------------------------------------------
            # Calculate change branch metrics
            # ------------------------------------------------------------
            for schedule, ce, _wbe in valid_change_schedules:
                budget = ce.budget_amount or Decimal("0")
                if not (schedule.start_date and schedule.end_date):
                    continue

                try:
                    # Budget/PV: Use progression strategy
                    strategy = get_progression_strategy(schedule.progression_type)
                    progress = strategy.calculate_progress(
                        week_mid, schedule.start_date, schedule.end_date
                    )
                    budget_pv = Decimal(str(progress)) * budget

                    change_budget += budget_pv
                    change_pv += budget_pv

                    # EV: Use progress entries (as of week_mid for historical accuracy)
                    progress_entries = progress_lookup.get(
                        (ce.cost_element_id, branch_name), []
                    )
                    progress_pct = self._get_progress_as_of(progress_entries, week_mid)
                    ev = budget * progress_pct / Decimal("100")
                    change_ev += ev

                    # AC: Use cost registrations
                    registrations = cost_reg_lookup.get(
                        (ce.cost_element_id, branch_name), []
                    )
                    for cr in registrations:
                        if cr.registration_date and cr.registration_date <= week_mid:
                            change_ac += cr.amount

                except ValueError:
                    pass

            # ------------------------------------------------------------
            # MERGE mode: Add unchanged WBEs from main to change
            # ------------------------------------------------------------
            for schedule, ce, wbe in valid_main_schedules:
                if wbe.wbe_id in only_in_main:
                    budget = ce.budget_amount or Decimal("0")
                    if not (schedule.start_date and schedule.end_date):
                        continue

                    try:
                        strategy = get_progression_strategy(schedule.progression_type)
                        progress = strategy.calculate_progress(
                            week_mid, schedule.start_date, schedule.end_date
                        )
                        budget_pv = Decimal(str(progress)) * budget

                        change_budget += budget_pv
                        change_pv += budget_pv

                        # EV: Use progress entries from main (as of week_mid)
                        progress_entries = progress_lookup.get(
                            (ce.cost_element_id, "main"), []
                        )
                        progress_pct = self._get_progress_as_of(
                            progress_entries, week_mid
                        )
                        ev = budget * progress_pct / Decimal("100")
                        change_ev += ev

                        # AC: Use cost registrations from main
                        registrations = cost_reg_lookup.get(
                            (ce.cost_element_id, "main"), []
                        )
                        for cr in registrations:
                            if (
                                cr.registration_date
                                and cr.registration_date <= week_mid
                            ):
                                change_ac += cr.amount

                    except ValueError:
                        pass

            # ------------------------------------------------------------
            # Create time series points for this week
            # ------------------------------------------------------------
            budget_series.append(
                TimeSeriesPoint(
                    week_start=week_start_date,
                    main_value=main_budget,
                    change_value=change_budget,
                )
            )
            pv_series.append(
                TimeSeriesPoint(
                    week_start=week_start_date,
                    main_value=main_pv,
                    change_value=change_pv,
                )
            )
            ev_series.append(
                TimeSeriesPoint(
                    week_start=week_start_date,
                    main_value=main_ev,
                    change_value=change_ev,
                )
            )
            ac_series.append(
                TimeSeriesPoint(
                    week_start=week_start_date,
                    main_value=main_ac,
                    change_value=change_ac,
                )
            )

        # ========================================================================
        # STEP 7: Build and return the 4 time series
        # ========================================================================
        return [
            TimeSeriesData(metric_name="budget", data_points=budget_series),
            TimeSeriesData(metric_name="pv", data_points=pv_series),
            TimeSeriesData(metric_name="ev", data_points=ev_series),
            TimeSeriesData(metric_name="ac", data_points=ac_series),
        ]

    async def _generate_simple_budget_series(
        self, project_id: UUID, branch_name: str, as_of: datetime | None = None
    ) -> list[TimeSeriesData]:
        """Generate simple budget-based time series when no schedules exist.

        Fallback method for projects without schedule baselines.
        Calculates budget totals from WBEs only.

        Args:
            project_id: UUID of the project
            branch_name: Name of the change branch
            as_of: Time travel timestamp (None = current, past = historical point)

        Returns:
            List with single TimeSeriesData for budget metric
        """
        # Get total budget from main branch
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            main_budget_stmt = (
                select(func.sum(CostElement.budget_amount))
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == "main",
                    or_(
                        cast(Any, WBE).deleted_at.is_(None),
                        cast(Any, WBE).deleted_at > as_of,
                    ),
                    WBE.valid_time.op("@>")(as_of_tstz),
                    func.lower(WBE.valid_time) <= as_of_tstz,
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                )
            )
        else:
            main_budget_stmt = (
                select(func.sum(CostElement.budget_amount))
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == "main",
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
            )
        main_budget_result = await self._db.execute(main_budget_stmt)
        main_total = main_budget_result.scalar() or Decimal("0")

        # Get total budget from change branch (merged view)
        if as_of is not None:
            main_ces_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == "main",
                    or_(
                        cast(Any, WBE).deleted_at.is_(None),
                        cast(Any, WBE).deleted_at > as_of,
                    ),
                    WBE.valid_time.op("@>")(as_of_tstz),
                    func.lower(WBE.valid_time) <= as_of_tstz,
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                )
            )
            branch_ces_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == branch_name,
                    or_(
                        cast(Any, WBE).deleted_at.is_(None),
                        cast(Any, WBE).deleted_at > as_of,
                    ),
                    WBE.valid_time.op("@>")(as_of_tstz),
                    func.lower(WBE.valid_time) <= as_of_tstz,
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                )
            )
        else:
            main_ces_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == "main",
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
            )
            branch_ces_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == branch_name,
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
            )

        main_ces_result = await self._db.execute(main_ces_stmt)
        main_ces = {ce.cost_element_id: ce for ce in main_ces_result.scalars().all()}
        branch_ces_result = await self._db.execute(branch_ces_stmt)
        branch_ces = {
            ce.cost_element_id: ce for ce in branch_ces_result.scalars().all()
        }

        merged_total = Decimal("0")
        for ce_id, main_ce in main_ces.items():
            if ce_id in branch_ces:
                merged_total += branch_ces[ce_id].budget_amount or Decimal("0")
            else:
                merged_total += main_ce.budget_amount or Decimal("0")

        for ce_id, branch_ce in branch_ces.items():
            if ce_id not in main_ces:
                merged_total += branch_ce.budget_amount or Decimal("0")

        change_total = merged_total

        # Return as a single time point (current week)
        current_week_start = datetime.now(UTC).date()

        budget_point = TimeSeriesPoint(
            week_start=current_week_start,
            main_value=main_total,
            change_value=change_total,
        )

        return [
            TimeSeriesData(
                metric_name="budget",
                data_points=[budget_point],
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

    async def _fetch_and_compare_schedule_baselines(
        self,
        project_id: UUID,
        branch_name: str,
        branch_mode: BranchMode = BranchMode.MERGE,
        as_of: datetime | None = None,
    ) -> dict[str, KPIMetric | None]:
        """Fetch and compare schedule baselines between main and change branches.

        Args:
            project_id: UUID of the project
            branch_name: Name of the change branch
            branch_mode: MERGE mode calculates merged values, STRICT mode calculates isolated values
            as_of: Time travel timestamp (None = current, past = historical point)

        Returns:
            Dictionary with schedule_start_date, schedule_end_date, schedule_duration KPIMetrics
            Returns None for all fields if schedule baselines not found
        """
        # Get all cost elements for the project (both branches)
        # We need to find schedule baselines via cost elements

        # Fetch cost elements from main branch with temporal filtering
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            main_ce_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == "main",
                    # Zombie protection for WBE
                    or_(
                        cast(Any, WBE).deleted_at.is_(None),
                        cast(Any, WBE).deleted_at > as_of,
                    ),
                    # Time travel for WBE
                    WBE.valid_time.op("@>")(as_of_tstz),
                    func.lower(WBE.valid_time) <= as_of_tstz,
                    # Zombie protection for CostElement
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    # Time travel for CostElement
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                )
            )
            change_ce_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == branch_name,
                    # Zombie protection for WBE
                    or_(
                        cast(Any, WBE).deleted_at.is_(None),
                        cast(Any, WBE).deleted_at > as_of,
                    ),
                    # Time travel for WBE
                    WBE.valid_time.op("@>")(as_of_tstz),
                    func.lower(WBE.valid_time) <= as_of_tstz,
                    # Zombie protection for CostElement
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    # Time travel for CostElement
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                )
            )
        else:
            # Current version query
            main_ce_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == "main",
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                )
            )
            change_ce_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == branch_name,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                )
            )
        main_ce_result = await self._db.execute(main_ce_stmt)
        main_cost_elements = main_ce_result.scalars().all()

        change_ce_result = await self._db.execute(change_ce_stmt)
        change_cost_elements = change_ce_result.scalars().all()

        # If no cost elements in either branch, return None
        if not main_cost_elements and not change_cost_elements:
            return {
                "schedule_start_date": None,
                "schedule_end_date": None,
                "schedule_duration": None,
            }

        # Get schedule baselines from cost elements
        main_baseline_ids = [
            ce.schedule_baseline_id
            for ce in main_cost_elements
            if ce.schedule_baseline_id
        ]
        change_baseline_ids = [
            ce.schedule_baseline_id
            for ce in change_cost_elements
            if ce.schedule_baseline_id
        ]

        # Fetch schedule baselines with temporal filtering
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            if main_baseline_ids:
                main_sb_stmt = select(ScheduleBaseline).where(
                    ScheduleBaseline.schedule_baseline_id.in_(main_baseline_ids),
                    ScheduleBaseline.branch == "main",
                    # Zombie protection
                    or_(
                        cast(Any, ScheduleBaseline).deleted_at.is_(None),
                        cast(Any, ScheduleBaseline).deleted_at > as_of,
                    ),
                    # Time travel
                    ScheduleBaseline.valid_time.op("@>")(as_of_tstz),
                    func.lower(ScheduleBaseline.valid_time) <= as_of_tstz,
                )
                main_sb_result = await self._db.execute(main_sb_stmt)
                main_schedule_baselines = main_sb_result.scalars().all()
            else:
                main_schedule_baselines = []

            if change_baseline_ids:
                change_sb_stmt = select(ScheduleBaseline).where(
                    ScheduleBaseline.schedule_baseline_id.in_(change_baseline_ids),
                    ScheduleBaseline.branch == branch_name,
                    # Zombie protection
                    or_(
                        cast(Any, ScheduleBaseline).deleted_at.is_(None),
                        cast(Any, ScheduleBaseline).deleted_at > as_of,
                    ),
                    # Time travel
                    ScheduleBaseline.valid_time.op("@>")(as_of_tstz),
                    func.lower(ScheduleBaseline.valid_time) <= as_of_tstz,
                )
                change_sb_result = await self._db.execute(change_sb_stmt)
                change_schedule_baselines = change_sb_result.scalars().all()
            else:
                change_schedule_baselines = []
        else:
            # Current version query
            if main_baseline_ids:
                main_sb_stmt = select(ScheduleBaseline).where(
                    ScheduleBaseline.schedule_baseline_id.in_(main_baseline_ids),
                    ScheduleBaseline.branch == "main",
                    func.upper(cast(Any, ScheduleBaseline).valid_time).is_(None),
                    cast(Any, ScheduleBaseline).deleted_at.is_(None),
                )
                main_sb_result = await self._db.execute(main_sb_stmt)
                main_schedule_baselines = main_sb_result.scalars().all()
            else:
                main_schedule_baselines = []

            if change_baseline_ids:
                change_sb_stmt = select(ScheduleBaseline).where(
                    ScheduleBaseline.schedule_baseline_id.in_(change_baseline_ids),
                    ScheduleBaseline.branch == branch_name,
                    func.upper(cast(Any, ScheduleBaseline).valid_time).is_(None),
                    cast(Any, ScheduleBaseline).deleted_at.is_(None),
                )
                change_sb_result = await self._db.execute(change_sb_stmt)
                change_schedule_baselines = change_sb_result.scalars().all()
            else:
                change_schedule_baselines = []

        # If no schedule baselines found, return None
        if not main_schedule_baselines and not change_schedule_baselines:
            return {
                "schedule_start_date": None,
                "schedule_end_date": None,
                "schedule_duration": None,
            }

        # Aggregate schedule data (use min start, max end for project-level view)
        # For main branch
        if main_schedule_baselines:
            main_start = min(sb.start_date for sb in main_schedule_baselines)
            main_end = max(sb.end_date for sb in main_schedule_baselines)
            main_duration = (main_end - main_start).days
        else:
            main_start = datetime.now(UTC)
            main_end = datetime.now(UTC)
            main_duration = 0

        # For change branch
        if change_schedule_baselines:
            change_start = min(sb.start_date for sb in change_schedule_baselines)
            change_end = max(sb.end_date for sb in change_schedule_baselines)
            change_duration = (change_end - change_start).days
        else:
            # Use main branch values if no change branch baselines
            change_start = main_start
            change_end = main_end
            change_duration = main_duration

        # Convert to KPIMetric format
        # For dates, we store timestamps as Decimal (Unix timestamp)
        def _calculate_date_metric(main_dt: datetime, change_dt: datetime) -> KPIMetric:
            """Calculate date metric as Unix timestamp."""
            main_ts = Decimal(str(int(main_dt.timestamp())))
            change_ts = Decimal(str(int(change_dt.timestamp())))
            delta = change_ts - main_ts
            # Percent change for dates doesn't make sense, set to None

            # Calculate merged value when in MERGE mode
            merged_value = None
            if branch_mode == BranchMode.MERGE:
                merged_value = main_ts + delta

            return KPIMetric(
                main_value=main_ts,
                change_value=change_ts,
                merged_value=merged_value,
                delta=delta,
                delta_percent=None,
            )

        def _calculate_duration_metric(main_dur: int, change_dur: int) -> KPIMetric:
            """Calculate duration metric in days."""
            delta = Decimal(str(change_dur - main_dur))
            delta_percent = (
                float((change_dur - main_dur) / main_dur * 100)
                if main_dur > 0
                else None
            )

            # Calculate merged value when in MERGE mode
            merged_value = None
            if branch_mode == BranchMode.MERGE:
                merged_value = Decimal(str(main_dur)) + delta

            return KPIMetric(
                main_value=Decimal(str(main_dur)),
                change_value=Decimal(str(change_dur)),
                merged_value=merged_value,
                delta=delta,
                delta_percent=delta_percent,
            )

        return {
            "schedule_start_date": _calculate_date_metric(main_start, change_start),
            "schedule_end_date": _calculate_date_metric(main_end, change_end),
            "schedule_duration": _calculate_duration_metric(
                main_duration, change_duration
            ),
        }

    async def _fetch_and_compare_evm_metrics(
        self,
        project_id: UUID,
        branch_name: str,
        branch_mode: BranchMode = BranchMode.MERGE,
        as_of: datetime | None = None,
    ) -> dict[str, KPIMetric | None]:
        """Fetch and compare EVM metrics between main and change branches.

        Args:
            project_id: UUID of the project
            branch_name: Name of the change branch
            branch_mode: MERGE mode calculates merged values, STRICT mode calculates isolated values
            as_of: Time travel timestamp (None = current, past = historical point)

        Returns:
            Dictionary with cpi, spi, tcpi, eac, vac KPIMetrics
            Returns None for all fields if EVM calculation fails
        """
        try:
            # Calculate EVM metrics for main branch
            control_date = as_of if as_of is not None else datetime.now(UTC)
            main_evm_response = await self._evm_service.calculate_evm_metrics_batch(
                entity_type=EntityType.PROJECT,
                entity_ids=[project_id],
                control_date=control_date,
                branch="main",
                branch_mode=BranchMode.MERGE,
            )

            # Calculate EVM metrics for change branch
            change_evm_response = await self._evm_service.calculate_evm_metrics_batch(
                entity_type=EntityType.PROJECT,
                entity_ids=[project_id],
                control_date=control_date,
                branch=branch_name,
                branch_mode=BranchMode.MERGE,
            )

            # Extract metrics (convert to Decimal to ensure type safety)
            main_cpi = (
                Decimal(str(main_evm_response.cpi))
                if main_evm_response.cpi is not None
                else Decimal("1.0")
            )
            change_cpi = (
                Decimal(str(change_evm_response.cpi))
                if change_evm_response.cpi is not None
                else Decimal("1.0")
            )

            main_spi = (
                Decimal(str(main_evm_response.spi))
                if main_evm_response.spi is not None
                else Decimal("1.0")
            )
            change_spi = (
                Decimal(str(change_evm_response.spi))
                if change_evm_response.spi is not None
                else Decimal("1.0")
            )

            # TCPI calculation (simplified: BAC / EAC if EAC exists)
            main_eac_for_tcpi = (
                Decimal(str(main_evm_response.eac))
                if main_evm_response.eac is not None
                else None
            )
            main_tcpi = (
                Decimal("1.0")
                if main_eac_for_tcpi is None or main_eac_for_tcpi == 0
                else Decimal(str(main_evm_response.bac)) / main_eac_for_tcpi
            )
            change_eac_for_tcpi = (
                Decimal(str(change_evm_response.eac))
                if change_evm_response.eac is not None
                else None
            )
            change_tcpi = (
                Decimal("1.0")
                if change_eac_for_tcpi is None or change_eac_for_tcpi == 0
                else Decimal(str(change_evm_response.bac)) / change_eac_for_tcpi
            )

            main_eac = (
                Decimal(str(main_evm_response.eac))
                if main_evm_response.eac is not None
                else Decimal(str(main_evm_response.bac))
            )
            change_eac = (
                Decimal(str(change_evm_response.eac))
                if change_evm_response.eac is not None
                else Decimal(str(change_evm_response.bac))
            )

            # Calculate VAC (ensure Decimal)
            main_bac_dec = Decimal(str(main_evm_response.bac))
            change_bac_dec = Decimal(str(change_evm_response.bac))
            main_vac = main_bac_dec - main_eac
            change_vac = change_bac_dec - change_eac

            # Convert to KPIMetric format
            def _calculate_metric(main_val: Decimal, change_val: Decimal) -> KPIMetric:
                """Calculate metric KPIMetric."""
                delta = change_val - main_val
                delta_percent = float(delta / main_val * 100) if main_val != 0 else None

                # Calculate merged value when in MERGE mode
                merged_value = None
                if branch_mode == BranchMode.MERGE:
                    # If change branch has no data (equals 0 when main > 0), it means "no changes"
                    # In this case, merged value should equal main value
                    if change_val == 0 and main_val > 0:
                        merged_value = main_val  # No changes - merged equals main
                    else:
                        merged_value = main_val + delta  # Normal merge calculation

                return KPIMetric(
                    main_value=main_val,
                    change_value=change_val,
                    merged_value=merged_value,
                    delta=delta,
                    delta_percent=delta_percent,
                )

            return {
                "cpi": _calculate_metric(main_cpi, change_cpi),
                "spi": _calculate_metric(main_spi, change_spi),
                "tcpi": _calculate_metric(main_tcpi, change_tcpi),
                "eac": _calculate_metric(main_eac, change_eac),
                "vac": _calculate_metric(main_vac, change_vac),
            }

        except Exception:
            # If EVM calculation fails, return None for all metrics
            return {
                "cpi": None,
                "spi": None,
                "tcpi": None,
                "eac": None,
                "vac": None,
            }

    async def _compare_forecasts(
        self, project_id: UUID, branch_name: str, as_of: datetime | None = None
    ) -> ForecastChanges | None:
        """Compare forecasts between main and change branches using MERGE mode.

        Builds a merged forecast view where branch forecasts override main forecasts,
        then compares main vs merged to identify changes.

        Time Machine (as_of):
        - When as_of is provided, filters all temporal data (CostElement, Forecast)
          to include only entities with valid_time starting before or at the as_of timestamp
        - When as_of is None, returns current state (no temporal filtering)

        Returns:
            ForecastChanges with EAC comparisons for cost elements with forecast changes.
            Only returns forecasts that have been added, modified, or removed.
        """
        from app.services.forecast_service import ForecastService

        forecast_service = ForecastService(self._db)

        # ========================================
        # STEP 1: Get cost elements using proper temporal filtering
        # ========================================
        # Use sql_cast for consistency with time-travel pattern
        if as_of is not None:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            main_ce_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == "main",
                    # Zombie protection: Entity visible if not deleted, or deleted AFTER as_of
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                )
                .order_by(cast(Any, CostElement).valid_time.desc())
            )
            change_ce_stmt = (
                select(CostElement)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    CostElement.branch == branch_name,
                    # Zombie protection
                    or_(
                        cast(Any, CostElement).deleted_at.is_(None),
                        cast(Any, CostElement).deleted_at > as_of,
                    ),
                    CostElement.valid_time.op("@>")(as_of_tstz),
                    func.lower(CostElement.valid_time) <= as_of_tstz,
                )
                .order_by(cast(Any, CostElement).valid_time.desc())
            )
        else:
            # No time filtering - get current cost elements
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

        main_ce_result = await self._db.execute(main_ce_stmt)
        main_cost_elements = main_ce_result.scalars().all()

        change_ce_result = await self._db.execute(change_ce_stmt)
        change_cost_elements = change_ce_result.scalars().all()

        # If no cost elements in either branch, return None
        if not main_cost_elements and not change_cost_elements:
            return None

        # ========================================
        # STEP 2: Get forecasts with as_of support
        # ========================================
        main_ce_ids = [ce.cost_element_id for ce in main_cost_elements]
        main_forecasts = await forecast_service.get_forecasts_for_cost_elements(
            main_ce_ids, branch="main", as_of=as_of
        )

        change_ce_ids = [ce.cost_element_id for ce in change_cost_elements]
        change_forecasts = await forecast_service.get_forecasts_for_cost_elements(
            change_ce_ids, branch=branch_name, as_of=as_of
        )

        # ========================================
        # STEP 3: Build merged forecast view (MERGE MODE)
        # ========================================
        # Key: Branch forecasts override main forecasts; main forecasts are inherited
        merged_forecasts: dict[UUID, Forecast] = {}

        # First, add all main forecasts to merged view (base layer)
        for ce_id, forecast in main_forecasts.items():
            merged_forecasts[ce_id] = forecast

        # Then, override with branch forecasts (branch takes precedence)
        for ce_id, forecast in change_forecasts.items():
            merged_forecasts[ce_id] = forecast

        # ========================================
        # STEP 4: Compare main vs merged view to identify changes
        # ========================================
        main_ce_map = {ce.cost_element_id: ce for ce in main_cost_elements}
        change_ce_map = {ce.cost_element_id: ce for ce in change_cost_elements}

        comparisons: list[ForecastComparison] = []
        all_ce_ids = set(main_ce_map.keys()) | set(change_ce_map.keys())

        for ce_id in all_ce_ids:
            ce = change_ce_map.get(ce_id) or main_ce_map.get(ce_id)
            if not ce:
                continue

            main_fcast = main_forecasts.get(ce_id)
            merged_fcast = merged_forecasts.get(ce_id)

            # Determine change type
            is_added = main_fcast is None and merged_fcast is not None
            is_removed = main_fcast is not None and merged_fcast is None
            is_modified = (
                main_fcast is not None
                and merged_fcast is not None
                and main_fcast.eac_amount != merged_fcast.eac_amount
            )

            # Only include if there's a change
            if is_added or is_removed or is_modified:
                # Get actual branch forecast for frontend compatibility
                # (may be None if removed, or the branch forecast otherwise)
                branch_fcast_for_frontend = change_forecasts.get(ce_id)

                comparisons.append(
                    ForecastComparison(
                        cost_element_id=ce_id,
                        cost_element_code=ce.code,
                        cost_element_name=ce.name,
                        budget_amount=ce.budget_amount,
                        main_eac=main_fcast.eac_amount if main_fcast else None,
                        main_forecast=ForecastRead.model_validate(main_fcast)
                        if main_fcast
                        else None,
                        change_eac=merged_fcast.eac_amount if merged_fcast else None,
                        branch_forecast=ForecastRead.model_validate(
                            branch_fcast_for_frontend
                        )
                        if branch_fcast_for_frontend
                        else None,
                    )
                )

        if not comparisons:
            return None

        return ForecastChanges(forecasts=comparisons)
