"""Tests for unified EVM aggregation API endpoints."""

import uuid
from datetime import date, datetime, timezone
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
    CostRegistration,
    CostRegistrationCreate,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)
from tests.utils.cost_element_schedule import create_schedule_for_cost_element
from tests.utils.earned_value_entry import create_earned_value_entry
from tests.utils.user import set_time_machine_date


def _create_cost_element_type(db: Session) -> CostElementType:
    """Create a cost element type for testing."""
    cet_in = CostElementTypeCreate(
        type_code=f"evm_agg_type_{uuid.uuid4().hex[:8]}",
        type_name="EVM Aggregation Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)
    return cet


def _create_project_with_manager(db: Session) -> tuple[Project, uuid.UUID]:
    """Create a project with a project manager user."""
    email = f"evm_agg_pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="EVM Aggregation Test Project",
        customer_name="EVM Aggregation Customer",
        contract_value=Decimal("500000.00"),
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project, pm_user.id


def _create_wbe(
    db: Session,
    project_id: uuid.UUID,
    revenue: Decimal,
) -> WBE:
    wbe_in = WBECreate(
        project_id=project_id,
        machine_type="EVM Aggregation Machine",
        revenue_allocation=revenue,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    wbe.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    wbe.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)
    return wbe


def _create_cost_element(
    db: Session,
    wbe_id: uuid.UUID,
    cet: CostElementType,
    *,
    department_code: str,
    department_name: str,
    budget_bac: Decimal,
    revenue_plan: Decimal,
) -> CostElement:
    ce_in = CostElementCreate(
        wbe_id=wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code=department_code,
        department_name=department_name,
        budget_bac=budget_bac,
        revenue_plan=revenue_plan,
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    ce.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ce.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(ce)
    db.commit()
    db.refresh(ce)
    return ce


def _cost_element_endpoint(project_id: uuid.UUID, cost_element_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/evm-metrics/cost-elements/{cost_element_id}"


def _wbe_endpoint(project_id: uuid.UUID, wbe_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/evm-metrics/wbes/{wbe_id}"


def _project_endpoint(project_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/evm-metrics"


def test_get_cost_element_evm_metrics_endpoint_normal_case(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Cost element EVM metrics endpoint should return all metrics."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("200000.00"))
    cet = _create_cost_element_type(db)

    ce = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    schedule = create_schedule_for_cost_element(
        db,
        ce.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        created_by_id=created_by_id,
    )
    schedule.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule)
    db.commit()

    create_earned_value_entry(
        db,
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 6, 15),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )

    cr_in = CostRegistrationCreate(
        cost_element_id=ce.cost_element_id,
        registration_date=date(2024, 6, 1),
        amount=Decimal("50000.00"),
        cost_category="labor",
        description="Test cost registration",
        is_quality_cost=False,
    )
    cr_data = cr_in.model_dump()
    cr_data["created_by_id"] = created_by_id
    cr = CostRegistration.model_validate(cr_data)
    cr.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
    db.add(cr)
    db.commit()

    control_date = date(2024, 6, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _cost_element_endpoint(project.project_id, ce.cost_element_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "cost-element"
    assert data["cost_element_id"] == str(ce.cost_element_id)
    assert "planned_value" in data
    assert "earned_value" in data
    assert "actual_cost" in data
    assert "budget_bac" in data
    assert "cpi" in data
    assert "spi" in data
    assert "tcpi" in data
    assert "cost_variance" in data
    assert "schedule_variance" in data


def test_get_wbe_evm_metrics_endpoint_normal_case(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """WBE EVM metrics endpoint should return aggregated metrics."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("200000.00"))
    cet = _create_cost_element_type(db)

    ce = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    schedule = create_schedule_for_cost_element(
        db,
        ce.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        created_by_id=created_by_id,
    )
    schedule.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule)
    db.commit()

    create_earned_value_entry(
        db,
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 6, 15),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )

    cr_in = CostRegistrationCreate(
        cost_element_id=ce.cost_element_id,
        registration_date=date(2024, 6, 1),
        amount=Decimal("50000.00"),
        cost_category="labor",
        description="Test cost registration",
        is_quality_cost=False,
    )
    cr_data = cr_in.model_dump()
    cr_data["created_by_id"] = created_by_id
    cr = CostRegistration.model_validate(cr_data)
    cr.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
    db.add(cr)
    db.commit()

    control_date = date(2024, 6, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _wbe_endpoint(project.project_id, wbe.wbe_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "wbe"
    assert data["wbe_id"] == str(wbe.wbe_id)
    assert "planned_value" in data
    assert "earned_value" in data
    assert "actual_cost" in data
    assert "budget_bac" in data
    assert "cpi" in data
    assert "spi" in data
    assert "tcpi" in data
    assert "cost_variance" in data
    assert "schedule_variance" in data


def test_get_project_evm_metrics_endpoint_normal_case(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Project EVM metrics endpoint should return aggregated metrics."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("200000.00"))
    cet = _create_cost_element_type(db)

    ce = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    schedule = create_schedule_for_cost_element(
        db,
        ce.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        created_by_id=created_by_id,
    )
    schedule.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule)
    db.commit()

    create_earned_value_entry(
        db,
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 6, 15),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )

    cr_in = CostRegistrationCreate(
        cost_element_id=ce.cost_element_id,
        registration_date=date(2024, 6, 1),
        amount=Decimal("50000.00"),
        cost_category="labor",
        description="Test cost registration",
        is_quality_cost=False,
    )
    cr_data = cr_in.model_dump()
    cr_data["created_by_id"] = created_by_id
    cr = CostRegistration.model_validate(cr_data)
    cr.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
    db.add(cr)
    db.commit()

    control_date = date(2024, 6, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _project_endpoint(project.project_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "project"
    assert data["project_id"] == str(project.project_id)
    assert "planned_value" in data
    assert "earned_value" in data
    assert "actual_cost" in data
    assert "budget_bac" in data
    assert "cpi" in data
    assert "spi" in data
    assert "tcpi" in data
    assert "cost_variance" in data
    assert "schedule_variance" in data
