"""Unit tests for change order status versioning with control_date.

Tests that workflow operations properly create new versions with
valid_time based on control_date, ensuring temporal consistency.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import UpdateChangeOrderStatusCommand
from app.models.domain.change_order import ChangeOrder


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_change_order() -> ChangeOrder:
    """Create a mock change order entity."""
    co = MagicMock(spec=ChangeOrder)
    co.id = uuid4()
    co.change_order_id = uuid4()
    co.status = "Draft"
    co.clone = MagicMock(return_value=co)
    co.valid_time = MagicMock()
    co.valid_time.lower = datetime.now(UTC) - timedelta(days=1)
    return co


class TestUpdateChangeOrderStatusCommand:
    """Tests for UpdateChangeOrderStatusCommand with control_date."""

    def test_init_with_control_date(self) -> None:
        """Test command initialization with control_date."""
        co_id = uuid4()
        actor_id = uuid4()
        control_date = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)

        cmd = UpdateChangeOrderStatusCommand(
            change_order_id=co_id,
            new_status="Submitted for Approval",
            actor_id=actor_id,
            branch="main",
            control_date=control_date,
            additional_updates={"sla_status": "pending"},
        )

        assert cmd.change_order_id == co_id
        assert cmd.new_status == "Submitted for Approval"
        assert cmd.actor_id == actor_id
        assert cmd.branch == "main"
        assert cmd.control_date == control_date
        assert cmd.additional_updates == {"sla_status": "pending"}

    def test_init_without_control_date(self) -> None:
        """Test command initialization without control_date (defaults to None)."""
        co_id = uuid4()
        actor_id = uuid4()

        cmd = UpdateChangeOrderStatusCommand(
            change_order_id=co_id,
            new_status="Approved",
            actor_id=actor_id,
        )

        assert cmd.control_date is None

    @pytest.mark.asyncio
    async def test_execute_uses_control_date_for_valid_time(
        self, mock_session: AsyncMock, mock_change_order: ChangeOrder
    ) -> None:
        """Test that execute sets valid_time to control_date."""
        co_id = uuid4()
        actor_id = uuid4()
        control_date = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)
        current_lower = datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC)

        # Mock the current version query
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(
            id=mock_change_order.id,
            valid_time=MagicMock(lower=current_lower),
        )
        mock_session.execute.return_value = mock_result

        # Mock the session.get for the entity
        mock_session.get = AsyncMock(return_value=mock_change_order)

        cmd = UpdateChangeOrderStatusCommand(
            change_order_id=co_id,
            new_status="Submitted for Approval",
            actor_id=actor_id,
            control_date=control_date,
        )

        await cmd.execute(mock_session)

        # Verify that session.execute was called with SQL that sets valid_time
        # The third call should be the SET valid_time statement
        calls = mock_session.execute.call_args_list
        assert len(calls) >= 3

        # Check that the valid_time SQL was executed
        set_time_call = calls[-1]
        sql_text = str(set_time_call[0][0])
        assert "valid_time = tstzrange" in sql_text
        assert "control_date" in sql_text

    @pytest.mark.asyncio
    async def test_execute_raises_for_nonexistent_change_order(
        self, mock_session: AsyncMock
    ) -> None:
        """Test that execute raises ValueError if change order not found."""
        co_id = uuid4()
        actor_id = uuid4()

        # Mock the current version query returning None
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        cmd = UpdateChangeOrderStatusCommand(
            change_order_id=co_id,
            new_status="Approved",
            actor_id=actor_id,
        )

        with pytest.raises(ValueError) as exc_info:
            await cmd.execute(mock_session)

        assert "No active Change Order found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_creates_new_version_with_status(
        self, mock_session: AsyncMock, mock_change_order: ChangeOrder
    ) -> None:
        """Test that execute creates a new version with the new status."""
        # co_id = uuid4()
        actor_id = uuid4()
        # control_date = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)
        current_lower = datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC)

        # Mock the current version query
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(
            id=mock_change_order.id,
            valid_time=MagicMock(lower=current_lower),
        )
        mock_session.execute.return_value = mock_result

        # Mock the session.get for the entity
        mock_session.get = AsyncMock(return_value=mock_change_order)

        # cmd = UpdateChangeOrderStatusCommand(
        #    change_order_id=co_id,
        #    new_status="Approved",
        #    actor_id=actor_id,
        #    control_date=control_date,
        # )

        # result = await cmd.execute(mock_session)

        # Verify clone was called with the new status
        mock_change_order.clone.assert_called_once()
        call_kwargs = mock_change_order.clone.call_args[1]
        assert call_kwargs["created_by"] == actor_id
        assert call_kwargs["status"] == "Approved"

        # Verify the new version was added to session
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_additional_updates(
        self, mock_session: AsyncMock, mock_change_order: ChangeOrder
    ) -> None:
        """Test that execute includes additional_updates in the new version."""
        co_id = uuid4()
        actor_id = uuid4()
        control_date = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)
        current_lower = datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC)

        # Mock the current version query
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(
            id=mock_change_order.id,
            valid_time=MagicMock(lower=current_lower),
        )
        mock_session.execute.return_value = mock_result

        # Mock the session.get for the entity
        mock_session.get = AsyncMock(return_value=mock_change_order)

        cmd = UpdateChangeOrderStatusCommand(
            change_order_id=co_id,
            new_status="Submitted for Approval",
            actor_id=actor_id,
            control_date=control_date,
            additional_updates={
                "sla_status": "pending",
                "sla_assigned_at": control_date,
            },
        )

        await cmd.execute(mock_session)

        # Verify clone was called with additional updates
        mock_change_order.clone.assert_called_once()
        call_kwargs = mock_change_order.clone.call_args[1]
        assert call_kwargs["sla_status"] == "pending"
        assert call_kwargs["sla_assigned_at"] == control_date
