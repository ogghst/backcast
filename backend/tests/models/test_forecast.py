"""Tests for Forecast model."""
import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    WBE,
    CostElement,
    CostElementCreate,
    CostElementType,
    CostElementTypeCreate,
    Forecast,
    ForecastCreate,
    ForecastPublic,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)


def test_create_forecast(db: Session) -> None:
    """Test creating a forecast."""
    # Create full hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Forecast Test Project",
        customer_name="Test Customer",
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
        machine_type="Test Machine",
        revenue_allocation=50000.00,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    cet_in = CostElementTypeCreate(
        type_code=f"forecast_test_{uuid.uuid4().hex[:8]}",
        type_name="Test Engineering",
        category_type="engineering_mechanical",
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
        department_code="ENG",
        department_name="Engineering",
        budget_bac=10000.00,
        revenue_plan=12000.00,
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Create forecast
    forecast_in = ForecastCreate(
        cost_element_id=ce.cost_element_id,
        forecast_date=date(2024, 6, 30),
        estimate_at_completion=15000.00,
        forecast_type="bottom_up",
        assumptions="Based on current performance trends",
        estimator_id=pm_user.id,
        is_current=True,
    )

    forecast = Forecast.model_validate(forecast_in)
    db.add(forecast)
    db.commit()
    db.refresh(forecast)

    # Verify forecast was created
    assert forecast.forecast_id is not None
    assert forecast.cost_element_id == ce.cost_element_id
    assert forecast.estimate_at_completion == 15000.00
    assert forecast.forecast_type == "bottom_up"
    assert forecast.is_current is True
    assert hasattr(forecast, "cost_element")  # Relationship should exist


def test_forecast_type_enum(db: Session) -> None:
    """Test that forecast_type is validated."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Forecast Type Test",
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
        type_code=f"ftype_test_{uuid.uuid4().hex[:8]}",
        type_name="Test Type",
        category_type="other",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    # Test valid forecast types
    valid_types = ["bottom_up", "performance_based", "management_judgment"]
    for forecast_type in valid_types:
        ce_in = CostElementCreate(
            wbe_id=wbe.wbe_id,
            cost_element_type_id=cet.cost_element_type_id,
            department_code=f"TEST_{forecast_type}",
            department_name=f"Test Dept {forecast_type}",
            budget_bac=5000.00,
            revenue_plan=6000.00,
            status="active",
        )
        ce = CostElement.model_validate(ce_in)
        db.add(ce)
        db.commit()
        db.refresh(ce)

        forecast_in = ForecastCreate(
            cost_element_id=ce.cost_element_id,
            forecast_date=date(2024, 6, 30),
            estimate_at_completion=10000.00,
            forecast_type=forecast_type,
            estimator_id=pm_user.id,
        )
        forecast = Forecast.model_validate(forecast_in)
        db.add(forecast)
        db.commit()
        db.refresh(forecast)
        assert forecast.forecast_type == forecast_type


def test_forecast_public_schema() -> None:
    """Test ForecastPublic schema for API responses."""
    import datetime

    forecast_id = uuid.uuid4()
    ce_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    forecast_public = ForecastPublic(
        forecast_id=forecast_id,
        cost_element_id=ce_id,
        forecast_date=date(2024, 9, 30),
        estimate_at_completion=20000.00,
        forecast_type="performance_based",
        assumptions="Public test assumptions",
        estimator_id=user_id,
        is_current=False,
        created_at=now,
        last_modified_at=now,
    )

    assert forecast_public.forecast_id == forecast_id
    assert forecast_public.estimate_at_completion == 20000.00
    assert forecast_public.forecast_type == "performance_based"
    assert forecast_public.is_current is False
