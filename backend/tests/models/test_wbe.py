"""Tests for WBE model."""
import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    WBE,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
    WBEPublic,
)


def test_create_wbe(db: Session) -> None:
    """Test creating a WBE."""
    # Create a project first
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Test Project",
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

    # Create a WBE
    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Robotic Assembly Unit",
        serial_number="RB-001",
        contracted_delivery_date=date(2024, 6, 30),
        revenue_allocation=50000.00,
        status="designing",
        notes="Primary WBE for test project",
    )

    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Verify WBE was created
    assert wbe.wbe_id is not None
    assert wbe.machine_type == "Robotic Assembly Unit"
    assert wbe.serial_number == "RB-001"
    assert wbe.revenue_allocation == 50000.00
    assert wbe.status == "designing"
    assert wbe.project_id == project.project_id
    assert hasattr(wbe, "project")  # Relationship should exist


def test_wbe_project_relationship(db: Session) -> None:
    """Test that WBE can be accessed through project relationship."""
    # Create a project
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Relationship Test Project",
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

    # Create multiple WBEs for this project
    wbe1_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine A",
        revenue_allocation=30000.00,
        status="designing",
    )
    wbe1 = WBE.model_validate(wbe1_in)
    db.add(wbe1)

    wbe2_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine B",
        revenue_allocation=20000.00,
        status="in-production",
    )
    wbe2 = WBE.model_validate(wbe2_in)
    db.add(wbe2)

    db.commit()
    db.refresh(project)

    # Verify relationship
    assert wbe1.project_id == project.project_id
    assert wbe2.project_id == project.project_id


def test_wbe_status_enum(db: Session) -> None:
    """Test that WBE status is validated."""
    # Create a project
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Status Test Project",
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

    # Test valid statuses
    valid_statuses = [
        "designing",
        "in-production",
        "shipped",
        "commissioning",
        "completed",
    ]
    for status in valid_statuses:
        wbe_in = WBECreate(
            project_id=project.project_id,
            machine_type=f"Machine {status}",
            revenue_allocation=10000.00,
            status=status,
        )
        wbe = WBE.model_validate(wbe_in)
        db.add(wbe)
        db.commit()
        db.refresh(wbe)
        assert wbe.status == status


def test_wbe_public_schema() -> None:
    """Test WBEPublic schema for API responses."""
    wbe_id = uuid.uuid4()
    project_id = uuid.uuid4()

    wbe_public = WBEPublic(
        wbe_id=wbe_id,
        project_id=project_id,
        machine_type="Public WBE",
        serial_number="PUB-001",
        contracted_delivery_date=date(2024, 6, 30),
        revenue_allocation=25000.00,
        status="designing",
        notes="Public test WBE",
    )

    assert wbe_public.wbe_id == wbe_id
    assert wbe_public.project_id == project_id
    assert wbe_public.machine_type == "Public WBE"
    assert wbe_public.revenue_allocation == 25000.00
