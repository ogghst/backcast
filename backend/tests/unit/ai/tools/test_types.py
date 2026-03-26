"""Tests for AI tool types."""

from unittest.mock import MagicMock

import pytest

from app.ai.tools.types import ToolContext, ToolMetadata


class TestToolContext:
    """Test ToolContext functionality."""

    @pytest.mark.asyncio
    async def test_context_initialization(self):
        """Test ToolContext initializes with session and user_id."""
        mock_session = MagicMock()
        context = ToolContext(session=mock_session, user_id="user123")

        # The original session is stored in _root_session
        assert context._root_session == mock_session
        assert context.user_id == "user123"
        # The session property returns a task-local session (AsyncSession from scoped factory)
        # This is different from the original mock session to enable concurrent tool execution

    @pytest.mark.asyncio
    async def test_permission_checking_with_cache(self):
        """Test permission checking with caching."""
        mock_session = MagicMock()
        # Use "admin" role which has all permissions in the RBAC config
        context = ToolContext(session=mock_session, user_id="user123", user_role="admin")

        # First check
        result1 = await context.check_permission("project-read")
        assert result1 is True

        # Second check should use cache
        result2 = await context.check_permission("project-read")
        assert result2 is True

        # Verify cached (cache key format is "permission:scope")
        assert "project-read:global" in context._permission_cache

    @pytest.mark.asyncio
    async def test_permission_checking_different_permissions(self):
        """Test permission checking for different permissions."""
        mock_session = MagicMock()
        # Use "admin" role which has all permissions in the RBAC config
        context = ToolContext(session=mock_session, user_id="user123", user_role="admin")

        # Check different permissions
        result1 = await context.check_permission("project-read")
        result2 = await context.check_permission("user-update")

        assert result1 is True
        assert result2 is True

        # Both should be cached (cache key format is "permission:scope")
        assert len(context._permission_cache) == 2
        assert "project-read:global" in context._permission_cache
        assert "user-update:global" in context._permission_cache

    @pytest.mark.asyncio
    async def test_service_accessor(self):
        """Test project_service accessor."""
        mock_session = MagicMock()
        context = ToolContext(session=mock_session, user_id="user123")

        service = context.project_service
        assert service is not None
        # The service gets the task-local session from context.session property
        # This is an AsyncSession from the scoped factory, not the original mock
        assert service.session is not None


class TestToolMetadata:
    """Test ToolMetadata functionality."""

    def test_metadata_initialization(self):
        """Test ToolMetadata initialization."""
        metadata = ToolMetadata(
            name="test_tool",
            description="Test description",
            permissions=["project-read"],
            category="projects",
            version="1.0.0"
        )

        assert metadata.name == "test_tool"
        assert metadata.description == "Test description"
        assert metadata.permissions == ["project-read"]
        assert metadata.category == "projects"
        assert metadata.version == "1.0.0"

    def test_metadata_defaults(self):
        """Test ToolMetadata with default values."""
        metadata = ToolMetadata(
            name="test_tool",
            description="Test description",
            permissions=[]
        )

        assert metadata.category is None
        assert metadata.version == "1.0.0"

    def test_to_dict_serialization(self):
        """Test ToolMetadata serialization."""
        metadata = ToolMetadata(
            name="test_tool",
            description="Test description",
            permissions=["project-read", "admin"]
        )

        data = metadata.to_dict()
        assert data["name"] == "test_tool"
        assert data["description"] == "Test description"
        assert data["permissions"] == ["project-read", "admin"]
        assert data["category"] is None
        assert data["version"] == "1.0.0"

    def test_to_dict_with_category(self):
        """Test ToolMetadata serialization with category."""
        metadata = ToolMetadata(
            name="test_tool",
            description="Test description",
            permissions=["project-read"],
            category="projects"
        )

        data = metadata.to_dict()
        assert data["category"] == "projects"

    def test_multiple_permissions(self):
        """Test ToolMetadata with multiple permissions."""
        metadata = ToolMetadata(
            name="admin_tool",
            description="Admin tool",
            permissions=["read", "write", "delete"],
            category="admin"
        )

        assert len(metadata.permissions) == 3
        assert "write" in metadata.permissions
        assert "delete" in metadata.permissions
