from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies.auth import get_current_active_user, get_user_service
from app.main import app
from app.models.domain.user import User


# Mock user for auth
def mock_get_current_active_user():
    # Return a mocked admin user
    return User(
        id=uuid4(),
        user_id=uuid4(),
        email="admin@example.com",
        is_active=True,
        role="admin",
        full_name="Admin User",
        hashed_password="hash",
    )


@pytest.fixture
def mock_user_service():
    return AsyncMock()


@pytest.fixture
def override_deps(mock_user_service):
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    yield
    app.dependency_overrides = {}


class MockRange:
    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper


@pytest.mark.asyncio
async def test_get_user_history_returns_temporal_fields(
    client: AsyncClient, override_deps, mock_user_service
):
    """Test that the history endpoint returns valid_time and transaction_time."""
    user_id = uuid4()
    now = datetime.now()

    # Create mock user objects representing history
    # Note: User constructor arguments must match model fields or validation
    user_v1 = User(
        id=uuid4(),
        user_id=user_id,
        email="test@example.com",
        full_name="Version 1",
        role="viewer",
        is_active=True,
        hashed_password="hash",
        valid_time=MockRange(now, None),
        transaction_time=MockRange(now, None),
    )

    mock_user_service.get_user_history.return_value = [user_v1]

    # Call API
    response = await client.get(f"/api/v1/users/{user_id}/history")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["full_name"] == "Version 1"
    assert "valid_time" in data[0]
    assert isinstance(data[0]["valid_time"], list)
    assert len(data[0]["valid_time"]) == 2
