"""Fixtures for Cost Registration testing.

Provides cost element fixtures with budget allocations for testing budget validation.
"""

from decimal import Decimal
from uuid import uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.department import Department
from app.models.domain.wbe import WBE


@pytest_asyncio.fixture
async def sample_department(db_session: AsyncSession) -> Department:
    """Create a sample department for testing."""
    department = Department(
        department_id=uuid4(),
        code="ENG",
        name="Engineering",
        description="Engineering Department",
        created_by=uuid4(),
    )
    db_session.add(department)
    await db_session.flush()
    return department


@pytest_asyncio.fixture
async def sample_cost_element_type(sample_department: Department) -> CostElementType:
    """Create a sample cost element type for testing."""
    cost_element_type = CostElementType(
        cost_element_type_id=uuid4(),
        department_id=sample_department.department_id,
        code="LABOR",
        name="Labor Hours",
        description="Labor cost tracking",
        created_by=uuid4(),
    )
    return cost_element_type


@pytest_asyncio.fixture
async def sample_wbe(db_session: AsyncSession) -> WBE:
    """Create a sample WBE for testing."""
    wbe = WBE(
        wbe_id=uuid4(),
        project_id=uuid4(),
        code="1.1",
        name="Site Preparation",
        description="Initial site preparation work",
        created_by=uuid4(),
    )
    db_session.add(wbe)
    await db_session.flush()
    return wbe


@pytest_asyncio.fixture
async def sample_cost_element_with_budget(
    db_session: AsyncSession,
    sample_wbe: WBE,
    sample_cost_element_type: CostElementType,
) -> CostElement:
    """Create a sample cost element with budget for testing.

    Returns a CostElement with budget_amount=1000.00.
    """
    cost_element = CostElement(
        cost_element_id=uuid4(),
        wbe_id=sample_wbe.wbe_id,
        cost_element_type_id=sample_cost_element_type.cost_element_type_id,
        code="TEST-001",
        name="Test Cost Element",
        budget_amount=Decimal("1000.00"),
        description="Test cost element with budget",
        created_by=uuid4(),
    )
    db_session.add(cost_element)
    await db_session.flush()
    return cost_element
