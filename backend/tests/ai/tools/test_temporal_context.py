"""Tests for ToolContext temporal parameters."""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.temporal_tools import get_temporal_context
from app.ai.tools.types import ToolContext


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

    @pytest.mark.asyncio
    async def test_get_temporal_context_includes_current_date_field(
        self, db_session: AsyncSession
    ):
        """Test that get_temporal_context returns both ISO and human-readable date formats."""
        # Arrange
        as_of = datetime(2025, 6, 15, 12, 30, 45)
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            user_role="admin",
            as_of=as_of,
            branch_name="feature-1",
            branch_mode="isolated",  # type: ignore
        )

        # Act
        result = await get_temporal_context.ainvoke({"context": context})

        # Assert
        # Check ISO format still exists in as_of field
        assert result["as_of"] == "2025-06-15T12:30:45"
        # Check new human-readable format in current_date field
        assert result["current_date"] == "Sunday, June 15, 2025 at 12:30 PM"
        # Check other fields still exist
        assert result["branch_name"] == "feature-1"
        assert result["branch_mode"] == "isolated"

    @pytest.mark.asyncio
    async def test_get_temporal_context_with_none_as_of(self, db_session: AsyncSession):
        """Test that get_temporal_context uses system time for current_date when as_of is None."""
        # Arrange
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            user_role="admin",
        )

        # Act
        result = await get_temporal_context.ainvoke({"context": context})

        # Assert
        # as_of should be None (no time-travel active)
        assert result["as_of"] is None
        # current_date should be system time (not None)
        assert result["current_date"] is not None
        assert isinstance(result["current_date"], str)
        # Verify format: "DayOfWeek, MonthName DD, YYYY at HH:MM AM/PM"
        # Examples: "Monday, March 31, 2026 at 03:45 PM"
        import re

        date_pattern = r"^[A-Za-z]+, [A-Za-z]+ \d{1,2}, \d{4} at \d{1,2}:\d{2} [AP]M$"
        assert re.match(date_pattern, result["current_date"]), (
            f"current_date '{result['current_date']}' does not match expected format"
        )
        # Other fields should have defaults
        assert result["branch_name"] == "main"
        assert result["branch_mode"] == "merged"

    @pytest.mark.asyncio
    async def test_get_temporal_context_with_midnight_time(
        self, db_session: AsyncSession
    ):
        """Test that get_temporal_context formats midnight time correctly."""
        # Arrange
        as_of = datetime(2025, 6, 15, 0, 0, 0)
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            user_role="admin",
            as_of=as_of,
        )

        # Act
        result = await get_temporal_context.ainvoke({"context": context})

        # Assert
        assert result["as_of"] == "2025-06-15T00:00:00"
        assert result["current_date"] == "Sunday, June 15, 2025 at 12:00 AM"

    @pytest.mark.asyncio
    async def test_get_temporal_context_with_noon_time(self, db_session: AsyncSession):
        """Test that get_temporal_context formats noon time correctly."""
        # Arrange
        as_of = datetime(2025, 6, 15, 12, 0, 0)
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            user_role="admin",
            as_of=as_of,
        )

        # Act
        result = await get_temporal_context.ainvoke({"context": context})

        # Assert
        assert result["as_of"] == "2025-06-15T12:00:00"
        assert result["current_date"] == "Sunday, June 15, 2025 at 12:00 PM"
