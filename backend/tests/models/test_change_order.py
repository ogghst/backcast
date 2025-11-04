"""Tests for ChangeOrder model."""
import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    ChangeOrder,
    ChangeOrderCreate,
    ChangeOrderPublic,
    Project,
    ProjectCreate,
    UserCreate,
)


def test_create_change_order(db: Session) -> None:
    """Test creating a change order."""
    # Create user
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Change Order Test Project",
        customer_name="Test Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create change order
    co_in = ChangeOrderCreate(
        project_id=project.project_id,
        change_order_number="CO-001",
        title="Add Feature X",
        description="Additional feature requested by customer",
        requesting_party="Customer",
        justification="Business requirement",
        effective_date=date(2024, 6, 1),
        cost_impact=5000.00,
        revenue_impact=6000.00,
        status="draft",
        created_by_id=pm_user.id,
    )

    co = ChangeOrder.model_validate(co_in)
    db.add(co)
    db.commit()
    db.refresh(co)

    # Verify change order was created
    assert co.change_order_id is not None
    assert co.change_order_number == "CO-001"
    assert co.status == "draft"
    assert co.cost_impact == 5000.00
    assert hasattr(co, "project")  # Relationship should exist


def test_change_order_status_enum(db: Session) -> None:
    """Test that change order status is validated."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Status Test",
        customer_name="Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Test valid statuses
    valid_statuses = [
        "draft",
        "submitted",
        "under_review",
        "approved",
        "rejected",
        "implemented",
    ]
    for status in valid_statuses:
        unique_number = f"CO_{status}_{uuid.uuid4().hex[:8]}"
        co_in = ChangeOrderCreate(
            project_id=project.project_id,
            change_order_number=unique_number,
            title=f"Test {status}",
            description="Test change order",
            requesting_party="Internal",
            effective_date=date(2024, 6, 1),
            status=status,
            created_by_id=pm_user.id,
        )
        co = ChangeOrder.model_validate(co_in)
        db.add(co)
        db.commit()
        db.refresh(co)
        assert co.status == status


def test_change_order_public_schema() -> None:
    """Test ChangeOrderPublic schema for API responses."""
    import datetime

    co_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    co_public = ChangeOrderPublic(
        change_order_id=co_id,
        project_id=project_id,
        change_order_number="CO-999",
        title="Public test change order",
        description="Public test description",
        requesting_party="Customer",
        effective_date=date(2024, 8, 1),
        cost_impact=10000.00,
        revenue_impact=12000.00,
        status="approved",
        created_by_id=user_id,
        created_at=now,
    )

    assert co_public.change_order_id == co_id
    assert co_public.change_order_number == "CO-999"
    assert co_public.status == "approved"
