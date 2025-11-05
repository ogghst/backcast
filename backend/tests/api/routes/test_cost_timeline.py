"""Tests for cost timeline API endpoints."""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import (
    WBE,
    CostElement,
    CostElementCreate,
    CostRegistration,
    CostRegistrationCreate,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)
from tests.utils.cost_element_type import create_random_cost_element_type


def test_get_project_cost_timeline(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost timeline for a project with single cost registration."""
    # Create project manager user
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    # Create project
    project_in = ProjectCreate(
        project_name="Test Project",
        customer_name="Test Customer",
        contract_value=Decimal("100000.00"),
        start_date=date.today(),
        planned_completion_date=date.today() + timedelta(days=365),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create WBE
    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 1",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Create cost element type
    cost_element_type = create_random_cost_element_type(db)

    # Create cost element
    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    cost_element = CostElement.model_validate(ce_in)
    db.add(cost_element)
    db.commit()
    db.refresh(cost_element)

    # Create cost registration on a specific date
    registration_date = date.today() + timedelta(days=10)
    cr_data = CostRegistrationCreate(
        cost_element_id=cost_element.cost_element_id,
        registration_date=registration_date,
        amount=Decimal("5000.00"),
        cost_category="labor",
        description="Labor cost",
        is_quality_cost=False,
    )
    cr = CostRegistration.model_validate(
        {**cr_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr)
    db.commit()

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-timeline/",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    # Check structure
    assert "data" in content
    assert "total_cost" in content
    assert isinstance(content["data"], list)
    assert len(content["data"]) > 0

    # Check total cost
    assert float(content["total_cost"]) == 5000.00

    # Check that we have a point for the registration date
    registration_point = next(
        (
            p
            for p in content["data"]
            if p["point_date"] == registration_date.isoformat()
        ),
        None,
    )
    assert registration_point is not None
    assert float(registration_point["cumulative_cost"]) == 5000.00
    assert float(registration_point["period_cost"]) == 5000.00


def test_get_project_cost_timeline_multiple_dates(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost timeline with multiple cost registrations on different dates."""
    # Create project manager user
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    # Create project
    project_in = ProjectCreate(
        project_name="Test Project",
        customer_name="Test Customer",
        contract_value=Decimal("100000.00"),
        start_date=date.today(),
        planned_completion_date=date.today() + timedelta(days=365),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create WBE
    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 1",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Create cost element type
    cost_element_type = create_random_cost_element_type(db)

    # Create cost element
    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    cost_element = CostElement.model_validate(ce_in)
    db.add(cost_element)
    db.commit()
    db.refresh(cost_element)

    # Create cost registrations on different dates
    date1 = date.today() + timedelta(days=10)
    date2 = date.today() + timedelta(days=20)
    date3 = date.today() + timedelta(days=30)

    cr1_data = CostRegistrationCreate(
        cost_element_id=cost_element.cost_element_id,
        registration_date=date1,
        amount=Decimal("2000.00"),
        cost_category="labor",
        description="Cost 1",
        is_quality_cost=False,
    )
    cr1 = CostRegistration.model_validate(
        {**cr1_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr1)

    cr2_data = CostRegistrationCreate(
        cost_element_id=cost_element.cost_element_id,
        registration_date=date2,
        amount=Decimal("3000.00"),
        cost_category="materials",
        description="Cost 2",
        is_quality_cost=False,
    )
    cr2 = CostRegistration.model_validate(
        {**cr2_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr2)

    cr3_data = CostRegistrationCreate(
        cost_element_id=cost_element.cost_element_id,
        registration_date=date3,
        amount=Decimal("5000.00"),
        cost_category="labor",
        description="Cost 3",
        is_quality_cost=False,
    )
    cr3 = CostRegistration.model_validate(
        {**cr3_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr3)

    db.commit()

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-timeline/",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    # Check total cost
    assert float(content["total_cost"]) == 10000.00  # 2000 + 3000 + 5000

    # Check timeline points (should be sorted by date)
    assert len(content["data"]) == 3

    # Check first point (date1)
    point1 = next(p for p in content["data"] if p["point_date"] == date1.isoformat())
    assert float(point1["cumulative_cost"]) == 2000.00
    assert float(point1["period_cost"]) == 2000.00

    # Check second point (date2)
    point2 = next(p for p in content["data"] if p["point_date"] == date2.isoformat())
    assert float(point2["cumulative_cost"]) == 5000.00  # 2000 + 3000
    assert float(point2["period_cost"]) == 3000.00

    # Check third point (date3)
    point3 = next(p for p in content["data"] if p["point_date"] == date3.isoformat())
    assert float(point3["cumulative_cost"]) == 10000.00  # 2000 + 3000 + 5000
    assert float(point3["period_cost"]) == 5000.00


def test_get_project_cost_timeline_same_date(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost timeline with multiple registrations on same date (should sum)."""
    # Create project manager user
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    # Create project
    project_in = ProjectCreate(
        project_name="Test Project",
        customer_name="Test Customer",
        contract_value=Decimal("100000.00"),
        start_date=date.today(),
        planned_completion_date=date.today() + timedelta(days=365),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create WBE
    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 1",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Create cost element type
    cost_element_type = create_random_cost_element_type(db)

    # Create cost element
    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    cost_element = CostElement.model_validate(ce_in)
    db.add(cost_element)
    db.commit()
    db.refresh(cost_element)

    # Create multiple cost registrations on same date
    same_date = date.today() + timedelta(days=10)

    cr1_data = CostRegistrationCreate(
        cost_element_id=cost_element.cost_element_id,
        registration_date=same_date,
        amount=Decimal("2000.00"),
        cost_category="labor",
        description="Cost 1",
        is_quality_cost=False,
    )
    cr1 = CostRegistration.model_validate(
        {**cr1_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr1)

    cr2_data = CostRegistrationCreate(
        cost_element_id=cost_element.cost_element_id,
        registration_date=same_date,
        amount=Decimal("3000.00"),
        cost_category="materials",
        description="Cost 2",
        is_quality_cost=False,
    )
    cr2 = CostRegistration.model_validate(
        {**cr2_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr2)

    db.commit()

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-timeline/",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    # Check total cost
    assert float(content["total_cost"]) == 5000.00  # 2000 + 3000

    # Should have only one point (same date)
    assert len(content["data"]) == 1

    point = content["data"][0]
    assert point["point_date"] == same_date.isoformat()
    assert float(point["cumulative_cost"]) == 5000.00  # Sum of both
    assert float(point["period_cost"]) == 5000.00  # Sum of both


def test_get_project_cost_timeline_empty(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost timeline for project with no cost registrations."""
    # Create project manager user
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    # Create project
    project_in = ProjectCreate(
        project_name="Test Project",
        customer_name="Test Customer",
        contract_value=Decimal("100000.00"),
        start_date=date.today(),
        planned_completion_date=date.today() + timedelta(days=365),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Call the endpoint (no WBEs, no cost registrations)
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-timeline/",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()
    assert content["data"] == []
    assert float(content["total_cost"]) == 0.00


def test_get_project_cost_timeline_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test getting cost timeline for non-existent project."""
    fake_project_id = uuid.uuid4()

    response = client.get(
        f"{settings.API_V1_STR}/projects/{fake_project_id}/cost-timeline/",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()
