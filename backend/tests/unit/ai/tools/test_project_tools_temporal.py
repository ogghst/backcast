"""Unit tests for project_tools temporal context integration.

Tests temporal logging and metadata additions to project tools.

These tests verify that:
1. Temporal context is logged when tools execute
2. Temporal metadata is added to tool results
3. Existing result fields are preserved
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.ai.tools.types import ToolContext


@pytest.fixture
def mock_tool_context():
    """Create a mock ToolContext with temporal parameters."""
    context = MagicMock(spec=ToolContext)
    context.user_id = str(uuid4())
    context.user_role = "project_manager"
    context.as_of = None  # Current time
    context.branch_name = "main"
    context.branch_mode = "merged"
    context._permission_cache = {}

    # Mock session
    context.session = AsyncMock()

    # Mock project_service
    context.project_service = AsyncMock()
    context.project_service.get_projects = AsyncMock(return_value=([], 0))
    context.project_service.get_as_of = AsyncMock(return_value=None)

    return context


@pytest.fixture
def mock_tool_context_with_temporal_params():
    """Create a mock ToolContext with non-default temporal parameters."""
    from datetime import datetime

    context = MagicMock(spec=ToolContext)
    context.user_id = str(uuid4())
    context.user_role = "project_manager"
    context.as_of = datetime(2025, 6, 15, 12, 0, 0)
    context.branch_name = "feature-branch-1"
    context.branch_mode = "isolated"
    context._permission_cache = {}

    # Mock session
    context.session = AsyncMock()

    # Mock project_service
    context.project_service = AsyncMock()

    return context


@pytest.mark.asyncio
async def test_list_projects_logs_temporal_context(
    mock_tool_context, caplog
):
    """Test that list_projects logs temporal context at tool start."""
    # Import after all mocks are set up
    from app.ai.tools.project_tools import list_projects

    # Mock RBAC service
    with patch("app.core.rbac.get_rbac_service") as mock_rbac:
        mock_rbac_service = AsyncMock()
        mock_rbac_service.get_user_projects = AsyncMock(return_value=[])
        mock_rbac_service.session = None
        mock_rbac.return_value = mock_rbac_service

        with caplog.at_level(logging.INFO):
            # Invoke the tool
            await list_projects.ainvoke(  # type: ignore
                {
                    "search": None,
                    "status": None,
                    "skip": 0,
                    "limit": 10,
                    "sort_field": None,
                    "sort_order": "asc",
                    "context": mock_tool_context,
                }
            )

    # Verify temporal context was logged
    temporal_logs = [
        record
        for record in caplog.records
        if "TEMPORAL_CONTEXT" in record.message
        and "list_projects" in record.message
    ]
    assert len(temporal_logs) >= 1, "Temporal context should be logged"
    assert "as_of=None (current time)" in temporal_logs[0].message
    assert "branch=main" in temporal_logs[0].message
    assert "mode=merged" in temporal_logs[0].message


@pytest.mark.asyncio
async def test_list_projects_logs_temporal_context_with_params(
    mock_tool_context_with_temporal_params, caplog
):
    """Test that list_projects logs non-default temporal parameters."""
    from app.ai.tools.project_tools import list_projects

    # Mock RBAC service
    with patch("app.core.rbac.get_rbac_service") as mock_rbac:
        mock_rbac_service = AsyncMock()
        mock_rbac_service.get_user_projects = AsyncMock(return_value=[])
        mock_rbac_service.session = None
        mock_rbac.return_value = mock_rbac_service

        # Mock project service to return test data
        mock_project = MagicMock()
        mock_project.project_id = str(uuid4())
        mock_project.code = "PRJ001"
        mock_project.name = "Test Project"
        mock_project.description = "Test"
        mock_project.status = "ACT"
        mock_project.budget = 100000.0
        mock_project.start_date = None
        mock_project.end_date = None

        mock_tool_context_with_temporal_params.project_service.get_projects = (
            AsyncMock(return_value=([mock_project], 1))
        )

        with caplog.at_level(logging.INFO):
            await list_projects.ainvoke(  # type: ignore
                {
                    "search": None,
                    "status": None,
                    "skip": 0,
                    "limit": 10,
                    "sort_field": None,
                    "sort_order": "asc",
                    "context": mock_tool_context_with_temporal_params,
                }
            )

    # Verify temporal context was logged with correct values
    temporal_logs = [
        record
        for record in caplog.records
        if "TEMPORAL_CONTEXT" in record.message
        and "list_projects" in record.message
    ]
    assert len(temporal_logs) >= 1
    assert "2025-06-15" in temporal_logs[0].message
    assert "branch=feature-branch-1" in temporal_logs[0].message
    assert "mode=isolated" in temporal_logs[0].message


@pytest.mark.asyncio
async def test_list_projects_adds_temporal_metadata_to_result(mock_tool_context):
    """Test that list_projects adds temporal metadata to results."""
    from app.ai.tools.project_tools import list_projects

    # Mock RBAC service
    with patch("app.core.rbac.get_rbac_service") as mock_rbac:
        mock_rbac_service = AsyncMock()
        mock_rbac_service.get_user_projects = AsyncMock(return_value=[str(uuid4())])
        mock_rbac_service.session = None
        mock_rbac.return_value = mock_rbac_service

        # Mock project service to return test data
        mock_project = MagicMock()
        mock_project.project_id = str(uuid4())
        mock_project.code = "PRJ001"
        mock_project.name = "Test Project"
        mock_project.description = "Test"
        mock_project.status = "ACT"
        mock_project.budget = 100000.0
        mock_project.start_date = None
        mock_project.end_date = None

        mock_tool_context.project_service.get_projects = AsyncMock(
            return_value=([mock_project], 1)
        )

        result = await list_projects.ainvoke(  # type: ignore
            {
                "search": None,
                "status": None,
                "skip": 0,
                "limit": 10,
                "sort_field": None,
                "sort_order": "asc",
                "context": mock_tool_context,
            }
        )

    # Verify temporal metadata is in result
    assert "_temporal_context" in result
    assert result["_temporal_context"]["as_of"] is None
    assert result["_temporal_context"]["branch"] == "main"
    assert result["_temporal_context"]["mode"] == "merged"


@pytest.mark.asyncio
async def test_list_projects_preserves_existing_result_fields(mock_tool_context):
    """Test that temporal metadata addition preserves existing result fields."""
    from app.ai.tools.project_tools import list_projects

    # Mock RBAC service
    with patch("app.core.rbac.get_rbac_service") as mock_rbac:
        mock_rbac_service = AsyncMock()
        mock_rbac_service.get_user_projects = AsyncMock(return_value=[str(uuid4())])
        mock_rbac_service.session = None
        mock_rbac.return_value = mock_rbac_service

        # Mock project service to return test data
        mock_project = MagicMock()
        mock_project.project_id = str(uuid4())
        mock_project.code = "PRJ001"
        mock_project.name = "Test Project"
        mock_project.description = "Test"
        mock_project.status = "ACT"
        mock_project.budget = 100000.0
        mock_project.start_date = None
        mock_project.end_date = None

        mock_tool_context.project_service.get_projects = AsyncMock(
            return_value=([mock_project], 1)
        )

        result = await list_projects.ainvoke(  # type: ignore
            {
                "search": None,
                "status": None,
                "skip": 0,
                "limit": 10,
                "sort_field": None,
                "sort_order": "asc",
                "context": mock_tool_context,
            }
        )

    # Verify all expected fields are present
    assert "projects" in result
    assert "total" in result
    assert "skip" in result
    assert "limit" in result
    assert "_temporal_context" in result


@pytest.mark.asyncio
async def test_get_project_logs_temporal_context(mock_tool_context, caplog):
    """Test that get_project logs temporal context at tool start."""
    from app.ai.tools.project_tools import get_project

    # Mock project service to return test data
    mock_project = MagicMock()
    mock_project.project_id = str(uuid4())
    mock_project.code = "PRJ001"
    mock_project.name = "Test Project"
    mock_project.description = "Test"
    mock_project.status = "ACT"
    mock_project.budget = 100000.0
    mock_project.start_date = None
    mock_project.end_date = None
    mock_project.branch = "main"

    mock_tool_context.project_service.get_as_of = AsyncMock(return_value=mock_project)

    # Mock RBAC to allow project-read
    with patch("app.core.rbac.get_rbac_service") as mock_rbac:
        mock_rbac_service = AsyncMock()
        mock_rbac_service.has_permission = AsyncMock(return_value=True)
        mock_rbac.return_value = mock_rbac_service

        with caplog.at_level(logging.INFO):
            await get_project.ainvoke(  # type: ignore
                {"project_id": str(mock_project.project_id), "context": mock_tool_context}
            )

    # Verify temporal context was logged
    temporal_logs = [
        record
        for record in caplog.records
        if "TEMPORAL_CONTEXT" in record.message and "get_project" in record.message
    ]
    assert len(temporal_logs) >= 1, "Temporal context should be logged"
    assert "as_of=None (current time)" in temporal_logs[0].message
    assert "branch=main" in temporal_logs[0].message
    assert "mode=merged" in temporal_logs[0].message


@pytest.mark.asyncio
async def test_get_project_adds_temporal_metadata_to_result(mock_tool_context):
    """Test that get_project adds temporal metadata to results."""
    from app.ai.tools.project_tools import get_project

    # Mock project service to return test data
    mock_project = MagicMock()
    mock_project.project_id = str(uuid4())
    mock_project.code = "PRJ001"
    mock_project.name = "Test Project"
    mock_project.description = "Test"
    mock_project.status = "ACT"
    mock_project.budget = 100000.0
    mock_project.start_date = None
    mock_project.end_date = None
    mock_project.branch = "main"

    mock_tool_context.project_service.get_as_of = AsyncMock(return_value=mock_project)

    # Mock RBAC to allow project-read
    with patch("app.core.rbac.get_rbac_service") as mock_rbac:
        mock_rbac_service = AsyncMock()
        mock_rbac_service.has_permission = AsyncMock(return_value=True)
        mock_rbac.return_value = mock_rbac_service

        result = await get_project.ainvoke(  # type: ignore
            {"project_id": str(mock_project.project_id), "context": mock_tool_context}
        )

    # Verify temporal metadata is in result
    assert "_temporal_context" in result
    assert result["_temporal_context"]["as_of"] is None
    assert result["_temporal_context"]["branch"] == "main"
    assert result["_temporal_context"]["mode"] == "merged"


@pytest.mark.asyncio
async def test_get_project_preserves_existing_result_fields(mock_tool_context):
    """Test that temporal metadata addition preserves existing result fields."""
    from app.ai.tools.project_tools import get_project

    # Mock project service to return test data
    mock_project = MagicMock()
    mock_project.project_id = str(uuid4())
    mock_project.code = "PRJ001"
    mock_project.name = "Test Project"
    mock_project.description = "Test"
    mock_project.status = "ACT"
    mock_project.budget = 100000.0
    mock_project.start_date = None
    mock_project.end_date = None
    mock_project.branch = "main"

    mock_tool_context.project_service.get_as_of = AsyncMock(return_value=mock_project)

    # Mock RBAC to allow project-read
    with patch("app.core.rbac.get_rbac_service") as mock_rbac:
        mock_rbac_service = AsyncMock()
        mock_rbac_service.has_permission = AsyncMock(return_value=True)
        mock_rbac.return_value = mock_rbac_service

        result = await get_project.ainvoke(  # type: ignore
            {"project_id": str(mock_project.project_id), "context": mock_tool_context}
        )

    # Verify all expected fields are present
    assert "id" in result
    assert "code" in result
    assert "name" in result
    assert "description" in result
    assert "status" in result
    assert "budget" in result
    assert "branch" in result
    assert "_temporal_context" in result


@pytest.mark.asyncio
async def test_get_project_handles_not_found(mock_tool_context, caplog):
    """Test that get_project handles project not found with temporal metadata."""
    from app.ai.tools.project_tools import get_project

    # Mock project service to return None
    mock_tool_context.project_service.get_as_of = AsyncMock(return_value=None)

    # Mock RBAC to allow project-read
    with patch("app.core.rbac.get_rbac_service") as mock_rbac:
        mock_rbac_service = AsyncMock()
        mock_rbac_service.has_permission = AsyncMock(return_value=True)
        mock_rbac.return_value = mock_rbac_service

        with caplog.at_level(logging.INFO):
            result = await get_project.ainvoke(  # type: ignore
                {"project_id": str(uuid4()), "context": mock_tool_context}
            )

    # Verify error response includes temporal metadata
    assert "error" in result
    assert "_temporal_context" in result
