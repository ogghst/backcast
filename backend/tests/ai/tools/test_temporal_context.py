"""Tests for ToolContext temporal parameters."""

import pytest
from datetime import datetime
from app.ai.tools.types import ToolContext
from sqlalchemy.ext.asyncio import AsyncSession


class TestToolContextTemporalParams:
    """Test ToolContext temporal parameter functionality."""

    @pytest.mark.asyncio
    async def test_toolcontext_with_temporal_params_accepts_values(
        self, db_session: AsyncSession
    ):
        """Test that ToolContext accepts and stores temporal parameters."""
        # Arrange
        as_of = datetime(2024, 1, 1, 12, 0, 0)
        branch_name = "BR-001"
        branch_mode = "isolated"

        # Act
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            user_role="admin",
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,  # type: ignore
        )

        # Assert
        assert context.as_of == as_of
        assert context.branch_name == branch_name
        assert context.branch_mode == branch_mode

    @pytest.mark.asyncio
    async def test_toolcontext_defaults_to_none(self, db_session: AsyncSession):
        """Test that ToolContext defaults temporal fields to None."""
        # Arrange & Act
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            user_role="admin",
        )

        # Assert
        assert context.as_of is None
        assert context.branch_name is None
        assert context.branch_mode is None

    @pytest.mark.asyncio
    async def test_toolcontext_with_partial_temporal_params(
        self, db_session: AsyncSession
    ):
        """Test that ToolContext accepts partial temporal parameters."""
        # Arrange
        as_of = datetime(2024, 1, 1, 12, 0, 0)

        # Act
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            user_role="admin",
            as_of=as_of,
        )

        # Assert
        assert context.as_of == as_of
        assert context.branch_name is None
        assert context.branch_mode is None
