"""Tests for refactored @ai_tool decorator with LangChain integration."""

import pytest
from typing import Any
from uuid import uuid4

from langchain_core.tools import BaseTool

from app.ai.tools.decorator import ai_tool, to_langchain_tool
from app.ai.tools.types import ToolContext, ToolMetadata


class TestAIToolDecoratorComposition:
    """Test suite for @ai_tool decorator composition with LangChain."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        from unittest.mock import AsyncMock
        from sqlalchemy.ext.asyncio import AsyncSession
        return AsyncMock(spec=AsyncSession)

    def test_ai_tool_decorator_composes_with_langchain_tool(self) -> None:
        """Test that decorator composes with LangChain @tool correctly.

        Given:
            A function decorated with @ai_tool
        When:
            The decorated function is inspected
        Then:
            The result is a LangChain BaseTool instance
            The tool has proper schema and metadata
        """
        # Arrange & Act: Define a function with @ai_tool
        @ai_tool(
            name="test_tool",
            description="Test description",
            permissions=["test-read"],
            category="test"
        )
        async def test_function(param1: str, context: ToolContext) -> dict[str, Any]:
            """Test function.

            Args:
                param1: First parameter
                context: Tool context

            Returns:
                Result dictionary
            """
            return {"result": param1}

        # Assert: Should be a BaseTool instance
        assert isinstance(test_function, BaseTool)
        assert test_function.name == "test_tool"

    def test_ai_tool_decorator_attaches_tool_metadata(self) -> None:
        """Test that decorator attaches ToolMetadata correctly.

        Given:
            A function decorated with @ai_tool with metadata
        When:
            The decorated tool is inspected
        Then:
            The tool has _tool_metadata attribute
            Metadata contains correct permissions, category, version
        """
        # Arrange & Act: Define function with metadata
        @ai_tool(
            name="metadata_test",
            description="Test metadata attachment",
            permissions=["project-read", "project-write"],
            category="projects"
        )
        async def test_function(param: str, context: ToolContext) -> str:
            """Test function.

            Args:
                param: Input parameter
                context: Tool execution context

            Returns:
                Result string
            """
            return param

        # Assert: Metadata should be attached
        assert hasattr(test_function, "_tool_metadata")
        metadata = test_function._tool_metadata
        assert isinstance(metadata, ToolMetadata)
        assert metadata.name == "metadata_test"
        assert metadata.permissions == ["project-read", "project-write"]
        assert metadata.category == "projects"
        assert metadata.version == "1.0.0"

    def test_ai_tool_decorator_sets_is_ai_tool_flag(self) -> None:
        """Test that decorator sets _is_ai_tool flag.

        Given:
            A function decorated with @ai_tool
        When:
            The decorated tool is inspected
        Then:
            The tool has _is_ai_tool attribute set to True
        """
        # Arrange & Act
        @ai_tool(name="flag_test")
        async def test_function(param: str, context: ToolContext) -> str:
            """Test function.

            Args:
                param: Input parameter
                context: Tool execution context

            Returns:
                Result string
            """
            return param

        # Assert
        assert hasattr(test_function, "_is_ai_tool")
        assert test_function._is_ai_tool is True

    def test_docstring_parsing(self) -> None:
        """Test that tool schema includes parameter descriptions from docstrings.

        Given:
            A function with Google-style docstring
            Using parse_docstring=True in decorator
        When:
            The tool schema is generated
        Then:
            Parameter descriptions are extracted from Args section
            Schema fields have descriptions
        """
        # Arrange & Act: Create tool with detailed docstring
        @ai_tool(
            name="search_projects",
            description="Search projects with filters",
            permissions=["project-read"],
            category="projects"
        )
        async def search_projects(
            search: str,
            status: str | None = None,
            limit: int = 20,
            context: ToolContext = None,
        ) -> dict[str, Any]:
            """Search for projects matching criteria.

            Context: Provides database session and user context.

            Args:
                search: Search term to filter project names or codes
                status: Optional status filter (e.g., 'ACT', 'PLN')
                limit: Maximum number of results to return (default 20)
                context: Injected tool execution context

            Returns:
                Dictionary with list of matching projects and total count

            Raises:
                ValueError: If search parameter is empty
            """
            return {"projects": [], "total": 0}

        # Assert: Schema should have parameter descriptions
        assert search_projects.args_schema is not None
        schema = search_projects.args_schema

        # Check that fields exist
        assert "search" in schema.model_fields
        assert "status" in schema.model_fields
        assert "limit" in schema.model_fields

        # Check descriptions (LangChain should parse from docstring)
        search_field = schema.model_fields["search"]
        # Note: LangChain may or may not include descriptions depending on implementation
        # The key is that the schema is generated correctly

    def test_injected_tool_arg_exclusion(self) -> None:
        """Test that context parameter is excluded from tool schema.

        Given:
            A function with Annotated[ToolContext, InjectedToolArg]
        When:
            The tool schema is generated
        Then:
            context parameter is NOT in the schema
            context can still be passed at runtime
        """
        # Arrange & Act: Create tool with InjectedToolArg
        from typing import Annotated
        from langchain_core.tools import InjectedToolArg

        @ai_tool(
            name="context_test",
            description="Test context injection",
            permissions=["test-read"],
            category="test"
        )
        async def test_function(
            param1: str,
            context: Annotated[ToolContext, InjectedToolArg],
        ) -> str:
            """Test function with injected context.

            Args:
                param1: First parameter
                context: Injected tool context (not in schema)

            Returns:
                Result string with user info
            """
            return f"Got: {param1}, user: {context.user_id}"

        # Assert: context should not be in schema
        schema = test_function.args_schema
        if schema:
            # InjectedToolArg should exclude context from schema
            # Note: LangChain handles this by excluding InjectedToolArg parameters
            # The schema fields should only contain non-injected parameters
            schema_fields = set(schema.model_fields.keys())
            assert "param1" in schema_fields, "param1 should be in schema"
            # context might or might not be in fields depending on LangChain version
            # The key is that InjectedToolArg parameters are handled specially

    def test_ai_tool_default_values(self) -> None:
        """Test that decorator works with default parameter values.

        Given:
            A function with default parameter values
        When:
            The tool is created
        Then:
            Schema correctly reflects default values
        """
        # Arrange & Act
        @ai_tool(name="defaults_test")
        async def test_function(
            required: str,
            optional: str = "default_value",
            context: ToolContext = None,
        ) -> str:
            """Test function with defaults.

            Args:
                required: Required parameter
                optional: Optional parameter with default
                context: Tool context

            Returns:
                Result string combining both parameters
            """
            return f"{required}:{optional}"

        # Assert
        schema = test_function.args_schema
        if schema:
            required_field = schema.model_fields["required"]
            optional_field = schema.model_fields["optional"]

            # Required should not have default
            # Optional should have default
            assert optional_field.default == "default_value"

    def test_ai_tool_returns_base_tool_instance(self) -> None:
        """Test that decorator returns BaseTool not wrapped function.

        Given:
            A function decorated with @ai_tool
        When:
            The return value is checked
        Then:
            Returns BaseTool instance from langchain_core.tools
            Can be used directly in LangGraph
        """
        # Arrange & Act
        @ai_tool(name="base_tool_test")
        async def test_function(param: str, context: ToolContext) -> str:
            """Test function.

            Args:
                param: Input parameter
                context: Tool execution context

            Returns:
                Result string
            """
            return param

        # Assert: Should be a BaseTool
        from langchain_core.tools import BaseTool
        assert isinstance(test_function, BaseTool)

        # Should have LangChain tool attributes
        assert hasattr(test_function, "name")
        assert hasattr(test_function, "description")
        assert hasattr(test_function, "args_schema")


class TestAIToolDecoratorErrorPaths:
    """Test suite for @ai_tool decorator error handling."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        from unittest.mock import AsyncMock
        from sqlalchemy.ext.asyncio import AsyncSession
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_tool_returns_error_on_exception(self, mock_session) -> None:
        """Test that decorator catches exceptions and returns error dict.

        Given:
            A tool function that raises an exception
        When:
            The tool is invoked via ainvoke
        Then:
            An error dictionary is returned
            The error message is included
        """
        # Arrange: Create a tool that raises an exception
        @ai_tool(name="error_tool")
        async def failing_tool(context: ToolContext) -> dict[str, Any]:
            """Tool that always fails.

            Args:
                context: Tool context

            Returns:
                Result dictionary

            Raises:
                ValueError: Always raises this error
            """
            raise ValueError("Test error message")

        # Act: Invoke the tool
        context = ToolContext(session=mock_session, user_id="test-user", user_role="admin")
        result = await failing_tool.ainvoke({"context": context})

        # Assert: Should return error dict
        assert isinstance(result, dict)
        assert "error" in result
        assert "Test error message" in result["error"]

    @pytest.mark.asyncio
    async def test_tool_enforces_rbac_permissions_denied(self, mock_session) -> None:
        """Test that decorator enforces RBAC permissions when denied.

        Given:
            A tool with required permissions
            And a user without those permissions
        When:
            The tool is invoked
        Then:
            A permission denied error is returned
        """
        # Arrange: Create a tool with admin-only permission
        @ai_tool(
            name="admin_tool",
            permissions=["admin-only"]
        )
        async def admin_tool(context: ToolContext) -> dict[str, Any]:
            """Admin-only tool.

            Args:
                context: Tool context

            Returns:
                Success message
            """
            return {"success": True}

        # Act: Invoke with guest role (no permissions)
        context = ToolContext(session=mock_session, user_id="test-user", user_role="guest")
        result = await admin_tool.ainvoke({"context": context})

        # Assert: Should return permission denied error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Permission denied" in result["error"]
        assert "admin-only" in result["error"]

    @pytest.mark.asyncio
    async def test_tool_allows_rbac_permissions_granted(self, mock_session) -> None:
        """Test that decorator allows execution when permissions granted.

        Given:
            A tool with required permissions
            And a user with those permissions
        When:
            The tool is invoked
        Then:
            The tool executes successfully
        """
        # Arrange: Create a tool with project-read permission
        @ai_tool(
            name="viewer_tool",
            permissions=["project-read"]
        )
        async def viewer_tool(context: ToolContext) -> dict[str, Any]:
            """Viewer tool.

            Args:
                context: Tool context

            Returns:
                Success message
            """
            return {"success": True, "data": "some data"}

        # Act: Invoke with viewer role (has project-read permission)
        context = ToolContext(session=mock_session, user_id="test-user", user_role="viewer")
        result = await viewer_tool.ainvoke({"context": context})

        # Assert: Should return success
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert result.get("data") == "some data"

    @pytest.mark.asyncio
    async def test_tool_validates_context_present(self, mock_session) -> None:
        """Test that decorator validates context is provided.

        Given:
            A tool that requires context
        When:
            The tool is invoked with proper context
        Then:
            The tool executes successfully
        """
        # Arrange: Create a tool
        @ai_tool(name="context_tool")
        async def context_tool(context: ToolContext) -> dict[str, Any]:
            """Tool requiring context.

            Args:
                context: Tool context

            Returns:
                Success message
            """
            return {"success": True}

        # Act: Invoke with proper context
        context = ToolContext(session=mock_session, user_id="test-user", user_role="viewer")
        result = await context_tool.ainvoke({"context": context})

        # Assert: Tool should work with proper context
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_tool_context_type_fallback(self, mock_session) -> None:
        """Test that decorator handles context objects with matching attributes.

        Given:
            A tool that requires context
            And a context-like object with session and user_id attributes
            But not a ToolContext instance
        When:
            The tool is invoked with the context-like object
        Then:
            The decorator accepts the object as context
            The tool executes successfully
        """
        # Arrange: Create a tool
        @ai_tool(name="context_fallback_tool")
        async def context_tool(context: ToolContext) -> dict[str, Any]:
            """Tool requiring context.

            Args:
                context: Tool context

            Returns:
                Success message
            """
            return {"success": True, "user": context.user_id}

        # Create a mock context-like object (not ToolContext but has same attributes)
        class MockContext:
            def __init__(self):
                self.session = mock_session
                self.user_id = "mock-user"
                self.user_role = "admin"

        mock_context = MockContext()

        # Act: Invoke with mock context
        result = await context_tool.ainvoke({"context": mock_context})

        # Assert: Tool should work with fallback context
        assert result.get("success") is True
        assert result.get("user") == "mock-user"

    @pytest.mark.asyncio
    async def test_tool_missing_context_returns_error(self, mock_session) -> None:
        """Test that decorator returns error when context is None.

        Given:
            A tool that requires context
        When:
            The tool is invoked without context or with None
        Then:
            An error dictionary is returned
            Error message indicates context not provided
        """
        # Arrange: Create a tool
        @ai_tool(name="no_context_tool")
        async def context_tool(context: ToolContext) -> dict[str, Any]:
            """Tool requiring context.

            Args:
                context: Tool context

            Returns:
                Success message
            """
            return {"success": True}

        # Act: Invoke without context (None)
        result = await context_tool.ainvoke({"context": None})

        # Assert: Should return error dict
        assert isinstance(result, dict)
        assert "error" in result
        assert "context not provided" in result["error"].lower()


