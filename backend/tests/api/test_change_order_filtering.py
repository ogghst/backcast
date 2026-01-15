from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User


# --- Mocks for Auth ---
mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
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
        return [
            "project-read",
            "change-order-read",
            "change-order-create",
            "change-order-update",
            "change-order-delete",
        ]

def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()

@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


# --- Fixtures ---
@pytest_asyncio.fixture
async def test_project(client: AsyncClient) -> dict[str, Any]:
    project_data = {
        "name": "CO Test Project",
        "code": "CO-PROJ",
        "budget": 500000,
    }
    response = await client.post("/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()


# --- Tests ---

@pytest.mark.asyncio
async def test_search_change_orders(
    client: AsyncClient,
    test_project: dict[str, Any],
) -> None:
    """Test searching Change Orders by code or name."""
    project_id = test_project["project_id"]

    # 1. Create Change Orders
    co1 = {
        "project_id": project_id,
        "code": "CO-SEARCH-1",
        "title": "Alpha Change",
        "status": "Draft",
        "description": "First CO",
    }
    co2 = {
        "project_id": project_id,
        "code": "CO-SEARCH-2",
        "title": "Beta Change",
        "status": "Submitted",
        "description": "Second CO",
    }
    
    resp1 = await client.post("/api/v1/change-orders", json=co1)
    assert resp1.status_code == 201
    
    resp2 = await client.post("/api/v1/change-orders", json=co2)
    assert resp2.status_code == 201

    # 2. Search for "Alpha" -> Should return CO1 only
    search_resp = await client.get(
        f"/api/v1/change-orders",
        params={"project_id": project_id, "search": "Alpha"}
    )
    assert search_resp.status_code == 200
    results = search_resp.json()["items"]
    
    # Assert
    assert len(results) == 1
    assert results[0]["code"] == "CO-SEARCH-1"
    assert results[0]["title"] == "Alpha Change"

    # 3. Search for "SEARCH" -> Should return both
    search_all = await client.get(
        f"/api/v1/change-orders",
        params={"project_id": project_id, "search": "SEARCH"}
    )
    assert search_all.status_code == 200
    assert len(search_all.json()["items"]) == 2

@pytest.mark.asyncio
async def test_filter_change_orders(
    client: AsyncClient,
    test_project: dict[str, Any],
) -> None:
    """Test filtering Change Orders by status."""
    project_id = test_project["project_id"]

    # 1. Create COs with different statuses
    co1 = {
        "project_id": project_id,
        "code": "CO-FILT-1",
        "title": "Draft CO",
        "status": "Draft",
        "description": "Draft",
    }
    co2 = {
        "project_id": project_id,
        "code": "CO-FILT-2",
        "title": "Submitted CO",
        "status": "Submitted",
        "description": "Submitted",
    }
    
    await client.post("/api/v1/change-orders", json=co1)
    await client.post("/api/v1/change-orders", json=co2)

    # 2. Filter by status:Draft
    resp = await client.get(
        "/api/v1/change-orders",
        params={"project_id": project_id, "filters": "status:Draft"}
    )
    assert resp.status_code == 200
    results = resp.json()["items"]
    
    assert len(results) == 1
    assert results[0]["code"] == "CO-FILT-1"
    assert results[0]["status"] == "Draft"
    
@pytest.mark.asyncio
async def test_merge_change_order(
    client: AsyncClient,
    test_project: dict[str, Any],
    db_session: AsyncSession,
) -> None:
    """Test merging a Change Order branch into main."""
    from sqlalchemy import select as sql_select
    from app.models.domain.change_order import ChangeOrder

    project_id = test_project["project_id"]

    # 1. Create CO on main (creates branch co-TEST-MERGE)
    co_data = {
        "project_id": project_id,
        "code": "TEST-MERGE",
        "title": "Original Title",
        "status": "Draft",
    }
    resp = await client.post("/api/v1/change-orders", json=co_data)
    assert resp.status_code == 201
    co_id = UUID(resp.json()["change_order_id"])  # Convert to UUID
    main_v1_id = UUID(resp.json()["id"])  # Convert to UUID
    branch_name = f"co-TEST-MERGE"

    # Verify DB state: V1 exists on main
    from sqlalchemy import func
    stmt = sql_select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == "main",
    ).order_by(ChangeOrder.valid_time.desc())
    result = await db_session.execute(stmt)
    main_versions = result.scalars().all()
    print(f"DEBUG: After CO creation, main versions:")
    for i, v in enumerate(main_versions):
        print(f"  [{i}] id={v.id}")
        print(f"      title={v.title}")
        print(f"      valid_time=[{v.valid_time.lower}, {v.valid_time.upper})")
        print(f"      transaction_time=[{v.transaction_time.lower}, {v.transaction_time.upper})")
    assert len(main_versions) == 1
    assert main_versions[0].title == "Original Title"

    # Debug: Check if CO creation also created a version on the branch
    stmt_branch_after_create = sql_select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == branch_name,
    ).order_by(ChangeOrder.valid_time.desc())
    result_branch_after_create = await db_session.execute(stmt_branch_after_create)
    branch_versions_after_create = result_branch_after_create.scalars().all()
    print(f"DEBUG: After CO creation, {len(branch_versions_after_create)} versions on {branch_name}:")
    for i, v in enumerate(branch_versions_after_create):
        print(f"  [{i}] id={v.id}")
        print(f"      title={v.title}")
        print(f"      valid_time=[{v.valid_time.lower}, {v.valid_time.upper})")
        print(f"      transaction_time=[{v.transaction_time.lower}, {v.transaction_time.upper})")

    # 2. Update CO on its branch (this should auto-fork and create V2 on co-TEST-MERGE)
    # First, check what's on the branch BEFORE update
    from sqlalchemy import func
    stmt_branch_before = sql_select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == branch_name,
        ChangeOrder.deleted_at.is_(None),
        func.upper(ChangeOrder.valid_time).is_(None),  # Current version only (matches user-facing logic)
    ).order_by(ChangeOrder.valid_time.desc())
    result_branch_before = await db_session.execute(stmt_branch_before)
    branch_versions_before = result_branch_before.scalars().all()
    print(f"DEBUG: Before update, {len(branch_versions_before)} current versions on {branch_name}")

    update_data = {
        "title": "Modified on Branch",
        "branch": branch_name,  # Specify branch to update on
    }
    update_resp = await client.put(f"/api/v1/change-orders/{co_id}", json=update_data)
    assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
    branch_v2_id = UUID(update_resp.json()["id"])  # Convert to UUID
    assert branch_v2_id != main_v1_id, "Update should create a new version"

    # Verify DB state: V2 exists on co-TEST-MERGE branch (current version only)
    stmt_branch = sql_select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == branch_name,
        ChangeOrder.deleted_at.is_(None),
        func.upper(ChangeOrder.valid_time).is_(None),  # Current version only (matches user-facing logic)
    ).order_by(ChangeOrder.valid_time.desc())
    result_branch = await db_session.execute(stmt_branch)
    branch_versions = result_branch.scalars().all()

    # Debug: print all branch versions with full temporal details
    stmt_all_branch = sql_select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == branch_name,
    ).order_by(ChangeOrder.valid_time.desc())
    result_all_branch = await db_session.execute(stmt_all_branch)
    all_branch_versions = result_all_branch.scalars().all()
    print(f"DEBUG: After update, {len(branch_versions)} current versions, {len(all_branch_versions)} total versions on {branch_name}:")
    for i, v in enumerate(all_branch_versions):
        print(f"  [{i}] id={v.id}")
        print(f"      title={v.title}")
        print(f"      valid_time=[{v.valid_time.lower}, {v.valid_time.upper})")
        print(f"      transaction_time=[{v.transaction_time.lower}, {v.transaction_time.upper})")
        print(f"      deleted_at={v.deleted_at}")

    assert len(branch_versions) >= 1, f"Expected at least 1 current version on branch, got {len(branch_versions)}"
    # Find the version with the expected title
    matching_versions = [v for v in branch_versions if v.title == "Modified on Branch"]
    assert len(matching_versions) >= 1, f"Expected to find version with 'Modified on Branch' title, got {[v.title for v in branch_versions]}"

    # 3. Merge co-TEST-MERGE -> main (creates V3 on main with branch content)
    merge_resp = await client.post(f"/api/v1/change-orders/{co_id}/merge")
    assert merge_resp.status_code == 200, f"Merge failed: {merge_resp.text}"
    merged_data = merge_resp.json()
    assert merged_data["branch"] == "main"
    merged_v3_id = UUID(merged_data["id"])  # Convert to UUID for type consistency
    assert merged_v3_id != main_v1_id
    assert merged_v3_id != branch_v2_id

    # 4. Verify DB state after merge:
    # - V3 on main has the merged content ("Modified on Branch")
    # - V1 on main is closed (transaction_time upper bound set)
    # - V2 on co-TEST-MERGE remains unchanged

    # First, get all versions (including closed ones)
    stmt_main_all = sql_select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == "main",
    ).order_by(ChangeOrder.valid_time.desc())
    result_main_all = await db_session.execute(stmt_main_all)
    main_versions_all = result_main_all.scalars().all()

    # Debug: print all main versions with full temporal details
    print(f"DEBUG: After merge, {len(main_versions_all)} total versions on main:")
    for i, v in enumerate(main_versions_all):
        print(f"  [{i}] id={v.id}")
        print(f"      title={v.title}")
        print(f"      valid_time=[{v.valid_time.lower}, {v.valid_time.upper})")
        print(f"      transaction_time=[{v.transaction_time.lower}, {v.transaction_time.upper})")
        print(f"      deleted_at={v.deleted_at}, merge_from={getattr(v, 'merge_from_branch', None)}")
    print(f"DEBUG: merged_v3_id from API response = {merged_v3_id}")
    print(f"DEBUG: main_v1_id = {main_v1_id}")
    print(f"DEBUG: branch_v2_id = {branch_v2_id}")

    # Should have 2 versions on main now (V1 closed, V3 current)
    assert len(main_versions_all) == 2

    # Now get the CURRENT version (transaction_time.upper IS NULL)
    stmt_main_current = sql_select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == "main",
        func.upper(ChangeOrder.valid_time).is_(None),  # Current version only (matches user-facing logic)  # Current version only
    ).order_by(ChangeOrder.valid_time.desc())
    result_main_current = await db_session.execute(stmt_main_current)
    main_current_versions = result_main_current.scalars().all()

    # Should have exactly 1 current version
    assert len(main_current_versions) == 1, f"Expected 1 current version on main, got {len(main_current_versions)}"

    # Current version should be V3 with merged content
    current_main = main_current_versions[0]
    assert current_main.id == merged_v3_id, f"Expected current main id={merged_v3_id}, got {current_main.id}"
    assert current_main.title == "Modified on Branch"
    assert current_main.merge_from_branch == branch_name

    # Previous version V1 should be closed (find it in the all versions list)
    old_main = [v for v in main_versions_all if v.id == main_v1_id][0]
    assert old_main.transaction_time.upper is not None  # Should be closed

    # Branch version should remain unchanged (current version only)
    stmt_branch_final = sql_select(ChangeOrder).where(
        ChangeOrder.change_order_id == co_id,
        ChangeOrder.branch == branch_name,
        ChangeOrder.deleted_at.is_(None),
        func.upper(ChangeOrder.valid_time).is_(None),  # Current version only (matches user-facing logic)  # Current version only
    ).order_by(ChangeOrder.valid_time.desc())
    result_branch_final = await db_session.execute(stmt_branch_final)
    branch_versions_final = result_branch_final.scalars().all()
    print(f"DEBUG: Final branch versions (current only):")
    for i, v in enumerate(branch_versions_final):
        print(f"  [{i}] id={v.id}")
        print(f"      title={v.title}")
        print(f"      valid_time=[{v.valid_time.lower}, {v.valid_time.upper})")
        print(f"      transaction_time=[{v.transaction_time.lower}, {v.transaction_time.upper})")
    assert len(branch_versions_final) == 1, f"Expected 1 current version on branch after merge, got {len(branch_versions_final)}"
    assert branch_versions_final[0].id == branch_v2_id
    assert branch_versions_final[0].title == "Modified on Branch"

