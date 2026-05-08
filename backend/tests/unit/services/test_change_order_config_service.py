"""Unit tests for ChangeOrderConfigService.

Tests the change order workflow configuration service including:
- Global config retrieval (seeded from migration)
- Config update with optimistic locking
- Project-specific overrides
- Snapshot generation
- Audit log creation

The migration seeds a global config with these values:
  Thresholds: LOW=10000, MEDIUM=50000, HIGH=100000, CRITICAL=999999999
  SLA days:   LOW=2, MEDIUM=5, HIGH=10, CRITICAL=15
  Approval rules: LOW->viewer, MEDIUM->editor_pm, HIGH->dept_head/director, CRITICAL->admin
  Weights: budget=0.4, schedule=0.3, revenue=0.2, evm=0.1
  Score boundaries: LOW=10, MEDIUM=30, HIGH=50, CRITICAL=999
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order_config import (
    ChangeOrderConfigAuditLog,
)
from app.services.change_order_config_service import (
    ChangeOrderConfigService,
    ConfigurationConflictError,
    ConfigurationError,
)


def _make_impact_levels() -> list[dict]:
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


def _make_approval_rules() -> list[dict]:
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


def _make_sla_rules() -> list[dict]:
    """Create default SLA rule config data."""
    return [
        {"impact_level_name": "LOW", "business_days": 2},
        {"impact_level_name": "MEDIUM", "business_days": 5},
        {"impact_level_name": "HIGH", "business_days": 10},
        {"impact_level_name": "CRITICAL", "business_days": 15},
    ]


def _make_impact_weights() -> dict:
    """Create default impact weights."""
    return {"budget": 0.4, "schedule": 0.3, "revenue": 0.2, "evm": 0.1}


def _make_score_boundaries() -> dict:
    """Create default score boundaries."""
    return {"LOW": 10, "MEDIUM": 30, "HIGH": 50, "CRITICAL": 999}


class TestGetGlobalConfig:
    """Test get_global_config retrieval."""

    @pytest.mark.asyncio
    async def test_get_global_config_returns_seeded_defaults(
        self, db_session: AsyncSession
    ) -> None:
        """Verify the seeded global config is returned with correct values."""
        service = ChangeOrderConfigService(db_session)

        config = await service.get_global_config()

        assert config is not None
        assert config.project_id is None
        assert config.is_active is True
        assert config.version == 1

        # Verify impact levels
        levels = sorted(config.impact_levels, key=lambda level: level.level_order)
        assert len(levels) == 4
        assert levels[0].level_name == "LOW"
        assert levels[0].threshold_amount == Decimal("10000.00")
        assert levels[1].level_name == "MEDIUM"
        assert levels[1].threshold_amount == Decimal("50000.00")
        assert levels[2].level_name == "HIGH"
        assert levels[2].threshold_amount == Decimal("100000.00")
        assert levels[3].level_name == "CRITICAL"

        # Verify SLA rules
        sla_map = {r.impact_level_name: r.business_days for r in config.sla_rules}
        assert sla_map["LOW"] == 2
        assert sla_map["MEDIUM"] == 5
        assert sla_map["HIGH"] == 10
        assert sla_map["CRITICAL"] == 15

        # Verify approval rules exist
        assert len(config.approval_rules) >= 4

        # Verify weights and boundaries
        assert config.impact_weights["budget"] == 0.4
        assert config.score_boundaries["LOW"] == 10


class TestUpdateGlobalConfig:
    """Test update_config with optimistic locking."""

    @pytest.mark.asyncio
    async def test_update_global_config_persists(
        self, db_session: AsyncSession
    ) -> None:
        """Update impact level thresholds, verify they persist."""
        service = ChangeOrderConfigService(db_session)
        actor_id = uuid4()

        # Get current config
        config = await service.get_global_config()
        assert config is not None

        # Capture version before update (object is tracked by session)
        original_version = config.version

        # Update with new thresholds
        updated_levels = _make_impact_levels()
        updated_levels[0]["threshold_amount"] = "25000"  # LOW: 10000 -> 25000
        updated_levels[1]["threshold_amount"] = "75000"  # MEDIUM: 50000 -> 75000

        updated = await service.update_config(
            config_id=config.config_id,
            actor_id=actor_id,
            version=original_version,
            impact_levels=updated_levels,
            approval_rules=_make_approval_rules(),
            sla_rules=_make_sla_rules(),
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        # Verify version bumped from original
        assert updated.version == original_version + 1

        # Verify new thresholds
        levels = sorted(updated.impact_levels, key=lambda level: level.level_order)
        assert levels[0].threshold_amount == Decimal("25000")
        assert levels[1].threshold_amount == Decimal("75000")

    @pytest.mark.asyncio
    async def test_optimistic_locking_rejects_stale_update(
        self, db_session: AsyncSession
    ) -> None:
        """Fetch config v1, simulate concurrent update to v2, then try
        updating with v1 version -- should raise ConfigurationConflictError."""
        service = ChangeOrderConfigService(db_session)
        actor_id = uuid4()

        # Fetch config at v1
        config = await service.get_global_config()
        assert config is not None
        stale_version = config.version
        config_id = config.config_id

        # Simulate concurrent update (bumps to v2)
        await service.update_config(
            config_id=config_id,
            actor_id=actor_id,
            version=stale_version,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=_make_sla_rules(),
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        # Try updating with the stale version -- should fail
        with pytest.raises(ConfigurationConflictError, match="expected version"):
            await service.update_config(
                config_id=config_id,
                actor_id=actor_id,
                version=stale_version,
                impact_levels=_make_impact_levels(),
                approval_rules=_make_approval_rules(),
                sla_rules=_make_sla_rules(),
                impact_weights=_make_impact_weights(),
                score_boundaries=_make_score_boundaries(),
            )


class TestMissingConfig:
    """Test behavior when config is missing."""

    @pytest.mark.asyncio
    async def test_missing_config_raises_error(self, db_session: AsyncSession) -> None:
        """When no global config exists, get_active_config raises
        ConfigurationError."""
        service = ChangeOrderConfigService(db_session)

        # Delete the seeded global config
        config = await service.get_global_config()
        assert config is not None
        await db_session.delete(config)
        await db_session.flush()

        # Now get_active_config should raise
        with pytest.raises(ConfigurationError, match="No global"):
            await service.get_active_config()


class TestGenerateSnapshot:
    """Test snapshot generation."""

    @pytest.mark.asyncio
    async def test_generate_config_snapshot(self, db_session: AsyncSession) -> None:
        """Verify snapshot generation produces valid dict with all sections."""
        service = ChangeOrderConfigService(db_session)

        snapshot = await service.generate_snapshot()

        assert "config_id" in snapshot
        assert "impact_levels" in snapshot
        assert "approval_rules" in snapshot
        assert "sla_rules" in snapshot
        assert "impact_weights" in snapshot
        assert "score_boundaries" in snapshot

        # Verify impact levels contain expected fields
        assert len(snapshot["impact_levels"]) == 4
        level = snapshot["impact_levels"][0]
        assert "level_name" in level
        assert "threshold_amount" in level
        assert "score_threshold_min" in level
        assert "score_threshold_max" in level

        # Verify approval rules
        assert len(snapshot["approval_rules"]) >= 4

        # Verify SLA rules
        assert len(snapshot["sla_rules"]) == 4

        # Verify weights and boundaries
        assert snapshot["impact_weights"]["budget"] == 0.4
        assert snapshot["score_boundaries"]["LOW"] == 10


class TestProjectOverride:
    """Test per-project override CRUD."""

    @pytest.mark.asyncio
    async def test_create_project_override(self, db_session: AsyncSession) -> None:
        """Create a project-specific override, verify it coexists with global."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        override = await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=_make_sla_rules(),
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        assert override is not None
        assert override.project_id == project_id
        assert override.version == 1
        assert override.is_active is True

        # Global config should still exist
        global_config = await service.get_global_config()
        assert global_config is not None
        assert global_config.project_id is None

    @pytest.mark.asyncio
    async def test_get_active_config_falls_back_to_global(
        self, db_session: AsyncSession
    ) -> None:
        """When project has no override, returns global config."""
        service = ChangeOrderConfigService(db_session)
        random_project_id = uuid4()

        config = await service.get_active_config(random_project_id)

        assert config is not None
        assert config.project_id is None  # Falls back to global

    @pytest.mark.asyncio
    async def test_get_active_config_returns_project_override(
        self, db_session: AsyncSession
    ) -> None:
        """When project has an override, returns it instead of global."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        # Create override with modified SLA
        modified_sla = _make_sla_rules()
        modified_sla[0]["business_days"] = 99  # LOW: 2 -> 99

        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=modified_sla,
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        # get_active_config should return the project override
        config = await service.get_active_config(project_id)
        assert config.project_id == project_id

        sla_map = {r.impact_level_name: r.business_days for r in config.sla_rules}
        assert sla_map["LOW"] == 99

    @pytest.mark.asyncio
    async def test_delete_project_override(self, db_session: AsyncSession) -> None:
        """Delete project config, verify it is gone."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        # Create override
        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=_make_sla_rules(),
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        # Verify it exists
        override = await service.get_project_config(project_id)
        assert override is not None

        # Delete it
        await service.delete_project_override(project_id, actor_id=uuid4())

        # Verify it is gone
        deleted = await service.get_project_config(project_id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_override_raises_error(
        self, db_session: AsyncSession
    ) -> None:
        """Deleting a non-existent override should raise ConfigurationError."""
        service = ChangeOrderConfigService(db_session)

        with pytest.raises(ConfigurationError, match="No configuration override"):
            await service.delete_project_override(uuid4(), actor_id=uuid4())

    @pytest.mark.asyncio
    async def test_create_duplicate_override_raises_error(
        self, db_session: AsyncSession
    ) -> None:
        """Creating a second override for same project should raise."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=_make_sla_rules(),
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        with pytest.raises(ConfigurationError, match="already has a configuration"):
            await service.create_project_override(
                project_id=project_id,
                actor_id=actor_id,
                impact_levels=_make_impact_levels(),
                approval_rules=_make_approval_rules(),
                sla_rules=_make_sla_rules(),
                impact_weights=_make_impact_weights(),
                score_boundaries=_make_score_boundaries(),
            )


class TestAuditLog:
    """Test audit log creation on config changes."""

    @pytest.mark.asyncio
    async def test_audit_log_created_on_update(self, db_session: AsyncSession) -> None:
        """After updating config, verify audit log entry exists."""
        service = ChangeOrderConfigService(db_session)
        actor_id = uuid4()

        config = await service.get_global_config()
        assert config is not None

        await service.update_config(
            config_id=config.config_id,
            actor_id=actor_id,
            version=config.version,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=_make_sla_rules(),
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        # Query audit log
        stmt = select(ChangeOrderConfigAuditLog).where(
            ChangeOrderConfigAuditLog.changed_by == actor_id
        )
        result = await db_session.execute(stmt)
        audit_entries = result.scalars().all()

        assert len(audit_entries) >= 1
        entry = audit_entries[0]
        assert entry.old_values is not None
        assert entry.new_values is not None
        assert entry.changed_by == actor_id

    @pytest.mark.asyncio
    async def test_audit_log_created_on_project_override_create(
        self, db_session: AsyncSession
    ) -> None:
        """Creating a project override writes an audit log with old_values=None
        and new_values populated."""
        service = ChangeOrderConfigService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        await service.create_project_override(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=_make_impact_levels(),
            approval_rules=_make_approval_rules(),
            sla_rules=_make_sla_rules(),
            impact_weights=_make_impact_weights(),
            score_boundaries=_make_score_boundaries(),
        )

        # Find the create audit entry
        stmt = select(ChangeOrderConfigAuditLog).where(
            ChangeOrderConfigAuditLog.changed_by == actor_id
        )
        result = await db_session.execute(stmt)
        entries = result.scalars().all()

        assert len(entries) >= 1
        create_entry = entries[0]
        assert create_entry.old_values is None  # No old values on create
        assert create_entry.new_values is not None  # New values populated


class TestHelperMethods:
    """Test convenience methods that read from config."""

    @pytest.mark.asyncio
    async def test_get_thresholds(self, db_session: AsyncSession) -> None:
        """get_thresholds returns level_name -> threshold_amount dict."""
        service = ChangeOrderConfigService(db_session)

        thresholds = await service.get_thresholds()

        assert thresholds["LOW"] == Decimal("10000.00")
        assert thresholds["MEDIUM"] == Decimal("50000.00")
        assert thresholds["HIGH"] == Decimal("100000.00")
        assert thresholds["CRITICAL"] == Decimal("999999999.00")

    @pytest.mark.asyncio
    async def test_get_sla_days(self, db_session: AsyncSession) -> None:
        """get_sla_days returns level_name -> business_days dict."""
        service = ChangeOrderConfigService(db_session)

        sla_days = await service.get_sla_days()

        assert sla_days["LOW"] == 2
        assert sla_days["MEDIUM"] == 5
        assert sla_days["HIGH"] == 10
        assert sla_days["CRITICAL"] == 15

    @pytest.mark.asyncio
    async def test_get_approval_matrix(self, db_session: AsyncSession) -> None:
        """get_approval_matrix returns impact_level -> list of role/authority."""
        service = ChangeOrderConfigService(db_session)

        matrix = await service.get_approval_matrix()

        assert "LOW" in matrix
        assert "MEDIUM" in matrix
        assert "HIGH" in matrix
        assert "CRITICAL" in matrix

        # HIGH should have two approvers (dept_head and director)
        assert len(matrix["HIGH"]) == 2
        roles = {r["role"] for r in matrix["HIGH"]}
        assert "dept_head" in roles
        assert "director" in roles

    @pytest.mark.asyncio
    async def test_get_impact_authority_mapping(self, db_session: AsyncSession) -> None:
        """get_impact_authority_mapping returns impact -> authority."""
        service = ChangeOrderConfigService(db_session)

        mapping = await service.get_impact_authority_mapping()

        assert mapping["LOW"] == "LOW"
        assert mapping["MEDIUM"] == "MEDIUM"
        assert mapping["HIGH"] == "HIGH"
        assert mapping["CRITICAL"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_get_role_authority_mapping(self, db_session: AsyncSession) -> None:
        """get_role_authority_mapping returns role -> highest authority."""
        service = ChangeOrderConfigService(db_session)

        mapping = await service.get_role_authority_mapping()

        assert mapping["viewer"] == "LOW"
        assert mapping["editor_pm"] == "MEDIUM"
        assert mapping["admin"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_classify_financial_impact(self, db_session: AsyncSession) -> None:
        """classify_financial_impact returns correct level for amounts."""
        service = ChangeOrderConfigService(db_session)

        assert (
            service.classify_financial_impact(Decimal("0"), {"LOW": Decimal("10000")})
            == "LOW"
        )
        assert (
            service.classify_financial_impact(
                Decimal("5000"), {"LOW": Decimal("10000")}
            )
            == "LOW"
        )
        assert (
            service.classify_financial_impact(
                Decimal("10000"), {"LOW": Decimal("10000"), "MEDIUM": Decimal("50000")}
            )
            == "MEDIUM"
        )
        assert (
            service.classify_financial_impact(
                Decimal("50000"),
                {
                    "LOW": Decimal("10000"),
                    "MEDIUM": Decimal("50000"),
                    "HIGH": Decimal("100000"),
                },
            )
            == "HIGH"
        )
        assert (
            service.classify_financial_impact(
                Decimal("100000"),
                {
                    "LOW": Decimal("10000"),
                    "MEDIUM": Decimal("50000"),
                    "HIGH": Decimal("100000"),
                },
            )
            == "CRITICAL"
        )

    @pytest.mark.asyncio
    async def test_get_score_boundaries(self, db_session: AsyncSession) -> None:
        """get_score_boundaries returns level -> upper bound score."""
        service = ChangeOrderConfigService(db_session)

        boundaries = await service.get_score_boundaries()

        assert boundaries["LOW"] == Decimal("10")
        assert boundaries["MEDIUM"] == Decimal("30")
        assert boundaries["HIGH"] == Decimal("50")
        assert boundaries["CRITICAL"] == Decimal("999")

    @pytest.mark.asyncio
    async def test_get_impact_weights(self, db_session: AsyncSession) -> None:
        """get_impact_weights returns weight name -> value."""
        service = ChangeOrderConfigService(db_session)

        weights = await service.get_impact_weights()

        assert weights["budget"] == Decimal("0.4")
        assert weights["schedule"] == Decimal("0.3")
        assert weights["revenue"] == Decimal("0.2")
        assert weights["evm"] == Decimal("0.1")

    @pytest.mark.asyncio
    async def test_get_config_by_config_id(self, db_session: AsyncSession) -> None:
        """get_config_by_config_id returns config by root UUID."""
        service = ChangeOrderConfigService(db_session)

        global_config = await service.get_global_config()
        assert global_config is not None

        found = await service.get_config_by_config_id(global_config.config_id)
        assert found is not None
        assert found.config_id == global_config.config_id

    @pytest.mark.asyncio
    async def test_get_config_by_config_id_returns_none_for_unknown(
        self, db_session: AsyncSession
    ) -> None:
        """get_config_by_config_id returns None for unknown UUID."""
        service = ChangeOrderConfigService(db_session)

        result = await service.get_config_by_config_id(uuid4())
        assert result is None
