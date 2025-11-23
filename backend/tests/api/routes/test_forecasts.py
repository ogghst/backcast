"""Tests for Forecast API routes."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
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
    ForecastType,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)


def _post_forecast(client: TestClient, headers: dict[str, str], payload: dict) -> dict:
    """Helper to POST a forecast."""
    return client.post("/api/v1/forecasts/", headers=headers, json=payload)


def test_read_forecasts_empty_list(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading forecasts returns empty list when none exist."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Empty Forecasts Test",
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
        type_code=f"empty_forecasts_{uuid.uuid4().hex[:8]}",
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

    # Test empty list
    response = client.get(
        f"/api/v1/forecasts/?cost_element_id={ce.cost_element_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data or isinstance(data, list)
    if "data" in data:
        assert len(data["data"]) == 0
    else:
        assert len(data) == 0


def test_read_forecasts_list(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading forecasts returns list ordered by forecast_date DESC."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="List Forecasts Test",
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
        type_code=f"list_forecasts_{uuid.uuid4().hex[:8]}",
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
    )
    forecast3 = Forecast.model_validate(forecast3_in)
    db.add(forecast3)
    db.commit()
    db.refresh(forecast3)

    # Test list endpoint
    response = client.get(
        f"/api/v1/forecasts/?cost_element_id={ce.cost_element_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Handle both list and dict response formats
    if "data" in data:
        forecasts = data["data"]
    else:
        forecasts = data

    assert len(forecasts) == 3

    # Verify ordering by forecast_date DESC (newest first)
    assert forecasts[0]["forecast_date"] == "2024-07-02"
    assert forecasts[1]["forecast_date"] == "2024-07-01"
    assert forecasts[2]["forecast_date"] == "2024-06-30"


def test_read_forecast_by_id(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading a single forecast by ID."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Read Forecast Test",
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
        type_code=f"read_forecast_{uuid.uuid4().hex[:8]}",
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

    forecast_in = ForecastCreate(
        cost_element_id=ce.cost_element_id,
        forecast_date=date(2024, 6, 30),
        estimate_at_completion=Decimal("10000.00"),
        forecast_type=ForecastType.bottom_up,
        assumptions="Test assumptions",
        estimator_id=pm_user.id,
        is_current=True,
    )
    forecast = Forecast.model_validate(forecast_in)
    db.add(forecast)
    db.commit()
    db.refresh(forecast)

    # Test read endpoint
    response = client.get(
        f"/api/v1/forecasts/{forecast.forecast_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["forecast_id"] == str(forecast.forecast_id)
    assert data["forecast_date"] == "2024-06-30"
    assert float(data["estimate_at_completion"]) == 10000.00
    assert data["forecast_type"] == "bottom_up"
    assert data["assumptions"] == "Test assumptions"
    assert data["is_current"] is True


def test_read_forecast_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test reading non-existent forecast returns 404."""
    fake_id = uuid.uuid4()
    response = client.get(
        f"/api/v1/forecasts/{fake_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_forecast_success(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a forecast with valid data."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Create Forecast Test",
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
        type_code=f"create_forecast_{uuid.uuid4().hex[:8]}",
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

    # Get current user for estimator_id
    response_user = client.get("/api/v1/users/me", headers=superuser_token_headers)
    current_user_id = response_user.json()["id"]

    payload = {
        "cost_element_id": str(ce.cost_element_id),
        "forecast_date": "2024-06-30",
        "estimate_at_completion": "10000.00",
        "forecast_type": "bottom_up",
        "assumptions": "Test assumptions",
        "estimator_id": current_user_id,
        "is_current": True,
    }

    response = client.post(
        "/api/v1/forecasts/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cost_element_id"] == str(ce.cost_element_id)
    assert data["forecast_date"] == "2024-06-30"
    assert float(data["estimate_at_completion"]) == 10000.00
    assert data["forecast_type"] == "bottom_up"
    assert data["assumptions"] == "Test assumptions"
    assert data["is_current"] is True
    assert "forecast_id" in data


def test_create_forecast_future_date_warning(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating forecast with future date returns warning but succeeds."""
    # Create hierarchy (similar setup as above)
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Future Date Test",
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
        type_code=f"future_date_{uuid.uuid4().hex[:8]}",
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

    response_user = client.get("/api/v1/users/me", headers=superuser_token_headers)
    current_user_id = response_user.json()["id"]

    # Use future date
    from datetime import timedelta

    future_date = (date.today() + timedelta(days=1)).isoformat()

    payload = {
        "cost_element_id": str(ce.cost_element_id),
        "forecast_date": future_date,
        "estimate_at_completion": "10000.00",
        "forecast_type": "bottom_up",
        "estimator_id": current_user_id,
    }

    response = client.post(
        "/api/v1/forecasts/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert "warning" in data
    assert "future" in data["warning"].lower()


def test_create_forecast_max_dates_exceeded(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating forecast fails when max 3 forecast dates exceeded."""
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
        type_code=f"max_dates_{uuid.uuid4().hex[:8]}",
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

    response_user = client.get("/api/v1/users/me", headers=superuser_token_headers)
    current_user_id = response_user.json()["id"]

    # Create 3 forecasts with different dates
    for i in range(3):
        payload = {
            "cost_element_id": str(ce.cost_element_id),
            "forecast_date": f"2024-06-{30 + i}",
            "estimate_at_completion": "10000.00",
            "forecast_type": "bottom_up",
            "estimator_id": current_user_id,
        }
        response = client.post(
            "/api/v1/forecasts/",
            headers=superuser_token_headers,
            json=payload,
        )
        assert response.status_code == 200

    # Try to create 4th forecast with new date (should fail)
    payload = {
        "cost_element_id": str(ce.cost_element_id),
        "forecast_date": "2024-07-03",
        "estimate_at_completion": "10000.00",
        "forecast_type": "bottom_up",
        "estimator_id": current_user_id,
    }
    response = client.post(
        "/api/v1/forecasts/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 400
    assert (
        "maximum" in response.json()["detail"].lower()
        or "three" in response.json()["detail"].lower()
    )


def test_create_forecast_sets_other_to_not_current(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating forecast with is_current=True sets others to False."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Current Forecast Test",
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
        type_code=f"current_forecast_{uuid.uuid4().hex[:8]}",
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

    response_user = client.get("/api/v1/users/me", headers=superuser_token_headers)
    current_user_id = response_user.json()["id"]

    # Create first forecast with is_current=True
    payload1 = {
        "cost_element_id": str(ce.cost_element_id),
        "forecast_date": "2024-06-30",
        "estimate_at_completion": "10000.00",
        "forecast_type": "bottom_up",
        "estimator_id": current_user_id,
        "is_current": True,
    }
    response1 = client.post(
        "/api/v1/forecasts/",
        headers=superuser_token_headers,
        json=payload1,
    )
    assert response1.status_code == 200
    forecast1_id = response1.json()["forecast_id"]

    # Create second forecast with is_current=True
    payload2 = {
        "cost_element_id": str(ce.cost_element_id),
        "forecast_date": "2024-07-01",
        "estimate_at_completion": "11000.00",
        "forecast_type": "performance_based",
        "estimator_id": current_user_id,
        "is_current": True,
    }
    response2 = client.post(
        "/api/v1/forecasts/",
        headers=superuser_token_headers,
        json=payload2,
    )
    assert response2.status_code == 200
    forecast2_id = response2.json()["forecast_id"]

    # Verify first forecast is now is_current=False
    response = client.get(
        f"/api/v1/forecasts/{forecast1_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_current"] is False

    # Verify second forecast is is_current=True
    response = client.get(
        f"/api/v1/forecasts/{forecast2_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_current"] is True


def test_update_forecast_only_current_allowed(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating non-current forecast returns 400 error."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Update Forecast Test",
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
        type_code=f"update_forecast_{uuid.uuid4().hex[:8]}",
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

    # Create forecast with is_current=False
    forecast_in = ForecastCreate(
        cost_element_id=ce.cost_element_id,
        forecast_date=date(2024, 6, 30),
        estimate_at_completion=Decimal("10000.00"),
        forecast_type=ForecastType.bottom_up,
        estimator_id=pm_user.id,
        is_current=False,
    )
    forecast = Forecast.model_validate(forecast_in)
    db.add(forecast)
    db.commit()
    db.refresh(forecast)

    # Try to update non-current forecast (should fail)
    payload = {
        "estimate_at_completion": "12000.00",
    }
    response = client.put(
        f"/api/v1/forecasts/{forecast.forecast_id}",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 400
    assert "current" in response.json()["detail"].lower()


def test_update_forecast_success(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating current forecast succeeds."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Update Success Test",
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
        type_code=f"update_success_{uuid.uuid4().hex[:8]}",
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

    # Create forecast with is_current=True
    forecast_in = ForecastCreate(
        cost_element_id=ce.cost_element_id,
        forecast_date=date(2024, 6, 30),
        estimate_at_completion=Decimal("10000.00"),
        forecast_type=ForecastType.bottom_up,
        assumptions="Original assumptions",
        estimator_id=pm_user.id,
        is_current=True,
    )
    forecast = Forecast.model_validate(forecast_in)
    db.add(forecast)
    db.commit()
    db.refresh(forecast)

    # Update forecast
    payload = {
        "estimate_at_completion": "12000.00",
        "assumptions": "Updated assumptions",
    }
    response = client.put(
        f"/api/v1/forecasts/{forecast.forecast_id}",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert float(data["estimate_at_completion"]) == 12000.00
    assert data["assumptions"] == "Updated assumptions"


def test_delete_forecast_success(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test deleting a forecast succeeds."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Delete Forecast Test",
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
        type_code=f"delete_forecast_{uuid.uuid4().hex[:8]}",
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

    # Create forecast
    forecast_in = ForecastCreate(
        cost_element_id=ce.cost_element_id,
        forecast_date=date(2024, 6, 30),
        estimate_at_completion=Decimal("10000.00"),
        forecast_type=ForecastType.bottom_up,
        estimator_id=pm_user.id,
        is_current=False,
    )
    forecast = Forecast.model_validate(forecast_in)
    db.add(forecast)
    db.commit()
    db.refresh(forecast)

    # Delete forecast
    response = client.delete(
        f"/api/v1/forecasts/{forecast.forecast_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert "success" in response.json()["message"].lower()

    # Verify forecast is deleted
    response = client.get(
        f"/api/v1/forecasts/{forecast.forecast_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404


def test_delete_current_forecast_auto_promotes_previous(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test deleting current forecast auto-promotes previous forecast."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Auto Promote Test",
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
        type_code=f"auto_promote_{uuid.uuid4().hex[:8]}",
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

    # Delete current forecast (forecast2)
    response = client.delete(
        f"/api/v1/forecasts/{forecast2.forecast_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200

    # Verify forecast1 (previous by date) is now is_current=True
    response = client.get(
        f"/api/v1/forecasts/{forecast1.forecast_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_current"] is True

    # Verify forecast3 is still is_current=False
    response = client.get(
        f"/api/v1/forecasts/{forecast3.forecast_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_current"] is False


def test_create_forecast_invalid_cost_element(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test creating forecast with invalid cost element ID returns 400."""
    fake_id = uuid.uuid4()
    response_user = client.get("/api/v1/users/me", headers=superuser_token_headers)
    current_user_id = response_user.json()["id"]

    payload = {
        "cost_element_id": str(fake_id),
        "forecast_date": "2024-06-30",
        "estimate_at_completion": "10000.00",
        "forecast_type": "bottom_up",
        "estimator_id": current_user_id,
    }

    response = client.post(
        "/api/v1/forecasts/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 400
    assert "cost element" in response.json()["detail"].lower()


def test_create_forecast_invalid_forecast_type(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating forecast with invalid forecast_type returns 400."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Invalid Type Test",
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
        type_code=f"invalid_type_{uuid.uuid4().hex[:8]}",
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

    response_user = client.get("/api/v1/users/me", headers=superuser_token_headers)
    current_user_id = response_user.json()["id"]

    payload = {
        "cost_element_id": str(ce.cost_element_id),
        "forecast_date": "2024-06-30",
        "estimate_at_completion": "10000.00",
        "forecast_type": "invalid_type",
        "estimator_id": current_user_id,
    }

    response = client.post(
        "/api/v1/forecasts/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 400
    assert "forecast_type" in response.json()["detail"].lower()


def test_create_forecast_zero_eac(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating forecast with EAC = 0 returns 400."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Zero EAC Test",
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
        type_code=f"zero_eac_{uuid.uuid4().hex[:8]}",
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

    response_user = client.get("/api/v1/users/me", headers=superuser_token_headers)
    current_user_id = response_user.json()["id"]

    payload = {
        "cost_element_id": str(ce.cost_element_id),
        "forecast_date": "2024-06-30",
        "estimate_at_completion": "0.00",
        "forecast_type": "bottom_up",
        "estimator_id": current_user_id,
    }

    response = client.post(
        "/api/v1/forecasts/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 400
    assert "greater than zero" in response.json()["detail"].lower()


def test_delete_forecast_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test deleting non-existent forecast returns 404."""
    fake_id = uuid.uuid4()
    response = client.delete(
        f"/api/v1/forecasts/{fake_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404


def test_update_forecast_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test updating non-existent forecast returns 404."""
    fake_id = uuid.uuid4()
    payload = {
        "estimate_at_completion": "12000.00",
    }
    response = client.put(
        f"/api/v1/forecasts/{fake_id}",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 404


def test_create_forecast_same_date_allowed(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating multiple forecasts with same date is allowed (max 3 unique dates)."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Same Date Test",
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
        type_code=f"same_date_{uuid.uuid4().hex[:8]}",
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

    response_user = client.get("/api/v1/users/me", headers=superuser_token_headers)
    current_user_id = response_user.json()["id"]

    # Create 2 forecasts with same date (should be allowed)
    payload1 = {
        "cost_element_id": str(ce.cost_element_id),
        "forecast_date": "2024-06-30",
        "estimate_at_completion": "10000.00",
        "forecast_type": "bottom_up",
        "estimator_id": current_user_id,
    }
    response1 = client.post(
        "/api/v1/forecasts/",
        headers=superuser_token_headers,
        json=payload1,
    )
    assert response1.status_code == 200

    payload2 = {
        "cost_element_id": str(ce.cost_element_id),
        "forecast_date": "2024-06-30",  # Same date
        "estimate_at_completion": "11000.00",
        "forecast_type": "performance_based",
        "estimator_id": current_user_id,
    }
    response2 = client.post(
        "/api/v1/forecasts/",
        headers=superuser_token_headers,
        json=payload2,
    )
    assert response2.status_code == 200
