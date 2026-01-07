"""Pydantic schemas for Cost Element Type."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CostElementTypeBase(BaseModel):
    """Shared properties for Cost Element Type."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class CostElementTypeCreate(CostElementTypeBase):
    """Properties required for creating a Cost Element Type."""

    department_id: UUID


class CostElementTypeUpdate(BaseModel):
    """Properties that can be updated."""

    code: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    department_id: UUID | None = None


class CostElementTypeRead(CostElementTypeBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cost_element_type_id: UUID
    department_id: UUID
    created_by: UUID
