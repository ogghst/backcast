"""Security tests for AI tool RBAC enforcement.

After BE-003, permission checking is handled solely by
BackcastSecurityMiddleware. The @ai_tool decorator no longer
enforces permissions -- it only attaches metadata.

Tests verify:
- Decorator does NOT check permissions (middleware is sole enforcer)
- Tool metadata (permissions, category) is correctly attached
- Context isolation works correctly
- Middleware uses contextvar session (not singleton mutation)
- Integration: tool filtering by AI assistant role (TEST-002)
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools import ToolContext
from app.core.rbac import RBACServiceABC, set_rbac_service


class MockRBACService(RBACServiceABC):
    """Mock RBAC service for testing."""

    def __init__(self) -> None:
        self.permission_map: dict[str, list[str]] = {
            "admin": ["project-read", "project-write", "project-delete"],
            "manager": ["project-read", "project-write"],
            "viewer": ["project-read"],
            "guest": [],
        }
        self.session: object = None

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return user_role in required_roles

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return required_permission in self.permission_map.get(user_role, [])

    def get_user_permissions(self, user_role: str) -> list[str]:
        return self.permission_map.get(user_role, [])

    async def has_project_access(
        self,
        user_id: UUID,
        user_role: str,
        project_id: UUID,
        required_permission: str,
    ) -> bool:
        """Check if user has access to a project with required permission."""
        if user_role == "admin":
            return True
        return self.has_permission(user_role, required_permission)

    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        """Get list of project IDs the user has access to."""
        return []

    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        """Get user's role within a specific project."""
        return None


# Test fixtures
@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock AsyncSession."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def setup_mock_rbac():
    """Set up mock RBAC service for tests that need it."""
    mock_service = MockRBACService()
    from app.core import rbac as rbac_module

    original_service = rbac_module._rbac_service
    set_rbac_service(mock_service)

    yield mock_service

    rbac_module._rbac_service = original_service


@pytest.fixture
def real_rbac_service() -> Any:
    """Set up the REAL JsonRBACService from config/rbac.json.

    Integration tests use the actual RBAC configuration to verify
    that tool filtering works end-to-end with real role definitions.
    """
    from app.core.rbac import JsonRBACService

    # backend/tests/security/ai/ -> 4 parents to backend/
    backend_dir = Path(__file__).resolve().parent.parent.parent.parent
    config_path = backend_dir / "config" / "rbac.json"
    service = JsonRBACService(config_path=config_path)

    from app.core import rbac as rbac_module

    original_service = rbac_module._rbac_service
    set_rbac_service(service)

    yield service

    rbac_module._rbac_service = original_service


@pytest.fixture
def all_tools(real_rbac_service: Any) -> list[BaseTool]:
    """Create all real tools using the real RBAC service.

    Clears the tool cache before creating tools to ensure a fresh set.
    """
    import app.ai.tools as tools_module

    # Clear the tool cache to get fresh tools
    tools_module._cached_tools = None

    mock_ctx = MagicMock(spec=ToolContext)
    mock_ctx.user_role = "admin"
    mock_ctx.user_id = "test-user-id"
    mock_ctx.session = MagicMock()

    tools = tools_module.create_project_tools(mock_ctx)
    return tools


# --- Decorator permission tests (BE-003: decorator no longer checks) ---


@pytest.mark.asyncio
@pytest.mark.security
async def test_decorator_does_not_check_permissions(
    mock_session: MagicMock,
) -> None:
    """After BE-003, @ai_tool wrapper does not check permissions.

    Permission checking is handled solely by BackcastSecurityMiddleware.
    The decorator should execute the tool function without consulting
    the RBAC service, even when the user role lacks the tool's declared
    permissions.
    """
    from app.ai.tools.decorator import ai_tool
    from app.ai.tools.types import ToolContext

    @ai_tool(
        name="test_no_perm_check",
        description="Test tool",
        permissions=["project-read"],
    )
    async def test_tool(input: str, context: ToolContext) -> dict:
        """Test tool.

        Args:
            input: Test input
            context: Tool context
        """
        return {"result": input}

    # Guest role has NO permissions in MockRBACService
    ctx = ToolContext(
        session=mock_session,
        user_id="test-user-id",
        user_role="guest",
    )

    # Patch get_rbac_service at its source module to verify it is NOT called
    with patch("app.core.rbac.get_rbac_service") as mock_get_rbac:
        with patch("app.ai.tools.session_manager.ToolSessionManager"):
            result = await test_tool.ainvoke({"input": "test", "context": ctx})

            assert not mock_get_rbac.called

    assert result["result"] == "test"


