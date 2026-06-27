"""Change Order Workflow Configuration Service.

Manages configurable parameters for the change order workflow:
- Impact level thresholds and score boundaries
- Approval authority mapping (role-to-authority)
- SLA deadlines per impact level
- Impact calculation weights

Follows per-project override pattern from ProjectBudgetSettingsService:
- Global config: project_id = NULL
- Per-project override: project_id = UUID
- All-or-nothing override model
- Lazy inheritance (no record = use global)
- Fail loudly if no config exists (no hardcoded fallback)
"""

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order_config import (
    ChangeOrderApprovalRuleConfig,
    ChangeOrderConfigAuditLog,
    ChangeOrderImpactLevelConfig,
    ChangeOrderSLARuleConfig,
    ChangeOrderWorkflowConfig,
)

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when workflow configuration is missing or invalid."""

    pass


class ConfigurationConflictError(Exception):
    """Raised when optimistic locking detects a concurrent update."""

    pass


class ChangeOrderConfigService:
    """Service for change order workflow configuration management.

    Provides CRUD for global and per-project config, active config lookup
    with fallback, snapshot generation for CO submission, and optimistic
    locking for concurrent update protection.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize with a database session.

        Args:
            db_session: Async database session
        """
        self._db = db_session

    async def get_global_config(self) -> ChangeOrderWorkflowConfig | None:
        """Get the global workflow configuration with creator name.

        Returns:
            Global config or None if not found
        """
        from typing import cast

        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )
        stmt = (
            select(
                ChangeOrderWorkflowConfig,
                creator_subq.c.full_name.label("created_by_name"),
            )
            .outerjoin(
                creator_subq,
                ChangeOrderWorkflowConfig.created_by == creator_subq.c.user_id,
            )
            .where(
                ChangeOrderWorkflowConfig.project_id.is_(None),
                ChangeOrderWorkflowConfig.is_active == True,  # noqa: E712
            )
        )
        result = await self._db.execute(stmt)
        row = result.first()
        if row is None:
            return None
        entity = row[0]
        entity.created_by_name = row[1]
        return entity

    async def get_project_config(
        self, project_id: UUID
    ) -> ChangeOrderWorkflowConfig | None:
        """Get a project-specific workflow configuration override with creator name.

        Args:
            project_id: Project UUID

        Returns:
            Project config or None if no override exists
        """
        from typing import cast

        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )
        stmt = (
            select(
                ChangeOrderWorkflowConfig,
                creator_subq.c.full_name.label("created_by_name"),
            )
            .outerjoin(
                creator_subq,
                ChangeOrderWorkflowConfig.created_by == creator_subq.c.user_id,
            )
            .where(
                ChangeOrderWorkflowConfig.project_id == project_id,
                ChangeOrderWorkflowConfig.is_active == True,  # noqa: E712
            )
        )
        result = await self._db.execute(stmt)
        row = result.first()
        if row is None:
            return None
        entity = row[0]
        entity.created_by_name = row[1]
        return entity

    async def get_active_config(
        self, project_id: UUID | None = None
    ) -> ChangeOrderWorkflowConfig:
        """Get the active configuration for a project.

        Resolution order:
        1. Per-project override (if project_id provided and exists)
        2. Global default

        Args:
            project_id: Optional project UUID for per-project lookup

        Returns:
            Active workflow configuration

        Raises:
            ConfigurationError: If no global config exists
        """
        # Try per-project override first
        if project_id is not None:
            project_config = await self.get_project_config(project_id)
            if project_config is not None:
                logger.debug("Using per-project config for project %s", project_id)
                return project_config

        # Fall back to global
        global_config = await self.get_global_config()
        if global_config is None:
            raise ConfigurationError(
                "No global change order workflow configuration found. "
                "An administrator must configure the workflow settings before "
                "change orders can be processed."
            )

        return global_config

    async def get_thresholds(
        self, project_id: UUID | None = None
    ) -> dict[str, Decimal]:
        """Get financial impact thresholds from active config.

        Args:
            project_id: Optional project for per-project override

        Returns:
            Dict mapping level_name -> threshold_amount
        """
        config = await self.get_active_config(project_id)
        return {
            level.level_name: level.threshold_amount
            for level in config.impact_levels
            if level.is_active
        }

    async def get_sla_days(self, project_id: UUID | None = None) -> dict[str, int]:
        """Get SLA business days per impact level.

        Args:
            project_id: Optional project for per-project override

        Returns:
            Dict mapping level_name -> business_days
        """
        config = await self.get_active_config(project_id)
        return {rule.impact_level_name: rule.business_days for rule in config.sla_rules}

    async def get_approval_matrix(
        self, project_id: UUID | None = None
    ) -> dict[str, list[dict[str, str]]]:
        """Get approval authority mapping from active config.

        Args:
            project_id: Optional project for per-project override

        Returns:
            Dict mapping impact_level -> list of {role, authority}
        """
        config = await self.get_active_config(project_id)
        result: dict[str, list[dict[str, str]]] = {}
        for rule in config.approval_rules:
            if rule.impact_level_name not in result:
                result[rule.impact_level_name] = []
            result[rule.impact_level_name].append(
                {
                    "role": rule.approver_role,
                    "authority_level": rule.required_authority_level,
                }
            )
        return result

    async def get_authority_hierarchy(
        self, project_id: UUID | None = None
    ) -> dict[str, int]:
        """Get authority level hierarchy from approval rules.

        Derives the hierarchy from unique authority levels in the config.

        Args:
            project_id: Optional project for per-project override

        Returns:
            Dict mapping authority_level -> numeric rank (higher = more authority)
        """
        config = await self.get_active_config(project_id)
        authority_levels: set[str] = set()
        for rule in config.approval_rules:
            authority_levels.add(rule.required_authority_level)

        # Standard authority order: LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4
        standard_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        return {
            level: standard_order.get(level, idx + 1)
            for idx, level in enumerate(sorted(authority_levels))
        }

    async def get_role_authority_mapping(
        self, project_id: UUID | None = None
    ) -> dict[str, str]:
        """Get role-to-highest-authority-level mapping.

        Args:
            project_id: Optional project for per-project override

        Returns:
            Dict mapping role -> highest authority level that role can approve
        """
        config = await self.get_active_config(project_id)
        hierarchy = await self.get_authority_hierarchy(project_id)

        role_authority: dict[str, str] = {}
        for rule in config.approval_rules:
            role = rule.approver_role
            authority = rule.required_authority_level
            # Keep the highest authority for each role
            if role not in role_authority:
                role_authority[role] = authority
            elif hierarchy.get(authority, 0) > hierarchy.get(role_authority[role], 0):
                role_authority[role] = authority

        return role_authority

    async def get_impact_authority_mapping(
        self, project_id: UUID | None = None
    ) -> dict[str, str]:
        """Get impact-level-to-required-authority mapping.

        Args:
            project_id: Optional project for per-project override

        Returns:
            Dict mapping impact_level -> required authority level
        """
        config = await self.get_active_config(project_id)
        return {
            rule.impact_level_name: rule.required_authority_level
            for rule in config.approval_rules
        }

    async def get_score_boundaries(
        self, project_id: UUID | None = None
    ) -> dict[str, Decimal]:
        """Get score-to-impact-level boundaries from active config.

        Args:
            project_id: Optional project for per-project override

        Returns:
            Dict mapping level_name -> upper bound score
        """
        config = await self.get_active_config(project_id)
        if config.score_boundaries:
            return {k: Decimal(str(v)) for k, v in config.score_boundaries.items()}
        # Fallback to impact level configs if score_boundaries not set
        return {
            level.level_name: level.score_threshold_max
            for level in config.impact_levels
        }

    async def get_impact_weights(
        self, project_id: UUID | None = None
    ) -> dict[str, Decimal]:
        """Get impact calculation weights from active config.

        Args:
            project_id: Optional project for per-project override

        Returns:
            Dict with keys: budget, schedule, revenue, evm and their weights
        """
        config = await self.get_active_config(project_id)
        if config.impact_weights:
            return {k: Decimal(str(v)) for k, v in config.impact_weights.items()}
        # Default weights if not set
        return {
            "budget": Decimal("0.4"),
            "schedule": Decimal("0.3"),
            "revenue": Decimal("0.2"),
            "evm": Decimal("0.1"),
        }

    async def get_workflow_transitions(
        self, project_id: UUID | None = None
    ) -> dict[str, Any] | None:
        """Get workflow transitions from active config.

        Args:
            project_id: Optional project for per-project override

        Returns:
            Transition graph dict or None if not configured
        """
        config = await self.get_active_config(project_id)
        return config.workflow_transitions

    async def get_escalation_triggers(
        self, project_id: UUID | None = None
    ) -> dict[str, Decimal]:
        """Get escalation trigger percentages per impact level.

        Args:
            project_id: Optional project for per-project override

        Returns:
            Dict mapping level_name -> escalation_trigger_pct
        """
        config = await self.get_active_config(project_id)
        result: dict[str, Decimal] = {}
        for rule in config.sla_rules:
            if rule.escalation_trigger_pct is not None:
                result[rule.impact_level_name] = rule.escalation_trigger_pct
        return result

    def classify_impact_by_score(
        self,
        score: Decimal,
        boundaries: dict[str, Decimal],
    ) -> str:
        """Classify impact level from score using config boundaries.

        Args:
            score: Impact severity score
            boundaries: Score boundaries from config

        Returns:
            Impact level string (LOW/MEDIUM/HIGH/CRITICAL)
        """
        if score < boundaries.get("LOW", Decimal("10")):
            return "LOW"
        elif score < boundaries.get("MEDIUM", Decimal("30")):
            return "MEDIUM"
        elif score < boundaries.get("HIGH", Decimal("50")):
            return "HIGH"
        else:
            return "CRITICAL"

    def classify_financial_impact(
        self,
        budget_delta: Decimal,
        thresholds: dict[str, Decimal],
    ) -> str:
        """Classify financial impact level from budget delta using config thresholds.

        Args:
            budget_delta: Absolute budget change amount
            thresholds: Financial thresholds from config

        Returns:
            Impact level string (LOW/MEDIUM/HIGH/CRITICAL)
        """
        if budget_delta < thresholds.get("LOW", Decimal("10000")):
            return "LOW"
        elif budget_delta < thresholds.get("MEDIUM", Decimal("50000")):
            return "MEDIUM"
        elif budget_delta < thresholds.get("HIGH", Decimal("100000")):
            return "HIGH"
        else:
            return "CRITICAL"

    async def generate_snapshot(self, project_id: UUID | None = None) -> dict[str, Any]:
        """Generate a config snapshot for storing on CO submission.

        Creates a frozen copy of the active config as a JSONB-compatible
        dict. This is stored on the change order at submission time to
        preserve the config that was active when the CO was submitted.

        Args:
            project_id: Optional project for per-project override

        Returns:
            Dict representation of the active config
        """
        config = await self.get_active_config(project_id)

        snapshot: dict[str, Any] = {
            "config_id": str(config.config_id),
            "impact_levels": [
                {
                    "level_name": level.level_name,
                    "level_order": level.level_order,
                    "threshold_amount": float(level.threshold_amount),
                    "score_threshold_min": float(level.score_threshold_min),
                    "score_threshold_max": float(level.score_threshold_max),
                }
                for level in config.impact_levels
                if level.is_active
            ],
            "approval_rules": [
                {
                    "impact_level_name": rule.impact_level_name,
                    "required_authority_level": rule.required_authority_level,
                    "approver_role": rule.approver_role,
                }
                for rule in config.approval_rules
            ],
            "sla_rules": [
                {
                    "impact_level_name": rule.impact_level_name,
                    "business_days": rule.business_days,
                    "escalation_trigger_pct": (
                        float(rule.escalation_trigger_pct)
                        if rule.escalation_trigger_pct
                        else None
                    ),
                }
                for rule in config.sla_rules
            ],
            "impact_weights": config.impact_weights,
            "score_boundaries": config.score_boundaries,
            "workflow_transitions": config.workflow_transitions,
            "holiday_country_code": config.holiday_country_code,
            "custom_fields": config.custom_fields,
        }

        return snapshot

    async def create_global_config(
        self,
        actor_id: UUID,
        impact_levels: list[dict[str, Any]],
        approval_rules: list[dict[str, Any]],
        sla_rules: list[dict[str, Any]],
        impact_weights: dict[str, Any],
        score_boundaries: dict[str, Any],
        workflow_transitions: dict[str, Any] | None = None,
        holiday_country_code: str | None = None,
        custom_fields: list[dict[str, Any]] | None = None,
    ) -> ChangeOrderWorkflowConfig:
        """Create the global workflow configuration.

        Args:
            actor_id: User creating the config
            impact_levels: Impact level configurations
            approval_rules: Approval rule configurations
            sla_rules: SLA rule configurations
            impact_weights: Impact calculation weights
            score_boundaries: Score-to-level boundaries

        Returns:
            Created config record

        Raises:
            ConfigurationError: If global config already exists
        """
        existing = await self.get_global_config()
        if existing is not None:
            raise ConfigurationError(
                "Global workflow configuration already exists. Use update to modify it."
            )

        return await self._create_config(
            project_id=None,
            actor_id=actor_id,
            impact_levels=impact_levels,
            approval_rules=approval_rules,
            sla_rules=sla_rules,
            impact_weights=impact_weights,
            score_boundaries=score_boundaries,
            workflow_transitions=workflow_transitions,
            holiday_country_code=holiday_country_code,
            custom_fields=custom_fields,
        )

    async def update_config(
        self,
        config_id: UUID,
        actor_id: UUID,
        version: int,
        impact_levels: list[dict[str, Any]],
        approval_rules: list[dict[str, Any]],
        sla_rules: list[dict[str, Any]],
        impact_weights: dict[str, Any],
        score_boundaries: dict[str, Any],
        workflow_transitions: dict[str, Any] | None = None,
        holiday_country_code: str | None = None,
        custom_fields: list[dict[str, Any]] | None = None,
    ) -> ChangeOrderWorkflowConfig:
        """Update an existing workflow configuration.

        Uses optimistic locking: the version must match the current version
        in the database.

        Args:
            config_id: Root config UUID to update
            actor_id: User making the update
            version: Expected current version (for optimistic locking)
            impact_levels: Updated impact level configurations
            approval_rules: Updated approval rule configurations
            sla_rules: Updated SLA rule configurations
            impact_weights: Updated impact calculation weights
            score_boundaries: Updated score-to-level boundaries

        Returns:
            Updated config record

        Raises:
            ConfigurationError: If config not found
            ConfigurationConflictError: If version mismatch (concurrent update)
        """
        # Fetch existing config
        stmt = select(ChangeOrderWorkflowConfig).where(
            ChangeOrderWorkflowConfig.config_id == config_id
        )
        result = await self._db.execute(stmt)
        config = result.scalar_one_or_none()

        if config is None:
            raise ConfigurationError(f"Configuration {config_id} not found.")

        # Optimistic locking check
        if config.version != version:
            raise ConfigurationConflictError(
                f"Configuration was modified by another user "
                f"(expected version {version}, current is {config.version}). "
                f"Please refresh and try again."
            )

        # Snapshot old values for audit
        old_values = await self._config_to_dict(config)

        # Delete existing child records
        for level in list(config.impact_levels):
            await self._db.delete(level)
        for rule in list(config.approval_rules):
            await self._db.delete(rule)
        for sla_rule in list(config.sla_rules):
            await self._db.delete(sla_rule)
        await self._db.flush()

        # Update parent record
        config.version = version + 1
        config.updated_by = actor_id
        config.impact_weights = impact_weights
        config.score_boundaries = score_boundaries
        config.workflow_transitions = workflow_transitions
        config.holiday_country_code = holiday_country_code
        config.custom_fields = custom_fields

        # Create new child records
        await self._create_impact_levels(config.id, impact_levels)
        await self._create_approval_rules(config.id, approval_rules)
        await self._create_sla_rules(config.id, sla_rules)

        await self._db.flush()

        # Refresh to load relationships
        await self._db.refresh(config)

        # Audit log
        new_values = await self._config_to_dict(config)
        await self._write_audit_log(
            config_pk=config.id,
            actor_id=actor_id,
            old_values=old_values,
            new_values=new_values,
        )

        logger.info(
            "Updated workflow config %s to version %d",
            config.config_id,
            config.version,
        )
        return config

    async def create_project_override(
        self,
        project_id: UUID,
        actor_id: UUID,
        impact_levels: list[dict[str, Any]],
        approval_rules: list[dict[str, Any]],
        sla_rules: list[dict[str, Any]],
        impact_weights: dict[str, Any],
        score_boundaries: dict[str, Any],
        workflow_transitions: dict[str, Any] | None = None,
        holiday_country_code: str | None = None,
        custom_fields: list[dict[str, Any]] | None = None,
    ) -> ChangeOrderWorkflowConfig:
        """Create a per-project configuration override.

        Args:
            project_id: Project to override config for
            actor_id: User creating the override
            impact_levels: Impact level configurations
            approval_rules: Approval rule configurations
            sla_rules: SLA rule configurations
            impact_weights: Impact calculation weights
            score_boundaries: Score-to-level boundaries

        Returns:
            Created project config record

        Raises:
            ConfigurationError: If override already exists for this project
        """
        existing = await self.get_project_config(project_id)
        if existing is not None:
            raise ConfigurationError(
                f"Project {project_id} already has a configuration override. "
                f"Use update to modify it."
            )

        return await self._create_config(
            project_id=project_id,
            actor_id=actor_id,
            impact_levels=impact_levels,
            approval_rules=approval_rules,
            sla_rules=sla_rules,
            impact_weights=impact_weights,
            score_boundaries=score_boundaries,
            workflow_transitions=workflow_transitions,
            holiday_country_code=holiday_country_code,
            custom_fields=custom_fields,
        )

    async def delete_project_override(self, project_id: UUID, actor_id: UUID) -> None:
        """Delete a per-project configuration override (reset to global).

        Args:
            project_id: Project to reset
            actor_id: User performing the reset

        Raises:
            ConfigurationError: If no override exists for this project
        """
        config = await self.get_project_config(project_id)
        if config is None:
            raise ConfigurationError(
                f"No configuration override found for project {project_id}."
            )

        # Audit log before deletion
        old_values = await self._config_to_dict(config)
        await self._write_audit_log(
            config_pk=config.id,
            actor_id=actor_id,
            old_values=old_values,
            new_values=None,
        )

        await self._db.delete(config)
        await self._db.flush()

        logger.info("Deleted project override for project %s", project_id)

    async def get_config_by_config_id(
        self, config_id: UUID
    ) -> ChangeOrderWorkflowConfig | None:
        """Get a config record by its root config_id.

        Args:
            config_id: Root config UUID

        Returns:
            Config record or None
        """
        stmt = select(ChangeOrderWorkflowConfig).where(
            ChangeOrderWorkflowConfig.config_id == config_id
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    # --- Private helpers ---

    async def _create_config(
        self,
        project_id: UUID | None,
        actor_id: UUID,
        impact_levels: list[dict[str, Any]],
        approval_rules: list[dict[str, Any]],
        sla_rules: list[dict[str, Any]],
        impact_weights: dict[str, Any],
        score_boundaries: dict[str, Any],
        workflow_transitions: dict[str, Any] | None = None,
        holiday_country_code: str | None = None,
        custom_fields: list[dict[str, Any]] | None = None,
    ) -> ChangeOrderWorkflowConfig:
        """Create a new workflow configuration with child records."""
        config_id = uuid4()
        config = ChangeOrderWorkflowConfig(
            config_id=config_id,
            project_id=project_id,
            is_active=True,
            version=1,
            created_by=actor_id,
            updated_by=None,
            impact_weights=impact_weights,
            score_boundaries=score_boundaries,
            workflow_transitions=workflow_transitions,
            holiday_country_code=holiday_country_code,
            custom_fields=custom_fields,
        )
        self._db.add(config)
        await self._db.flush()

        # Create child records
        await self._create_impact_levels(config.id, impact_levels)
        await self._create_approval_rules(config.id, approval_rules)
        await self._create_sla_rules(config.id, sla_rules)
        await self._db.flush()

        # Refresh to load relationships
        await self._db.refresh(config)

        # Audit log
        new_values = await self._config_to_dict(config)
        await self._write_audit_log(
            config_pk=config.id,
            actor_id=actor_id,
            old_values=None,
            new_values=new_values,
        )

        scope = "global" if project_id is None else str(project_id)[:8]
        logger.info("Created workflow config for scope %s", scope)
        return config

    async def _create_impact_levels(
        self, config_pk: UUID, levels: list[dict[str, Any]]
    ) -> None:
        """Create impact level config records."""
        for level_data in levels:
            level = ChangeOrderImpactLevelConfig(
                config_id=config_pk,
                level_name=level_data["level_name"],
                level_order=level_data["level_order"],
                threshold_amount=Decimal(str(level_data["threshold_amount"])),
                score_threshold_min=Decimal(str(level_data["score_threshold_min"])),
                score_threshold_max=Decimal(str(level_data["score_threshold_max"])),
                is_active=level_data.get("is_active", True),
            )
            self._db.add(level)

    async def _create_approval_rules(
        self, config_pk: UUID, rules: list[dict[str, Any]]
    ) -> None:
        """Create approval rule config records."""
        for rule_data in rules:
            rule = ChangeOrderApprovalRuleConfig(
                config_id=config_pk,
                impact_level_name=rule_data["impact_level_name"],
                required_authority_level=rule_data["required_authority_level"],
                approver_role=rule_data["approver_role"],
            )
            self._db.add(rule)

    async def _create_sla_rules(
        self, config_pk: UUID, rules: list[dict[str, Any]]
    ) -> None:
        """Create SLA rule config records."""
        for rule_data in rules:
            sla_rule = ChangeOrderSLARuleConfig(
                config_id=config_pk,
                impact_level_name=rule_data["impact_level_name"],
                business_days=rule_data["business_days"],
                escalation_trigger_pct=rule_data.get("escalation_trigger_pct"),
            )
            self._db.add(sla_rule)

    async def _config_to_dict(
        self, config: ChangeOrderWorkflowConfig
    ) -> dict[str, Any]:
        """Serialize a config record to a dict for audit logging."""
        return {
            "config_id": str(config.config_id),
            "project_id": str(config.project_id) if config.project_id else None,
            "version": config.version,
            "impact_weights": config.impact_weights,
            "score_boundaries": config.score_boundaries,
            "impact_levels": [
                {
                    "level_name": il.level_name,
                    "threshold_amount": float(il.threshold_amount),
                }
                for il in config.impact_levels
            ],
            "approval_rules": [
                {
                    "impact_level_name": r.impact_level_name,
                    "approver_role": r.approver_role,
                }
                for r in config.approval_rules
            ],
            "sla_rules": [
                {
                    "impact_level_name": s.impact_level_name,
                    "business_days": s.business_days,
                }
                for s in config.sla_rules
            ],
            "workflow_transitions": config.workflow_transitions,
            "holiday_country_code": config.holiday_country_code,
            "custom_fields": config.custom_fields,
        }

    async def _write_audit_log(
        self,
        config_pk: UUID,
        actor_id: UUID,
        old_values: dict[str, Any] | None,
        new_values: dict[str, Any] | None,
    ) -> None:
        """Write an audit log entry for a config change."""
        log_entry = ChangeOrderConfigAuditLog(
            config_id=config_pk,
            changed_by=actor_id,
            old_values=old_values,
            new_values=new_values,
        )
        self._db.add(log_entry)
