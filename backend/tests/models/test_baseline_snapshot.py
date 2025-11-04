"""Tests for BaselineSnapshot model."""
import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    BaselineSnapshot,
    BaselineSnapshotCreate,
    BaselineSnapshotPublic,
    Project,
    ProjectCreate,
    UserCreate,
)


def test_create_baseline_snapshot(db: Session) -> None:
    """Test creating a baseline snapshot."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Baseline Snapshot Test",
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

    # Create baseline snapshot
    snapshot_in = BaselineSnapshotCreate(
        project_id=project.project_id,
        baseline_date=date(2024, 1, 15),
        milestone_type="kickoff",
        description="Initial project baseline established",
        department="Project Management",
        is_pmb=True,
        created_by_id=pm_user.id,
    )

    snapshot = BaselineSnapshot.model_validate(snapshot_in)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    # Verify snapshot was created
    assert snapshot.snapshot_id is not None
    assert snapshot.milestone_type == "kickoff"
    assert snapshot.is_pmb is True
    assert hasattr(snapshot, "project")  # Relationship should exist


def test_baseline_snapshot_milestone_enum(db: Session) -> None:
    """Test that milestone_type is validated."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Milestone Test",
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

    valid_milestones = [
        "kickoff",
        "bom_release",
        "engineering_complete",
        "procurement_complete",
        "manufacturing_start",
        "shipment",
        "site_arrival",
        "commissioning_start",
        "commissioning_complete",
        "closeout",
    ]
    for milestone_type in valid_milestones:
        snapshot_in = BaselineSnapshotCreate(
            project_id=project.project_id,
            baseline_date=date(2024, 6, 1),
            milestone_type=milestone_type,
            department="Test",
            is_pmb=False,
            created_by_id=pm_user.id,
        )
        snapshot = BaselineSnapshot.model_validate(snapshot_in)
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        assert snapshot.milestone_type == milestone_type


def test_baseline_snapshot_public_schema() -> None:
    """Test BaselineSnapshotPublic schema for API responses."""
    import datetime

    snapshot_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    snapshot_public = BaselineSnapshotPublic(
        snapshot_id=snapshot_id,
        project_id=project_id,
        baseline_date=date(2024, 8, 15),
        milestone_type="engineering_complete",
        description="Public test baseline snapshot",
        department="Engineering",
        is_pmb=False,
        created_by_id=user_id,
        created_at=now,
    )

    assert snapshot_public.snapshot_id == snapshot_id
    assert snapshot_public.milestone_type == "engineering_complete"
