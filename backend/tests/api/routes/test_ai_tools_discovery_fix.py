"""Test that all template modules are discovered in the AI tools endpoint.

This test verifies the fix for the missing template discovery in ai_config.py
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.ai.tools.registry import get_registry
from app.api.dependencies.auth import get_current_user
from app.core.rbac_unified import (
    UnifiedRBACService,
    set_unified_rbac_service,
)
from app.main import app
from app.models.domain.user import User
from tests.conftest import MockUnifiedRBACService

# Mock admin user for auth
mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    full_name="Admin User",
    hashed_password="hash",
    created_by=uuid4(),
)
def mock_get_current_user() -> User:
    return mock_admin_user
@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_user

    set_unified_rbac_service(MockUnifiedRBACService())

    yield

    set_unified_rbac_service(UnifiedRBACService())
    app.dependency_overrides = {}
def test_all_template_modules_are_discovered() -> None:
    """Test that all 7 template modules are discovered and registered."""
    registry = get_registry()

    # Clear registry to start fresh
    registry._tools.clear()

    # Simulate the discovery process from the endpoint
    registry.discover_and_register("app.ai.tools.project_tools")
    registry.discover_and_register("app.ai.tools.templates.analysis_template")
    registry.discover_and_register("app.ai.tools.templates.change_order_template")
    registry.discover_and_register("app.ai.tools.templates.project_template")
    registry.discover_and_register("app.ai.tools.templates.cost_element_template")
    registry.discover_and_register("app.ai.tools.templates.user_management_template")
    registry.discover_and_register("app.ai.tools.templates.advanced_analysis_template")
    registry.discover_and_register("app.ai.tools.templates.diagram_template")

    tools = registry.get_all_metadata()

    # Verify we have tools from all expected modules
    tool_names = [tool.name for tool in tools]

    # From project_tools (2 tools)
    assert "list_projects" in tool_names
    assert "get_project" in tool_names

    # From project_template (6 unique tools - excluding duplicates)
    assert "create_project" in tool_names
    assert "update_project" in tool_names
    assert "find_wbes" in tool_names
    assert "create_wbe" in tool_names

    # From analysis_template (1 consolidated tool)
    assert "get_project_analysis" in tool_names

    # From change_order_template (8 tools)
    assert "find_change_orders" in tool_names
    assert "create_change_order" in tool_names
    assert "generate_change_order_draft" in tool_names
    assert "submit_change_order_for_approval" in tool_names
    assert "approve_change_order" in tool_names
    assert "reject_change_order" in tool_names
    assert "analyze_change_order_impact" in tool_names

    # From cost_element_template (13 tools: find + CRUD CE, find + CRUD CE Type, batch CE)
    assert "find_cost_elements" in tool_names
    assert "create_cost_element" in tool_names
    assert "update_cost_element" in tool_names
    assert "delete_cost_element" in tool_names
    assert "find_cost_element_types" in tool_names
    assert "create_cost_element_type" in tool_names
    assert "update_cost_element_type" in tool_names
    assert "delete_cost_element_type" in tool_names

    # From user_management_template (8 tools)
    assert "find_users" in tool_names
    assert "create_user" in tool_names
    assert "update_user" in tool_names
    assert "delete_user" in tool_names
    assert "find_departments" in tool_names
    assert "create_department" in tool_names
    assert "update_department" in tool_names
    assert "delete_department" in tool_names

    # From advanced_analysis_template (1 consolidated tool)
    assert "get_project_forecast" in tool_names

    # From diagram_template (1 tool)
    assert "generate_mermaid_diagram" in tool_names

    # Total expected: ~48 tools (some duplicates removed)
    assert len(tool_names) >= 38, f"Expected at least 38 tools, got {len(tool_names)}"
@pytest.mark.asyncio
async def test_tools_endpoint_returns_all_templates(client: AsyncClient) -> None:
    """Test that the /tools endpoint returns tools from all template modules."""
    # Act
    r = await client.get("/api/v1/ai/config/tools")

    # Assert
    assert r.status_code == 200, f"Unexpected status code: {r.status_code}"

    tools = r.json()
    assert isinstance(tools, list)

    # Verify we have a substantial number of tools from all modules
    # Should be at least 38 unique tools
    assert len(tools) >= 38, f"Expected at least 38 tools, got {len(tools)}"

    # Verify tool categories are present
    categories = {tool.get("category") for tool in tools}
    assert len(categories) > 1, "Expected tools from multiple categories"

    # Verify specific tools from each module are present
    tool_names = [tool.get("name") for tool in tools]

    # Check a sample from each module
    assert "list_projects" in tool_names, "Missing project_tools"
    assert "get_project_analysis" in tool_names, "Missing analysis_template"
    assert "create_change_order" in tool_names, "Missing change_order_template"
    assert "create_cost_element" in tool_names, "Missing cost_element_template"
    assert "find_users" in tool_names, "Missing user_management_template"
    assert "get_project_forecast" in tool_names, "Missing advanced_analysis_template"
    assert "generate_mermaid_diagram" in tool_names, "Missing diagram_template"
