from collections.abc import Generator
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, set_rbac_service
from app.main import app
from app.models.domain.user import User

# Mock admin user for auth
mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
    created_by=uuid4(),
)


def mock_get_current_user() -> User:
    return mock_admin_user


def mock_get_current_active_user() -> User:
    return mock_admin_user


class MockRBACService(RBACServiceABC):
    """Mock RBAC service for API tests."""

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True  # Admin has all roles

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True  # Admin has all permissions

    def get_user_permissions(self, user_role: str) -> list[str]:
        return ["*"]  # Admin has all permissions


@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user

    # Set up mock RBAC service
    mock_rbac = MockRBACService()
    set_rbac_service(mock_rbac)

    yield

    app.dependency_overrides = {}
    # Reset RBAC service to prevent test pollution
    set_rbac_service(None)


@pytest.mark.asyncio
async def test_getting_ai_tools_list_returns_valid_schemas(
    client: AsyncClient, override_auth: None
) -> None:
    # Act
    r = await client.get("/api/v1/ai/config/tools")

    # Assert
    assert r.status_code == 200, f"Unexpected status code: {r.status_code}"

    tools = r.json()
    assert isinstance(tools, list)
    assert len(tools) > 0, "No tools returned from registry"

    # Verify basic schema shape of first tool
    tool = tools[0]
    # tool is an AIToolPublic schema instance
    assert "name" in tool
    assert "description" in tool
    assert "permissions" in tool
    assert isinstance(tool["permissions"], list)
    assert "category" in tool
    assert "version" in tool
