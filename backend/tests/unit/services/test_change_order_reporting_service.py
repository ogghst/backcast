"""Unit tests for ChangeOrderReportingService.

Tests use the ChangeOrderService to create test data, ensuring proper JSONB handling.
"""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.change_order import ChangeOrderCreate
from app.services.change_order_reporting_service import ChangeOrderReportingService
from app.services.change_order_service import ChangeOrderService


class TestChangeOrderReportingService:
    """Test ChangeOrderReportingService aggregation methods."""

    @pytest.fixture
    def service(self, db_session: AsyncSession) -> ChangeOrderReportingService:
        """Create service instance."""
        return ChangeOrderReportingService(db_session)

    @pytest.fixture
    def co_service(self, db_session: AsyncSession) -> ChangeOrderService:
        """Create change order service instance."""
        return ChangeOrderService(db_session)


class TestGetSummaryKpis(TestChangeOrderReportingService):
    """Test _get_summary_kpis method."""

    @pytest.mark.asyncio
    async def test_get_summary_kpis_no_change_orders(
        self,
        service: ChangeOrderReportingService,
    ) -> None:
        """Test summary KPIs when no change orders exist.

        Expected: All zeros
        """
        result = await service._get_summary_kpis(
            project_id=uuid4(),  # Non-existent project
            branch="main",
            as_of=datetime.now(UTC),
        )

        assert result["total_count"] == 0
        assert result["total_cost_exposure"] == Decimal("0")
        assert result["pending_value"] == Decimal("0")
        assert result["approved_value"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_summary_kpis_with_data(
        self,
        service: ChangeOrderReportingService,
        co_service: ChangeOrderService,
        db_session: AsyncSession,
    ) -> None:
        """Test summary KPIs calculation with various CO states."""
        project_id = uuid4()
        actor_id = uuid4()

        # Create change orders using the service
        co1 = await co_service.create_change_order(
            ChangeOrderCreate(
                project_id=project_id,
                code="CO-STAT-001",
                title="Draft CO",
                description="Test",
            ),
            actor_id=actor_id,
        )

        co2 = await co_service.create_change_order(
            ChangeOrderCreate(
                project_id=project_id,
                code="CO-STAT-002",
                title="Another Draft CO",
                description="Test",
            ),
            actor_id=actor_id,
        )

        # Update with impact analysis results for one CO
        # Use raw update to set impact_analysis_results
        await db_session.execute(
            text("""
                UPDATE change_orders
                SET impact_analysis_results = '{"kpi_scorecard": {"budget_delta": {"delta": 10000}}}'::jsonb
                WHERE change_order_id = :co_id
            """),
            {"co_id": co1.change_order_id},
        )
        await db_session.commit()

        result = await service._get_summary_kpis(
            project_id=project_id,
            branch="main",
            as_of=datetime.now(UTC),
        )

        # Should have 2 COs
        assert result["total_count"] == 2
        # One CO has 10000 impact
        assert result["total_cost_exposure"] == Decimal("10000")
        # Draft COs are pending
        assert result["pending_value"] == Decimal("10000")
        # No approved COs
        assert result["approved_value"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_summary_kpis_null_impact_results(
        self,
        service: ChangeOrderReportingService,
        co_service: ChangeOrderService,
    ) -> None:
        """Test summary KPIs with null impact_analysis_results.

        Expected: Values default to 0
        """
        project_id = uuid4()
        actor_id = uuid4()

        # Create CO without impact analysis
        await co_service.create_change_order(
            ChangeOrderCreate(
                project_id=project_id,
                code="CO-NULL-001",
                title="Null Impact CO",
                description="Test",
            ),
            actor_id=actor_id,
        )

        result = await service._get_summary_kpis(
            project_id=project_id,
            branch="main",
            as_of=datetime.now(UTC),
        )

        assert result["total_count"] == 1
        assert result["total_cost_exposure"] == Decimal("0")
        assert result["pending_value"] == Decimal("0")


class TestGetStatusDistribution(TestChangeOrderReportingService):
    """Test _get_status_distribution method."""

    @pytest.mark.asyncio
    async def test_get_status_distribution_grouping(
        self,
        service: ChangeOrderReportingService,
        co_service: ChangeOrderService,
    ) -> None:
        """Test status distribution groups COs correctly."""
        project_id = uuid4()
        actor_id = uuid4()

        # Create multiple COs (all Draft by default)
        for i in range(3):
            await co_service.create_change_order(
                ChangeOrderCreate(
                    project_id=project_id,
                    code=f"CO-STAT-{i:03d}",
                    title=f"CO {i}",
                    description="Test",
                ),
                actor_id=actor_id,
            )

        result = await service._get_status_distribution(
            project_id=project_id,
            branch="main",
            as_of=datetime.now(UTC),
        )

        # All 3 should be in Draft status
        assert len(result) == 1
        assert result[0].status == "Draft"
        assert result[0].count == 3

    @pytest.mark.asyncio
    async def test_get_status_distribution_empty(
        self,
        service: ChangeOrderReportingService,
    ) -> None:
        """Test status distribution with no COs."""
        result = await service._get_status_distribution(
            project_id=uuid4(),
            branch="main",
            as_of=datetime.now(UTC),
        )

        assert result == []


class TestGetImpactDistribution(TestChangeOrderReportingService):
    """Test _get_impact_distribution method."""

    @pytest.mark.asyncio
    async def test_get_impact_distribution_empty(
        self,
        service: ChangeOrderReportingService,
    ) -> None:
        """Test impact distribution with no COs."""
        result = await service._get_impact_distribution(
            project_id=uuid4(),
            branch="main",
            as_of=datetime.now(UTC),
        )

        assert result == []


class TestGetCostTrend(TestChangeOrderReportingService):
    """Test _get_cost_trend method."""

    @pytest.mark.asyncio
    async def test_get_cost_trend_no_data(
        self,
        service: ChangeOrderReportingService,
    ) -> None:
        """Test cost trend returns empty list when no COs."""
        result = await service._get_cost_trend(
            project_id=uuid4(),
            branch="main",
            as_of=datetime.now(UTC),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_cost_trend_with_data(
        self,
        service: ChangeOrderReportingService,
        co_service: ChangeOrderService,
    ) -> None:
        """Test cost trend with COs."""
        project_id = uuid4()
        actor_id = uuid4()

        # Create a CO
        await co_service.create_change_order(
            ChangeOrderCreate(
                project_id=project_id,
                code="CO-TREND-001",
                title="Trend CO",
                description="Test",
            ),
            actor_id=actor_id,
        )

        result = await service._get_cost_trend(
            project_id=project_id,
            branch="main",
            as_of=datetime.now(UTC),
        )

        # Should have at least one trend point
        assert len(result) >= 1
        # Last point should have cumulative count of 1
        assert result[-1].count == 1


class TestGetAgingItems(TestChangeOrderReportingService):
    """Test _get_aging_items method."""

    @pytest.mark.asyncio
    async def test_get_aging_items_empty(
        self,
        service: ChangeOrderReportingService,
    ) -> None:
        """Test aging items with no COs."""
        result = await service._get_aging_items(
            project_id=uuid4(),
            branch="main",
            as_of=datetime.now(UTC),
            threshold_days=7,
        )

        assert result == []


class TestGetApprovalWorkload(TestChangeOrderReportingService):
    """Test _get_approval_workload method."""

    @pytest.mark.asyncio
    async def test_get_approval_workload_empty(
        self,
        service: ChangeOrderReportingService,
    ) -> None:
        """Test approval workload with no pending COs."""
        result = await service._get_approval_workload(
            project_id=uuid4(),
            branch="main",
            as_of=datetime.now(UTC),
        )

        assert result == []


class TestGetAvgApprovalTime(TestChangeOrderReportingService):
    """Test _get_avg_approval_time method."""

    @pytest.mark.asyncio
    async def test_get_avg_approval_time_no_approved(
        self,
        service: ChangeOrderReportingService,
    ) -> None:
        """Test average approval time when no approved COs."""
        result = await service._get_avg_approval_time(
            project_id=uuid4(),
            branch="main",
            as_of=datetime.now(UTC),
        )

        assert result is None


class TestGetChangeOrderStats(TestChangeOrderReportingService):
    """Test get_change_order_stats (main entry point)."""

    @pytest.mark.asyncio
    async def test_get_change_order_stats_empty_project(
        self,
        service: ChangeOrderReportingService,
    ) -> None:
        """Test stats response for project with no COs."""
        result = await service.get_change_order_stats(
            project_id=uuid4(),
            branch="main",
            as_of=datetime.now(UTC),
            aging_threshold_days=7,
        )

        assert result.total_count == 0
        assert result.total_cost_exposure == Decimal("0")
        assert result.pending_value == Decimal("0")
        assert result.approved_value == Decimal("0")
        assert result.by_status == []
        assert result.by_impact_level == []
        assert result.cost_trend == []
        assert result.approval_workload == []
        assert result.aging_items == []
        assert result.avg_approval_time_days is None

    @pytest.mark.asyncio
    async def test_get_change_order_stats_with_data(
        self,
        service: ChangeOrderReportingService,
        co_service: ChangeOrderService,
    ) -> None:
        """Test complete stats response with COs."""
        project_id = uuid4()
        actor_id = uuid4()

        # Create some COs
        for i in range(2):
            await co_service.create_change_order(
                ChangeOrderCreate(
                    project_id=project_id,
                    code=f"CO-COMPLETE-{i:03d}",
                    title=f"Complete CO {i}",
                    description="Test",
                ),
                actor_id=actor_id,
            )

        result = await service.get_change_order_stats(
            project_id=project_id,
            branch="main",
            as_of=datetime.now(UTC),
            aging_threshold_days=7,
        )

        # Verify response structure
        assert result.total_count == 2
        assert isinstance(result.total_cost_exposure, Decimal)
        assert isinstance(result.pending_value, Decimal)
        assert isinstance(result.approved_value, Decimal)
        assert isinstance(result.by_status, list)
        assert isinstance(result.by_impact_level, list)
        assert isinstance(result.cost_trend, list)
        assert isinstance(result.approval_workload, list)
        assert isinstance(result.aging_items, list)
        assert result.aging_threshold_days == 7

    @pytest.mark.asyncio
    async def test_get_change_order_stats_custom_threshold(
        self,
        service: ChangeOrderReportingService,
    ) -> None:
        """Test stats with custom aging threshold."""
        result = await service.get_change_order_stats(
            project_id=uuid4(),
            branch="main",
            as_of=datetime.now(UTC),
            aging_threshold_days=14,
        )

        assert result.aging_threshold_days == 14
