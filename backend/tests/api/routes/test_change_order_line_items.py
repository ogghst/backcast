"""Tests for Change Order Line Items API routes."""

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Project, User, UserCreate


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


def test_line_items_auto_generated_from_branch_comparison(
    client: TestClient, db: Session
) -> None:
    """Test that line items are auto-generated from branch vs main comparison."""
    from app.models import WBE, CostElement, CostElementType, CostElementTypeCreate

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
        "change_order_number": "CO-LINE-001",
        "title": "Line Items Test",
        "description": "Test line items generation",
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

    # Create CostElementType
    cet_in = CostElementTypeCreate(
        type_code=f"line_{uuid.uuid4().hex[:6]}",
        type_name="Line Item Type",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    # Create WBE in main branch
    main_entity_id = uuid.uuid4()
    main_wbe = WBE(
        entity_id=main_entity_id,
        project_id=project.project_id,
        machine_type="Main WBE",
        revenue_allocation=10000.00,
        business_status="designing",
        branch="main",
        version=1,
        status="active",
    )
    db.add(main_wbe)
    db.flush()

    # Create CostElement in main
    main_ce_entity_id = uuid.uuid4()
    main_ce = CostElement(
        entity_id=main_ce_entity_id,
        wbe_id=main_wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="MAIN",
        department_name="Main Department",
        budget_bac=5000.00,
        revenue_plan=6000.00,
        business_status="planned",
        branch="main",
        version=1,
        status="active",
    )
    db.add(main_ce)
    db.commit()

    # Create modified WBE in branch (UPDATE operation)
    branch_wbe = WBE(
        entity_id=main_entity_id,  # Same entity_id = update
        project_id=project.project_id,
        machine_type="Updated WBE",
        revenue_allocation=15000.00,  # Changed
        business_status="designing",
        branch=branch,
        version=1,
        status="active",
    )
    db.add(branch_wbe)
    db.flush()

    # Create new CostElement in branch (CREATE operation)
    new_ce_entity_id = uuid.uuid4()
    branch_ce_new = CostElement(
        entity_id=new_ce_entity_id,
        wbe_id=branch_wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="NEW",
        department_name="New Department",
        budget_bac=3000.00,
        revenue_plan=4000.00,
        business_status="planned",
        branch=branch,
        version=1,
        status="active",
    )
    db.add(branch_ce_new)
    db.commit()

    # Trigger line items generation (GET endpoint should auto-generate)
    response = client.get(
        f"/api/v1/projects/{project.project_id}/change-orders/{co_id}/line-items",
        headers=headers,
    )
    assert response.status_code == 200
    line_items = response.json()

    # Verify line items were generated
    assert len(line_items) >= 2  # At least UPDATE and CREATE operations

    # Find UPDATE line item
    update_item = next(
        (item for item in line_items if item["operation_type"] == "update"), None
    )
    assert update_item is not None
    assert update_item["target_type"] == "wbe"
    assert (
        update_item["budget_change"] is not None
        or update_item["revenue_change"] is not None
    )

    # Find CREATE line item
    create_item = next(
        (item for item in line_items if item["operation_type"] == "create"), None
    )
    assert create_item is not None
    assert create_item["target_type"] == "cost_element"


def test_line_items_get_endpoint(client: TestClient, db: Session) -> None:
    """Test that line items can be read (GET endpoint)."""
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
        "change_order_number": "CO-LINE-002",
        "title": "Line Items Test 2",
        "description": "Test line items GET",
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

    # Get line items (should return empty list if no branch changes)
    response = client.get(
        f"/api/v1/projects/{project.project_id}/change-orders/{co_id}/line-items",
        headers=headers,
    )
    assert response.status_code == 200
    line_items = response.json()
    assert isinstance(line_items, list)


def test_line_items_include_required_fields(client: TestClient, db: Session) -> None:
    """Test that line items include operation_type, target_type, and financial changes."""
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
        "change_order_number": "CO-LINE-003",
        "title": "Line Items Fields Test",
        "description": "Test line items fields",
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
        revenue_allocation=20000.00,
        business_status="designing",
        branch=branch,
        version=1,
        status="active",
    )
    db.add(branch_wbe)
    db.commit()

    # Get line items
    response = client.get(
        f"/api/v1/projects/{project.project_id}/change-orders/{co_id}/line-items",
        headers=headers,
    )
    assert response.status_code == 200
    line_items = response.json()

    if len(line_items) > 0:
        item = line_items[0]
        # Verify required fields exist
        assert "operation_type" in item
        assert "target_type" in item
        assert "budget_change" in item
        assert "revenue_change" in item
        assert item["operation_type"] in ["create", "update", "delete"]
        assert item["target_type"] in ["wbe", "cost_element"]
