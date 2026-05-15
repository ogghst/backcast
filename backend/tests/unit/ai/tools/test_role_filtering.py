"""Unit tests for AI tool role-based filtering.

Tests for filter_tools_by_role() function that removes tools whose
required permissions are not granted by the assistant's RBAC role.

BE-007: Filter tools by assistant RBAC role in agent creation.
BE-001: Async cache-miss refresh tests (RED phase).
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.tools import BaseTool

from app.ai.tools import filter_tools_by_role
from app.ai.tools.types import RiskLevel, ToolMetadata
from app.core.rbac_unified import (
    UnifiedRBACService,
    set_unified_rbac_service,
    set_unified_rbac_session,
)


def _make_mock_tool(
    name: str,
    permissions: list[str] | None = None,
) -> BaseTool:
    """Create a mock BaseTool with optional _tool_metadata.

    Args:
        name: Tool name
        permissions: Required permissions list, or None for no metadata

    Returns:
        Mock BaseTool instance
    """
    tool = MagicMock(spec=BaseTool)
    tool.name = name

    if permissions is not None:
        metadata = ToolMetadata(
            name=name,
            description=f"Test tool {name}",
            permissions=permissions,
            risk_level=RiskLevel.LOW,
        )
        tool._tool_metadata = metadata
    else:
        # Explicitly no metadata attribute
        del tool._tool_metadata

    return tool


def _make_rbac_service_mock(
    role_permissions: dict[str, set[str]],
) -> MagicMock:
    """Create a mock UnifiedRBACService with controlled permission responses.

    Args:
        role_permissions: Map of role -> set of granted permissions

    Returns:
        Mock service with _get_cached_permissions method
    """
    service = MagicMock()
    service._get_cached_permissions = MagicMock(
        side_effect=lambda role: list(role_permissions.get(role, set())) or None
    )
    service.refresh_permissions_cache = AsyncMock()
    return service


class TestFilterToolsByRole:
    """Tests for filter_tools_by_role() function."""

    @pytest.mark.asyncio
    async def test_tools_without_metadata_always_pass(self) -> None:
        """Tools without _tool_metadata should always be included."""
        mock_service = _make_rbac_service_mock({})
        set_unified_rbac_service(mock_service)
        try:
            tool = _make_mock_tool("no_meta_tool", permissions=None)
            result = await filter_tools_by_role([tool], "ai-viewer")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert len(result) == 1
        assert result[0].name == "no_meta_tool"

    @pytest.mark.asyncio
    async def test_tools_with_empty_permissions_always_pass(self) -> None:
        """Tools with metadata but empty permissions list should pass."""
        mock_service = _make_rbac_service_mock({})
        set_unified_rbac_service(mock_service)
        try:
            tool = _make_mock_tool("empty_perms_tool", permissions=[])
            result = await filter_tools_by_role([tool], "ai-viewer")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert len(result) == 1
        assert result[0].name == "empty_perms_tool"

    @pytest.mark.asyncio
    async def test_tool_passes_when_role_has_all_permissions(self) -> None:
        """Tool included when role has all required permissions."""
        mock_service = _make_rbac_service_mock(
            {"ai-manager": {"project-read", "project-create"}}
        )
        set_unified_rbac_service(mock_service)
        try:
            tool = _make_mock_tool(
                "create_project",
                permissions=["project-read", "project-create"],
            )
            result = await filter_tools_by_role([tool], "ai-manager")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert len(result) == 1
        assert result[0].name == "create_project"

    @pytest.mark.asyncio
    async def test_tool_filtered_when_role_lacks_permission(self) -> None:
        """Tool excluded when role lacks even one required permission."""
        mock_service = _make_rbac_service_mock(
            {
                "ai-viewer": {"project-read"}  # missing project-delete
            }
        )
        set_unified_rbac_service(mock_service)
        try:
            tool = _make_mock_tool(
                "delete_project",
                permissions=["project-read", "project-delete"],
            )
            result = await filter_tools_by_role([tool], "ai-viewer")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_mixed_tools_filters_correctly(self) -> None:
        """Multiple tools filtered according to each tool's permissions."""
        mock_service = _make_rbac_service_mock(
            {"ai-viewer": {"project-read", "wbe-read", "cost-element-read"}}
        )
        set_unified_rbac_service(mock_service)
        try:
            tools = [
                _make_mock_tool("list_projects", permissions=["project-read"]),
                _make_mock_tool(
                    "create_project",
                    permissions=["project-read", "project-create"],
                ),
                _make_mock_tool("list_wbes", permissions=["wbe-read"]),
                _make_mock_tool(
                    "delete_project",
                    permissions=["project-read", "project-delete"],
                ),
                _make_mock_tool("no_meta_tool", permissions=None),
            ]
            result = await filter_tools_by_role(tools, "ai-viewer")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        result_names = [t.name for t in result]
        assert "list_projects" in result_names
        assert "list_wbes" in result_names
        assert "no_meta_tool" in result_names
        assert "create_project" not in result_names
        assert "delete_project" not in result_names

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_empty_input(self) -> None:
        """Empty tool list returns empty list."""
        mock_service = _make_rbac_service_mock({})
        set_unified_rbac_service(mock_service)
        try:
            result = await filter_tools_by_role([], "ai-admin")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert result == []

    @pytest.mark.asyncio
    async def test_unknown_role_denies_all_permissioned_tools(self) -> None:
        """Unknown role denies all tools that require permissions."""
        mock_service = _make_rbac_service_mock({})  # no role permissions
        set_unified_rbac_service(mock_service)
        try:
            tool = _make_mock_tool("some_tool", permissions=["any-permission"])
            result = await filter_tools_by_role([tool], "unknown-role")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert len(result) == 0


