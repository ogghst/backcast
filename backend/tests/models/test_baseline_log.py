"""Tests for BaselineLog model."""
import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    BaselineLog,
    BaselineLogCreate,
    BaselineLogPublic,
    UserCreate,
)


def test_create_baseline_log(db: Session) -> None:
    """Test creating a baseline log entry."""
    # Create a user
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Create a baseline log
    baseline_in = BaselineLogCreate(
        baseline_type="schedule",
        baseline_date=date(2024, 1, 15),
        description="Initial schedule baseline",
        created_by_id=user.id,
    )

    baseline = BaselineLog.model_validate(baseline_in)
    db.add(baseline)
    db.commit()
    db.refresh(baseline)

    # Verify baseline was created
    assert baseline.baseline_id is not None
    assert baseline.baseline_type == "schedule"
    assert baseline.baseline_date == date(2024, 1, 15)
    assert baseline.description == "Initial schedule baseline"
    assert baseline.created_by_id == user.id
    assert hasattr(baseline, "created_by")  # Relationship should exist


def test_baseline_type_enum(db: Session) -> None:
    """Test that baseline_type is validated."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Test valid types
    valid_types = ["schedule", "earned_value", "budget", "forecast", "combined"]
    for baseline_type in valid_types:
        baseline_in = BaselineLogCreate(
            baseline_type=baseline_type,
            baseline_date=date(2024, 1, 15),
            created_by_id=user.id,
        )
        baseline = BaselineLog.model_validate(baseline_in)
        db.add(baseline)
        db.commit()
        db.refresh(baseline)
        assert baseline.baseline_type == baseline_type


def test_baseline_user_relationship(db: Session) -> None:
    """Test that baseline log references user correctly."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    baseline_in = BaselineLogCreate(
        baseline_type="schedule",
        baseline_date=date(2024, 2, 1),
        description="Test baseline",
        created_by_id=user.id,
    )
    baseline = BaselineLog.model_validate(baseline_in)
    db.add(baseline)
    db.commit()
    db.refresh(baseline)

    assert baseline.created_by_id == user.id


def test_baseline_log_public_schema() -> None:
    """Test BaselineLogPublic schema for API responses."""
    import datetime

    baseline_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    baseline_public = BaselineLogPublic(
        baseline_id=baseline_id,
        baseline_type="earned_value",
        baseline_date=date(2024, 3, 1),
        description="Public test baseline",
        created_by_id=user_id,
        created_at=now,
    )

    assert baseline_public.baseline_id == baseline_id
    assert baseline_public.baseline_type == "earned_value"
    assert baseline_public.created_by_id == user_id
    assert baseline_public.created_at == now
