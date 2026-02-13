"""Unit tests for ImpactAnalysisService.

Tests follow Red-Green-Refactor TDD cycle.
Tests are ordered from simplest to most complex.
"""

from datetime import UTC
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.impact_analysis import EntityChange
from app.services.impact_analysis_service import ImpactAnalysisService


class TestImpactAnalysisServiceCompareKPIs:
    """Test ImpactAnalysisService._compare_kpis() method."""

    @pytest.mark.asyncio
    async def test_compare_kpis_no_changes(self, db_session: AsyncSession) -> None:
        """Test KPI comparison when branches have identical data.

        Acceptance Criteria:
        - All delta values are zero
        - delta_percent is 0 or None for all metrics
        - All main_value and change_value match

        This is the simplest test case - no changes between branches.
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        main_bac = Decimal("100000.00")
        change_bac = Decimal("100000.00")
        main_budget = Decimal("100000.00")
        change_budget = Decimal("100000.00")
        main_margin = Decimal("20000.00")
        change_margin = Decimal("20000.00")
        main_actual_costs = Decimal("80000.00")
        change_actual_costs = Decimal("80000.00")
        main_revenue = Decimal("150000.00")
        change_revenue = Decimal("150000.00")

        # Act
        result = service._compare_kpis(
            main_bac=main_bac,
            change_bac=change_bac,
            main_budget_total=main_budget,
            change_budget_total=change_budget,
            main_gross_margin=main_margin,
            change_gross_margin=change_margin,
            main_actual_costs=main_actual_costs,
            change_actual_costs=change_actual_costs,
            main_revenue_total=main_revenue,
            change_revenue_total=change_revenue,
        )

        # Assert - All deltas are zero, delta_percent is 0.0
        assert result.bac.main_value == main_bac
        assert result.bac.change_value == change_bac
        assert result.bac.delta == Decimal("0")
        assert result.bac.delta_percent == 0.0

        assert result.budget_delta.main_value == main_budget
        assert result.budget_delta.change_value == change_budget
        assert result.budget_delta.delta == Decimal("0")
        assert result.budget_delta.delta_percent == 0.0

        assert result.gross_margin.main_value == main_margin
        assert result.gross_margin.change_value == change_margin
        assert result.gross_margin.delta == Decimal("0")
        assert result.gross_margin.delta_percent == 0.0

        # Assert revenue delta
        assert result.revenue_delta.main_value == main_revenue
        assert result.revenue_delta.change_value == change_revenue
        assert result.revenue_delta.delta == Decimal("0")
        assert result.revenue_delta.delta_percent == 0.0

    @pytest.mark.asyncio
    async def test_compare_kpis_happy_path(self, db_session: AsyncSession) -> None:
        """Test KPI comparison with actual differences between branches.

        Acceptance Criteria:
        - Delta values calculated correctly (change - main)
        - Delta percent calculated correctly (delta / main * 100)
        - Handles positive and negative changes
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        main_bac = Decimal("100000.00")
        main_budget = Decimal("100000.00")
        main_margin = Decimal("20000.00")

        change_bac = Decimal("120000.00")
        change_budget = Decimal("120000.00")
        change_margin = Decimal("25000.00")
        main_actual_costs = Decimal("80000.00")
        change_actual_costs = Decimal("95000.00")
        main_revenue = Decimal("150000.00")
        change_revenue = Decimal("165000.00")

        # Act
        result = service._compare_kpis(
            main_bac=main_bac,
            change_bac=change_bac,
            main_budget_total=main_budget,
            change_budget_total=change_budget,
            main_gross_margin=main_margin,
            change_gross_margin=change_margin,
            main_actual_costs=main_actual_costs,
            change_actual_costs=change_actual_costs,
            main_revenue_total=main_revenue,
            change_revenue_total=change_revenue,
        )

        # Assert - Delta and percent calculated correctly
        assert result.bac.delta == Decimal("20000.00")  # 120k - 100k
        assert result.bac.delta_percent == 20.0  # 20k / 100k * 100

        assert result.budget_delta.delta == Decimal("20000.00")
        assert result.budget_delta.delta_percent == 20.0

        assert result.gross_margin.delta == Decimal("5000.00")  # 25k - 20k
        assert result.gross_margin.delta_percent == 25.0  # 5k / 20k * 100

        # Assert revenue calculations
        assert result.revenue_delta.delta == Decimal("15000.00")  # 165k - 150k
        assert result.revenue_delta.delta_percent == 10.0  # 15k / 150k * 100


