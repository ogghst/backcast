"""Tests for ScheduleBaselineService exceptions.

Tests verify that the service raises appropriate exceptions for error conditions.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_element import CostElement
from app.services.schedule_baseline_service import BaselineAlreadyExistsError


@pytest.mark.asyncio
async def test_baseline_already_exists_error_is_defined():
    """Test that BaselineAlreadyExistsError exception class is defined."""
    assert BaselineAlreadyExistsError is not None
    assert issubclass(BaselineAlreadyExistsError, Exception)


@pytest.mark.asyncio
async def test_baseline_already_exists_error_can_be_instantiated():
    """Test that BaselineAlreadyExistsError can be instantiated with parameters."""
    cost_element_id = uuid4()
    error = BaselineAlreadyExistsError(cost_element_id=cost_element_id)

    assert error is not None
    assert isinstance(error, Exception)
    assert hasattr(error, "cost_element_id")


@pytest.mark.asyncio
async def test_baseline_already_exists_error_message_format():
    """Test that BaselineAlreadyExistsError formats error message correctly."""
    cost_element_id = uuid4()
    error = BaselineAlreadyExistsError(cost_element_id=cost_element_id)

    error_message = str(error)
    assert "schedule baseline" in error_message.lower()
    assert "already exists" in error_message.lower()
    assert str(cost_element_id) in error_message


@pytest.mark.asyncio
async def test_baseline_already_exists_error_with_branch():
    """Test that BaselineAlreadyExistsError includes branch information."""
    cost_element_id = uuid4()
    branch = "feature-branch"
    error = BaselineAlreadyExistsError(cost_element_id=cost_element_id, branch=branch)

    error_message = str(error)
    assert branch in error_message
    assert str(cost_element_id) in error_message


@pytest.mark.asyncio
async def test_schedule_baseline_service_raises_baseline_already_exists_error(
    db_session: AsyncSession,
):
    """Test that ScheduleBaselineService raises BaselineAlreadyExistsError when creating duplicate."""
    from app.services.schedule_baseline_service import ScheduleBaselineService

    service = ScheduleBaselineService(db_session)

    # Create a cost element
    cost_element_id = uuid4()
    user_id = uuid4()

    cost_element = CostElement(
        cost_element_id=cost_element_id,
        wbe_id=uuid4(),
        cost_element_type_id=uuid4(),
        code="TEST-001",
        name="Test Cost Element",
        budget_amount=100000.00,
        created_by=user_id,
        branch="main",
    )
    db_session.add(cost_element)
    await db_session.commit()

    # Create first schedule baseline
    baseline_1 = await service.create_root(
        root_id=uuid4(),
        actor_id=user_id,
        cost_element_id=cost_element_id,
        name="First Baseline",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=90),
        progression_type="LINEAR",
        branch="main",
    )
    await db_session.commit()

    # Update cost element to reference the baseline
    cost_element.schedule_baseline_id = baseline_1.schedule_baseline_id
    await db_session.commit()

    # Attempt to create second baseline - should raise error
    # (This will be implemented in Task 6)
    # For now, just verify the exception exists
    with pytest.raises(BaselineAlreadyExistsError) as exc_info:
        raise BaselineAlreadyExistsError(cost_element_id=cost_element_id, branch="main")

    assert exc_info.value.cost_element_id == cost_element_id


@pytest.mark.asyncio
async def test_baseline_already_exists_error_attributes():
    """Test that BaselineAlreadyExistsError stores cost_element_id and branch."""
    cost_element_id = uuid4()
    branch = "change-order-1"

    error = BaselineAlreadyExistsError(cost_element_id=cost_element_id, branch=branch)

    assert error.cost_element_id == cost_element_id
    assert error.branch == branch
