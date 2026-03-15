"""Change Order workflow validation logic.

Provides validation utilities for change order workflow operations,
including control date sequence validation to ensure chronological
consistency of workflow operations.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order_audit_log import ChangeOrderAuditLog


class ControlDateSequenceViolationError(Exception):
    """Raised when a workflow operation violates control date sequence.

    This exception is raised when attempting to perform a workflow operation
    (submit, approve, reject, recover) at a control date that is chronologically
    earlier than the previous operation's control date.

    Attributes:
        change_order_id: UUID of the change order
        new_control_date: The control date of the attempted operation
        last_control_date: The control date of the previous operation
    """

    def __init__(
        self,
        change_order_id: UUID,
        new_control_date: datetime,
        last_control_date: datetime,
    ) -> None:
        """Initialize control date sequence violation error.

        Args:
            change_order_id: UUID of the change order
            new_control_date: The control date of the attempted operation
            last_control_date: The control date of the previous operation
        """
        self.change_order_id = change_order_id
        self.new_control_date = new_control_date
        self.last_control_date = last_control_date

        message = (
            f"Cannot perform workflow operation at control_date {new_control_date.isoformat()}: "
            f"previous operation was recorded at {last_control_date.isoformat()}. "
            f"Operations must be performed in chronological order."
        )

        super().__init__(message)


class ControlDateValidator:
    """Validator for control date sequence consistency.

    Ensures that workflow operations are performed in chronological order
    by validating that each new operation's control date is >= the last
    operation's control date.
    """

    @staticmethod
    async def get_last_operation_control_date(
        change_order_id: UUID, session: AsyncSession
    ) -> datetime | None:
        """Get the control_date of the most recent audit log entry.

        Args:
            change_order_id: UUID of the change order
            session: Database session

        Returns:
            The control_date of the most recent audit log entry,
            or None if no prior operations exist.
        """
        stmt = (
            select(ChangeOrderAuditLog.control_date)
            .where(ChangeOrderAuditLog.change_order_id == change_order_id)
            .order_by(ChangeOrderAuditLog.control_date.desc())
            .limit(1)
        )

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def validate_control_date_sequence(
        change_order_id: UUID,
        new_control_date: datetime,
        session: AsyncSession,
    ) -> None:
        """Validate that new_control_date >= last operation's control_date.

        Args:
            change_order_id: UUID of the change order
            new_control_date: Control date for the new operation
            session: Database session

        Raises:
            ControlDateSequenceViolationError: If new_control_date < last operation's control_date
        """
        last_control_date = await ControlDateValidator.get_last_operation_control_date(
            change_order_id, session
        )

        # No prior operations - validation passes
        if last_control_date is None:
            return

        # Normalize timezones for comparison
        # If one is aware and the other is naive, assume the naive one is in the same timezone
        new_cd = new_control_date
        last_cd = last_control_date

        if new_cd.tzinfo is not None and last_cd.tzinfo is None:
            last_cd = last_cd.replace(tzinfo=new_cd.tzinfo)
        elif new_cd.tzinfo is None and last_cd.tzinfo is not None:
            new_cd = new_cd.replace(tzinfo=last_cd.tzinfo)

        # Check sequence - new must be >= last
        if new_cd < last_cd:
            raise ControlDateSequenceViolationError(
                change_order_id=change_order_id,
                new_control_date=new_control_date,
                last_control_date=last_control_date,
            )
