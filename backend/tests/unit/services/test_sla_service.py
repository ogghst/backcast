"""Unit tests for SLAService config integration.

Tests that SLAService reads SLA days from the configurable workflow
configuration service, not from hardcoded values. Verifies:
- calculate_sla_deadline reads business days from config
- _get_sla_days returns correct days per impact level from config
- Missing config raises ConfigurationError (not silent fallback)
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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
            {"level_name": "LOW", "level_order": 1, "threshold_amount": "10000",
             "score_threshold_min": "0", "score_threshold_max": "9.99", "is_active": True},
            {"level_name": "MEDIUM", "level_order": 2, "threshold_amount": "50000",
             "score_threshold_min": "10", "score_threshold_max": "29.99", "is_active": True},
            {"level_name": "HIGH", "level_order": 3, "threshold_amount": "100000",
             "score_threshold_min": "30", "score_threshold_max": "49.99", "is_active": True},
            {"level_name": "CRITICAL", "level_order": 4, "threshold_amount": "999999999",
             "score_threshold_min": "50", "score_threshold_max": "999", "is_active": True},
        ]
        approval_rules = [
            {"impact_level_name": "LOW", "required_authority_level": "LOW", "approver_role": "viewer"},
            {"impact_level_name": "MEDIUM", "required_authority_level": "MEDIUM", "approver_role": "editor_pm"},
            {"impact_level_name": "HIGH", "required_authority_level": "HIGH", "approver_role": "dept_head"},
            {"impact_level_name": "HIGH", "required_authority_level": "HIGH", "approver_role": "director"},
            {"impact_level_name": "CRITICAL", "required_authority_level": "CRITICAL", "approver_role": "admin"},
        ]
        impact_weights: dict[str, object] = {"budget": 0.4, "schedule": 0.3, "revenue": 0.2, "evm": 0.1}
        score_boundaries: dict[str, object] = {"LOW": 10, "MEDIUM": 30, "HIGH": 50, "CRITICAL": 999}

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
