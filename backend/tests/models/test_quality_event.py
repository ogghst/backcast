"""Tests for QualityEvent model."""
import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    Project,
    ProjectCreate,
    QualityEvent,
    QualityEventCreate,
    QualityEventPublic,
    UserCreate,
)


def test_create_quality_event(db: Session) -> None:
    """Test creating a quality event."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Quality Event Test Project",
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

    # Create quality event
    qe_in = QualityEventCreate(
        project_id=project.project_id,
        event_date=date(2024, 5, 15),
        title="Non-conformity in assembly",
        description="Component mismatch discovered during quality check",
        root_cause="non_conformita",
        responsible_department="Quality Control",
        estimated_cost_impact=2500.00,
        status="identified",
        created_by_id=pm_user.id,
    )

    qe = QualityEvent.model_validate(qe_in)
    db.add(qe)
    db.commit()
    db.refresh(qe)

    # Verify quality event was created
    assert qe.quality_event_id is not None
    assert qe.title == "Non-conformity in assembly"
    assert qe.root_cause == "non_conformita"
    assert qe.estimated_cost_impact == 2500.00
    assert hasattr(qe, "project")  # Relationship should exist


def test_quality_event_root_cause_enum(db: Session) -> None:
    """Test that root_cause is validated."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Root Cause Test",
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

    # Test valid root causes
    valid_causes = [
        "non_conformita",
        "forecasting",
        "ordine_integrativo",
        "baseline",
        "scrittura_actual",
        "garanzia",
        "closure",
    ]
    for root_cause in valid_causes:
        qe_in = QualityEventCreate(
            project_id=project.project_id,
            event_date=date(2024, 6, 1),
            title=f"Test {root_cause}",
            description="Test quality event",
            root_cause=root_cause,
            responsible_department="Test",
            status="identified",
            created_by_id=pm_user.id,
        )
        qe = QualityEvent.model_validate(qe_in)
        db.add(qe)
        db.commit()
        db.refresh(qe)
        assert qe.root_cause == root_cause


def test_quality_event_status_enum(db: Session) -> None:
    """Test that status is validated."""
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

    valid_statuses = [
        "identified",
        "investigating",
        "corrective_action_planned",
        "corrective_action_in_progress",
        "resolved",
    ]
    for status in valid_statuses:
        qe_in = QualityEventCreate(
            project_id=project.project_id,
            event_date=date(2024, 6, 1),
            title=f"Test {status}",
            description="Test quality event",
            root_cause="non_conformita",
            responsible_department="Test",
            status=status,
            created_by_id=pm_user.id,
        )
        qe = QualityEvent.model_validate(qe_in)
        db.add(qe)
        db.commit()
        db.refresh(qe)
        assert qe.status == status


def test_quality_event_public_schema() -> None:
    """Test QualityEventPublic schema for API responses."""
    import datetime

    qe_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    qe_public = QualityEventPublic(
        quality_event_id=qe_id,
        project_id=project_id,
        event_date=date(2024, 7, 20),
        title="Public test quality event",
        description="Public test description",
        root_cause="forecasting",
        responsible_department="Engineering",
        estimated_cost_impact=5000.00,
        actual_cost_impact=5200.00,
        status="resolved",
        created_by_id=user_id,
        created_at=now,
    )

    assert qe_public.quality_event_id == qe_id
    assert qe_public.title == "Public test quality event"
    assert qe_public.root_cause == "forecasting"
