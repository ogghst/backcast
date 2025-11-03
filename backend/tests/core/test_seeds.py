"""Tests for seed functions."""
from unittest.mock import patch

from sqlmodel import Session, delete, select

from app.core.seeds import (
    _seed_cost_element_types,
    _seed_departments,
    _seed_project_from_template,
)
from app.models import (
    WBE,
    CostElement,
    CostElementType,
    Department,
    Project,
)


def test_seed_departments_creates_records(db: Session) -> None:
    """Test that _seed_departments creates departments from JSON file."""
    # Run seed function (will use actual JSON file)
    _seed_departments(db)

    # Verify at least one department from seed file was created
    department = db.exec(
        select(Department).where(Department.department_code == "MECH")
    ).first()

    assert department is not None
    assert department.department_code == "MECH"
    assert department.department_name == "Mechanical Engineering"
    assert department.is_active is True


def test_seed_departments_idempotent(db: Session) -> None:
    """Test that _seed_departments doesn't create duplicates on re-run."""
    # Run seed function first time
    _seed_departments(db)
    count_first = len(db.exec(select(Department)).all())

    # Run seed function second time
    _seed_departments(db)
    count_second = len(db.exec(select(Department)).all())

    assert count_second == count_first, "Should not create duplicate departments"


def test_seed_departments_missing_file(db: Session) -> None:
    """Test that _seed_departments handles missing file gracefully."""
    # Count before (may have departments from other tests)
    count_before = len(db.exec(select(Department)).all())

    # Mock Path so the seed file appears to not exist
    with patch("app.core.seeds.Path") as mock_path:
        # Set up the mock chain: Path(__file__).parent / "departments_seed.json"
        mock_file_path_instance = mock_path.return_value
        mock_parent = mock_file_path_instance.parent
        mock_seed_file = mock_parent.__truediv__.return_value
        mock_seed_file.exists.return_value = False

        # Should not raise exception
        _seed_departments(db)

    # Verify no new departments were created
    count_after = len(db.exec(select(Department)).all())
    assert (
        count_after == count_before
    ), "Should not create departments when file doesn't exist"


def test_seed_order_departments_first(db: Session) -> None:
    """Integration test: departments must be seeded before cost element types."""
    from app.core.db import init_db

    # Clear existing data
    statement = delete(CostElementType)
    db.execute(statement)
    statement = delete(Department)
    db.execute(statement)
    db.commit()

    # Run init_db which should seed departments first
    init_db(db)

    # Verify departments were created
    departments = db.exec(select(Department)).all()
    assert len(departments) > 0, "Departments should be seeded"

    # Verify cost element types were created and can reference departments
    cost_element_types = db.exec(select(CostElementType)).all()
    assert len(cost_element_types) > 0, "Cost element types should be seeded"

    # Verify at least one cost element type has a department reference
    cet_with_dept = next(
        (cet for cet in cost_element_types if cet.department_id is not None), None
    )
    assert cet_with_dept is not None, "Cost element types should reference departments"

    # Refresh to load relationship
    db.refresh(cet_with_dept)
    assert (
        cet_with_dept.department is not None
    ), "Department relationship should be loaded"


def test_seed_cost_element_types_still_works(db: Session) -> None:
    """Regression test: verify cost element types seed function still works after refactor."""
    # Clear existing data
    statement = delete(CostElementType)
    db.execute(statement)
    statement = delete(Department)
    db.execute(statement)
    db.commit()

    # Seed departments first (dependency)
    _seed_departments(db)

    # Seed cost element types
    _seed_cost_element_types(db)

    # Verify cost element types were created
    cost_element_types = db.exec(select(CostElementType)).all()
    assert len(cost_element_types) > 0, "Cost element types should be seeded"

    # Verify they can reference departments
    cet_with_dept = next(
        (cet for cet in cost_element_types if cet.department_id is not None), None
    )
    assert (
        cet_with_dept is not None
    ), "Cost element types should have department references"


def test_seed_cost_element_types_with_hardcoded_uuids(db: Session) -> None:
    """Test that cost element types are created with hardcoded UUIDs from JSON."""
    import json
    from pathlib import Path

    # Clear existing data
    statement = delete(CostElementType)
    db.execute(statement)
    statement = delete(Department)
    db.execute(statement)
    db.commit()

    # Seed departments first (dependency)
    _seed_departments(db)

    # Load JSON to get expected UUIDs
    seed_file = (
        Path(__file__).parent.parent / "app" / "core" / "cost_element_types_seed.json"
    )
    with open(seed_file, encoding="utf-8") as f:
        seed_data = json.load(f)

    # Seed cost element types
    _seed_cost_element_types(db)

    # Verify each cost element type has correct UUID
    for item in seed_data:
        cost_element_type_id_str = item.get("cost_element_type_id")
        type_code = item.get("type_code")

        if cost_element_type_id_str:
            import uuid

            expected_uuid = uuid.UUID(cost_element_type_id_str)

            # Find by UUID
            cet = db.get(CostElementType, expected_uuid)
            assert (
                cet is not None
            ), f"Cost element type {type_code} with UUID {expected_uuid} should exist"
            assert (
                cet.cost_element_type_id == expected_uuid
            ), f"Cost element type {type_code} should have UUID {expected_uuid}"


