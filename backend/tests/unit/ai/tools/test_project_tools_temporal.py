"""Unit tests for project_tools temporal context integration.

Tests temporal logging and metadata additions to project tools.

These tests verify that:
1. Temporal context is logged when tools execute
2. Temporal metadata is added to tool results
3. Existing result fields are preserved
"""

import logging
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.ai.tools.types import ToolContext
from app.core.rbac_unified import set_unified_rbac_service, set_unified_rbac_session

TEMPORAL_LOGGER = "app.ai.tools.temporal_logging"


@pytest.fixture(autouse=True)
def _ensure_temporal_logger_enabled():
    """Ensure the temporal_logging logger is enabled during tests.

    caplog.at_level() can leave loggers in a disabled=True state after
    teardown, which prevents subsequent tests from capturing any output.
    """
    logger = logging.getLogger(TEMPORAL_LOGGER)
    original_level = logger.level
    original_disabled = logger.disabled
    logger.setLevel(logging.INFO)
    logger.disabled = False
    logger.propagate = True
    yield
    logger.setLevel(original_level)
    logger.disabled = original_disabled


@pytest.fixture
def mock_tool_context():
    """Create a mock ToolContext with temporal parameters."""
    context = MagicMock(spec=ToolContext)
    context.user_id = str(uuid4())
    context.user_role = "project_manager"
    context.project_id = None
    context.branch_id = None
    context.as_of = None
    context.branch_name = "main"
    context.branch_mode = "merged"
    context._permission_cache = {}
    context.session = AsyncMock()
    context._root_session = AsyncMock()
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
    context.project_id = None
    context.branch_id = None
    context.as_of = datetime(2025, 6, 15, 12, 0, 0)
    context.branch_name = "feature-branch-1"
    context.branch_mode = "isolated"
    context._permission_cache = {}
    context.session = AsyncMock()
    context._root_session = AsyncMock()
    context.project_service = AsyncMock()
    return context


def _make_log_handler() -> tuple[logging.StreamHandler, list[str]]:
    """Create a log handler that captures log messages into a list."""
    records: list[str] = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(self.format(record))

    handler = ListHandler()
    handler.setLevel(logging.INFO)
    return handler, records


def _setup_unified_rbac_mock(
    accessible_projects: list[str] | None = None,
    has_permission: bool = True,
) -> MagicMock:
    """Create and inject a mock UnifiedRBACService.

    Args:
        accessible_projects: List of project ID strings to return.
        has_permission: Whether has_permission returns True.

    Returns:
        The mock service that was injected.
    """
    mock_service = MagicMock()
    mock_service.get_accessible_projects = AsyncMock(
        return_value=accessible_projects or []
    )
    mock_service.has_permission = AsyncMock(return_value=has_permission)
    mock_service.has_project_access = AsyncMock(return_value=has_permission)
    set_unified_rbac_service(mock_service)
    set_unified_rbac_session(AsyncMock())
    return mock_service


def _cleanup_unified_rbac() -> None:
    """Reset unified RBAC service and session after test."""
    set_unified_rbac_service(None)  # type: ignore[arg-type]
    set_unified_rbac_session(None)


