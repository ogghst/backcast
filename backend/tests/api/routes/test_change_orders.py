"""Tests for Change Order API routes."""

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import ChangeOrder, Project, User, UserCreate


def _create_pm_user(session: Session) -> User:
    """Helper to create a project manager user."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    from app import crud

    return crud.create_user(session=session, user_create=user_in)


def _create_project(session: Session, pm_user: User) -> Project:
    """Helper to create a project."""
    from app.models import ProjectCreate

    project_in = ProjectCreate(
        project_name="Test Project",
        customer_name="Test Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        business_status="active",
    )
    project = Project.model_validate(project_in)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def test_create_change_order_creates_branch(client: TestClient, db: Session) -> None:
    """Test that ChangeOrder creation automatically creates branch."""
    # Create user and project
    pm_user = _create_pm_user(db)
    project = _create_project(db, pm_user)

    # Login
    response = client.post(
        "/api/v1/login/access-token",
        data={"username": pm_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create change order
    co_data = {
        "project_id": str(project.project_id),
        "change_order_number": "CO-001",
        "title": "Test Change Order",
        "description": "Test description",
        "requesting_party": "Customer",
        "effective_date": "2024-06-01",
        "workflow_status": "design",
        "created_by_id": str(pm_user.id),
    }

    response = client.post(
        f"/api/v1/projects/{project.project_id}/change-orders",
        json=co_data,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Verify change order was created
    assert data["change_order_id"] is not None
    assert data["branch"] is not None
    assert data["branch"].startswith("co-")

    # Verify branch exists in database
    change_order = db.get(ChangeOrder, uuid.UUID(data["change_order_id"]))
    assert change_order is not None
    assert change_order.branch is not None
    assert change_order.branch.startswith("co-")


def test_change_order_has_branch_field(client: TestClient, db: Session) -> None:
    """Test that ChangeOrder model has branch field."""
    pm_user = _create_pm_user(db)
    project = _create_project(db, pm_user)

    # Login
    response = client.post(
        "/api/v1/login/access-token",
        data={"username": pm_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create change order
    co_data = {
        "project_id": str(project.project_id),
        "change_order_number": "CO-002",
        "title": "Test Change Order",
        "description": "Test description",
        "requesting_party": "Customer",
        "effective_date": "2024-06-01",
        "workflow_status": "design",
        "created_by_id": str(pm_user.id),
    }

    response = client.post(
        f"/api/v1/projects/{project.project_id}/change-orders",
        json=co_data,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Verify branch field exists
    assert "branch" in data
    assert data["branch"] is not None


def test_change_order_approval_triggers_merge(client: TestClient, db: Session) -> None:
    """Test that ChangeOrder approval triggers merge operation."""
    from app.models import WBE

    pm_user = _create_pm_user(db)
    project = _create_project(db, pm_user)

    # Login
    response = client.post(
        "/api/v1/login/access-token",
        data={"username": pm_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create change order
    co_data = {
        "project_id": str(project.project_id),
        "change_order_number": "CO-003",
        "title": "Test Change Order",
        "description": "Test description",
        "requesting_party": "Customer",
        "effective_date": "2024-06-01",
        "workflow_status": "design",
        "created_by_id": str(pm_user.id),
    }

    response = client.post(
        f"/api/v1/projects/{project.project_id}/change-orders",
        json=co_data,
        headers=headers,
    )
    assert response.status_code == 200
    co_id = uuid.UUID(response.json()["change_order_id"])
    branch = response.json()["branch"]

    # Create WBE in branch
    entity_id = uuid.uuid4()
    branch_wbe = WBE(
        entity_id=entity_id,
        project_id=project.project_id,
        machine_type="Branch WBE",
        revenue_allocation=50000.00,
        business_status="designing",
        branch=branch,
        version=1,
        status="active",
    )
    db.add(branch_wbe)
    db.commit()

    # Approve change order (transition to 'approve')
    response = client.post(
        f"/api/v1/projects/{project.project_id}/change-orders/{co_id}/transition",
        json={"workflow_status": "approve", "approved_by_id": str(pm_user.id)},
        headers=headers,
    )
    assert response.status_code == 200

    # Execute change order (transition to 'execute' - this triggers merge)
    response = client.post(
        f"/api/v1/projects/{project.project_id}/change-orders/{co_id}/transition",
        json={"workflow_status": "execute", "implemented_by_id": str(pm_user.id)},
        headers=headers,
    )
    assert response.status_code == 200

    # Verify branch was merged (WBE should exist in main branch)
    main_wbe = db.exec(
        select(WBE)
        .where(WBE.entity_id == entity_id)
        .where(WBE.branch == "main")
        .order_by(WBE.version.desc())
    ).first()
    assert main_wbe is not None
    assert main_wbe.machine_type == "Branch WBE"


def test_change_order_cancellation_triggers_branch_delete(
    client: TestClient, db: Session
) -> None:
    """Test that ChangeOrder cancellation triggers branch soft delete."""
    from app.models import WBE
    from app.services.branch_filtering import apply_branch_filters

    pm_user = _create_pm_user(db)
    project = _create_project(db, pm_user)

    # Login
    response = client.post(
        "/api/v1/login/access-token",
        data={"username": pm_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create change order
    co_data = {
        "project_id": str(project.project_id),
        "change_order_number": "CO-004",
        "title": "Test Change Order",
        "description": "Test description",
        "requesting_party": "Customer",
        "effective_date": "2024-06-01",
        "workflow_status": "design",
        "created_by_id": str(pm_user.id),
    }

    response = client.post(
        f"/api/v1/projects/{project.project_id}/change-orders",
        json=co_data,
        headers=headers,
    )
    assert response.status_code == 200
    co_id = uuid.UUID(response.json()["change_order_id"])
    branch = response.json()["branch"]

    # Create WBE in branch
    entity_id = uuid.uuid4()
    branch_wbe = WBE(
        entity_id=entity_id,
        project_id=project.project_id,
        machine_type="Branch WBE",
        revenue_allocation=50000.00,
        business_status="designing",
        branch=branch,
        version=1,
        status="active",
    )
    db.add(branch_wbe)
    db.commit()
    wbe_id = branch_wbe.wbe_id

    # Cancel change order (set workflow_status to 'cancelled')
    # Note: Cancellation should be done via update endpoint
    response = client.put(
        f"/api/v1/projects/{project.project_id}/change-orders/{co_id}",
        json={"workflow_status": "cancelled"},
        headers=headers,
    )
    assert response.status_code == 200

    # Refresh session to see changes from endpoint
    db.expire_all()

    # Verify branch entities are soft deleted (status='deleted')
    deleted_wbe = db.get(WBE, wbe_id)
    assert deleted_wbe is not None
    assert deleted_wbe.status == "deleted"

    # Verify branch entities don't appear in normal queries
    normal_query = apply_branch_filters(
        select(WBE), WBE, branch=branch, include_deleted=False
    )
    active_wbes = db.exec(normal_query).all()
    assert len(active_wbes) == 0


def test_change_order_number_auto_generation(client: TestClient, db: Session) -> None:
    """Test that change order number is auto-generated if not provided."""
    pm_user = _create_pm_user(db)
    project = _create_project(db, pm_user)

    # Login
    response = client.post(
        "/api/v1/login/access-token",
        data={"username": pm_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create change order without change_order_number
    co_data = {
        "project_id": str(project.project_id),
        "title": "Test Change Order",
        "description": "Test description",
        "requesting_party": "Customer",
        "effective_date": "2024-06-01",
        "workflow_status": "design",
        "created_by_id": str(pm_user.id),
    }

    response = client.post(
        f"/api/v1/projects/{project.project_id}/change-orders",
        json=co_data,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Verify change order number was auto-generated
    assert "change_order_number" in data
    assert data["change_order_number"] is not None
    assert data["change_order_number"].startswith("CO-")
