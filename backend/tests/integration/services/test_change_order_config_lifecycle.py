"""Integration tests for Change Order Config lifecycle.

Verifies end-to-end config behavior including:
- Global config read and update lifecycle
- Per-project override lifecycle (create, use, delete, fallback)
- Config update reflected in SLA calculation
- Config snapshot generation
- Config helper methods with project overrides

These tests use real DB sessions with transaction rollback. The seeded
global config from the migration is always present. Tests that modify
the global config use the transaction rollback for cleanup.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.change_order_config_service import ChangeOrderConfigService
from app.services.sla_service import SLAService


def _make_impact_levels() -> list[dict[str, Any]]:
    """Create default impact level config data."""
    return [
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


def _make_approval_rules() -> list[dict[str, Any]]:
    """Create default approval rule config data."""
    return [
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


def _make_sla_rules() -> list[dict[str, Any]]:
    """Create default SLA rule config data."""
    return [
        {"impact_level_name": "LOW", "business_days": 2},
        {"impact_level_name": "MEDIUM", "business_days": 5},
        {"impact_level_name": "HIGH", "business_days": 10},
        {"impact_level_name": "CRITICAL", "business_days": 15},
    ]


def _make_impact_weights() -> dict[str, Any]:
    """Create default impact weights."""
    return {"budget": 0.4, "schedule": 0.3, "revenue": 0.2, "evm": 0.1}


def _make_score_boundaries() -> dict[str, Any]:
    """Create default score boundaries."""
    return {"LOW": 10, "MEDIUM": 30, "HIGH": 50, "CRITICAL": 999}


class TestGlobalConfigLifecycle:
    """Integration tests for global config read and update cycle."""

    @pytest.mark.asyncio
    async def test_seeded_global_config_is_present(
        self, db_session: AsyncSession
    ) -> None:
        """The migration-seeded global config should be present."""
        service = ChangeOrderConfigService(db_session)

        config = await service.get_global_config()
        assert config is not None
        assert config.project_id is None
        assert config.is_active is True
        assert config.version == 1

    @pytest.mark.asyncio
    async def test_update_global_config_persists_new_values(
        self, db_session: AsyncSession
    ) -> None:
        """Update global config with different SLA days, verify persistence."""
        service = ChangeOrderConfigService(db_session)
        actor_id = uuid4()

        config = await service.get_global_config()
        assert config is not None

        # Capture version before update
        version_before = config.version

        # Update with modified SLA
        new_sla = _make_sla_rules()
        new_sla[0]["business_days"] = 7  # LOW: 2 -> 7
        new_sla[3]["business_days"] = 30  # CRITICAL: 15 -> 30

        updated = await service.update_config(
            config_id=config.config_id,
            actor_id=actor_id,
            version=version_before,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=new_sla,
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        assert updated.version == version_before + 1

        # Re-fetch from DB to confirm persistence
        re_fetched = await service.get_global_config()
        assert re_fetched is not None
        sla_map = {r.impact_level_name: r.business_days for r in re_fetched.sla_rules}
        assert sla_map["LOW"] == 7
        assert sla_map["CRITICAL"] == 30
        # Unchanged levels
        assert sla_map["MEDIUM"] == 5
        assert sla_map["HIGH"] == 10


class TestProjectOverrideLifecycle:
    """Integration tests for per-project override create, use, delete, fallback."""

    @pytest.mark.asyncio
    async def test_project_override_takes_precedence(
        self, db_session: AsyncSession
    ) -> None:
        """Project with override uses project config, not global."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        # Create override with different SLA
        modified_sla = _make_sla_rules()
        modified_sla[1]["business_days"] = 99  # MEDIUM: 5 -> 99

        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=modified_sla,
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        # get_active_config should return project override
        active = await service.get_active_config(project_id)
        assert active.project_id == project_id
        sla_map = {r.impact_level_name: r.business_days for r in active.sla_rules}
        assert sla_map["MEDIUM"] == 99

    @pytest.mark.asyncio
    async def test_delete_override_falls_back_to_global(
        self, db_session: AsyncSession
    ) -> None:
        """Delete project override, verify fallback to global config."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        # Create override
        modified_sla = _make_sla_rules()
        modified_sla[0]["business_days"] = 50

        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=modified_sla,
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        # Verify override is active
        active_before = await service.get_active_config(project_id)
        assert active_before.project_id == project_id

        # Delete override
        await service.delete_project_override(project_id, actor_id=uuid4())

        # Verify fallback to global
        active_after = await service.get_active_config(project_id)
        assert active_after.project_id is None  # Global config
        sla_map = {r.impact_level_name: r.business_days for r in active_after.sla_rules}
        assert sla_map["LOW"] == 2  # Original global value

    @pytest.mark.asyncio
    async def test_project_without_override_uses_global(
        self, db_session: AsyncSession
    ) -> None:
        """Project without override returns global config."""
        service = ChangeOrderConfigService(db_session)

        active = await service.get_active_config(uuid4())
        assert active.project_id is None

    @pytest.mark.asyncio
    async def test_get_sla_days_uses_project_override(
        self, db_session: AsyncSession
    ) -> None:
        """get_sla_days returns project-specific values when override exists."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        modified_sla = _make_sla_rules()
        modified_sla[2]["business_days"] = 42  # HIGH: 10 -> 42

        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=modified_sla,
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        sla_days = await service.get_sla_days(project_id)
        assert sla_days["HIGH"] == 42