@pytest.mark.asyncio
async def test_list_projects_logs_temporal_context(mock_tool_context):
    """Test that list_projects logs temporal context at tool start."""
    from app.ai.tools.project_tools import list_projects

    _setup_unified_rbac_mock(accessible_projects=[])
    handler, records = _make_log_handler()
    logger = logging.getLogger(TEMPORAL_LOGGER)
    logger.addHandler(handler)

    try:
        await list_projects.ainvoke(
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

        output = "\n".join(records)
        assert "TEMPORAL_CONTEXT" in output
        assert "list_projects" in output
        assert "as_of=None (current time)" in output
        assert "branch=main" in output
        assert "mode=merged" in output
    finally:
        logger.removeHandler(handler)
        _cleanup_unified_rbac()


@pytest.mark.asyncio
async def test_list_projects_logs_temporal_context_with_params(
    mock_tool_context_with_temporal_params,
):
    """Test that list_projects logs non-default temporal parameters."""
    from app.ai.tools.project_tools import list_projects

    _setup_unified_rbac_mock(accessible_projects=[])
    handler, records = _make_log_handler()
    logger = logging.getLogger(TEMPORAL_LOGGER)
    logger.addHandler(handler)

    try:
        mock_project = MagicMock()
        mock_project.project_id = str(uuid4())
        mock_project.code = "PRJ001"
        mock_project.name = "Test Project"
        mock_project.description = "Test"
        mock_project.status = "ACT"
        mock_project.budget = 100000.0
        mock_project.start_date = None
        mock_project.end_date = None

        mock_tool_context_with_temporal_params.project_service.get_projects = AsyncMock(
            return_value=([mock_project], 1)
        )

        await list_projects.ainvoke(
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

        output = "\n".join(records)
        assert "TEMPORAL_CONTEXT" in output
        assert "2025-06-15" in output
        assert "branch=feature-branch-1" in output
        assert "mode=isolated" in output
    finally:
        logger.removeHandler(handler)
        _cleanup_unified_rbac()


@pytest.mark.asyncio
async def test_list_projects_adds_temporal_metadata_to_result(mock_tool_context):
    """Test that list_projects adds temporal metadata to results."""
    from app.ai.tools.project_tools import list_projects

    _setup_unified_rbac_mock(accessible_projects=[str(uuid4())])

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

    try:
        result = await list_projects.ainvoke(
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
    finally:
        _cleanup_unified_rbac()

    assert "_temporal_context" in result
    assert result["_temporal_context"]["as_of"] is None
    assert result["_temporal_context"]["branch_name"] == "main"
    assert result["_temporal_context"]["branch_mode"] == "merged"


@pytest.mark.asyncio
async def test_list_projects_preserves_existing_result_fields(mock_tool_context):
    """Test that temporal metadata addition preserves existing result fields."""
    from app.ai.tools.project_tools import list_projects

    _setup_unified_rbac_mock(accessible_projects=[str(uuid4())])

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

    try:
        result = await list_projects.ainvoke(
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
    finally:
        _cleanup_unified_rbac()

    assert "projects" in result
    assert "total" in result
    assert "skip" in result
    assert "limit" in result
    assert "_temporal_context" in result


@pytest.mark.asyncio
async def test_get_project_logs_temporal_context(mock_tool_context):
    """Test that get_project logs temporal context at tool start."""
    from app.ai.tools.project_tools import get_project

    _setup_unified_rbac_mock(has_permission=True)

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

    handler, records = _make_log_handler()
    logger = logging.getLogger(TEMPORAL_LOGGER)
    logger.addHandler(handler)

    try:
        await get_project.ainvoke(
            {
                "project_id": str(mock_project.project_id),
                "context": mock_tool_context,
            }
        )

        output = "\n".join(records)
        assert "TEMPORAL_CONTEXT" in output
        assert "get_project" in output
        assert "as_of=None (current time)" in output
        assert "branch=main" in output
        assert "mode=merged" in output
    finally:
        logger.removeHandler(handler)
        _cleanup_unified_rbac()


@pytest.mark.asyncio
async def test_get_project_adds_temporal_metadata_to_result(mock_tool_context):
    """Test that get_project adds temporal metadata to results."""
    from app.ai.tools.project_tools import get_project

    _setup_unified_rbac_mock(has_permission=True)

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

    try:
        result = await get_project.ainvoke(
            {"project_id": str(mock_project.project_id), "context": mock_tool_context}
        )
    finally:
        _cleanup_unified_rbac()

    assert "_temporal_context" in result
    assert result["_temporal_context"]["as_of"] is None
    assert result["_temporal_context"]["branch_name"] == "main"
    assert result["_temporal_context"]["branch_mode"] == "merged"


@pytest.mark.asyncio
async def test_get_project_preserves_existing_result_fields(mock_tool_context):
    """Test that temporal metadata addition preserves existing result fields."""
    from app.ai.tools.project_tools import get_project

    _setup_unified_rbac_mock(has_permission=True)

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

    try:
        result = await get_project.ainvoke(
            {"project_id": str(mock_project.project_id), "context": mock_tool_context}
        )
    finally:
        _cleanup_unified_rbac()

    assert "id" in result
    assert "code" in result
    assert "name" in result
    assert "description" in result
    assert "status" in result
    assert "budget" in result
    assert "branch" in result
    assert "_temporal_context" in result


@pytest.mark.asyncio
async def test_get_project_handles_not_found(mock_tool_context):
    """Test that get_project handles project not found with temporal metadata."""
    from app.ai.tools.project_tools import get_project

    _setup_unified_rbac_mock(has_permission=True)

    mock_tool_context.project_service.get_as_of = AsyncMock(return_value=None)

    try:
        result = await get_project.ainvoke(
            {"project_id": str(uuid4()), "context": mock_tool_context}
        )
    finally:
        _cleanup_unified_rbac()

    assert "error" in result
    assert "_temporal_context" in result