class TestFilterToolsByRoleAsyncCacheRefresh:
    """Tests for async cache-miss refresh behavior in filter_tools_by_role().

    These tests validate the BE-002 async conversion:
    - On cache miss, filter_tools_by_role() should await refresh_permissions_cache()
    - After refresh, _get_cached_permissions() should return valid permissions
    - On cache hit (warm), no refresh should be triggered

    RED phase: These tests will fail because filter_tools_by_role() is currently
    synchronous and does not call refresh_permissions_cache().
    """

    @pytest.mark.asyncio
    async def test_filter_tools_by_role_cache_miss_triggers_refresh(self) -> None:
        """T-001: Cache miss triggers on-demand refresh and returns non-empty tools.

        Criterion: FC-1
        """
        mock_service = MagicMock()
        # First call returns None (cache miss), second call returns permissions after refresh
        mock_service._get_cached_permissions = MagicMock(
            side_effect=[
                None,  # First call: cache miss
                ["project-read", "project-create"],  # Second call: after refresh
            ]
        )
        mock_service.refresh_permissions_cache = AsyncMock()

        set_unified_rbac_service(mock_service)
        try:
            tool = _make_mock_tool(
                "create_project",
                permissions=["project-read", "project-create"],
            )
            result = await filter_tools_by_role([tool], "ai-manager")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        # Assert refresh was awaited exactly once
        mock_service.refresh_permissions_cache.assert_awaited_once()
        # Assert non-empty tool list returned
        assert len(result) == 1
        assert result[0].name == "create_project"

    @pytest.mark.asyncio
    async def test_filter_tools_by_role_cache_miss_returns_all_permitted_tools(
        self,
    ) -> None:
        """T-002: After cache-miss refresh, all permitted tools for admin role are returned.

        Criterion: FC-2
        """
        admin_permissions = [
            "project-read",
            "project-create",
            "project-update",
            "project-delete",
            "wbe-read",
            "wbe-create",
        ]

        mock_service = MagicMock()
        mock_service._get_cached_permissions = MagicMock(
            side_effect=[
                None,  # Cache miss on first call
                admin_permissions,  # After refresh, return all admin permissions
            ]
        )
        mock_service.refresh_permissions_cache = AsyncMock()

        set_unified_rbac_service(mock_service)
        try:
            tools = [
                _make_mock_tool("list_projects", permissions=["project-read"]),
                _make_mock_tool(
                    "create_project",
                    permissions=["project-read", "project-create"],
                ),
                _make_mock_tool(
                    "delete_project",
                    permissions=["project-read", "project-delete"],
                ),
                _make_mock_tool("list_wbes", permissions=["wbe-read"]),
                _make_mock_tool(
                    "create_wbe",
                    permissions=["wbe-read", "wbe-create"],
                ),
            ]
            result = await filter_tools_by_role(tools, "ai-admin")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        result_names = [t.name for t in result]
        # All tools should be present for admin role
        assert len(result) == 5
        assert "list_projects" in result_names
        assert "create_project" in result_names
        assert "delete_project" in result_names
        assert "list_wbes" in result_names
        assert "create_wbe" in result_names

    @pytest.mark.asyncio
    async def test_filter_tools_by_role_cache_warm_no_refresh(self) -> None:
        """T-003: When cache is warm, refresh is NOT called and filtering works normally.

        Criterion: FC-3
        """
        mock_service = MagicMock()
        # Cache is warm -- returns valid permissions immediately
        mock_service._get_cached_permissions = MagicMock(
            return_value=["project-read", "wbe-read"]
        )
        mock_service.refresh_permissions_cache = AsyncMock()

        set_unified_rbac_service(mock_service)
        try:
            tools = [
                _make_mock_tool("list_projects", permissions=["project-read"]),
                _make_mock_tool(
                    "create_project",
                    permissions=["project-read", "project-create"],
                ),
                _make_mock_tool("list_wbes", permissions=["wbe-read"]),
            ]
            result = await filter_tools_by_role(tools, "ai-viewer")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        # Assert refresh was NOT called (cache was warm)
        mock_service.refresh_permissions_cache.assert_not_called()
        # Assert filtering still works correctly
        result_names = [t.name for t in result]
        assert "list_projects" in result_names
        assert "list_wbes" in result_names
        assert "create_project" not in result_names  # lacks project-create

    @pytest.mark.asyncio
    async def test_filter_tools_by_role_cache_miss_logs_error(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """T-005: Cache miss triggers an ERROR-level log message.

        Criterion: TC-6
        """
        mock_service = MagicMock()
        mock_service._get_cached_permissions = MagicMock(
            side_effect=[
                None,  # Cache miss
                ["project-read"],  # After refresh
            ]
        )
        mock_service.refresh_permissions_cache = AsyncMock()

        set_unified_rbac_service(mock_service)
        try:
            tool = _make_mock_tool("list_projects", permissions=["project-read"])
            with caplog.at_level(logging.ERROR, logger="app.ai.tools"):
                await filter_tools_by_role([tool], "ai-viewer")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        # Assert ERROR-level log containing "cache" and ("miss" or "expired")
        error_records = [
            r
            for r in caplog.records
            if r.levelname == "ERROR" and "cache" in r.message.lower()
        ]
        assert len(error_records) >= 1, (
            "Expected at least one ERROR-level log message containing 'cache'"
        )
        log_msg = error_records[0].message.lower()
        assert "miss" in log_msg or "expired" in log_msg, (
            f"Expected log message to contain 'miss' or 'expired', got: {error_records[0].message}"
        )

    @pytest.mark.asyncio
    async def test_filter_tools_by_role_cache_miss_refresh_with_session(self) -> None:
        """T-006: Cache miss with a real session triggers actual refresh_permissions_cache.

        Verifies that refresh_permissions_cache() exercises the database query
        path when an AsyncSession is available via the ContextVar. This tests
        the code path that was broken by premature session cleanup in the
        WebSocket handler (set_unified_rbac_session(None) before agent run).

        Criterion: FC-1 (refresh uses session, not mocked away)
        """
        # Use a REAL service so refresh_permissions_cache() actually runs
        real_service = UnifiedRBACService()

        # Set up a mock AsyncSession that returns role-permission rows
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("ai-manager", "project-read"),
            ("ai-manager", "project-create"),
        ]
        mock_session.execute.return_value = mock_result

        set_unified_rbac_service(real_service)
        set_unified_rbac_session(mock_session)
        try:
            tool = _make_mock_tool(
                "create_project",
                permissions=["project-read", "project-create"],
            )
            result = await filter_tools_by_role([tool], "ai-manager")

            # Assert the session.execute was called (refresh used the session)
            mock_session.execute.assert_awaited_once()

            # Assert the tool passed filtering (permissions were loaded from session)
            assert len(result) == 1
            assert result[0].name == "create_project"

            # Assert the cache was populated by the refresh
            cached = real_service._get_cached_permissions("ai-manager")
            assert cached is not None
            assert "project-read" in cached
            assert "project-create" in cached
        finally:
            set_unified_rbac_session(None)
            set_unified_rbac_service(None)  # type: ignore[arg-type]
