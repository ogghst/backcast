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
    BudgetAllocation,
    CostElement,
    CostElementSchedule,
    CostElementType,
    CostRegistration,
    Department,
    EarnedValueEntry,
    Forecast,
    Project,
    QualityEvent,
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

    # Clear existing data in correct dependency order
    # Delete records that reference CostElement first
    statement = delete(EarnedValueEntry)
    db.execute(statement)
    statement = delete(Forecast)
    db.execute(statement)
    statement = delete(QualityEvent)
    db.execute(statement)
    statement = delete(BudgetAllocation)
    db.execute(statement)
    statement = delete(CostRegistration)
    db.execute(statement)
    statement = delete(CostElementSchedule)
    db.execute(statement)
    # Delete CostElement (references CostElementType)
    statement = delete(CostElement)
    db.execute(statement)
    # Now safe to delete CostElementType
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
    # Clear existing data in correct dependency order
    # Delete records that reference CostElement first
    statement = delete(EarnedValueEntry)
    db.execute(statement)
    statement = delete(Forecast)
    db.execute(statement)
    statement = delete(QualityEvent)
    db.execute(statement)
    statement = delete(BudgetAllocation)
    db.execute(statement)
    statement = delete(CostRegistration)
    db.execute(statement)
    statement = delete(CostElementSchedule)
    db.execute(statement)
    # Delete CostElement (references CostElementType)
    statement = delete(CostElement)
    db.execute(statement)
    # Now safe to delete CostElementType
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

    # Clear existing data in correct dependency order
    # Delete records that reference CostElement first
    statement = delete(EarnedValueEntry)
    db.execute(statement)
    statement = delete(Forecast)
    db.execute(statement)
    statement = delete(QualityEvent)
    db.execute(statement)
    statement = delete(BudgetAllocation)
    db.execute(statement)
    statement = delete(CostRegistration)
    db.execute(statement)
    statement = delete(CostElementSchedule)
    db.execute(statement)
    # Delete CostElement (references CostElementType)
    statement = delete(CostElement)
    db.execute(statement)
    # Now safe to delete CostElementType
    statement = delete(CostElementType)
    db.execute(statement)
    statement = delete(Department)
    db.execute(statement)
    db.commit()

    # Seed departments first (dependency)
    _seed_departments(db)

    # Load JSON to get expected UUIDs
    seed_file = (
        Path(__file__).parent.parent.parent
        / "app"
        / "core"
        / "cost_element_types_seed.json"
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

    # Get the seeded project by project_code
    seeded_project = db.exec(
        select(Project).where(Project.project_code == "PRE_LSI2300157_05_03_ET_01-")
    ).first()
    assert seeded_project is not None, "Seeded project should exist"

    # Count WBEs for this specific project
    wbes_first = db.exec(
        select(WBE).where(WBE.project_id == seeded_project.project_id)
    ).all()

    assert len(wbes_first) == 3, "Should have 3 WBEs after first seed"

    # Run seed function second time (should update, not duplicate)
    _seed_project_from_template(db)

    # Verify project still exists and wasn't duplicated
    seeded_project_second = db.exec(
        select(Project).where(Project.project_code == "PRE_LSI2300157_05_03_ET_01-")
    ).first()
    assert (
        seeded_project_second is not None
    ), "Seeded project should still exist after second seed"
    assert (
        seeded_project_second.project_id == seeded_project.project_id
    ), "Should be the same project (updated, not duplicated)"

    wbes_second = db.exec(
        select(WBE).where(WBE.project_id == seeded_project.project_id)
    ).all()

    # Should still have same counts (updated, not duplicated)
    assert len(wbes_second) == 3, "Should still have 3 WBEs after second seed"

    # Verify project was updated (check project_name still matches)
    assert (
        seeded_project_second.project_name == "PRE_LSI2300157_05_03_ET_01-"
    ), "Project name should match seed data"


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

    # Clear all data in correct dependency order
    # Delete records that reference CostElement first
    statement = delete(EarnedValueEntry)
    db.execute(statement)
    statement = delete(Forecast)
    db.execute(statement)
    statement = delete(QualityEvent)
    db.execute(statement)
    statement = delete(BudgetAllocation)
    db.execute(statement)
    statement = delete(CostRegistration)
    db.execute(statement)
    statement = delete(CostElementSchedule)
    db.execute(statement)
    # Delete CostElement (references CostElementType and WBE)
    statement = delete(CostElement)
    db.execute(statement)
    # Delete WBE (references Project)
    statement = delete(WBE)
    db.execute(statement)
    # Delete Project
    statement = delete(Project)
    db.execute(statement)
    # Now safe to delete CostElementType
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


def test_seed_project_from_template_creates_budget_allocations_and_schedules(
    db: Session,
) -> None:
    """Test that _seed_project_from_template creates budget allocations and schedules for cost elements."""
    from app import crud
    from app.core.config import settings
    from app.models import User, UserCreate, UserRole

    # Ensure prerequisites exist
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

    # Get project
    project = db.exec(
        select(Project).where(Project.project_code == "PRE_LSI2300157_05_03_ET_01-")
    ).first()
    assert project is not None

    # Get all cost elements for this project
    wbes = db.exec(select(WBE).where(WBE.project_id == project.project_id)).all()
    cost_elements = []
    for wbe in wbes:
        ces = db.exec(select(CostElement).where(CostElement.wbe_id == wbe.wbe_id)).all()
        cost_elements.extend(ces)

    assert len(cost_elements) > 0, "Should have cost elements to test"

    # Verify each cost element has a budget allocation
    for ce in cost_elements:
        budget_allocations = db.exec(
            select(BudgetAllocation).where(
                BudgetAllocation.cost_element_id == ce.cost_element_id
            )
        ).all()
        assert (
            len(budget_allocations) > 0
        ), f"Cost element {ce.cost_element_id} should have at least one budget allocation"

        # Verify budget allocation matches cost element budget_bac and revenue_plan
        initial_budget = next(
            (ba for ba in budget_allocations if ba.allocation_type == "initial"),
            None,
        )
        assert (
            initial_budget is not None
        ), f"Cost element {ce.cost_element_id} should have initial budget allocation"
        assert (
            initial_budget.budget_amount == ce.budget_bac
        ), "Budget allocation amount should match cost element budget_bac"
        assert (
            initial_budget.revenue_amount == ce.revenue_plan
        ), "Budget allocation revenue should match cost element revenue_plan"
        assert (
            initial_budget.allocation_date == project.start_date
        ), "Budget allocation date should match project start date"
        assert (
            initial_budget.created_by_id == user.id
        ), "Budget allocation should be created by first superuser"

    # Load template data to verify schedules match JSON
    import json
    from pathlib import Path

    # Path from tests/core/ to backend/app/core/
    seed_file = (
        Path(__file__).parent.parent.parent
        / "app"
        / "core"
        / "project_template_seed.json"
    )
    with open(seed_file, encoding="utf-8") as f:
        template_data = json.load(f)

    # Build list of expected schedules in order (matching JSON structure)
    expected_schedules_list = []
    for wbe_item in template_data.get("wbes", []):
        wbe_machine_type = wbe_item.get("wbe", {}).get("machine_type")
        for ce_data in wbe_item.get("cost_elements", []):
            expected_schedules_list.append(
                {
                    "wbe_machine_type": wbe_machine_type,
                    "department_code": ce_data.get("department_code"),
                    "cost_element_type_id": ce_data.get("cost_element_type_id"),
                    "budget_bac": ce_data.get("budget_bac"),
                    "schedule": ce_data.get("schedule"),
                }
            )

    # Verify each cost element has a schedule and matches JSON
    # Match cost elements to expected schedules by matching wbe + department + type + budget
    for ce in cost_elements:
        schedules = db.exec(
            select(CostElementSchedule).where(
                CostElementSchedule.cost_element_id == ce.cost_element_id
            )
        ).all()
        assert (
            len(schedules) == 1
        ), f"Cost element {ce.cost_element_id} should have exactly one schedule"

        schedule = schedules[0]

        # Find matching expected schedule from JSON
        # Get the WBE for this cost element
        ce_wbe = db.get(WBE, ce.wbe_id)
        expected_schedule_data = None
        for exp_data in expected_schedules_list:
            if (
                exp_data["department_code"] == ce.department_code
                and exp_data["cost_element_type_id"] == str(ce.cost_element_type_id)
                and float(exp_data["budget_bac"]) == float(ce.budget_bac)
                and ce_wbe.machine_type == exp_data["wbe_machine_type"]
            ):
                expected_schedule_data = exp_data.get("schedule")
                break

        if expected_schedule_data:
            # Verify schedule matches JSON data
            from datetime import date

            expected_start = date.fromisoformat(expected_schedule_data["start_date"])
            expected_end = date.fromisoformat(expected_schedule_data["end_date"])
            assert (
                schedule.start_date == expected_start
            ), f"Schedule start date should match JSON data for {ce.department_code} (expected {expected_start}, got {schedule.start_date})"
            assert (
                schedule.end_date == expected_end
            ), f"Schedule end date should match JSON data for {ce.department_code} (expected {expected_end}, got {schedule.end_date})"
            assert (
                schedule.progression_type == expected_schedule_data["progression_type"]
            ), f"Schedule progression type should match JSON data for {ce.department_code} (expected {expected_schedule_data['progression_type']}, got {schedule.progression_type})"
            if expected_schedule_data.get("notes"):
                assert (
                    schedule.notes == expected_schedule_data["notes"]
                ), f"Schedule notes should match JSON data for {ce.department_code}"
        else:
            # Fallback: if no schedule in JSON, should use project dates (backward compatibility)
            assert (
                schedule.start_date == project.start_date
            ), "Schedule start date should match project start date when not in JSON"
            assert (
                schedule.end_date == project.planned_completion_date
            ), "Schedule end date should match project planned completion date when not in JSON"
            assert (
                schedule.progression_type == "linear"
            ), "Schedule progression type should be linear by default"

        assert (
            schedule.created_by_id == user.id
        ), "Schedule should be created by first superuser"
