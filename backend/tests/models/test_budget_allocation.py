"""Tests for BudgetAllocation model."""
import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    WBE,
    BudgetAllocation,
    BudgetAllocationCreate,
    BudgetAllocationPublic,
    CostElement,
    CostElementCreate,
    CostElementType,
    CostElementTypeCreate,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)


def test_create_budget_allocation(db: Session) -> None:
    """Test creating a budget allocation."""
    # Create full hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Budget Test Project",
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

    # Create budget allocation
    budget_in = BudgetAllocationCreate(
        cost_element_id=ce.cost_element_id,
        allocation_date=date(2024, 1, 1),
        budget_amount=10000.00,
        revenue_amount=12000.00,
        allocation_type="initial",
        description="Initial budget allocation",
        created_by_id=pm_user.id,
    )

    budget = BudgetAllocation.model_validate(budget_in)
    db.add(budget)
    db.commit()
    db.refresh(budget)

    # Verify budget allocation was created
    assert budget.budget_allocation_id is not None
    assert budget.budget_amount == 10000.00
    assert budget.revenue_amount == 12000.00
    assert budget.allocation_type == "initial"
    assert budget.cost_element_id == ce.cost_element_id
    assert budget.created_by_id == pm_user.id
    assert hasattr(budget, "cost_element")  # Relationship should exist


def test_allocation_type_enum(db: Session) -> None:
    """Test that allocation_type is validated."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Allocation Type Test",
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
        type_code=f"test_type_{uuid.uuid4().hex[:8]}",
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

    # Test valid allocation types
    valid_types = ["initial", "change_order", "adjustment"]
    for allocation_type in valid_types:
        budget_in = BudgetAllocationCreate(
            cost_element_id=ce.cost_element_id,
            allocation_date=date(2024, 1, 1),
            budget_amount=1000.00,
            allocation_type=allocation_type,
            created_by_id=pm_user.id,
        )
        budget = BudgetAllocation.model_validate(budget_in)
        db.add(budget)
        db.commit()
        db.refresh(budget)
        assert budget.allocation_type == allocation_type


def test_budget_cost_element_relationship(db: Session) -> None:
    """Test that budget allocation references cost element correctly."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Relationship Test",
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
        type_code=f"rel_test_{uuid.uuid4().hex[:8]}",
        type_name="Relationship Test",
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
        department_code="REL",
        department_name="Relationship",
        budget_bac=5000.00,
        revenue_plan=6000.00,
        status="active",
    )
    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)

    budget_in = BudgetAllocationCreate(
        cost_element_id=ce.cost_element_id,
        allocation_date=date(2024, 1, 1),
        budget_amount=5000.00,
        allocation_type="initial",
        created_by_id=pm_user.id,
    )
    budget = BudgetAllocation.model_validate(budget_in)
    db.add(budget)
    db.commit()
    db.refresh(budget)

    assert budget.cost_element_id == ce.cost_element_id


def test_budget_allocation_public_schema() -> None:
    """Test BudgetAllocationPublic schema for API responses."""
    import datetime

    budget_id = uuid.uuid4()
    ce_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    budget_public = BudgetAllocationPublic(
        budget_allocation_id=budget_id,
        cost_element_id=ce_id,
        allocation_date=date(2024, 1, 15),
        budget_amount=15000.00,
        revenue_amount=18000.00,
        allocation_type="initial",
        description="Public test allocation",
        created_by_id=user_id,
        created_at=now,
    )

    assert budget_public.budget_allocation_id == budget_id
    assert budget_public.budget_amount == 15000.00
    assert budget_public.revenue_amount == 18000.00
    assert budget_public.created_at == now
