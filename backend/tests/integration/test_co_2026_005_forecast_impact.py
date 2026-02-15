"""Integration test for CO-2026-005 impact analysis forecast changes.

Tests that ImpactAnalysisService correctly identifies NEW forecasts for a
scope addition change order where cost element IDs are completely different
between main and branch (no overlap).

Tests time-travel functionality with as_of parameter at:
1. Project start date (end of day)
2. Project end date (end of day)
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.versioning.enums import BranchMode
from app.db.seeder import DataSeeder
from app.models.domain.change_order import ChangeOrder
from app.models.domain.project import Project
from app.models.schemas.impact_analysis import ForecastChanges
from app.services.impact_analysis_service import ImpactAnalysisService

# Expected constants based on seed data analysis
BRANCH_NAME = "BR-CO-2026-005"
EXPECTED_FORECAST_COUNT = 25
EXPECTED_TOTAL_BRANCH_EAC = Decimal("375000.00")  # 25 * 15000

# Use the test database URL
TEST_DATABASE_URL = str(settings.DATABASE_URL)

# Module-level cache for seeded data
_seeded_engine: AsyncEngine | None = None
_co_and_project_cache: tuple[ChangeOrder, Project] | None = None
_seeding_lock = asyncio.Lock()


async def _ensure_seeded() -> AsyncEngine:
    """Ensure database is seeded, return engine."""
    global _seeded_engine

    if _seeded_engine is not None:
        return _seeded_engine

    async with _seeding_lock:
        # Double-check after acquiring lock
        if _seeded_engine is not None:
            return _seeded_engine

        engine = create_async_engine(
            TEST_DATABASE_URL, echo=False, poolclass=NullPool, pool_pre_ping=True
        )

        # Clean up tables before seeding
        async with engine.connect() as conn:
            await conn.execute(
                text(
                    "TRUNCATE TABLE cost_elements, cost_element_types, wbes, projects, "
                    "departments, users, cost_registrations, progress_entries, "
                    "schedule_baselines, branches, change_orders, change_order_audit_log, "
                    "forecasts RESTART IDENTITY CASCADE"
                )
            )
            await conn.commit()

        # Seed the database
        async with AsyncSession(engine, expire_on_commit=False) as session:
            seeder = DataSeeder()
            await seeder.seed_all(session)

        _seeded_engine = engine
        return engine


async def _get_co_and_project(session: AsyncSession) -> tuple[ChangeOrder, Project]:
    """Get CO-2026-005 and its project, using cache if available."""
    global _co_and_project_cache

    if _co_and_project_cache is not None:
        return _co_and_project_cache

    # Get CO-2026-005 (filter for current version - valid_time upper bound is None)
    stmt = select(ChangeOrder).where(
        ChangeOrder.code == "CO-2026-005",
        ChangeOrder.branch == "main",
        func.upper(cast(Any, ChangeOrder.valid_time)).is_(None),
        cast(Any, ChangeOrder.deleted_at).is_(None),
    )
    co = (await session.execute(stmt)).scalar_one()

    # Get project for dates (filter for current version)
    proj_stmt = select(Project).where(
        Project.project_id == co.project_id,
        Project.branch == "main",
        func.upper(cast(Any, Project.valid_time)).is_(None),
        cast(Any, Project.deleted_at).is_(None),
    )
    project = (await session.execute(proj_stmt)).scalar_one()

    _co_and_project_cache = (co, project)
    return co, project


@pytest_asyncio.fixture
async def seeded_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a session for the seeded database."""
    engine = await _ensure_seeded()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture
async def co_and_project(seeded_session: AsyncSession) -> tuple[ChangeOrder, Project]:
    """Get CO-2026-005 and its project from the seeded database."""
    return await _get_co_and_project(seeded_session)


def _get_new_forecasts(forecast_changes: ForecastChanges) -> list[Any]:
    """Get forecasts that are NEW (only on branch, not on main)."""
    return [
        fc for fc in forecast_changes.forecasts
        if fc.main_forecast is None and fc.branch_forecast is not None
    ]


