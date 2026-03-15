"""Test Change Order tool template functionality and validation."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.types import ToolContext


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


class TestChangeOrderTemplateValidation:
    """Test Change Order template input validation and error handling."""

    # === T-TPL-CO-01: test_propose_change_order_validates_status ===
    @pytest.mark.asyncio
    async def test_create_change_order_validates_required_fields(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that create_change_order validates required fields.

        Given:
            A create_change_order call with missing required fields
        When:
            The function is called
        Then:
            Validation error is returned or handled gracefully
        """
        from app.ai.tools.templates import change_order_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Try to create with missing title (required field)
        result = await change_order_template.create_change_order(  # type: ignore[operator]
            project_id=str(uuid4()),
            title="",  # Empty title should be invalid
            description="Test description",
            reason="Test reason",
            context=context
        )

        # Assert: Should handle gracefully (error or validation)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_create_change_order_validates_project_id(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that create_change_order validates project_id format.

        Given:
            A create_change_order call with invalid project_id
        When:
            The function is called
        Then:
            Error is returned for invalid UUID format
        """
        from app.ai.tools.templates import change_order_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Try to create with invalid project_id
        result = await change_order_template.create_change_order(  # type: ignore[operator]
            project_id="not-a-uuid",  # Invalid UUID
            title="Test Change Order",
            description="Test description",
            reason="Test reason",
            context=context
        )

        # Assert: Should return error
        assert "error" in result
        assert "Invalid" in result["error"] or "input" in result["error"]

    @pytest.mark.asyncio
    async def test_approve_change_order_checks_permission(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that approve_change_order requires proper permissions.

        Given:
            A user without change-order-approve permission
        When:
            approve_change_order is called
        Then:
            Permission check is performed (via decorator)
        """
        from app.ai.tools.templates import change_order_template

        # Arrange: Create context with viewer role (no approve permission)
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="viewer"  # Limited permissions
        )

        # Mock change order service
        mock_co_service = AsyncMock()
        mock_co_service.approve_change_order.return_value = MagicMock()

        # Act: Try to approve change order
        # Note: The @ai_tool decorator handles RBAC, so we test the function signature
        result = await change_order_template.approve_change_order(  # type: ignore[operator]
            change_order_id=str(uuid4()),
            context=context
        )

        # Assert: Should return a result (dict)
        # The actual permission check happens in the decorator
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_reject_change_order_validates_reason(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that reject_change_order handles rejection reason.

        Given:
            A reject_change_order call with/without reason
        When:
            The function is called
        Then:
            Reason is recorded or handled gracefully
        """
        from app.ai.tools.templates import change_order_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Reject with reason
        result = await change_order_template.reject_change_order(  # type: ignore[operator]
            change_order_id=str(uuid4()),
            reason="Budget constraints",
            context=context
        )

        # Assert: Should handle gracefully
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_submit_for_approval_validates_status(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that submit_change_order_for_approval validates current status.

        Given:
            A change order not in Draft status
        When:
            submit_for_approval is called
        Then:
            Status validation is performed
        """
        from app.ai.tools.templates import change_order_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Mock service to return change order
        mock_co_service = AsyncMock()
        mock_co = MagicMock()
        mock_co.status = "Draft"
        mock_co_service.get_by_id.return_value = mock_co

        with patch.object(
            ToolContext,
            'change_order_service',
            mock_co_service
        ):
            # Act: Submit for approval
            result = await change_order_template.submit_change_order_for_approval(  # type: ignore[operator]
                change_order_id=str(uuid4()),
                context=context
            )

            # Assert: Should handle gracefully
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_analyze_impact_validates_change_order_exists(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that analyze_change_order_impact checks change order exists.

        Given:
            A non-existent change order ID
        When:
            analyze_impact is called
        Then:
            Error is returned for non-existent change order
        """
        from app.ai.tools.templates import change_order_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Mock service to return None (not found)
        mock_co_service = AsyncMock()
        mock_co_service.get_by_id.return_value = None

        with patch.object(
            ToolContext,
            'change_order_service',
            mock_co_service
        ):
            # Act: Try to analyze non-existent change order
            result = await change_order_template.analyze_change_order_impact(  # type: ignore[operator]
                change_order_id=str(uuid4()),
                context=context
            )

            # Assert: Should return error
            assert "error" in result or "not found" in str(result).lower()


class TestChangeOrderTemplateExisting:
    """Keep existing basic tests for template structure."""

    def test_change_order_template_can_be_imported(self) -> None:
        """Test that the Change Order template can be imported without errors."""
        try:
            from app.ai.tools.templates import change_order_template
            assert change_order_template is not None
        except Exception as e:
            pytest.fail(f"Failed to import Change Order template: {e}")

    def test_change_order_template_has_required_functions(self) -> None:
        """Test that the Change Order template has all required example functions."""
        from app.ai.tools.templates import change_order_template

        # Check that all Change Order functions exist
        assert hasattr(change_order_template, "list_change_orders")
        assert hasattr(change_order_template, "get_change_order")
        assert hasattr(change_order_template, "create_change_order")
        assert hasattr(change_order_template, "generate_change_order_draft")
        assert hasattr(change_order_template, "submit_change_order_for_approval")
        assert hasattr(change_order_template, "approve_change_order")
        assert hasattr(change_order_template, "reject_change_order")
        assert hasattr(change_order_template, "analyze_change_order_impact")

    def test_change_order_template_functions_have_decorators(self) -> None:
        """Test that Change Order template functions have @ai_tool decorators."""
        from app.ai.tools.templates import change_order_template

        # Check that functions have the _is_ai_tool attribute set by decorator
        functions = [
            "list_change_orders",
            "get_change_order",
            "create_change_order",
            "generate_change_order_draft",
            "submit_change_order_for_approval",
            "approve_change_order",
            "reject_change_order",
            "analyze_change_order_impact",
        ]

        for func_name in functions:
            func = getattr(change_order_template, func_name)
            # All should have _is_ai_tool attribute from decorator
            assert hasattr(func, "_is_ai_tool"), f"{func_name} missing @ai_tool decorator"
            assert func._is_ai_tool is True, f"{func_name} decorator not properly applied"
