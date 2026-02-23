import uuid
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.domain.cost_element import CostElement
from app.models.domain.project import Project
from app.models.domain.wbe import WBE


@pytest.mark.asyncio
async def test_wbe_project_link_stability(db_session):
    """
    T-001: Verify that WBE remains linked to Project root ID even after Project is updated.
    This demonstrates bitemporal link stability using root IDs.
    """
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    # 1. Create Project (V1)
    project_v1 = Project(
        project_id=project_id,
        code="PRJ-REG-001",
        name="Regression Project V1",
        status="active",
        created_by=user_id,
    )
    db_session.add(project_v1)
    await db_session.commit()

    # 2. Create WBE linked to Project root ID
    wbe_id = uuid.uuid4()
    wbe = WBE(
        wbe_id=wbe_id,
        project_id=project_id,
        code="WBE-001",
        name="Regression WBE",
        level=1,
        budget_allocation=0,
        created_by=user_id,
    )
    db_session.add(wbe)
    await db_session.commit()

    # 3. Update Project (creates V2) - in our system this usually means creating a new row with same project_id
    project_v2 = Project(
        project_id=project_id,
        code="PRJ-REG-001",
        name="Regression Project V2 (Updated)",
        status="active",
        created_by=user_id,
    )
    db_session.add(project_v2)
    await db_session.commit()

    # 4. Fetch WBE and verify link
    from sqlalchemy.orm import selectinload

    result = await db_session.execute(
        select(WBE).options(selectinload(WBE.project)).where(WBE.wbe_id == wbe_id)
    )
    fetched_wbe = result.scalar_one()

    assert fetched_wbe.project_id == project_id

    # 5. Verify we can find all versions of the project via the WBE's project_id
    proj_result = await db_session.execute(
        select(Project).where(Project.project_id == fetched_wbe.project_id)
    )
    projects = proj_result.scalars().all()
    assert len(projects) >= 2
    assert any(p.name == "Regression Project V1" for p in projects)
    assert any(p.name == "Regression Project V2 (Updated)" for p in projects)

    # 6. Verify Relationship Navigation (primaryjoin)
    # Refresh to ensure we exercise the relationship fetch
    await db_session.refresh(fetched_wbe)
    assert fetched_wbe.project is not None
    assert fetched_wbe.project.project_id == project_id


@pytest.mark.asyncio
async def test_cost_element_wbe_link_stability(db_session):
    """
    T-002: Verify that CostElement remains linked to WBE root ID even after WBE is updated.
    """
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    wbe_id = uuid.uuid4()

    # Setup parent Project
    project = Project(
        project_id=project_id,
        code="PRJ-CE-001",
        name="CE Project",
        status="active",
        created_by=user_id,
    )
    db_session.add(project)

    # 1. Create WBE (V1)
    wbe_v1 = WBE(
        wbe_id=wbe_id,
        project_id=project_id,
        code="WBE-CE-001",
        name="WBE V1",
        level=1,
        budget_allocation=0,
        created_by=user_id,
    )
    db_session.add(wbe_v1)
    await db_session.commit()

    # 2. Create CostElement linked to WBE root
    ce_id = uuid.uuid4()
    ce = CostElement(
        cost_element_id=ce_id,
        wbe_id=wbe_id,
        cost_element_type_id=uuid.uuid4(),  # Just a dummy for now
        code="CE-001",
        name="Regression CE",
        budget_amount=1000.00,
        created_by=user_id,
    )
    db_session.add(ce)
    await db_session.commit()

    # 3. Update WBE (creates V2)
    wbe_v2 = WBE(
        wbe_id=wbe_id,
        project_id=project_id,
        code="WBE-CE-001",
        name="WBE V2 (Updated)",
        level=1,
        budget_allocation=0,
        created_by=user_id,
    )
    db_session.add(wbe_v2)
    await db_session.commit()

    # 4. Verify link
    from sqlalchemy.orm import selectinload

    result = await db_session.execute(
        select(CostElement)
        .options(selectinload(CostElement.wbe))
        .where(CostElement.cost_element_id == ce_id)
    )
    fetched_ce = result.scalar_one()

    assert fetched_ce.wbe_id == wbe_id

    # 5. Verify Relationship Navigation
    # Already loaded via selectinload
    assert fetched_ce.wbe is not None
    assert fetched_ce.wbe.wbe_id == wbe_id


