"""Configuration for AI integration tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.agent_service import AgentService
from app.core.rbac_unified import (
    UnifiedRBACService,
    set_unified_rbac_service,
)
from tests.conftest import MockUnifiedRBACService


@pytest.fixture(autouse=True)
def setup_mock_rbac():
    """Automatically use mock RBAC service for all AI integration tests."""
    set_unified_rbac_service(MockUnifiedRBACService())

    yield

    set_unified_rbac_service(UnifiedRBACService())

@pytest.fixture
def mock_agent_service():
    """Create a mock AgentService for testing."""
    return MagicMock(spec=AgentService)

@pytest.fixture
def mock_project_service():
    """Create a mock ProjectService for testing."""
    service = MagicMock()
    service.get_projects = AsyncMock(return_value=([], 0))
    service.get_by_id = AsyncMock(return_value=None)
    service.create_project = AsyncMock(return_value=None)
    service.update_project = AsyncMock(return_value=None)
    return service
