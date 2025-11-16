"""Tests for EVM performance indices API endpoints."""

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
        type_code=f"evm_type_{uuid.uuid4().hex[:8]}",
        type_name="EVM Engineering",
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
    email = f"evm_pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="EVM Indices Test Project",
        customer_name="EVM Customer",
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
        machine_type="EVM Machine",
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


def _wbe_endpoint(project_id: uuid.UUID, wbe_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/evm-indices/wbes/{wbe_id}"


def _project_endpoint(project_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/evm-indices"


def test_get_wbe_evm_indices_normal_case(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """WBE EVM indices should calculate correctly for normal case."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("200000.00"))
    cet = _create_cost_element_type(db)

    # Create cost element with schedule, earned value, and cost registration
    ce = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    # Create schedule (50% complete at control date)
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
    # Set created_at to be before control date for time-machine filtering
    schedule.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # Create earned value entry (40% complete)
    create_earned_value_entry(
        db,
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 1, 15),
        percent_complete=Decimal("40.00"),
        created_by_id=created_by_id,
    )

    # Create cost registration (AC = 45000)
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
    assert data["level"] == "wbe"
    assert data["wbe_id"] == str(wbe.wbe_id)
    # PV = 100000 * 0.4516 = 45160 (45.16% of schedule at day 15 of 31-day period)
    # EV = 100000 * 0.4 = 40000 (40% earned)
    # AC = 45000
    # BAC = 100000
    # CPI = EV/AC = 40000/45000 = 0.8889
    # SPI = EV/PV = 40000/45160 = 0.8857
    # TCPI = (BAC-EV)/(BAC-AC) = (100000-40000)/(100000-45000) = 60000/55000 = 1.0909
    assert abs(Decimal(str(data["planned_value"])) - Decimal("45160.00")) < Decimal(
        "1.00"
    )
    assert Decimal(str(data["earned_value"])) == Decimal("40000.00")
    assert Decimal(str(data["actual_cost"])) == Decimal("45000.00")
    assert Decimal(str(data["budget_bac"])) == Decimal("100000.00")
    assert abs(Decimal(str(data["cpi"])) - Decimal("0.8889")) < Decimal("0.0001")
    assert abs(Decimal(str(data["spi"])) - Decimal("0.8857")) < Decimal("0.0001")
    assert abs(Decimal(str(data["tcpi"])) - Decimal("1.0909")) < Decimal("0.0001")


def test_get_wbe_evm_indices_cpi_undefined(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """WBE EVM indices should return CPI=None when AC=0 and EV>0."""
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

    # No cost registrations (AC = 0)

    control_date = date(2024, 1, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _wbe_endpoint(project.project_id, wbe.wbe_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["cpi"] is None  # AC = 0, EV > 0 → CPI undefined
    assert data["spi"] is not None  # SPI should be defined
    assert data["tcpi"] is not None  # TCPI should be defined


def test_get_wbe_evm_indices_spi_null(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """WBE EVM indices should return SPI=None when PV=0."""
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

    # No schedule (PV = 0)
    # But create earned value entry
    create_earned_value_entry(
        db,
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 1, 15),
        percent_complete=Decimal("40.00"),
        created_by_id=created_by_id,
    )

    control_date = date(2024, 1, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _wbe_endpoint(project.project_id, wbe.wbe_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["spi"] is None  # PV = 0 → SPI null
    assert data["cpi"] is None  # AC = 0 → CPI undefined
    assert data["tcpi"] is not None  # TCPI should be defined if BAC > 0


def test_get_wbe_evm_indices_tcpi_overrun(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """WBE EVM indices should return TCPI='overrun' when BAC≤AC."""
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

    # Create cost registration where AC >= BAC (overrun)
    cr_in = CostRegistrationCreate(
        cost_element_id=ce.cost_element_id,
        registration_date=date(2024, 1, 15),
        amount=Decimal("100000.00"),  # AC = BAC
        cost_category="labor",
        description="Overrun cost registration",
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
    assert data["tcpi"] == "overrun"  # BAC = AC → overrun


def test_get_wbe_evm_indices_not_found(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """WBE EVM indices should return 404 for non-existent WBE."""
    project, _ = _create_project_with_manager(db)
    fake_wbe_id = uuid.uuid4()

    control_date = date(2024, 1, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _wbe_endpoint(project.project_id, fake_wbe_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 404


def test_get_wbe_evm_indices_includes_variances(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """WBE EVM indices should include cost_variance and schedule_variance fields."""
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
    # Verify variance fields exist
    assert "cost_variance" in data
    assert "schedule_variance" in data


def test_get_wbe_evm_indices_variance_calculation(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """WBE EVM indices should calculate variances correctly: CV=EV-AC, SV=EV-PV."""
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
    # EV = 40000, AC = 45000, PV ≈ 45160
    # CV = EV - AC = 40000 - 45000 = -5000 (over-budget)
    # SV = EV - PV = 40000 - 45160 = -5160 (behind-schedule)
    ev = Decimal(str(data["earned_value"]))
    ac = Decimal(str(data["actual_cost"]))
    pv = Decimal(str(data["planned_value"]))
    cv = Decimal(str(data["cost_variance"]))
    sv = Decimal(str(data["schedule_variance"]))

    # Verify CV = EV - AC
    assert abs(cv - (ev - ac)) < Decimal("0.01")
    # Verify SV = EV - PV
    assert abs(sv - (ev - pv)) < Decimal("1.00")  # Allow for PV rounding


def test_get_wbe_evm_indices_backward_compatibility(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """WBE EVM indices should maintain backward compatibility with existing fields."""
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

    control_date = date(2024, 1, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _wbe_endpoint(project.project_id, wbe.wbe_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # Verify all existing fields are still present
    assert "cpi" in data
    assert "spi" in data
    assert "tcpi" in data
    assert "planned_value" in data
    assert "earned_value" in data
    assert "actual_cost" in data
    assert "budget_bac" in data
    assert "level" in data
    assert "control_date" in data
    assert "wbe_id" in data


def test_get_wbe_evm_indices_negative_variances(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """WBE EVM indices should handle negative variances correctly."""
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

    # Create earned value entry (30% complete - behind schedule)
    create_earned_value_entry(
        db,
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 1, 15),
        percent_complete=Decimal("30.00"),
        created_by_id=created_by_id,
    )

    # Create cost registration (AC = 50000 - over budget)
    cr_in = CostRegistrationCreate(
        cost_element_id=ce.cost_element_id,
        registration_date=date(2024, 1, 15),
        amount=Decimal("50000.00"),
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
    # EV = 30000, AC = 50000, PV ≈ 45160
    # CV = EV - AC = 30000 - 50000 = -20000 (over-budget, negative)
    # SV = EV - PV = 30000 - 45160 = -15160 (behind-schedule, negative)
    cv = Decimal(str(data["cost_variance"]))
    sv = Decimal(str(data["schedule_variance"]))

    assert cv < Decimal("0.00")  # Negative (over-budget)
    assert sv < Decimal("0.00")  # Negative (behind-schedule)


def test_get_project_evm_indices_normal_case(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Project EVM indices should calculate correctly for normal case."""
    project, created_by_id = _create_project_with_manager(db)
    wbe1 = _create_wbe(db, project.project_id, Decimal("200000.00"))
    wbe2 = _create_wbe(db, project.project_id, Decimal("300000.00"))
    cet = _create_cost_element_type(db)

    # Create cost elements for both WBEs
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
        budget_bac=Decimal("150000.00"),
        revenue_plan=Decimal("180000.00"),
    )

    # Create schedules
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

    schedule2 = create_schedule_for_cost_element(
        db,
        ce2.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 2, 1),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
        description="Baseline",
        created_by_id=created_by_id,
    )
    schedule2.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(schedule2)
    db.commit()
    db.refresh(schedule1)
    db.refresh(schedule2)

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

    # Create cost registrations
    cr1_in = CostRegistrationCreate(
        cost_element_id=ce1.cost_element_id,
        registration_date=date(2024, 1, 15),
        amount=Decimal("45000.00"),
        cost_category="labor",
        description="Cost registration 1",
        is_quality_cost=False,
    )
    cr1_data = cr1_in.model_dump()
    cr1_data["created_by_id"] = created_by_id
    cr1 = CostRegistration.model_validate(cr1_data)
    cr1.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    db.add(cr1)

    cr2_in = CostRegistrationCreate(
        cost_element_id=ce2.cost_element_id,
        registration_date=date(2024, 1, 15),
        amount=Decimal("80000.00"),
        cost_category="labor",
        description="Cost registration 2",
        is_quality_cost=False,
    )
    cr2_data = cr2_in.model_dump()
    cr2_data["created_by_id"] = created_by_id
    cr2 = CostRegistration.model_validate(cr2_data)
    cr2.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    db.add(cr2)
    db.commit()

    control_date = date(2024, 1, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _project_endpoint(project.project_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "project"
    assert data["project_id"] == str(project.project_id)
    # Aggregated values
    # PV = 100000*(14/31) + 150000*(14/31) = 45160 + 67740 = 112900
    # EV = 100000*0.4 + 150000*0.5 = 40000 + 75000 = 115000
    # AC = 45000 + 80000 = 125000
    # BAC = 100000 + 150000 = 250000
    # CPI = 115000/125000 = 0.9200
    # SPI = 115000/112900 = 1.0186
    # TCPI = (250000-115000)/(250000-125000) = 135000/125000 = 1.0800
    assert abs(Decimal(str(data["planned_value"])) - Decimal("112900.00")) < Decimal(
        "1.00"
    )
    assert Decimal(str(data["earned_value"])) == Decimal("115000.00")
    assert Decimal(str(data["actual_cost"])) == Decimal("125000.00")
    assert Decimal(str(data["budget_bac"])) == Decimal("250000.00")
    assert abs(Decimal(str(data["cpi"])) - Decimal("0.9200")) < Decimal("0.0001")
    assert abs(Decimal(str(data["spi"])) - Decimal("1.0186")) < Decimal("0.0001")
    assert abs(Decimal(str(data["tcpi"])) - Decimal("1.0800")) < Decimal("0.0001")


def test_get_project_evm_indices_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Project EVM indices should return 404 for non-existent project."""
    fake_project_id = uuid.uuid4()

    control_date = date(2024, 1, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _project_endpoint(fake_project_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 404


def test_get_project_evm_indices_includes_variances(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Project EVM indices should include cost_variance and schedule_variance fields."""
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
        _project_endpoint(project.project_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # Verify variance fields exist
    assert "cost_variance" in data
    assert "schedule_variance" in data


def test_get_project_evm_indices_variance_calculation(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Project EVM indices should calculate variances correctly: CV=EV-AC, SV=EV-PV."""
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
        _project_endpoint(project.project_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # EV = 40000, AC = 45000, PV ≈ 45160
    # CV = EV - AC = 40000 - 45000 = -5000 (over-budget)
    # SV = EV - PV = 40000 - 45160 = -5160 (behind-schedule)
    ev = Decimal(str(data["earned_value"]))
    ac = Decimal(str(data["actual_cost"]))
    pv = Decimal(str(data["planned_value"]))
    cv = Decimal(str(data["cost_variance"]))
    sv = Decimal(str(data["schedule_variance"]))

    # Verify CV = EV - AC
    assert abs(cv - (ev - ac)) < Decimal("0.01")
    # Verify SV = EV - PV
    assert abs(sv - (ev - pv)) < Decimal("1.00")  # Allow for PV rounding


def test_get_project_evm_indices_backward_compatibility(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Project EVM indices should maintain backward compatibility with existing fields."""
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

    control_date = date(2024, 1, 15)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        _project_endpoint(project.project_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # Verify all existing fields are still present
    assert "cpi" in data
    assert "spi" in data
    assert "tcpi" in data
    assert "planned_value" in data
    assert "earned_value" in data
    assert "actual_cost" in data
    assert "budget_bac" in data
    assert "level" in data
    assert "control_date" in data
    assert "project_id" in data


def test_get_project_evm_indices_negative_variances(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Project EVM indices should handle negative variances correctly."""
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

    # Create earned value entry (30% complete - behind schedule)
    create_earned_value_entry(
        db,
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 1, 15),
        percent_complete=Decimal("30.00"),
        created_by_id=created_by_id,
    )

    # Create cost registration (AC = 50000 - over budget)
    cr_in = CostRegistrationCreate(
        cost_element_id=ce.cost_element_id,
        registration_date=date(2024, 1, 15),
        amount=Decimal("50000.00"),
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
        _project_endpoint(project.project_id),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # EV = 30000, AC = 50000, PV ≈ 45160
    # CV = EV - AC = 30000 - 50000 = -20000 (over-budget, negative)
    # SV = EV - PV = 30000 - 45160 = -15160 (behind-schedule, negative)
    cv = Decimal(str(data["cost_variance"]))
    sv = Decimal(str(data["schedule_variance"]))

    assert cv < Decimal("0.00")  # Negative (over-budget)
    assert sv < Decimal("0.00")  # Negative (behind-schedule)
