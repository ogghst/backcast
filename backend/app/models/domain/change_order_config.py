"""Change Order Workflow Configuration domain models.

Stores configurable parameters for the change order workflow:
- Impact level thresholds and score boundaries
- Approval authority mapping (role-to-authority)
- SLA deadlines per impact level
- Audit log for configuration changes

These are Simple entities (non-versioned, non-branchable) using
SimpleEntityBase. Configuration changes are tracked via the
co_config_audit_log table.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import SimpleEntityBase


class ChangeOrderWorkflowConfig(SimpleEntityBase):
    """Parent configuration record for change order workflow.

    One record per scope: global default (project_id=NULL) or
    per-project override. Uses optimistic locking via version column.

    Attributes:
        config_id: Root UUID for the config aggregation.
        project_id: NULL for global default, UUID for per-project override.
        is_active: Whether this config is active.
        version: Optimistic locking version counter.
        created_by: User who created this config.
        updated_by: User who last updated this config.
        impact_weights: JSONB for impact calculation weights (budget%, schedule%, revenue%, evm%).
        score_boundaries: JSONB for score-to-impact-level mapping thresholds.
    """

    __tablename__ = "co_workflow_config"

    config_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, unique=True, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID, nullable=True, unique=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    created_by: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True)

    # Impact calculation weights (JSONB)
    # Example: {"budget": 0.4, "schedule": 0.3, "revenue": 0.2, "evm": 0.1}
    impact_weights: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Score-to-level boundaries (JSONB)
    # Example: {"LOW": 10, "MEDIUM": 30, "HIGH": 50, "CRITICAL": 999}
    # Meaning: score < LOW -> LOW, score < MEDIUM -> MEDIUM, etc.
    score_boundaries: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Relationships
    impact_levels: Mapped[list["ChangeOrderImpactLevelConfig"]] = relationship(
        "ChangeOrderImpactLevelConfig",
        back_populates="config",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    approval_rules: Mapped[list["ChangeOrderApprovalRuleConfig"]] = relationship(
        "ChangeOrderApprovalRuleConfig",
        back_populates="config",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sla_rules: Mapped[list["ChangeOrderSLARuleConfig"]] = relationship(
        "ChangeOrderSLARuleConfig",
        back_populates="config",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        scope = "global" if self.project_id is None else str(self.project_id)[:8]
        return (
            f"<ChangeOrderWorkflowConfig(id={self.id}, "
            f"scope={scope}, version={self.version})>"
        )


class ChangeOrderImpactLevelConfig(SimpleEntityBase):
    """Impact level configuration with financial thresholds.

    Defines the four fixed impact levels (LOW/MEDIUM/HIGH/CRITICAL)
    with configurable financial thresholds and score boundaries.

    Attributes:
        config_id: FK to parent config.
        level_name: Impact level name (LOW, MEDIUM, HIGH, CRITICAL).
        level_order: Sort order for display (1=LOW, 2=MEDIUM, 3=HIGH, 4=CRITICAL).
        threshold_amount: Maximum amount for this level (upper bound in EUR).
        score_threshold_min: Minimum impact score for this level.
        score_threshold_max: Maximum impact score for this level.
        is_active: Whether this level is active.
    """

    __tablename__ = "co_impact_level_config"

    config_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        sa.ForeignKey("co_workflow_config.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level_name: Mapped[str] = mapped_column(String(20), nullable=False)
    level_order: Mapped[int] = mapped_column(Integer, nullable=False)
    threshold_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False
    )
    score_threshold_min: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    score_threshold_max: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # Relationships
    config: Mapped["ChangeOrderWorkflowConfig"] = relationship(
        "ChangeOrderWorkflowConfig", back_populates="impact_levels"
    )

    def __repr__(self) -> str:
        return (
            f"<ChangeOrderImpactLevelConfig(level={self.level_name}, "
            f"threshold={self.threshold_amount})>"
        )


class ChangeOrderApprovalRuleConfig(SimpleEntityBase):
    """Approval authority mapping for change orders.

    Maps impact levels to required approval authority levels and
    which role can approve at that level. Supports the 5-role system:
    viewer, editor_pm, dept_head, director, admin.

    Attributes:
        config_id: FK to parent config.
        impact_level_name: Impact level this rule applies to.
        required_authority_level: Authority level string (LOW/MEDIUM/HIGH/CRITICAL).
        approver_role: Role that can approve at this level.
    """

    __tablename__ = "co_approval_rule_config"

    config_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        sa.ForeignKey("co_workflow_config.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    impact_level_name: Mapped[str] = mapped_column(String(20), nullable=False)
    required_authority_level: Mapped[str] = mapped_column(String(20), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    config: Mapped["ChangeOrderWorkflowConfig"] = relationship(
        "ChangeOrderWorkflowConfig", back_populates="approval_rules"
    )

    def __repr__(self) -> str:
        return (
            f"<ChangeOrderApprovalRuleConfig(impact={self.impact_level_name}, "
            f"authority={self.required_authority_level}, role={self.approver_role})>"
        )


class ChangeOrderSLARuleConfig(SimpleEntityBase):
    """SLA deadline configuration per impact level.

    Defines the number of business days allowed for approval
    at each impact level.

    Attributes:
        config_id: FK to parent config.
        impact_level_name: Impact level this SLA applies to.
        business_days: Number of business days for SLA deadline.
        escalation_trigger_pct: Percentage of SLA time remaining before escalation (nullable, future use).
    """

    __tablename__ = "co_sla_rule_config"

    config_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        sa.ForeignKey("co_workflow_config.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    impact_level_name: Mapped[str] = mapped_column(String(20), nullable=False)
    business_days: Mapped[int] = mapped_column(Integer, nullable=False)
    escalation_trigger_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=5, scale=2), nullable=True
    )

    # Relationships
    config: Mapped["ChangeOrderWorkflowConfig"] = relationship(
        "ChangeOrderWorkflowConfig", back_populates="sla_rules"
    )

    def __repr__(self) -> str:
        return (
            f"<ChangeOrderSLARuleConfig(impact={self.impact_level_name}, "
            f"days={self.business_days})>"
        )


class ChangeOrderConfigAuditLog(SimpleEntityBase):
    """Audit log for change order workflow configuration changes.

    Records every create/update/delete of configuration with old and new
    values as JSONB for traceability.

    Attributes:
        config_id: FK to the parent config that was changed.
        changed_by: User who made the change.
        old_values: Previous configuration values as JSONB.
        new_values: New configuration values as JSONB.
        changed_at: When the change was made.
    """

    __tablename__ = "co_config_audit_log"

    config_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        sa.ForeignKey("co_workflow_config.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_by: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )

    def __repr__(self) -> str:
        return (
            f"<ChangeOrderConfigAuditLog(config_id={self.config_id}, "
            f"changed_by={self.changed_by})>"
        )
