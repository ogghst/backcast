"""SLA Service for change order approval deadline calculation.

This service calculates SLA deadlines for change order approvals based on
impact level. SLAs are measured in business days (Monday-Friday, excluding
holidays).

Context: Used by ChangeOrderWorkflowService to set SLA deadlines when
change orders are submitted for approval.

SLA deadlines are now read from the configurable workflow configuration
service (ChangeOrderConfigService), eliminating the previous hardcoded values.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import SLAStatus

if TYPE_CHECKING:
    from app.models.domain.change_order import ChangeOrder
    from app.services.change_order_config_service import ChangeOrderConfigService


class SLAService:
    """Service for calculating SLA deadlines for change order approvals.

    Calculates SLA deadlines based on impact level, using business days
    (Monday-Friday, excluding weekends). Business days per impact level
    are read from the workflow configuration.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        config_service: ChangeOrderConfigService | None = None,
    ) -> None:
        """Initialize the service with a database session.

        Args:
            db_session: Async database session for queries
            config_service: Optional config service for SLA lookup.
        """
        self._db = db_session
        self._config_service = config_service

    async def calculate_sla_deadline(
        self, impact_level: str, start_date: datetime
    ) -> datetime:
        """Calculate SLA deadline based on impact level and start date.

        Reads SLA days from the workflow configuration.

        Args:
            impact_level: Financial impact level (LOW/MEDIUM/HIGH/CRITICAL)
            start_date: When the SLA timer starts (e.g., submission date)

        Returns:
            SLA deadline as datetime (timezone-aware if start_date is)

        Raises:
            ValueError: If impact_level is invalid
        """
        sla_days_map = await self._get_sla_days()

        if impact_level not in sla_days_map:
            raise ValueError(
                f"Invalid impact_level: {impact_level}. "
                f"Must be one of: {list(sla_days_map.keys())}"
            )

        business_days = sla_days_map[impact_level]

        # Get holiday country code from config
        country_code = await self._get_holiday_country_code()

        deadline = self._add_business_days(start_date, business_days, country_code)

        return deadline

    def calculate_sla_status(
        self,
        due_date: datetime,
        current_date: datetime | None = None,
        sla_assigned_at: datetime | None = None,
        escalation_trigger_pct: Decimal | None = None,
    ) -> str:
        """Calculate SLA status based on due date and current date.

        Args:
            due_date: SLA deadline
            current_date: Current date (defaults to now if None)
            sla_assigned_at: When the SLA timer started (for escalation calc)
            escalation_trigger_pct: Percentage threshold for escalation

        Returns:
            SLA status: pending, approaching, escalated, or overdue
        """
        if current_date is None:
            current_date = datetime.now(UTC)

        if current_date.tzinfo is None:
            current_date = current_date.replace(tzinfo=UTC)
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=UTC)

        remaining_delta = due_date - current_date

        # Check if overdue (highest priority)
        if remaining_delta.total_seconds() < 0:
            return SLAStatus.OVERDUE

        # Check escalation trigger (if configured)
        if sla_assigned_at is not None and escalation_trigger_pct is not None:
            if sla_assigned_at.tzinfo is None:
                sla_assigned_at = sla_assigned_at.replace(tzinfo=UTC)
            total_duration = (due_date - sla_assigned_at).total_seconds()
            if total_duration > 0:
                elapsed = (current_date - sla_assigned_at).total_seconds()
                elapsed_pct = (elapsed / total_duration) * 100
                if elapsed_pct >= float(escalation_trigger_pct):
                    return SLAStatus.ESCALATED

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
        self,
        due_date: datetime,
        current_date: datetime | None = None,
        country_code: str | None = None,
    ) -> int:
        """Calculate the number of business days remaining until SLA deadline.

        Args:
            due_date: SLA deadline
            current_date: Current date (defaults to now if None)
            country_code: Optional ISO country code for holiday lookup

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
            if self._is_business_day(temp_date, country_code):
                business_days += 1
            temp_date = self._add_days(temp_date, 1)

        return business_days

    def _add_business_days(
        self,
        start_date: datetime,
        business_days: int,
        country_code: str | None = None,
    ) -> datetime:
        """Add business days to a date, skipping weekends and holidays.

        Args:
            start_date: Starting datetime
            business_days: Number of business days to add
            country_code: Optional ISO country code for holiday lookup

        Returns:
            Datetime after adding business days
        """
        current = start_date.date()
        days_added = 0

        while days_added < business_days:
            current = self._add_days(current, 1)
            if self._is_business_day(current, country_code):
                days_added += 1

        # Combine with the time from start_date
        return datetime.combine(current, start_date.time(), tzinfo=start_date.tzinfo)

    def _is_business_day(
        self, check_date: date, country_code: str | None = None
    ) -> bool:
        """Check if a date is a business day (Monday-Friday, excluding holidays).

        Args:
            check_date: Date to check
            country_code: Optional ISO country code for holiday lookup

        Returns:
            True if business day, False if weekend or holiday
        """
        if check_date.weekday() >= 5:
            return False

        if country_code is not None:
            import holidays as hol

            country_holidays = hol.country_holidays(country_code)
            if check_date in country_holidays:
                return False

        return True

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

        # Get escalation trigger for this CO's impact level
        escalation_trigger: Decimal | None = None
        if change_order.impact_level and change_order.sla_assigned_at:
            triggers = await self._get_escalation_triggers()
            escalation_trigger = triggers.get(change_order.impact_level)

        # Calculate new SLA status
        new_status = self.calculate_sla_status(
            change_order.sla_due_date,
            datetime.now(UTC),
            sla_assigned_at=change_order.sla_assigned_at,
            escalation_trigger_pct=escalation_trigger,
        )

        # Update if changed
        if change_order.sla_status != new_status:
            change_order.sla_status = new_status
            await self._db.flush()

        return new_status

    async def _get_sla_days(self) -> dict[str, int]:
        """Get SLA business days per impact level from config."""
        from app.services.change_order_config_service import (
            ChangeOrderConfigService,
        )

        if self._config_service is not None:
            return await self._config_service.get_sla_days()
        config_service = ChangeOrderConfigService(self._db)
        return await config_service.get_sla_days()

    async def _get_escalation_triggers(self) -> dict[str, Decimal]:
        """Get escalation trigger percentages per impact level from config."""
        from app.services.change_order_config_service import (
            ChangeOrderConfigService,
        )

        if self._config_service is not None:
            return await self._config_service.get_escalation_triggers()
        config_service = ChangeOrderConfigService(self._db)
        return await config_service.get_escalation_triggers()

    async def _get_holiday_country_code(self) -> str | None:
        """Get holiday country code from config."""
        from app.services.change_order_config_service import (
            ChangeOrderConfigService,
        )

        config_service = self._config_service or ChangeOrderConfigService(self._db)
        config = await config_service.get_global_config()
        if config is not None and config.holiday_country_code is not None:
            return config.holiday_country_code
        return None

    async def check_escalation_eligible(self, change_order: ChangeOrder) -> bool:
        """Check if a change order should be escalated based on SLA time elapsed."""
        if (
            change_order.sla_assigned_at is None
            or change_order.sla_due_date is None
            or change_order.impact_level is None
        ):
            return False

        if change_order.sla_status == SLAStatus.ESCALATED:
            return False

        triggers = await self._get_escalation_triggers()
        trigger_pct = triggers.get(change_order.impact_level)
        if trigger_pct is None:
            return False

        now = datetime.now(UTC)
        total_duration = (
            change_order.sla_due_date - change_order.sla_assigned_at
        ).total_seconds()
        if total_duration <= 0:
            return True

        elapsed = (now - change_order.sla_assigned_at).total_seconds()
        elapsed_pct = (elapsed / total_duration) * 100

        return elapsed_pct >= float(trigger_pct)

    async def get_escalatable_change_orders(self) -> list[ChangeOrder]:
        """Find all change orders eligible for SLA escalation."""
        from typing import Any
        from typing import cast as typing_cast

        from sqlalchemy import cast as sql_cast
        from sqlalchemy import func, select
        from sqlalchemy.dialects.postgresql import TIMESTAMP

        from app.models.domain.change_order import ChangeOrder

        as_of_tstz = sql_cast(func.clock_timestamp(), TIMESTAMP(timezone=True))
        stmt = (
            select(ChangeOrder)
            .where(
                ChangeOrder.branch == "main",
                ChangeOrder.status.in_(["submitted_for_approval", "under_review"]),
                ChangeOrder.sla_assigned_at.isnot(None),
                ChangeOrder.sla_due_date.isnot(None),
                typing_cast(Any, ChangeOrder).valid_time.op("@>")(as_of_tstz),
                func.lower(typing_cast(Any, ChangeOrder).valid_time) <= as_of_tstz,
                typing_cast(Any, ChangeOrder).deleted_at.is_(None),
            )
            .order_by(typing_cast(Any, ChangeOrder).valid_time.desc())
        )
        result = await self._db.execute(stmt)
        cos = result.scalars().all()

        escalatable = []
        for co in cos:
            if await self.check_escalation_eligible(co):
                escalatable.append(co)
        return escalatable

    async def escalate_change_order(
        self, change_order_id: str, actor_id: UUID
    ) -> ChangeOrder:
        """Escalate a change order's SLA status.

        Args:
            change_order_id: UUID string of the change order
            actor_id: UUID of the user/system triggering escalation

        Returns:
            Updated ChangeOrder with sla_status set to ESCALATED

        Raises:
            ValueError: If change order not found or not in escalatable status
        """
        from typing import Any
        from typing import cast as typing_cast

        from sqlalchemy import cast as sql_cast
        from sqlalchemy import func, select
        from sqlalchemy.dialects.postgresql import TIMESTAMP

        from app.models.domain.change_order import ChangeOrder
        from app.models.domain.change_order_audit_log import ChangeOrderAuditLog

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

        if change_order.status not in [
            "submitted_for_approval",
            "under_review",
        ]:
            raise ValueError(
                f"Cannot escalate change order in status '{change_order.status}'. "
                "Only submitted_for_approval or under_review can be escalated."
            )

        if change_order.sla_status == SLAStatus.ESCALATED:
            return change_order

        change_order.sla_status = SLAStatus.ESCALATED
        await self._db.flush()

        audit_entry = ChangeOrderAuditLog(
            change_order_id=change_order.change_order_id,
            old_status=change_order.status,
            new_status=change_order.status,
            comment="SLA escalation triggered: approval deadline approaching",
            changed_by=actor_id,
        )
        self._db.add(audit_entry)
        await self._db.flush()

        return change_order
