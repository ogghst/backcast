"""Tests for ToolContext temporal parameters and set_temporal_context tool."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.temporal_tools import get_temporal_context, set_temporal_context
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

class TestSetTemporalContext:
    """Test set_temporal_context tool functionality."""

    @pytest.mark.asyncio
    async def test_change_as_of_date(self, db_session: AsyncSession):
        """Test changing only the as_of date."""
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            user_role="admin",
        )

        result = await set_temporal_context.ainvoke(
            {"as_of": "2025-01-15", "context": context}
        )

        assert result["success"] is True
        assert "as_of" in result["changes"]
        assert result["changes"]["as_of"]["from"] is None
        assert result["changes"]["as_of"]["to"] == "2025-01-15T00:00:00"
        assert context.as_of == datetime(2025, 1, 15)

    @pytest.mark.asyncio
    async def test_change_branch_name(self, db_session: AsyncSession):
        """Test changing only the branch name to main (always valid)."""
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            user_role="admin",
            branch_name="main",
        )

        result = await set_temporal_context.ainvoke(
            {"branch_mode": "isolated", "context": context}
        )

        assert result["success"] is True
        assert "branch_mode" in result["changes"]
        assert result["changes"]["branch_mode"]["from"] == "merged"
        assert result["changes"]["branch_mode"]["to"] == "isolated"
        assert context.branch_mode == "isolated"

    @pytest.mark.asyncio
    async def test_change_multiple_params(self, db_session: AsyncSession):
        """Test changing multiple parameters at once."""
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            user_role="admin",
        )

        result = await set_temporal_context.ainvoke(
            {"as_of": "2025-03-01", "branch_mode": "isolated", "context": context}
        )

        assert result["success"] is True
        assert len(result["changes"]) == 2
        assert context.as_of == datetime(2025, 3, 1)
        assert context.branch_mode == "isolated"

    @pytest.mark.asyncio
    async def test_unset_params_remain_unchanged(self, db_session: AsyncSession):
        """Test that unset parameters remain unchanged."""
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            user_role="admin",
            branch_name="BR-001",
            branch_mode="isolated",  # type: ignore
        )

        result = await set_temporal_context.ainvoke(
            {"as_of": "2025-01-15", "context": context}
        )

        assert result["success"] is True
        assert "branch_name" not in result["changes"]
        assert "branch_mode" not in result["changes"]
        assert context.branch_name == "BR-001"
        assert context.branch_mode == "isolated"

    @pytest.mark.asyncio
    async def test_error_no_params_provided(self, db_session: AsyncSession):
        """Test error when no parameters are provided."""
        context = ToolContext(
            session=db_session,
            user_id="user-123",
        )

        result = await set_temporal_context.ainvoke({"context": context})

        assert "error" in result
        assert "At least one parameter" in result["error"]

    @pytest.mark.asyncio
    async def test_error_invalid_as_of_format(self, db_session: AsyncSession):
        """Test error with invalid date format."""
        context = ToolContext(
            session=db_session,
            user_id="user-123",
        )

        result = await set_temporal_context.ainvoke(
            {"as_of": "not-a-date", "context": context}
        )

        assert "error" in result
        assert "Invalid as_of format" in result["error"]

    @pytest.mark.asyncio
    async def test_error_invalid_branch_mode(self, db_session: AsyncSession):
        """Test error with invalid branch mode."""
        context = ToolContext(
            session=db_session,
            user_id="user-123",
        )

        result = await set_temporal_context.ainvoke(
            {"branch_mode": "invalid", "context": context}
        )

        assert "error" in result
        assert "Invalid branch_mode" in result["error"]

    @pytest.mark.asyncio
    async def test_reset_as_of_to_now(self, db_session: AsyncSession):
        """Test resetting as_of to current time."""
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            as_of=datetime(2025, 1, 15),
        )

        result = await set_temporal_context.ainvoke(
            {"as_of": "now", "context": context}
        )

        assert result["success"] is True
        assert context.as_of is None

    @pytest.mark.asyncio
    async def test_publishes_event_on_bus(self, db_session: AsyncSession):
        """Test that tool publishes event when event bus is available."""
        mock_bus = MagicMock()
        context = ToolContext(
            session=db_session,
            user_id="user-123",
            _event_bus=mock_bus,
        )

        result = await set_temporal_context.ainvoke(
            {"branch_mode": "isolated", "context": context}
        )

        assert result["success"] is True
        mock_bus.publish.assert_called_once()
        event = mock_bus.publish.call_args[0][0]
        assert event.event_type == "temporal_context_change"
        assert event.data["branch_mode"] == "isolated"

    @pytest.mark.asyncio
    async def test_no_event_when_bus_is_none(self, db_session: AsyncSession):
        """Test that tool works without event bus."""
        context = ToolContext(
            session=db_session,
            user_id="user-123",
        )

        result = await set_temporal_context.ainvoke(
            {"branch_mode": "merged", "context": context}
        )

        assert result["success"] is True
        assert context.branch_mode == "merged"
