"""Tests for Project model."""
import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    Project,
    ProjectCreate,
    ProjectPublic,
    UserCreate,
)


def test_create_project(db: Session) -> None:
    """Test creating a project."""
    # First create a user to be the project manager
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    # Create a project
    project_in = ProjectCreate(
        project_name="Test Project",
        customer_name="Test Customer",
        contract_value=100000.00,
        project_code="PROJ-001",
        pricelist_code="LISTINO 118",
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
        notes="Test project notes",
    )

    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Verify project was created
    assert project.project_id is not None
    assert project.project_name == "Test Project"
    assert project.customer_name == "Test Customer"
    assert project.contract_value == 100000.00
    assert project.project_code == "PROJ-001"
    assert project.status == "active"
    assert project.project_manager_id == pm_user.id
    assert hasattr(project, "project_manager")  # Relationship should exist


def test_project_status_enum(db: Session) -> None:
    """Test that project status is validated."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    # Test valid statuses
    valid_statuses = ["active", "on-hold", "completed", "cancelled"]
    for status in valid_statuses:
        project_in = ProjectCreate(
            project_name=f"Project {status}",
            customer_name="Test Customer",
            contract_value=50000.00,
            start_date=date(2024, 1, 1),
            planned_completion_date=date(2024, 12, 31),
            project_manager_id=pm_user.id,
            status=status,
        )
        project = Project.model_validate(project_in)
        db.add(project)
        db.commit()
        db.refresh(project)
        assert project.status == status


def test_project_validation_rules(db: Session) -> None:
    """Test project field validation rules."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    # Test contract_value >= 0 (should allow 0 and positive values)
    project_in = ProjectCreate(
        project_name="Zero Value Project",
        customer_name="Test Customer",
        contract_value=0.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)
    assert project.contract_value == 0.00

    # Test that start_date < planned_completion_date validation
    # (this will be validated at application level)


def test_project_relationships(db: Session) -> None:
    """Test project relationships with User."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Relationship Test Project",
        customer_name="Test Customer",
        contract_value=75000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )

    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Verify foreign key relationship works
    assert project.project_manager_id == pm_user.id


def test_project_public_schema() -> None:
    """Test ProjectPublic schema for API responses."""
    project_id = uuid.uuid4()
    manager_id = uuid.uuid4()

    project_public = ProjectPublic(
        project_id=project_id,
        project_name="Public Project",
        customer_name="Public Customer",
        contract_value=100000.00,
        project_code="PUB-001",
        pricelist_code="LISTINO 119",
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=manager_id,
        status="active",
    )

    assert project_public.project_id == project_id
    assert project_public.project_name == "Public Project"
    assert project_public.contract_value == 100000.00
