"""Unit tests for change order workflow validation.

Tests for ControlDateValidator and ControlDateSequenceViolationError.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order_audit_log import ChangeOrderAuditLog
from app.services.change_order_workflow_validation import (
    ControlDateSequenceViolationError,
    ControlDateValidator,
)


@pytest.mark.asyncio
class TestControlDateValidator:
    """Tests for ControlDateValidator class."""

    async def test_get_last_operation_control_date_returns_none_for_no_prior_operations(
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_last_operation_control_date returns None when no prior operations exist."""
        change_order_id = uuid4()

        result = await ControlDateValidator.get_last_operation_control_date(
            change_order_id, db_session
        )

        assert result is None

    async def test_get_last_operation_control_date_returns_most_recent(
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_last_operation_control_date returns the most recent control_date."""
        change_order_id = uuid4()
        actor_id = uuid4()

        # Create audit log entries with different control_dates
        now = datetime.now(UTC)
        earlier = now - timedelta(days=2)
        latest = now - timedelta(days=1)

        # Earlier entry
        audit1 = ChangeOrderAuditLog(
            change_order_id=change_order_id,
            old_status="Draft",
            new_status="Submitted for Approval",
            changed_by=actor_id,
            control_date=earlier,
        )
        db_session.add(audit1)
        await db_session.flush()

        # Later entry
        audit2 = ChangeOrderAuditLog(
            change_order_id=change_order_id,
            old_status="Submitted for Approval",
            new_status="Under Review",
            changed_by=actor_id,
            control_date=latest,
        )
        db_session.add(audit2)
        await db_session.flush()

        result = await ControlDateValidator.get_last_operation_control_date(
            change_order_id, db_session
        )

        # Should return the latest control_date
        assert result is not None
        # Compare timestamps without microseconds to avoid precision issues
        assert abs((result - latest).total_seconds()) < 1

    async def test_validate_control_date_sequence_passes_for_first_operation(
        self, db_session: AsyncSession
    ) -> None:
        """Test that validation passes when there are no prior operations."""
        change_order_id = uuid4()
        new_control_date = datetime.now(UTC)

        # Should not raise any exception
        await ControlDateValidator.validate_control_date_sequence(
            change_order_id=change_order_id,
            new_control_date=new_control_date,
            session=db_session,
        )

    async def test_validate_control_date_sequence_passes_for_later_date(
        self, db_session: AsyncSession
    ) -> None:
        """Test that validation passes when new_control_date >= last operation's control_date."""
        change_order_id = uuid4()
        actor_id = uuid4()

        # Create prior audit log entry
        now = datetime.now(UTC)
        earlier = now - timedelta(days=1)

        audit = ChangeOrderAuditLog(
            change_order_id=change_order_id,
            old_status="Draft",
            new_status="Submitted for Approval",
            changed_by=actor_id,
            control_date=earlier,
        )
        db_session.add(audit)
        await db_session.flush()

        # New control_date is later - should pass
        new_control_date = now

        # Should not raise any exception
        await ControlDateValidator.validate_control_date_sequence(
            change_order_id=change_order_id,
            new_control_date=new_control_date,
            session=db_session,
        )

    async def test_validate_control_date_sequence_passes_for_same_date(
        self, db_session: AsyncSession
    ) -> None:
        """Test that validation passes when new_control_date == last operation's control_date."""
        change_order_id = uuid4()
        actor_id = uuid4()

        # Create prior audit log entry
        control_date = datetime.now(UTC)

        audit = ChangeOrderAuditLog(
            change_order_id=change_order_id,
            old_status="Draft",
            new_status="Submitted for Approval",
            changed_by=actor_id,
            control_date=control_date,
        )
        db_session.add(audit)
        await db_session.flush()

        # New control_date is the same - should pass (>= check)
        await ControlDateValidator.validate_control_date_sequence(
            change_order_id=change_order_id,
            new_control_date=control_date,
            session=db_session,
        )

    async def test_validate_control_date_sequence_raises_for_earlier_date(
        self, db_session: AsyncSession
    ) -> None:
        """Test that validation raises error when new_control_date < last operation's control_date."""
        change_order_id = uuid4()
        actor_id = uuid4()

        # Create prior audit log entry with a later control_date
        now = datetime.now(UTC)
        later = now + timedelta(days=1)

        audit = ChangeOrderAuditLog(
            change_order_id=change_order_id,
            old_status="Draft",
            new_status="Submitted for Approval",
            changed_by=actor_id,
            control_date=later,
        )
        db_session.add(audit)
        await db_session.flush()

        # New control_date is earlier - should raise
        earlier = now

        with pytest.raises(ControlDateSequenceViolationError) as exc_info:
            await ControlDateValidator.validate_control_date_sequence(
                change_order_id=change_order_id,
                new_control_date=earlier,
                session=db_session,
            )

        # Verify error details
        error = exc_info.value
        assert error.change_order_id == change_order_id
        assert error.new_control_date == earlier
        assert error.last_control_date == later
        assert "Cannot perform workflow operation" in str(error)
        assert "chronological order" in str(error)

    async def test_validate_control_date_sequence_isolated_to_change_order(
        self, db_session: AsyncSession
    ) -> None:
        """Test that validation only checks audit logs for the specific change order."""
        change_order_id_1 = uuid4()
        change_order_id_2 = uuid4()
        actor_id = uuid4()

        # Create audit log for first change order
        now = datetime.now(UTC)
        later = now + timedelta(days=1)

        audit1 = ChangeOrderAuditLog(
            change_order_id=change_order_id_1,
            old_status="Draft",
            new_status="Submitted for Approval",
            changed_by=actor_id,
            control_date=later,
        )
        db_session.add(audit1)
        await db_session.flush()

        # Second change order should not be affected by first's audit log
        earlier = now

        # Should pass - no prior operations for change_order_id_2
        await ControlDateValidator.validate_control_date_sequence(
            change_order_id=change_order_id_2,
            new_control_date=earlier,
            session=db_session,
        )


class TestControlDateSequenceViolationError:
    """Tests for ControlDateSequenceViolationError exception."""

    def test_error_message_contains_dates(self) -> None:
        """Test that error message contains both dates in ISO format."""
        change_order_id = uuid4()
        new_control_date = datetime(2026, 2, 25, 10, 0, 0, tzinfo=UTC)
        last_control_date = datetime(2026, 2, 26, 10, 0, 0, tzinfo=UTC)

        error = ControlDateSequenceViolationError(
            change_order_id=change_order_id,
            new_control_date=new_control_date,
            last_control_date=last_control_date,
        )

        message = str(error)
        assert "2026-02-25T10:00:00" in message
        assert "2026-02-26T10:00:00" in message
        assert "chronological order" in message

    def test_error_attributes(self) -> None:
        """Test that error has correct attributes."""
        change_order_id = uuid4()
        new_control_date = datetime.now(UTC)
        last_control_date = datetime.now(UTC) + timedelta(days=1)

        error = ControlDateSequenceViolationError(
            change_order_id=change_order_id,
            new_control_date=new_control_date,
            last_control_date=last_control_date,
        )

        assert error.change_order_id == change_order_id
        assert error.new_control_date == new_control_date
        assert error.last_control_date == last_control_date
