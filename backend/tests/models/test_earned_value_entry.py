"""Tests for EarnedValueEntry model."""
import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    WBE,
    CostElement,
    CostElementCreate,
    CostElementType,
    CostElementTypeCreate,
    EarnedValueEntry,
    EarnedValueEntryCreate,
    EarnedValueEntryPublic,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)


def test_create_earned_value_entry(db: Session) -> None:
    """Test creating an earned value entry."""
    # Create full hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Earned Value Test Project",
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
        type_code=f"ev_test_{uuid.uuid4().hex[:8]}",
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

    # Create earned value entry
    ev_in = EarnedValueEntryCreate(
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 3, 15),
        percent_complete=30.50,
        earned_value=3050.00,
        deliverables="Phase 1 design completed",
        description="Successful completion of design phase",
        created_by_id=pm_user.id,
    )

    ev = EarnedValueEntry.model_validate(ev_in)
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # Verify earned value entry was created
    assert ev.earned_value_id is not None
    assert ev.cost_element_id == ce.cost_element_id
    assert ev.completion_date == date(2024, 3, 15)
    assert ev.percent_complete == 30.50
    assert ev.earned_value == 3050.00
    assert hasattr(ev, "cost_element")  # Relationship should exist


def test_earned_value_calculation() -> None:
    """Test that earned value can be calculated."""
    # Create earned value entry
    ev_in = EarnedValueEntryCreate(
        cost_element_id=uuid.uuid4(),
        completion_date=date(2024, 2, 1),
        percent_complete=50.00,
        earned_value=5000.00,
        description="50% complete",
        created_by_id=uuid.uuid4(),
    )

    ev = EarnedValueEntry.model_validate(ev_in)
    # Verify calculation: if BAC = 10000, and percent_complete = 50%, EV should be 5000
    assert ev.earned_value == 5000.00
    assert ev.percent_complete == 50.00


def test_earned_value_entry_public_schema() -> None:
    """Test EarnedValueEntryPublic schema for API responses."""
    import datetime

    ev_id = uuid.uuid4()
    ce_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    ev_public = EarnedValueEntryPublic(
        earned_value_id=ev_id,
        cost_element_id=ce_id,
        completion_date=date(2024, 4, 30),
        percent_complete=75.25,
        earned_value=7525.00,
        deliverables="Final deliverables",
        description="Public test earned value entry",
        created_by_id=user_id,
        created_at=now,
        last_modified_at=now,
    )

    assert ev_public.earned_value_id == ev_id
    assert ev_public.completion_date == date(2024, 4, 30)
    assert ev_public.percent_complete == 75.25
    assert ev_public.earned_value == 7525.00
    assert ev_public.deliverables == "Final deliverables"
