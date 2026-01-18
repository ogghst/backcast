"""Performance tests for EVM calculations.

These tests verify that EVM calculations meet performance requirements
(< 500ms for typical queries) even with large datasets.
"""

import time
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.department import Department
from app.models.domain.progress_entry import ProgressEntry
from app.models.domain.project import Project
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.domain.user import User
from app.models.domain.wbe import WBE
from app.services.evm_service import EVMService


@pytest.mark.asyncio
@pytest.mark.performance
async def test_evm_calculation_performance_with_100_elements(db_session):
    """Verify EVM calculations complete within 500ms for 100 cost elements.

    This test creates 100 cost elements with full history (baselines,
    registrations, progress) and verifies that EVM metrics calculation
    completes within the required 500ms timeframe.

    Requirement: TC-1 - EVM calculations < 500ms
    """
    # Setup: Create test data
    department = Department(
        department_id=uuid4(),
        department_code="PERF-DEPT",
        department_name="Performance Test Department",
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(department)

    user = User(
        user_id=uuid4(),
        username="perfuser",
        email="perf@example.com",
        full_name="Performance User",
        department_id=department.department_id,
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(user)

    project = Project(
        project_id=uuid4(),
        project_code="PERF-PROJ",
        project_name="Performance Test Project",
        department_id=department.department_id,
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(project)

    wbe = WBE(
        wbe_id=uuid4(),
        wbe_code="PERF-WBE",
        wbe_name="Performance Test WBE",
        project_id=project.project_id,
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(wbe)

    cost_element_type = CostElementType(
        cost_element_type_id=uuid4(),
        cost_element_type_code="LABOR",
        cost_element_type_name="Labor",
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(cost_element_type)

    # Create 100 cost elements with baselines
    cost_elements = []
    for i in range(100):
        cost_element = CostElement(
            cost_element_id=uuid4(),
            wbe_id=wbe.wbe_id,
            cost_element_type_id=cost_element_type.cost_element_type_id,
            cost_element_code=f"CE-{i:04d}",
            cost_element_name=f"Cost Element {i}",
            budget_amount=Decimal("10000.00"),
            valid_time=None,
            transaction_time=None,
        )
        db_session.add(cost_element)
        cost_elements.append(cost_element)

        # Create baseline
        baseline = ScheduleBaseline(
            schedule_baseline_id=uuid4(),
            cost_element_id=cost_element.cost_element_id,
            planned_start_date=None,
            planned_end_date=None,
            valid_time=None,
            transaction_time=None,
        )
        db_session.add(baseline)

        # Create cost registration
        registration = CostRegistration(
            cost_registration_id=uuid4(),
            cost_element_id=cost_element.cost_element_id,
            reported_date=None,
            reported_by_user_id=user.user_id,
            actual_cost_amount=Decimal("5000.00"),
            valid_time=None,
            transaction_time=None,
        )
        db_session.add(registration)

        # Create progress entry
        progress = ProgressEntry(
            progress_entry_id=uuid4(),
            cost_element_id=cost_element.cost_element_id,
            progress_percentage=Decimal("50.00"),
            reported_date=None,
            reported_by_user_id=user.user_id,
            valid_time=None,
            transaction_time=None,
        )
        db_session.add(progress)

    await db_session.commit()

    # Act: Calculate EVM metrics for all cost elements and measure time
    evm_service = EVMService(db_session)

    start_time = time.time()
    results = []
    for cost_element in cost_elements:
        metrics = await evm_service.get_evm_metrics(cost_element.cost_element_id)
        results.append(metrics)
    end_time = time.time()

    total_time = (end_time - start_time) * 1000  # Convert to milliseconds
    avg_time_per_element = total_time / 100

    # Assert: Performance requirement met
    assert total_time < 500, (
        f"EVM calculations for 100 elements took {total_time:.2f}ms, "
        f"exceeding 500ms requirement (avg: {avg_time_per_element:.2f}ms per element)"
    )

    # Verify results are valid
    assert len(results) == 100
    for metrics in results:
        assert metrics.bac == Decimal("10000.00")
        assert metrics.ac == Decimal("5000.00")
        assert metrics.ev == Decimal("5000.00")  # 50% of 10000
        assert metrics.cv == Decimal("0.00")  # EV - AC = 5000 - 5000


@pytest.mark.asyncio
@pytest.mark.performance
async def test_cost_aggregation_performance_with_1000_entries(db_session):
    """Verify cost aggregation completes within 500ms for 1000 cost entries.

    This test creates 1000 cost registrations across multiple cost elements
    and verifies that cost aggregation queries complete within the required
    500ms timeframe.

    Requirement: TC-1 - EVM calculations < 500ms
    """
    # Setup: Create test data
    department = Department(
        department_id=uuid4(),
        department_code="PERF-DEPT-2",
        department_name="Performance Test Department 2",
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(department)

    user = User(
        user_id=uuid4(),
        username="perfuser2",
        email="perf2@example.com",
        full_name="Performance User 2",
        department_id=department.department_id,
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(user)

    project = Project(
        project_id=uuid4(),
        project_code="PERF-PROJ-2",
        project_name="Performance Test Project 2",
        department_id=department.department_id,
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(project)

    wbe = WBE(
        wbe_id=uuid4(),
        wbe_code="PERF-WBE-2",
        wbe_name="Performance Test WBE 2",
        project_id=project.project_id,
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(wbe)

    cost_element_type = CostElementType(
        cost_element_type_id=uuid4(),
        cost_element_type_code="MATERIAL",
        cost_element_type_name="Material",
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(cost_element_type)

    # Create 10 cost elements
    cost_elements = []
    for i in range(10):
        cost_element = CostElement(
            cost_element_id=uuid4(),
            wbe_id=wbe.wbe_id,
            cost_element_type_id=cost_element_type.cost_element_type_id,
            cost_element_code=f"CE-AGG-{i:04d}",
            cost_element_name=f"Cost Element for Aggregation {i}",
            budget_amount=Decimal("10000.00"),
            valid_time=None,
            transaction_time=None,
        )
        db_session.add(cost_element)
        cost_elements.append(cost_element)

    await db_session.flush()

    # Create 1000 cost registrations (100 per cost element)
    from datetime import datetime, timedelta

    base_date = datetime(2026, 1, 1)
    for cost_element in cost_elements:
        for i in range(100):
            registration = CostRegistration(
                cost_registration_id=uuid4(),
                cost_element_id=cost_element.cost_element_id,
                reported_date=base_date + timedelta(days=i),
                reported_by_user_id=user.user_id,
                actual_cost_amount=Decimal(f"{i * 10}.00"),
                valid_time=None,
                transaction_time=None,
            )
            db_session.add(registration)

    await db_session.commit()

    # Act: Aggregate costs by period and measure time
    from app.services.cost_aggregation_service import CostAggregationService

    aggregation_service = CostAggregationService(db_session)

    start_time = time.time()
    daily_costs = await aggregation_service.get_costs_by_period(
        cost_element_id=cost_elements[0].cost_element_id, period="daily"
    )
    end_time = time.time()

    total_time = (end_time - start_time) * 1000  # Convert to milliseconds

    # Assert: Performance requirement met
    assert total_time < 500, (
        f"Cost aggregation took {total_time:.2f}ms, "
        f"exceeding 500ms requirement"
    )

    # Verify results are valid
    assert len(daily_costs) == 100  # 100 daily entries


@pytest.mark.asyncio
@pytest.mark.performance
async def test_evm_query_with_complex_filters_performance(db_session):
    """Verify EVM queries with complex time-travel filters are performant.

    This test verifies that time-travel queries (which use bitemporal filtering)
    complete within acceptable timeframes even with complex filtering.
    """
    # Setup: Create test data with historical versions
    department = Department(
        department_id=uuid4(),
        department_code="PERF-DEPT-3",
        department_name="Performance Test Department 3",
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(department)

    user = User(
        user_id=uuid4(),
        username="perfuser3",
        email="perf3@example.com",
        full_name="Performance User 3",
        department_id=department.department_id,
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(user)

    project = Project(
        project_id=uuid4(),
        project_code="PERF-PROJ-3",
        project_name="Performance Test Project 3",
        department_id=department.department_id,
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(project)

    wbe = WBE(
        wbe_id=uuid4(),
        wbe_code="PERF-WBE-3",
        wbe_name="Performance Test WBE 3",
        project_id=project.project_id,
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(wbe)

    cost_element_type = CostElementType(
        cost_element_type_id=uuid4(),
        cost_element_type_code="EQUIPMENT",
        cost_element_type_name="Equipment",
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(cost_element_type)

    cost_element = CostElement(
        cost_element_id=uuid4(),
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        cost_element_code="CE-PERF-0001",
        cost_element_name="Cost Element for Time-Travel Performance",
        budget_amount=Decimal("10000.00"),
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(cost_element)

    baseline = ScheduleBaseline(
        schedule_baseline_id=uuid4(),
        cost_element_id=cost_element.cost_element_id,
        planned_start_date=None,
        planned_end_date=None,
        valid_time=None,
        transaction_time=None,
    )
    db_session.add(baseline)

    # Create 50 historical cost registrations
    from datetime import datetime, timedelta

    base_date = datetime(2026, 1, 1)
    for i in range(50):
        registration = CostRegistration(
            cost_registration_id=uuid4(),
            cost_element_id=cost_element.cost_element_id,
            reported_date=base_date + timedelta(days=i),
            reported_by_user_id=user.user_id,
            actual_cost_amount=Decimal(f"{i * 100}.00"),
            valid_time=None,
            transaction_time=None,
        )
        db_session.add(registration)

    await db_session.commit()

    # Act: Query with time-travel filter and measure time
    from app.services.cost_registration_service import CostRegistrationService

    registration_service = CostRegistrationService(db_session)

    start_time = time.time()
    # Query historical costs as of a specific date
    historical_costs = await registration_service.get_as_of(
        cost_element_id=cost_element.cost_element_id,
        as_of=base_date + timedelta(days=25),
    )
    end_time = time.time()

    total_time = (end_time - start_time) * 1000  # Convert to milliseconds

    # Assert: Performance requirement met
    assert total_time < 500, (
        f"Time-travel query took {total_time:.2f}ms, "
        f"exceeding 500ms requirement"
    )

    # Verify results are valid (should only see entries up to day 25)
    assert len(historical_costs) == 26  # Days 0-25 inclusive
