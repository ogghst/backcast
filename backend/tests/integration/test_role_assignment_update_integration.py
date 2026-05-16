"""Integration test for role assignment update bug diagnosis."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac_unified import (
    get_unified_rbac_service,
    set_unified_rbac_session,
)
from app.models.domain.rbac import RBACRole
from app.models.domain.user import User
from app.models.domain.user_role_assignment import UserRoleAssignment


@pytest.mark.asyncio
async def test_role_assignment_update_integration(db_session: AsyncSession):
    """Test that role assignment update actually persists to database."""

    # Create test user
    test_user_id = uuid4()
    test_user = User(
        user_id=test_user_id,
        email=f"test-{test_user_id.hex[:8]}@backcast.org",
        full_name="Integration Test User",
        hashed_password="hashed",
        is_active=True,
        department="TEST",
        created_by=test_user_id,
    )
    db_session.add(test_user)
    await db_session.flush()

    # Create test roles
    admin_role = RBACRole(
        id=uuid4(),
        name="test_admin",
        description="Test admin role",
        is_system=False,
    )
    manager_role = RBACRole(
        id=uuid4(),
        name="test_manager",
        description="Test manager role",
        is_system=False,
    )
    db_session.add_all([admin_role, manager_role])
    await db_session.flush()

    # Create initial role assignment (admin role)
    assignment = UserRoleAssignment(
        id=uuid4(),
        user_id=test_user_id,
        role_id=admin_role.id,
        scope_type="global",
        scope_id=None,
        metadata_=None,
        granted_by=test_user_id,
        granted_at=datetime.now(UTC),
        expires_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(assignment)
    await db_session.commit()

    # Get the role_id we want to update to
    new_role_id = manager_role.id

    # Verify initial state
    result = await db_session.execute(
        select(UserRoleAssignment).where(UserRoleAssignment.id == assignment.id)
    )
    initial_assignment = result.scalar_one()
    initial_role_id = initial_assignment.role_id

    print("\n=== BEFORE UPDATE ===")
    print(f"Assignment ID: {assignment.id}")
    print(f"Initial role_id: {initial_role_id}")

    # Wait to ensure timestamp difference
    import asyncio

    await asyncio.sleep(0.1)

    # Perform the update using the service directly
    set_unified_rbac_session(db_session)
    service = get_unified_rbac_service()

    updated_assignment = await service.update_assignment(
        assignment_id=assignment.id,
        role_id=new_role_id,
    )

    await db_session.commit()

    # Verify the assignment was actually updated in the database
    result_after = await db_session.execute(
        select(UserRoleAssignment).where(UserRoleAssignment.id == assignment.id)
    )
    db_assignment = result_after.scalar_one()

    print("\n=== AFTER UPDATE ===")
    print(
        f"Service returned role_id: {updated_assignment.role_id if updated_assignment else 'None'}"
    )
    print(f"Database role_id: {db_assignment.role_id}")

    # Assertions
    assert db_assignment is not None, "Assignment should still exist"
    assert db_assignment.role_id == new_role_id, (
        f"role_id should be updated to {new_role_id}"
    )
    # Note: Don't assert updated_at > initial_updated_at because of clock skew between
    # app time (datetime.now(UTC)) and database time (func.now()). The important thing
    # is that the role_id was updated correctly.

    print("\n=== TEST PASSED ===")

    # Cleanup
    await db_session.rollback()
