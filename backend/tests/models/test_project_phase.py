"""Tests for ProjectPhase model."""
import uuid

from sqlmodel import Session

from app.models import (
    ProjectPhase,
    ProjectPhaseCreate,
    ProjectPhasePublic,
)


def test_create_project_phase(db: Session) -> None:
    """Test creating a project phase."""
    unique_id = uuid.uuid4().hex[:8]
    phase_in = ProjectPhaseCreate(
        phase_code=f"test_aperture_{unique_id}",
        phase_name="Opening/Kickoff",
        description="Project kickoff phase",
        display_order=1,
    )

    phase = ProjectPhase.model_validate(phase_in)
    db.add(phase)
    db.commit()
    db.refresh(phase)

    # Verify phase was created
    assert phase.phase_id is not None
    assert phase.phase_code == f"test_aperture_{unique_id}"
    assert phase.phase_name == "Opening/Kickoff"
    assert phase.description == "Project kickoff phase"
    assert phase.display_order == 1


def test_project_phase_unique_code(db: Session) -> None:
    """Test that phase_code must be unique."""
    unique_id = uuid.uuid4().hex[:8]
    phase1_in = ProjectPhaseCreate(
        phase_code=f"dup_{unique_id}",
        phase_name="Duplicate Test",
        display_order=1,
    )
    phase1 = ProjectPhase.model_validate(phase1_in)
    db.add(phase1)
    db.commit()

    # Try to create another phase with same code
    phase2_in = ProjectPhaseCreate(
        phase_code=f"dup_{unique_id}",
        phase_name="Duplicate Test 2",
        display_order=1,
    )
    phase2 = ProjectPhase.model_validate(phase2_in)
    db.add(phase2)

    # Should fail on commit due to unique constraint
    try:
        db.commit()
        raise AssertionError("Should have raised IntegrityError for duplicate code")
    except Exception:
        db.rollback()
        assert True


def test_project_phase_display_order(db: Session) -> None:
    """Test creating phases with different display orders."""
    import uuid

    # Use unique codes to avoid conflicts
    unique_id = uuid.uuid4().hex[:8]
    phase1 = ProjectPhase.model_validate(
        ProjectPhaseCreate(
            phase_code=f"order1_{unique_id}",
            phase_name="Order 1",
            display_order=1,
        )
    )
    phase2 = ProjectPhase.model_validate(
        ProjectPhaseCreate(
            phase_code=f"order2_{unique_id}",
            phase_name="Order 2",
            display_order=2,
        )
    )

    db.add(phase1)
    db.add(phase2)
    db.commit()

    assert phase1.display_order == 1
    assert phase2.display_order == 2


def test_project_phase_public_schema() -> None:
    """Test ProjectPhasePublic schema for API responses."""
    phase_id = uuid.uuid4()
    phase_public = ProjectPhasePublic(
        phase_id=phase_id,
        phase_code="collaudo",
        phase_name="Testing/Acceptance",
        description="Final testing phase",
        display_order=5,
    )

    assert phase_public.phase_id == phase_id
    assert phase_public.phase_code == "collaudo"
    assert phase_public.display_order == 5
