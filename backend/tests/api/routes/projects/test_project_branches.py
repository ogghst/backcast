from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
        ]

    async def has_project_access(
        self,
        user_id: UUID,
        user_role: str,
        project_id: UUID,
        required_permission: str,
    ) -> bool:
        return True

    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        return []

    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        return None


def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()


@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


# --- Tests ---


@pytest.mark.asyncio
async def test_get_branches_empty(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    # Create project
    p_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Branch Test 1", "code": "B-TEST-1"},
    )
    assert p_resp.status_code == 201
    pid = p_resp.json()["project_id"]

    # Get branches
    resp = await client.get(f"/api/v1/projects/{pid}/branches")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 1
    assert data[0]["name"] == "main"
    assert data[0]["type"] == "main"
    assert data[0]["is_default"] is True


@pytest.mark.asyncio
async def test_get_branches_with_cos(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    # Create project
    p_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Branch Test 2", "code": "B-TEST-2"},
    )
    pid = p_resp.json()["project_id"]

    # Create CO 1 (Draft)
    co1_resp = await client.post(
        "/api/v1/change-orders",
        json={
            "project_id": pid,
            "code": "CO-1",
            "title": "C1",
            "status": "Draft",
            "description": "Desc",
        },
    )
    assert co1_resp.status_code == 201

    # Create CO 2 (Approved)
    co2_resp = await client.post(
        "/api/v1/change-orders",
        json={
            "project_id": pid,
            "code": "CO-2",
            "title": "C2",
            "status": "Approved",
            "description": "Desc",
        },
    )
    assert co2_resp.status_code == 201

    # Get branches
    resp = await client.get(f"/api/v1/projects/{pid}/branches")
    assert resp.status_code == 200
    data = resp.json()

    # Expect 3 branches: main, BR-CO-1, BR-CO-2
    assert len(data) == 3

    names = [b["name"] for b in data]
    assert "main" in names
    assert "BR-CO-1" in names
    assert "BR-CO-2" in names

    # Check details for CO-1
    co1_branch = next(b for b in data if b["name"] == "BR-CO-1")

    assert co1_branch["type"] == "change_order"
    assert co1_branch["change_order_code"] == "CO-1"
    assert co1_branch["change_order_status"] == "Draft"
    assert co1_branch["is_default"] is False
