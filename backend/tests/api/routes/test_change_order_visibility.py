import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from uuid import uuid4
from collections.abc import Generator

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User

# --- Auth Mocks ---
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
            "project-create",
            "change-order-create",
            "change-order-read",
            "change-order-audit-read",  # Add other potential perms if needed
        ]

def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()

@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_change_order_branch_visibility_future_control_date(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Test that a Change Order created with a future control_date
    creates a branch that is visible in get_project_branches immediately.
    """
    # 1. Create Project
    p_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Visibility Test Project", "code": "VIS-TEST", "budget": 100000},
    )
    assert p_resp.status_code == 201
    project_id = p_resp.json()["project_id"]

    future_date = datetime.now() + timedelta(days=30)
    
    # 2. Create Change Order with future control_date
    co_data = {
        "project_id": str(project_id),
        "code": "CO-FUTURE-001",
        "title": "Future Change Order",
        "description": "Testing visibility",
        "control_date": future_date.isoformat(),
        "branch": "main"
    }
    
    response = await client.post(
        "/api/v1/change-orders",
        json=co_data,
    )
    assert response.status_code == 201
    
    # 3. Get Project Branches
    response = await client.get(
        f"/api/v1/projects/{project_id}/branches",
    )
    assert response.status_code == 200
    branches = response.json()
    
    # 4. Verify Branch Exists
    co_branch = next((b for b in branches if b["name"] == "co-CO-FUTURE-001"), None)
    assert co_branch is not None, "Change Order branch not found in project branches"
    
    # 5. Verify Change Order Status is present (not None)
    assert co_branch["change_order_status"] == "Draft", \
        f"Expected status 'Draft', got {co_branch.get('change_order_status')}"
