"""Pydantic schemas for Change Order API.

Source of truth for Change Order API contracts.
Frontend TypeScript types must match these schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas.common import PaginatedResponse


class ChangeOrderBase(BaseModel):
    """Base schema with common Change Order fields."""

    code: str = Field(
        ..., min_length=1, max_length=50, description="Business identifier (e.g., CO-2026-001)"
    )
    project_id: UUID = Field(..., description="Project this change applies to")
    title: str = Field(..., min_length=1, max_length=200, description="Brief title")
    description: str | None = Field(None, description="Detailed description")
    justification: str | None = Field(None, description="Business justification")
    effective_date: datetime | None = Field(None, description="When change takes effect")
    status: str = Field(default="Draft", description="Workflow state")


class ChangeOrderCreate(ChangeOrderBase):
    """Schema for creating a new Change Order."""

    # Removed strict=True to allow automatic string-to-UUID conversion from frontend
    # model_config = ConfigDict(strict=True)

    # change_order_id is auto-generated (UUID), not user-provided
    # effective_date can be provided for time-travel scenarios
    control_date: datetime | None = Field(
        None, description="Control date for bitemporal operations"
    )


class ChangeOrderUpdate(BaseModel):
    """Schema for updating a Change Order.

    All fields are optional to support partial updates.
    """

    # Removed strict=True to allow automatic string-to-UUID conversion from frontend
    # model_config = ConfigDict(strict=True)

    code: str | None = Field(None, min_length=1, max_length=50)
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    justification: str | None = None
    effective_date: datetime | None = None
    status: str | None = None
    control_date: datetime | None = Field(
        None, description="Control date for bitemporal operations"
    )


class ChangeOrderPublic(ChangeOrderBase):
    """Schema for Change Order API responses."""

    model_config = ConfigDict(from_attributes=True)

    change_order_id: UUID = Field(..., description="Root UUID identifier")
    id: UUID = Field(..., description="Version ID (primary key)")
    created_by: UUID = Field(..., description="User who created this version")
    created_at: datetime | None = Field(None, description="When this version was created (derived from transaction_time)")
    updated_by: UUID | None = Field(None, description="User who last updated")
    updated_at: datetime | None = Field(None, description="When last updated")
    branch: str = Field(..., description="Branch name")
    parent_id: UUID | None = Field(None, description="Parent version ID")
    deleted_at: datetime | None = Field(None, description="Soft delete timestamp")


# Response schemas for list endpoints
ChangeOrderListResponse = PaginatedResponse[ChangeOrderPublic]
