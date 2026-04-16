"""Pydantic schemas for Cost Element."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.core.temporal import format_temporal_range_for_api


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


class CostElementUpdate(BaseModel):
    """Properties that can be updated."""

    code: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=255)
    budget_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    description: str | None = None
    cost_element_type_id: UUID | None = None
    branch: str | None = Field(
        None, description="Branch name for update (defaults to current branch)"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class CostElementRead(CostElementBase):
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


class CostElementReadWithType(CostElementRead):
    """Cost Element with denormalized type information for convenience."""

    cost_element_type_code: str
    cost_element_type_name: str
    department_id: UUID  # Derived from type
    department_name: str  # Derived from type
