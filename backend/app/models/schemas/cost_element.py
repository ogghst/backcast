"""Pydantic schemas for Cost Element."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas.mixins import TemporalComputedMixin
from app.models.schemas.temporal_validators import TemporalRange
from app.models.schemas.validators import NotEmptyString


class CostElementBase(BaseModel):
    """Shared properties for Cost Element."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    budget_amount: Decimal = Field(decimal_places=2)
    description: str | None = None


class CostElementCreate(CostElementBase):
    """Properties required for creating a Cost Element."""

    cost_element_id: UUID | None = Field(
        None,
        description="Root Cost Element ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )
    wbe_id: UUID
    cost_element_type_id: UUID
    branch: str = Field(
        ...,  # Required field - no default
        description="Branch name for entity creation",
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )
    schedule_start_date: datetime | None = Field(
        None, description="Optional start date for the auto-created schedule baseline"
    )
    schedule_end_date: datetime | None = Field(
        None, description="Optional end date for the auto-created schedule baseline"
    )
    schedule_progression_type: str | None = Field(
        None,
        description="Optional progression type for the schedule (LINEAR, GAUSSIAN, LOGARITHMIC)",
    )


class CostElementUpdate(BaseModel):
    """Properties that can be updated."""

    code: NotEmptyString = Field(None, min_length=1, max_length=50)
    name: NotEmptyString = Field(None, min_length=1, max_length=255)
    budget_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    description: str | None = None
    cost_element_type_id: UUID | None = None
    branch: str | None = Field(
        None, description="Branch name for update (defaults to current branch)"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class CostElementRead(CostElementBase, TemporalComputedMixin):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cost_element_id: UUID
    wbe_id: UUID
    wbe_name: str | None = None
    cost_element_type_id: UUID
    cost_element_type_name: str | None = None
    cost_element_type_code: str | None = None
    branch: str
    created_by: UUID
    valid_time: TemporalRange = None
    transaction_time: TemporalRange = None


class CostElementReadWithType(CostElementRead):
    """Cost Element with denormalized type information for convenience."""

    cost_element_type_code: str
    cost_element_type_name: str
    department_id: UUID  # Derived from type
    department_name: str  # Derived from type
