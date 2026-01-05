"""Pydantic schemas for WBE entity."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WBEBase(BaseModel):
    """Base schema for WBE with common fields."""

    project_id: UUID = Field(..., description="Parent project root ID")
    code: str = Field(..., max_length=50, description="WBS code (e.g., 1.2.3)")
    name: str = Field(..., max_length=255, description="WBE name")
    budget_allocation: Decimal = Field(0, ge=0, description="Budget allocation")
    level: int = Field(1, ge=1, description="Hierarchy level")
    parent_wbe_id: UUID | None = Field(None, description="Parent WBE root ID")
    description: str | None = Field(None, max_length=5000, description="Description")


class WBECreate(WBEBase):
    """Schema for creating a new WBE."""

    pass


class WBEUpdate(BaseModel):
    """Schema for updating an existing WBE."""

    name: str | None = Field(None, max_length=255)
    budget_allocation: Decimal | None = Field(None, ge=0)
    level: int | None = Field(None, ge=1)
    parent_wbe_id: UUID | None = None
    description: str | None = Field(None, max_length=5000)


class WBERead(WBEBase):
    """Schema for reading WBE data."""

    id: UUID
    wbe_id: UUID
    branch: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
WBEPublic = WBERead
