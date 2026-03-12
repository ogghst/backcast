import pytest
from httpx import AsyncClient
from collections.abc import Generator

from app.main import app
from app.api.dependencies.auth import get_current_user, get_current_active_user
from app.models.domain.user import User
from uuid import uuid4

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

@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    yield
    app.dependency_overrides = {}

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
