"""Tests for CostRegistration model."""
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
    CostRegistration,
    CostRegistrationCreate,
    CostRegistrationPublic,
    Project,
    ProjectCreate,
    UserCreate,
    WBECreate,
)


def test_create_cost_registration(db: Session) -> None:
    """Test creating a cost registration."""
    # Create full hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Cost Registration Test Project",
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
        type_code=f"test_cr_{uuid.uuid4().hex[:8]}",
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

    # Create cost registration
    cost_in = CostRegistrationCreate(
        cost_element_id=ce.cost_element_id,
        registration_date=date(2024, 2, 15),
        amount=1500.00,
        cost_category="labor",
        description="8 hours of engineering work",
        is_quality_cost=False,
        created_by_id=pm_user.id,
    )

    cost = CostRegistration.model_validate(cost_in)
    db.add(cost)
    db.commit()
    db.refresh(cost)

    # Verify cost registration was created
    assert cost.cost_registration_id is not None
    assert cost.amount == 1500.00
    assert cost.cost_category == "labor"
    assert cost.is_quality_cost is False
    assert cost.cost_element_id == ce.cost_element_id
    assert cost.created_by_id == pm_user.id
    assert hasattr(cost, "cost_element")  # Relationship should exist


def test_cost_category_enum(db: Session) -> None:
    """Test that cost_category is validated."""
    # Create hierarchy
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Cost Category Test",
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
        type_code=f"cat_test_{uuid.uuid4().hex[:8]}",
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

    # Test valid cost categories
    valid_categories = ["labor", "materials", "subcontracts", "other"]
    for cost_category in valid_categories:
        cost_in = CostRegistrationCreate(
            cost_element_id=ce.cost_element_id,
            registration_date=date(2024, 2, 1),
            amount=100.00,
            cost_category=cost_category,
            description="Test cost",
            is_quality_cost=False,
            created_by_id=pm_user.id,
        )
        cost = CostRegistration.model_validate(cost_in)
        db.add(cost)
        db.commit()
        db.refresh(cost)
        assert cost.cost_category == cost_category


def test_cost_registration_public_schema() -> None:
    """Test CostRegistrationPublic schema for API responses."""
    import datetime

    cost_id = uuid.uuid4()
    ce_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    cost_public = CostRegistrationPublic(
        cost_registration_id=cost_id,
        cost_element_id=ce_id,
        registration_date=date(2024, 3, 15),
        amount=2500.00,
        cost_category="materials",
        invoice_number="INV-12345",
        description="Public test cost registration",
        is_quality_cost=False,
        created_by_id=user_id,
        created_at=now,
        last_modified_at=now,
    )

    assert cost_public.cost_registration_id == cost_id
    assert cost_public.amount == 2500.00
    assert cost_public.cost_category == "materials"
    assert cost_public.invoice_number == "INV-12345"
