"""Integration tests for Forecast, Cost Registration, and Progress Entry AI tools.

Tests verify:
- Tool discovery (all 13 tools are registered)
- Tool execution via LangGraph
- Permission verification
- End-to-end workflows
"""

from uuid import uuid4

import pytest

from app.ai.tools import create_project_tools
from app.ai.tools.templates.forecast_cost_progress_template import (
    compare_forecast_to_budget,
    create_cost_registration,
    create_forecast,
    create_progress_entry,
    get_budget_status,
    get_cost_element_summary,
    get_cost_trends,
    get_cumulative_costs,
    get_forecast,
    get_latest_progress,
    get_progress_history,
    list_cost_registrations,
    update_forecast,
)
from app.ai.tools.types import ToolContext
from app.core.rbac import RBACServiceABC

# =============================================================================
# Mock RBAC Service
# =============================================================================


class MockRBACService(RBACServiceABC):
    """Mock RBAC service that allows everything for testing."""

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        # Return all possible permissions for testing
        return [
            "forecast-read",
            "forecast-create",
            "forecast-update",
            "cost-registration-read",
            "cost-registration-create",
            "progress-entry-read",
            "progress-entry-create",
            "project-read",
            "project-create",
            "wbe-read",
            "wbe-create",
            "cost-element-read",
            "cost-element-create",
        ]

    # Project-level RBAC methods (mocked - allow all)
    async def has_project_access(
        self,
        user_id,
        user_role: str,
        project_id,
        required_permission: str,
    ) -> bool:
        return True

    async def get_user_projects(self, user_id, user_role: str) -> list:
        return []

    async def get_project_role(self, user_id, project_id) -> str | None:
        return None


@pytest.fixture(autouse=True)
def mock_rbac_service(monkeypatch):
    """Mock RBAC service for all integration tests."""

    def mock_get_rbac_service():
        return MockRBACService()

    # Monkey patch the get_rbac_service function in rbac module
    import app.core.rbac as rbac_module

    monkeypatch.setattr(
        rbac_module, "get_rbac_service", mock_get_rbac_service
    )


@pytest.mark.asyncio
async def test_all_tools_discoverable(db_session):
    """Test that all 13 forecast/cost/progress tools are discoverable via create_project_tools."""
    # Arrange
    context = ToolContext(
        session=db_session,
        user_id="test-user-id",
        user_role="admin",
    )

    # Act
    tools = create_project_tools(context)

    # Assert - All 13 tools should be discoverable
    tool_names = {tool.name for tool in tools}

    # Forecast tools (4)
    assert "get_forecast" in tool_names
    assert "create_forecast" in tool_names
    assert "update_forecast" in tool_names
    assert "compare_forecast_to_budget" in tool_names

    # Cost Registration tools (5)
    assert "get_budget_status" in tool_names
    assert "create_cost_registration" in tool_names
    assert "list_cost_registrations" in tool_names
    assert "get_cost_trends" in tool_names
    assert "get_cumulative_costs" in tool_names

    # Progress Entry tools (3)
    assert "get_latest_progress" in tool_names
    assert "create_progress_entry" in tool_names
    assert "get_progress_history" in tool_names

    # Summary tool (1)
    assert "get_cost_element_summary" in tool_names

    # Total count check (13 new tools)
    forecast_cost_progress_tools = {
        "get_forecast",
        "create_forecast",
        "update_forecast",
        "compare_forecast_to_budget",
        "get_budget_status",
        "create_cost_registration",
        "list_cost_registrations",
        "get_cost_trends",
        "get_cumulative_costs",
        "get_latest_progress",
        "create_progress_entry",
        "get_progress_history",
        "get_cost_element_summary",
    }
    assert forecast_cost_progress_tools.issubset(tool_names)