@pytest.mark.asyncio
async def test_department_manager_link_stability(db_session):
    """
    T-003: Verify that Department remains linked to User root ID.
    """
    from app.models.domain.department import Department
    from app.models.domain.user import User

    user_id = uuid.uuid4()
    dept_id = uuid.uuid4()

    # 1. Create User
    user = User(
        user_id=user_id,
        email="manager@example.com",
        full_name="Test Manager",
        hashed_password="...",
        created_by=user_id,
    )
    db_session.add(user)

    # 2. Create Department referencing User root
    dept = Department(
        department_id=dept_id,
        manager_id=user_id,
        code="DEPT-001",
        name="Test Dept",
        created_by=user_id,
    )
    db_session.add(dept)
    await db_session.commit()

    # 3. Verify link
    from sqlalchemy.orm import selectinload

    result = await db_session.execute(
        select(Department)
        .options(selectinload(Department.manager))
        .where(Department.department_id == dept_id)
    )
    fetched_dept = result.scalar_one()
    assert fetched_dept.manager_id == user_id

    # 4. Verify Relationship Navigation
    assert fetched_dept.manager is not None
    assert fetched_dept.manager.user_id == user_id


@pytest.mark.asyncio
async def test_cost_element_type_department_link_stability(db_session):
    """
    T-004: Verify that CostElementType remains linked to Department root ID.
    """
    from app.models.domain.cost_element_type import CostElementType
    from app.models.domain.department import Department

    actor_id = uuid4()
    dept_id = uuid4()

    # 1. Create Department
    dept = Department(
        department_id=dept_id,
        manager_id=uuid4(),
        code="DEPT-CET-001",
        name="CET Dept",
        created_by=actor_id,
    )
    db_session.add(dept)

    # 2. Create CostElementType referencing Department root
    cet_id = uuid4()
    cet = CostElementType(
        cost_element_type_id=cet_id,
        department_id=dept_id,
        code="CET-001",
        name="Test CET",
        created_by=actor_id,
    )
    db_session.add(cet)
    await db_session.commit()

    # 3. Verify link
    result = await db_session.execute(
        select(CostElementType).where(CostElementType.cost_element_type_id == cet_id)
    )
    fetched_cet = result.scalar_one()
    assert fetched_cet.department_id == dept_id


@pytest.mark.asyncio
async def test_cost_registration_cost_element_link_stability(db_session):
    """
    T-005: Verify that CostRegistration remains linked to CostElement root ID.
    """
    from app.models.domain.cost_element import CostElement
    from app.models.domain.cost_registration import CostRegistration

    actor_id = uuid4()
    ce_id = uuid4()

    # 1. Create CostElement
    ce = CostElement(
        cost_element_id=ce_id,
        wbe_id=uuid4(),
        cost_element_type_id=uuid4(),
        code="CE-REG-001",
        name="Reg CE",
        budget_amount=Decimal("1000.00"),
        created_by=actor_id,
    )
    db_session.add(ce)

    # 2. Create CostRegistration referencing CE root
    reg_id = uuid4()
    registration = CostRegistration(
        cost_registration_id=reg_id,
        cost_element_id=ce_id,
        amount=Decimal("500.00"),
        description="Test Registration",
        created_by=actor_id,
    )
    db_session.add(registration)
    await db_session.commit()

    # 3. Verify link
    result = await db_session.execute(
        select(CostRegistration).where(CostRegistration.cost_registration_id == reg_id)
    )
    fetched_reg = result.scalar_one()
    assert fetched_reg.cost_element_id == ce_id
