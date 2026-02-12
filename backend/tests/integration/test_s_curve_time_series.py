"""Integration tests for S-Curve time series generation in Impact Analysis.

Tests the _generate_time_series() method with realistic database scenarios
including edge cases for branch differences, progression types, and schedule variations.

Updated to test 4 EVM metrics: budget, PV, EV, AC.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.department import Department
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.domain.wbe import WBE
from app.services.impact_analysis_service import ImpactAnalysisService


@pytest.mark.asyncio
class TestSCurveTimeSeriesGeneration:
    """Test S-curve time series generation with various edge cases.

    Edge Case 1: Budget increase on change branch
    - Main branch: WBE with $50k budget
    - Change branch: Same WBE with $75k budget (50% increase)
    - Expected: Change branch values should be 50% higher than main

    Edge Case 2: New WBE added on change branch
    - Main branch: 1 WBE with $100k budget
    - Change branch: 2 WBEs (original + new $50k)
    - Expected: Change branch cumulative should include both WBEs

    Edge Case 3: Progression type change
    - Main branch: LINEAR progression
    - Change branch: GAUSSIAN progression (S-curve)
    - Expected: Different curve shapes, same total budget

    Edge Case 4: Schedule duration extension
    - Main branch: 6-month schedule
    - Change branch: 9-month schedule (extended)
    - Expected: Flatter curve over longer period
    """

    async def test_s_curve_with_budget_increase(
        self, db_session: AsyncSession
    ) -> None:
        """Test S-curve when change branch increases WBE budget.

        Edge Case 1: Budget Increase
        - Main: WBE-1 with $50,000 budget, LINEAR progression, 6 months
        - Change: WBE-1 with $75,000 budget (50% increase), same schedule
        - Expected: Change curve should be 50% higher at all points
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        project_id = uuid4()
        wbe_id = uuid4()
        dept_id = uuid4()
        branch_name = "BR-test-001"

        # Create department
        dept = Department(
            department_id=dept_id,
            code="ENG",
            name="Engineering",
            manager_id=uuid4(),
        )
        db_session.add(dept)

        # Create cost element type
        cet_id = self._create_cost_element_type(db_session, dept_id)

        # Create WBEs and cost elements
        main_wbe = WBE(
            wbe_id=wbe_id,
            project_id=project_id,
            code="1.1",
            name="Assembly",
            budget_allocation=Decimal("50000.00"),
            revenue_allocation=Decimal("60000.00"),
            branch="main",
        )
        db_session.add(main_wbe)

        change_wbe = WBE(
            wbe_id=wbe_id,
            project_id=project_id,
            code="1.1",
            name="Assembly",
            budget_allocation=Decimal("75000.00"),  # 50% increase
            revenue_allocation=Decimal("90000.00"),
            branch=branch_name,
        )
        db_session.add(change_wbe)

        # Create schedule baselines with dates
        schedule_start = datetime(2026, 1, 1, tzinfo=UTC)
        schedule_end = datetime(2026, 6, 30, tzinfo=UTC)

        self._create_schedule_baseline(
            db_session, wbe_id, cet_id, "main", schedule_start, schedule_end, "LINEAR"
        )
        self._create_schedule_baseline(
            db_session, wbe_id, cet_id, branch_name, schedule_start, schedule_end, "LINEAR"
        )

        await db_session.commit()

        # Act
        result = await service._generate_time_series(project_id, branch_name)

        # Assert
        assert len(result) == 4, "Should return 4 time series (budget, pv, ev, ac)"

        # Get budget time series
        budget_series = next((ts for ts in result if ts.metric_name == "budget"), None)
        assert budget_series is not None, "Should have budget time series"

        data_points = budget_series.data_points
        assert len(data_points) > 1, "Should generate multiple weekly data points"

        # Check that change branch values are consistently 50% higher
        for point in data_points:
            main_val = point.main_value or Decimal("0")
            change_val = point.change_value or Decimal("0")

            # Change should be 1.5x main (50% increase)
            if main_val > 0:
                ratio = change_val / main_val
                assert (
                    abs(ratio - Decimal("1.5")) < Decimal("0.01")
                ), f"At {point.week_start}, change ({change_val}) should be ~1.5x main ({main_val}), got ratio {ratio}"

        # Verify final cumulative values match total budgets
        final_point = data_points[-1]
        assert final_point.main_value == Decimal("50000.00")
        assert final_point.change_value == Decimal("75000.00")

    async def test_s_curve_with_new_wbe_added(
        self, db_session: AsyncSession
    ) -> None:
        """Test S-curve when change branch adds a new WBE.

        Edge Case 2: New WBE Added
        - Main: 1 WBE with $100k budget, LINEAR, 6 months
        - Change: 2 WBEs (original $100k + new $50k), same schedule
        - Expected: Change cumulative = $100k (original) + $50k (new) = $150k
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        project_id = uuid4()
        wbe_1_id = uuid4()
        wbe_2_id = uuid4()  # New WBE only in change branch
        cet_id = uuid4()
        branch_name = "BR-test-002"

        # Create cost element type
        cet = CostElementType(
            cost_element_type_id=cet_id,
            code="LABOR",
            name="Labor",
            description="Labor costs",
            branch="main",
        )
        db_session.add(cet)

        # Create main branch WBE-1 with $100k budget
        main_wbe_1 = WBE(
            wbe_id=wbe_1_id,
            project_id=project_id,
            code="1.1",
            name="Assembly Station",
            budget_allocation=Decimal("100000.00"),
            revenue_allocation=Decimal("120000.00"),
            branch="main",
        )
        db_session.add(main_wbe_1)

        # Create change branch WBE-1 (same as main)
        change_wbe_1 = WBE(
            wbe_id=wbe_1_id,
            project_id=project_id,
            code="1.1",
            name="Assembly Station",
            budget_allocation=Decimal("100000.00"),
            revenue_allocation=Decimal("120000.00"),
            branch=branch_name,
        )
        db_session.add(change_wbe_1)

        # Create NEW WBE-2 only on change branch
        change_wbe_2 = WBE(
            wbe_id=wbe_2_id,
            project_id=project_id,
            code="1.2",
            name="Test Station",  # New WBE
            budget_allocation=Decimal("50000.00"),  # Additional $50k
            revenue_allocation=Decimal("60000.00"),
            branch=branch_name,
        )
        db_session.add(change_wbe_2)

        # Create schedule baselines
        schedule_start = datetime(2026, 1, 1, tzinfo=UTC)
        schedule_end = datetime(2026, 6, 30, tzinfo=UTC)

        self._create_schedule_baseline(
            db_session, wbe_1_id, cet_id, "main", schedule_start, schedule_end, "LINEAR"
        )
        self._create_schedule_baseline(
            db_session, wbe_1_id, cet_id, branch_name, schedule_start, schedule_end, "LINEAR"
        )
        self._create_schedule_baseline(
            db_session, wbe_2_id, cet_id, branch_name, schedule_start, schedule_end, "LINEAR"
        )

        await db_session.commit()

        # Act
        result = await service._generate_time_series(project_id, branch_name)

        # Assert
        assert len(result) == 4, "Should return 4 time series (budget, pv, ev, ac)"

        # Get budget time series
        budget_series = next((ts for ts in result if ts.metric_name == "budget"), None)
        assert budget_series is not None, "Should have budget time series"

        data_points = budget_series.data_points
        assert len(data_points) > 1, "Should generate multiple weekly data points"

        # Verify final cumulative values
        final_point = data_points[-1]
        assert final_point.main_value == Decimal("100000.00"), "Main branch should have $100k total"
        assert (
            final_point.change_value == Decimal("150000.00")
        ), "Change branch should have $150k total ($100k + $50k new WBE)"

        # Verify that change branch is consistently $50k higher throughout
        mid_point = data_points[len(data_points) // 2]
        main_mid = mid_point.main_value or Decimal("0")
        change_mid = mid_point.change_value or Decimal("0")
        delta = change_mid - main_mid

        # Delta should be approximately $50k (the new WBE's contribution)
        # We allow some tolerance due to weekly aggregation
        assert abs(delta - Decimal("50000.00")) < Decimal("5000.00"), (
            f"Delta should be ~$50k, got {delta} "
            f"(main={main_mid}, change={change_mid})"
        )

    async def test_s_curve_with_progression_type_change(
        self, db_session: AsyncSession
    ) -> None:
        """Test S-curve when progression type changes between branches.

        Edge Case 3: Progression Type Change
        - Main: LINEAR progression (straight line)
        - Change: GAUSSIAN progression (S-curve)
        - Expected: Different curve shapes, same total budget
        - Gaussian should be lower at start, higher in middle, similar at end
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        project_id = uuid4()
        wbe_id = uuid4()
        cet_id = uuid4()
        branch_name = "BR-test-003"

        # Create cost element type
        cet = CostElementType(
            cost_element_type_id=cet_id,
            code="LABOR",
            name="Labor",
            description="Labor costs",
            branch="main",
        )
        db_session.add(cet)

        # Create WBEs with same budget
        main_wbe = WBE(
            wbe_id=wbe_id,
            project_id=project_id,
            code="1.1",
            name="Assembly",
            budget_allocation=Decimal("100000.00"),
            revenue_allocation=Decimal("120000.00"),
            branch="main",
        )
        db_session.add(main_wbe)

        change_wbe = WBE(
            wbe_id=wbe_id,
            project_id=project_id,
            code="1.1",
            name="Assembly",
            budget_allocation=Decimal("100000.00"),
            revenue_allocation=Decimal("120000.00"),
            branch=branch_name,
        )
        db_session.add(change_wbe)

        # Create schedule baselines with DIFFERENT progression types
        schedule_start = datetime(2026, 1, 1, tzinfo=UTC)
        schedule_end = datetime(2026, 12, 31, tzinfo=UTC)  # Full year for better S-curve visibility

        self._create_schedule_baseline(
            db_session, wbe_id, cet_id, "main", schedule_start, schedule_end, "LINEAR"
        )
        self._create_schedule_baseline(
            db_session, wbe_id, cet_id, branch_name, schedule_start, schedule_end, "GAUSSIAN"
        )

        await db_session.commit()

        # Act
        result = await service._generate_time_series(project_id, branch_name)

        # Assert
        assert len(result) == 4, "Should return 4 time series (budget, pv, ev, ac)"

        # Get budget time series
        budget_series = next((ts for ts in result if ts.metric_name == "budget"), None)
        assert budget_series is not None, "Should have budget time series"

        data_points = budget_series.data_points
        assert len(data_points) > 10, "Should generate many weekly data points for a year-long project"

        # Verify final values are the same (same total budget)
        final_point = data_points[-1]
        assert final_point.main_value == Decimal("100000.00")
        assert final_point.change_value == Decimal("100000.00")

        # Verify curve shapes are different
        # At the start, LINEAR should be higher than GAUSSIAN (S-curve starts slow)
        first_point = data_points[0]
        main_first = first_point.main_value or Decimal("0")
        change_first = first_point.change_value or Decimal("0")

        # Linear starts immediately, Gaussian starts slower
        assert main_first > change_first, (
            f"LINEAR should start higher than GAUSSIAN at start: "
            f"main={main_first}, change={change_first}"
        )

        # In the middle, GAUSSIAN should be higher than LINEAR (S-curve peaks)
        mid_point = data_points[len(data_points) // 2]
        main_mid = mid_point.main_value or Decimal("0")
        change_mid = mid_point.change_value or Decimal("0")

        # At midpoint, Gaussian S-curve should be ahead of Linear
        assert change_mid > main_mid, (
            f"GAUSSIAN should be higher than LINEAR at midpoint: "
            f"main={main_mid}, change={change_mid}"
        )

    async def test_s_curve_with_schedule_extension(
        self, db_session: AsyncSession
    ) -> None:
        """Test S-curve when schedule duration is extended on change branch.

        Edge Case 4: Schedule Duration Extension
        - Main: 6-month schedule, $100k budget
        - Change: 9-month schedule (50% longer), same $100k budget
        - Expected: Flatter curve over longer period (slower accumulation)
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        project_id = uuid4()
        wbe_id = uuid4()
        cet_id = uuid4()
        branch_name = "BR-test-004"

        # Create cost element type
        cet = CostElementType(
            cost_element_type_id=cet_id,
            code="LABOR",
            name="Labor",
            description="Labor costs",
            branch="main",
        )
        db_session.add(cet)

        # Create WBEs with same budget
        main_wbe = WBE(
            wbe_id=wbe_id,
            project_id=project_id,
            code="1.1",
            name="Assembly",
            budget_allocation=Decimal("100000.00"),
            revenue_allocation=Decimal("120000.00"),
            branch="main",
        )
        db_session.add(main_wbe)

        change_wbe = WBE(
            wbe_id=wbe_id,
            project_id=project_id,
            code="1.1",
            name="Assembly",
            budget_allocation=Decimal("100000.00"),
            revenue_allocation=Decimal("120000.00"),
            branch=branch_name,
        )
        db_session.add(change_wbe)

        # Create schedule baselines with DIFFERENT durations
        main_start = datetime(2026, 1, 1, tzinfo=UTC)
        main_end = datetime(2026, 6, 30, tzinfo=UTC)  # 6 months

        change_start = datetime(2026, 1, 1, tzinfo=UTC)
        change_end = datetime(2026, 9, 30, tzinfo=UTC)  # 9 months (50% longer)

        self._create_schedule_baseline(
            db_session, wbe_id, cet_id, "main", main_start, main_end, "LINEAR"
        )
        self._create_schedule_baseline(
            db_session, wbe_id, cet_id, branch_name, change_start, change_end, "LINEAR"
        )

        await db_session.commit()

        # Act
        result = await service._generate_time_series(project_id, branch_name)

        # Assert
        assert len(result) == 4, "Should return 4 time series (budget, pv, ev, ac)"

        # Get budget time series
        budget_series = next((ts for ts in result if ts.metric_name == "budget"), None)
        assert budget_series is not None, "Should have budget time series"

        data_points = budget_series.data_points
        assert len(data_points) > 1, "Should generate multiple weekly data points"

        # Find the point at 3 months (end of main's 50% mark)
        three_months_point = None
        for point in data_points:
            if point.week_start.month == 4 and point.week_start.day <= 7:
                three_months_point = point
                break

        assert three_months_point is not None, "Should find a point around 3 months"

        # At 3 months:
        # - Main (6-month): Should have ~50% of budget ($50k)
        # - Change (9-month): Should have ~33% of budget ($33k)
        main_at_3m = three_months_point.main_value or Decimal("0")
        change_at_3m = three_months_point.change_value or Decimal("0")

        # Main should be ahead because it's shorter duration
        assert main_at_3m > change_at_3m, (
            f"Main (6-month) should be ahead of Change (9-month) at 3 months: "
            f"main={main_at_3m}, change={change_at_3m}"
        )

        # Verify main has approximately 50% at midpoint
        assert (
            abs(main_at_3m - Decimal("50000.00")) < Decimal("10000.00")
        ), f"Main should have ~$50k at 3 months, got {main_at_3m}"

        # Verify change has approximately 33% at 3 months
        assert (
            abs(change_at_3m - Decimal("33333.00")) < Decimal("10000.00")
        ), f"Change should have ~$33k at 3 months, got {change_at_3m}"

    async def test_s_curve_empty_project(
        self, db_session: AsyncSession
    ) -> None:
        """Test S-curve generation when project has no WBEs or schedules.

        Edge Case 5: Empty Project
        - Project exists but has no WBEs or schedule baselines
        - Expected: Return empty list (graceful degradation)
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        project_id = uuid4()
        branch_name = "BR-test-empty"

        # Don't create any WBEs or schedules

        # Act
        result = await service._generate_time_series(project_id, branch_name)

        # Assert
        assert result == [], "Should return empty list for project with no schedules"

    async def test_s_curve_no_schedule_baselines(
        self, db_session: AsyncSession
    ) -> None:
        """Test S-curve generation when WBEs exist but have no schedule baselines.

        Edge Case 6: WBEs Without Schedule Baselines
        - Project has WBEs but no schedule baselines
        - Expected: Return empty list (can't generate time series without schedules)
        """
        # Arrange
        service = ImpactAnalysisService(db_session)
        project_id = uuid4()
        wbe_id = uuid4()
        cet_id = uuid4()
        branch_name = "BR-test-no-schedule"

        # Create cost element type
        cet = CostElementType(
            cost_element_type_id=cet_id,
            code="LABOR",
            name="Labor",
            description="Labor costs",
            branch="main",
        )
        db_session.add(cet)

        # Create WBE without schedule baseline
        main_wbe = WBE(
            wbe_id=wbe_id,
            project_id=project_id,
            code="1.1",
            name="Assembly Station",
            budget_allocation=Decimal("100000.00"),
            revenue_allocation=Decimal("120000.00"),
            branch="main",
        )
        db_session.add(main_wbe)

        await db_session.commit()

        # Act
        result = await service._generate_time_series(project_id, branch_name)

        # Assert
        assert result == [], "Should return empty list when no schedule baselines exist"

    def _create_schedule_baseline(
        self,
        db_session: AsyncSession,
        wbe_id: UUID,
        cost_element_type_id: UUID,
        branch: str,
        start_date: datetime,
        end_date: datetime,
        progression_type: str,
    ) -> ScheduleBaseline:
        """Helper method to create a complete schedule baseline with cost element.

        Args:
            db_session: Database session
            wbe_id: WBE root ID
            cost_element_type_id: Cost element type ID
            branch: Branch name
            start_date: Schedule start date
            end_date: Schedule end date
            progression_type: Progression type (LINEAR, GAUSSIAN, LOGARITHMIC)

        Returns:
            Created ScheduleBaseline instance
        """
        # Create cost element
        cost_elem = CostElement(
            cost_element_id=uuid4(),
            wbe_id=wbe_id,
            cost_element_type_id=cost_element_type_id,
            code="CE-001",
            name="Cost Element",
            budget_amount=Decimal("100000.00"),
            branch=branch,
        )
        db_session.add(cost_elem)

        # Create schedule baseline
        schedule = ScheduleBaseline(
            schedule_baseline_id=uuid4(),
            cost_element_id=cost_elem.cost_element_id,
            name=f"Schedule {branch}",
            start_date=start_date,
            end_date=end_date,
            progression_type=progression_type,
            branch=branch,
        )
        db_session.add(schedule)

        # Link schedule to cost element (inverted FK)
        cost_elem.schedule_baseline_id = schedule.schedule_baseline_id

        return schedule

    def _create_cost_element_type(
        self, db_session: AsyncSession, department_id: UUID
    ) -> UUID:
        """Helper method to create a cost element type.

        Args:
            db_session: Database session
            department_id: Department ID for the cost element type

        Returns:
            Created cost element type ID
        """
        cet_id = uuid4()
        cet = CostElementType(
            cost_element_type_id=cet_id,
            department_id=department_id,
            code="LABOR",
            name="Labor",
            description="Labor costs",
        )
        db_session.add(cet)
        return cet_id
