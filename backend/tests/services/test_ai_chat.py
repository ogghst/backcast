"""Tests for AI chat service."""

import uuid
from datetime import date

from sqlmodel import Session

from app.services.ai_chat import collect_context_metrics


def test_collect_context_metrics_project(db: Session) -> None:
    """Test collecting metrics for project context."""
    # Create a test project with WBEs and cost elements
    from app import crud
    from app.models import Project, ProjectCreate, UserCreate

    # Create user
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Create project
    project_in = ProjectCreate(
        project_name="Test Project",
        customer_name="Test Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    control_date = date(2024, 6, 15)
    metrics = collect_context_metrics(
        session=db,
        context_type="project",
        context_id=project.project_id,
        control_date=control_date,
    )

    # Verify metrics structure for project
    assert isinstance(metrics, dict)
    assert "context_type" in metrics
    assert metrics["context_type"] == "project"
    assert "project_id" in metrics
    assert metrics["project_id"] == str(project.project_id)
    assert "control_date" in metrics
    # EVM metrics should be present
    assert "planned_value" in metrics or "evm_metrics" in metrics


def test_collect_context_metrics_wbe(db: Session) -> None:
    """Test collecting metrics for WBE context."""
    from app import crud
    from app.models import WBE, Project, ProjectCreate, UserCreate, WBECreate

    # Create user and project
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Test Project",
        customer_name="Test Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create WBE
    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Test Machine",
        serial_number="TM-001",
        contracted_delivery_date=date(2024, 6, 30),
        revenue_allocation=50000.00,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    control_date = date(2024, 6, 15)
    metrics = collect_context_metrics(
        session=db,
        context_type="wbe",
        context_id=wbe.wbe_id,
        control_date=control_date,
    )

    # Verify metrics structure for WBE
    assert isinstance(metrics, dict)
    assert "context_type" in metrics
    assert metrics["context_type"] == "wbe"
    assert "wbe_id" in metrics
    assert metrics["wbe_id"] == str(wbe.wbe_id)


def test_collect_context_metrics_cost_element(db: Session) -> None:
    """Test collecting metrics for cost element context."""
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

    # Create user, project, WBE, and cost element
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Test Project",
        customer_name="Test Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    wbe_in = WBECreate(
        project_id=project.project_id,
        machine_type="Test Machine",
        serial_number="TM-001",
        contracted_delivery_date=date(2024, 6, 30),
        revenue_allocation=50000.00,
        status="designing",
    )
    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)

    # Create cost element type

    cet_in = CostElementTypeCreate(
        type_code="test_eng",
        type_name="Test Engineering",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)

    cost_element_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering Department",
        budget_bac=10000.00,
        revenue_plan=12000.00,
        status="active",
    )
    cost_element = CostElement.model_validate(cost_element_in)
    db.add(cost_element)
    db.commit()
    db.refresh(cost_element)

    control_date = date(2024, 6, 15)
    metrics = collect_context_metrics(
        session=db,
        context_type="cost-element",
        context_id=cost_element.cost_element_id,
        control_date=control_date,
    )

    # Verify metrics structure for cost element
    assert isinstance(metrics, dict)
    assert "context_type" in metrics
    assert metrics["context_type"] == "cost-element"
    assert "cost_element_id" in metrics
    assert metrics["cost_element_id"] == str(cost_element.cost_element_id)


def test_collect_context_metrics_baseline(db: Session) -> None:
    """Test collecting metrics for baseline context."""
    from app import crud
    from app.models import (
        BaselineLog,
        BaselineLogCreate,
        Project,
        ProjectCreate,
        UserCreate,
    )

    # Create user and project
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Test Project",
        customer_name="Test Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create baseline
    baseline_in = BaselineLogCreate(
        project_id=project.project_id,
        created_by_id=user.id,
        baseline_type="combined",
        baseline_date=date(2024, 3, 1),
        milestone_type="kickoff",
        description="Project kickoff baseline",
        is_pmb=True,
    )
    baseline = BaselineLog.model_validate(baseline_in)
    db.add(baseline)
    db.commit()
    db.refresh(baseline)

    control_date = date(2024, 6, 15)
    metrics = collect_context_metrics(
        session=db,
        context_type="baseline",
        context_id=baseline.baseline_id,
        control_date=control_date,
    )

    # Verify metrics structure for baseline
    assert isinstance(metrics, dict)
    assert "context_type" in metrics
    assert metrics["context_type"] == "baseline"
    assert "baseline_id" in metrics
    assert metrics["baseline_id"] == str(baseline.baseline_id)


def test_collect_context_metrics_invalid_context_type_raises_error(db: Session) -> None:
    """Test that invalid context type raises ValueError."""
    from app import crud
    from app.models import Project, ProjectCreate, UserCreate

    # Create user and project
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name="Test Project",
        customer_name="Test Customer",
        contract_value=100000.00,
        start_date=date(2024, 1, 1),
        planned_completion_date=date(2024, 12, 31),
        project_manager_id=user.id,
        status="active",
    )
    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)

    import pytest

    control_date = date(2024, 6, 15)
    with pytest.raises(ValueError, match="Invalid context_type"):
        collect_context_metrics(
            session=db,
            context_type="invalid_type",
            context_id=project.project_id,
            control_date=control_date,
        )


def test_collect_context_metrics_nonexistent_context_raises_error(db: Session) -> None:
    """Test that nonexistent context ID raises ValueError."""
    import pytest

    control_date = date(2024, 6, 15)
    fake_id = uuid.uuid4()

    with pytest.raises(ValueError, match="not found"):
        collect_context_metrics(
            session=db,
            context_type="project",
            context_id=fake_id,
            control_date=control_date,
        )