def test_seed_project_from_template_creates_project(db: Session) -> None:
    """Test that _seed_project_from_template creates project from JSON file."""
    # Ensure prerequisites exist: departments, cost element types, and first superuser
    from app import crud
    from app.core.config import settings
    from app.models import User, UserCreate, UserRole

    # Create first superuser if it doesn't exist
    user = db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            role=UserRole.admin,
        )
        user = crud.create_user(session=db, user_create=user_in)

    _seed_departments(db)
    _seed_cost_element_types(db)

    # Run seed function
    _seed_project_from_template(db)

    # Verify project was created
    project = db.exec(
        select(Project).where(Project.project_code == "PRE_LSI2300157_05_03_ET_01-")
    ).first()

    assert project is not None
    assert project.project_code == "PRE_LSI2300157_05_03_ET_01-"
    assert project.project_name == "PRE_LSI2300157_05_03_ET_01-"
    assert project.project_manager_id == user.id

    # Verify WBEs were created
    wbes = db.exec(select(WBE).where(WBE.project_id == project.project_id)).all()
    assert len(wbes) == 3, "Should create 3 WBEs from template"

    # Verify cost elements were created for first WBE
    cost_elements = db.exec(
        select(CostElement).where(CostElement.wbe_id == wbes[0].wbe_id)
    ).all()
    assert len(cost_elements) == 1, "First WBE should have 1 cost element"


def test_seed_project_from_template_idempotent(db: Session) -> None:
    """Test that _seed_project_from_template updates existing project by project_code."""
    # Ensure prerequisites exist
    from app import crud
    from app.core.config import settings
    from app.models import User, UserCreate, UserRole

    user = db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            role=UserRole.admin,
        )
        user = crud.create_user(session=db, user_create=user_in)

    _seed_departments(db)
    _seed_cost_element_types(db)

    # Run seed function first time
    _seed_project_from_template(db)

    # Count projects, WBEs, and cost elements
    projects_first = db.exec(select(Project)).all()
    wbes_first = db.exec(select(WBE)).all()

    assert len(projects_first) == 1, "Should have 1 project after first seed"
    assert len(wbes_first) == 3, "Should have 3 WBEs after first seed"

    # Run seed function second time (should update, not duplicate)
    _seed_project_from_template(db)

    projects_second = db.exec(select(Project)).all()
    wbes_second = db.exec(select(WBE)).all()

    # Should still have same counts (updated, not duplicated)
    assert len(projects_second) == 1, "Should still have 1 project after second seed"
    assert len(wbes_second) == 3, "Should still have 3 WBEs after second seed"

    # Verify project was updated (check project_name still matches)
    project = db.exec(
        select(Project).where(Project.project_code == "PRE_LSI2300157_05_03_ET_01-")
    ).first()
    assert project is not None
    assert project.project_name == "PRE_LSI2300157_05_03_ET_01-"


def test_seed_project_from_template_missing_file(db: Session) -> None:
    """Test that _seed_project_from_template handles missing file gracefully."""
    # Count before
    count_before = len(db.exec(select(Project)).all())

    # Mock Path so the seed file appears to not exist
    with patch("app.core.seeds.Path") as mock_path:
        # Set up the mock chain: Path(__file__).parent / "project_template_seed.json"
        mock_file_path_instance = mock_path.return_value
        mock_parent = mock_file_path_instance.parent
        mock_seed_file = mock_parent.__truediv__.return_value
        mock_seed_file.exists.return_value = False

        # Should not raise exception
        _seed_project_from_template(db)

    # Verify no new projects were created
    count_after = len(db.exec(select(Project)).all())
    assert (
        count_after == count_before
    ), "Should not create projects when file doesn't exist"


def test_integration_all_seeds_together(db: Session) -> None:
    """Integration test: verify all seeds work together in the correct order."""
    from app.core.db import init_db

    # Clear all data
    statement = delete(CostElement)
    db.execute(statement)
    statement = delete(WBE)
    db.execute(statement)
    statement = delete(Project)
    db.execute(statement)
    statement = delete(CostElementType)
    db.execute(statement)
    statement = delete(Department)
    db.execute(statement)
    db.commit()

    # Run init_db which runs all seeds in order
    init_db(db)

    # Verify departments were created
    departments = db.exec(select(Department)).all()
    assert len(departments) > 0, "Departments should be seeded"

    # Verify cost element types were created
    cost_element_types = db.exec(select(CostElementType)).all()
    assert len(cost_element_types) > 0, "Cost element types should be seeded"

    # Verify project was created
    project = db.exec(
        select(Project).where(Project.project_code == "PRE_LSI2300157_05_03_ET_01-")
    ).first()
    assert project is not None, "Project should be seeded"

    # Verify WBEs were created
    wbes = db.exec(select(WBE).where(WBE.project_id == project.project_id)).all()
    assert len(wbes) == 3, "Should have 3 WBEs"

    # Verify cost elements were created (check total across all WBEs)
    cost_elements = db.exec(select(CostElement)).all()
    assert len(cost_elements) > 0, "Cost elements should be seeded"

    # Verify cost elements reference correct cost element types with hardcoded UUIDs
    for ce in cost_elements:
        assert (
            ce.cost_element_type_id is not None
        ), "Cost element should have cost_element_type_id"
        cet = db.get(CostElementType, ce.cost_element_type_id)
        assert (
            cet is not None
        ), f"Cost element type {ce.cost_element_type_id} should exist"