@pytest.mark.asyncio
@pytest.mark.security
async def test_decorator_executes_tool_without_permission_check(
    mock_session: MagicMock,
) -> None:
    """Decorator executes the underlying function regardless of user role.

    The decorator used to block execution for unauthorized roles.
    After BE-003, it always executes the function. Permission enforcement
    is the middleware's responsibility.
    """
    from app.ai.tools.decorator import ai_tool
    from app.ai.tools.types import ToolContext

    function_executed = False

    @ai_tool(
        name="test_exec_always",
        description="Test tool",
        permissions=["project-read"],
    )
    async def test_tool(input: str, context: ToolContext) -> dict:
        """Test tool.

        Args:
            input: Test input
            context: Tool context
        """
        nonlocal function_executed
        function_executed = True
        return {"result": input}

    # Guest role has no permissions -- but decorator should still execute
    ctx = ToolContext(
        session=mock_session,
        user_id="test-user-id",
        user_role="guest",
    )

    with patch("app.ai.tools.session_manager.ToolSessionManager"):
        result = await test_tool.ainvoke({"input": "hello", "context": ctx})

    assert function_executed, "Function should execute regardless of role"
    assert result["result"] == "hello"


# --- Metadata tests (permissions still attached for middleware) ---


@pytest.mark.asyncio
@pytest.mark.security
async def test_tool_level_rbac_metadata() -> None:
    """Tool metadata includes permission information for middleware enforcement."""
    from app.ai.tools.decorator import ai_tool

    @ai_tool(
        name="secure_tool",
        description="A tool that requires permissions",
        permissions=["project-read", "project-write"],
        category="projects",
    )
    async def secure_tool(input: str, context: ToolContext) -> dict:
        """A secure tool that processes input.

        Args:
            input: The input string to process
            context: The tool context

        Returns:
            A dictionary containing the processed result
        """
        return {"result": f"Processed: {input}"}

    if hasattr(secure_tool, "_tool_metadata"):
        metadata = secure_tool._tool_metadata
        assert metadata.permissions == ["project-read", "project-write"]
        assert metadata.category == "projects"
    else:
        pytest.skip("Tool metadata not accessible in this version")


# --- Context isolation tests ---


@pytest.mark.asyncio
@pytest.mark.security
async def test_tool_context_user_id_isolation(
    mock_session: MagicMock,
) -> None:
    """ToolContext properly isolates user context."""
    from app.ai.tools.decorator import ai_tool
    from app.ai.tools.types import ToolContext

    captured_user_ids: list[str] = []

    @ai_tool(
        name="context_tool",
        description="A tool that uses context",
    )
    async def context_tool(input: str, context: ToolContext) -> dict:
        """A tool that captures context.

        Args:
            input: The input string to process
            context: The tool context

        Returns:
            A dictionary containing the user ID
        """
        captured_user_ids.append(context.user_id)
        return {"result": f"User: {context.user_id}"}

    ctx = ToolContext(
        session=mock_session,
        user_id="user-1",
        user_role="viewer",
    )

    with patch("app.ai.tools.session_manager.ToolSessionManager"):
        await context_tool.ainvoke({"input": "test", "context": ctx})

    assert len(captured_user_ids) == 1
    assert captured_user_ids[0] == "user-1"


# --- Middleware contextvar tests (BE-005) ---


