"""Integration tests for EVM performance indices API endpoints."""

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


def _create_project_with_manager(db: Session) -> tuple[Project, uuid.UUID]:
    """Create a project with a project manager user."""
    email = f"evm_int_pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="EVM Indices Integration Test Project",
        customer_name="EVM Integration Customer",
        contract_value=Decimal("1000000.00"),
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
    )
    ce = CostElement.model_validate(ce_in)
    ce.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ce.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(ce)
    db.commit()
    db.refresh(ce)
    return ce


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


def _wbe_endpoint(project_id: uuid.UUID, wbe_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/evm-indices/wbes/{wbe_id}"


def _project_endpoint(project_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/evm-indices"


def test_wbe_evm_indices_integration(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Integration test: Full WBE scenario with multiple cost elements."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("500000.00"))
    cet = _create_cost_element_type(db)

    # Create multiple cost elements with different scenarios
    ce1 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("200000.00"),
        revenue_plan=Decimal("240000.00"),
    )

    ce2 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="MECH",
        department_name="Mechanical",
        budget_bac=Decimal("150000.00"),
        revenue_plan=Decimal("180000.00"),
    )

    ce3 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ELEC",
        department_name="Electrical",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    # Create schedules for all cost elements
    schedule1 = create_schedule_for_cost_element(
        db,
        ce1.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        description="Q1 Schedule",
        created_by_id=created_by_id,
    )
    schedule1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule1)

    schedule2 = create_schedule_for_cost_element(
        db,
        ce2.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 2, 29),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        description="Q1 Schedule",
        created_by_id=created_by_id,
    )
    schedule2.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule2)

    schedule3 = create_schedule_for_cost_element(
        db,
        ce3.cost_element_id,
        start_date=date(2024, 2, 1),
        end_date=date(2024, 4, 30),
        progression_type="linear",
        registration_date=date(2024, 2, 1),
        description="Q2 Schedule",
        created_by_id=created_by_id,
    )
    schedule3.created_at = datetime(2024, 2, 1, tzinfo=timezone.utc)
    db.add(schedule3)
    db.commit()
    db.refresh(schedule1)
    db.refresh(schedule2)
    db.refresh(schedule3)

    # Create earned value entries
    create_earned_value_entry(
        db,
        cost_element_id=ce1.cost_element_id,
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )

    create_earned_value_entry(
        db,
        cost_element_id=ce2.cost_element_id,
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("60.00"),
        created_by_id=created_by_id,
    )

    # CE3 has no earned value entry (0% complete)

    # Create cost registrations
    cr1_in = CostRegistrationCreate(
        cost_element_id=ce1.cost_element_id,
        registration_date=date(2024, 2, 15),
        amount=Decimal("110000.00"),  # Over budget (50% EV but 55% AC)
        cost_category="labor",
        description="Engineering costs",
        is_quality_cost=False,
    )
    cr1_data = cr1_in.model_dump()
    cr1_data["created_by_id"] = created_by_id
    cr1 = CostRegistration.model_validate(cr1_data)
    cr1.created_at = datetime(2024, 2, 15, tzinfo=timezone.utc)
    db.add(cr1)

    cr2_in = CostRegistrationCreate(
        cost_element_id=ce2.cost_element_id,
        registration_date=date(2024, 2, 15),
        amount=Decimal("85000.00"),  # Under budget (60% EV, 56.67% AC)
        cost_category="labor",
        description="Mechanical costs",
        is_quality_cost=False,
    )
    cr2_data = cr2_in.model_dump()
    cr2_data["created_by_id"] = created_by_id
    cr2 = CostRegistration.model_validate(cr2_data)
    cr2.created_at = datetime(2024, 2, 15, tzinfo=timezone.utc)
    db.add(cr2)

    # CE3 has no cost registrations
    db.commit()

    control_date = date(2024, 2, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _wbe_endpoint(project.project_id, wbe.wbe_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "wbe"
    assert data["wbe_id"] == str(wbe.wbe_id)

    # Verify aggregated values
    # Total BAC = 200000 + 150000 + 100000 = 450000
    # Total EV = 200000*0.5 + 150000*0.6 + 0 = 100000 + 90000 = 190000
    # Total AC = 110000 + 85000 + 0 = 195000
    # Total PV = calculated from schedules at control date
    assert Decimal(str(data["budget_bac"])) == Decimal("450000.00")
    assert Decimal(str(data["earned_value"])) == Decimal("190000.00")
    assert Decimal(str(data["actual_cost"])) == Decimal("195000.00")
    assert Decimal(str(data["planned_value"])) > Decimal("0.00")

    # CPI = 190000/195000 = 0.9744 (underperforming)
    # SPI = EV/PV (will be calculated)
    # TCPI = (450000-190000)/(450000-195000) = 260000/255000 = 1.0196
    assert data["cpi"] is not None
    assert abs(Decimal(str(data["cpi"])) - Decimal("0.9744")) < Decimal("0.0001")
    assert data["spi"] is not None
    assert data["tcpi"] is not None
    assert abs(Decimal(str(data["tcpi"])) - Decimal("1.0196")) < Decimal("0.0001")

    # Verify variances are included and calculated correctly
    assert "cost_variance" in data
    assert "schedule_variance" in data
    # CV = EV - AC = 190000 - 195000 = -5000 (over-budget)
    # SV = EV - PV (will be calculated)
    cv = Decimal(str(data["cost_variance"]))
    sv = Decimal(str(data["schedule_variance"]))
    ev = Decimal(str(data["earned_value"]))
    ac = Decimal(str(data["actual_cost"]))
    pv = Decimal(str(data["planned_value"]))
    assert abs(cv - (ev - ac)) < Decimal("0.01")  # CV = EV - AC
    assert abs(sv - (ev - pv)) < Decimal("1.00")  # SV = EV - PV (allow for PV rounding)
    assert cv < Decimal("0.00")  # Negative (over-budget)


def test_project_evm_indices_integration(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Integration test: Full project scenario with multiple WBEs and cost elements."""
    project, created_by_id = _create_project_with_manager(db)
    cet = _create_cost_element_type(db)

    # Create multiple WBEs
    wbe1 = _create_wbe(db, project.project_id, Decimal("300000.00"))
    wbe2 = _create_wbe(db, project.project_id, Decimal("200000.00"))
    wbe3 = _create_wbe(db, project.project_id, Decimal("100000.00"))

    # Create cost elements for each WBE
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
        department_code="MECH",
        department_name="Mechanical",
        budget_bac=Decimal("80000.00"),
        revenue_plan=Decimal("96000.00"),
    )

    ce3 = _create_cost_element(
        db,
        wbe3.wbe_id,
        cet,
        department_code="ELEC",
        department_name="Electrical",
        budget_bac=Decimal("60000.00"),
        revenue_plan=Decimal("72000.00"),
    )

    # Create schedules
    schedule1 = create_schedule_for_cost_element(
        db,
        ce1.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 6, 30),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        description="H1 Schedule",
        created_by_id=created_by_id,
    )
    schedule1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule1)

    schedule2 = create_schedule_for_cost_element(
        db,
        ce2.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 4, 30),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        description="Q1-Q2 Schedule",
        created_by_id=created_by_id,
    )
    schedule2.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule2)

    schedule3 = create_schedule_for_cost_element(
        db,
        ce3.cost_element_id,
        start_date=date(2024, 2, 1),
        end_date=date(2024, 5, 31),
        progression_type="linear",
        registration_date=date(2024, 2, 1),
        description="Q2 Schedule",
        created_by_id=created_by_id,
    )
    schedule3.created_at = datetime(2024, 2, 1, tzinfo=timezone.utc)
    db.add(schedule3)
    db.commit()
    db.refresh(schedule1)
    db.refresh(schedule2)
    db.refresh(schedule3)

    # Create earned value entries
    create_earned_value_entry(
        db,
        cost_element_id=ce1.cost_element_id,
        completion_date=date(2024, 3, 15),
        percent_complete=Decimal("40.00"),
        created_by_id=created_by_id,
    )

    create_earned_value_entry(
        db,
        cost_element_id=ce2.cost_element_id,
        completion_date=date(2024, 3, 15),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )

    create_earned_value_entry(
        db,
        cost_element_id=ce3.cost_element_id,
        completion_date=date(2024, 3, 15),
        percent_complete=Decimal("30.00"),
        created_by_id=created_by_id,
    )

    # Create cost registrations
    cr1_in = CostRegistrationCreate(
        cost_element_id=ce1.cost_element_id,
        registration_date=date(2024, 3, 15),
        amount=Decimal("45000.00"),
        cost_category="labor",
        description="Engineering costs",
        is_quality_cost=False,
    )
    cr1_data = cr1_in.model_dump()
    cr1_data["created_by_id"] = created_by_id
    cr1 = CostRegistration.model_validate(cr1_data)
    cr1.created_at = datetime(2024, 3, 15, tzinfo=timezone.utc)
    db.add(cr1)

    cr2_in = CostRegistrationCreate(
        cost_element_id=ce2.cost_element_id,
        registration_date=date(2024, 3, 15),
        amount=Decimal("42000.00"),
        cost_category="labor",
        description="Mechanical costs",
        is_quality_cost=False,
    )
    cr2_data = cr2_in.model_dump()
    cr2_data["created_by_id"] = created_by_id
    cr2 = CostRegistration.model_validate(cr2_data)
    cr2.created_at = datetime(2024, 3, 15, tzinfo=timezone.utc)
    db.add(cr2)

    cr3_in = CostRegistrationCreate(
        cost_element_id=ce3.cost_element_id,
        registration_date=date(2024, 3, 15),
        amount=Decimal("20000.00"),
        cost_category="labor",
        description="Electrical costs",
        is_quality_cost=False,
    )
    cr3_data = cr3_in.model_dump()
    cr3_data["created_by_id"] = created_by_id
    cr3 = CostRegistration.model_validate(cr3_data)
    cr3.created_at = datetime(2024, 3, 15, tzinfo=timezone.utc)
    db.add(cr3)
    db.commit()

    control_date = date(2024, 3, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _project_endpoint(project.project_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "project"
    assert data["project_id"] == str(project.project_id)

    # Verify aggregated values
    # Total BAC = 100000 + 80000 + 60000 = 240000
    # Total EV = 100000*0.4 + 80000*0.5 + 60000*0.3 = 40000 + 40000 + 18000 = 98000
    # Total AC = 45000 + 42000 + 20000 = 107000
    assert Decimal(str(data["budget_bac"])) == Decimal("240000.00")
    assert Decimal(str(data["earned_value"])) == Decimal("98000.00")
    assert Decimal(str(data["actual_cost"])) == Decimal("107000.00")
    assert Decimal(str(data["planned_value"])) > Decimal("0.00")

    # CPI = 98000/107000 = 0.9159
    # SPI = EV/PV (calculated)
    # TCPI = (240000-98000)/(240000-107000) = 142000/133000 = 1.0677
    assert data["cpi"] is not None
    assert abs(Decimal(str(data["cpi"])) - Decimal("0.9159")) < Decimal("0.0001")
    assert data["spi"] is not None
    assert data["tcpi"] is not None
    assert abs(Decimal(str(data["tcpi"])) - Decimal("1.0677")) < Decimal("0.0001")

    # Verify variances are included and calculated correctly
    assert "cost_variance" in data
    assert "schedule_variance" in data
    # CV = EV - AC = 98000 - 107000 = -9000 (over-budget)
    # SV = EV - PV (will be calculated)
    cv = Decimal(str(data["cost_variance"]))
    sv = Decimal(str(data["schedule_variance"]))
    ev = Decimal(str(data["earned_value"]))
    ac = Decimal(str(data["actual_cost"]))
    pv = Decimal(str(data["planned_value"]))
    assert abs(cv - (ev - ac)) < Decimal("0.01")  # CV = EV - AC
    assert abs(sv - (ev - pv)) < Decimal("1.00")  # SV = EV - PV (allow for PV rounding)
    assert cv < Decimal("0.00")  # Negative (over-budget)


def test_evm_indices_time_machine_integration(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Integration test: Verify time-machine control date filtering works correctly."""
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

    # Create schedule
    schedule = create_schedule_for_cost_element(
        db,
        ce.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        description="Q1 Schedule",
        created_by_id=created_by_id,
    )
    schedule.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # Create earned value entries at different dates
    entry1 = create_earned_value_entry(
        db,
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("30.00"),
        created_by_id=created_by_id,
    )
    entry1.created_at = datetime(2024, 2, 15, tzinfo=timezone.utc)
    db.add(entry1)

    entry2 = create_earned_value_entry(
        db,
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 3, 15),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )
    entry2.created_at = datetime(2024, 3, 15, tzinfo=timezone.utc)
    db.add(entry2)
    db.commit()

    # Create cost registrations at different dates
    cr1_in = CostRegistrationCreate(
        cost_element_id=ce.cost_element_id,
        registration_date=date(2024, 2, 15),
        amount=Decimal("30000.00"),
        cost_category="labor",
        description="February costs",
        is_quality_cost=False,
    )
    cr1_data = cr1_in.model_dump()
    cr1_data["created_by_id"] = created_by_id
    cr1 = CostRegistration.model_validate(cr1_data)
    cr1.created_at = datetime(2024, 2, 15, tzinfo=timezone.utc)
    db.add(cr1)

    cr2_in = CostRegistrationCreate(
        cost_element_id=ce.cost_element_id,
        registration_date=date(2024, 3, 15),
        amount=Decimal("20000.00"),
        cost_category="labor",
        description="March costs",
        is_quality_cost=False,
    )
    cr2_data = cr2_in.model_dump()
    cr2_data["created_by_id"] = created_by_id
    cr2 = CostRegistration.model_validate(cr2_data)
    cr2.created_at = datetime(2024, 3, 15, tzinfo=timezone.utc)
    db.add(cr2)
    db.commit()

    # Test at first control date (Feb 15)
    control_date1 = date(2024, 2, 15)
    set_time_machine_date(client, superuser_token_headers, control_date1)

    response1 = client.get(
        _wbe_endpoint(project.project_id, wbe.wbe_id),
        headers=superuser_token_headers,
    )

    assert response1.status_code == 200
    data1 = response1.json()
    # At Feb 15: EV = 30%, AC = 30000
    assert Decimal(str(data1["earned_value"])) == Decimal("30000.00")
    assert Decimal(str(data1["actual_cost"])) == Decimal("30000.00")

    # Test at second control date (Mar 15)
    control_date2 = date(2024, 3, 15)
    set_time_machine_date(client, superuser_token_headers, control_date2)

    response2 = client.get(
        _wbe_endpoint(project.project_id, wbe.wbe_id),
        headers=superuser_token_headers,
    )

    assert response2.status_code == 200
    data2 = response2.json()
    # At Mar 15: EV = 50%, AC = 30000 + 20000 = 50000
    assert Decimal(str(data2["earned_value"])) == Decimal("50000.00")
    assert Decimal(str(data2["actual_cost"])) == Decimal("50000.00")

    # Verify indices changed
    assert data1["cpi"] != data2["cpi"] or data1["spi"] != data2["spi"]

    # Verify variances are included and respect control date
    assert "cost_variance" in data1
    assert "schedule_variance" in data1
    assert "cost_variance" in data2
    assert "schedule_variance" in data2
    # At Feb 15: CV = 30000 - 30000 = 0 (on-budget)
    # At Mar 15: CV = 50000 - 50000 = 0 (on-budget)
    assert Decimal(str(data1["cost_variance"])) == Decimal("0.00")
    assert Decimal(str(data2["cost_variance"])) == Decimal("0.00")
    # Variances should change as control date changes (if EV/PV/AC change)
    # In this case, both dates have EV=AC, so CV stays 0, but SV may change


def test_evm_indices_edge_cases_integration(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Integration test: All edge cases in a realistic scenario."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("200000.00"))
    cet = _create_cost_element_type(db)

    # CE1: Normal case
    ce1 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    # CE2: No schedule (PV = 0, SPI = None)
    ce2 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="MECH",
        department_name="Mechanical",
        budget_bac=Decimal("50000.00"),
        revenue_plan=Decimal("60000.00"),
    )

    # CE3: No earned value entry (EV = 0)
    _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ELEC",
        department_name="Electrical",
        budget_bac=Decimal("30000.00"),
        revenue_plan=Decimal("36000.00"),
    )

    # CE4: Overrun (AC >= BAC, TCPI = 'overrun')
    ce4 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="QUAL",
        department_name="Quality",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("24000.00"),
    )

    # Create schedule only for CE1
    schedule1 = create_schedule_for_cost_element(
        db,
        ce1.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 2, 1),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        description="Baseline",
        created_by_id=created_by_id,
    )
    schedule1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule1)
    db.commit()
    db.refresh(schedule1)

    # Create earned value entries
    create_earned_value_entry(
        db,
        cost_element_id=ce1.cost_element_id,
        completion_date=date(2024, 1, 15),
        percent_complete=Decimal("40.00"),
        created_by_id=created_by_id,
    )

    create_earned_value_entry(
        db,
        cost_element_id=ce2.cost_element_id,
        completion_date=date(2024, 1, 15),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )

    # CE3 has no earned value entry
    # CE4 has earned value but will have overrun

    create_earned_value_entry(
        db,
        cost_element_id=ce4.cost_element_id,
        completion_date=date(2024, 1, 15),
        percent_complete=Decimal("30.00"),
        created_by_id=created_by_id,
    )

    # Create cost registrations
    cr1_in = CostRegistrationCreate(
        cost_element_id=ce1.cost_element_id,
        registration_date=date(2024, 1, 15),
        amount=Decimal("45000.00"),
        cost_category="labor",
        description="Engineering costs",
        is_quality_cost=False,
    )
    cr1_data = cr1_in.model_dump()
    cr1_data["created_by_id"] = created_by_id
    cr1 = CostRegistration.model_validate(cr1_data)
    cr1.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    db.add(cr1)

    # CE2: No cost registrations (AC = 0, but EV > 0, so CPI = None)
    # CE3: No cost registrations (AC = 0, EV = 0, CPI = None)

    # CE4: Overrun
    cr4_in = CostRegistrationCreate(
        cost_element_id=ce4.cost_element_id,
        registration_date=date(2024, 1, 15),
        amount=Decimal("20000.00"),  # AC = BAC (overrun)
        cost_category="labor",
        description="Quality costs",
        is_quality_cost=False,
    )
    cr4_data = cr4_in.model_dump()
    cr4_data["created_by_id"] = created_by_id
    cr4 = CostRegistration.model_validate(cr4_data)
    cr4.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    db.add(cr4)
    db.commit()

    control_date = date(2024, 1, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _wbe_endpoint(project.project_id, wbe.wbe_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "wbe"

    # Verify aggregated values
    # Total BAC = 100000 + 50000 + 30000 + 20000 = 200000
    # Total EV = 100000*0.4 + 50000*0.5 + 0 + 20000*0.3 = 40000 + 25000 + 0 + 6000 = 71000
    # Total AC = 45000 + 0 + 0 + 20000 = 65000
    assert Decimal(str(data["budget_bac"])) == Decimal("200000.00")
    assert Decimal(str(data["earned_value"])) == Decimal("71000.00")
    assert Decimal(str(data["actual_cost"])) == Decimal("65000.00")

    # Aggregated indices should handle edge cases
    # CPI should be calculated (71000/65000 = 1.0923)
    # SPI should be calculated (EV/PV, where PV > 0 from CE1)
    # TCPI should be calculated normally (aggregation doesn't use 'overrun')
    assert data["cpi"] is not None
    assert abs(Decimal(str(data["cpi"])) - Decimal("1.0923")) < Decimal("0.0001")
    assert data["spi"] is not None  # PV > 0 from CE1
    assert data["tcpi"] is not None
    assert isinstance(data["tcpi"], str | float)  # Can be number or 'overrun' string

    # Verify variances are included and handle edge cases correctly
    assert "cost_variance" in data
    assert "schedule_variance" in data
    # CV = EV - AC = 71000 - 65000 = 6000 (under-budget, positive)
    # SV = EV - PV (will be calculated)
    cv = Decimal(str(data["cost_variance"]))
    sv = Decimal(str(data["schedule_variance"]))
    ev = Decimal(str(data["earned_value"]))
    ac = Decimal(str(data["actual_cost"]))
    pv = Decimal(str(data["planned_value"]))
    assert abs(cv - (ev - ac)) < Decimal("0.01")  # CV = EV - AC
    assert abs(sv - (ev - pv)) < Decimal("1.00")  # SV = EV - PV (allow for PV rounding)
    assert cv > Decimal("0.00")  # Positive (under-budget)


def test_evm_indices_variance_consistency(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Integration test: Verify variances and indices use the same inputs (consistency check)."""
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
        end_date=date(2024, 2, 1),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        description="Baseline",
        created_by_id=created_by_id,
    )
    schedule.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    create_earned_value_entry(
        db,
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 1, 15),
        percent_complete=Decimal("40.00"),
        created_by_id=created_by_id,
    )

    cr_in = CostRegistrationCreate(
        cost_element_id=ce.cost_element_id,
        registration_date=date(2024, 1, 15),
        amount=Decimal("45000.00"),
        cost_category="labor",
        description="Test cost registration",
        is_quality_cost=False,
    )
    cr_data = cr_in.model_dump()
    cr_data["created_by_id"] = created_by_id
    cr = CostRegistration.model_validate(cr_data)
    cr.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    db.add(cr)
    db.commit()

    control_date = date(2024, 1, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _wbe_endpoint(project.project_id, wbe.wbe_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Extract values
    ev = Decimal(str(data["earned_value"]))
    ac = Decimal(str(data["actual_cost"]))
    pv = Decimal(str(data["planned_value"]))
    cpi = Decimal(str(data["cpi"])) if data["cpi"] is not None else None
    spi = Decimal(str(data["spi"])) if data["spi"] is not None else None
    cv = Decimal(str(data["cost_variance"]))
    sv = Decimal(str(data["schedule_variance"]))

    # Verify consistency: CV should match EV - AC
    assert abs(cv - (ev - ac)) < Decimal("0.01")
    # Verify consistency: SV should match EV - PV
    assert abs(sv - (ev - pv)) < Decimal("1.00")

    # Verify consistency: CPI and CV should be consistent
    # If CPI is defined, CV should be negative when CPI < 1, positive when CPI > 1
    if cpi is not None:
        if cpi < Decimal("1.0"):
            assert cv < Decimal("0.00")  # Over-budget
        elif cpi > Decimal("1.0"):
            assert cv > Decimal("0.00")  # Under-budget
        else:
            assert abs(cv) < Decimal("0.01")  # On-budget

    # Verify consistency: SPI and SV should be consistent
    # If SPI is defined, SV should be negative when SPI < 1, positive when SPI > 1
    if spi is not None:
        if spi < Decimal("1.0"):
            assert sv < Decimal("0.00")  # Behind-schedule
        elif spi > Decimal("1.0"):
            assert sv > Decimal("0.00")  # Ahead-of-schedule
        else:
            assert abs(sv) < Decimal("1.00")  # On-schedule (allow for PV rounding)
