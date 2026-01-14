"""Test temporal consistency of Change Order updates.

This test verifies that when a Change Order is updated:
1. The old version is properly closed with correct valid_time and transaction_time
2. The new version has correct temporal ranges
3. No empty ranges are created (e.g., [t, t))
"""

import asyncio
from datetime import datetime, timedelta, UTC
from uuid import UUID
from sqlalchemy import select as sql_select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.models.domain.change_order import ChangeOrder
from app.models.domain.user import User
from typing import Any, cast


# --- Mocks for Auth ---
mock_admin_user = User(
    id=UUID('00000000-0000-0000-0000-000000000001'),
    user_id=UUID('00000000-0000-0000-0000-000000000001'),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
)

def mock_get_current_user() -> User:
    return mock_admin_user

def mock_get_current_active_user() -> User:
    return mock_admin_user

class MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return ["change-order-read", "change-order-create", "change-order-update"]

def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()

@pytest.fixture(autouse=True)
def override_auth():
    import app.api.routes.change_orders as co_routes
    import app.main as app_main
    app_main.app.dependency_overrides[get_current_user] = mock_get_current_user
    app_main.app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app_main.app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app_main.app.dependency_overrides = {}


@pytest_asyncio.fixture
async def test_project(client: AsyncClient) -> dict[str, Any]:
    """Create a test project."""
    project_data = {
        "name": "Temporal Test Project",
        "code": "TEMP-TEST",
        "budget": 500000,
    }
    response = await client.post("/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()


async def print_version_details(
    version: ChangeOrder,
    label: str,
    indent: str = "  "
) -> None:
    """Print detailed temporal information for a version."""
    print(f"{indent}{label}:")
    print(f"{indent}  id={version.id}")
    print(f"{indent}  title={version.title}")
    print(f"{indent}  branch={version.branch}")
    print(f"{indent}  parent_id={version.parent_id}")
    print(f"{indent}  merge_from_branch={getattr(version, 'merge_from_branch', None)}")
    print(f"{indent}  deleted_at={version.deleted_at}")

    # Temporal ranges
    vt_lower = version.valid_time.lower
    vt_upper = version.valid_time.upper
    tt_lower = version.transaction_time.lower
    tt_upper = version.transaction_time.upper

    print(f"{indent}  valid_time=[{vt_lower}, {vt_upper})")
    print(f"{indent}  transaction_time=[{tt_lower}, {tt_upper})")

    # Check for issues
    if vt_lower is None:
        print(f"{indent}  ⚠️  WARNING: valid_time lower bound is NULL")
    if vt_upper is not None and vt_lower is not None:
        if vt_upper <= vt_lower:
            print(f"{indent}  ❌ ERROR: valid_time is empty or inverted [{vt_lower}, {vt_upper})")
        else:
            duration = vt_upper - vt_lower
            print(f"{indent}  ✓ valid_time duration: {duration.total_seconds():.3f}s")
    else:
        print(f"{indent}  ✓ valid_time is open-ended")

    if tt_lower is None:
        print(f"{indent}  ⚠️  WARNING: transaction_time lower bound is NULL")
    if tt_upper is not None and tt_lower is not None:
        if tt_upper <= tt_lower:
            print(f"{indent}  ❌ ERROR: transaction_time is empty or inverted [{tt_lower}, {tt_upper})")
        else:
            duration = tt_upper - tt_lower
            print(f"{indent}  ✓ transaction_time duration: {duration.total_seconds():.3f}s")
    else:
        print(f"{indent}  ✓ transaction_time is open-ended (current version)")


@pytest.mark.asyncio
async def test_change_order_update_temporal_consistency(
    client: AsyncClient,
    test_project: dict[str, Any],
    db_session: AsyncSession,
) -> None:
    """Test that updating a Change Order maintains correct temporal ranges."""
    from app.models.domain.change_order import ChangeOrder

    project_id = test_project["project_id"]

    print("\n" + "="*80)
    print("TEMPORAL CONSISTENCY TEST")
    print("="*80)

    # ========================================================================
    # STEP 1: Create initial Change Order
    # ========================================================================
    print("\n--- STEP 1: Creating initial Change Order ---")

    co_data = {
        "project_id": project_id,
        "code": "TEMP-001",
        "title": "Initial Title",
        "status": "Draft",
        "description": "Initial description",
    }

    create_resp = await client.post("/api/v1/change-orders", json=co_data)
    assert create_resp.status_code == 201
    created_data = create_resp.json()

    co_id = UUID(created_data["change_order_id"])
    initial_version_id = UUID(created_data["id"])

    print(f"Created Change Order:")
    print(f"  change_order_id={co_id}")
    print(f"  version_id={initial_version_id}")
    print(f"  code={created_data['code']}")
    print(f"  title={created_data['title']}")

    # Fetch from DB to verify temporal ranges
    stmt = sql_select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == "main",
    ).order_by(ChangeOrder.valid_time.desc())
    result = await db_session.execute(stmt)
    versions_after_create = result.scalars().all()

    print(f"\nDatabase state after creation ({len(versions_after_create)} version(s)):")
    for i, v in enumerate(versions_after_create):
        await print_version_details(v, f"Version [{i}]")

    # Verify: Should have exactly 1 version
    assert len(versions_after_create) == 1, f"Expected 1 version after creation, got {len(versions_after_create)}"
    v1 = versions_after_create[0]

    # Verify: V1 should be current (open-ended ranges)
    assert v1.valid_time.upper is None, "V1 valid_time should be open-ended"
    assert v1.transaction_time.upper is None, "V1 transaction_time should be open-ended"
    assert v1.title == "Initial Title"

    print("✓ STEP 1 PASSED: Initial version created with correct temporal ranges")

    # ========================================================================
    # STEP 2: Wait 3 seconds
    # ========================================================================
    print("\n--- STEP 2: Waiting 3 seconds ---")
    await asyncio.sleep(3)
    print("✓ Wait completed")

    # ========================================================================
    # STEP 3: Update the Change Order
    # ========================================================================
    print("\n--- STEP 3: Updating Change Order ---")

    # Record time before update
    update_start_time = datetime.now(UTC)
    print(f"Update started at: {update_start_time.isoformat()}")

    update_data = {
        "title": "Updated Title",
        "description": "Updated description",
    }

    update_resp = await client.put(f"/api/v1/change-orders/{co_id}", json=update_data)
    assert update_resp.status_code == 200
    updated_data = update_resp.json()

    new_version_id = UUID(updated_data["id"])

    # Record time after update
    update_end_time = datetime.now(UTC)
    print(f"Update completed at: {update_end_time.isoformat()}")

    print(f"Updated Change Order:")
    print(f"  new version_id={new_version_id}")
    print(f"  title={updated_data['title']}")
    print(f"  description={updated_data['description']}")

    # Verify: New version ID is different
    assert new_version_id != initial_version_id, "Update should create a new version"

    print("✓ STEP 3 PASSED: Update created new version")

    # ========================================================================
    # STEP 4: Fetch and verify temporal consistency
    # ========================================================================
    print("\n--- STEP 4: Verifying temporal consistency ---")

    # Fetch all versions (including closed ones)
    stmt_all = sql_select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == "main",
    ).order_by(ChangeOrder.valid_time.desc())
    result_all = await db_session.execute(stmt_all)
    all_versions = result_all.scalars().all()

    print(f"\nDatabase state after update ({len(all_versions)} version(s)):")
    for i, v in enumerate(all_versions):
        await print_version_details(v, f"Version [{i}]")

    # Verify: Should have exactly 2 versions
    assert len(all_versions) == 2, f"Expected 2 versions after update, got {len(all_versions)}"

    # Separate into old (V1) and new (V2)
    old_version = [v for v in all_versions if v.id == initial_version_id][0]
    new_version = [v for v in all_versions if v.id == new_version_id][0]

    print("\n--- VERIFYING OLD VERSION (V1) ---")
    await print_version_details(old_version, "Old Version (V1)")

    # Verify: V1 should be closed
    assert old_version.valid_time.upper is not None, "V1 valid_time should be closed"
    assert old_version.transaction_time.upper is not None, "V1 transaction_time should be closed"

    # Verify: V1 should not be empty
    vt_lower = old_version.valid_time.lower
    vt_upper = old_version.valid_time.upper
    tt_lower = old_version.transaction_time.lower
    tt_upper = old_version.transaction_time.upper

    assert vt_lower is not None, "V1 valid_time lower bound should not be NULL"
    assert vt_upper is not None, "V1 valid_time upper bound should not be NULL"
    assert tt_lower is not None, "V1 transaction_time lower bound should not be NULL"
    assert tt_upper is not None, "V1 transaction_time upper bound should not be NULL"

    # Verify: V1 ranges should not be empty (upper > lower)
    assert vt_upper > vt_lower, f"V1 valid_time should not be empty: [{vt_lower}, {vt_upper})"
    assert tt_upper > tt_lower, f"V1 transaction_time should not be empty: [{tt_lower}, {tt_upper})"

    # Verify: V1 should have the old content
    assert old_version.title == "Initial Title", "V1 should retain old title"
    assert old_version.description == "Initial description", "V1 should retain old description"

    # Verify: V1 valid_time should span from creation to update
    # The update happened ~3 seconds after creation, so valid_time should be ~3 seconds
    v1_duration = (vt_upper - vt_lower).total_seconds()
    print(f"\nV1 valid_time duration: {v1_duration:.3f}s")
    assert v1_duration >= 2.5, f"V1 valid_time should span at least 2.5s, got {v1_duration:.3f}s"
    assert v1_duration <= 5.0, f"V1 valid_time should span at most 5s, got {v1_duration:.3f}s"

    # Verify: V1 transaction_time should also be closed
    # The closing should happen very close to the update time
    v1_tx_duration = (tt_upper - tt_lower).total_seconds()
    print(f"V1 transaction_time duration: {v1_tx_duration:.3f}s")
    assert v1_tx_duration >= 2.5, f"V1 transaction_time should span at least 2.5s, got {v1_tx_duration:.3f}s"
    assert v1_tx_duration <= 5.0, f"V1 transaction_time should span at most 5s, got {v1_tx_duration:.3f}s"

    print("✓ OLD VERSION (V1) VERIFIED: Properly closed with correct temporal ranges")

    print("\n--- VERIFYING NEW VERSION (V2) ---")
    await print_version_details(new_version, "New Version (V2)")

    # Verify: V2 should be current (open-ended)
    assert new_version.valid_time.upper is None, "V2 valid_time should be open-ended"
    assert new_version.transaction_time.upper is None, "V2 transaction_time should be open-ended"

    # Verify: V2 should have the new content
    assert new_version.title == "Updated Title", "V2 should have new title"
    assert new_version.description == "Updated description", "V2 should have new description"

    # Verify: V2 parent should be V1
    assert new_version.parent_id == initial_version_id, "V2 parent should be V1"

    # Verify: V2 lower bounds should be after or at V1 upper bounds
    v2_vt_lower = new_version.valid_time.lower
    v2_tt_lower = new_version.transaction_time.lower

    assert v2_vt_lower is not None, "V2 valid_time lower bound should not be NULL"
    assert v2_tt_lower is not None, "V2 transaction_time lower bound should not be NULL"

    # V2 valid_time should start at or after V1 valid_time ends
    # There might be a tiny gap due to clock precision, but it should be minimal
    if v2_vt_lower >= vt_upper:
        gap = (v2_vt_lower - vt_upper).total_seconds()
        print(f"\nV2 valid_time starts {gap:.6f}s after V1 ends")
        assert gap < 0.1, f"Gap between V1 and V2 should be minimal, got {gap:.6f}s"

    # V2 transaction_time should start at or after V1 transaction_time ends
    if v2_tt_lower >= tt_upper:
        gap = (v2_tt_lower - tt_upper).total_seconds()
        print(f"V2 transaction_time starts {gap:.6f}s after V1 ends")
        assert gap < 0.1, f"Gap between V1 and V2 should be minimal, got {gap:.6f}s"

    print("✓ NEW VERSION (V2) VERIFIED: Current version with correct temporal ranges")

    # ========================================================================
    # STEP 5: Verify no duplicate current versions
    # ========================================================================
    print("\n--- STEP 5: Verifying no duplicate current versions ---")

    # Fetch only current versions (valid_time upper IS NULL - matches user-facing logic)
    stmt_current = sql_select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == "main",
        ChangeOrder.deleted_at.is_(None),
        func.upper(ChangeOrder.valid_time).is_(None),
    ).order_by(ChangeOrder.valid_time.desc())
    result_current = await db_session.execute(stmt_current)
    current_versions = result_current.scalars().all()

    print(f"Current versions: {len(current_versions)}")
    assert len(current_versions) == 1, f"Should have exactly 1 current version, got {len(current_versions)}"
    assert current_versions[0].id == new_version_id, "Current version should be V2"

    print("✓ STEP 5 PASSED: No duplicate current versions")

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("✓ ALL CHECKS PASSED")
    print("="*80)
    print("\nSummary:")
    print("  • V1 (old version) properly closed with non-empty temporal ranges")
    print("  • V2 (new version) is current with open-ended temporal ranges")
    print("  • No duplicate current versions")
    print("  • Temporal ranges are consistent with bitemporal design")
    print("\n")
