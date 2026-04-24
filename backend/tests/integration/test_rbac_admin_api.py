"""Integration tests for RBAC Admin API routes.

Tests cover:
- Role CRUD endpoints (list, create, update, delete)
- Permission listing endpoint
- Provider status endpoint
- Authorization guards (admin-only, non-admin forbidden)
- Error handling (duplicate name, system-role delete, not-found)
"""

from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.db.session import get_db
from app.main import app
from app.models.domain.user import User

# ---------------------------------------------------------------------------
# Mock users
# ---------------------------------------------------------------------------

MOCK_ADMIN = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@test.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
)

MOCK_VIEWER = User(
    id=uuid4(),
    user_id=uuid4(),
    email="viewer@test.com",
    is_active=True,
    role="viewer",
    full_name="Viewer User",
    hashed_password="hash",
)


class AllowAllRBAC(RBACServiceABC):
    """RBAC service that grants all permissions for testing."""

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return user_role in required_roles

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return ["admin"]

    async def has_project_access(
        self, user_id: UUID, user_role: str, project_id: UUID, required_permission: str
    ) -> bool:
        return True

    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        return []

    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client authenticated as admin."""

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
    app.dependency_overrides[get_current_active_user] = lambda: MOCK_ADMIN
    app.dependency_overrides[get_rbac_service] = lambda: AllowAllRBAC()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def viewer_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client authenticated as a non-admin viewer."""

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: MOCK_VIEWER
    app.dependency_overrides[get_current_active_user] = lambda: MOCK_VIEWER
    app.dependency_overrides[get_rbac_service] = lambda: AllowAllRBAC()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def custom_role(admin_client: AsyncClient) -> dict[str, Any]:
    """Create a custom role via the API and return its JSON data."""
    payload = {
        "name": "engineer",
        "description": "Engineering role",
        "permissions": ["project-read", "project-write"],
    }
    response = await admin_client.post("/api/v1/admin/rbac/roles", json=payload)
    assert response.status_code == 201
    return response.json()


# ---------------------------------------------------------------------------
# List roles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_roles_returns_all(
    admin_client: AsyncClient,
) -> None:
    """GET /admin/rbac/roles returns at least the seeded system roles."""
    response = await admin_client.get("/api/v1/admin/rbac/roles")
    assert response.status_code == 200

    data = response.json()
    names = {r["name"] for r in data}

    # Seeded system roles from the migration
    assert "admin" in names
    assert "viewer" in names
    assert "manager" in names


# ---------------------------------------------------------------------------
# Create role
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_role_success(
    admin_client: AsyncClient,
) -> None:
    """POST /admin/rbac/roles with valid data returns 201."""
    payload = {
        "name": "planner",
        "description": "Planning department role",
        "permissions": ["project-read", "schedule-baseline-read"],
    }
    response = await admin_client.post("/api/v1/admin/rbac/roles", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "planner"
    assert data["description"] == "Planning department role"
    assert data["is_system"] is False
    perm_names = {p["permission"] for p in data["permissions"]}
    assert perm_names == {"project-read", "schedule-baseline-read"}


@pytest.mark.asyncio
async def test_create_role_duplicate_name_400(
    admin_client: AsyncClient,
) -> None:
    """POST /admin/rbac/roles with existing name returns 400."""
    payload = {
        "name": "admin",
        "description": "Duplicate admin",
        "permissions": ["project-read"],
    }
    response = await admin_client.post("/api/v1/admin/rbac/roles", json=payload)

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Update role
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_role_success(
    admin_client: AsyncClient,
    custom_role: dict[str, Any],
) -> None:
    """PUT /admin/rbac/roles/{id} returns 200 with updated data."""
    role_id = custom_role["id"]
    payload = {
        "name": "senior-engineer",
        "description": "Senior engineering role",
        "permissions": ["project-read", "project-write", "project-delete"],
    }
    response = await admin_client.put(
        f"/api/v1/admin/rbac/roles/{role_id}", json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "senior-engineer"
    assert data["description"] == "Senior engineering role"
    assert len(data["permissions"]) == 3


@pytest.mark.asyncio
async def test_update_role_not_found(
    admin_client: AsyncClient,
) -> None:
    """PUT /admin/rbac/roles/{id} with nonexistent ID returns 404."""
    fake_id = str(uuid4())
    payload = {"name": "ghost"}
    response = await admin_client.put(
        f"/api/v1/admin/rbac/roles/{fake_id}", json=payload
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete role
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_role_success(
    admin_client: AsyncClient,
    custom_role: dict[str, Any],
) -> None:
    """DELETE /admin/rbac/roles/{id} returns 204 for non-system role."""
    role_id = custom_role["id"]
    response = await admin_client.delete(f"/api/v1/admin/rbac/roles/{role_id}")

    assert response.status_code == 204

    # Verify role is gone
    response = await admin_client.get(f"/api/v1/admin/rbac/roles/{role_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_system_role_400(
    admin_client: AsyncClient,
) -> None:
    """DELETE /admin/rbac/roles/{id} returns 400 for system roles."""
    # Get a system role ID from the list
    list_response = await admin_client.get("/api/v1/admin/rbac/roles")
    system_role = next(r for r in list_response.json() if r["is_system"])

    response = await admin_client.delete(
        f"/api/v1/admin/rbac/roles/{system_role['id']}"
    )

    assert response.status_code == 400
    assert "system" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_role_not_found(
    admin_client: AsyncClient,
) -> None:
    """DELETE /admin/rbac/roles/{id} with nonexistent ID returns 404."""
    fake_id = str(uuid4())
    response = await admin_client.delete(f"/api/v1/admin/rbac/roles/{fake_id}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# List permissions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_permissions(
    admin_client: AsyncClient,
) -> None:
    """GET /admin/rbac/permissions returns a distinct list of permission strings."""
    response = await admin_client.get("/api/v1/admin/rbac/permissions")

    assert response.status_code == 200
    perms = response.json()
    assert isinstance(perms, list)
    assert len(perms) > 0
    # All entries are strings
    assert all(isinstance(p, str) for p in perms)
    # No duplicates
    assert len(perms) == len(set(perms))


# ---------------------------------------------------------------------------
# Provider status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_status_database(
    admin_client: AsyncClient,
) -> None:
    """GET /admin/rbac/provider-status returns current provider info."""
    response = await admin_client.get("/api/v1/admin/rbac/provider-status")

    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "editable" in data
    assert isinstance(data["editable"], bool)


# ---------------------------------------------------------------------------
# Authorization guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_admin_forbidden(
    viewer_client: AsyncClient,
) -> None:
    """Non-admin user receives 403 on all admin RBAC endpoints."""
    endpoints = [
        ("GET", "/api/v1/admin/rbac/roles"),
        ("POST", "/api/v1/admin/rbac/roles"),
        ("GET", "/api/v1/admin/rbac/permissions"),
        ("GET", "/api/v1/admin/rbac/provider-status"),
    ]
    for method, url in endpoints:
        if method == "GET":
            response = await viewer_client.get(url)
        else:
            response = await viewer_client.post(
                url,
                json={
                    "name": "forbidden",
                    "permissions": ["test"],
                },
            )
        assert response.status_code == 403, f"{method} {url} should be 403"
