"""Tests for earned value API endpoints."""
import uuid
from datetime import date
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
from tests.utils.earned_value_entry import create_earned_value_entry
from tests.utils.user import set_time_machine_date


def _create_project_with_manager(db: Session) -> tuple[Project, uuid.UUID]:
    """Create a project with a project manager user."""
    email = f"ev_pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="EV Test Project",
        customer_name="EV Customer",
        contract_value=Decimal("250000.00"),
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


def _create_cost_element_type(db: Session) -> CostElementType:
    cet_in = CostElementTypeCreate(
        type_code=f"ev_type_{uuid.uuid4().hex[:8]}",
        type_name="EV Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)
    return cet


def _create_wbe(db: Session, project_id: uuid.UUID, revenue: Decimal) -> WBE:
    wbe_in = WBECreate(
        project_id=project_id,
        machine_type="EV Machine",
        revenue_allocation=revenue,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
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
    db.add(ce)
    db.commit()
    db.refresh(ce)
    return ce


def test_select_entry_for_cost_element_finds_latest(
    client: TestClient,  # noqa: ARG001
    superuser_token_headers: dict[str, str],  # noqa: ARG001
    db: Session,
) -> None:
    """Should find the most recent entry where completion_date <= control_date."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("100000.00"))
    cet = _create_cost_element_type(db)

    cost_element = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    # Create entries with different completion dates
    _entry1 = create_earned_value_entry(
        db,
        cost_element_id=cost_element.cost_element_id,
        completion_date=date(2024, 1, 15),
        percent_complete=Decimal("30.00"),
        created_by_id=created_by_id,
    )
    entry2 = create_earned_value_entry(
        db,
        cost_element_id=cost_element.cost_element_id,
        completion_date=date(2024, 2, 10),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )
    _entry3 = create_earned_value_entry(
        db,
        cost_element_id=cost_element.cost_element_id,
        completion_date=date(2024, 2, 20),  # After control_date
        percent_complete=Decimal("70.00"),
        created_by_id=created_by_id,
    )

    # Import the helper function
    from app.api.routes.earned_value import _select_entry_for_cost_element

    control_date = date(2024, 2, 15)
    result = _select_entry_for_cost_element(
        db, cost_element.cost_element_id, control_date
    )

    assert result is not None
    assert result.earned_value_id == entry2.earned_value_id
    assert result.completion_date == date(2024, 2, 10)


def test_select_entry_for_cost_element_returns_none_if_none(
    client: TestClient,  # noqa: ARG001
    superuser_token_headers: dict[str, str],  # noqa: ARG001
    db: Session,
) -> None:
    """Should return None if no entries exist or all entries are after control_date."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("100000.00"))
    cet = _create_cost_element_type(db)

    cost_element = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    # Create entry after control_date
    create_earned_value_entry(
        db,
        cost_element_id=cost_element.cost_element_id,
        completion_date=date(2024, 2, 20),  # After control_date
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )

    from app.api.routes.earned_value import _select_entry_for_cost_element

    control_date = date(2024, 2, 10)  # Before entry
    result = _select_entry_for_cost_element(
        db, cost_element.cost_element_id, control_date
    )

    assert result is None


def test_get_entry_map_batches_queries(
    client: TestClient,  # noqa: ARG001
    superuser_token_headers: dict[str, str],  # noqa: ARG001
    db: Session,
) -> None:
    """Should efficiently query entries for multiple cost elements."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("100000.00"))
    cet = _create_cost_element_type(db)

    ce1 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG1",
        department_name="Engineering 1",
        budget_bac=Decimal("50000.00"),
        revenue_plan=Decimal("60000.00"),
    )
    ce2 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG2",
        department_name="Engineering 2",
        budget_bac=Decimal("30000.00"),
        revenue_plan=Decimal("35000.00"),
    )

    # Create entries for both cost elements
    entry1 = create_earned_value_entry(
        db,
        cost_element_id=ce1.cost_element_id,
        completion_date=date(2024, 2, 10),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )
    entry2 = create_earned_value_entry(
        db,
        cost_element_id=ce2.cost_element_id,
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("30.00"),
        created_by_id=created_by_id,
    )

    from app.api.routes.earned_value import _get_entry_map

    control_date = date(2024, 2, 20)
    cost_element_ids = [ce1.cost_element_id, ce2.cost_element_id]
    result = _get_entry_map(db, cost_element_ids, control_date)

    assert len(result) == 2
    assert result[ce1.cost_element_id] is not None
    assert result[ce1.cost_element_id].earned_value_id == entry1.earned_value_id
    assert result[ce2.cost_element_id] is not None
    assert result[ce2.cost_element_id].earned_value_id == entry2.earned_value_id


def test_get_entry_map_empty_list(
    client: TestClient,  # noqa: ARG001
    superuser_token_headers: dict[str, str],  # noqa: ARG001
    db: Session,
) -> None:
    """Should return empty dict for empty cost_element_ids list."""
    from app.api.routes.earned_value import _get_entry_map

    control_date = date(2024, 2, 20)
    result = _get_entry_map(db, [], control_date)

    assert result == {}


def test_get_earned_value_for_cost_element(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Should return earned value for a cost element at control date."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("100000.00"))
    cet = _create_cost_element_type(db)

    cost_element = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    # Create earned value entry
    create_earned_value_entry(
        db,
        cost_element_id=cost_element.cost_element_id,
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("50.00"),
        created_by_id=created_by_id,
    )

    control_date = date(2024, 2, 20)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        (
            f"{settings.API_V1_STR}/projects/{project.project_id}"
            f"/earned-value/cost-elements/{cost_element.cost_element_id}"
        ),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["level"] == "cost-element"
    assert data["cost_element_id"] == str(cost_element.cost_element_id)
    assert data["control_date"] == control_date.isoformat()
    assert Decimal(data["earned_value"]) == Decimal("50000.00")  # 100000 * 0.50
    assert Decimal(data["percent_complete"]) == Decimal("0.5000")
    assert Decimal(data["budget_bac"]) == Decimal("100000.00")


def test_get_earned_value_cost_element_no_entry_returns_zero(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Should return zero EV if no earned value entries exist."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("100000.00"))
    cet = _create_cost_element_type(db)

    cost_element = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    control_date = date(2024, 2, 20)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        (
            f"{settings.API_V1_STR}/projects/{project.project_id}"
            f"/earned-value/cost-elements/{cost_element.cost_element_id}"
        ),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert Decimal(data["earned_value"]) == Decimal("0.00")
    assert Decimal(data["percent_complete"]) == Decimal("0.0000")


def test_get_earned_value_cost_element_not_found(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Should return 404 if cost element not found."""
    project, _ = _create_project_with_manager(db)

    control_date = date(2024, 2, 20)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        (
            f"{settings.API_V1_STR}/projects/{project.project_id}"
            f"/earned-value/cost-elements/{uuid.uuid4()}"
        ),
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_earned_value_cost_element_uses_time_machine(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Should use stored time machine date when query param is omitted."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("100000.00"))
    cet = _create_cost_element_type(db)

    cost_element = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("100000.00"),
        revenue_plan=Decimal("120000.00"),
    )

    control_date = date(2024, 2, 20)
    create_earned_value_entry(
        db,
        cost_element_id=cost_element.cost_element_id,
        completion_date=control_date,
        percent_complete=Decimal("25.00"),
        created_by_id=created_by_id,
    )

    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        (
            f"{settings.API_V1_STR}/projects/{project.project_id}"
            f"/earned-value/cost-elements/{cost_element.cost_element_id}"
        ),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["control_date"] == control_date.isoformat()
    assert Decimal(data["earned_value"]) == Decimal("25000.00")
    assert Decimal(data["percent_complete"]) == Decimal("0.2500")


def test_get_earned_value_for_wbe(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Should return aggregated earned value for a WBE."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("150000.00"))
    cet = _create_cost_element_type(db)

    ce1 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG1",
        department_name="Engineering 1",
        budget_bac=Decimal("60000.00"),
        revenue_plan=Decimal("70000.00"),
    )
    ce2 = _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG2",
        department_name="Engineering 2",
        budget_bac=Decimal("40000.00"),
        revenue_plan=Decimal("50000.00"),
    )

    # Create earned value entries
    create_earned_value_entry(
        db,
        cost_element_id=ce1.cost_element_id,
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("50.00"),  # 60000 * 0.50 = 30000
        created_by_id=created_by_id,
    )
    create_earned_value_entry(
        db,
        cost_element_id=ce2.cost_element_id,
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("25.00"),  # 40000 * 0.25 = 10000
        created_by_id=created_by_id,
    )

    control_date = date(2024, 2, 20)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        (
            f"{settings.API_V1_STR}/projects/{project.project_id}"
            f"/earned-value/wbes/{wbe.wbe_id}"
        ),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["level"] == "wbe"
    assert data["wbe_id"] == str(wbe.wbe_id)
    assert data["control_date"] == control_date.isoformat()
    # Total EV = 30000 + 10000 = 40000
    assert Decimal(data["earned_value"]) == Decimal("40000.00")
    # Total BAC = 60000 + 40000 = 100000
    assert Decimal(data["budget_bac"]) == Decimal("100000.00")
    # Weighted percent = 40000 / 100000 = 0.40
    assert Decimal(data["percent_complete"]) == Decimal("0.4000")


def test_get_earned_value_wbe_no_entries_returns_zero(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Should return zero EV if WBE has no earned value entries."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("100000.00"))
    cet = _create_cost_element_type(db)

    _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("50000.00"),
        revenue_plan=Decimal("60000.00"),
    )

    control_date = date(2024, 2, 20)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        (
            f"{settings.API_V1_STR}/projects/{project.project_id}"
            f"/earned-value/wbes/{wbe.wbe_id}"
        ),
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert Decimal(data["earned_value"]) == Decimal("0.00")
    assert Decimal(data["percent_complete"]) == Decimal("0.0000")


def test_get_earned_value_wbe_not_found(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Should return 404 if WBE not found."""
    project, _ = _create_project_with_manager(db)

    control_date = date(2024, 2, 20)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        (
            f"{settings.API_V1_STR}/projects/{project.project_id}"
            f"/earned-value/wbes/{uuid.uuid4()}"
        ),
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_earned_value_for_project(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Should return aggregated earned value for a project across all WBEs."""
    project, created_by_id = _create_project_with_manager(db)
    cet = _create_cost_element_type(db)

    wbe1 = _create_wbe(db, project.project_id, Decimal("80000.00"))
    wbe2 = _create_wbe(db, project.project_id, Decimal("90000.00"))

    ce1 = _create_cost_element(
        db,
        wbe1.wbe_id,
        cet,
        department_code="ENG1",
        department_name="Engineering 1",
        budget_bac=Decimal("30000.00"),
        revenue_plan=Decimal("35000.00"),
    )
    ce2 = _create_cost_element(
        db,
        wbe2.wbe_id,
        cet,
        department_code="ENG2",
        department_name="Engineering 2",
        budget_bac=Decimal("50000.00"),
        revenue_plan=Decimal("55000.00"),
    )

    # Create earned value entries
    create_earned_value_entry(
        db,
        cost_element_id=ce1.cost_element_id,
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("60.00"),  # 30000 * 0.60 = 18000
        created_by_id=created_by_id,
    )
    create_earned_value_entry(
        db,
        cost_element_id=ce2.cost_element_id,
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("40.00"),  # 50000 * 0.40 = 20000
        created_by_id=created_by_id,
    )

    control_date = date(2024, 2, 20)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/earned-value",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["level"] == "project"
    assert data["project_id"] == str(project.project_id)
    assert data["control_date"] == control_date.isoformat()
    # Total EV = 18000 + 20000 = 38000
    assert Decimal(data["earned_value"]) == Decimal("38000.00")
    # Total BAC = 30000 + 50000 = 80000
    assert Decimal(data["budget_bac"]) == Decimal("80000.00")
    # Weighted percent = 38000 / 80000 = 0.4750
    assert Decimal(data["percent_complete"]) == Decimal("0.4750")


def test_get_earned_value_project_no_entries_returns_zero(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Should return zero EV if project has no earned value entries."""
    project, created_by_id = _create_project_with_manager(db)
    wbe = _create_wbe(db, project.project_id, Decimal("50000.00"))
    cet = _create_cost_element_type(db)

    _create_cost_element(
        db,
        wbe.wbe_id,
        cet,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("30000.00"),
        revenue_plan=Decimal("35000.00"),
    )

    control_date = date(2024, 2, 20)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}/earned-value",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert Decimal(data["earned_value"]) == Decimal("0.00")
    assert Decimal(data["percent_complete"]) == Decimal("0.0000")


def test_get_earned_value_project_not_found(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,  # noqa: ARG001
) -> None:
    """Should return 404 if project not found."""
    control_date = date(2024, 2, 20)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        f"{settings.API_V1_STR}/projects/{uuid.uuid4()}/earned-value",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
