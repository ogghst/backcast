"""Pydantic schemas for Project Budget Settings."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectBudgetSettingsBase(BaseModel):
    """Shared properties for Project Budget Settings."""

    warning_threshold_percent: Decimal = Field(
        default=Decimal("80.0"),
        ge=Decimal("0.0"),
        le=Decimal("100.0"),
        decimal_places=2,
        description="Warning threshold percentage (0-100)",
    )
    allow_project_admin_override: bool = Field(
        default=True,
        description="Whether project admins can override budget warnings",
    )
    enforce_budget: bool = Field(
        default=False,
        description="Whether to block cost registrations that exceed budget",
    )


class ProjectBudgetSettingsCreate(ProjectBudgetSettingsBase):
    """Properties for creating/updating Project Budget Settings."""

    # All fields are optional for upsert operations
    # Defaults will be used if not provided
    pass


class ProjectBudgetSettingsRead(ProjectBudgetSettingsBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_budget_settings_id: UUID
    project_id: UUID
    created_by: UUID


class BudgetWarning(BaseModel):
    """Budget warning information for cost registrations.

    Provides metadata about budget status without blocking operations.
    """

    exceeds_threshold: bool = Field(
        ..., description="Whether the cost exceeds the warning threshold"
    )
    threshold_percent: Decimal = Field(..., description="Warning threshold percentage")
    current_percent: Decimal = Field(..., description="Current budget usage percentage")
    message: str = Field(..., description="Human-readable warning message")


class BudgetExceededError(BaseModel):
    """Error returned when budget enforcement blocks a cost registration."""

    cost_element_id: UUID = Field(
        ..., description="Cost element that would exceed budget"
    )
    budget: Decimal = Field(..., description="Cost element budget amount")
    used: Decimal = Field(..., description="Current total spend on this cost element")
    projected: Decimal = Field(
        ..., description="Projected total after new registration"
    )
    over_by: Decimal = Field(..., description="Amount over budget")
    message: str = Field(..., description="Human-readable error message")