@pytest.mark.asyncio
@pytest.mark.security
async def test_middleware_uses_contextvar_session() -> None:
    """Middleware sets session via set_rbac_session(), not singleton mutation.

    Given:
        A BackcastSecurityMiddleware with a tool requiring project-level RBAC
        A mock RBAC service with a tracked .session attribute
    When:
        _check_tool_permission() is called with a project_id
    Then:
        set_rbac_session() is called with ctx.session
        The singleton's .session attribute is never assigned during the call

    This is the regression test for BE-005: verifies the middleware no longer
    corrupts the singleton's session on concurrent WebSocket connections.
    """
    from app.ai.middleware.backcast_security import BackcastSecurityMiddleware
    from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext

    # Arrange: create a mock tool with project-level permissions
    mock_tool = MagicMock()
    mock_tool.name = "test_project_tool"
    mock_tool._tool_metadata = MagicMock()
    mock_tool._tool_metadata.permissions = ["project-read"]
    mock_tool._tool_metadata.risk_level = RiskLevel.LOW

    # Arrange: create a mock RBAC service that tracks session mutations
    mock_rbac = MockRBACService()
    mock_rbac.session = "original_session_value"  # sentinel to detect mutation
    mock_rbac.has_project_access = AsyncMock(return_value=True)
    set_rbac_service(mock_rbac)

    # Arrange: create context and middleware
    mock_session = MagicMock(spec=AsyncSession)
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = "00000000-0000-0000-0000-000000000001"
    ctx.user_role = "viewer"
    ctx.session = mock_session
    ctx.execution_mode = ExecutionMode.STANDARD

    middleware = BackcastSecurityMiddleware(context=ctx, tools=[mock_tool])

    # Patch set_rbac_session at the module where it is imported/used
    with (
        patch(
            "app.ai.middleware.backcast_security.get_request_tool_context",
            return_value=ctx,
        ),
        patch(
            "app.ai.middleware.backcast_security.set_rbac_session",
        ) as mock_set_rbac_session,
    ):
        # Act
        result = await middleware._check_tool_permission(
            tool_name="test_project_tool",
            tool_args={"project_id": "00000000-0000-0000-0000-000000000002"},
        )

    # Assert: permission check succeeds
    assert result is None  # None means permitted

    # Assert: set_rbac_session was called with the context session
    mock_set_rbac_session.assert_called_once_with(mock_session)

    # Assert: singleton's .session was NOT directly mutated
    assert mock_rbac.session == "original_session_value", (
        "Middleware should NOT mutate rbac_service.session directly"
    )


# =============================================================================
# Integration tests: Tool filtering by AI assistant role (TEST-002)
#
# These tests use the REAL rbac.json and REAL tool definitions to verify
# end-to-end that filter_tools_by_role() correctly filters tools based on
# each AI assistant's role permissions.
# =============================================================================


def _tool_names(tools: list[BaseTool]) -> set[str]:
    """Extract tool names from a list of BaseTool instances."""
    return {t.name for t in tools}


def _permissioned_tool_names(tools: list[BaseTool]) -> set[str]:
    """Extract names of tools that have non-empty permission metadata."""
    names: set[str] = set()
    for t in tools:
        metadata = getattr(t, "_tool_metadata", None)
        if metadata is not None and metadata.permissions:
            names.add(t.name)
    return names


def _unpermissioned_tool_names(tools: list[BaseTool]) -> set[str]:
    """Extract names of tools with no permissions (always pass filtering)."""
    names: set[str] = set()
    for t in tools:
        metadata = getattr(t, "_tool_metadata", None)
        if metadata is None or not metadata.permissions:
            names.add(t.name)
    return names


