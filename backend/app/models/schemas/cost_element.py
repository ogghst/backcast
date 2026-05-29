"""Pydantic schemas for Cost Element entity (EOC under Work Package)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas.mixins import TemporalComputedMixin
from app.models.schemas.temporal_validators import TemporalRange


class CostElementBase(BaseModel):
    """Base schema for Cost Element."""

    cost_element_type_id: UUID = Field(
        ..., description="Reference to standardized cost type"
    )
    amount: Decimal = Field(
        Decimal("0"), ge=0, decimal_places=2, description="Allocated amount"
    )
    description: str | None = None


class CostElementCreate(CostElementBase):
    """Schema for creating a new Cost Element."""

    cost_element_id: UUID | None = Field(
        None,
        description="Root Cost Element ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )
    work_package_id: UUID = Field(..., description="Parent Work Package root ID")
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class CostElementUpdate(BaseModel):
    """Schema for updating an existing Cost Element."""

    cost_element_type_id: UUID | None = None
    amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    description: str | None = None
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class CostElementRead(CostElementBase, TemporalComputedMixin):
    """Schema for reading Cost Element data."""

    id: UUID
    cost_element_id: UUID
    work_package_id: UUID
    created_by: UUID
    created_by_name: str | None = None
    deleted_by: UUID | None = None
    valid_time: TemporalRange = None
    transaction_time: TemporalRange = None
    # Denormalized names for convenience
    work_package_name: str | None = None
    work_package_code: str | None = None
    cost_element_type_name: str | None = None
    cost_element_type_code: str | None = None
    project_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class CostElementReadWithType(CostElementRead):
    """Cost Element with denormalized type information for convenience."""

    cost_element_type_code: str
    cost_element_type_name: str
    organizational_unit_id: UUID  # Derived from type
    organizational_unit_name: str  # Derived from type