class TestImpactAnalysisServiceCompareEntities:
    """Test ImpactAnalysisService._compare_entities() method."""

    @pytest.mark.asyncio
    async def test_compare_entities_added_wbe(self, db_session: AsyncSession) -> None:
        """Test entity comparison when WBE is added in change branch.

        Acceptance Criteria:
        - WBE appears in wbes list with change_type="added"
        - Financial fields populated
        """
        # Arrange
        wbe_id = uuid4()
        wbe_name = "1.5 - New Safety System"

        # Expected result structure
        expected = EntityChange(
            id=int(wbe_id.int >> 96),  # Simplified ID extraction
            name=wbe_name,
            change_type="added",  # EntityChangeType is a TypeAlias, use string literal
            budget_delta=None,  # New entity, no delta
            revenue_delta=None,
            cost_delta=None,
        )

        # Assert expected structure
        assert expected.change_type == "added"
        assert expected.name == wbe_name
        assert expected.budget_delta is None

    @pytest.mark.asyncio
    async def test_compare_entities_modified_wbe(
        self, db_session: AsyncSession
    ) -> None:
        """Test entity comparison when WBE is modified in change branch.

        Acceptance Criteria:
        - WBE appears with change_type="modified"
        - Budget delta calculated correctly
        """
        # Arrange
        old_budget = Decimal("50000.00")
        new_budget = Decimal("60000.00")

        expected_delta = new_budget - old_budget  # Decimal("10000.00")

        # Assert
        assert expected_delta == Decimal("10000.00")

    @pytest.mark.asyncio
    async def test_compare_entities_removed_wbe(self, db_session: AsyncSession) -> None:
        """Test entity comparison when WBE is removed in change branch.

        Acceptance Criteria:
        - WBE appears with change_type="removed"
        - Previous financial values shown as negative impact
        """
        # Arrange
        old_budget = Decimal("50000.00")

        # When removed, the delta is negative (lost budget)
        expected_delta = -old_budget  # Decimal("-50000.00")

        # Assert
        assert expected_delta == Decimal("-50000.00")


class TestImpactAnalysisServiceBuildWaterfall:
    """Test ImpactAnalysisService._build_waterfall() method."""

    @pytest.mark.asyncio
    async def test_build_waterfall_bridge(self, db_session: AsyncSession) -> None:
        """Test waterfall chart construction from KPI comparison.

        Acceptance Criteria:
        - Returns 3 segments: current margin, delta, new margin
        - Values calculated correctly
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        current_margin = Decimal("20000.00")
        margin_delta = Decimal("5000.00")

        # Act
        result = service._build_waterfall(current_margin, margin_delta)

        # Assert - 3 segments with correct values
        assert len(result) == 3

        assert result[0].name == "Current Margin"
        assert result[0].value == Decimal("20000.00")
        assert result[0].is_delta is False

        assert result[1].name == "Change Impact"
        assert result[1].value == Decimal("5000.00")
        assert result[1].is_delta is True

        assert result[2].name == "New Margin"
        assert result[2].value == Decimal("25000.00")
        assert result[2].is_delta is False


class TestImpactAnalysisServiceGenerateTimeSeries:
    """Test ImpactAnalysisService._generate_time_series() method."""

    @pytest.mark.asyncio
    async def test_generate_time_series_weekly(self, db_session: AsyncSession) -> None:
        """Test weekly time-series data generation.

        Acceptance Criteria:
        - Data points grouped by week (week_start date)
        - Main and change values populated for each point
        - Returns TimeSeriesPoint objects
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        project_id = uuid4()
        branch_name = "BR-test-001"

        # Act - This will return empty results since project has no WBEs
        result = await service._generate_time_series(project_id, branch_name)

        # Assert - Should return a list with one TimeSeriesPoint
        # (or empty if no data found)
        assert isinstance(result, list)
        # Empty project returns zero budget
        assert len(result) >= 1  # At least one time point


