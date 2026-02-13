"""
Comprehensive CRUD lifecycle test for versioned entities.
Tests Create, Read, Update, Delete operations and verifies version consistency.
"""

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.models.schemas.user import UserRegister, UserUpdate
from app.services.user import UserService


@pytest.mark.asyncio
async def test_crud_lifecycle_complete(db_session):
    """Test full CRUD lifecycle ensuring version consistency."""
    service = UserService(db_session)
    actor_id = uuid4()

    print("\n=== CRUD Lifecycle Test ===")

    # ==================== CREATE ====================
    print("\n1. CREATE Operation")
    user_in = UserRegister(
        email=f"crud_{uuid4()}@test.com",
        full_name="Test User Original",
        password="password123",
        role="viewer",
        department="Engineering",
    )

    created_user = await service.create_user(user_in, actor_id)
    root_id = created_user.user_id
    version_1_id = created_user.id

    await db_session.commit()
    print(f"   Created User - Root ID: {root_id}, Version ID: {version_1_id}")

    # Verify: 1 total version, 1 active version
    result = await db_session.execute(
        text("SELECT count(*) FROM users WHERE user_id = :uid"), {"uid": root_id}
    )
    assert result.scalar() == 1, "Should have 1 total version after create"

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM users WHERE user_id = :uid AND upper(valid_time) IS NULL"
        ),
        {"uid": root_id},
    )
    assert result.scalar() == 1, "Should have 1 active version after create"

    # ==================== READ ====================
    print("\n2. READ Operation")
    users = await service.get_users()
    target_users = [u for u in users if u.user_id == root_id]

    assert len(target_users) == 1, (
        f"get_users() should return 1 user, got {len(target_users)}"
    )
    assert target_users[0].full_name == "Test User Original"
    assert target_users[0].id == version_1_id
    print(f"   Read User - Found 1 active version: {target_users[0].full_name}")

    # ==================== UPDATE ====================
    print("\n3. UPDATE Operation")
    update_in = UserUpdate(full_name="Test User Updated")
    updated_user = await service.update_user(root_id, update_in, actor_id)
    version_2_id = updated_user.id

    await db_session.commit()
    print(f"   Updated User - New Version ID: {version_2_id}")

    # Verify: 2 total versions, 1 active version
    result = await db_session.execute(
        text("SELECT count(*) FROM users WHERE user_id = :uid"), {"uid": root_id}
    )
    total_versions = result.scalar()
    assert total_versions == 2, (
        f"Should have 2 total versions after update, got {total_versions}"
    )

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM users WHERE user_id = :uid AND upper(valid_time) IS NULL"
        ),
        {"uid": root_id},
    )
    active_versions = result.scalar()
    assert active_versions == 1, (
        f"Should have 1 active version after update, got {active_versions}"
    )

    # Verify old version is closed
    result = await db_session.execute(
        text("SELECT upper(valid_time) IS NULL as is_open FROM users WHERE id = :vid"),
        {"vid": version_1_id},
    )
    old_version_open = result.scalar()
    assert not old_version_open, (
        "Old version should be closed (valid_time upper bound set)"
    )
    print(f"   ✓ Old version {version_1_id} is closed")

    # Verify new version is open
    result = await db_session.execute(
        text("SELECT upper(valid_time) IS NULL as is_open FROM users WHERE id = :vid"),
        {"vid": version_2_id},
    )
    new_version_open = result.scalar()
    assert new_version_open, "New version should be open (valid_time upper bound NULL)"
    print(f"   ✓ New version {version_2_id} is open")

    # Verify get_users returns only the new version
    users = await service.get_users()
    target_users = [u for u in users if u.user_id == root_id]

    assert len(target_users) == 1, (
        f"get_users() should return 1 user after update, got {len(target_users)}"
    )
    assert target_users[0].full_name == "Test User Updated"
    assert target_users[0].id == version_2_id
    print("   ✓ get_users() returns only new version")

    # ==================== SECOND UPDATE ====================
    print("\n4. SECOND UPDATE Operation (stress test)")
    update_in_2 = UserUpdate(full_name="Test User Updated Again", department="Sales")
    updated_user_2 = await service.update_user(root_id, update_in_2, actor_id)
    version_3_id = updated_user_2.id

    await db_session.commit()
    print(f"   Updated User Again - New Version ID: {version_3_id}")

    # Verify: 3 total versions, 1 active version
    result = await db_session.execute(
        text("SELECT count(*) FROM users WHERE user_id = :uid"), {"uid": root_id}
    )
    assert result.scalar() == 3, "Should have 3 total versions after second update"

    result = await db_session.execute(
        text(
            "SELECT count(*) FROM users WHERE user_id = :uid AND upper(valid_time) IS NULL"
        ),
        {"uid": root_id},
    )
    active_after_2nd = result.scalar()
    assert active_after_2nd == 1, (
        f"Should have 1 active version after second update, got {active_after_2nd}"
    )
    print("   ✓ Still only 1 active version after second update")

    # ==================== DELETE ====================
    print("\n5. DELETE Operation")
    await service.delete_user(root_id, actor_id)
    await db_session.commit()
    print(f"   Soft-deleted user {root_id}")

    # Verify: deleted_at is set on current version
    result = await db_session.execute(
        text("SELECT deleted_at IS NOT NULL as is_deleted FROM users WHERE id = :vid"),
        {"vid": version_3_id},
    )
    is_deleted = result.scalar()
    assert is_deleted, "Current version should have deleted_at set"
    print(f"   ✓ Version {version_3_id} is soft-deleted")

    # Verify get_users does not return deleted user
    users = await service.get_users()
    target_users = [u for u in users if u.user_id == root_id]
    assert len(target_users) == 0, "get_users() should not return deleted user"
    print("   ✓ get_users() excludes deleted user")

    print("\n=== All CRUD Operations Passed ===\n")
