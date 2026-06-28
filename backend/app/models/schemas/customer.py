"""Pydantic schemas for Customer (non-versioned reference data)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    """Shared properties for Customer."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_active: bool = True


class CustomerCreate(CustomerBase):
    """Properties required for creating a Customer."""


class CustomerUpdate(BaseModel):
    """Properties that can be updated."""

    code: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class CustomerRead(CustomerBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