@pytest.mark.asyncio
async def test_revert_change_order(
    client: AsyncClient,
    test_project: dict[str, Any],
) -> None:
    """Test reverting a Change Order."""
    project_id = test_project["project_id"]

    # 1. Create CO
    co_data = {
        "project_id": project_id,
        "code": "TEST-REVERT",
        "title": "Revert Test",
        "status": "Draft",
    }
    resp = await client.post("/api/v1/change-orders", json=co_data)
    assert resp.status_code == 201
    co_id = resp.json()["change_order_id"]
    initial_id = resp.json()["id"]

    # 2. Update CO (New Version) - use valid workflow transition "Draft" → "Submitted for Approval"
    put_resp = await client.put(f"/api/v1/change-orders/{co_id}", json={"status": "Submitted for Approval"})
    assert put_resp.status_code == 200, f"PUT failed: {put_resp.text}"
    updated_id = put_resp.json()["id"]

    # Verify we got a new version ID (update creates new version)
    assert updated_id != initial_id, "Update should create a new version"

    # Verify current is "Submitted for Approval"
    curr_resp = await client.get(f"/api/v1/change-orders/{co_id}")
    assert curr_resp.status_code == 200
    curr_data = curr_resp.json()
    assert curr_data["status"] == "Submitted for Approval", f"Expected 'Submitted for Approval', got '{curr_data['status']}'"

    # 3. Revert - should create V3 with status from V1 (Draft)
    # POST /{id}/revert
    revert_resp = await client.post(f"/api/v1/change-orders/{co_id}/revert")
    assert revert_resp.status_code == 200, f"Revert failed: {revert_resp.text}"
    reverted_id = revert_resp.json()["id"]

    # Verify we got another new version ID (revert creates new version)
    assert reverted_id != updated_id, "Revert should create a new version"

    # Verify status reverted to Draft (cloned from V1)
    final_resp = await client.get(f"/api/v1/change-orders/{co_id}")
    assert final_resp.status_code == 200
    final_data = final_resp.json()
    assert final_data["status"] == "Draft", f"Expected 'Draft' after revert, got '{final_data['status']}'"