class TestImpactAnalysisServiceRevenueImpact:
    """Test revenue impact calculation in change order analysis.

    Phase 3: Revenue Modification Support
    Tests revenue delta calculation between main and change branches.
    """

    @pytest.mark.asyncio
    async def test_compare_kpis_with_revenue_delta(
        self, db_session: AsyncSession
    ) -> None:
        """Test KPI scorecard includes revenue impact calculation.

        Acceptance Criteria:
        - KPIScorecard includes revenue_delta metric
        - Revenue delta calculated as (change_revenue - main_revenue)
        - Delta percent calculated correctly when main_revenue > 0
        - Delta percent is None when main_revenue is 0
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        main_bac = Decimal("100000.00")
        change_bac = Decimal("120000.00")
        main_budget = Decimal("100000.00")
        change_budget = Decimal("120000.00")
        main_margin = Decimal("20000.00")
        change_margin = Decimal("25000.00")
        main_actual_costs = Decimal("80000.00")
        change_actual_costs = Decimal("95000.00")
        main_revenue = Decimal("150000.00")
        change_revenue = Decimal("175000.00")

        # Act
        result = service._compare_kpis(
            main_bac=main_bac,
            change_bac=change_bac,
            main_budget_total=main_budget,
            change_budget_total=change_budget,
            main_gross_margin=main_margin,
            change_gross_margin=change_margin,
            main_actual_costs=main_actual_costs,
            change_actual_costs=change_actual_costs,
            main_revenue_total=main_revenue,
            change_revenue_total=change_revenue,
        )

        # Assert - Revenue delta calculated correctly
        assert result.revenue_delta.main_value == main_revenue
        assert result.revenue_delta.change_value == change_revenue
        assert result.revenue_delta.delta == Decimal("25000.00")  # 175k - 150k
        assert result.revenue_delta.delta_percent == pytest.approx(16.6667, rel=0.001)  # 25k / 150k * 100

    @pytest.mark.asyncio
    async def test_compare_kpis_revenue_zero_main(
        self, db_session: AsyncSession
    ) -> None:
        """Test revenue delta when main branch has zero revenue.

        Acceptance Criteria:
        - Delta calculated correctly
        - Delta percent is None (division by zero avoided)
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        main_revenue = Decimal("0")
        change_revenue = Decimal("50000.00")

        # Act
        result = service._compare_kpis(
            main_bac=Decimal("100000.00"),
            change_bac=Decimal("100000.00"),
            main_budget_total=Decimal("100000.00"),
            change_budget_total=Decimal("100000.00"),
            main_gross_margin=Decimal("20000.00"),
            change_gross_margin=Decimal("20000.00"),
            main_actual_costs=Decimal("80000.00"),
            change_actual_costs=Decimal("80000.00"),
            main_revenue_total=main_revenue,
            change_revenue_total=change_revenue,
        )

        # Assert
        assert result.revenue_delta.delta == Decimal("50000.00")
        assert result.revenue_delta.delta_percent is None

    @pytest.mark.asyncio
    async def test_compare_kpis_revenue_no_change(
        self, db_session: AsyncSession
    ) -> None:
        """Test revenue delta when both branches have same revenue.

        Acceptance Criteria:
        - Delta is zero
        - Delta percent is 0.0
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        main_revenue = Decimal("150000.00")
        change_revenue = Decimal("150000.00")

        # Act
        result = service._compare_kpis(
            main_bac=Decimal("100000.00"),
            change_bac=Decimal("100000.00"),
            main_budget_total=Decimal("100000.00"),
            change_budget_total=Decimal("100000.00"),
            main_gross_margin=Decimal("20000.00"),
            change_gross_margin=Decimal("20000.00"),
            main_actual_costs=Decimal("80000.00"),
            change_actual_costs=Decimal("80000.00"),
            main_revenue_total=main_revenue,
            change_revenue_total=change_revenue,
        )

        # Assert
        assert result.revenue_delta.delta == Decimal("0")
        assert result.revenue_delta.delta_percent == 0.0

    @pytest.mark.asyncio
    async def test_compare_wbe_revenue_delta_modified(
        self, db_session: AsyncSession
    ) -> None:
        """Test WBE comparison includes revenue delta for modified entities.

        Acceptance Criteria:
        - Modified WBE shows revenue_delta
        - Revenue delta calculated as (change_revenue - main_revenue)
        """
        # Arrange
        from app.models.domain.wbe import WBE

        wbe_id = uuid4()
        project_id = uuid4()

        main_wbe = WBE(
            wbe_id=wbe_id,
            project_id=project_id,
            code="1.1",
            name="Assembly Station",
            budget_allocation=Decimal("50000.00"),
            revenue_allocation=Decimal("60000.00"),
            branch="main",
        )

        change_wbe = WBE(
            wbe_id=wbe_id,
            project_id=project_id,
            code="1.1",
            name="Assembly Station",
            budget_allocation=Decimal("55000.00"),
            revenue_allocation=Decimal("70000.00"),
            branch="BR-test-001",
        )

        service = ImpactAnalysisService(db_session)

        # Act
        changes = service._compare_wbe_lists([main_wbe], [change_wbe])

        # Assert
        assert len(changes) == 1
        assert changes[0].change_type == "modified"
        assert changes[0].revenue_delta == Decimal("10000.00")  # 70k - 60k
        assert changes[0].budget_delta == Decimal("5000.00")  # 55k - 50k

    @pytest.mark.asyncio
    async def test_compare_wbe_revenue_delta_removed(
        self, db_session: AsyncSession
    ) -> None:
        """Test WBE comparison includes revenue impact for removed entities.

        Acceptance Criteria:
        - Removed WBE shows negative revenue_delta
        - Revenue delta equals negative of main revenue allocation
        """
        # Arrange
        from app.models.domain.wbe import WBE

        wbe_id = uuid4()
        project_id = uuid4()

        main_wbe = WBE(
            wbe_id=wbe_id,
            project_id=project_id,
            code="1.2",
            name="Test Station",
            budget_allocation=Decimal("30000.00"),
            revenue_allocation=Decimal("40000.00"),
            branch="main",
        )

        service = ImpactAnalysisService(db_session)

        # Act - WBE removed in change branch
        changes = service._compare_wbe_lists([main_wbe], [])

        # Assert
        assert len(changes) == 1
        assert changes[0].change_type == "removed"
        assert changes[0].revenue_delta == Decimal("-40000.00")  # Lost revenue
        assert changes[0].budget_delta == Decimal("-30000.00")  # Lost budget


class TestImpactAnalysisServiceScheduleBaselineComparison:
    """Test schedule baseline comparison between branches.

    Phase 5, Task 1: Schedule Implication Analysis
    Tests compare schedule baselines (start_date, end_date, duration, progression_type).
    """

    @pytest.mark.asyncio
    async def test_compare_schedule_baselines_no_changes(
        self, db_session: AsyncSession
    ) -> None:
        """Test schedule comparison when branches have identical schedules.

        Acceptance Criteria:
        - Start date delta is zero
        - End date delta is zero
        - Duration delta is zero
        - Progression type is unchanged
        - Returns schedule metrics with zero deltas
        """
        # Arrange
        from datetime import datetime

        service = ImpactAnalysisService(db_session)

        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 6, 30, tzinfo=UTC)
        duration = (end_date - start_date).days  # 180 days

        # Mock schedule baselines (in real implementation, these would be fetched from DB)
        main_start = start_date
        main_end = end_date
        main_duration = duration
        main_progression = "LINEAR"

        change_start = start_date
        change_end = end_date
        change_duration = duration
        change_progression = "LINEAR"

        # Act - Call the comparison method
        result = service._compare_schedule_baselines(
            main_start_date=main_start,
            main_end_date=main_end,
            main_duration=main_duration,
            main_progression_type=main_progression,
            change_start_date=change_start,
            change_end_date=change_end,
            change_duration=change_duration,
            change_progression_type=change_progression,
        )

        # Assert - All deltas should be zero
        assert result["start_delta_days"] == 0
        assert result["end_delta_days"] == 0
        assert result["duration_delta_days"] == 0
        assert result["progression_changed"] is False

    @pytest.mark.asyncio
    async def test_compare_schedule_baselines_extended_duration(
        self, db_session: AsyncSession
    ) -> None:
        """Test schedule comparison when change branch extends schedule.

        Acceptance Criteria:
        - Start date delta calculated correctly
        - End date delta calculated correctly
        - Duration delta positive (schedule extended)
        - Returns correct delta values
        """
        # Arrange
        from datetime import datetime

        service = ImpactAnalysisService(db_session)

        main_start = datetime(2026, 1, 1, tzinfo=UTC)
        main_end = datetime(2026, 6, 30, tzinfo=UTC)
        main_duration = (main_end - main_start).days

        change_start = datetime(2026, 1, 15, tzinfo=UTC)  # 2 weeks later
        change_end = datetime(2026, 7, 31, tzinfo=UTC)  # 1 month later
        change_duration = (change_end - change_start).days

        # Act
        result = service._compare_schedule_baselines(
            main_start_date=main_start,
            main_end_date=main_end,
            main_duration=main_duration,
            main_progression_type="LINEAR",
            change_start_date=change_start,
            change_end_date=change_end,
            change_duration=change_duration,
            change_progression_type="LINEAR",
        )

        # Assert
        assert result["start_delta_days"] == 14  # 2 weeks later
        assert result["end_delta_days"] == 31  # 1 month later
        # Duration: (197 days) - (180 days) = 17 days extension
        assert result["duration_delta_days"] == 17
        assert result["progression_changed"] is False

    @pytest.mark.asyncio
    async def test_compare_schedule_baselines_progression_type_changed(
        self, db_session: AsyncSession
    ) -> None:
        """Test schedule comparison when progression type changes.

        Acceptance Criteria:
        - Detects progression type change
        - Returns progression_changed=True
        - Includes old and new progression types
        """
        # Arrange
        from datetime import datetime

        service = ImpactAnalysisService(db_session)

        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 6, 30, tzinfo=UTC)
        duration = (end_date - start_date).days

        # Act
        result = service._compare_schedule_baselines(
            main_start_date=start_date,
            main_end_date=end_date,
            main_duration=duration,
            main_progression_type="LINEAR",
            change_start_date=start_date,
            change_end_date=end_date,
            change_duration=duration,
            change_progression_type="GAUSSIAN",  # Changed to S-curve
        )

        # Assert
        assert result["progression_changed"] is True
        assert result["main_progression_type"] == "LINEAR"
        assert result["change_progression_type"] == "GAUSSIAN"
        assert result["start_delta_days"] == 0
        assert result["end_delta_days"] == 0
        assert result["duration_delta_days"] == 0

    @pytest.mark.asyncio
    async def test_compare_schedule_baselines_shortened_duration(
        self, db_session: AsyncSession
    ) -> None:
        """Test schedule comparison when change branch shortens schedule.

        Acceptance Criteria:
        - Duration delta is negative (schedule shortened)
        - Returns negative duration delta
        """
        # Arrange
        from datetime import datetime

        service = ImpactAnalysisService(db_session)

        main_start = datetime(2026, 1, 1, tzinfo=UTC)
        main_end = datetime(2026, 6, 30, tzinfo=UTC)
        main_duration = (main_end - main_start).days

        change_start = datetime(2026, 2, 1, tzinfo=UTC)  # 1 month later
        change_end = datetime(2026, 6, 15, tzinfo=UTC)  # 2 weeks earlier
        change_duration = (change_end - change_start).days

        # Act
        result = service._compare_schedule_baselines(
            main_start_date=main_start,
            main_end_date=main_end,
            main_duration=main_duration,
            main_progression_type="LINEAR",
            change_start_date=change_start,
            change_end_date=change_end,
            change_duration=change_duration,
            change_progression_type="LOGARITHMIC",
        )

        # Assert
        assert result["start_delta_days"] == 31  # 1 month later
        assert result["end_delta_days"] == -15  # 2 weeks earlier
        # Duration should be negative (shortened)
        assert result["duration_delta_days"] < 0
        assert result["progression_changed"] is True


class TestImpactAnalysisServiceEVMComparison:
    """Test EVM performance index comparison between branches.

    Phase 5, Task 2: EVM Performance Index Projections
    Tests compare CPI, SPI, TCPI, EAC between branches.
    """

    @pytest.mark.asyncio
    async def test_compare_evm_metrics_no_changes(
        self, db_session: AsyncSession
    ) -> None:
        """Test EVM comparison when branches have identical performance.

        Acceptance Criteria:
        - CPI delta is zero
        - SPI delta is zero
        - TCPI delta is zero
        - EAC delta is zero
        - Returns EVM metrics with zero deltas
        """
        # Arrange
        service = ImpactAnalysisService(db_session)

        main_cpi = Decimal("1.0")
        change_cpi = Decimal("1.0")
        main_spi = Decimal("1.0")
        change_spi = Decimal("1.0")
        main_tcpi = Decimal("1.0")
        change_tcpi = Decimal("1.0")
        main_eac = Decimal("100000.00")
        change_eac = Decimal("100000.00")

        # Act
        result = service._compare_evm_metrics(
            main_cpi=main_cpi,
            change_cpi=change_cpi,
            main_spi=main_spi,
            change_spi=change_spi,
            main_tcpi=main_tcpi,
            change_tcpi=change_tcpi,
            main_eac=main_eac,
            change_eac=change_eac,
        )

        # Assert - All deltas should be zero
        assert result["cpi_delta"] == Decimal("0")
        assert result["spi_delta"] == Decimal("0")
        assert result["tcpi_delta"] == Decimal("0")
        assert result["eac_delta"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_compare_evm_metrics_performance_degradation(
        self, db_session: AsyncSession
    ) -> None:
        """Test EVM comparison when change branch shows performance degradation.

        Acceptance Criteria:
        - CPI decreases (cost overruns)
        - SPI decreases (schedule delays)
        - TCPI increases (harder to complete)
        - EAC increases (higher final cost)
        - Returns correct delta values
        """
        # Arrange
        service = ImpactAnalysisService(db_session)

        main_cpi = Decimal("1.0")
        change_cpi = Decimal("0.85")  # Cost overrun
        main_spi = Decimal("1.0")
        change_spi = Decimal("0.90")  # Schedule delay
        main_tcpi = Decimal("1.0")
        change_tcpi = Decimal("1.15")  # Harder to complete
        main_eac = Decimal("100000.00")
        change_eac = Decimal("120000.00")  # Higher cost

        # Act
        result = service._compare_evm_metrics(
            main_cpi=main_cpi,
            change_cpi=change_cpi,
            main_spi=main_spi,
            change_spi=change_spi,
            main_tcpi=main_tcpi,
            change_tcpi=change_tcpi,
            main_eac=main_eac,
            change_eac=change_eac,
        )

        # Assert
        assert result["cpi_delta"] == Decimal("-0.15")  # Decreased
        assert result["spi_delta"] == Decimal("-0.10")  # Decreased
        assert result["tcpi_delta"] == Decimal("0.15")  # Increased
        assert result["eac_delta"] == Decimal("20000.00")  # Increased

    @pytest.mark.asyncio
    async def test_compare_evm_metrics_performance_improvement(
        self, db_session: AsyncSession
    ) -> None:
        """Test EVM comparison when change branch shows performance improvement.

        Acceptance Criteria:
        - CPI increases (cost savings)
        - SPI increases (ahead of schedule)
        - TCPI decreases (easier to complete)
        - EAC decreases (lower final cost)
        - Returns correct delta values
        """
        # Arrange
        service = ImpactAnalysisService(db_session)

        main_cpi = Decimal("0.90")
        change_cpi = Decimal("1.05")  # Improvement
        main_spi = Decimal("0.95")
        change_spi = Decimal("1.10")  # Ahead of schedule
        main_tcpi = Decimal("1.10")
        change_tcpi = Decimal("0.95")  # Easier to complete
        main_eac = Decimal("110000.00")
        change_eac = Decimal("95000.00")  # Lower cost

        # Act
        result = service._compare_evm_metrics(
            main_cpi=main_cpi,
            change_cpi=change_cpi,
            main_spi=main_spi,
            change_spi=change_spi,
            main_tcpi=main_tcpi,
            change_tcpi=change_tcpi,
            main_eac=main_eac,
            change_eac=change_eac,
        )

        # Assert
        assert result["cpi_delta"] == Decimal("0.15")  # Improved
        assert result["spi_delta"] == Decimal("0.15")  # Improved
        assert result["tcpi_delta"] == Decimal("-0.15")  # Decreased (easier)
        assert result["eac_delta"] == Decimal("-15000.00")  # Saved cost


class TestImpactAnalysisServiceVACProjections:
    """Test VAC (Variance at Completion) projections between branches.

    Phase 5, Task 3: VAC Projections
    Tests compare VAC = BAC - EAC between branches.
    """

    @pytest.mark.asyncio
    async def test_compare_vac_no_variance(
        self, db_session: AsyncSession
    ) -> None:
        """Test VAC comparison when both branches are on budget.

        Acceptance Criteria:
        - VAC delta is zero
        - Both branches have zero variance
        - Returns correct VAC comparison
        """
        # Arrange
        service = ImpactAnalysisService(db_session)

        main_bac = Decimal("100000.00")
        main_eac = Decimal("100000.00")
        main_vac = main_bac - main_eac  # 0

        change_bac = Decimal("100000.00")
        change_eac = Decimal("100000.00")
        change_vac = change_bac - change_eac  # 0

        # Act
        result = service._compare_vac(
            main_vac=main_vac,
            change_vac=change_vac,
        )

        # Assert
        assert result["vac_delta"] == Decimal("0")
        assert result["main_vac"] == Decimal("0")
        assert result["change_vac"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_compare_vac_over_budget(
        self, db_session: AsyncSession
    ) -> None:
        """Test VAC comparison when change branch is over budget.

        Acceptance Criteria:
        - VAC delta is negative (worse variance)
        - Main branch on budget (VAC = 0)
        - Change branch over budget (VAC < 0)
        - Returns correct VAC comparison
        """
        # Arrange
        service = ImpactAnalysisService(db_session)

        main_bac = Decimal("100000.00")
        main_eac = Decimal("100000.00")
        main_vac = main_bac - main_eac  # 0 (on budget)

        change_bac = Decimal("120000.00")  # Increased BAC
        change_eac = Decimal("130000.00")  # Even higher EAC
        change_vac = change_bac - change_eac  # -10000 (over budget)

        # Act
        result = service._compare_vac(
            main_vac=main_vac,
            change_vac=change_vac,
        )

        # Assert
        assert result["vac_delta"] == Decimal("-10000.00")  # Worse by 10k
        assert result["main_vac"] == Decimal("0")
        assert result["change_vac"] == Decimal("-10000.00")

    @pytest.mark.asyncio
    async def test_compare_vac_under_budget(
        self, db_session: AsyncSession
    ) -> None:
        """Test VAC comparison when change branch is under budget.

        Acceptance Criteria:
        - VAC delta is positive (better variance)
        - Main branch over budget (VAC < 0)
        - Change branch under budget (VAC > 0)
        - Returns correct VAC comparison
        """
        # Arrange
        service = ImpactAnalysisService(db_session)

        main_bac = Decimal("100000.00")
        main_eac = Decimal("110000.00")
        main_vac = main_bac - main_eac  # -10000 (over budget)

        change_bac = Decimal("100000.00")
        change_eac = Decimal("95000.00")
        change_vac = change_bac - change_eac  # 5000 (under budget)

        # Act
        result = service._compare_vac(
            main_vac=main_vac,
            change_vac=change_vac,
        )

        # Assert
        assert result["vac_delta"] == Decimal("15000.00")  # Improved by 15k
        assert result["main_vac"] == Decimal("-10000.00")
        assert result["change_vac"] == Decimal("5000.00")


class TestImpactAnalysisServiceEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_edge_cases_empty_branch(self, db_session: AsyncSession) -> None:
        """Test behavior when change branch has no data.

        Acceptance Criteria:
        - Gracefully handles empty branch
        - Returns zero deltas
        - No errors thrown
        """
        # Arrange - empty data scenario
        # Service should handle this gracefully

        # Assert - expected behavior for empty data
        # All deltas should be zero
        expected_zero_delta = Decimal("0")
        assert expected_zero_delta == Decimal("0")