class TestCO2026005ForecastImpact:
    """Integration test suite for CO-2026-005 forecast impact analysis."""

    @pytest.mark.asyncio
    async def test_forecast_changes_exists(
        self, seeded_session: AsyncSession, co_and_project: tuple[ChangeOrder, Project]
    ) -> None:
        """Test that forecast_changes is populated (current time)."""
        co, _ = co_and_project
        assert co.branch_name is not None, "branch_name should not be None"

        service = ImpactAnalysisService(seeded_session)
        impact = await service.analyze_impact(
            change_order_id=co.change_order_id,
            branch_name=co.branch_name,
            branch_mode=BranchMode.MERGE,
            include_evm_metrics=False,
            as_of=None,  # Current time
        )

        assert impact.forecast_changes is not None, "forecast_changes should not be None"
        assert len(impact.forecast_changes.forecasts) > 0, "Should have forecast comparisons"

    @pytest.mark.asyncio
    async def test_new_forecasts_count(
        self, seeded_session: AsyncSession, co_and_project: tuple[ChangeOrder, Project]
    ) -> None:
        """Test that correct number of NEW forecasts (only on branch) returned."""
        co, _ = co_and_project
        assert co.branch_name is not None, "branch_name should not be None"

        service = ImpactAnalysisService(seeded_session)
        impact = await service.analyze_impact(
            change_order_id=co.change_order_id,
            branch_name=co.branch_name,
            branch_mode=BranchMode.MERGE,
            include_evm_metrics=False,
        )

        assert impact.forecast_changes is not None
        new_forecasts = _get_new_forecasts(impact.forecast_changes)
        assert len(new_forecasts) == EXPECTED_FORECAST_COUNT, (
            f"Expected {EXPECTED_FORECAST_COUNT} NEW forecasts (branch only), "
            f"got {len(new_forecasts)}"
        )

    @pytest.mark.asyncio
    async def test_new_forecasts_identified(
        self, seeded_session: AsyncSession, co_and_project: tuple[ChangeOrder, Project]
    ) -> None:
        """Test that NEW forecasts (only on branch) have main_forecast=None."""
        co, _ = co_and_project
        assert co.branch_name is not None, "branch_name should not be None"

        service = ImpactAnalysisService(seeded_session)
        impact = await service.analyze_impact(
            change_order_id=co.change_order_id,
            branch_name=co.branch_name,
            branch_mode=BranchMode.MERGE,
            include_evm_metrics=False,
        )

        assert impact.forecast_changes is not None
        new_forecasts = _get_new_forecasts(impact.forecast_changes)

        # All NEW forecasts should have main_forecast=None and branch_forecast populated
        for fc in new_forecasts:
            assert fc.main_forecast is None, "Expected main_forecast=None for NEW forecasts"
            assert fc.branch_forecast is not None, "branch_forecast should be populated"

    @pytest.mark.asyncio
    async def test_total_branch_eac_values(
        self, seeded_session: AsyncSession, co_and_project: tuple[ChangeOrder, Project]
    ) -> None:
        """Test that total EAC values for NEW forecasts match expected totals."""
        co, _ = co_and_project
        assert co.branch_name is not None, "branch_name should not be None"

        service = ImpactAnalysisService(seeded_session)
        impact = await service.analyze_impact(
            change_order_id=co.change_order_id,
            branch_name=co.branch_name,
            branch_mode=BranchMode.MERGE,
            include_evm_metrics=False,
        )

        assert impact.forecast_changes is not None
        new_forecasts = _get_new_forecasts(impact.forecast_changes)

        total_branch_eac = sum(
            fc.branch_forecast.eac_amount
            for fc in new_forecasts
            if fc.branch_forecast
        )

        assert total_branch_eac == EXPECTED_TOTAL_BRANCH_EAC, (
            f"Expected total branch EAC of {EXPECTED_TOTAL_BRANCH_EAC}, got {total_branch_eac}"
        )

    @pytest.mark.asyncio
    async def test_forecast_comparison_structure(
        self, seeded_session: AsyncSession, co_and_project: tuple[ChangeOrder, Project]
    ) -> None:
        """Test that each forecast comparison has required fields."""
        co, _ = co_and_project
        assert co.branch_name is not None, "branch_name should not be None"

        service = ImpactAnalysisService(seeded_session)
        impact = await service.analyze_impact(
            change_order_id=co.change_order_id,
            branch_name=co.branch_name,
            branch_mode=BranchMode.MERGE,
            include_evm_metrics=False,
        )

        assert impact.forecast_changes is not None
        new_forecasts = _get_new_forecasts(impact.forecast_changes)
        assert len(new_forecasts) > 0, "Should have at least one NEW forecast"
        fc = new_forecasts[0]

        assert isinstance(fc.cost_element_id, UUID)
        assert isinstance(fc.cost_element_code, str)
        assert isinstance(fc.cost_element_name, str)
        assert isinstance(fc.budget_amount, Decimal)
        assert fc.branch_forecast is not None
        assert isinstance(fc.branch_forecast.eac_amount, Decimal)

    # ========================================
    # TIME-TRAVEL TESTS (as_of parameter)
    # ========================================

    @pytest.mark.asyncio
    async def test_impact_at_project_start_date(
        self, seeded_session: AsyncSession, co_and_project: tuple[ChangeOrder, Project]
    ) -> None:
        """Test impact analysis at project creation time (end of day).

        as_of = project.start_date end of day (2026-01-07T23:59:59Z)
        """
        co, project = co_and_project
        assert co.branch_name is not None, "branch_name should not be None"

        # End of day on project start date
        as_of_start = datetime(2026, 1, 7, 23, 59, 59, tzinfo=UTC)

        service = ImpactAnalysisService(seeded_session)
        impact = await service.analyze_impact(
            change_order_id=co.change_order_id,
            branch_name=co.branch_name,
            branch_mode=BranchMode.MERGE,
            include_evm_metrics=False,
            as_of=as_of_start,
        )

        # Verify forecast changes at project start
        assert impact.forecast_changes is not None

        # Count NEW forecasts at project start
        new_forecasts = _get_new_forecasts(impact.forecast_changes)
        assert len(new_forecasts) == EXPECTED_FORECAST_COUNT

    @pytest.mark.asyncio
    async def test_impact_at_project_end_date(
        self, seeded_session: AsyncSession, co_and_project: tuple[ChangeOrder, Project]
    ) -> None:
        """Test impact analysis at project end time (end of day).

        as_of = project.end_date end of day (2027-01-07T23:59:59Z)
        """
        co, project = co_and_project
        assert co.branch_name is not None, "branch_name should not be None"

        # End of day on project end date
        as_of_end = datetime(2027, 1, 7, 23, 59, 59, tzinfo=UTC)

        service = ImpactAnalysisService(seeded_session)
        impact = await service.analyze_impact(
            change_order_id=co.change_order_id,
            branch_name=co.branch_name,
            branch_mode=BranchMode.MERGE,
            include_evm_metrics=False,
            as_of=as_of_end,
        )

        # Verify forecast changes at project end
        assert impact.forecast_changes is not None

        # Count NEW forecasts and sum their EAC at project end
        new_forecasts = _get_new_forecasts(impact.forecast_changes)
        assert len(new_forecasts) == EXPECTED_FORECAST_COUNT

        total_branch_eac = sum(
            fc.branch_forecast.eac_amount
            for fc in new_forecasts
            if fc.branch_forecast
        )

        assert total_branch_eac == EXPECTED_TOTAL_BRANCH_EAC

    @pytest.mark.asyncio
    async def test_impact_consistency_across_time(
        self, seeded_session: AsyncSession, co_and_project: tuple[ChangeOrder, Project]
    ) -> None:
        """Test that impact analysis returns consistent results across time points.

        For this static seed data, NEW forecast counts and totals should be
        identical at project start and project end.
        """
        co, project = co_and_project
        assert co.branch_name is not None, "branch_name should not be None"

        service = ImpactAnalysisService(seeded_session)

        # Impact at project start
        as_of_start = datetime(2026, 1, 7, 23, 59, 59, tzinfo=UTC)
        impact_start = await service.analyze_impact(
            change_order_id=co.change_order_id,
            branch_name=co.branch_name,
            branch_mode=BranchMode.MERGE,
            include_evm_metrics=False,
            as_of=as_of_start,
        )

        # Impact at project end
        as_of_end = datetime(2027, 1, 7, 23, 59, 59, tzinfo=UTC)
        impact_end = await service.analyze_impact(
            change_order_id=co.change_order_id,
            branch_name=co.branch_name,
            branch_mode=BranchMode.MERGE,
            include_evm_metrics=False,
            as_of=as_of_end,
        )

        # Count NEW forecasts at both time points
        assert impact_start.forecast_changes is not None
        assert impact_end.forecast_changes is not None

        new_forecasts_start = _get_new_forecasts(impact_start.forecast_changes)
        new_forecasts_end = _get_new_forecasts(impact_end.forecast_changes)

        # NEW forecast counts should match
        assert len(new_forecasts_start) == len(new_forecasts_end) == EXPECTED_FORECAST_COUNT

        # Total EAC for NEW forecasts should match
        eac_start = sum(
            fc.branch_forecast.eac_amount
            for fc in new_forecasts_start
            if fc.branch_forecast
        )
        eac_end = sum(
            fc.branch_forecast.eac_amount
            for fc in new_forecasts_end
            if fc.branch_forecast
        )
        assert eac_start == eac_end == EXPECTED_TOTAL_BRANCH_EAC
