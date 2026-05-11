"""Unit tests for AI tool role-based filtering.

Tests for filter_tools_by_role() function that removes tools whose
required permissions are not granted by the assistant's RBAC role.

BE-007: Filter tools by assistant RBAC role in agent creation.
"""

from unittest.mock import MagicMock

from langchain_core.tools import BaseTool

from app.ai.tools import filter_tools_by_role
from app.ai.tools.types import RiskLevel, ToolMetadata
from app.core.rbac_unified import set_unified_rbac_service


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
    return service


class TestFilterToolsByRole:
    """Tests for filter_tools_by_role() function."""

    def test_tools_without_metadata_always_pass(self) -> None:
        """Tools without _tool_metadata should always be included."""
        mock_service = _make_rbac_service_mock({})
        set_unified_rbac_service(mock_service)
        try:
            tool = _make_mock_tool("no_meta_tool", permissions=None)
            result = filter_tools_by_role([tool], "ai-viewer")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert len(result) == 1
        assert result[0].name == "no_meta_tool"

    def test_tools_with_empty_permissions_always_pass(self) -> None:
        """Tools with metadata but empty permissions list should pass."""
        mock_service = _make_rbac_service_mock({})
        set_unified_rbac_service(mock_service)
        try:
            tool = _make_mock_tool("empty_perms_tool", permissions=[])
            result = filter_tools_by_role([tool], "ai-viewer")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert len(result) == 1
        assert result[0].name == "empty_perms_tool"

    def test_tool_passes_when_role_has_all_permissions(self) -> None:
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
            result = filter_tools_by_role([tool], "ai-manager")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert len(result) == 1
        assert result[0].name == "create_project"

    def test_tool_filtered_when_role_lacks_permission(self) -> None:
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
            result = filter_tools_by_role([tool], "ai-viewer")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert len(result) == 0

    def test_mixed_tools_filters_correctly(self) -> None:
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
            result = filter_tools_by_role(tools, "ai-viewer")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        result_names = [t.name for t in result]
        assert "list_projects" in result_names
        assert "list_wbes" in result_names
        assert "no_meta_tool" in result_names
        assert "create_project" not in result_names
        assert "delete_project" not in result_names

    def test_returns_empty_list_for_empty_input(self) -> None:
        """Empty tool list returns empty list."""
        mock_service = _make_rbac_service_mock({})
        set_unified_rbac_service(mock_service)
        try:
            result = filter_tools_by_role([], "ai-admin")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert result == []

    def test_unknown_role_denies_all_permissioned_tools(self) -> None:
        """Unknown role denies all tools that require permissions."""
        mock_service = _make_rbac_service_mock({})  # no role permissions
        set_unified_rbac_service(mock_service)
        try:
            tool = _make_mock_tool("some_tool", permissions=["any-permission"])
            result = filter_tools_by_role([tool], "unknown-role")
        finally:
            set_unified_rbac_service(None)  # type: ignore[arg-type]

        assert len(result) == 0
