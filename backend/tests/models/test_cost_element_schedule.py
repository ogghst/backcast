"""Tests for CostElementSchedule model."""
import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    WBE,
    CostElement,
    CostElementCreate,
    CostElementSchedule,
    CostElementScheduleCreate,
    CostElementSchedulePublic,
    CostElementType,
    CostElementTypeCreate,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)


def test_create_cost_element_schedule(db: Session) -> None:
    """Test creating a cost element schedule."""
    # Create full hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Schedule Test Project",
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

    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Test Machine",
        revenue_allocation=50000.00,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    cet_in = CostElementTypeCreate(
        type_code=f"schedule_test_{uuid.uuid4().hex[:8]}",
        type_name="Test Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=10000.00,
        revenue_plan=12000.00,
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Create cost element schedule
    schedule_in = CostElementScheduleCreate(
        cost_element_id=ce.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
        notes="Baseline schedule for engineering work",
        created_by_id=pm_user.id,
    )

    schedule = CostElementSchedule.model_validate(schedule_in)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # Verify schedule was created
    assert schedule.schedule_id is not None
    assert schedule.cost_element_id == ce.cost_element_id
    assert schedule.start_date == date(2024, 1, 1)
    assert schedule.end_date == date(2024, 12, 31)
    assert schedule.progression_type == "linear"
    assert hasattr(schedule, "cost_element")  # Relationship should exist


def test_progression_type_enum(db: Session) -> None:
    """Test that progression_type is validated."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Progression Type Test",
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

    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine",
        revenue_allocation=50000.00,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    cet_in = CostElementTypeCreate(
        type_code=f"prog_test_{uuid.uuid4().hex[:8]}",
        type_name="Test Type",
        category_type="other",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="TEST",
        department_name="Test Dept",
        budget_bac=5000.00,
        revenue_plan=6000.00,
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Test valid progression types
    valid_types = ["linear", "gaussian", "logarithmic"]
    for progression_type in valid_types:
        # Create a new cost element for each progression type to avoid unique constraint
        ce_new_in = CostElementCreate(
            wbe_id=wbe.wbe_id,
            cost_element_type_id=cet.cost_element_type_id,
            department_code=f"TEST_{progression_type}",
            department_name=f"Test Dept {progression_type}",
            budget_bac=5000.00,
            revenue_plan=6000.00,
            status="active",
        )
        ce_new = CostElement.model_validate(ce_new_in)
        db.add(ce_new)
        db.commit()
        db.refresh(ce_new)

        schedule_in = CostElementScheduleCreate(
            cost_element_id=ce_new.cost_element_id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            progression_type=progression_type,
            created_by_id=pm_user.id,
        )
        schedule = CostElementSchedule.model_validate(schedule_in)
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        assert schedule.progression_type == progression_type


def test_cost_element_schedule_public_schema() -> None:
    """Test CostElementSchedulePublic schema for API responses."""
    import datetime

    schedule_id = uuid.uuid4()
    ce_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    schedule_public = CostElementSchedulePublic(
        schedule_id=schedule_id,
        cost_element_id=ce_id,
        start_date=date(2024, 2, 1),
        end_date=date(2024, 11, 30),
        progression_type="gaussian",
        notes="Public test schedule",
        created_by_id=user_id,
        created_at=now,
        updated_at=now,
    )

    assert schedule_public.schedule_id == schedule_id
    assert schedule_public.start_date == date(2024, 2, 1)
    assert schedule_public.end_date == date(2024, 11, 30)
    assert schedule_public.progression_type == "gaussian"
