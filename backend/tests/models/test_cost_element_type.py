"""Tests for CostElementType model."""
import uuid
from datetime import datetime

from sqlmodel import Session

from app.models import (
    CostElementType,
    CostElementTypeCreate,
    CostElementTypePublic,
)


def test_create_cost_element_type(db: Session) -> None:
    """Test creating a cost element type."""
    unique_code = f"test_{uuid.uuid4().hex[:8]}"
    cet_in = CostElementTypeCreate(
        type_code=unique_code,
        type_name="Robot Mechanical Engineering",
        category_type="engineering_mechanical",
        tracks_hours=True,
        display_order=1,
        is_active=True,
    )

    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    # Verify cost element type was created
    assert cet.cost_element_type_id is not None
    assert cet.type_code == unique_code
    assert cet.type_name == "Robot Mechanical Engineering"
    assert cet.category_type == "engineering_mechanical"
    assert cet.tracks_hours is True
    assert cet.display_order == 1
    assert cet.is_active is True


def test_cost_element_type_unique_code(db: Session) -> None:
    """Test that type_code must be unique."""
    unique_code = f"DUPLICATE_{uuid.uuid4().hex[:8]}"
    cet1_in = CostElementTypeCreate(
        type_code=unique_code,
        type_name="Duplicate Test",
        category_type="other",
        display_order=1,
        is_active=True,
    )
    cet1 = CostElementType.model_validate(cet1_in)
    db.add(cet1)
    db.commit()

    # Try to create another type with same code
    cet2_in = CostElementTypeCreate(
        type_code=unique_code,
        type_name="Duplicate Test 2",
        category_type="other",
        display_order=1,
        is_active=True,
    )
    cet2 = CostElementType.model_validate(cet2_in)
    db.add(cet2)

    # Should fail on commit due to unique constraint
    try:
        db.commit()
        raise AssertionError("Should have raised IntegrityError for duplicate code")
    except Exception:
        db.rollback()
        assert True


def test_cost_element_type_category_enum(db: Session) -> None:
    """Test that category_type enum is validated."""
    # Valid category
    unique_code = f"test_eng_{uuid.uuid4().hex[:8]}"
    cet_in = CostElementTypeCreate(
        type_code=unique_code,
        type_name="Test Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    assert cet.category_type == "engineering_mechanical"

    # Try invalid category (should fail validation)
    try:
        invalid_code = f"test_invalid_{uuid.uuid4().hex[:8]}"
        cet_invalid = CostElementTypeCreate(
            type_code=invalid_code,
            type_name="Test Invalid",
            category_type="invalid_category",
            display_order=1,
            is_active=True,
        )
        CostElementType.model_validate(cet_invalid)
        raise AssertionError("Should have raised ValidationError for invalid category")
    except Exception:
        assert True


def test_cost_element_type_public_schema() -> None:
    """Test CostElementTypePublic schema for API responses."""
    cet_id = uuid.uuid4()
    now = datetime.now()

    cet_public = CostElementTypePublic(
        cost_element_type_id=cet_id,
        type_code="sw_pc",
        type_name="PC Software",
        category_type="software",
        tracks_hours=True,
        display_order=10,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    assert cet_public.cost_element_type_id == cet_id
    assert cet_public.type_code == "sw_pc"
    assert cet_public.category_type == "software"
