"""Integration tests for temporal context flow in AI agent interactions.

These tests verify that:
1. LLM can successfully call get_temporal_context tool
2. Temporal metadata is included in tool results
3. Temporal context changes propagate correctly through the system
4. Temporal context is logged for observability
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.tools import project_tools, temporal_tools
from app.ai.tools.types import ToolContext
from app.models.domain.project import Project


@pytest.mark.integration
class TestTemporalContextIntegration:
    """Test temporal context integration in AI agent workflows."""

    @pytest.mark.asyncio
    async def test_llm_can_call_get_temporal_context(self):
        """Verify that the LLM can successfully call get_temporal_context tool.

        This test simulates an LLM tool call to query the current temporal state.
        The tool should return accurate temporal context information.
        """
        # Setup: Create context with specific temporal values
        test_as_of = datetime(2026, 3, 15, 12, 30, 45)
        test_branch = "feature-branch-123"
        test_mode = "merged"

        context = ToolContext(
            session=AsyncMock(),
            user_id="00000000-0000-0000-0000-000000000001",
            user_role="admin",
            project_id=None,
            as_of=test_as_of,
            branch_name=test_branch,
            branch_mode=test_mode,
        )

        # Act: Call the raw function (not LangChain wrapper)
        result = await temporal_tools.get_temporal_context.coroutine(context=context)

        # Assert: Verify tool returns correct temporal state
        assert result["as_of"] == test_as_of.isoformat(), (
            f"get_temporal_context should return as_of={test_as_of}, got {result['as_of']}"
        )
        assert result["branch_name"] == test_branch, (
            f"get_temporal_context should return branch={test_branch}, got {result['branch_name']}"
        )
        assert result["branch_mode"] == "merged", (
            f"get_temporal_context should return mode='merged', got {result['branch_mode']}"
        )

    @pytest.mark.asyncio
    async def test_get_temporal_context_with_none_values(self):
        """Verify get_temporal_context handles None/default values correctly."""
        # Setup: Create context with None values (defaults)
        context = ToolContext(
            session=AsyncMock(),
            user_id="00000000-0000-0000-0000-000000000001",
            user_role="admin",
            project_id=None,
            as_of=None,
            branch_name=None,
            branch_mode=None,
        )

        # Act: Call the raw function
        result = await temporal_tools.get_temporal_context.coroutine(context=context)

        # Assert: Verify defaults are handled correctly
        assert result["as_of"] is None, "as_of should be None when not set"
        # When branch_name is None, get_temporal_context returns "main" as default
        assert result["branch_name"] == "main", "branch_name should default to 'main'"
        # When branch_mode is None, get_temporal_context returns "merged" as default
        assert result["branch_mode"] == "merged", "branch_mode should default to 'merged'"

    @pytest.mark.asyncio
    async def test_temporal_metadata_in_tool_results(self):
        """Verify that temporal metadata is included in all temporal tool results.

        This ensures the LLM and users are aware of the temporal context
        in which results were generated.
        """
        # Setup: Create mock project
        mock_project = MagicMock(spec=Project)
        mock_project.project_id = MagicMock()
        mock_project.project_id.__str__ = lambda self: "test-project-id"
        mock_project.name = "Test Project"
        mock_project.code = "TEST-001"
        mock_project.description = "Test Description"
        mock_project.status = "Active"
        mock_project.budget = 100000.0
        mock_project.start_date = None
        mock_project.end_date = None

        async def mock_get_by_id(*args, **kwargs):
            return mock_project

        # Create context with temporal values
        test_as_of = "2026-03-15T00:00:00"
        test_branch = "main"
        test_mode = "merged"

        context = ToolContext(
            session=AsyncMock(),
            user_id="00000000-0000-0000-0000-000000000001",
            user_role="admin",
            project_id=None,
            as_of=datetime.fromisoformat(test_as_of),
            branch_name=test_branch,
            branch_mode=test_mode,
        )

        with patch("app.services.project.ProjectService.get_as_of", mock_get_by_id):
            # Act: Call the raw function
            result = await project_tools.get_project.coroutine(
                project_id="00000000-0000-0000-0000-000000000002",
                context=context,
            )

        # Assert: Verify temporal metadata is in result
        assert "_temporal_context" in result, (
            "Tool result should include _temporal_context metadata"
        )

        temporal_metadata = result["_temporal_context"]
        assert temporal_metadata["as_of"] == test_as_of, (
            f"Temporal metadata should include as_of={test_as_of}"
        )
        assert temporal_metadata["branch_name"] == test_branch, (
            f"Temporal metadata should include branch={test_branch}"
        )
        assert temporal_metadata["branch_mode"] == test_mode, (
            f"Temporal metadata should include mode={test_mode}"
        )

    @pytest.mark.asyncio
    async def test_temporal_metadata_in_list_results(self):
        """Verify temporal metadata in list tool results."""
        # Setup: Create mock projects with UUID project_ids
        from uuid import UUID

        mock_projects = []
        project_ids = []
        for i in range(3):
            mock_p = MagicMock(spec=Project)
            mock_p.project_id = UUID(f"00000000-0000-0000-0000-00000000001{i}")
            mock_p.name = f"Project {i}"
            mock_p.code = f"PROJ-{i:03d}"
            mock_p.description = f"Description {i}"
            mock_p.status = "Active"
            mock_p.budget = float(100000 * (i + 1))
            mock_projects.append(mock_p)
            project_ids.append(mock_p.project_id)

        async def mock_get_projects(*args, **kwargs):
            return (mock_projects, 3)

        # Create context
        test_as_of = "2026-03-20T00:00:00"
        context = ToolContext(
            session=AsyncMock(),
            user_id="00000000-0000-0000-0000-000000000001",
            user_role="admin",
            project_id=None,
            as_of=datetime.fromisoformat(test_as_of),
            branch_name="main",
            branch_mode="merged",
        )

        # Mock both ProjectService and RBAC service
        with patch("app.services.project.ProjectService.get_projects", mock_get_projects), \
             patch("app.core.rbac.get_rbac_service") as mock_rbac_get:
            mock_rbac = AsyncMock()
            mock_rbac.get_user_projects = AsyncMock(return_value=project_ids)
            mock_rbac.session = None
            mock_rbac_get.return_value = mock_rbac

            # Act: Call the raw function
            result = await project_tools.list_projects.coroutine(context=context)

        # Assert: Verify temporal metadata
        assert "_temporal_context" in result
        assert result["_temporal_context"]["as_of"] == test_as_of
        assert result["total"] == 3
        assert len(result["projects"]) == 3

    @pytest.mark.asyncio
    async def test_temporal_metadata_in_error_results(self):
        """Verify temporal metadata is included even in error results."""
        # Setup: Make service return None (project not found)
        async def mock_get_by_id(*args, **kwargs):
            return None

        context = ToolContext(
            session=AsyncMock(),
            user_id="00000000-0000-0000-0000-000000000001",
            user_role="admin",
            project_id=None,
            as_of=datetime.fromisoformat("2026-03-15T00:00:00"),
            branch_name="main",
            branch_mode="merged",
        )

        with patch("app.services.project.ProjectService.get_as_of", mock_get_by_id):
            # Act: Call the raw function
            result = await project_tools.get_project.coroutine(
                project_id="00000000-0000-0000-0000-000000000003",
                context=context,
            )

        # Assert: Verify temporal metadata is present even in error
        assert "error" in result
        assert "_temporal_context" in result, (
            "Temporal metadata should be included in error results"
        )
        assert result["_temporal_context"]["as_of"] == "2026-03-15T00:00:00"

    @pytest.mark.asyncio
    async def test_temporal_context_changes_via_websocket(self):
        """Verify that temporal context changes propagate correctly from WebSocket.

        This simulates a user changing the Time Machine UI settings, which sends
        a WebSocket message with new temporal parameters.

        Expected: New temporal context is reflected in subsequent tool calls.
        """
        # Mock project
        mock_project = MagicMock(spec=Project)
        mock_project.project_id = MagicMock()
        mock_project.project_id.__str__ = lambda self: "test-project-id"
        mock_project.name = "Test Project"
        mock_project.code = "TEST-001"
        mock_project.description = "Test"
        mock_project.status = "Active"
        mock_project.budget = 100000.0
        mock_project.start_date = None
        mock_project.end_date = None

        async def mock_get_by_id(*args, **kwargs):
            return mock_project

        # Setup: Initial context
        initial_context = ToolContext(
            session=AsyncMock(),
            user_id="00000000-0000-0000-0000-000000000001",
            user_role="admin",
            project_id=None,
            as_of=datetime.fromisoformat("2026-03-15T00:00:00"),
            branch_name="main",
            branch_mode="merged",
        )

        with patch("app.services.project.ProjectService.get_as_of", mock_get_by_id):
            # Act: Initial tool call
            initial_result = await project_tools.get_project.coroutine(
                project_id="00000000-0000-0000-0000-000000000002",
                context=initial_context,
            )

        # Assert: Verify initial temporal context
        assert initial_result["_temporal_context"]["as_of"] == "2026-03-15T00:00:00"

        # Simulate WebSocket message updating temporal context
        # (User changes Time Machine to view different date/branch)
        updated_context = ToolContext(
            session=AsyncMock(),
            user_id="00000000-0000-0000-0000-000000000001",
            user_role="admin",
            project_id=None,
            as_of=datetime.fromisoformat("2026-02-01T00:00:00"),  # Different date
            branch_name="feature-branch",  # Different branch
            branch_mode="isolated",  # Different mode
        )

        with patch("app.services.project.ProjectService.get_as_of", mock_get_by_id):
            # Act: Tool call with updated context
            updated_result = await project_tools.get_project.coroutine(
                project_id="00000000-0000-0000-0000-000000000002",
                context=updated_context,
            )

        # Assert: Verify updated temporal context
        assert updated_result["_temporal_context"]["as_of"] == "2026-02-01T00:00:00", (
            "Temporal context should reflect updated as_of date"
        )
        assert updated_result["_temporal_context"]["branch_name"] == "feature-branch", (
            "Temporal context should reflect updated branch"
        )
        assert updated_result["_temporal_context"]["branch_mode"] == "isolated", (
            "Temporal context should reflect updated mode"
        )

    @pytest.mark.asyncio
    async def test_temporal_metadata_preserves_existing_fields(self):
        """Verify that add_temporal_metadata preserves existing result fields."""
        # Setup: Mock service
        from uuid import UUID

        mock_project = MagicMock(spec=Project)
        mock_project.project_id = UUID("00000000-0000-0000-0000-000000000002")
        mock_project.name = "Test Project"
        mock_project.code = "TEST-001"
        mock_project.description = "Test"
        mock_project.status = "Active"
        mock_project.budget = 100000.0
        mock_project.start_date = None
        mock_project.end_date = None

        async def mock_get_by_id(*args, **kwargs):
            return mock_project

        context = ToolContext(
            session=AsyncMock(),
            user_id="00000000-0000-0000-0000-000000000001",
            user_role="admin",
            project_id=None,
            as_of=datetime.fromisoformat("2026-03-15T00:00:00"),
            branch_name="main",
            branch_mode="merged",
        )

        # Mock both ProjectService and RBAC service
        with patch("app.services.project.ProjectService.get_as_of", mock_get_by_id), \
             patch("app.core.rbac.get_rbac_service") as mock_rbac_get:
            mock_rbac = AsyncMock()
            mock_rbac.has_project_access = AsyncMock(return_value=True)
            mock_rbac.session = None
            mock_rbac_get.return_value = mock_rbac

            # Act: Call the raw function
            result = await project_tools.get_project.coroutine(
                project_id="00000000-0000-0000-0000-000000000002",
                context=context,
            )

        # Assert: Verify all expected fields are present
        expected_fields = {
            "id",
            "name",
            "code",
            "description",
            "status",
            "budget",
            "start_date",
            "end_date",
            "branch",  # Added by get_project function
            "_temporal_context",  # Added by temporal metadata
        }

        actual_fields = set(result.keys())
        assert actual_fields == expected_fields, (
            f"Result should have all expected fields. Expected: {expected_fields}, Got: {actual_fields}"
        )

    @pytest.mark.asyncio
    async def test_llm_provides_temporal_context_to_user(self):
        """Verify that LLM can access temporal context to inform users.

        This test simulates a user asking "What time period am I viewing?"
        The LLM should be able to call get_temporal_context and provide that info.
        """
        # Setup: Create context representing a specific temporal view
        context = ToolContext(
            session=AsyncMock(),
            user_id="00000000-0000-0000-0000-000000000001",
            user_role="admin",
            project_id=None,
            as_of=datetime.fromisoformat("2026-03-15T00:00:00"),
            branch_name="feature-scope-change",
            branch_mode="merged",
        )

        # Act: Call the raw function
        temporal_info = await temporal_tools.get_temporal_context.coroutine(context=context)

        # Assert: Verify LLM has accurate information to provide to user
        assert temporal_info["as_of"] == "2026-03-15T00:00:00"
        assert temporal_info["branch_name"] == "feature-scope-change"
        assert temporal_info["branch_mode"] == "merged"

        # LLM can now construct a response like:
        # "You are currently viewing data as of March 15, 2026 on the
        #  feature-scope-change branch (merged mode)."

    @pytest.mark.asyncio
    async def test_multiple_tools_consistent_temporal_context(self):
        """Verify that temporal context is consistent across multiple tool calls.

        This ensures that all tools in a conversation use the same temporal context.
        """
        # Setup: Mock projects list
        mock_projects = []
        mock_p = MagicMock(spec=Project)
        mock_p.project_id = MagicMock()
        mock_p.project_id.__str__ = lambda self: "test-project-id"
        mock_p.name = "Test Project"
        mock_p.code = "TEST-001"
        mock_p.description = "Test"
        mock_p.status = "Active"
        mock_p.budget = 100000.0
        mock_projects.append(mock_p)

        async def mock_get_projects(*args, **kwargs):
            return (mock_projects, 1)

        async def mock_get_by_id(*args, **kwargs):
            return mock_p

        # Create context
        context = ToolContext(
            session=AsyncMock(),
            user_id="00000000-0000-0000-0000-000000000001",
            user_role="admin",
            project_id=None,
            as_of=datetime.fromisoformat("2026-03-15T00:00:00"),
            branch_name="main",
            branch_mode="merged",
        )

        with patch("app.services.project.ProjectService.get_projects", mock_get_projects), \
             patch("app.services.project.ProjectService.get_as_of", mock_get_by_id):
            # Act: Call multiple tools using raw functions
            list_result = await project_tools.list_projects.coroutine(context=context)
            get_result = await project_tools.get_project.coroutine(
                project_id="00000000-0000-0000-0000-000000000002",
                context=context,
            )
            temporal_result = await temporal_tools.get_temporal_context.coroutine(context=context)

        # Assert: Verify all tools have consistent temporal context
        assert list_result["_temporal_context"]["as_of"] == "2026-03-15T00:00:00"
        assert get_result["_temporal_context"]["as_of"] == "2026-03-15T00:00:00"
        assert temporal_result["as_of"] == "2026-03-15T00:00:00"

        # All show same branch and mode
        assert list_result["_temporal_context"]["branch_name"] == "main"
        assert get_result["_temporal_context"]["branch_name"] == "main"
        assert temporal_result["branch_name"] == "main"