class TestConfigUpdateReflectedInWorkflow:
    """Integration tests verifying config changes propagate to workflow services."""

    @pytest.mark.asyncio
    async def test_sla_service_uses_updated_config(
        self, db_session: AsyncSession
    ) -> None:
        """Update SLA days in config, verify SLAService picks up new values."""
        config_service = ChangeOrderConfigService(db_session)
        sla_service = SLAService(db_session, config_service)
        actor_id = uuid4()

        # Get original SLA days
        original_days = await config_service.get_sla_days()
        assert original_days["LOW"] == 2

        # Update config with new SLA days for LOW
        config = await config_service.get_global_config()
        assert config is not None

        # Capture version before update
        version_before = config.version

        new_sla = _make_sla_rules()
        new_sla[0]["business_days"] = 10  # LOW: 2 -> 10

        await config_service.update_config(
            config_id=config.config_id,
            actor_id=actor_id,
            version=version_before,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=new_sla,
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        # SLAService should now use the updated value
        start = datetime(2026, 5, 4, 9, 0, 0, tzinfo=UTC)  # Monday
        deadline = await sla_service.calculate_sla_deadline("LOW", start)

        # 10 business days from Monday May 4 = Monday May 18
        # (May 4 + 10 business days = May 18, no weekends crossed in 2 weeks)
        assert deadline.date().isoformat() == "2026-05-18"

    @pytest.mark.asyncio
    async def test_sla_service_uses_global_config_not_project_override(
        self, db_session: AsyncSession
    ) -> None:
        """SLAService uses global config even when a project override exists.

        SLAService does not accept project_id, so it always reads global.
        This test verifies that a project override does NOT affect SLAService.
        """
        project_id = uuid4()
        actor_id = uuid4()
        config_service = ChangeOrderConfigService(db_session)

        # Create project override with different SLA
        modified_sla = _make_sla_rules()
        modified_sla[1]["business_days"] = 1  # MEDIUM: 5 -> 1

        await config_service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=modified_sla,
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        # SLAService uses global config (not project-scoped)
        sla_service = SLAService(db_session, config_service)

        start = datetime(2026, 5, 4, 9, 0, 0, tzinfo=UTC)  # Monday
        deadline = await sla_service.calculate_sla_deadline("MEDIUM", start)

        # Should use global MEDIUM=5 business days, NOT project override of 1
        # 5 business days from Monday May 4 = Monday May 11
        assert deadline.date().isoformat() == "2026-05-11"


class TestConfigSnapshot:
    """Integration tests for config snapshot generation."""

    @pytest.mark.asyncio
    async def test_snapshot_captures_all_sections(
        self, db_session: AsyncSession
    ) -> None:
        """Generate snapshot and verify all config sections are present."""
        service = ChangeOrderConfigService(db_session)

        snapshot = await service.generate_snapshot()

        # Verify all required sections exist
        assert "config_id" in snapshot
        assert "impact_levels" in snapshot
        assert "approval_rules" in snapshot
        assert "sla_rules" in snapshot
        assert "impact_weights" in snapshot
        assert "score_boundaries" in snapshot

        # Verify content completeness
        assert len(snapshot["impact_levels"]) == 4
        assert len(snapshot["sla_rules"]) == 4
        assert len(snapshot["approval_rules"]) == 5

        # Verify impact level structure
        low_level = next(
            il for il in snapshot["impact_levels"] if il["level_name"] == "LOW"
        )
        assert "threshold_amount" in low_level
        assert "score_threshold_min" in low_level
        assert "score_threshold_max" in low_level
        assert "level_order" in low_level

        # Verify SLA rule structure
        low_sla = next(
            s for s in snapshot["sla_rules"] if s["impact_level_name"] == "LOW"
        )
        assert low_sla["business_days"] == 2

        # Verify weights
        assert snapshot["impact_weights"]["budget"] == 0.4
        assert snapshot["impact_weights"]["schedule"] == 0.3

        # Verify score boundaries
        assert snapshot["score_boundaries"]["LOW"] == 10

    @pytest.mark.asyncio
    async def test_snapshot_with_project_override(
        self, db_session: AsyncSession
    ) -> None:
        """Snapshot for project with override captures override values."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        # Create override
        modified_sla = _make_sla_rules()
        modified_sla[0]["business_days"] = 20

        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=modified_sla,
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        snapshot = await service.generate_snapshot(project_id)

        # Verify snapshot uses project override values
        low_sla = next(
            s for s in snapshot["sla_rules"] if s["impact_level_name"] == "LOW"
        )
        assert low_sla["business_days"] == 20


class TestHelperMethodsWithOverride:
    """Integration tests for config helper methods with project overrides."""

    @pytest.mark.asyncio
    async def test_get_thresholds_with_project_override(
        self, db_session: AsyncSession
    ) -> None:
        """get_thresholds returns project-specific thresholds when override exists."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        modified_levels = _make_impact_levels()
        modified_levels[0]["threshold_amount"] = "25000"  # LOW: 10000 -> 25000

        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=modified_levels,
            approval_rules=_make_approval_rules(),
            sla_rules=_make_sla_rules(),
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        thresholds = await service.get_thresholds(project_id)
        assert thresholds["LOW"] == Decimal("25000")

    @pytest.mark.asyncio
    async def test_get_score_boundaries_with_project_override(
        self, db_session: AsyncSession
    ) -> None:
        """get_score_boundaries returns project-specific values."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        modified_boundaries = _make_score_boundaries()
        modified_boundaries["MEDIUM"] = 50  # 30 -> 50

        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=_make_sla_rules(),
            impact_weights=_make_impact_weights(),
            score_boundaries=modified_boundaries,
        )

        boundaries = await service.get_score_boundaries(project_id)
        assert boundaries["MEDIUM"] == Decimal("50")

    @pytest.mark.asyncio
    async def test_classify_impact_with_config_boundaries(
        self, db_session: AsyncSession
    ) -> None:
        """classify_impact_by_score uses boundaries from config."""
        service = ChangeOrderConfigService(db_session)

        boundaries = await service.get_score_boundaries()

        # Score below LOW boundary (10)
        assert service.classify_impact_by_score(Decimal("5"), boundaries) == "LOW"
        # Score between LOW (10) and MEDIUM (30)
        assert service.classify_impact_by_score(Decimal("15"), boundaries) == "MEDIUM"
        # Score between MEDIUM (30) and HIGH (50)
        assert service.classify_impact_by_score(Decimal("40"), boundaries) == "HIGH"
        # Score above HIGH (50)
        assert service.classify_impact_by_score(Decimal("60"), boundaries) == "CRITICAL"

    @pytest.mark.asyncio
    async def test_get_approval_matrix_with_project_override(
        self, db_session: AsyncSession
    ) -> None:
        """get_approval_matrix returns project-specific matrix when override exists."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        modified_rules = _make_approval_rules()
        # Change LOW approver from viewer to editor_pm
        modified_rules[0]["approver_role"] = "editor_pm"

        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=modified_rules,
            sla_rules=_make_sla_rules(),
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        matrix = await service.get_approval_matrix(project_id)
        assert matrix["LOW"][0]["role"] == "editor_pm"

        # Global should still have viewer
        global_matrix = await service.get_approval_matrix()
        assert global_matrix["LOW"][0]["role"] == "viewer"

    @pytest.mark.asyncio
    async def test_get_impact_weights_with_project_override(
        self, db_session: AsyncSession
    ) -> None:
        """get_impact_weights returns project-specific weights when override exists."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        modified_weights = _make_impact_weights()
        modified_weights["budget"] = 0.6  # 0.4 -> 0.6
        modified_weights["schedule"] = 0.1  # 0.3 -> 0.1

        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=_make_sla_rules(),
            impact_weights=modified_weights,
            score_boundaries=_make_score_boundaries(),
        )

        weights = await service.get_impact_weights(project_id)
        assert weights["budget"] == Decimal("0.6")
        assert weights["schedule"] == Decimal("0.1")