@pytest.mark.asyncio
async def test_tools_have_correct_permissions():
    """Test that all tools have correct permission scopes."""
    # Arrange - All 13 tools with their expected permissions
    expected_permissions = {
        "get_forecast": ["forecast-read"],
        "create_forecast": ["forecast-create"],
        "update_forecast": ["forecast-update"],
        "compare_forecast_to_budget": ["forecast-read", "cost-registration-read"],
        "get_budget_status": ["cost-registration-read"],
        "create_cost_registration": ["cost-registration-create"],
        "list_cost_registrations": ["cost-registration-read"],
        "get_cost_trends": ["cost-registration-read"],
        "get_cumulative_costs": ["cost-registration-read"],
        "get_latest_progress": ["progress-entry-read"],
        "create_progress_entry": ["progress-entry-create"],
        "get_progress_history": ["progress-entry-read"],
        "get_cost_element_summary": ["forecast-read", "cost-registration-read", "progress-entry-read"],
    }

    # Import all tools
    tools = {
        "get_forecast": get_forecast,
        "create_forecast": create_forecast,
        "update_forecast": update_forecast,
        "compare_forecast_to_budget": compare_forecast_to_budget,
        "get_budget_status": get_budget_status,
        "create_cost_registration": create_cost_registration,
        "list_cost_registrations": list_cost_registrations,
        "get_cost_trends": get_cost_trends,
        "get_cumulative_costs": get_cumulative_costs,
        "get_latest_progress": get_latest_progress,
        "create_progress_entry": create_progress_entry,
        "get_progress_history": get_progress_history,
        "get_cost_element_summary": get_cost_element_summary,
    }

    # Act & Assert - Verify each tool has correct permissions
    for tool_name, tool in tools.items():
        expected = expected_permissions[tool_name]
        # Decorator stores permissions in _tool_metadata.permissions
        assert hasattr(tool, "_tool_metadata"), f"{tool_name} should have _tool_metadata"
        assert tool._tool_metadata.permissions == expected, f"{tool_name} has incorrect permissions: {tool._tool_metadata.permissions} != {expected}"


@pytest.mark.asyncio
async def test_tool_execution_via_langgraph(db_session, test_cost_element):
    """Test that tools can be executed through LangGraph's invoke pattern."""
    # Arrange
    context = ToolContext(
        session=db_session,
        user_id="test-user-id",
        user_role="admin",
    )

    # Create a forecast for testing (or use existing)
    from decimal import Decimal

    from app.services.forecast_service import ForecastService

    service = ForecastService(db_session)

    # Check if forecast exists, delete if it does
    existing = await service.get_for_cost_element(
        test_cost_element.cost_element_id, branch="main"
    )
    if existing:
        await service.soft_delete(
            forecast_id=existing.forecast_id,
            actor_id=uuid4(),
            branch="main",
        )
        await db_session.flush()

    await service.create_for_cost_element(
        cost_element_id=test_cost_element.cost_element_id,
        actor_id=uuid4(),
        branch="main",
        eac_amount=Decimal("110000.00"),
        basis_of_estimate="Test forecast",
    )
    await db_session.commit()

    # Act - Call get_forecast via LangGraph's ainvoke pattern
    result = await get_forecast.ainvoke({
        "cost_element_id": str(test_cost_element.cost_element_id),
        "context": context,
    })

    # Assert
    assert "error" not in result
    assert "id" in result
    assert "eac_amount" in result
    assert result["eac_amount"] == 110000.00


@pytest.mark.asyncio
async def test_end_to_end_summary_workflow(db_session, test_cost_element):
    """Test end-to-end workflow using get_cost_element_summary."""
    # Arrange
    from decimal import Decimal

    from app.models.schemas.progress_entry import ProgressEntryCreate
    from app.services.forecast_service import ForecastService
    from app.services.progress_entry_service import ProgressEntryService

    context = ToolContext(
        session=db_session,
        user_id="test-user-id",
        user_role="admin",
    )

    # Create forecast (handle existing forecast)
    forecast_service = ForecastService(db_session)
    existing = await forecast_service.get_for_cost_element(
        test_cost_element.cost_element_id, branch="main"
    )
    if existing:
        await forecast_service.soft_delete(
            forecast_id=existing.forecast_id,
            actor_id=uuid4(),
            branch="main",
        )
        await db_session.flush()

    await forecast_service.create_for_cost_element(
        cost_element_id=test_cost_element.cost_element_id,
        actor_id=uuid4(),
        branch="main",
        eac_amount=Decimal("120000.00"),
        basis_of_estimate="E2E test forecast",
    )

    # Create progress entry
    progress_service = ProgressEntryService(db_session)
    progress_in = ProgressEntryCreate(
        cost_element_id=test_cost_element.cost_element_id,
        progress_percentage=Decimal("75.00"),
        notes="E2E test progress",
    )
    await progress_service.create(
        actor_id=uuid4(),
        progress_in=progress_in,
    )

    await db_session.commit()

    # Act - Get complete summary
    result = await get_cost_element_summary.ainvoke({
        "cost_element_id": str(test_cost_element.cost_element_id),
        "context": context,
    })

    # Assert - Summary should include all three data types
    assert "error" not in result
    assert "cost_element_id" in result
    assert "forecast" in result
    assert "budget_status" in result
    assert "progress" in result

    # Verify forecast data
    assert result["forecast"] is not None
    assert result["forecast"]["eac_amount"] == 120000.00

    # Verify budget status data
    assert result["budget_status"] is not None
    assert "budget" in result["budget_status"]
    assert "used" in result["budget_status"]

    # Verify progress data
    assert result["progress"] is not None
    assert result["progress"]["progress_percentage"] == 75.00
