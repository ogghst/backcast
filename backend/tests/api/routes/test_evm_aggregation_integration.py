"""Integration tests for unified EVM aggregation endpoints."""

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
        type_code=f"evm_int_type_{uuid.uuid4().hex[:8]}",
        type_name="EVM Integration Engineering",
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
    email = f"evm_int_pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="EVM Integration Test Project",
        customer_name="EVM Integration Customer",
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
        machine_type="EVM Integration Machine",
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


def test_unified_wbe_endpoint_matches_separate_endpoints(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Unified WBE endpoint should produce same results as aggregating separate endpoints."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("200000.00"))
    cet = _create_cost_element_type(db)

    ce1 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    ce2 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="PROC",
        department_name="Procurement",
        budget_bac=Decimal("80000.00"),
        revenue_plan=Decimal("100000.00"),
    )

    # Create schedules
    schedule1 = create_schedule_for_cost_element(
        db,
        ce1.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        created_by_id=created_by_id,
    )
    schedule1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule1)
    db.commit()

    schedule2 = create_schedule_for_cost_element(
        db,
        ce2.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        created_by_id=created_by_id,
    )
    schedule2.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule2)
    db.commit()

    # Create earned value entries
    create_earned_value_entry(
        db,
        cost_element_id=ce1.cost_element_id,
        completion_date=date(2024, 6, 15),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )

    create_earned_value_entry(
        db,
        cost_element_id=ce2.cost_element_id,
        completion_date=date(2024, 6, 15),
        percent_complete=Decimal("40.00"),
        created_by_id=created_by_id,
    )

    # Create cost registrations
    cr1_in = CostRegistrationCreate(
        cost_element_id=ce1.cost_element_id,
        registration_date=date(2024, 6, 1),
        amount=Decimal("50000.00"),
        cost_category="labor",
        description="CE1 cost",
        is_quality_cost=False,
    )
    cr1_data = cr1_in.model_dump()
    cr1_data["created_by_id"] = created_by_id
    cr1 = CostRegistration.model_validate(cr1_data)
    cr1.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
    db.add(cr1)

    cr2_in = CostRegistrationCreate(
        cost_element_id=ce2.cost_element_id,
        registration_date=date(2024, 6, 1),
        amount=Decimal("35000.00"),
        cost_category="labor",
        description="CE2 cost",
        is_quality_cost=False,
    )
    cr2_data = cr2_in.model_dump()
    cr2_data["created_by_id"] = created_by_id
    cr2 = CostRegistration.model_validate(cr2_data)
    cr2.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
    db.add(cr2)
    db.commit()

    control_date = date(2024, 6, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    # Get unified endpoint result
    unified_response = client.get(
        f"/api/v1/projects/{project.project_id}/evm-metrics/wbes/{wbe.wbe_id}",
        headers=superuser_token_headers,
    )
    assert unified_response.status_code == 200
    unified_data = unified_response.json()

    # Get separate endpoints and aggregate manually
    pv_response = client.get(
        f"/api/v1/projects/{project.project_id}/planned-value/wbes/{wbe.wbe_id}?control_date={control_date}",
        headers=superuser_token_headers,
    )
    assert pv_response.status_code == 200
    pv_data = pv_response.json()

    ev_response = client.get(
        f"/api/v1/projects/{project.project_id}/earned-value/wbes/{wbe.wbe_id}",
        headers=superuser_token_headers,
    )
    assert ev_response.status_code == 200
    ev_data = ev_response.json()

    # Verify unified endpoint matches aggregated separate endpoints
    assert abs(
        Decimal(str(unified_data["planned_value"]))
        - Decimal(str(pv_data["planned_value"]))
    ) < Decimal("0.01")
    assert abs(
        Decimal(str(unified_data["earned_value"]))
        - Decimal(str(ev_data["earned_value"]))
    ) < Decimal("0.01")
    assert abs(
        Decimal(str(unified_data["budget_bac"])) - Decimal(str(pv_data["budget_bac"]))
    ) < Decimal("0.01")
    assert abs(
        Decimal(str(unified_data["budget_bac"])) - Decimal(str(ev_data["budget_bac"]))
    ) < Decimal("0.01")

    # Verify unified endpoint has all metrics
    assert "actual_cost" in unified_data
    assert "cpi" in unified_data
    assert "spi" in unified_data
    assert "tcpi" in unified_data
    assert "cost_variance" in unified_data
    assert "schedule_variance" in unified_data


def test_unified_project_endpoint_matches_separate_endpoints(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Unified project endpoint should produce same results as aggregating separate endpoints."""
    project, created_by_id = _create_project_with_manager(db)
    wbe1 = _create_wbe(db, project.project_id, Decimal("200000.00"))
    wbe2 = _create_wbe(db, project.project_id, Decimal("150000.00"))
    cet = _create_cost_element_type(db)

    ce1 = _create_cost_element(
        db,
        wbe1.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    ce2 = _create_cost_element(
        db,
        wbe2.wbe_id,
        cet,
        department_code="PROC",
        department_name="Procurement",
        budget_bac=Decimal("80000.00"),
        revenue_plan=Decimal("100000.00"),
    )

    # Create schedules
    schedule1 = create_schedule_for_cost_element(
        db,
        ce1.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        created_by_id=created_by_id,
    )
    schedule1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule1)
    db.commit()

    schedule2 = create_schedule_for_cost_element(
        db,
        ce2.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        created_by_id=created_by_id,
    )
    schedule2.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule2)
    db.commit()

    # Create earned value entries
    create_earned_value_entry(
        db,
        cost_element_id=ce1.cost_element_id,
        completion_date=date(2024, 6, 15),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )

    create_earned_value_entry(
        db,
        cost_element_id=ce2.cost_element_id,
        completion_date=date(2024, 6, 15),
        percent_complete=Decimal("40.00"),
        created_by_id=created_by_id,
    )

    # Create cost registrations
    cr1_in = CostRegistrationCreate(
        cost_element_id=ce1.cost_element_id,
        registration_date=date(2024, 6, 1),
        amount=Decimal("50000.00"),
        cost_category="labor",
        description="CE1 cost",
        is_quality_cost=False,
    )
    cr1_data = cr1_in.model_dump()
    cr1_data["created_by_id"] = created_by_id
    cr1 = CostRegistration.model_validate(cr1_data)
    cr1.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
    db.add(cr1)

    cr2_in = CostRegistrationCreate(
        cost_element_id=ce2.cost_element_id,
        registration_date=date(2024, 6, 1),
        amount=Decimal("35000.00"),
        cost_category="labor",
        description="CE2 cost",
        is_quality_cost=False,
    )
    cr2_data = cr2_in.model_dump()
    cr2_data["created_by_id"] = created_by_id
    cr2 = CostRegistration.model_validate(cr2_data)
    cr2.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
    db.add(cr2)
    db.commit()

    control_date = date(2024, 6, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    # Get unified endpoint result
    unified_response = client.get(
        f"/api/v1/projects/{project.project_id}/evm-metrics",
        headers=superuser_token_headers,
    )
    assert unified_response.status_code == 200
    unified_data = unified_response.json()

    # Get separate endpoints
    pv_response = client.get(
        f"/api/v1/projects/{project.project_id}/planned-value?control_date={control_date}",
        headers=superuser_token_headers,
    )
    assert pv_response.status_code == 200
    pv_data = pv_response.json()

    ev_response = client.get(
        f"/api/v1/projects/{project.project_id}/earned-value",
        headers=superuser_token_headers,
    )
    assert ev_response.status_code == 200
    ev_data = ev_response.json()

    # Verify unified endpoint matches aggregated separate endpoints
    assert abs(
        Decimal(str(unified_data["planned_value"]))
        - Decimal(str(pv_data["planned_value"]))
    ) < Decimal("0.01")
    assert abs(
        Decimal(str(unified_data["earned_value"]))
        - Decimal(str(ev_data["earned_value"]))
    ) < Decimal("0.01")
    assert abs(
        Decimal(str(unified_data["budget_bac"])) - Decimal(str(pv_data["budget_bac"]))
    ) < Decimal("0.01")
    assert abs(
        Decimal(str(unified_data["budget_bac"])) - Decimal(str(ev_data["budget_bac"]))
    ) < Decimal("0.01")

    # Verify unified endpoint has all metrics
    assert "actual_cost" in unified_data
    assert "cpi" in unified_data
    assert "spi" in unified_data
    assert "tcpi" in unified_data
    assert "cost_variance" in unified_data
    assert "schedule_variance" in unified_data
