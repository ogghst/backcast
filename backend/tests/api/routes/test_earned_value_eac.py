"""Test EAC calculation in earned value endpoints with forecast date filtering."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Session

from app.models import (
    WBE,
    CostElement,
    Forecast,
    ForecastType,
    Project,
)


def test_get_cost_element_earned_value_with_forecast_before_control_date(
    session: Session,
) -> None:
    """Should return EAC from forecast when forecast_date <= control_date."""
    # Create test data
    project = Project(
        project_id=uuid.uuid4(),
        project_name="Test Project",
        created_by_id=uuid.uuid4(),
    )
    session.add(project)
    session.commit()

    wbe = WBE(
        wbe_id=uuid.uuid4(),
        project_id=project.project_id,
        wbe_code="WBE001",
        wbe_name="Test WBE",
        created_by_id=uuid.uuid4(),
    )
    session.add(wbe)
    session.commit()

    cost_element = CostElement(
        cost_element_id=uuid.uuid4(),
        wbe_id=wbe.wbe_id,
        cost_element_type_id=uuid.uuid4(),
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("10000.00"),
        revenue_plan=Decimal("12000.00"),
        status="active",
    )
    session.add(cost_element)
    session.commit()

    # Create forecast with forecast_date = Nov 21, 2025
    forecast = Forecast(
        forecast_id=uuid.uuid4(),
        cost_element_id=cost_element.cost_element_id,
        estimator_id=uuid.uuid4(),
        forecast_date=date(2025, 11, 21),
        estimate_at_completion=Decimal("15564.38"),
        forecast_type=ForecastType.bottom_up,
        is_current=True,
        created_at=datetime(2025, 11, 22, 22, 1, 29, tzinfo=timezone.utc),
        last_modified_at=datetime(2025, 11, 22, 22, 1, 29, tzinfo=timezone.utc),
    )
    session.add(forecast)
    session.commit()

    # Control date is Nov 22, 2025
    control_date = date(2025, 11, 22)

    # Import the function to test
    from app.api.routes.earned_value import _get_forecast_eac_map

    # Test the forecast retrieval
    forecast_map = _get_forecast_eac_map(
        session, [cost_element.cost_element_id], control_date
    )

    # Should find the forecast since forecast_date (Nov 21) <= control_date (Nov 22)
    assert cost_element.cost_element_id in forecast_map
    assert forecast_map[cost_element.cost_element_id] == Decimal("15564.38")


def test_get_cost_element_earned_value_with_forecast_after_control_date(
    session: Session,
) -> None:
    """Should NOT return EAC from forecast when forecast_date > control_date."""
    # Create test data
    project = Project(
        project_id=uuid.uuid4(),
        project_name="Test Project",
        created_by_id=uuid.uuid4(),
    )
    session.add(project)
    session.commit()

    wbe = WBE(
        wbe_id=uuid.uuid4(),
        project_id=project.project_id,
        wbe_code="WBE001",
        wbe_name="Test WBE",
        created_by_id=uuid.uuid4(),
    )
    session.add(wbe)
    session.commit()

    cost_element = CostElement(
        cost_element_id=uuid.uuid4(),
        wbe_id=wbe.wbe_id,
        cost_element_type_id=uuid.uuid4(),
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("10000.00"),
        revenue_plan=Decimal("12000.00"),
        status="active",
    )
    session.add(cost_element)
    session.commit()

    # Create forecast with forecast_date = Nov 23, 2025 (AFTER control date)
    forecast = Forecast(
        forecast_id=uuid.uuid4(),
        cost_element_id=cost_element.cost_element_id,
        estimator_id=uuid.uuid4(),
        forecast_date=date(2025, 11, 23),
        estimate_at_completion=Decimal("15564.38"),
        forecast_type=ForecastType.bottom_up,
        is_current=True,
        created_at=datetime(2025, 11, 22, 22, 1, 29, tzinfo=timezone.utc),
        last_modified_at=datetime(2025, 11, 22, 22, 1, 29, tzinfo=timezone.utc),
    )
    session.add(forecast)
    session.commit()

    # Control date is Nov 22, 2025
    control_date = date(2025, 11, 22)

    # Import the function to test
    from app.api.routes.earned_value import _get_forecast_eac_map

    # Test the forecast retrieval
    forecast_map = _get_forecast_eac_map(
        session, [cost_element.cost_element_id], control_date
    )

    # Should NOT find the forecast since forecast_date (Nov 23) > control_date (Nov 22)
    # Should return None (fallback to BAC)
    assert cost_element.cost_element_id in forecast_map
    assert forecast_map[cost_element.cost_element_id] is None
