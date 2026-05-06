"""Pydantic schemas for Change Order Workflow Configuration API.

Source of truth for CO Workflow Config API contracts.
Defines request/response schemas for global and per-project config management.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImpactLevelConfigSchema(BaseModel):
    """Schema for a single impact level configuration."""

    level_name: str = Field(
        ..., description="Impact level name (LOW/MEDIUM/HIGH/CRITICAL)"
    )
    level_order: int = Field(..., ge=1, le=4, description="Sort order (1-4)")
    threshold_amount: Decimal = Field(
        ..., ge=0, description="Maximum amount for this level (upper bound in EUR)"
    )
    score_threshold_min: Decimal = Field(
        ..., ge=0, description="Minimum impact score for this level"
    )
    score_threshold_max: Decimal = Field(
        ..., ge=0, description="Maximum impact score for this level"
    )
    is_active: bool = Field(True, description="Whether this level is active")

    @model_validator(mode="after")
    def validate_score_bounds(self) -> "ImpactLevelConfigSchema":
        """Ensure min <= max for score thresholds."""
        if self.score_threshold_min > self.score_threshold_max:
            raise ValueError("score_threshold_min must be <= score_threshold_max")
        return self


class ApprovalRuleConfigSchema(BaseModel):
    """Schema for an approval rule configuration."""

    impact_level_name: str = Field(..., description="Impact level this rule applies to")
    required_authority_level: str = Field(
        ..., description="Required authority level (LOW/MEDIUM/HIGH/CRITICAL)"
    )
    approver_role: str = Field(..., description="Role that can approve at this level")


class SLARuleConfigSchema(BaseModel):
    """Schema for an SLA rule configuration."""

    impact_level_name: str = Field(..., description="Impact level this SLA applies to")
    business_days: int = Field(
        ..., ge=1, le=60, description="Number of business days for SLA deadline"
    )
    escalation_trigger_pct: Decimal | None = Field(
        None,
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Percentage of SLA time remaining before escalation (future use)",
    )


class ImpactWeightsSchema(BaseModel):
    """Schema for impact calculation weights."""

    budget: Decimal = Field(
        ..., ge=0, le=1, description="Weight for budget impact (0-1)"
    )
    schedule: Decimal = Field(
        ..., ge=0, le=1, description="Weight for schedule impact (0-1)"
    )
    revenue: Decimal = Field(
        ..., ge=0, le=1, description="Weight for revenue impact (0-1)"
    )
    evm: Decimal = Field(..., ge=0, le=1, description="Weight for EVM impact (0-1)")

    @model_validator(mode="after")
    def validate_weights_sum_to_one(self) -> "ImpactWeightsSchema":
        """Ensure weights sum to approximately 1.0."""
        total = self.budget + self.schedule + self.revenue + self.evm
        if abs(total - Decimal("1.0")) > Decimal("0.01"):
            raise ValueError(f"Impact weights must sum to 1.0, got {total}")
        return self


class ScoreBoundariesSchema(BaseModel):
    """Schema for score-to-impact-level boundaries."""

    LOW: Decimal = Field(..., ge=0, description="Upper bound for LOW level")
    MEDIUM: Decimal = Field(..., ge=0, description="Upper bound for MEDIUM level")
    HIGH: Decimal = Field(..., ge=0, description="Upper bound for HIGH level")
    CRITICAL: Decimal = Field(..., ge=0, description="Upper bound for CRITICAL level")

    @model_validator(mode="after")
    def validate_boundaries_ascending(self) -> "ScoreBoundariesSchema":
        """Ensure boundaries are in ascending order."""
        if not (self.LOW <= self.MEDIUM <= self.HIGH <= self.CRITICAL):
            raise ValueError(
                "Score boundaries must be in ascending order: LOW <= MEDIUM <= HIGH <= CRITICAL"
            )
        return self


class WorkflowConfigUpdateRequest(BaseModel):
    """Request schema for creating/updating workflow configuration."""

    impact_levels: list[ImpactLevelConfigSchema] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Impact level configurations (exactly 4)",
    )
    approval_rules: list[ApprovalRuleConfigSchema] = Field(
        ..., min_length=4, description="Approval rules (one per impact level)"
    )
    sla_rules: list[SLARuleConfigSchema] = Field(
        ..., min_length=4, description="SLA rules (one per impact level)"
    )
    impact_weights: ImpactWeightsSchema = Field(
        ..., description="Impact calculation weights"
    )
    score_boundaries: ScoreBoundariesSchema = Field(
        ..., description="Score-to-impact-level boundaries"
    )


class WorkflowConfigResponse(BaseModel):
    """Response schema for workflow configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Config record ID")
    config_id: UUID = Field(..., description="Root config UUID")
    project_id: UUID | None = Field(
        None, description="Project ID (null for global config)"
    )
    is_active: bool = Field(..., description="Whether this config is active")
    version: int = Field(..., description="Optimistic locking version")
    created_by: UUID = Field(..., description="User who created this config")
    updated_by: UUID | None = Field(
        None, description="User who last updated this config"
    )
    created_at: datetime = Field(..., description="When created")
    updated_at: datetime = Field(..., description="When last updated")
    impact_levels: list[ImpactLevelConfigSchema] = Field(
        ..., description="Impact level configurations"
    )
    approval_rules: list[ApprovalRuleConfigSchema] = Field(
        ..., description="Approval rules"
    )
    sla_rules: list[SLARuleConfigSchema] = Field(..., description="SLA rules")
    impact_weights: ImpactWeightsSchema = Field(
        ..., description="Impact calculation weights"
    )
    score_boundaries: ScoreBoundariesSchema = Field(
        ..., description="Score-to-impact-level boundaries"
    )


class ConfigAuditLogResponse(BaseModel):
    """Response schema for config audit log entries."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    config_id: UUID
    changed_by: UUID
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    changed_at: datetime
