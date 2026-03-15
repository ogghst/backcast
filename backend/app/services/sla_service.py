"""SLA Service for change order approval deadline calculation.

This service calculates SLA deadlines for change order approvals based on
impact level. SLAs are measured in business days (Monday-Friday, excluding
holidays).

Context: Used by ChangeOrderWorkflowService to set SLA deadlines when
change orders are submitted for approval.

Service Layer:
- Calculates SLA deadlines based on impact level
- Tracks SLA status (pending/approaching/overdue)
- Provides business day calculations
"""

from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ImpactLevel, SLAStatus


class SLAService:
    """Service for calculating SLA deadlines for change order approvals.

    Calculates SLA deadlines based on impact level, using business days
    (Monday-Friday, excluding weekends). Holidays are not yet supported
    but can be added in a future iteration.

    SLA Deadlines by Impact Level:
    - LOW: 2 business days
    - MEDIUM: 5 business days
    - HIGH: 10 business days
    - CRITICAL: 15 business days
    """

    # Business day SLA mapping (impact level -> business days)
    SLA_BUSINESS_DAYS: dict[str, int] = {
        ImpactLevel.LOW: 2,
        ImpactLevel.MEDIUM: 5,
        ImpactLevel.HIGH: 10,
        ImpactLevel.CRITICAL: 15,
    }

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service with a database session.

        Args:
            db_session: Async database session for queries
        """
        self._db = db_session

    def calculate_sla_deadline(
        self, impact_level: str, start_date: datetime
    ) -> datetime:
        """Calculate SLA deadline based on impact level and start date.

        Adds the required number of business days to the start date.
        Business days are Monday-Friday (weekends excluded).

        Args:
            impact_level: Financial impact level (LOW/MEDIUM/HIGH/CRITICAL)
            start_date: When the SLA timer starts (e.g., submission date)

        Returns:
            SLA deadline as datetime (timezone-aware if start_date is)

        Raises:
            ValueError: If impact_level is invalid

        Example:
            >>> service = SLAService(session)
            >>> deadline = service.calculate_sla_deadline('MEDIUM', datetime.now())
            >>> print(deadline)
            datetime.datetime(2026, 2, 10, 14, 30, tzinfo=datetime.timezone.utc)
        """
        if impact_level not in self.SLA_BUSINESS_DAYS:
            raise ValueError(
                f"Invalid impact_level: {impact_level}. "
                f"Must be one of: {list(self.SLA_BUSINESS_DAYS.keys())}"
            )

        business_days = self.SLA_BUSINESS_DAYS[impact_level]

        # Add business days (skip weekends)
        deadline = self._add_business_days(start_date, business_days)

        return deadline

    def calculate_sla_status(
        self, due_date: datetime, current_date: datetime | None = None
    ) -> str:
        """Calculate SLA status based on due date and current date.

        Args:
            due_date: SLA deadline
            current_date: Current date (defaults to now if None)

        Returns:
            SLA status: pending, approaching, or overdue

        Example:
            >>> service = SLAService(session)
            >>> status = service.calculate_sla_status(deadline)
            >>> print(status)
            'approaching'
        """
        if current_date is None:
            current_date = datetime.now(UTC)

        # Ensure both datetimes are timezone-aware
        if current_date.tzinfo is None:
            current_date = current_date.replace(tzinfo=UTC)
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=UTC)

        # Calculate remaining time
        remaining_delta = due_date - current_date

        # Check if overdue
        if remaining_delta.total_seconds() < 0:
            return SLAStatus.OVERDUE

        # Calculate total SLA duration
        sla_duration = due_date - current_date
        if sla_duration.total_seconds() == 0:
            return SLAStatus.APPROACHING

        # Check if approaching (less than 50% of SLA time remaining)
        # We use the difference between due_date and current_date as the remaining time
        # We need to know when the SLA started to calculate percentage
        # For simplicity, we'll use a heuristic: < 1 business day remaining = approaching
        one_business_day_seconds = 24 * 60 * 60  # Conservative estimate
        if remaining_delta.total_seconds() < one_business_day_seconds:
            return SLAStatus.APPROACHING

        return SLAStatus.PENDING

    def calculate_business_days_remaining(
        self, due_date: datetime, current_date: datetime | None = None
    ) -> int:
        """Calculate the number of business days remaining until SLA deadline.

        Args:
            due_date: SLA deadline
            current_date: Current date (defaults to now if None)

        Returns:
            Number of business days remaining (can be negative if overdue)
        """
        if current_date is None:
            current_date = datetime.now(UTC)

        # Ensure both datetimes are timezone-aware
        if current_date.tzinfo is None:
            current_date = current_date.replace(tzinfo=UTC)
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=UTC)

        # Convert to dates for business day calculation
        current_date_only = current_date.date()
        due_date_only = due_date.date()

        # Count business days between dates
        business_days = 0
        temp_date = current_date_only

        while temp_date < due_date_only:
            if self._is_business_day(temp_date):
                business_days += 1
            temp_date = self._add_days(temp_date, 1)

        return business_days

    def _add_business_days(self, start_date: datetime, business_days: int) -> datetime:
        """Add business days to a date, skipping weekends.

        Args:
            start_date: Starting datetime
            business_days: Number of business days to add

        Returns:
            Datetime after adding business days
        """
        current = start_date.date()
        days_added = 0

        while days_added < business_days:
            current = self._add_days(current, 1)
            if self._is_business_day(current):
                days_added += 1

        # Combine with the time from start_date
        return datetime.combine(current, start_date.time(), tzinfo=start_date.tzinfo)

    def _is_business_day(self, check_date: date) -> bool:
        """Check if a date is a business day (Monday-Friday).

        Args:
            check_date: Date to check

        Returns:
            True if Monday-Friday, False if Saturday/Sunday

        Note:
            Holidays are not yet supported. Can be added by checking
            against a holiday calendar table in future iterations.
        """
        # Monday=0, Tuesday=1, ..., Friday=4, Saturday=5, Sunday=6
        return check_date.weekday() < 5

    def _add_days(self, input_date: date, days: int) -> date:
        """Add days to a date.

        Args:
            input_date: Starting date
            days: Number of days to add

        Returns:
            New date after adding days
        """
        from datetime import timedelta

        return input_date + timedelta(days=days)

    async def update_sla_status_for_change_order(self, change_order_id: str) -> str:
        """Update SLA status for a change order based on current time.

        This method is intended to be called by a background job that
        periodically updates SLA statuses for pending change orders.

        Args:
            change_order_id: UUID of the change order (as string)

        Returns:
            Updated SLA status

        Raises:
            ValueError: If change order not found
        """
        from typing import Any
        from typing import cast as typing_cast

        from sqlalchemy import cast as sql_cast
        from sqlalchemy import func, select
        from sqlalchemy.dialects.postgresql import TIMESTAMP

        from app.models.domain.change_order import ChangeOrder

        # Get change order
        as_of_tstz = sql_cast(func.clock_timestamp(), TIMESTAMP(timezone=True))
        co_stmt = (
            select(ChangeOrder)
            .where(
                ChangeOrder.change_order_id == change_order_id,
                ChangeOrder.branch == "main",
                typing_cast(Any, ChangeOrder).valid_time.op("@>")(as_of_tstz),
                func.lower(typing_cast(Any, ChangeOrder).valid_time) <= as_of_tstz,
                typing_cast(Any, ChangeOrder).deleted_at.is_(None),
            )
            .order_by(typing_cast(Any, ChangeOrder).valid_time.desc())
            .limit(1)
        )
        co_result = await self._db.execute(co_stmt)
        change_order = co_result.scalar_one_or_none()

        if change_order is None:
            raise ValueError(f"Change order {change_order_id} not found")

        if change_order.sla_due_date is None:
            return SLAStatus.PENDING

        # Calculate new SLA status
        new_status = self.calculate_sla_status(
            change_order.sla_due_date, datetime.now(UTC)
        )

        # Update if changed
        if change_order.sla_status != new_status:
            change_order.sla_status = new_status
            await self._db.flush()

        return new_status
