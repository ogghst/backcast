"""Tests for forecast validation helper functions."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app import crud
from app.api.routes.forecasts import (
    ensure_single_current_forecast,
    get_previous_forecast_for_promotion,
    validate_cost_element_exists,
    validate_eac,
    validate_forecast_date,
    validate_forecast_type,
    validate_max_forecast_dates,
)
from app.models import (
    WBE,
    CostElement,
    CostElementCreate,
    CostElementType,
    CostElementTypeCreate,
    Forecast,
    ForecastCreate,
    ForecastType,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)


def test_validate_cost_element_exists_success(db: Session) -> None:
    """Test validate_cost_element_exists returns CostElement when exists."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Helper Test Project",
        customer_name="Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine",
        revenue_allocation=50000.00,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    cet_in = CostElementTypeCreate(
        type_code=f"helper_test_{uuid.uuid4().hex[:8]}",
        type_name="Test Type",
        category_type="other",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="TEST",
        department_name="Test Dept",
        budget_bac=5000.00,
        revenue_plan=6000.00,
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Test validation succeeds
    result = validate_cost_element_exists(db, ce.cost_element_id)
    assert result == ce
    assert result.cost_element_id == ce.cost_element_id


def test_validate_cost_element_exists_not_found(db: Session) -> None:
    """Test validate_cost_element_exists raises HTTPException when not found."""
    fake_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        validate_cost_element_exists(db, fake_id)
    assert exc_info.value.status_code == 400
    assert "not found" in exc_info.value.detail.lower()


def test_validate_forecast_date_past_date() -> None:
    """Test validate_forecast_date returns None warning for past date."""
    past_date = date.today() - timedelta(days=1)
    warning = validate_forecast_date(past_date)
    assert warning is None


def test_validate_forecast_date_future_date() -> None:
    """Test validate_forecast_date returns warning dict for future date."""
    future_date = date.today() + timedelta(days=1)
    warning = validate_forecast_date(future_date)
    assert warning is not None
    assert "warning" in warning
    assert "future" in warning["warning"].lower()


def test_validate_forecast_type_valid() -> None:
    """Test validate_forecast_type accepts valid enum values."""
    # Should not raise for valid types
    validate_forecast_type(ForecastType.bottom_up)
    validate_forecast_type(ForecastType.performance_based)
    validate_forecast_type(ForecastType.management_judgment)


def test_validate_forecast_type_invalid() -> None:
    """Test validate_forecast_type raises HTTPException for invalid type."""
    with pytest.raises(HTTPException) as exc_info:
        validate_forecast_type("invalid_type")  # type: ignore
    assert exc_info.value.status_code == 400
    assert "forecast_type" in exc_info.value.detail.lower()


def test_validate_eac_positive() -> None:
    """Test validate_eac accepts positive values."""
    # Should not raise for positive values
    validate_eac(Decimal("100.00"))
    validate_eac(Decimal("0.01"))


def test_validate_eac_zero() -> None:
    """Test validate_eac raises HTTPException for zero."""
    with pytest.raises(HTTPException) as exc_info:
        validate_eac(Decimal("0.00"))
    assert exc_info.value.status_code == 400
    assert (
        "positive" in exc_info.value.detail.lower()
        or "greater than zero" in exc_info.value.detail.lower()
    )


def test_validate_eac_negative() -> None:
    """Test validate_eac raises HTTPException for negative values."""
    with pytest.raises(HTTPException) as exc_info:
        validate_eac(Decimal("-100.00"))
    assert exc_info.value.status_code == 400
    assert (
        "positive" in exc_info.value.detail.lower()
        or "greater than zero" in exc_info.value.detail.lower()
    )


def test_validate_max_forecast_dates_under_limit(db: Session) -> None:
    """Test validate_max_forecast_dates allows up to 3 unique dates."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Max Dates Test",
        customer_name="Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine",
        revenue_allocation=50000.00,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    cet_in = CostElementTypeCreate(
        type_code=f"max_dates_test_{uuid.uuid4().hex[:8]}",
        type_name="Test Type",
        category_type="other",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="TEST",
        department_name="Test Dept",
        budget_bac=5000.00,
        revenue_plan=6000.00,
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Create 2 forecasts with different dates (under limit)
    for i in range(2):
        forecast_in = ForecastCreate(
            cost_element_id=ce.cost_element_id,
            forecast_date=date(2024, 6, 30 + i),
            estimate_at_completion=Decimal("10000.00"),
            forecast_type=ForecastType.bottom_up,
            estimator_id=pm_user.id,
        )
        forecast = Forecast.model_validate(forecast_in)
        db.add(forecast)
    db.commit()

    # Should not raise for 2 dates (under limit of 3)
    validate_max_forecast_dates(db, ce.cost_element_id, date(2024, 7, 2))


def test_validate_max_forecast_dates_at_limit(db: Session) -> None:
    """Test validate_max_forecast_dates allows exactly 3 unique dates."""
    # Create hierarchy (similar setup as above)
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Max Dates Limit Test",
        customer_name="Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine",
        revenue_allocation=50000.00,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    cet_in = CostElementTypeCreate(
        type_code=f"max_dates_limit_{uuid.uuid4().hex[:8]}",
        type_name="Test Type",
        category_type="other",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="TEST",
        department_name="Test Dept",
        budget_bac=5000.00,
        revenue_plan=6000.00,
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Create 3 forecasts with different dates (at limit)
    for i in range(3):
        forecast_in = ForecastCreate(
            cost_element_id=ce.cost_element_id,
            forecast_date=date(2024, 6, 30 + i),
            estimate_at_completion=Decimal("10000.00"),
            forecast_type=ForecastType.bottom_up,
            estimator_id=pm_user.id,
        )
        forecast = Forecast.model_validate(forecast_in)
        db.add(forecast)
    db.commit()

    # Should not raise for 3 dates (at limit)
    # If trying to add a 4th unique date, should raise
    with pytest.raises(HTTPException) as exc_info:
        validate_max_forecast_dates(db, ce.cost_element_id, date(2024, 7, 3))
    assert exc_info.value.status_code == 400
    assert (
        "maximum" in exc_info.value.detail.lower()
        or "three" in exc_info.value.detail.lower()
    )


def test_ensure_single_current_forecast(db: Session) -> None:
    """Test ensure_single_current_forecast sets other forecasts to is_current=False."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Single Current Test",
        customer_name="Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine",
        revenue_allocation=50000.00,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    cet_in = CostElementTypeCreate(
        type_code=f"single_current_{uuid.uuid4().hex[:8]}",
        type_name="Test Type",
        category_type="other",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="TEST",
        department_name="Test Dept",
        budget_bac=5000.00,
        revenue_plan=6000.00,
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Create 2 forecasts, both with is_current=True
    forecast1_in = ForecastCreate(
        cost_element_id=ce.cost_element_id,
        forecast_date=date(2024, 6, 30),
        estimate_at_completion=Decimal("10000.00"),
        forecast_type=ForecastType.bottom_up,
        estimator_id=pm_user.id,
        is_current=True,
    )
    forecast1 = Forecast.model_validate(forecast1_in)
    db.add(forecast1)
    db.commit()
    db.refresh(forecast1)

    forecast2_in = ForecastCreate(
        cost_element_id=ce.cost_element_id,
        forecast_date=date(2024, 7, 1),
        estimate_at_completion=Decimal("11000.00"),
        forecast_type=ForecastType.performance_based,
        estimator_id=pm_user.id,
        is_current=True,
    )
    forecast2 = Forecast.model_validate(forecast2_in)
    db.add(forecast2)
    db.commit()
    db.refresh(forecast2)

    # Call ensure_single_current_forecast for forecast2
    ensure_single_current_forecast(db, ce.cost_element_id, forecast2.forecast_id)

    # Refresh from database
    db.refresh(forecast1)
    db.refresh(forecast2)

    # forecast1 should be is_current=False, forecast2 should be is_current=True
    assert forecast1.is_current is False
    assert forecast2.is_current is True


def test_get_previous_forecast_for_promotion(db: Session) -> None:
    """Test get_previous_forecast_for_promotion returns previous forecast by date."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Previous Forecast Test",
        customer_name="Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine",
        revenue_allocation=50000.00,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    cet_in = CostElementTypeCreate(
        type_code=f"previous_forecast_{uuid.uuid4().hex[:8]}",
        type_name="Test Type",
        category_type="other",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="TEST",
        department_name="Test Dept",
        budget_bac=5000.00,
        revenue_plan=6000.00,
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Create 3 forecasts with different dates
    forecast1_in = ForecastCreate(
        cost_element_id=ce.cost_element_id,
        forecast_date=date(2024, 6, 30),
        estimate_at_completion=Decimal("10000.00"),
        forecast_type=ForecastType.bottom_up,
        estimator_id=pm_user.id,
        is_current=False,
    )
    forecast1 = Forecast.model_validate(forecast1_in)
    db.add(forecast1)
    db.commit()
    db.refresh(forecast1)

    forecast2_in = ForecastCreate(
        cost_element_id=ce.cost_element_id,
        forecast_date=date(2024, 7, 1),
        estimate_at_completion=Decimal("11000.00"),
        forecast_type=ForecastType.performance_based,
        estimator_id=pm_user.id,
        is_current=True,  # Current forecast
    )
    forecast2 = Forecast.model_validate(forecast2_in)
    db.add(forecast2)
    db.commit()
    db.refresh(forecast2)

    forecast3_in = ForecastCreate(
        cost_element_id=ce.cost_element_id,
        forecast_date=date(2024, 7, 2),
        estimate_at_completion=Decimal("12000.00"),
        forecast_type=ForecastType.management_judgment,
        estimator_id=pm_user.id,
        is_current=False,
    )
    forecast3 = Forecast.model_validate(forecast3_in)
    db.add(forecast3)
    db.commit()
    db.refresh(forecast3)

    # Get previous forecast for forecast2 (should be forecast1, the most recent before forecast2)
    previous = get_previous_forecast_for_promotion(
        db, ce.cost_element_id, forecast2.forecast_id
    )
    assert previous is not None
    assert previous.forecast_id == forecast1.forecast_id

    # Get previous forecast for forecast1 (should be None, as it's the oldest)
    previous_none = get_previous_forecast_for_promotion(
        db, ce.cost_element_id, forecast1.forecast_id
    )
    assert previous_none is None