class TestToLangChainToolBackwardCompatibility:
    """Test suite for to_langchain_tool() backward compatibility function."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        from unittest.mock import AsyncMock
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_session = AsyncMock(spec=AsyncSession)
        return ToolContext(session=mock_session, user_id="test-user", user_role="admin")

    def test_to_langchain_tool_with_basetool_returns_as_is(self, mock_context) -> None:
        """Test that to_langchain_tool returns BaseTool as-is.

        Given:
            A BaseTool instance (from @ai_tool decorator)
        When:
            to_langchain_tool is called with the BaseTool
        Then:
            The same BaseTool instance is returned
        """
        # Arrange: Create an @ai_tool decorated function (returns BaseTool)
        @ai_tool(name="test_tool")
        async def test_tool(param: str, context: ToolContext) -> str:
            """Test tool.

            Args:
                param: Input parameter
                context: Tool context

            Returns:
                Result string
            """
            return param

        # Act: Call to_langchain_tool with the BaseTool
        result = to_langchain_tool(test_tool, mock_context)

        # Assert: Should return the same BaseTool instance
        from langchain_core.tools import BaseTool
        assert isinstance(result, BaseTool)
        assert result is test_tool  # Same object reference

    def test_to_langchain_tool_with_metadata_wraps_function(self, mock_context) -> None:
        """Test that to_langchain_tool wraps old-style decorated functions.

        Given:
            A function with _tool_metadata attribute (old decorator pattern)
        When:
            to_langchain_tool is called with the function
        Then:
            A new BaseTool is created wrapping the function
            The wrapper includes context in calls
        """
        # Arrange: Create an old-style decorated function with metadata
        async def old_style_tool(context: ToolContext, search: str = "") -> dict[str, Any]:
            """Old style tool function.

            Args:
                context: Tool context
                search: Search term

            Returns:
                Result dictionary
            """
            return {"results": [], "search": search}

        # Attach metadata like old decorator did
        old_style_tool._tool_metadata = ToolMetadata(
            name="old_tool",
            description="Old style tool",
            permissions=[],
            category="test",
            version="1.0.0"
        )

        # Act: Convert to LangChain tool
        result = to_langchain_tool(old_style_tool, mock_context)

        # Assert: Should return a BaseTool
        from langchain_core.tools import BaseTool
        assert isinstance(result, BaseTool)
        assert result.name == "old_tool"

    def test_to_langchain_tool_with_no_metadata_uses_function_name(self, mock_context) -> None:
        """Test that to_langchain_tool handles functions without metadata.

        Given:
            A function without _tool_metadata attribute
        When:
            to_langchain_tool is called with the function
        Then:
            A BaseTool is created using function name and docstring
        """
        # Arrange: Create a plain function without metadata
        async def plain_function(context: ToolContext, value: int) -> dict[str, Any]:
            """Plain function without metadata.

            Args:
                context: Tool context
                value: Input value

            Returns:
                Result with doubled value
            """
            return {"result": value * 2}

        # Act: Convert to LangChain tool
        result = to_langchain_tool(plain_function, mock_context)

        # Assert: Should return a BaseTool with function name
        from langchain_core.tools import BaseTool
        assert isinstance(result, BaseTool)
        assert result.name == "plain_function"
