from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.project import Project
from app.models.domain.user import User
from app.models.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate
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
async def test_change_order_update_consistency_fix(
    db_session: AsyncSession, admin_user: User
):
    """Verify that updating a change order immediately does not create empty valid_time versions."""

    # 1. Setup: Create Project
    project = Project(
        name="Test Project Consistency",
        code=f"PRJ-CONSIST-{uuid4().hex[:6]}",
        description="Test Description",
        created_by=admin_user.user_id,
        project_id=uuid4(),
    )
    db_session.add(project)
    await db_session.commit()

    service = ChangeOrderService(db_session)
    actor_id = admin_user.user_id

    # 2. Create Change Order
    co_create = ChangeOrderCreate(
        code=f"CO-CONSIST-{uuid4().hex[:6]}",
        project_id=project.project_id,
        title="Original Title",
        description="Original Description",
        control_date=datetime.now(UTC),  # Explict control date
    )

    co = await service.create_change_order(
        co_create, actor_id=actor_id
    )
    assert co is not None
    assert co.title == "Original Title"

    # Safe ID extraction
    co_id = co.change_order_id

    # 3. Update Change Order immediately (using same control_date or slightly after)
    # If we use the SAME control date (simulating fast batch update), it should trigger the fix.
    update_control_date = co_create.control_date

    co_update = ChangeOrderUpdate(
        title="Updated Title Consistency", control_date=update_control_date
    )

    updated_co = await service.update_change_order(
        change_order_id=co_id,
        change_order_in=co_update,
        actor_id=actor_id,
    )

    assert updated_co.title == "Updated Title Consistency"

    # 4. Verification: Check Database for 'empty' valid_time ranges
    # We expect 2 versions in transaction history:
    # 1. The initial creation (now closed/superseded at transaction time) - wait,
    # actually, since we updated at the exact same valid_time, the first version
    # effectively "never existed" in valid_time from the perspective of the final state?
    # No, Bitemporal logic:
    # V1: valid=[T1, inf), trans=[T_create, T_update)
    # V2: valid=[T1, inf), trans=[T_update, inf)

    # The erroneous behavior was creating a remainder:
    # Remainder: valid=[T1, T1), trans=[T_update, inf) <-- EMPTY RANGE

    stmt = text(
        "SELECT id, valid_time FROM change_orders WHERE change_order_id = :coid"
    )
    result = await db_session.execute(stmt, {"coid": co_id})
    rows = result.fetchall()

    for row in rows:
        # Check if valid_time is explicitly 'empty' (Postgres representation)
        valid_time_str = str(row.valid_time)
        assert valid_time_str != "empty", (
            f"Found version with empty valid_time: {row.id}"
        )

        # Also check manually if lower == upper and not empty (though postgres normalizes [x,x) to empty)
        if not row.valid_time.isempty:
            assert row.valid_time.lower != row.valid_time.upper, (
                f"Found version with zero duration: {row.id}"
            )


@pytest.mark.asyncio
async def test_change_order_active_versions(db_session: AsyncSession, admin_user: User):
    """Ensure we can retrieve the active version correctly after update."""
    # Setup
    project = Project(
        name="Test Project Active",
        code=f"PRJ-ACT-{uuid4().hex[:6]}",
        created_by=admin_user.user_id,
        project_id=uuid4(),
    )
    db_session.add(project)
    await db_session.commit()

    service = ChangeOrderService(db_session)
    actor_id = admin_user.user_id

    # Create
    co = await service.create_change_order(
        ChangeOrderCreate(
            code=f"CO-ACT-{uuid4().hex[:4]}", project_id=project.project_id, title="V1"
        ),
        actor_id=actor_id,
    )

    co_id = co.change_order_id

    # Update
    await service.update_change_order(
        co_id, ChangeOrderUpdate(title="V2"), actor_id=actor_id
    )

    # Active Fetch
    current = await service.get_current(co_id)
    assert current is not None
    assert current.title == "V2"

    # List Fetch
    results, total = await service.get_change_orders(project_id=project.project_id)
    assert total == 1
    assert results[0].title == "V2"


@pytest.mark.asyncio
async def test_change_order_crud_lifecycle(db_session: AsyncSession, admin_user: User):
    """Comprehensive CRUD lifecycle test."""

    # 1. Create Project
    project = Project(
        name="CRUD PROJ",
        code=f"PRJ-CRUD-{uuid4().hex[:6]}",
        created_by=admin_user.user_id,
        project_id=uuid4(),
    )
    db_session.add(project)
    await db_session.commit()

    service = ChangeOrderService(db_session)
    actor_id = admin_user.user_id

    # 2. CREATE
    co_in = ChangeOrderCreate(
        code="CO-CRUD-001",
        project_id=project.project_id,
        title="CRUD Title",
        description="Desc",
    )
    co = await service.create_change_order(co_in, actor_id=actor_id)

    assert co.title == "CRUD Title"
    assert co.status == "Draft"
    assert co.branch_name == "BR-CO-CRUD-001"

    co_id = co.change_order_id

    # 3. READ (Get by Code)
    fetched = await service.get_current_by_code("CO-CRUD-001")
    assert fetched is not None
    assert fetched.change_order_id == co_id

    # 4. UPDATE
    # Use valid transition "Submitted for Approval"
    update_in = ChangeOrderUpdate(
        description="Updated Desc", status="Submitted for Approval"
    )
    updated = await service.update_change_order(co_id, update_in, actor_id=actor_id)

    assert updated.description == "Updated Desc"
    assert updated.status == "Submitted for Approval"

    # 5. DELETE (Soft Delete)
    deleted = await service.delete_change_order(co_id, actor_id=actor_id)
    assert deleted.deleted_at is not None

    # 6. Verify Deletion
    # Should not be found via normal get_current
    missing = await service.get_current(co_id)
    assert missing is None

    # Should not be in list
    lst, _ = await service.get_change_orders(project_id=project.project_id)
    assert len(lst) == 0

    # But should be in history/time-travel (before delete)
    # Using specific timestamp would require careful time management in test,
    # but we can check direct DB access or generic history if available.
    # The service has get_history (inherited from BranchableService? No, explicitly implemented? inherited)
    # Let's check inheritance.
