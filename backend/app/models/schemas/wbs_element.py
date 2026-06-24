"""Pydantic schemas for WBS Element entity."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas.mixins import EntityMetadataMixin, TemporalComputedMixin
from app.models.schemas.temporal_validators import TemporalRange
from app.models.schemas.validators import NotEmptyString


class WBSElementBase(BaseModel):
    """Base schema for WBS Element with common fields."""

    project_id: UUID = Field(..., description="Parent project root ID")
    code: str = Field(..., max_length=50, description="WBS code (e.g., 1.2.3)")
    name: str = Field(..., max_length=255, description="WBS Element name")
    # NOTE: budget_allocation removed from input schemas
    # Budget is computed from child CostElement.amount values
    revenue_allocation: Decimal | None = Field(
        None, ge=0, description="Revenue allocation from project contract value"
    )
    level: int = Field(1, ge=1, description="Hierarchy level")
    parent_wbs_element_id: UUID | None = Field(
        None, description="Parent WBS Element root ID"
    )
    description: str | None = Field(None, max_length=5000, description="Description")


class WBSElementCreate(WBSElementBase):
    """Schema for creating a new WBS Element."""

    wbs_element_id: UUID | None = Field(
        None,
        description="Root WBS Element ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )
    branch: str = Field(
        "main",
        description="Branch name for creation (defaults to main if not specified)",
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class WBSElementUpdate(BaseModel):
    """Schema for updating an existing WBS Element."""

    name: NotEmptyString = Field(None, max_length=255)
    # NOTE: budget_allocation removed - budget is computed from cost elements
    revenue_allocation: Decimal | None = Field(None, ge=0)
    level: int | None = Field(None, ge=1)
    parent_wbs_element_id: UUID | None = None
    description: str | None = Field(None, max_length=5000)
    branch: str | None = Field(
        None, description="Branch name for update (defaults to current branch)"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class WBSElementRead(TemporalComputedMixin, EntityMetadataMixin, BaseModel):
    """Schema for reading WBS Element data."""

    id: UUID
    wbs_element_id: UUID
    project_id: UUID
    code: str
    name: str
    # NOTE: budget_allocation is computed from cost elements in the full hierarchy, not stored
    budget_allocation: Decimal = Field(
        Decimal(0),
        description="Computed budget (sum of cost element amounts in full hierarchy)",
    )
    revenue_allocation: Decimal | None = Field(
        None, ge=0, description="Revenue allocation from project contract value"
    )
    level: int
    parent_wbs_element_id: UUID | None = None
    description: str | None = None
    branch: str
    created_by: UUID
    parent_name: str | None = None
    deleted_by: UUID | None = None
    valid_time: TemporalRange = None
    transaction_time: TemporalRange = None

    model_config = ConfigDict(from_attributes=True)


# Breadcrumb schemas for hierarchical navigation
class ProjectBreadcrumbItem(BaseModel):
    """Minimal project info for breadcrumb."""

    id: UUID
    project_id: UUID
    code: str
    name: str


class WBSElementBreadcrumbItem(BaseModel):
    """Minimal WBS Element info for breadcrumb."""

    id: UUID
    wbs_element_id: UUID
    code: str
    name: str


class WBSElementBreadcrumb(BaseModel):
    """Breadcrumb trail for a WBS Element showing project and ancestor path."""

    project: ProjectBreadcrumbItem
    wbe_path: list[WBSElementBreadcrumbItem] = Field(
        ...,
        description="Ordered list of WBS Elements from root to current (last item is the current)",
    )


# Alias for backward compatibility
WBSElementPublic = WBSElementRead
