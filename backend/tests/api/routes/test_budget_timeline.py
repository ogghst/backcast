"""Tests for budget timeline API endpoints."""
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
    CostElementType,
    CostElementTypeCreate,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)
from tests.utils.cost_element_schedule import create_schedule_for_cost_element
from tests.utils.user import set_time_machine_date


def test_get_cost_elements_with_schedules_by_project(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting all cost elements with schedules for a project."""
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
        machine_type="Test Machine",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)
    wbe.created_at = datetime(2024, 1, 5, tzinfo=timezone.utc)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Create cost element type
    cet_in = CostElementTypeCreate(
        type_code=f"test_type_{uuid.uuid4().hex[:8]}",
        type_name="Test Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cost_element_type = CostElementType.model_validate(cet_in)
    db.add(cost_element_type)
    db.commit()
    db.refresh(cost_element_type)

    # Create cost elements
    ce1_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    ce1 = CostElement.model_validate(ce1_in)
    db.add(ce1)
    db.commit()
    db.refresh(ce1)

    ce2_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="PROC",
        department_name="Procurement",
        budget_bac=Decimal("15000.00"),
        revenue_plan=Decimal("20000.00"),
        status="active",
    )
    ce2 = CostElement.model_validate(ce2_in)
    db.add(ce2)
    db.commit()
    db.refresh(ce2)

    # Create schedules for cost elements
    schedule1 = create_schedule_for_cost_element(
        db,
        ce1.cost_element_id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=180),
        progression_type="linear",
        created_by_id=pm_user.id,
    )
    schedule1.created_at = datetime(2024, 1, 20, tzinfo=timezone.utc)
    db.add(schedule1)
    db.commit()
    db.refresh(schedule1)
    _schedule2 = create_schedule_for_cost_element(
        db,
        ce2.cost_element_id,
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=210),
        progression_type="gaussian",
        created_by_id=pm_user.id,
    )

    # Ensure control date is after the latest schedule registration so both appear
    set_time_machine_date(
        client, superuser_token_headers, date.today() + timedelta(days=400)
    )

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()

    # Check structure
    assert isinstance(content, list)
    assert len(content) == 2

    # Check first cost element
    ce1_data = next(
        ce for ce in content if ce["cost_element_id"] == str(ce1.cost_element_id)
    )
    assert ce1_data["department_name"] == "Engineering"
    assert float(ce1_data["budget_bac"]) == 20000.00
    assert ce1_data["schedule"] is not None
    assert ce1_data["schedule"]["start_date"] == schedule1.start_date.isoformat()
    assert ce1_data["schedule"]["progression_type"] == "linear"

    # Check second cost element
    ce2_data = next(
        ce for ce in content if ce["cost_element_id"] == str(ce2.cost_element_id)
    )
    assert ce2_data["department_name"] == "Procurement"
    assert float(ce2_data["budget_bac"]) == 15000.00
    assert ce2_data["schedule"] is not None
    assert ce2_data["schedule"]["progression_type"] == "gaussian"


def test_budget_timeline_respects_control_date(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Ensure cost elements/schedules after control date are excluded."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Timeline Control Project",
        customer_name="Test Customer",
        contract_value=Decimal("80000.00"),
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
    early_dt = datetime(2024, 1, 5, tzinfo=timezone.utc)
    late_dt = datetime(2024, 3, 5, tzinfo=timezone.utc)

    wbe1 = WBE.model_validate(
        WBECreate(
            project_id=project.project_id,
            machine_type="Machine Early",
            revenue_allocation=Decimal("40000.00"),
            status="designing",
        )
    )
    wbe1.created_at = early_dt
    db.add(wbe1)

    wbe2 = WBE.model_validate(
        WBECreate(
            project_id=project.project_id,
            machine_type="Machine Late",
            revenue_allocation=Decimal("40000.00"),
            status="designing",
        )
    )
    wbe2.created_at = late_dt
    db.add(wbe2)
    db.commit()
    db.refresh(wbe1)
    db.refresh(wbe2)

    cost_element_type = CostElementType.model_validate(
        CostElementTypeCreate(
            type_code=f"ct_{uuid.uuid4().hex[:6]}",
            type_name="Control Type",
            category_type="engineering_mechanical",
            display_order=1,
            is_active=True,
        )
    )
    db.add(cost_element_type)
    db.commit()
    db.refresh(cost_element_type)

    ce1 = CostElement.model_validate(
        CostElementCreate(
            wbe_id=wbe1.wbe_id,
            cost_element_type_id=cost_element_type.cost_element_type_id,
            department_code="ENG",
            department_name="Engineering",
            budget_bac=Decimal("15000.00"),
            revenue_plan=Decimal("18000.00"),
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
            budget_bac=Decimal("12000.00"),
            revenue_plan=Decimal("15000.00"),
            status="active",
        )
    )
    ce2.created_at = late_dt
    db.add(ce2)
    db.commit()
    db.refresh(ce1)
    db.refresh(ce2)

    schedule1 = create_schedule_for_cost_element(
        db,
        ce1.cost_element_id,
        start_date=date(2024, 1, 10),
        end_date=date(2024, 6, 1),
        progression_type="linear",
        registration_date=date(2024, 1, 12),
        created_by_id=pm_user.id,
    )
    create_schedule_for_cost_element(
        db,
        ce2.cost_element_id,
        start_date=date(2024, 3, 10),
        end_date=date(2024, 8, 1),
        progression_type="gaussian",
        registration_date=date(2024, 3, 15),
        created_by_id=pm_user.id,
    )

    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content) == 1
    assert content[0]["cost_element_id"] == str(ce1.cost_element_id)
    schedule_payload = content[0]["schedule"]
    assert schedule_payload is None or schedule_payload["schedule_id"] == str(
        schedule1.schedule_id
    )


def test_budget_timeline_hides_schedules_created_after_control_date_even_if_backdated(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Schedules created after the control date should be ignored even if their registration date is earlier."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project = Project.model_validate(
        ProjectCreate(
            project_name="Backdated Schedule Project",
            customer_name="Customer",
            contract_value=Decimal("60000.00"),
            start_date=date(2024, 1, 1),
            planned_completion_date=date(2024, 12, 31),
            project_manager_id=pm_user.id,
            status="active",
        )
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    wbe = WBE.model_validate(
        WBECreate(
            project_id=project.project_id,
            machine_type="Machine Alpha",
            revenue_allocation=Decimal("60000.00"),
            status="designing",
        )
    )
    db.add(wbe)
    db.commit()
    db.refresh(wbe)
    wbe.created_at = datetime(2024, 1, 5, tzinfo=timezone.utc)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    cost_element_type = CostElementType.model_validate(
        CostElementTypeCreate(
            type_code=f"ct_{uuid.uuid4().hex[:6]}",
            type_name="Control Type",
            category_type="engineering_mechanical",
            display_order=1,
            is_active=True,
        )
    )
    db.add(cost_element_type)
    db.commit()
    db.refresh(cost_element_type)

    cost_element = CostElement.model_validate(
        CostElementCreate(
            wbe_id=wbe.wbe_id,
            cost_element_type_id=cost_element_type.cost_element_type_id,
            department_code="ENG",
            department_name="Engineering",
            budget_bac=Decimal("20000.00"),
            revenue_plan=Decimal("22000.00"),
            status="active",
        )
    )
    db.add(cost_element)
    db.commit()
    db.refresh(cost_element)
    cost_element.created_at = datetime(2024, 1, 6, tzinfo=timezone.utc)
    db.add(cost_element)
    db.commit()
    db.refresh(cost_element)

    schedule = create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2024, 1, 10),
        end_date=date(2024, 4, 10),
        progression_type="linear",
        registration_date=date(2024, 1, 15),
        created_by_id=pm_user.id,
    )
    schedule.created_at = datetime(2024, 3, 1, tzinfo=timezone.utc)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    control_date = date(2024, 2, 1)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content) == 1
    assert content[0]["cost_element_id"] == str(cost_element.cost_element_id)
    assert content[0]["schedule"] is None


def test_get_cost_elements_with_schedules_by_wbe(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost elements with schedules filtered by WBE."""
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

    # Create two WBEs
    wbe1_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 1",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe1 = WBE.model_validate(wbe1_in)
    db.add(wbe1)
    db.commit()
    db.refresh(wbe1)

    wbe2_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 2",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe2 = WBE.model_validate(wbe2_in)
    db.add(wbe2)
    db.commit()
    db.refresh(wbe2)

    # Create cost element type
    cet_in = CostElementTypeCreate(
        type_code=f"test_type_{uuid.uuid4().hex[:8]}",
        type_name="Test Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cost_element_type = CostElementType.model_validate(cet_in)
    db.add(cost_element_type)
    db.commit()
    db.refresh(cost_element_type)

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
    db.commit()
    db.refresh(ce1)

    # Create cost elements for WBE 2
    ce2_in = CostElementCreate(
        wbe_id=wbe2.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="PROC",
        department_name="Procurement",
        budget_bac=Decimal("15000.00"),
        revenue_plan=Decimal("20000.00"),
        status="active",
    )
    ce2 = CostElement.model_validate(ce2_in)
    db.add(ce2)
    db.commit()
    db.refresh(ce2)

    # Create schedules
    create_schedule_for_cost_element(db, ce1.cost_element_id, created_by_id=pm_user.id)
    create_schedule_for_cost_element(db, ce2.cost_element_id, created_by_id=pm_user.id)

    # Call the endpoint filtering by WBE 1
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
        params={"wbe_ids": [str(wbe1.wbe_id)]},
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert len(content) == 1
    assert content[0]["cost_element_id"] == str(ce1.cost_element_id)
    assert content[0]["department_name"] == "Engineering"


def test_get_cost_elements_with_schedules_by_type(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost elements with schedules filtered by cost element type."""
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
        machine_type="Test Machine",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Create two cost element types
    cet1_in = CostElementTypeCreate(
        type_code=f"type1_{uuid.uuid4().hex[:8]}",
        type_name="Engineering Type 1",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    type1 = CostElementType.model_validate(cet1_in)
    db.add(type1)
    db.commit()
    db.refresh(type1)

    cet2_in = CostElementTypeCreate(
        type_code=f"type2_{uuid.uuid4().hex[:8]}",
        type_name="Engineering Type 2",
        category_type="engineering_electrical",
        display_order=2,
        is_active=True,
    )
    type2 = CostElementType.model_validate(cet2_in)
    db.add(type2)
    db.commit()
    db.refresh(type2)

    # Create cost elements with different types
    ce1_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=type1.cost_element_type_id,
        department_code="ENG1",
        department_name="Engineering 1",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    ce1 = CostElement.model_validate(ce1_in)
    db.add(ce1)
    db.commit()
    db.refresh(ce1)

    ce2_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=type2.cost_element_type_id,
        department_code="ENG2",
        department_name="Engineering 2",
        budget_bac=Decimal("15000.00"),
        revenue_plan=Decimal("20000.00"),
        status="active",
    )
    ce2 = CostElement.model_validate(ce2_in)
    db.add(ce2)
    db.commit()
    db.refresh(ce2)

    # Create schedules
    create_schedule_for_cost_element(db, ce1.cost_element_id, created_by_id=pm_user.id)
    create_schedule_for_cost_element(db, ce2.cost_element_id, created_by_id=pm_user.id)

    # Call the endpoint filtering by type 1
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
        params={"cost_element_type_ids": [str(type1.cost_element_type_id)]},
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert len(content) == 1
    assert content[0]["cost_element_id"] == str(ce1.cost_element_id)
    assert content[0]["department_name"] == "Engineering 1"


def test_get_cost_elements_with_schedules_combined_filters(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost elements with schedules using combined filters (WBE + type)."""
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

    # Create WBEs
    wbe1_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 1",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe1 = WBE.model_validate(wbe1_in)
    db.add(wbe1)
    db.commit()
    db.refresh(wbe1)

    wbe2_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 2",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe2 = WBE.model_validate(wbe2_in)
    db.add(wbe2)
    db.commit()
    db.refresh(wbe2)

    # Create cost element types
    cet1_in = CostElementTypeCreate(
        type_code=f"type1_{uuid.uuid4().hex[:8]}",
        type_name="Engineering Type 1",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    type1 = CostElementType.model_validate(cet1_in)
    db.add(type1)
    db.commit()
    db.refresh(type1)

    cet2_in = CostElementTypeCreate(
        type_code=f"type2_{uuid.uuid4().hex[:8]}",
        type_name="Engineering Type 2",
        category_type="engineering_electrical",
        display_order=2,
        is_active=True,
    )
    type2 = CostElementType.model_validate(cet2_in)
    db.add(type2)
    db.commit()
    db.refresh(type2)

    # Create cost elements: WBE1+Type1, WBE1+Type2, WBE2+Type1
    ce1_in = CostElementCreate(
        wbe_id=wbe1.wbe_id,
        cost_element_type_id=type1.cost_element_type_id,
        department_code="ENG1",
        department_name="Engineering 1",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    ce1 = CostElement.model_validate(ce1_in)
    db.add(ce1)
    db.commit()
    db.refresh(ce1)

    ce2_in = CostElementCreate(
        wbe_id=wbe1.wbe_id,
        cost_element_type_id=type2.cost_element_type_id,
        department_code="ENG2",
        department_name="Engineering 2",
        budget_bac=Decimal("15000.00"),
        revenue_plan=Decimal("20000.00"),
        status="active",
    )
    ce2 = CostElement.model_validate(ce2_in)
    db.add(ce2)
    db.commit()
    db.refresh(ce2)

    ce3_in = CostElementCreate(
        wbe_id=wbe2.wbe_id,
        cost_element_type_id=type1.cost_element_type_id,
        department_code="ENG3",
        department_name="Engineering 3",
        budget_bac=Decimal("18000.00"),
        revenue_plan=Decimal("22000.00"),
        status="active",
    )
    ce3 = CostElement.model_validate(ce3_in)
    db.add(ce3)
    db.commit()
    db.refresh(ce3)

    # Create schedules
    create_schedule_for_cost_element(db, ce1.cost_element_id, created_by_id=pm_user.id)
    create_schedule_for_cost_element(db, ce2.cost_element_id, created_by_id=pm_user.id)
    create_schedule_for_cost_element(db, ce3.cost_element_id, created_by_id=pm_user.id)

    # Call the endpoint with combined filters: WBE1 + Type1 (should return only ce1)
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
        params={
            "wbe_ids": [str(wbe1.wbe_id)],
            "cost_element_type_ids": [str(type1.cost_element_type_id)],
        },
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert len(content) == 1
    assert content[0]["cost_element_id"] == str(ce1.cost_element_id)
    assert content[0]["department_name"] == "Engineering 1"


def test_get_cost_elements_with_schedules_filtered(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost elements with schedules filtered by cost element IDs."""
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
        machine_type="Test Machine",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Create cost element type
    cet_in = CostElementTypeCreate(
        type_code=f"test_type_{uuid.uuid4().hex[:8]}",
        type_name="Test Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cost_element_type = CostElementType.model_validate(cet_in)
    db.add(cost_element_type)
    db.commit()
    db.refresh(cost_element_type)

    # Create three cost elements
    ce1_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG1",
        department_name="Engineering 1",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    ce1 = CostElement.model_validate(ce1_in)
    db.add(ce1)
    db.commit()
    db.refresh(ce1)

    ce2_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG2",
        department_name="Engineering 2",
        budget_bac=Decimal("15000.00"),
        revenue_plan=Decimal("20000.00"),
        status="active",
    )
    ce2 = CostElement.model_validate(ce2_in)
    db.add(ce2)
    db.commit()
    db.refresh(ce2)

    ce3_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG3",
        department_name="Engineering 3",
        budget_bac=Decimal("18000.00"),
        revenue_plan=Decimal("22000.00"),
        status="active",
    )
    ce3 = CostElement.model_validate(ce3_in)
    db.add(ce3)
    db.commit()
    db.refresh(ce3)

    # Create schedules
    create_schedule_for_cost_element(db, ce1.cost_element_id, created_by_id=pm_user.id)
    create_schedule_for_cost_element(db, ce2.cost_element_id, created_by_id=pm_user.id)
    create_schedule_for_cost_element(db, ce3.cost_element_id, created_by_id=pm_user.id)

    # Call the endpoint filtering by ce1 and ce2 IDs
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
        params={
            "cost_element_ids": [str(ce1.cost_element_id), str(ce2.cost_element_id)]
        },
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert len(content) == 2
    cost_element_ids = [ce["cost_element_id"] for ce in content]
    assert str(ce1.cost_element_id) in cost_element_ids
    assert str(ce2.cost_element_id) in cost_element_ids
    assert str(ce3.cost_element_id) not in cost_element_ids


def test_get_cost_elements_with_schedules_missing_schedule(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost elements where some have schedules and some don't."""
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
        machine_type="Test Machine",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Create cost element type
    cet_in = CostElementTypeCreate(
        type_code=f"test_type_{uuid.uuid4().hex[:8]}",
        type_name="Test Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cost_element_type = CostElementType.model_validate(cet_in)
    db.add(cost_element_type)
    db.commit()
    db.refresh(cost_element_type)

    # Create cost elements
    ce1_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG1",
        department_name="Engineering 1",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    ce1 = CostElement.model_validate(ce1_in)
    db.add(ce1)
    db.commit()
    db.refresh(ce1)

    ce2_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        department_code="ENG2",
        department_name="Engineering 2",
        budget_bac=Decimal("15000.00"),
        revenue_plan=Decimal("20000.00"),
        status="active",
    )
    ce2 = CostElement.model_validate(ce2_in)
    db.add(ce2)
    db.commit()
    db.refresh(ce2)

    # Create schedule only for ce1
    create_schedule_for_cost_element(db, ce1.cost_element_id, created_by_id=pm_user.id)
    # ce2 has no schedule

    # Call the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert len(content) == 2

    # Find elements
    ce1_data = next(
        ce for ce in content if ce["cost_element_id"] == str(ce1.cost_element_id)
    )
    ce2_data = next(
        ce for ce in content if ce["cost_element_id"] == str(ce2.cost_element_id)
    )

    # ce1 should have schedule
    assert ce1_data["schedule"] is not None
    assert ce1_data["schedule"]["progression_type"] == "linear"

    # ce2 should have null schedule
    assert ce2_data["schedule"] is None


def test_get_cost_elements_with_schedules_project_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test getting cost elements with schedules for non-existent project."""
    fake_project_id = uuid.uuid4()

    response = client.get(
        f"{settings.API_V1_STR}/projects/{fake_project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()


def test_get_cost_elements_with_schedules_empty_project(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting cost elements with schedules for project with no cost elements."""
    from datetime import date, timedelta

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
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert len(content) == 0


def test_get_cost_elements_with_schedules_no_matching_type(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test filtering by cost element type that doesn't match any cost elements."""
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
        machine_type="Test Machine",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Create cost element type (used in cost element)
    cet1_in = CostElementTypeCreate(
        type_code=f"type1_{uuid.uuid4().hex[:8]}",
        type_name="Engineering Type 1",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    type1 = CostElementType.model_validate(cet1_in)
    db.add(type1)
    db.commit()
    db.refresh(type1)

    # Create another cost element type (not used)
    cet2_in = CostElementTypeCreate(
        type_code=f"type2_{uuid.uuid4().hex[:8]}",
        type_name="Engineering Type 2",
        category_type="engineering_electrical",
        display_order=2,
        is_active=True,
    )
    type2 = CostElementType.model_validate(cet2_in)
    db.add(type2)
    db.commit()
    db.refresh(type2)

    # Create cost element with type1
    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=type1.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Create schedule
    create_schedule_for_cost_element(db, ce.cost_element_id, created_by_id=pm_user.id)

    # Call the endpoint filtering by type2 (which doesn't match)
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
        params={"cost_element_type_ids": [str(type2.cost_element_type_id)]},
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert len(content) == 0


def test_get_cost_elements_with_schedules_combined_filters_no_matches(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test combined filters that result in no matches."""
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

    # Create WBEs
    wbe1_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 1",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe1 = WBE.model_validate(wbe1_in)
    db.add(wbe1)
    db.commit()
    db.refresh(wbe1)

    wbe2_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 2",
        revenue_allocation=Decimal("50000.00"),
        status="designing",
    )
    wbe2 = WBE.model_validate(wbe2_in)
    db.add(wbe2)
    db.commit()
    db.refresh(wbe2)

    # Create cost element types
    cet1_in = CostElementTypeCreate(
        type_code=f"type1_{uuid.uuid4().hex[:8]}",
        type_name="Engineering Type 1",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    type1 = CostElementType.model_validate(cet1_in)
    db.add(type1)
    db.commit()
    db.refresh(type1)

    cet2_in = CostElementTypeCreate(
        type_code=f"type2_{uuid.uuid4().hex[:8]}",
        type_name="Engineering Type 2",
        category_type="engineering_electrical",
        display_order=2,
        is_active=True,
    )
    type2 = CostElementType.model_validate(cet2_in)
    db.add(type2)
    db.commit()
    db.refresh(type2)

    # Create cost element: WBE1 + Type1
    ce_in = CostElementCreate(
        wbe_id=wbe1.wbe_id,
        cost_element_type_id=type1.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("25000.00"),
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Create schedule
    create_schedule_for_cost_element(db, ce.cost_element_id, created_by_id=pm_user.id)

    # Call the endpoint with combined filters that don't match: WBE2 + Type1 (should return empty)
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/cost-elements-with-schedules",
        headers=superuser_token_headers,
        params={
            "wbe_ids": [str(wbe2.wbe_id)],
            "cost_element_type_ids": [str(type1.cost_element_type_id)],
        },
    )

    # Assertions
    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert len(content) == 0
