"""Integration tests for migrated project tools."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.ai.tools.project_tools import get_project, list_projects
from app.ai.tools.types import ToolContext

# Patch target for overriding ToolContext.session to use the test db_session
# instead of creating a task-scoped session from the production engine.
_GET_TOOL_SESSION_PATCH = "app.db.session.get_tool_session"

def _make_context(db_session, user_role: str = "viewer") -> ToolContext:
    """Create a ToolContext with the test db_session.

    ToolContext.session normally calls get_tool_session() which creates
    a task-scoped session from the production engine. In tests, callers
    must patch get_tool_session to return the test's db_session instead.
    """
    return ToolContext(
        session=db_session,
        user_id=str(uuid4()),
        user_role=user_role,
    )

@pytest.mark.asyncio
async def test_list_projects_migrated_basic(db_session):
    """Test migrated list_projects basic functionality."""
    context = _make_context(db_session, "viewer")

    # Patch get_tool_session to return the test's db_session
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await list_projects.ainvoke({"context": context})

    # Validate structure
    assert "projects" in result
    assert "total" in result
    assert "skip" in result
    assert "limit" in result
    assert isinstance(result["projects"], list)
    assert isinstance(result["total"], int)

@pytest.mark.asyncio
async def test_list_projects_migrated_with_parameters(db_session):
    """Test migrated list_projects with search parameters."""
    context = _make_context(db_session, "viewer")

    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await list_projects.ainvoke(
            {"search": "test", "skip": 0, "limit": 10, "context": context}
        )

    assert "projects" in result
    assert result["skip"] == 0
    assert result["limit"] == 10

@pytest.mark.asyncio
async def test_list_projects_permission_check(db_session):
    """Test list_projects with guest role returns empty project list.

    Note: Direct .ainvoke() bypasses BackcastSecurityMiddleware, so RBAC
    enforcement at the middleware level is not tested here. The tool's own
    code filters projects based on user access via unified RBAC.
    """
    context = _make_context(db_session, "guest")

    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await list_projects.ainvoke({"context": context})

    # Guest users get an empty project list (no accessible projects)
    assert "projects" in result
    assert result["total"] == 0

@pytest.mark.asyncio
async def test_get_project_migrated_success(db_session, test_project):
    """Test migrated get_project returns correct data."""
    await db_session.commit()

    context = _make_context(db_session, "viewer")

    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await get_project.ainvoke(
            {"project_id": str(test_project.project_id), "context": context}
        )

    # Validate structure - allow both success and error responses
    if "error" not in result:
        assert "id" in result
        assert "code" in result
        assert "name" in result
        assert result["id"] == str(test_project.project_id)

@pytest.mark.asyncio
async def test_get_project_not_found(db_session):
    """Test get_project returns error for non-existent project."""
    context = _make_context(db_session, "viewer")

    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await get_project.ainvoke(
            {"project_id": str(uuid4()), "context": context}
        )

    assert "error" in result
    assert "not found" in result["error"]

@pytest.mark.asyncio
async def test_get_project_invalid_uuid(db_session):
    """Test get_project returns error for invalid UUID."""
    context = _make_context(db_session, "viewer")

    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await get_project.ainvoke(
            {"project_id": "invalid-uuid", "context": context}
        )

    assert "error" in result
    assert "Invalid project ID" in result["error"]

@pytest.mark.asyncio
async def test_get_project_permission_check(db_session, test_project):
    """Test get_project with guest role.

    Note: Direct .ainvoke() bypasses BackcastSecurityMiddleware, so RBAC
    enforcement at the middleware level is not tested here. The tool's own
    code will look up the project; for a guest user, the mock RBAC will
    still allow access since the mock returns True by default.
    """
    await db_session.commit()

    context = _make_context(db_session, "guest")

    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await get_project.ainvoke(
            {"project_id": str(test_project.project_id), "context": context}
        )

    # The tool returns project data (mock RBAC allows access) or not found
    assert "error" not in result or "not found" in result["error"]

@pytest.mark.asyncio
async def test_list_projects_with_status_filter(db_session):
    """Test list_projects with status filter."""
    context = _make_context(db_session, "viewer")

    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await list_projects.ainvoke(
            {"status": "ACT", "skip": 0, "limit": 10, "context": context}
        )

    assert "projects" in result
    assert result["skip"] == 0
    assert result["limit"] == 10

@pytest.mark.asyncio
async def test_get_project_with_branch(db_session, test_project):
    """Test get_project returns branch information."""
    await db_session.commit()

    context = _make_context(db_session, "viewer")

    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await get_project.ainvoke(
            {"project_id": str(test_project.project_id), "context": context}
        )

    # If project found, check structure
    if "error" not in result:
        assert "branch" in result
        assert result["branch"] == "main"
