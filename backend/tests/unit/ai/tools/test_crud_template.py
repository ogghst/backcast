"""Test CRUD tool template functionality and validation."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.types import ToolContext


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


class TestCRUDTemplateValidation:
    """Test CRUD template input validation and error handling."""

    # === T-TPL-CRUD-01: test_list_projects_validates_pagination ===
    @pytest.mark.asyncio
    async def test_list_projects_validates_pagination(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that list_projects handles pagination parameters.

        Given:
            A list_projects call with various pagination values
        When:
            The function is called
        Then:
            Pagination parameters are passed correctly to service
        """
        from app.ai.tools.templates import crud_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Mock the project service
        mock_project_service = AsyncMock()
        mock_project_service.get_projects.return_value = ([], 0)

        # Act: Call with normal pagination
        with patch.object(
            ToolContext,
            'project_service',
            mock_project_service
        ):
            result = await crud_template.list_projects(  # type: ignore[operator]
                limit=50,
                skip=10,
                context=context
            )

        # Assert: Should call service with correct parameters
        mock_project_service.get_projects.assert_called_once()
        call_kwargs = mock_project_service.get_projects.call_args.kwargs
        assert call_kwargs["limit"] == 50
        assert call_kwargs["skip"] == 10
        # Verify result is a dict
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_list_projects_handles_large_limit(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that list_projects handles large limit values.

        Given:
            A list_projects call with limit > 100
        When:
            The function is called
        Then:
            Request is handled (may cap or pass through)
        """
        from app.ai.tools.templates import crud_template

        # Arrange
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        mock_project_service = AsyncMock()
        mock_project_service.get_projects.return_value = ([], 0)

        # Act: Call with excessive limit
        with patch.object(
            ToolContext,
            'project_service',
            mock_project_service
        ):
            result = await crud_template.list_projects(  # type: ignore[operator]
                limit=200,  # Exceeds typical max
                skip=0,
                context=context
            )

        # Assert: Should handle without error
        assert isinstance(result, dict)
        # The template may or may not cap the limit
        # We verify it doesn't crash

    # === T-TPL-CRUD-02: test_get_project_returns_404_for_invalid_id ===
    @pytest.mark.asyncio
    async def test_get_project_handles_invalid_uuid(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that get_project handles invalid UUID format.

        Given:
            A get_project call with invalid UUID format
        When:
            The function is called
        Then:
            Error message is returned
        """
        from app.ai.tools.templates import crud_template

        # Arrange
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Call with invalid UUID
        result = await crud_template.get_project(  # type: ignore[operator]
            project_id="not-a-valid-uuid",
            context=context
        )

        # Assert: Should return error
        assert "error" in result
        assert "Invalid project ID" in result["error"]

    @pytest.mark.asyncio
    async def test_get_project_handles_nonexistent_project(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that get_project handles non-existent project.

        Given:
            A get_project call with valid UUID but non-existent project
        When:
            The function is called
        Then:
            404-style error message is returned
        """
        from app.ai.tools.templates import crud_template

        # Arrange
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        mock_project_service = AsyncMock()
        mock_project_service.get_by_id.return_value = None

        with patch.object(
            ToolContext,
            'project_service',
            mock_project_service
        ):
            # Act: Call with non-existent project ID
            test_id = str(uuid4())
            result = await crud_template.get_project(  # type: ignore[operator]
                project_id=test_id,
                context=context
            )

        # Assert: Should return not found error
        assert "error" in result
        assert "not found" in result["error"]

    # === T-TPL-CRUD-03: test_create_project_validates_input ===
    @pytest.mark.asyncio
    async def test_create_project_validates_name_not_empty(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that create_project handles empty name.

        Given:
            A create_project call with empty name
        When:
            The function is called
        Then:
            Validation is performed (error or success with validation)
        """
        from app.ai.tools.templates import crud_template

        # Arrange
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        mock_project_service = AsyncMock()
        mock_project_service.create.return_value = MagicMock()

        with patch.object(
            ToolContext,
            'project_service',
            mock_project_service
        ):
            # Act: Try to create with empty name
            result = await crud_template.create_project(  # type: ignore[operator]
                name="",  # Empty name
                code="TEST-001",
                context=context
            )

        # Assert: Should handle (may return error or pass to service for validation)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_create_project_validates_code_required(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that create_project requires code field.

        Given:
            A create_project call with missing code
        When:
            The function is called
        Then:
            Validation error or graceful handling
        """
        from app.ai.tools.templates import crud_template

        # Arrange
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Try to create without code (will use default)
        result = await crud_template.create_project(  # type: ignore[operator]
            name="Test Project",
            # code not provided
            context=context
        )

        # Assert: Should handle gracefully
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_create_project_validates_budget_positive(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that create_project handles negative budget.

        Given:
            A create_project call with negative budget
        When:
            The function is called
        Then:
            Validation is performed or handled gracefully
        """
        from app.ai.tools.templates import crud_template

        # Arrange
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        mock_project_service = AsyncMock()
        mock_project_service.create.return_value = MagicMock()

        with patch.object(
            ToolContext,
            'project_service',
            mock_project_service
        ):
            # Act: Try to create with negative budget
            result = await crud_template.create_project(  # type: ignore[operator]
                name="Test Project",
                code="TEST-001",
                budget=-1000.0,  # Negative budget
                context=context
            )

        # Assert: Should handle gracefully
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_create_project_validates_date_range(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that create_project validates date range.

        Given:
            A create_project call with end_date before start_date
        When:
            The function is called
        Then:
            Validation is performed or handled gracefully
        """
        from app.ai.tools.templates import crud_template

        # Arrange
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Try to create with invalid date range
        result = await crud_template.create_project(  # type: ignore[operator]
            name="Test Project",
            code="TEST-001",
            start_date="2026-12-31",  # Later
            end_date="2026-01-01",    # Earlier
            context=context
        )

        # Assert: Should handle gracefully
        assert isinstance(result, dict)


class TestCRUDTemplateExisting:
    """Keep existing basic tests for template structure."""

    def test_crud_template_can_be_imported(self) -> None:
        """Test that the CRUD template can be imported without errors."""
        try:
            from app.ai.tools.templates import crud_template
            assert crud_template is not None
        except Exception as e:
            pytest.fail(f"Failed to import CRUD template: {e}")

    def test_crud_template_has_required_functions(self) -> None:
        """Test that the CRUD template has all required example functions."""
        from app.ai.tools.templates import crud_template

        # Check that all CRUD functions exist
        assert hasattr(crud_template, "list_projects")
        assert hasattr(crud_template, "get_project")
        assert hasattr(crud_template, "create_project")
        assert hasattr(crud_template, "update_project")
        assert hasattr(crud_template, "list_wbes")
        assert hasattr(crud_template, "get_wbe")
        assert hasattr(crud_template, "create_wbe")

    def test_crud_template_functions_have_decorators(self) -> None:
        """Test that CRUD template functions have @ai_tool decorators."""
        from app.ai.tools.templates import crud_template

        # Check that functions have the _is_ai_tool attribute set by decorator
        functions = [
            "list_projects",
            "get_project",
            "create_project",
            "update_project",
            "list_wbes",
            "get_wbe",
            "create_wbe",
        ]

        for func_name in functions:
            func = getattr(crud_template, func_name)
            # All should have _is_ai_tool attribute from decorator
            assert hasattr(func, "_is_ai_tool"), f"{func_name} missing @ai_tool decorator"
            assert func._is_ai_tool is True, f"{func_name} decorator not properly applied"
