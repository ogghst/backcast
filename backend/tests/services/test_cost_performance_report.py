"""Tests for Cost Performance Report service."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlmodel import Session

from app import crud
from app.models import (
    WBE,
    CostElement,
    CostElementCreate,
    CostElementType,
    CostElementTypeCreate,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)
from app.services.cost_performance_report import get_cost_performance_report


def test_get_cost_performance_report_empty_project(db: Session) -> None:
    """Test report for project with no cost elements."""
    # Create project
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    user_in = UserCreate(email=email, password="testpassword123")
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Empty Project",
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

    control_date = date(2024, 6, 15)
    report = get_cost_performance_report(db, project.project_id, control_date)

    assert report.project_id == project.project_id
    assert report.project_name == "Empty Project"
    assert report.control_date == control_date
    assert len(report.rows) == 0
    assert report.summary.planned_value == Decimal("0.00")
    assert report.summary.earned_value == Decimal("0.00")
    assert report.summary.actual_cost == Decimal("0.00")
    assert report.summary.budget_bac == Decimal("0.00")
    assert report.summary.cpi is None
    assert report.summary.spi is None


def test_get_cost_performance_report_single_cost_element(db: Session) -> None:
    """Test report for project with single cost element."""
    # Create project hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    user_in = UserCreate(email=email, password="testpassword123")
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Single CE Project",
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
        serial_number="SN-001",
        revenue_allocation=50000.00,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Create cost element type
    cet_in = CostElementTypeCreate(
        type_code=f"test_eng_{uuid.uuid4().hex[:8]}",
        type_name="Test Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    # Create cost element
    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering Department",
        budget_bac=Decimal("10000.00"),
        revenue_plan=Decimal("12000.00"),
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Create schedule
    from tests.utils.cost_element_schedule import create_schedule_for_cost_element

    create_schedule_for_cost_element(
        db,
        ce.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
    )

    # Create cost registration
    from tests.utils.cost_registration import create_random_cost_registration

    cr = create_random_cost_registration(
        db,
        cost_element_id=ce.cost_element_id,
        registration_date=date(2024, 6, 15),
        created_by_id=pm_user.id,
    )
    # Update amount and description
    cr.amount = Decimal("5000.00")
    cr.cost_category = "labor"
    cr.description = "Test cost"
    db.add(cr)
    db.commit()
    db.refresh(cr)

    # Create earned value entry
    from tests.utils.earned_value_entry import create_earned_value_entry

    create_earned_value_entry(
        db,
        cost_element_id=ce.cost_element_id,
        completion_date=date(2024, 6, 15),
        percent_complete=Decimal("50.00"),  # 50% completion
        description="50% complete",
        created_by_id=pm_user.id,
    )

    # Use a control date in the future to include all created items
    control_date = date(2025, 12, 31)  # Future date to include all items
    report = get_cost_performance_report(db, project.project_id, control_date)

    assert report.project_id == project.project_id
    assert len(report.rows) == 1
    row = report.rows[0]
    assert row.cost_element_id == ce.cost_element_id
    assert row.wbe_id == wbe.wbe_id
    assert row.wbe_name == "Test Machine"
    assert row.wbe_serial_number == "SN-001"
    assert row.department_code == "ENG"
    assert row.department_name == "Engineering Department"
    assert row.cost_element_type_name == "Test Engineering"
    assert row.budget_bac == Decimal("10000.00")
    assert row.actual_cost == Decimal("5000.00")
    assert row.earned_value == Decimal("5000.00")  # 50% of BAC
    assert report.summary.budget_bac == Decimal("10000.00")
    assert report.summary.actual_cost == Decimal("5000.00")
    assert report.summary.earned_value == Decimal("5000.00")


def test_get_cost_performance_report_multiple_cost_elements(db: Session) -> None:
    """Test report for project with multiple cost elements across multiple WBEs."""
    # Create project hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    user_in = UserCreate(email=email, password="testpassword123")
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Multi CE Project",
        customer_name="Test Customer",
        contract_value=200000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=pm_user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create two WBEs
    wbe1_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine A",
        serial_number="SN-A-001",
        revenue_allocation=100000.00,
        status="designing",
    )
    wbe1 = WBE.model_validate(wbe1_in)
    db.add(wbe1)
    db.commit()
    db.refresh(wbe1)

    wbe2_in = WBECreate(
        project_id=project.project_id,
        machine_type="Machine B",
        serial_number="SN-B-001",
        revenue_allocation=100000.00,
        status="designing",
    )
    wbe2 = WBE.model_validate(wbe2_in)
    db.add(wbe2)
    db.commit()
    db.refresh(wbe2)

    # Create cost element type
    cet_in = CostElementTypeCreate(
        type_code=f"test_eng_{uuid.uuid4().hex[:8]}",
        type_name="Test Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    # Create cost elements
    ce1_in = CostElementCreate(
        wbe_id=wbe1.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("10000.00"),
        revenue_plan=Decimal("12000.00"),
        status="active",
    )
    ce1 = CostElement.model_validate(ce1_in)
    db.add(ce1)
    db.commit()
    db.refresh(ce1)

    ce2_in = CostElementCreate(
        wbe_id=wbe2.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="MKT",
        department_name="Marketing",
        budget_bac=Decimal("20000.00"),
        revenue_plan=Decimal("15000.00"),
        status="active",
    )
    ce2 = CostElement.model_validate(ce2_in)
    db.add(ce2)
    db.commit()
    db.refresh(ce2)

    # Create schedules
    from tests.utils.cost_element_schedule import create_schedule_for_cost_element

    create_schedule_for_cost_element(
        db,
        ce1.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
    )

    create_schedule_for_cost_element(
        db,
        ce2.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 1),
    )

    # Create cost registrations
    from tests.utils.cost_registration import create_random_cost_registration
    from tests.utils.earned_value_entry import create_earned_value_entry

    cr1 = create_random_cost_registration(
        db,
        cost_element_id=ce1.cost_element_id,
        registration_date=date(2024, 6, 15),
        created_by_id=pm_user.id,
    )
    cr1.amount = Decimal("5000.00")
    cr1.cost_category = "labor"
    cr1.description = "CE1 cost"
    db.add(cr1)
    db.commit()
    db.refresh(cr1)

    cr2 = create_random_cost_registration(
        db,
        cost_element_id=ce2.cost_element_id,
        registration_date=date(2024, 6, 15),
        created_by_id=pm_user.id,
    )
    cr2.amount = Decimal("10000.00")
    cr2.cost_category = "labor"
    cr2.description = "CE2 cost"
    db.add(cr2)
    db.commit()
    db.refresh(cr2)

    # Create earned value entries
    create_earned_value_entry(
        db,
        cost_element_id=ce1.cost_element_id,
        completion_date=date(2024, 6, 15),
        percent_complete=Decimal("50.00"),  # 50% as percentage
        description="CE1 50%",
        created_by_id=pm_user.id,
    )

    create_earned_value_entry(
        db,
        cost_element_id=ce2.cost_element_id,
        completion_date=date(2024, 6, 15),
        percent_complete=Decimal("75.00"),  # 75% as percentage
        description="CE2 75%",
        created_by_id=pm_user.id,
    )

    # Use a control date in the future to include all created items
    control_date = date(2025, 12, 31)  # Future date to include all items
    report = get_cost_performance_report(db, project.project_id, control_date)

    assert report.project_id == project.project_id
    assert len(report.rows) == 2

    # Check rows are sorted/grouped correctly
    row_ce_ids = {row.cost_element_id for row in report.rows}
    assert ce1.cost_element_id in row_ce_ids
    assert ce2.cost_element_id in row_ce_ids

    # Check summary aggregation
    assert report.summary.budget_bac == Decimal("30000.00")  # 10000 + 20000
    assert report.summary.actual_cost == Decimal("15000.00")  # 5000 + 10000
    assert report.summary.earned_value == Decimal(
        "20000.00"
    )  # 5000 + 15000 (50% of 10000 + 75% of 20000)


def test_get_cost_performance_report_nonexistent_project(db: Session) -> None:
    """Test that service raises ValueError for non-existent project."""
    fake_project_id = uuid.uuid4()
    control_date = date(2024, 6, 15)

    with pytest.raises(ValueError, match="not found"):
        get_cost_performance_report(db, fake_project_id, control_date)


def test_get_cost_performance_report_time_machine_filtering(db: Session) -> None:
    """Test that report respects time-machine control date filtering."""
    # Create project
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    user_in = UserCreate(email=email, password="testpassword123")
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Time Machine Project",
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

    # Create cost element type
    cet_in = CostElementTypeCreate(
        type_code=f"test_eng_{uuid.uuid4().hex[:8]}",
        type_name="Test Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    # Create cost element
    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=Decimal("10000.00"),
        revenue_plan=Decimal("12000.00"),
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    # Use a control date in the future to include all created items
    control_date = date(2025, 12, 31)  # Future date to include all items
    report = get_cost_performance_report(db, project.project_id, control_date)

    # Cost element should be included (created_at <= control_date)
    assert len(report.rows) == 1
