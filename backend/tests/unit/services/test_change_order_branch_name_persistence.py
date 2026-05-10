"""Test branch_name persistence on change order creation and submission.

This test verifies Task BE-004: Ensure branch_name is set on CO submission.

The issue was that branch_name was being set in co_data but not persisted
to the database after change order creation.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.models.domain.project import Project
from app.models.domain.user import User
from app.models.schemas.change_order import ChangeOrderCreate
from app.services.change_order_service import ChangeOrderService


@pytest.fixture
def admin_user() -> User:
    return User(
        id=uuid4(),
        user_id=uuid4(),
        email="admin@example.com",
        is_active=True,
        role="admin",
        full_name="Admin User",
        hashed_password="hash",
        created_by=uuid4(),
    )


@pytest.mark.asyncio
async def test_branch_name_persisted_on_co_creation(
    db_session: AsyncSession, admin_user: User
):
    """Verify that branch_name is persisted when a change order is created.

    This is the core issue from BE-004: branch_name was being set in the
    data dictionary but not being persisted to the database.
    """

    # 1. Setup: Create Project
    project = Project(
        name="Test Project Branch Name",
        code=f"PRJ-BRANCH-{uuid4().hex[:6]}",
        description="Test Description",
        created_by=admin_user.user_id,
        project_id=uuid4(),
    )
    db_session.add(project)
    await db_session.commit()

    service = ChangeOrderService(db_session)
    actor_id = admin_user.user_id

    # 2. Create Change Order
    code = f"CO-BRANCH-{uuid4().hex[:6]}"
    expected_branch_name = f"BR-{code}"

    co_create = ChangeOrderCreate(
        code=code,
        project_id=project.project_id,
        title="Test CO Title",
        description="Test CO Description",
        control_date=datetime.now(UTC),
    )

    co = await service.create_change_order(co_create, actor_id=actor_id)

    # 3. Verify branch_name is set in memory
    assert co is not None, "Change order should be created"
    assert co.branch_name is not None, "branch_name should be set in memory"
    assert co.branch_name == expected_branch_name, (
        f"branch_name should be {expected_branch_name}, got {co.branch_name}"
    )

    # 4. Verify branch_name is persisted in database
    # Query the database directly to ensure it's not just in-memory
    stmt = text(
        "SELECT branch_name FROM change_orders WHERE change_order_id = :coid"
    )
    result = await db_session.execute(stmt, {"coid": str(co.change_order_id)})
    row = result.fetchone()

    assert row is not None, "Change order should be persisted"
    assert row[0] is not None, "branch_name should be persisted to database"
    assert row[0] == expected_branch_name, (
        f"Persisted branch_name should be {expected_branch_name}, got {row[0]}"
    )


@pytest.mark.asyncio
async def test_branch_name_persisted_after_update(
    db_session: AsyncSession, admin_user: User
):
    """Verify that branch_name is persisted when a change order is updated.

    This test verifies that branch_name remains set after CO updates.
    """

    # 1. Setup: Create Project
    project = Project(
        name="Test Project Update",
        code=f"PRJ-UPD-{uuid4().hex[:6]}",
        description="Test Description",
        created_by=admin_user.user_id,
        project_id=uuid4(),
    )
    db_session.add(project)
    await db_session.commit()

    service = ChangeOrderService(db_session)
    actor_id = admin_user.user_id

    # 2. Create Change Order
    code = f"CO-UPD-{uuid4().hex[:6]}"
    expected_branch_name = f"BR-{code}"

    co_create = ChangeOrderCreate(
        code=code,
        project_id=project.project_id,
        title="Original Title",
        description="Original Description",
        control_date=datetime.now(UTC),
    )

    co = await service.create_change_order(co_create, actor_id=actor_id)

    # 3. Verify branch_name is set after creation
    assert co.branch_name == expected_branch_name, (
        f"branch_name should be {expected_branch_name} after creation"
    )

    # 4. Update the change order
    from app.models.schemas.change_order import ChangeOrderUpdate

    co_update = ChangeOrderUpdate(
        title="Updated Title",
        description="Updated Description",
    )

    updated_co = await service.update_change_order(
        change_order_id=co.change_order_id,
        change_order_in=co_update,
        actor_id=actor_id,
    )

    # 5. Verify branch_name is still set after update
    assert updated_co.branch_name is not None, (
        "branch_name should be set after update"
    )
    assert updated_co.branch_name == expected_branch_name, (
        f"branch_name should still be {expected_branch_name} after update, "
        f"got {updated_co.branch_name}"
    )

    # 6. Verify branch_name is persisted in database after update
    stmt = text(
        "SELECT branch_name FROM change_orders WHERE change_order_id = :coid AND branch = 'main'"
    )
    result = await db_session.execute(stmt, {"coid": str(updated_co.change_order_id)})
    row = result.fetchone()

    assert row is not None, "Change order should be persisted after update"
    assert row[0] is not None, "branch_name should be persisted to database after update"
    assert row[0] == expected_branch_name, (
        f"Persisted branch_name after update should be {expected_branch_name}, got {row[0]}"
    )
