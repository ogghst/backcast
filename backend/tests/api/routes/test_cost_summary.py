"""Tests for Cost Summary API routes."""
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
    CostRegistration,
    CostRegistrationCreate,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)
from tests.utils.cost_element_type import create_random_cost_element_type
from tests.utils.user import set_time_machine_date


def test_get_cost_element_cost_summary(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost-element-level cost summary with multiple registrations."""

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

    # Create cost element with budget
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

    # Create cost registrations
    cr1_data = CostRegistrationCreate(
        cost_element_id=cost_element.cost_element_id,
        registration_date=date.today(),
        amount=Decimal("5000.00"),
        cost_category="labor",
        description="Labor cost 1",
        is_quality_cost=False,
    )
    cr1 = CostRegistration.model_validate(
        {**cr1_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr1)

    cr2_data = CostRegistrationCreate(
        cost_element_id=cost_element.cost_element_id,
        registration_date=date.today(),
        amount=Decimal("3000.00"),
        cost_category="materials",
        description="Materials cost",
        is_quality_cost=False,
    )
    cr2 = CostRegistration.model_validate(
        {**cr2_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr2)

    cr3_data = CostRegistrationCreate(
        cost_element_id=cost_element.cost_element_id,
        registration_date=date.today(),
        amount=Decimal("2000.00"),
        cost_category="labor",
        description="Quality cost",
        is_quality_cost=True,
    )
    cr3 = CostRegistration.model_validate(
        {**cr3_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr3)

    db.commit()

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/cost-summary/cost-element/{cost_element.cost_element_id}",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    # Check structure
    assert "level" in content
    assert content["level"] == "cost-element"
    assert "total_cost" in content
    assert "budget_bac" in content
    assert "cost_registration_count" in content
    assert "cost_percentage_of_budget" in content
    assert "cost_element_id" in content

    # Check calculated values (all costs: 5000 + 3000 + 2000 = 10000)
    assert float(content["total_cost"]) == 10000.00
    assert float(content["budget_bac"]) == 20000.00
    assert content["cost_registration_count"] == 3
    assert float(content["cost_percentage_of_budget"]) == 50.0  # (10000 / 20000) * 100
    assert content["cost_element_id"] == str(cost_element.cost_element_id)


def test_get_cost_element_cost_summary_empty(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost-element-level cost summary with no registrations."""

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

    # Create cost element with budget but no registrations
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

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/cost-summary/cost-element/{cost_element.cost_element_id}",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    assert content["level"] == "cost-element"
    assert float(content["total_cost"]) == 0.00
    assert float(content["budget_bac"]) == 20000.00
    assert content["cost_registration_count"] == 0
    assert float(content["cost_percentage_of_budget"]) == 0.0


def test_get_cost_element_cost_summary_quality_only(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost-element-level cost summary filtered by quality costs only."""

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

    # Create cost registrations (regular and quality)
    cr1_data = CostRegistrationCreate(
        cost_element_id=cost_element.cost_element_id,
        registration_date=date.today(),
        amount=Decimal("5000.00"),
        cost_category="labor",
        description="Regular cost",
        is_quality_cost=False,
    )
    cr1 = CostRegistration.model_validate(
        {**cr1_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr1)

    cr2_data = CostRegistrationCreate(
        cost_element_id=cost_element.cost_element_id,
        registration_date=date.today(),
        amount=Decimal("2000.00"),
        cost_category="labor",
        description="Quality cost",
        is_quality_cost=True,
    )
    cr2 = CostRegistration.model_validate(
        {**cr2_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr2)

    db.commit()

    # Call the endpoint with quality filter
    response = client.get(
        f"{settings.API_V1_STR}/cost-summary/cost-element/{cost_element.cost_element_id}",
        headers=superuser_token_headers,
        params={"is_quality_cost": True},
    )

    # Assertions - should only include quality costs (2000)
    assert response.status_code == 200
    content = response.json()

    assert content["level"] == "cost-element"
    assert float(content["total_cost"]) == 2000.00  # Only quality cost
    assert content["cost_registration_count"] == 1  # Only one quality cost registration


def test_get_cost_element_cost_summary_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test getting cost-element cost summary for non-existent cost element."""
    fake_cost_element_id = uuid.uuid4()

    response = client.get(
        f"{settings.API_V1_STR}/cost-summary/cost-element/{fake_cost_element_id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()


def test_get_wbe_cost_summary(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting WBE-level cost summary with multiple cost elements."""

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

    # Create cost element 1
    ce1_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    cost_element1 = CostElement.model_validate(ce1_in)
    db.add(cost_element1)
    db.commit()
    db.refresh(cost_element1)

    # Create cost element 2
    ce2_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="PROC",
        department_name="Procurement",
        budget_bac=Decimal("15000.00"),
        revenue_plan=Decimal("18000.00"),
        status="active",
    )
    cost_element2 = CostElement.model_validate(ce2_in)
    db.add(cost_element2)
    db.commit()
    db.refresh(cost_element2)

    # Create cost registrations for cost element 1
    cr1_data = CostRegistrationCreate(
        cost_element_id=cost_element1.cost_element_id,
        registration_date=date.today(),
        amount=Decimal("5000.00"),
        cost_category="labor",
        description="Labor cost 1",
        is_quality_cost=False,
    )
    cr1 = CostRegistration.model_validate(
        {**cr1_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr1)

    # Create cost registrations for cost element 2
    cr2_data = CostRegistrationCreate(
        cost_element_id=cost_element2.cost_element_id,
        registration_date=date.today(),
        amount=Decimal("3000.00"),
        cost_category="materials",
        description="Materials cost",
        is_quality_cost=False,
    )
    cr2 = CostRegistration.model_validate(
        {**cr2_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr2)

    db.commit()

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/cost-summary/wbe/{wbe.wbe_id}",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    # Check structure
    assert "level" in content
    assert content["level"] == "wbe"
    assert "total_cost" in content
    assert "budget_bac" in content
    assert "cost_registration_count" in content
    assert "wbe_id" in content

    # Check calculated values (5000 + 3000 = 8000)
    assert float(content["total_cost"]) == 8000.00
    assert float(content["budget_bac"]) == 35000.00  # 20000 + 15000
    assert content["cost_registration_count"] == 2
    assert content["wbe_id"] == str(wbe.wbe_id)


def test_get_wbe_cost_summary_empty(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting WBE-level cost summary with no cost elements."""

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

    # Create WBE with no cost elements
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
        f"{settings.API_V1_STR}/cost-summary/wbe/{wbe.wbe_id}",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    assert content["level"] == "wbe"
    assert float(content["total_cost"]) == 0.00
    assert float(content["budget_bac"]) == 0.00
    assert content["cost_registration_count"] == 0


def test_get_wbe_cost_summary_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test getting WBE cost summary for non-existent WBE."""
    fake_wbe_id = uuid.uuid4()

    response = client.get(
        f"{settings.API_V1_STR}/cost-summary/wbe/{fake_wbe_id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()


def test_get_project_cost_summary(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting project-level cost summary with multiple WBEs and cost elements."""

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

    # Create cost element 1 for WBE 1
    ce1_in = CostElementCreate(
        wbe_id=wbe1.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    cost_element1 = CostElement.model_validate(ce1_in)
    db.add(cost_element1)
    db.commit()
    db.refresh(cost_element1)

    # Create cost element 2 for WBE 2
    ce2_in = CostElementCreate(
        wbe_id=wbe2.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="PROC",
        department_name="Procurement",
        budget_bac=Decimal("15000.00"),
        revenue_plan=Decimal("18000.00"),
        status="active",
    )
    cost_element2 = CostElement.model_validate(ce2_in)
    db.add(cost_element2)
    db.commit()
    db.refresh(cost_element2)

    # Create cost registrations for cost element 1
    cr1_data = CostRegistrationCreate(
        cost_element_id=cost_element1.cost_element_id,
        registration_date=date.today(),
        amount=Decimal("5000.00"),
        cost_category="labor",
        description="Labor cost 1",
        is_quality_cost=False,
    )
    cr1 = CostRegistration.model_validate(
        {**cr1_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr1)

    # Create cost registrations for cost element 2
    cr2_data = CostRegistrationCreate(
        cost_element_id=cost_element2.cost_element_id,
        registration_date=date.today(),
        amount=Decimal("3000.00"),
        cost_category="materials",
        description="Materials cost",
        is_quality_cost=False,
    )
    cr2 = CostRegistration.model_validate(
        {**cr2_data.model_dump(), "created_by_id": pm_user.id}
    )
    db.add(cr2)

    db.commit()

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/cost-summary/project/{project.project_id}",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    # Check structure
    assert "level" in content
    assert content["level"] == "project"
    assert "total_cost" in content
    assert "budget_bac" in content
    assert "cost_registration_count" in content
    assert "project_id" in content

    # Check calculated values (5000 + 3000 = 8000)
    assert float(content["total_cost"]) == 8000.00
    assert float(content["budget_bac"]) == 35000.00  # 20000 + 15000
    assert content["cost_registration_count"] == 2
    assert content["project_id"] == str(project.project_id)


def test_project_cost_summary_respects_control_date(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Ensure project cost summary only includes data on/before control date."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Control Date Project",
        customer_name="Test Customer",
        contract_value=Decimal("120000.00"),
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    control_date = date(2024, 2, 1)
    early_dt = datetime(2024, 1, 10, tzinfo=timezone.utc)
    late_dt = datetime(2024, 3, 10, tzinfo=timezone.utc)

    wbe1 = WBE.model_validate(
        WBECreate(
            project_id=project.project_id,
            machine_type="Early Machine",
            revenue_allocation=Decimal("60000.00"),
            status="designing",
        )
    )
    wbe1.created_at = early_dt
    db.add(wbe1)

    wbe2 = WBE.model_validate(
        WBECreate(
            project_id=project.project_id,
            machine_type="Late Machine",
            revenue_allocation=Decimal("60000.00"),
            status="designing",
        )
    )
    wbe2.created_at = late_dt
    db.add(wbe2)
    db.commit()
    db.refresh(wbe1)
    db.refresh(wbe2)

    cost_element_type = create_random_cost_element_type(db)

    ce1 = CostElement.model_validate(
        CostElementCreate(
            wbe_id=wbe1.wbe_id,
            cost_element_type_id=cost_element_type.cost_element_type_id,
            department_code="ENG",
            department_name="Engineering",
            budget_bac=Decimal("25000.00"),
            revenue_plan=Decimal("30000.00"),
            status="active",
        )
    )
    ce1.created_at = early_dt
    db.add(ce1)

    ce2 = CostElement.model_validate(
        CostElementCreate(
            wbe_id=wbe2.wbe_id,
            cost_element_type_id=cost_element_type.cost_element_type_id,
            department_code="MFG",
            department_name="Manufacturing",
            budget_bac=Decimal("22000.00"),
            revenue_plan=Decimal("26000.00"),
            status="active",
        )
    )
    ce2.created_at = late_dt
    db.add(ce2)
    db.commit()
    db.refresh(ce1)
    db.refresh(ce2)

    cr1 = CostRegistration.model_validate(
        {
            **CostRegistrationCreate(
                cost_element_id=ce1.cost_element_id,
                registration_date=date(2024, 1, 25),
                amount=Decimal("7000.00"),
                cost_category="labor",
                description="Early labor",
                is_quality_cost=False,
            ).model_dump(),
            "created_by_id": pm_user.id,
        }
    )
    db.add(cr1)

    cr2 = CostRegistration.model_validate(
        {
            **CostRegistrationCreate(
                cost_element_id=ce2.cost_element_id,
                registration_date=date(2024, 3, 20),
                amount=Decimal("9000.00"),
                cost_category="materials",
                description="Late materials",
                is_quality_cost=False,
            ).model_dump(),
            "created_by_id": pm_user.id,
        }
    )
    db.add(cr2)
    db.commit()

    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        f"{settings.API_V1_STR}/cost-summary/project/{project.project_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()

    assert float(content["total_cost"]) == 7000.00
    assert float(content["budget_bac"]) == 25000.00
    assert content["cost_registration_count"] == 1


def test_get_project_cost_summary_empty(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting project-level cost summary with no WBEs."""

    # Create project manager user
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    # Create project with no WBEs
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
        f"{settings.API_V1_STR}/cost-summary/project/{project.project_id}",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    assert content["level"] == "project"
    assert float(content["total_cost"]) == 0.00
    assert float(content["budget_bac"]) == 0.00
    assert content["cost_registration_count"] == 0


def test_get_project_cost_summary_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test getting project cost summary for non-existent project."""
    fake_project_id = uuid.uuid4()

    response = client.get(
        f"{settings.API_V1_STR}/cost-summary/project/{fake_project_id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()