class TestToolFilteringByAssistantRole:
    """Integration tests for filter_tools_by_role() with real RBAC config.

    Verifies that each AI assistant role receives only the tools its
    permissions allow, using the real rbac.json and real tool definitions.
    """

    def test_ai_viewer_agent_gets_only_read_tools(
        self,
        all_tools: list[BaseTool],
        real_rbac_service: Any,
    ) -> None:
        """ai-viewer should receive only read-only tools.

        Given:
            The real tool set from create_project_tools()
            The real rbac.json with ai-viewer role
        When:
            Tools are filtered by ai-viewer role
        Then:
            No tool requiring create/update/delete permissions remains
            Read-only tools (list_projects, get_project, etc.) are present
            Tools without permissions are always included
        """
        from app.ai.tools import filter_tools_by_role

        # Act
        filtered = filter_tools_by_role(all_tools, "ai-viewer")
        filtered_names = _tool_names(filtered)

        # Assert: tools that require write permissions are NOT present
        write_tools = [
            "create_project",
            "update_project",
            "create_wbe",
            "update_wbe",
            "create_cost_element",
            "update_cost_element",
            "delete_cost_element",
            "create_user",
            "update_user",
            "delete_user",
            "create_department",
            "update_department",
            "delete_department",
            "create_cost_element_type",
            "update_cost_element_type",
            "delete_cost_element_type",
            "create_forecast",
            "update_forecast",
            "create_cost_registration",
            "update_cost_registration",
            "delete_cost_registration",
            "create_change_order",
            "update_change_order",
            "update_schedule_baseline",
            "delete_schedule_baseline",
            "create_progress_entry",
            "approve_change_order",
            "reject_change_order",
            "submit_change_order_for_approval",
        ]
        for tool_name in write_tools:
            assert tool_name not in filtered_names, (
                f"ai-viewer should NOT have write tool '{tool_name}'"
            )

        # Assert: read-only tools ARE present
        read_tools = [
            "list_projects",
            "get_project",
            "global_search",
            "get_project_context",
            "get_project_structure",
            "get_temporal_context",
            "list_wbes",
            "get_wbe",
            "list_cost_elements",
            "get_cost_element",
            "list_cost_element_types",
            "get_cost_element_type",
            "list_users",
            "get_user",
            "list_departments",
            "get_department",
            "list_change_orders",
            "get_change_order",
            "get_forecast",
            "list_cost_registrations",
            "get_cost_registration",
            "get_budget_status",
            "get_cost_trends",
            "get_cumulative_costs",
            "list_progress_entries",
            "get_progress_entry",
            "get_latest_progress",
            "get_progress_history",
            "get_schedule_baseline",
            "get_cost_element_summary",
        ]
        for tool_name in read_tools:
            assert tool_name in filtered_names, (
                f"ai-viewer should have read tool '{tool_name}'"
            )

        # Assert: unpermissioned tools are always included
        unpermissioned = _unpermissioned_tool_names(all_tools)
        assert unpermissioned.issubset(filtered_names), (
            f"Unpermissioned tools should always pass: {unpermissioned - filtered_names}"
        )

    def test_ai_manager_agent_gets_crud_tools(
        self,
        all_tools: list[BaseTool],
        real_rbac_service: Any,
    ) -> None:
        """ai-manager should receive read + CRUD tools but NOT delete-level tools.

        Given:
            The real tool set from create_project_tools()
            The real rbac.json with ai-manager role
        When:
            Tools are filtered by ai-manager role
        Then:
            Create/update tools (create_project, update_project, etc.) are present
            Delete tools for project-level entities are present (cost-registration-delete)
            Admin-only delete tools (user-delete, department-delete) are NOT present
        """
        from app.ai.tools import filter_tools_by_role

        # Act
        filtered = filter_tools_by_role(all_tools, "ai-manager")
        filtered_names = _tool_names(filtered)

        # Assert: create/update tools ARE present
        crud_tools = [
            "create_project",
            "update_project",
            "create_wbe",
            "update_wbe",
            "create_cost_element",
            "update_cost_element",
            "create_forecast",
            "update_forecast",
            "create_cost_registration",
            "update_cost_registration",
            "create_change_order",
            "generate_change_order_draft",
            "submit_change_order_for_approval",
            "approve_change_order",
            "reject_change_order",
            "create_progress_entry",
            "update_schedule_baseline",
        ]
        for tool_name in crud_tools:
            assert tool_name in filtered_names, (
                f"ai-manager should have CRUD tool '{tool_name}'"
            )

        # Assert: delete tools that ai-manager DOES have
        manager_delete_tools = [
            "delete_cost_registration",
        ]
        for tool_name in manager_delete_tools:
            assert tool_name in filtered_names, (
                f"ai-manager should have delete tool '{tool_name}'"
            )

        # Assert: admin-only tools are NOT present
        admin_only_tools = [
            "create_user",
            "update_user",
            "delete_user",
            "create_department",
            "update_department",
            "delete_department",
            "create_cost_element_type",
            "update_cost_element_type",
            "delete_cost_element_type",
        ]
        for tool_name in admin_only_tools:
            assert tool_name not in filtered_names, (
                f"ai-manager should NOT have admin tool '{tool_name}'"
            )

        # Assert: read tools are still present
        assert "list_projects" in filtered_names
        assert "get_project" in filtered_names
        assert "list_cost_elements" in filtered_names

    def test_ai_admin_agent_gets_admin_tools(
        self,
        all_tools: list[BaseTool],
        real_rbac_service: Any,
    ) -> None:
        """ai-admin should receive user/department/cost-element-type tools only.

        Given:
            The real tool set from create_project_tools()
            The real rbac.json with ai-admin role
        When:
            Tools are filtered by ai-admin role
        Then:
            User/department/cost-element-type CRUD tools are present
            Project entity write tools (wbe, forecast, cost-element) are NOT present
        """
        from app.ai.tools import filter_tools_by_role

        # Act
        filtered = filter_tools_by_role(all_tools, "ai-admin")
        filtered_names = _tool_names(filtered)

        # Assert: admin tools ARE present
        admin_tools = [
            "list_users",
            "get_user",
            "create_user",
            "update_user",
            "delete_user",
            "list_departments",
            "get_department",
            "create_department",
            "update_department",
            "delete_department",
            "list_cost_element_types",
            "get_cost_element_type",
            "create_cost_element_type",
            "update_cost_element_type",
            "delete_cost_element_type",
        ]
        for tool_name in admin_tools:
            assert tool_name in filtered_names, (
                f"ai-admin should have admin tool '{tool_name}'"
            )

        # Assert: project entity write tools are NOT present
        project_write_tools = [
            "create_project",
            "update_project",
            "create_wbe",
            "update_wbe",
            "create_cost_element",
            "update_cost_element",
            "create_forecast",
            "update_forecast",
            "create_cost_registration",
            "update_cost_registration",
            "create_change_order",
            "update_change_order",
            "create_progress_entry",
        ]
        for tool_name in project_write_tools:
            assert tool_name not in filtered_names, (
                f"ai-admin should NOT have project write tool '{tool_name}'"
            )

        # Assert: basic read tools that ai-admin has
        assert "list_projects" in filtered_names
        assert "get_project" in filtered_names

    def test_filter_tools_by_role_combined_with_execution_mode(
        self,
        all_tools: list[BaseTool],
        real_rbac_service: Any,
    ) -> None:
        """Combining role filter with execution mode filter yields the intersection.

        Given:
            The real tool set from create_project_tools()
            The real rbac.json with ai-viewer role
            ExecutionMode.SAFE (only LOW risk tools)
        When:
            Both filter_tools_by_role and filter_tools_by_execution_mode are applied
        Then:
            Only tools that pass BOTH filters remain
            No high/critical risk tools survive
            No write-permission tools survive
        """
        from app.ai.tools import filter_tools_by_execution_mode, filter_tools_by_role
        from app.ai.tools.types import ExecutionMode

        # Act: apply both filters
        role_filtered = filter_tools_by_role(all_tools, "ai-viewer")
        combined = filter_tools_by_execution_mode(role_filtered, ExecutionMode.SAFE)
        combined_names = _tool_names(combined)

        # Assert: no tools with write permissions survived
        for tool in combined:
            metadata = getattr(tool, "_tool_metadata", None)
            if metadata and metadata.permissions:
                for perm in metadata.permissions:
                    assert not any(
                        perm.endswith(suffix)
                        for suffix in ("-create", "-update", "-delete", "-write")
                    ), (
                        f"Tool '{tool.name}' has write permission '{perm}' "
                        f"but should be filtered out for ai-viewer in SAFE mode"
                    )

        # Assert: only LOW risk tools survived
        for tool in combined:
            metadata = getattr(tool, "_tool_metadata", None)
            if metadata:
                from app.ai.tools.types import RiskLevel

                assert metadata.risk_level == RiskLevel.LOW, (
                    f"Tool '{tool.name}' has risk_level={metadata.risk_level.value} "
                    f"but SAFE mode only allows LOW risk"
                )

        # Assert: some read tools survive (not empty)
        assert len(combined) > 0, (
            "ai-viewer in SAFE mode should still have some read-only tools"
        )

        # Assert: well-known read-only tools are present
        assert "list_projects" in combined_names
        assert "get_project" in combined_names


# Run security tests with pytest:
# pytest tests/security/ai/test_tool_rbac.py -v -m security
