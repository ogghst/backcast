import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import (
    WBE,
    CostElement,
    CostElementCreate,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)
from tests.utils.cost_element_type import create_random_cost_element_type
from tests.utils.user import set_time_machine_date


def test_get_project_budget_summary(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting project-level budget summary with WBEs and cost elements."""
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

    # Create WBE 1
    wbe1_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 1",
        revenue_allocation=Decimal("60000.00"),
        status="designing",
    )
    wbe1 = WBE.model_validate(wbe1_in)
    db.add(wbe1)
    db.commit()
    db.refresh(wbe1)

    # Create WBE 2
    wbe2_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 2",
        revenue_allocation=Decimal("40000.00"),
        status="designing",
    )
    wbe2 = WBE.model_validate(wbe2_in)
    db.add(wbe2)
    db.commit()
    db.refresh(wbe2)

    # Create cost element type
    cost_element_type = create_random_cost_element_type(db)

    # Create cost elements for WBE 1
    ce1_in = CostElementCreate(
        wbe_id=wbe1.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    ce1 = CostElement.model_validate(ce1_in)
    db.add(ce1)

    ce2_in = CostElementCreate(
        wbe_id=wbe1.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="PROC",
        department_name="Procurement",
        budget_bac=Decimal("15000.00"),
        revenue_plan=Decimal("20000.00"),
        status="active",
    )
    ce2 = CostElement.model_validate(ce2_in)
    db.add(ce2)

    # Create cost elements for WBE 2
    ce3_in = CostElementCreate(
        wbe_id=wbe2.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("18000.00"),
        revenue_plan=Decimal("22000.00"),
        status="active",
    )
    ce3 = CostElement.model_validate(ce3_in)
    db.add(ce3)
    db.commit()

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/budget-summary/project/{project.project_id}",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    # Check structure
    assert "level" in content
    assert content["level"] == "project"
    assert "revenue_limit" in content
    assert "total_revenue_allocated" in content
    assert "total_budget_bac" in content
    assert "total_revenue_plan" in content
    assert "remaining_revenue" in content
    assert "revenue_utilization_percent" in content

    # Check calculated values
    assert float(content["revenue_limit"]) == 100000.00  # contract_value
    assert float(content["total_revenue_allocated"]) == 100000.00  # 60000 + 40000
    assert float(content["total_budget_bac"]) == 53000.00  # 20000 + 15000 + 18000
    assert float(content["total_revenue_plan"]) == 67000.00  # 25000 + 20000 + 22000
    assert float(content["remaining_revenue"]) == 0.00  # 100000 - 100000
    assert (
        float(content["revenue_utilization_percent"]) == 100.0
    )  # (100000 / 100000) * 100


def test_project_budget_summary_respects_control_date(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Ensure only WBEs and cost elements created on/before control date are included."""
    # Create project manager user
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Time Machine Project",
        customer_name="Test Customer",
        contract_value=Decimal("150000.00"),
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    control_date = date(2024, 2, 15)
    early_dt = datetime(2024, 1, 10, tzinfo=timezone.utc)
    late_dt = datetime(2024, 3, 15, tzinfo=timezone.utc)

    # Create WBEs with different created_at timestamps
    wbe1 = WBE.model_validate(
        WBECreate(
            project_id=project.project_id,
            machine_type="Early Machine",
            revenue_allocation=Decimal("80000.00"),
            status="designing",
        )
    )
    wbe1.created_at = early_dt
    db.add(wbe1)

    wbe2 = WBE.model_validate(
        WBECreate(
            project_id=project.project_id,
            machine_type="Late Machine",
            revenue_allocation=Decimal("70000.00"),
            status="designing",
        )
    )
    wbe2.created_at = late_dt
    db.add(wbe2)
    db.commit()
    db.refresh(wbe1)
    db.refresh(wbe2)

    cost_element_type = create_random_cost_element_type(db)

    # Early cost elements (should be counted)
    ce1 = CostElement.model_validate(
        CostElementCreate(
            wbe_id=wbe1.wbe_id,
            cost_element_type_id=cost_element_type.cost_element_type_id,
            department_code="ENG",
            department_name="Engineering",
            budget_bac=Decimal("30000.00"),
            revenue_plan=Decimal("35000.00"),
            status="active",
        )
    )
    ce1.created_at = early_dt
    db.add(ce1)

    ce2 = CostElement.model_validate(
        CostElementCreate(
            wbe_id=wbe1.wbe_id,
            cost_element_type_id=cost_element_type.cost_element_type_id,
            department_code="PROC",
            department_name="Procurement",
            budget_bac=Decimal("10000.00"),
            revenue_plan=Decimal("12000.00"),
            status="active",
        )
    )
    ce2.created_at = early_dt + timedelta(days=1)
    db.add(ce2)

    # Late cost element (should be excluded)
    ce3 = CostElement.model_validate(
        CostElementCreate(
            wbe_id=wbe2.wbe_id,
            cost_element_type_id=cost_element_type.cost_element_type_id,
            department_code="MFG",
            department_name="Manufacturing",
            budget_bac=Decimal("20000.00"),
            revenue_plan=Decimal("25000.00"),
            status="active",
        )
    )
    ce3.created_at = late_dt
    db.add(ce3)
    db.commit()

    # Set control date for the authenticated user
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        f"{settings.API_V1_STR}/budget-summary/project/{project.project_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()

    # Only early WBE and cost elements should be included
    assert float(content["total_revenue_allocated"]) == 80000.00
    assert float(content["total_budget_bac"]) == 40000.00  # 30k + 10k
    assert float(content["total_revenue_plan"]) == 47000.00  # 35k + 12k


def test_get_project_budget_summary_empty_project(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting project-level budget summary for project with no WBEs."""
    # Create project manager user
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    # Create project
    project_in = ProjectCreate(
        project_name="Empty Project",
        customer_name="Test Customer",
        contract_value=Decimal("50000.00"),
        start_date=date.today(),
        planned_completion_date=date.today() + timedelta(days=365),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/budget-summary/project/{project.project_id}",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    assert content["level"] == "project"
    assert float(content["revenue_limit"]) == 50000.00
    assert float(content["total_revenue_allocated"]) == 0.00
    assert float(content["total_budget_bac"]) == 0.00
    assert float(content["total_revenue_plan"]) == 0.00
    assert float(content["remaining_revenue"]) == 50000.00
    assert float(content["revenue_utilization_percent"]) == 0.0


def test_get_project_budget_summary_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test getting project budget summary for non-existent project."""
    fake_project_id = uuid.uuid4()

    response = client.get(
        f"{settings.API_V1_STR}/budget-summary/project/{fake_project_id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()


def test_get_wbe_budget_summary(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting WBE-level budget summary with cost elements."""
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

    # Create cost elements
    ce1_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("15000.00"),
        revenue_plan=Decimal("20000.00"),
        status="active",
    )
    ce1 = CostElement.model_validate(ce1_in)
    db.add(ce1)

    ce2_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="PROC",
        department_name="Procurement",
        budget_bac=Decimal("12000.00"),
        revenue_plan=Decimal("15000.00"),
        status="active",
    )
    ce2 = CostElement.model_validate(ce2_in)
    db.add(ce2)
    db.commit()

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/budget-summary/wbe/{wbe.wbe_id}",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    # Check structure
    assert "level" in content
    assert content["level"] == "wbe"
    assert "revenue_limit" in content
    assert "total_revenue_allocated" in content
    assert "total_budget_bac" in content
    assert "total_revenue_plan" in content
    assert "remaining_revenue" in content
    assert "revenue_utilization_percent" in content

    # Check calculated values
    assert float(content["revenue_limit"]) == 50000.00  # wbe.revenue_allocation
    assert (
        float(content["total_revenue_allocated"]) == 35000.00
    )  # 20000 + 15000 (sum of revenue_plan)
    assert float(content["total_budget_bac"]) == 27000.00  # 15000 + 12000
    assert float(content["total_revenue_plan"]) == 35000.00  # 20000 + 15000
    assert float(content["remaining_revenue"]) == 15000.00  # 50000 - 35000
    assert (
        float(content["revenue_utilization_percent"]) == 70.0
    )  # (35000 / 50000) * 100


def test_get_wbe_budget_summary_empty_wbe(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting WBE-level budget summary for WBE with no cost elements."""
    from datetime import date, timedelta

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
        machine_type="Empty Machine",
        revenue_allocation=Decimal("30000.00"),
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/budget-summary/wbe/{wbe.wbe_id}",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    assert content["level"] == "wbe"
    assert float(content["revenue_limit"]) == 30000.00
    assert float(content["total_revenue_allocated"]) == 0.00
    assert float(content["total_budget_bac"]) == 0.00
    assert float(content["total_revenue_plan"]) == 0.00
    assert float(content["remaining_revenue"]) == 30000.00
    assert float(content["revenue_utilization_percent"]) == 0.0


def test_get_wbe_budget_summary_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test getting WBE budget summary for non-existent WBE."""
    fake_wbe_id = uuid.uuid4()

    response = client.get(
        f"{settings.API_V1_STR}/budget-summary/wbe/{fake_wbe_id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()
