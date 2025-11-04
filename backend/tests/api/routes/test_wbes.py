import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.cost_element import create_random_cost_element
from tests.utils.project import create_random_project
from tests.utils.wbe import create_random_wbe


def test_create_wbe(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a WBE."""
    # Create a project first
    project = create_random_project(db)

    data = {
        "machine_type": "Robotic Assembly Unit",
        "serial_number": "RB-001",
        "contracted_delivery_date": str(date.today() + timedelta(days=180)),
        "revenue_allocation": 50000.00,
        "status": "designing",
        "project_id": str(project.project_id),
    }
    response = client.post(
        f"{settings.API_V1_STR}/wbes/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["machine_type"] == data["machine_type"]
    assert content["serial_number"] == data["serial_number"]
    assert float(content["revenue_allocation"]) == data["revenue_allocation"]
    assert "wbe_id" in content
    assert content["project_id"] == str(project.project_id)


def test_create_wbe_invalid_project(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test creating a WBE with invalid project_id."""
    data = {
        "machine_type": "Test Machine",
        "revenue_allocation": 50000.00,
        "status": "designing",
        "project_id": str(uuid.uuid4()),
    }
    response = client.post(
        f"{settings.API_V1_STR}/wbes/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 400
    content = response.json()
    assert content["detail"] == "Project not found"


def test_read_wbe(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading a single WBE."""
    wbe = create_random_wbe(db)
    response = client.get(
        f"{settings.API_V1_STR}/wbes/{wbe.wbe_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["machine_type"] == wbe.machine_type
    assert content["wbe_id"] == str(wbe.wbe_id)


def test_read_wbe_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test reading a non-existent WBE."""
    response = client.get(
        f"{settings.API_V1_STR}/wbes/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "WBE not found"


def test_read_wbes_list_all(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading list of all WBEs."""
    create_random_wbe(db)
    create_random_wbe(db)
    response = client.get(
        f"{settings.API_V1_STR}/wbes/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content["data"]) >= 2
    assert "count" in content
    assert content["count"] >= 2


def test_read_wbes_filtered_by_project(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading WBEs filtered by project_id."""
    project = create_random_project(db)
    create_random_wbe(db, project.project_id)
    create_random_wbe(db, project.project_id)

    # Create another project with WBE
    other_project = create_random_project(db)
    create_random_wbe(db, other_project.project_id)

    response = client.get(
        f"{settings.API_V1_STR}/wbes/?project_id={project.project_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content["data"]) == 2
    assert content["count"] == 2
    # All results should belong to the requested project
    for wbe in content["data"]:
        assert wbe["project_id"] == str(project.project_id)


def test_update_wbe(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating a WBE."""
    wbe = create_random_wbe(db)
    data = {"machine_type": "Updated Machine Type", "status": "completed"}
    response = client.put(
        f"{settings.API_V1_STR}/wbes/{wbe.wbe_id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["machine_type"] == data["machine_type"]
    assert content["status"] == data["status"]
    assert content["wbe_id"] == str(wbe.wbe_id)


def test_update_wbe_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test updating a non-existent WBE."""
    data = {"machine_type": "Updated Machine Type"}
    response = client.put(
        f"{settings.API_V1_STR}/wbes/{uuid.uuid4()}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "WBE not found"


def test_delete_wbe(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test deleting a WBE."""
    wbe = create_random_wbe(db)
    response = client.delete(
        f"{settings.API_V1_STR}/wbes/{wbe.wbe_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "WBE deleted successfully"


def test_delete_wbe_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test deleting a non-existent WBE."""
    response = client.delete(
        f"{settings.API_V1_STR}/wbes/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "WBE not found"


def test_delete_wbe_with_cost_elements_should_fail(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test deleting a WBE with cost elements should be blocked."""
    wbe = create_random_wbe(db)
    # Create a cost element for this WBE
    create_random_cost_element(db, wbe.wbe_id)

    response = client.delete(
        f"{settings.API_V1_STR}/wbes/{wbe.wbe_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 400
    content = response.json()
    assert "Cannot delete WBE" in content["detail"]
    assert "existing cost element(s)" in content["detail"]

    # Verify WBE still exists
    response = client.get(
        f"{settings.API_V1_STR}/wbes/{wbe.wbe_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200


def test_create_wbe_exceeds_project_contract_value(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a WBE with revenue_allocation that exceeds project contract_value."""
    from decimal import Decimal

    from app import crud
    from app.models import Project, ProjectCreate, UserCreate

    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

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

    # Try to create WBE with revenue_allocation exceeding contract_value
    wbe_data = {
        "machine_type": "Test Machine",
        "revenue_allocation": 150000.00,  # Exceeds project contract_value of 100000.00
        "status": "designing",
        "project_id": str(project.project_id),
    }
    response = client.post(
        f"{settings.API_V1_STR}/wbes/",
        headers=superuser_token_headers,
        json=wbe_data,
    )
    assert response.status_code == 400
    content = response.json()
    assert "exceeds project contract value" in content["detail"]


def test_update_wbe_exceeds_project_contract_value(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating a WBE revenue_allocation that causes total to exceed limit."""
    from decimal import Decimal

    from app import crud
    from app.models import WBE, Project, ProjectCreate, UserCreate, WBECreate

    # Create project with specific contract_value
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

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

    # Create two WBEs within limit
    wbe1_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 1",
        revenue_allocation=Decimal("30000.00"),
        status="designing",
    )
    wbe1 = WBE.model_validate(wbe1_in)
    db.add(wbe1)
    db.commit()
    db.refresh(wbe1)

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

    # Try to update second WBE to exceed limit (total would be 30000 + 70000 = 100000)
    # But we try 70001 to exceed
    update_data = {
        "revenue_allocation": 70001.00,  # Total would be 30000 + 70001 = 100001, exceeding 100000
    }
    response = client.put(
        f"{settings.API_V1_STR}/wbes/{wbe2.wbe_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert response.status_code == 400
    content = response.json()
    assert "exceeds project contract value" in content["detail"]


def test_update_wbe_within_project_contract_value(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating a WBE revenue_allocation that stays within limit."""
    from decimal import Decimal

    from app import crud
    from app.models import WBE, Project, ProjectCreate, UserCreate, WBECreate

    # Create project with specific contract_value
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

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

    # Create two WBEs within limit
    wbe1_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine 1",
        revenue_allocation=Decimal("30000.00"),
        status="designing",
    )
    wbe1 = WBE.model_validate(wbe1_in)
    db.add(wbe1)
    db.commit()
    db.refresh(wbe1)

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

    # Update second WBE to stay within limit (total would be 30000 + 50000 = 80000, within 100000)
    update_data = {
        "revenue_allocation": 50000.00,
    }
    response = client.put(
        f"{settings.API_V1_STR}/wbes/{wbe2.wbe_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert response.status_code == 200
    content = response.json()
    assert float(content["revenue_allocation"]) == 50000.00
    assert content["machine_type"] == "Machine 2"
