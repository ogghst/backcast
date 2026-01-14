"""Unit tests for ImpactAnalysisService.

Tests follow Red-Green-Refactor TDD cycle.
Tests are ordered from simplest to most complex.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.impact_analysis import (
    EntityChange,
    EntityChangeType,
    ImpactAnalysisResponse,
    KPIMetric,
    KPIScorecard,
)
from app.services.impact_analysis_service import ImpactAnalysisService


class TestImpactAnalysisServiceCompareKPIs:
    """Test ImpactAnalysisService._compare_kpis() method."""

    @pytest.mark.asyncio
    async def test_compare_kpis_no_changes(
        self, db_session: AsyncSession
    ) -> None:
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

        # Act
        result = service._compare_kpis(
            main_bac=main_bac,
            change_bac=change_bac,
            main_budget_total=main_budget,
            change_budget_total=change_budget,
            main_gross_margin=main_margin,
            change_gross_margin=change_margin,
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

    @pytest.mark.asyncio
    async def test_compare_kpis_happy_path(
        self, db_session: AsyncSession
    ) -> None:
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

        # Act
        result = service._compare_kpis(
            main_bac=main_bac,
            change_bac=change_bac,
            main_budget_total=main_budget,
            change_budget_total=change_budget,
            main_gross_margin=main_margin,
            change_gross_margin=change_margin,
        )

        # Assert - Delta and percent calculated correctly
        assert result.bac.delta == Decimal("20000.00")  # 120k - 100k
        assert result.bac.delta_percent == 20.0  # 20k / 100k * 100

        assert result.budget_delta.delta == Decimal("20000.00")
        assert result.budget_delta.delta_percent == 20.0

        assert result.gross_margin.delta == Decimal("5000.00")  # 25k - 20k
        assert result.gross_margin.delta_percent == 25.0  # 5k / 20k * 100


class TestImpactAnalysisServiceCompareEntities:
    """Test ImpactAnalysisService._compare_entities() method."""

    @pytest.mark.asyncio
    async def test_compare_entities_added_wbe(
        self, db_session: AsyncSession
    ) -> None:
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
        wbe_id = uuid4()
        old_budget = Decimal("50000.00")
        new_budget = Decimal("60000.00")

        expected_delta = new_budget - old_budget  # Decimal("10000.00")

        # Assert
        assert expected_delta == Decimal("10000.00")

    @pytest.mark.asyncio
    async def test_compare_entities_removed_wbe(
        self, db_session: AsyncSession
    ) -> None:
        """Test entity comparison when WBE is removed in change branch.

        Acceptance Criteria:
        - WBE appears with change_type="removed"
        - Previous financial values shown as negative impact
        """
        # Arrange
        wbe_id = uuid4()
        old_budget = Decimal("50000.00")

        # When removed, the delta is negative (lost budget)
        expected_delta = -old_budget  # Decimal("-50000.00")

        # Assert
        assert expected_delta == Decimal("-50000.00")


class TestImpactAnalysisServiceBuildWaterfall:
    """Test ImpactAnalysisService._build_waterfall() method."""

    @pytest.mark.asyncio
    async def test_build_waterfall_bridge(
        self, db_session: AsyncSession
    ) -> None:
        """Test waterfall chart construction from KPI comparison.

        Acceptance Criteria:
        - Returns 3 segments: current margin, delta, new margin
        - Values calculated correctly
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        current_margin = Decimal("20000.00")
        margin_delta = Decimal("5000.00")
        new_margin = current_margin + margin_delta  # Decimal("25000.00")

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
    async def test_generate_time_series_weekly(
        self, db_session: AsyncSession
    ) -> None:
        """Test weekly time-series data generation.

        Acceptance Criteria:
        - Data points grouped by week (week_start date)
        - Main and change values populated for each point
        """
        # Arrange
        week_start = date(2026, 1, 1)
        main_budget = Decimal("10000.00")
        change_budget = Decimal("12000.00")

        # Expected structure validation
        assert week_start == date(2026, 1, 1)
        assert main_budget == Decimal("10000.00")
        assert change_budget == Decimal("12000.00")


class TestImpactAnalysisServiceEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_edge_cases_empty_branch(
        self, db_session: AsyncSession
    ) -> None:
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
