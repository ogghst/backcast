"""Unit tests for SLAService config integration.

Tests that SLAService reads SLA days from the configurable workflow
configuration service, not from hardcoded values. Verifies:
- calculate_sla_deadline reads business days from config
- _get_sla_days returns correct days per impact level from config
- Missing config raises ConfigurationError (not silent fallback)
- Holiday awareness via _is_business_day with country codes
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import SLAStatus
from app.services.change_order_config_service import (
    ChangeOrderConfigService,
    ConfigurationError,
)
from app.services.sla_service import SLAService


class TestSLADeadlineFromConfig:
    """Test that calculate_sla_deadline reads business days from config."""

    @pytest.mark.asyncio
    async def test_deadline_uses_config_low_days(
        self, db_session: AsyncSession
    ) -> None:
        """LOW impact deadline uses config value (2 business days)."""
        config_service = ChangeOrderConfigService(db_session)
        sla_service = SLAService(db_session, config_service)

        # Monday 9am UTC
        start = datetime(2026, 5, 4, 9, 0, 0, tzinfo=UTC)
        deadline = await sla_service.calculate_sla_deadline("LOW", start)

        # 2 business days from Monday = Wednesday
        assert deadline.date().isoformat() == "2026-05-06"

    @pytest.mark.asyncio
    async def test_deadline_uses_config_medium_days(
        self, db_session: AsyncSession
    ) -> None:
        """MEDIUM impact deadline uses config value (5 business days)."""
        config_service = ChangeOrderConfigService(db_session)
        sla_service = SLAService(db_session, config_service)

        # Monday 9am UTC
        start = datetime(2026, 5, 4, 9, 0, 0, tzinfo=UTC)
        deadline = await sla_service.calculate_sla_deadline("MEDIUM", start)

        # 5 business days from Monday = Monday next week
        assert deadline.date().isoformat() == "2026-05-11"

    @pytest.mark.asyncio
    async def test_deadline_uses_config_high_days(
        self, db_session: AsyncSession
    ) -> None:
        """HIGH impact deadline uses config value (10 business days)."""
        config_service = ChangeOrderConfigService(db_session)
        sla_service = SLAService(db_session, config_service)

        # Monday 9am UTC
        start = datetime(2026, 5, 4, 9, 0, 0, tzinfo=UTC)
        deadline = await sla_service.calculate_sla_deadline("HIGH", start)

        # 10 business days from Monday = Monday two weeks later
        assert deadline.date().isoformat() == "2026-05-18"

    @pytest.mark.asyncio
    async def test_deadline_uses_config_critical_days(
        self, db_session: AsyncSession
    ) -> None:
        """CRITICAL impact deadline uses config value (15 business days)."""
        config_service = ChangeOrderConfigService(db_session)
        sla_service = SLAService(db_session, config_service)

        # Monday 9am UTC
        start = datetime(2026, 5, 4, 9, 0, 0, tzinfo=UTC)
        deadline = await sla_service.calculate_sla_deadline("CRITICAL", start)

        # 15 business days from Monday May 4 = Monday May 25
        # (3 full weeks)
        assert deadline.date().isoformat() == "2026-05-25"

    @pytest.mark.asyncio
    async def test_invalid_impact_level_raises_error(
        self, db_session: AsyncSession
    ) -> None:
        """Invalid impact level raises ValueError, not silent fallback."""
        config_service = ChangeOrderConfigService(db_session)
        sla_service = SLAService(db_session, config_service)

        start = datetime(2026, 5, 4, 9, 0, 0, tzinfo=UTC)

        with pytest.raises(ValueError, match="Invalid impact_level"):
            await sla_service.calculate_sla_deadline("NONEXISTENT", start)


class TestGetSLADaysFromConfig:
    """Test that _get_sla_days returns correct days per impact level."""

    @pytest.mark.asyncio
    async def test_get_sla_days_returns_all_levels(
        self, db_session: AsyncSession
    ) -> None:
        """_get_sla_days returns dict with all 4 impact levels."""
        config_service = ChangeOrderConfigService(db_session)
        sla_service = SLAService(db_session, config_service)

        sla_days = await sla_service._get_sla_days()

        assert "LOW" in sla_days
        assert "MEDIUM" in sla_days
        assert "HIGH" in sla_days
        assert "CRITICAL" in sla_days

    @pytest.mark.asyncio
    async def test_get_sla_days_values_match_config(
        self, db_session: AsyncSession
    ) -> None:
        """_get_sla_days returns values that match the seeded config."""
        config_service = ChangeOrderConfigService(db_session)
        sla_service = SLAService(db_session, config_service)

        sla_days = await sla_service._get_sla_days()

        assert sla_days["LOW"] == 2
        assert sla_days["MEDIUM"] == 5
        assert sla_days["HIGH"] == 10
        assert sla_days["CRITICAL"] == 15

    @pytest.mark.asyncio
    async def test_get_sla_days_delegates_to_config_service(
        self, db_session: AsyncSession
    ) -> None:
        """When config_service is provided, _get_sla_days uses it."""
        config_service = ChangeOrderConfigService(db_session)

        # Get days directly from config service
        config_days = await config_service.get_sla_days()

        # Get days from SLA service
        sla_service = SLAService(db_session, config_service)
        sla_days = await sla_service._get_sla_days()

        # Should be identical
        assert sla_days == config_days


class TestSLADaysReflectConfigUpdate:
    """Test that SLA days change when config is updated."""

    @pytest.mark.asyncio
    async def test_updated_config_reflected_in_sla_days(
        self, db_session: AsyncSession
    ) -> None:
        """After updating config SLA days, _get_sla_days returns new values."""
        config_service = ChangeOrderConfigService(db_session)
        sla_service = SLAService(db_session, config_service)
        actor_id = uuid4()

        # Verify original values
        original_days = await sla_service._get_sla_days()
        assert original_days["LOW"] == 2

        # Update config
        config = await config_service.get_global_config()
        assert config is not None

        new_sla_rules = [
            {"impact_level_name": "LOW", "business_days": 20},
            {"impact_level_name": "MEDIUM", "business_days": 5},
            {"impact_level_name": "HIGH", "business_days": 10},
            {"impact_level_name": "CRITICAL", "business_days": 15},
        ]

        # Inline default config data to avoid cross-module test imports
        impact_levels = [
            {
                "level_name": "LOW",
                "level_order": 1,
                "threshold_amount": "10000",
                "score_threshold_min": "0",
                "score_threshold_max": "9.99",
                "is_active": True,
            },
            {
                "level_name": "MEDIUM",
                "level_order": 2,
                "threshold_amount": "50000",
                "score_threshold_min": "10",
                "score_threshold_max": "29.99",
                "is_active": True,
            },
            {
                "level_name": "HIGH",
                "level_order": 3,
                "threshold_amount": "100000",
                "score_threshold_min": "30",
                "score_threshold_max": "49.99",
                "is_active": True,
            },
            {
                "level_name": "CRITICAL",
                "level_order": 4,
                "threshold_amount": "999999999",
                "score_threshold_min": "50",
                "score_threshold_max": "999",
                "is_active": True,
            },
        ]
        approval_rules = [
            {
                "impact_level_name": "LOW",
                "required_authority_level": "LOW",
                "approver_role": "viewer",
            },
            {
                "impact_level_name": "MEDIUM",
                "required_authority_level": "MEDIUM",
                "approver_role": "editor_pm",
            },
            {
                "impact_level_name": "HIGH",
                "required_authority_level": "HIGH",
                "approver_role": "dept_head",
            },
            {
                "impact_level_name": "HIGH",
                "required_authority_level": "HIGH",
                "approver_role": "director",
            },
            {
                "impact_level_name": "CRITICAL",
                "required_authority_level": "CRITICAL",
                "approver_role": "admin",
            },
        ]
        impact_weights: dict[str, object] = {
            "budget": 0.4,
            "schedule": 0.3,
            "revenue": 0.2,
            "evm": 0.1,
        }
        score_boundaries: dict[str, object] = {
            "LOW": 10,
            "MEDIUM": 30,
            "HIGH": 50,
            "CRITICAL": 999,
        }

        await config_service.update_config(
            config_id=config.config_id,
            actor_id=actor_id,
            version=config.version,
            impact_levels=impact_levels,
            approval_rules=approval_rules,
            sla_rules=new_sla_rules,
            impact_weights=impact_weights,
            score_boundaries=score_boundaries,
        )

        # SLA service should see the new value
        updated_days = await sla_service._get_sla_days()
        assert updated_days["LOW"] == 20


class TestMissingConfigBehavior:
    """Test SLA behavior when config is missing."""

    @pytest.mark.asyncio
    async def test_missing_config_raises_configuration_error(
        self, db_session: AsyncSession
    ) -> None:
        """When no config exists, _get_sla_days raises ConfigurationError."""
        # Delete the seeded global config
        config_service = ChangeOrderConfigService(db_session)
        config = await config_service.get_global_config()
        assert config is not None
        await db_session.delete(config)
        await db_session.flush()

        # Create SLA service with the config service
        sla_service = SLAService(db_session, config_service)

        # _get_sla_days should raise ConfigurationError
        with pytest.raises(ConfigurationError, match="No global"):
            await sla_service._get_sla_days()


# ============================================================================
# Phase B: SLA Escalation Tests
# ============================================================================


class TestCheckEscalationEligible:
    """Test check_escalation_eligible method."""

    @pytest.mark.asyncio
    async def test_elapsed_past_trigger_returns_true(self) -> None:
        """CO at 90% elapsed with 80% trigger returns True."""
        sla_service = SLAService(MagicMock())
        sla_service._get_escalation_triggers = AsyncMock(
            return_value={"LOW": Decimal("80")}
        )

        now = datetime.now(UTC)
        co = MagicMock()
        co.sla_assigned_at = now - timedelta(hours=9)
        co.sla_due_date = now + timedelta(hours=1)
        co.impact_level = "LOW"
        co.sla_status = SLAStatus.PENDING

        assert await sla_service.check_escalation_eligible(co) is True

    @pytest.mark.asyncio
    async def test_elapsed_below_trigger_returns_false(self) -> None:
        """CO at 50% elapsed with 80% trigger returns False."""
        sla_service = SLAService(MagicMock())
        sla_service._get_escalation_triggers = AsyncMock(
            return_value={"LOW": Decimal("80")}
        )

        now = datetime.now(UTC)
        co = MagicMock()
        co.sla_assigned_at = now - timedelta(hours=5)
        co.sla_due_date = now + timedelta(hours=5)
        co.impact_level = "LOW"
        co.sla_status = SLAStatus.PENDING

        assert await sla_service.check_escalation_eligible(co) is False

    @pytest.mark.asyncio
    async def test_already_escalated_returns_false(self) -> None:
        """CO already in ESCALATED status returns False."""
        sla_service = SLAService(MagicMock())
        sla_service._get_escalation_triggers = AsyncMock(
            return_value={"LOW": Decimal("80")}
        )

        now = datetime.now(UTC)
        co = MagicMock()
        co.sla_assigned_at = now - timedelta(hours=9)
        co.sla_due_date = now + timedelta(hours=1)
        co.impact_level = "LOW"
        co.sla_status = SLAStatus.ESCALATED

        assert await sla_service.check_escalation_eligible(co) is False

    @pytest.mark.asyncio
    async def test_none_sla_assigned_at_returns_false(self) -> None:
        """CO with None sla_assigned_at returns False."""
        sla_service = SLAService(MagicMock())
        co = MagicMock()
        co.sla_assigned_at = None
        co.sla_due_date = datetime.now(UTC)
        co.impact_level = "LOW"
        co.sla_status = SLAStatus.PENDING

        assert await sla_service.check_escalation_eligible(co) is False

    @pytest.mark.asyncio
    async def test_no_trigger_for_impact_level_returns_false(self) -> None:
        """CO with no escalation trigger for its impact level returns False."""
        sla_service = SLAService(MagicMock())
        sla_service._get_escalation_triggers = AsyncMock(return_value={})

        now = datetime.now(UTC)
        co = MagicMock()
        co.sla_assigned_at = now - timedelta(hours=9)
        co.sla_due_date = now + timedelta(hours=1)
        co.impact_level = "LOW"
        co.sla_status = SLAStatus.PENDING

        assert await sla_service.check_escalation_eligible(co) is False


class TestCalculateSLAStatusWithEscalation:
    """Test calculate_sla_status with escalation parameters."""

    def test_returns_escalated_when_past_trigger(self) -> None:
        """Returns ESCALATED when elapsed >= trigger percentage."""
        sla_service = SLAService(MagicMock())
        now = datetime.now(UTC)
        assigned = now - timedelta(hours=9)
        due = now + timedelta(hours=1)

        result = sla_service.calculate_sla_status(
            due_date=due,
            current_date=now,
            sla_assigned_at=assigned,
            escalation_trigger_pct=Decimal("80"),
        )
        assert result == SLAStatus.ESCALATED

    def test_returns_pending_when_below_trigger(self) -> None:
        """Returns PENDING when elapsed < trigger and time remaining > 24h."""
        sla_service = SLAService(MagicMock())
        now = datetime.now(UTC)
        assigned = now - timedelta(hours=1)
        due = now + timedelta(days=5)

        result = sla_service.calculate_sla_status(
            due_date=due,
            current_date=now,
            sla_assigned_at=assigned,
            escalation_trigger_pct=Decimal("80"),
        )
        assert result == SLAStatus.PENDING

    def test_backward_compat_without_escalation_params(self) -> None:
        """Without escalation params, returns PENDING/APPROACHING/OVERDUE."""
        sla_service = SLAService(MagicMock())
        now = datetime.now(UTC)

        result = sla_service.calculate_sla_status(
            due_date=now + timedelta(days=5),
            current_date=now,
        )
        assert result == SLAStatus.PENDING

    def test_overdue_when_escalation_window_negative(self) -> None:
        """When total_duration <= 0, escalation skipped, returns OVERDUE."""
        sla_service = SLAService(MagicMock())
        now = datetime.now(UTC)
        # due before assigned → total_duration < 0, escalation check skipped
        assigned = now - timedelta(hours=1)
        due = now - timedelta(hours=5)

        result = sla_service.calculate_sla_status(
            due_date=due,
            current_date=now,
            sla_assigned_at=assigned,
            escalation_trigger_pct=Decimal("80"),
        )
        assert result == SLAStatus.OVERDUE

    def test_overdue_takes_precedence_over_escalation(self) -> None:
        """When overdue AND past escalation trigger, returns OVERDUE (highest priority)."""
        sla_service = SLAService(MagicMock())
        now = datetime.now(UTC)
        assigned = now - timedelta(hours=10)
        due = now - timedelta(hours=1)

        result = sla_service.calculate_sla_status(
            due_date=due,
            current_date=now,
            sla_assigned_at=assigned,
            escalation_trigger_pct=Decimal("80"),
        )
        assert result == SLAStatus.OVERDUE


class TestEscalateChangeOrder:
    """Test escalate_change_order method."""

    @pytest.mark.asyncio
    async def test_escalate_submitted_co(self) -> None:
        """Escalates a CO in Submitted for Approval status."""
        sla_service = SLAService(MagicMock())

        co = MagicMock()
        co.status = "Submitted for Approval"
        co.sla_status = SLAStatus.PENDING
        co.change_order_id = str(uuid4())

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = co
        sla_service._db.execute = AsyncMock(return_value=mock_result)
        sla_service._db.flush = AsyncMock()
        sla_service._db.add = MagicMock()

        actor_id = uuid4()
        result = await sla_service.escalate_change_order(str(uuid4()), actor_id)

        assert co.sla_status == SLAStatus.ESCALATED
        assert result == co
        sla_service._db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_escalate_raises_for_draft_status(self) -> None:
        """Raises ValueError for CO in Draft status."""
        sla_service = SLAService(MagicMock())

        co = MagicMock()
        co.status = "Draft"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = co
        sla_service._db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Cannot escalate"):
            await sla_service.escalate_change_order(str(uuid4()), uuid4())

    @pytest.mark.asyncio
    async def test_escalate_raises_for_not_found(self) -> None:
        """Raises ValueError when CO not found."""
        sla_service = SLAService(MagicMock())

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        sla_service._db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await sla_service.escalate_change_order(str(uuid4()), uuid4())


# ============================================================================
# Phase C: Holiday Awareness Tests
# ============================================================================


class TestHolidayAwareness:
    """Test _is_business_day and _add_business_days with holiday awareness."""

    def test_is_business_day_excludes_known_italian_holiday(self) -> None:
        """Jan 1 (Capodanno) is a holiday in Italy and is excluded."""
        sla_service = SLAService(MagicMock())

        # Jan 1, 2026 is a Thursday (weekday) but a holiday in Italy
        assert not sla_service._is_business_day(date(2026, 1, 1), "IT")

    def test_is_business_day_includes_non_holiday_weekday(self) -> None:
        """A regular weekday that is not a holiday returns True."""
        sla_service = SLAService(MagicMock())

        # Jan 2, 2026 is a Friday, not a holiday in Italy
        assert sla_service._is_business_day(date(2026, 1, 2), "IT")

    def test_is_business_day_no_country_code_falls_back_to_weekday(self) -> None:
        """Without country_code, only weekday check applies."""
        sla_service = SLAService(MagicMock())

        # Monday Jan 5, 2026 is a weekday
        assert sla_service._is_business_day(date(2026, 1, 5))
        # Saturday Jan 3, 2026 is a weekend
        assert not sla_service._is_business_day(date(2026, 1, 3))

    def test_is_business_day_weekend_still_excluded_with_country(self) -> None:
        """A Saturday with country_code='IT' still returns False."""
        sla_service = SLAService(MagicMock())

        # Jan 3, 2026 is a Saturday -- excluded regardless of country
        assert not sla_service._is_business_day(date(2026, 1, 3), "IT")

    def test_add_business_days_skips_holidays(self) -> None:
        """Adding 3 business days from Mon Dec 22 skips Dec 25 + Dec 26."""
        sla_service = SLAService(MagicMock())

        # Dec 25 (Natale) and Dec 26 (Santo Stefano) are Italian holidays
        assert not sla_service._is_business_day(date(2025, 12, 25), "IT")
        assert not sla_service._is_business_day(date(2025, 12, 26), "IT")

        # Add 3 business days from Monday Dec 22:
        # Day 1: Tue Dec 23 (biz), Day 2: Wed Dec 24 (biz),
        # skip Thu Dec 25 (holiday), skip Fri Dec 26 (holiday),
        # skip Sat Dec 27, skip Sun Dec 28,
        # Day 3: Mon Dec 29 (biz)
        result = sla_service._add_business_days(
            datetime(2025, 12, 22, 9, 0, tzinfo=UTC), 3, "IT"
        )
        assert result.date() == date(2025, 12, 29)


class TestCalculateBusinessDaysRemainingHolidayAwareness:
    """Test calculate_business_days_remaining with holiday awareness."""

    def test_calculate_business_days_remaining_skips_holidays(self) -> None:
        """Count business days from Dec 22 to Dec 29, 2025 with IT holidays.

        Dec 22 (Mon) to Dec 29 (Mon), current < due (so Dec 22 is counted):
        - Dec 22 (Mon): business day -> 1
        - Dec 23 (Tue): business day -> 2
        - Dec 24 (Wed): business day -> 3
        - Dec 25 (Thu): Italian holiday (Natale) -> skipped
        - Dec 26 (Fri): Italian holiday (Santo Stefano) -> skipped
        - Dec 27 (Sat): weekend -> skipped
        - Dec 28 (Sun): weekend -> skipped

        Total: 3 business days remaining.
        """
        sla_service = SLAService(MagicMock())

        current = datetime(2025, 12, 22, 9, 0, tzinfo=UTC)
        due = datetime(2025, 12, 29, 9, 0, tzinfo=UTC)

        result = sla_service.calculate_business_days_remaining(
            due, current, country_code="IT"
        )
        assert result == 3

    def test_calculate_business_days_remaining_without_country_code(self) -> None:
        """Without country_code, holidays are not skipped (only weekends)."""
        sla_service = SLAService(MagicMock())

        current = datetime(2025, 12, 22, 9, 0, tzinfo=UTC)
        due = datetime(2025, 12, 29, 9, 0, tzinfo=UTC)

        result = sla_service.calculate_business_days_remaining(due, current)

        # Without country_code: Dec 22 (Mon) through Dec 28 (Sun)
        # Dec 22 (Mon): biz 1, Dec 23 (Tue): biz 2, Dec 24 (Wed): biz 3,
        # Dec 25 (Thu): biz 4, Dec 26 (Fri): biz 5,
        # Dec 27 (Sat): weekend, Dec 28 (Sun): weekend
        assert result == 5
