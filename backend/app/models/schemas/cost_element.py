"""Pydantic schemas for Cost Element."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CostElementBase(BaseModel):
    """Shared properties for Cost Element."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    budget_amount: Decimal = Field(ge=0, decimal_places=2)
    description: str | None = None


class CostElementCreate(CostElementBase):
    """Properties required for creating a Cost Element."""

    wbe_id: UUID
    cost_element_type_id: UUID


class CostElementUpdate(BaseModel):
    """Properties that can be updated."""

    code: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=255)
    budget_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    description: str | None = None
    cost_element_type_id: UUID | None = None


class CostElementRead(CostElementBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cost_element_id: UUID
    wbe_id: UUID
    cost_element_type_id: UUID
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


class CostElementReadWithType(CostElementRead):
    """Cost Element with denormalized type information for convenience."""

    cost_element_type_code: str
    cost_element_type_name: str
    department_id: UUID  # Derived from type
    department_name: str  # Derived from type
