"""Integration tests for Forecast, Cost Registration, and Progress Entry AI tools.

Tests verify:
- Tool discovery (all 10 tools are registered)
- Tool execution via LangGraph
- Permission verification
- End-to-end workflows
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.ai.tools import create_project_tools
from app.ai.tools.templates.forecast_cost_progress_template import (
    batch_create_cost_registrations,
    batch_create_progress_entries,
    create_cost_registration,
    create_forecast,
    create_progress_entry,
    delete_cost_registration,
    get_cost_element_details,
    get_progress_data,
    update_cost_registration,
    update_forecast,
)
from app.ai.tools.types import ToolContext
from app.core.rbac_unified import set_unified_rbac_service
from tests.conftest import MockUnifiedRBACService


@pytest.fixture(autouse=True)
def mock_rbac_service():
    """Mock RBAC service for all integration tests."""
    set_unified_rbac_service(MockUnifiedRBACService())


@pytest.mark.asyncio
async def test_all_tools_discoverable(db_session):
    """Test that all 10 forecast/cost/progress tools are discoverable via create_project_tools."""
    # Arrange
    context = ToolContext(
        session=db_session,
        user_id="test-user-id",
        user_role="admin",
    )

    # Act
    tools = create_project_tools(context)

    # Assert - All 10 tools should be discoverable
    tool_names = {tool.name for tool in tools}

    # Forecast tools (2)
    assert "create_forecast" in tool_names
    assert "update_forecast" in tool_names

    # Cost Registration tools (4)
    assert "create_cost_registration" in tool_names
    assert "update_cost_registration" in tool_names
    assert "delete_cost_registration" in tool_names
    assert "batch_create_cost_registrations" in tool_names

    # Progress Entry tools (2)
    assert "create_progress_entry" in tool_names
    assert "batch_create_progress_entries" in tool_names

    # Consolidated read tools (2)
    assert "get_cost_element_details" in tool_names
    assert "get_progress_data" in tool_names

    # Total count check (10 tools)
    forecast_cost_progress_tools = {
        "create_forecast",
        "update_forecast",
        "create_cost_registration",
        "update_cost_registration",
        "delete_cost_registration",
        "batch_create_cost_registrations",
        "create_progress_entry",
        "batch_create_progress_entries",
        "get_cost_element_details",
        "get_progress_data",
    }
    assert forecast_cost_progress_tools.issubset(tool_names)


@pytest.mark.asyncio
async def test_tools_have_correct_permissions():
    """Test that all tools have correct permission scopes."""
    # Arrange - All 10 tools with their expected permissions
    expected_permissions = {
        "create_forecast": ["forecast-create"],
        "update_forecast": ["forecast-update"],
        "create_cost_registration": ["cost-registration-create"],
        "update_cost_registration": ["cost-registration-update"],
        "delete_cost_registration": ["cost-registration-delete"],
        "batch_create_cost_registrations": ["cost-registration-create"],
        "create_progress_entry": ["progress-entry-create"],
        "batch_create_progress_entries": ["progress-entry-create"],
        "get_cost_element_details": ["forecast-read", "cost-registration-read"],
        "get_progress_data": ["progress-entry-read"],
    }

    # Import all tools
    tools = {
        "create_forecast": create_forecast,
        "update_forecast": update_forecast,
        "create_cost_registration": create_cost_registration,
        "update_cost_registration": update_cost_registration,
        "delete_cost_registration": delete_cost_registration,
        "batch_create_cost_registrations": batch_create_cost_registrations,
        "create_progress_entry": create_progress_entry,
        "batch_create_progress_entries": batch_create_progress_entries,
        "get_cost_element_details": get_cost_element_details,
        "get_progress_data": get_progress_data,
    }

    # Act & Assert - Verify each tool has correct permissions
    for tool_name, tool in tools.items():
        expected = expected_permissions[tool_name]
        # Decorator stores permissions in _tool_metadata.permissions
        assert hasattr(tool, "_tool_metadata"), (
            f"{tool_name} should have _tool_metadata"
        )
        assert tool._tool_metadata.permissions == expected, (
            f"{tool_name} has incorrect permissions: {tool._tool_metadata.permissions} != {expected}"
        )


@pytest.mark.asyncio
async def test_tool_execution_via_langgraph(db_session, test_cost_element):
    """Test that tools can be executed through LangGraph's invoke pattern."""
    # Arrange
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

    # Patch get_tool_session to return the test's db_session so that
    # ToolContext.session property uses the same session that has the data.
    with patch("app.db.session.get_tool_session", return_value=db_session):
        context = ToolContext(
            session=db_session,
            user_id="test-user-id",
            user_role="admin",
        )

        # Act - Call get_cost_element_details via LangGraph's ainvoke pattern
        result = await get_cost_element_details.ainvoke(
            {
                "cost_element_id": str(test_cost_element.cost_element_id),
                "context": context,
            }
        )

    # Assert
    assert "error" not in result
    assert "forecast" in result
    assert result["forecast"] is not None
    assert result["forecast"]["eac_amount"] == 110000.00


@pytest.mark.asyncio
async def test_end_to_end_summary_workflow(db_session, test_cost_element):
    """Test end-to-end workflow using get_cost_element_details."""
    # Arrange
    from decimal import Decimal

    from app.models.schemas.progress_entry import ProgressEntryCreate
    from app.services.forecast_service import ForecastService
    from app.services.progress_entry_service import ProgressEntryService

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

    # Patch get_tool_session to return the test's db_session so that
    # ToolContext.session property uses the same session that has the data.
    with patch("app.db.session.get_tool_session", return_value=db_session):
        context = ToolContext(
            session=db_session,
            user_id="test-user-id",
            user_role="admin",
        )

        # Act - Get complete details via consolidated tool
        result = await get_cost_element_details.ainvoke(
            {
                "cost_element_id": str(test_cost_element.cost_element_id),
                "context": context,
            }
        )

    # Assert - Summary should include forecast and budget_status
    assert "error" not in result
    assert "forecast" in result
    assert "budget_status" in result
    assert "cost_registrations" in result

    # Verify forecast data
    assert result["forecast"] is not None
    assert result["forecast"]["eac_amount"] == 120000.00

    # Verify budget status data
    assert result["budget_status"] is not None
    assert "budget_amount" in result["budget_status"]
    assert "used" in result["budget_status"]

    # Verify progress via separate tool
    with patch("app.db.session.get_tool_session", return_value=db_session):
        progress_result = await get_progress_data.ainvoke(
            {
                "cost_element_id": str(test_cost_element.cost_element_id),
                "context": context,
            }
        )

    assert "error" not in progress_result
    assert progress_result["latest_progress"] is not None
    assert progress_result["latest_progress"]["progress_percentage"] == 75.00
