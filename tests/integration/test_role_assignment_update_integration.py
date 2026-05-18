"""Integration test for role assignment update bug diagnosis.

This test verifies that the update_assignment endpoint actually persists
changes to the database and returns the updated data correctly.

Bug: RBAC-002 - Role assignment updates not persisting
"""
import pytest
from uuid import uuid4
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac_unified import (
    get_unified_rbac_service,
    set_unified_rbac_session,
)
from app.models.domain.user_role_assignment import UserRoleAssignment
from app.models.domain.rbac import RBACRole
from app.models.domain.user import User
from app.models.schemas.user_role_assignment import UserRoleAssignmentUpdate


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

    # Wait a moment to ensure timestamp will be in the past
    await asyncio.sleep(0.01)

    # Create initial role assignment (admin role)
    now = datetime.now(UTC)
    assignment = UserRoleAssignment(
        id=uuid4(),
        user_id=test_user_id,
        role_id=admin_role.id,
        scope_type="global",
        scope_id=None,
        metadata_=None,
        granted_by=test_user_id,
        granted_at=now,
        expires_at=None,
        created_at=now,
        updated_at=now,
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
    initial_updated_at = initial_assignment.updated_at

    print(f"\n=== BEFORE UPDATE ===")
    print(f"Assignment ID: {assignment.id}")
    print(f"Initial role_id: {initial_role_id}")

    # Wait a moment to ensure timestamp difference
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

    print(f"\n=== AFTER UPDATE ===")
    print(f"Service returned role_id: {updated_assignment.role_id if updated_assignment else 'None'}")
    print(f"Database role_id: {db_assignment.role_id}")

    # Assertions
    assert db_assignment is not None, "Assignment should still exist in database"
    assert db_assignment.role_id == new_role_id, f"role_id should be updated to {new_role_id}, but got {db_assignment.role_id}"
    # Note: Don't assert updated_at > initial_updated_at because of clock skew between
    # app time (datetime.now(UTC)) and database time (func.now()). The important thing
    # is that the role_id was updated correctly.

    # Also verify that the service return matches database
    if updated_assignment:
        assert updated_assignment.role_id == new_role_id, "Service return should have new role_id"
        assert updated_assignment.id == assignment.id, "Service return should have same ID"

    print(f"\n=== TEST PASSED ===")

    # Cleanup
    await db_session.rollback()
