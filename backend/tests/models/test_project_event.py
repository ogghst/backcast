"""Tests for ProjectEvent model."""
import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    Project,
    ProjectCreate,
    ProjectEvent,
    ProjectEventCreate,
    ProjectEventPublic,
    UserCreate,
)


def test_create_project_event(db: Session) -> None:
    """Test creating a project event."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Project Event Test",
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

    # Create project event
    event_in = ProjectEventCreate(
        project_id=project.project_id,
        event_date=date(2024, 3, 15),
        event_type="aperture",
        department="Project Management",
        description="Project kickoff meeting completed",
        notes="All stakeholders present",
        created_by_id=pm_user.id,
        is_deleted=False,
    )

    event = ProjectEvent.model_validate(event_in)
    db.add(event)
    db.commit()
    db.refresh(event)

    # Verify event was created
    assert event.event_id is not None
    assert event.event_type == "aperture"
    assert event.department == "Project Management"
    assert event.is_deleted is False
    assert hasattr(event, "project")  # Relationship should exist


def test_project_event_type_enum(db: Session) -> None:
    """Test that event_type is validated."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Event Type Test",
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

    valid_types = [
        "aperture",
        "technical_release",
        "internal_test_start",
        "construction_start",
        "testing",
        "closure",
    ]
    for event_type in valid_types:
        event_in = ProjectEventCreate(
            project_id=project.project_id,
            event_date=date(2024, 6, 1),
            event_type=event_type,
            department="Test",
            description=f"Test {event_type} event",
            created_by_id=pm_user.id,
            is_deleted=False,
        )
        event = ProjectEvent.model_validate(event_in)
        db.add(event)
        db.commit()
        db.refresh(event)
        assert event.event_type == event_type


def test_project_event_public_schema() -> None:
    """Test ProjectEventPublic schema for API responses."""
    import datetime

    event_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    event_public = ProjectEventPublic(
        event_id=event_id,
        project_id=project_id,
        event_date=date(2024, 10, 15),
        event_type="closure",
        department="Project Management",
        description="Public test project event",
        created_by_id=user_id,
        created_at=now,
        last_modified_at=now,
        is_deleted=False,
    )

    assert event_public.event_id == event_id
    assert event_public.event_type == "closure"
