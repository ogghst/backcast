"""Tests for ToolContext user_role field."""

from uuid import uuid4

from app.ai.tools.types import ToolContext


class TestToolContextUserRole:
    """Test suite for ToolContext.user_role field."""

    def test_tool_context_user_role_field(self) -> None:
        """Test that ToolContext accepts and stores user_role.

        Given:
            A ToolContext dataclass with user_role field
        When:
            ToolContext is instantiated with user_role parameter
        Then:
            The user_role field is correctly stored
            The field has the correct type annotation
        """
        # Arrange: Create a mock session and user_role

        mock_session = None  # We'll use a mock
        user_id = str(uuid4())
        user_role = "admin"

        # Act: Create ToolContext with user_role
        context = ToolContext(
            session=mock_session,  # type: ignore[arg-type]
            user_id=user_id,
            user_role=user_role,
        )

        # Assert: user_role is stored correctly
        assert context.user_role == user_role
        assert context.user_id == user_id

    def test_tool_context_user_role_type_annotation(self) -> None:
        """Test that ToolContext.user_role has correct type annotation.

        Given:
            A ToolContext dataclass
        When:
            The type hints are inspected
        Then:
            user_role field has type str
        """
        # Arrange & Act: Get type hints
        import typing

        hints = typing.get_type_hints(ToolContext)

        # Assert: user_role should be annotated as str
        assert "user_role" in hints
        assert hints["user_role"] is str

    def test_tool_context_user_role_backward_compatible(self) -> None:
        """Test that ToolContext works without user_role (backward compatibility).

        Given:
            Existing code that creates ToolContext without user_role
        When:
            ToolContext is instantiated without user_role parameter
        Then:
            The instantiation should work with a default value
        """
        # Arrange: Create a mock session
        mock_session = None  # We'll use a mock
        user_id = str(uuid4())

        # Act: Create ToolContext without user_role (should use default)
        context = ToolContext(
            session=mock_session,  # type: ignore[arg-type]
            user_id=user_id,
        )

        # Assert: user_role should have a default value
        # This will be an empty string or some default
        assert hasattr(context, "user_role")

    def test_tool_context_with_all_fields(self) -> None:
        """Test that ToolContext works with all fields including user_role.

        Given:
            A ToolContext with session, user_id, and user_role
        When:
            ToolContext is fully populated
        Then:
            All fields are correctly accessible
        """
        # Arrange
        mock_session = None  # We'll use a mock
        user_id = str(uuid4())
        user_role = "viewer"

        # Act
        context = ToolContext(
            session=mock_session,  # type: ignore[arg-type]
            user_id=user_id,
            user_role=user_role,
        )

        # Assert
        assert context.user_id == user_id
        assert context.user_role == user_role
        # _root_session stores the original session
        assert context._root_session == mock_session
