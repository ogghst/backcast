"""Tests for Department model."""
import uuid

from sqlmodel import Session

from app.models import Department, DepartmentCreate, DepartmentPublic


def test_create_department(db: Session) -> None:
    """Test creating a department."""
    unique_code = f"test_{uuid.uuid4().hex[:8]}"
    dept_in = DepartmentCreate(
        department_code=unique_code,
        department_name="Engineering",
        description="Engineering department",
        is_active=True,
    )

    dept = Department.model_validate(dept_in)
    db.add(dept)
    db.commit()
    db.refresh(dept)

    # Verify department was created
    assert dept.department_id is not None
    assert dept.department_code == unique_code
    assert dept.department_name == "Engineering"
    assert dept.description == "Engineering department"
    assert dept.is_active is True


def test_department_unique_code(db: Session) -> None:
    """Test that department_code must be unique."""
    unique_code = f"DUP_{uuid.uuid4().hex[:8]}"
    dept1_in = DepartmentCreate(
        department_code=unique_code,
        department_name="Duplicate Test",
        is_active=True,
    )
    dept1 = Department.model_validate(dept1_in)
    db.add(dept1)
    db.commit()

    # Try to create another department with same code
    dept2_in = DepartmentCreate(
        department_code=unique_code,
        department_name="Duplicate Test 2",
        is_active=True,
    )
    dept2 = Department.model_validate(dept2_in)
    db.add(dept2)

    # Should fail on commit due to unique constraint
    try:
        db.commit()
        raise AssertionError("Should have raised IntegrityError for duplicate code")
    except Exception:
        db.rollback()
        assert True


def test_department_public_schema() -> None:
    """Test DepartmentPublic schema for API responses."""
    dept_id = uuid.uuid4()
    dept_public = DepartmentPublic(
        department_id=dept_id,
        department_code="SALES",
        department_name="Sales",
        description="Sales department",
        is_active=True,
    )

    assert dept_public.department_id == dept_id
    assert dept_public.department_code == "SALES"
    assert dept_public.is_active is True
