"""Pydantic schemas for WBE entity."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.core.temporal import format_temporal_range_for_api


class WBEBase(BaseModel):
    """Base schema for WBE with common fields."""

    project_id: UUID = Field(..., description="Parent project root ID")
    code: str = Field(..., max_length=50, description="WBS code (e.g., 1.2.3)")
    name: str = Field(..., max_length=255, description="WBE name")
    # NOTE: budget_allocation removed from input schemas
    # Budget is now computed from child CostElement.budget_amount values
    revenue_allocation: Decimal | None = Field(
        None, ge=0, description="Revenue allocation from project contract value"
    )
    level: int = Field(1, ge=1, description="Hierarchy level")
    parent_wbe_id: UUID | None = Field(None, description="Parent WBE root ID")
    description: str | None = Field(None, max_length=5000, description="Description")


class WBECreate(WBEBase):
    """Schema for creating a new WBE."""

    wbe_id: UUID | None = Field(
        None,
        description="Root WBE ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )
    branch: str = Field(
        "main",
        description="Branch name for creation (defaults to main if not specified)",
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class WBEUpdate(BaseModel):
    """Schema for updating an existing WBE."""

    name: str | None = Field(None, max_length=255)
    # NOTE: budget_allocation removed - budget is computed from cost elements
    revenue_allocation: Decimal | None = Field(None, ge=0)
    level: int | None = Field(None, ge=1)
    parent_wbe_id: UUID | None = None
    description: str | None = Field(None, max_length=5000)
    branch: str | None = Field(
        None, description="Branch name for update (defaults to current branch)"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class WBERead(BaseModel):
    """Schema for reading WBE data."""

    id: UUID
    wbe_id: UUID
    project_id: UUID
    code: str
    name: str
    # NOTE: budget_allocation is computed from cost elements in the full hierarchy, not stored
    budget_allocation: Decimal = Field(
        Decimal(0),
        description="Computed budget (sum of cost element budgets in full WBE hierarchy)",
    )
    revenue_allocation: Decimal | None = Field(
        None, ge=0, description="Revenue allocation from project contract value"
    )
    level: int
    parent_wbe_id: UUID | None = None
    description: str | None = None
    branch: str
    created_at: datetime | None = None
    created_by: UUID
    created_by_name: str | None = None
    parent_name: str | None = None
    deleted_by: UUID | None = None
    valid_time: str | None = None
    transaction_time: str | None = None

    @field_validator("valid_time", "transaction_time", mode="before")
    @classmethod
    def convert_range_to_str(cls, v: object) -> str | None:
        if v and not isinstance(v, str):
            return str(v)
        return v  # type: ignore

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valid_time_formatted(self) -> dict[str, str | bool | None]:
        """Display-ready valid_time temporal data.

        Returns pre-formatted temporal range information including:
        - ISO timestamps for machine processing
        - Formatted display strings for UI
        - Validity status

        This allows the frontend to display dates without parsing
        PostgreSQL range syntax.

        Example:
            {
                "lower": "2026-01-15T10:00:00+00:00",
                "upper": null,
                "lower_formatted": "January 15, 2026",
                "upper_formatted": "Present",
                "is_currently_valid": true
            }
        """
        return format_temporal_range_for_api(self.valid_time)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def transaction_time_formatted(self) -> dict[str, str | bool | None]:
        """Display-ready transaction_time temporal data.

        Returns pre-formatted temporal range information for the
        transaction time (when this version was created in the system).

        See valid_time_formatted for response format details.
        """
        return format_temporal_range_for_api(self.transaction_time)

    model_config = ConfigDict(from_attributes=True)


# Breadcrumb schemas for hierarchical navigation
class ProjectBreadcrumbItem(BaseModel):
    """Minimal project info for breadcrumb."""

    id: UUID
    project_id: UUID
    code: str
    name: str


class WBEBreadcrumbItem(BaseModel):
    """Minimal WBE info for breadcrumb."""

    id: UUID
    wbe_id: UUID
    code: str
    name: str


class WBEBreadcrumb(BaseModel):
    """Breadcrumb trail for a WBE showing project and ancestor path."""

    project: ProjectBreadcrumbItem
    wbe_path: list[WBEBreadcrumbItem] = Field(
        ...,
        description="Ordered list of WBEs from root to current (last item is the current WBE)",
    )


# Alias for backward compatibility
WBEPublic = WBERead
