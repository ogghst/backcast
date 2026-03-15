"""Integration test for S-Curve time series generation bug fix.

This test reproduces the issue where main and change branch S-curves
are identical when they should be different due to cost element modifications.

The root cause: The implementation needs to properly query budget_allocation
from WBEs, not cost_element budget_amount.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.department import Department
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.domain.wbe import WBE
from app.services.impact_analysis_service import ImpactAnalysisService


@pytest.mark.asyncio
async def test_s_curve_shows_differences_when_wbe_budget_changes(
    db_session: AsyncSession,
) -> None:
    """Test that S-curve shows different values when WBE budget changes on change branch.

    This is the BUG FIX TEST case:
    - Main branch: WBE with $100,000 budget_allocation
    - Change branch: Same WBE with $150,000 budget_allocation (50% increase)
    - Expected: Change branch S-curve values should be 50% higher than main branch
    - Bug: Both curves are identical (the issue reported by user)
    """
    # Arrange
    service = ImpactAnalysisService(db_session)
    project_id = uuid4()
    wbe_id = uuid4()
    dept_id = uuid4()
    user_id = uuid4()  # For created_by field
    branch_name = "BR-CO-2026-001"

    # Create department
    dept = Department(
        department_id=dept_id,
        code="ENG",
        name="Engineering",
        manager_id=user_id,
    )
    db_session.add(dept)

    # Create cost element type (not branchable, no branch field)
    cet = CostElementType(
        cost_element_type_id=uuid4(),
        department_id=dept_id,
        code="LABOR",
        name="Labor",
        description="Labor costs",
        created_by=user_id,
    )
    db_session.add(cet)

    # Create main branch WBE with $100k budget
    main_wbe = WBE(
        wbe_id=wbe_id,
        project_id=project_id,
        code="1.1",
        name="Assembly Station",
        budget_allocation=Decimal("100000.00"),  # Main: $100k
        revenue_allocation=Decimal("120000.00"),
        branch="main",
    )
    db_session.add(main_wbe)

    # Create change branch WBE with $150k budget (50% increase)
    change_wbe = WBE(
        wbe_id=wbe_id,
        project_id=project_id,
        code="1.1",
        name="Assembly Station",
        budget_allocation=Decimal("150000.00"),  # Change: $150k (50% higher)
        revenue_allocation=Decimal("180000.00"),
        branch=branch_name,
    )
    db_session.add(change_wbe)

    # Create schedule baselines with same dates
    schedule_start = datetime(2026, 1, 1, tzinfo=UTC)
    schedule_end = datetime(2026, 12, 31, tzinfo=UTC)

    # Main branch schedule baseline
    main_cost_elem = CostElement(
        cost_element_id=uuid4(),
        wbe_id=wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        code="CE-001",
        name="Labor Cost",
        budget_amount=Decimal("100000.00"),
        branch="main",
        created_by=user_id,
    )
    db_session.add(main_cost_elem)

    main_schedule = ScheduleBaseline(
        schedule_baseline_id=uuid4(),
        cost_element_id=main_cost_elem.cost_element_id,
        name="Main Schedule",
        start_date=schedule_start,
        end_date=schedule_end,
        progression_type="LINEAR",
        branch="main",
        created_by=user_id,
    )
    db_session.add(main_schedule)
    main_cost_elem.schedule_baseline_id = main_schedule.schedule_baseline_id

    # Change branch schedule baseline
    change_cost_elem = CostElement(
        cost_element_id=uuid4(),
        wbe_id=wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        code="CE-001",
        name="Labor Cost",
        budget_amount=Decimal("150000.00"),  # Higher budget on change branch
        branch=branch_name,
        created_by=user_id,
    )
    db_session.add(change_cost_elem)

    change_schedule = ScheduleBaseline(
        schedule_baseline_id=uuid4(),
        cost_element_id=change_cost_elem.cost_element_id,
        name="Change Schedule",
        start_date=schedule_start,
        end_date=schedule_end,
        progression_type="LINEAR",
        branch=branch_name,
        created_by=user_id,
    )
    db_session.add(change_schedule)
    change_cost_elem.schedule_baseline_id = change_schedule.schedule_baseline_id

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

    # CRITICAL ASSERTION: The curves should be different!
    # At any given week, change_value should be 1.5x main_value
    differences_found = False
    for i, point in enumerate(data_points):
        main_val = point.main_value or Decimal("0")
        change_val = point.change_value or Decimal("0")

        # Skip first and last points where values might be zero
        if 0 < i < len(data_points) - 1:
            # Change should be 1.5x main (50% increase)
            if main_val > 0:
                ratio = change_val / main_val
                # Allow small tolerance for floating point arithmetic
                if abs(ratio - Decimal("1.5")) > Decimal("0.01"):
                    # This is expected - they should be different
                    differences_found = True
                    print(
                        f"Week {point.week_start}: main={main_val}, change={change_val}, ratio={ratio}"
                    )
                    break

    # Verify that curves are NOT identical
    final_main = data_points[-1].main_value or Decimal("0")
    final_change = data_points[-1].change_value or Decimal("0")

    assert differences_found or (
        abs(final_main - Decimal("100000.00")) < Decimal("1000.00")
        and abs(final_change - Decimal("150000.00")) < Decimal("1000.00")
    ), (
        f"BUG: S-curves are identical! Main={final_main}, Change={final_change}. "
        f"Expected change to be 1.5x main. "
        f"This indicates the implementation is not correctly reading WBE.budget_allocation."
    )

    # Final verification
    assert final_main == Decimal("100000.00"), (
        f"Main final value should be $100k, got {final_main}"
    )
    assert final_change == Decimal("150000.00"), (
        f"Change final value should be $150k, got {final_change}"
    )
