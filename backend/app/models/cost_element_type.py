"""Cost Element Type lookup model."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class CostElementTypeBase(SQLModel):
    """Base cost element type schema with common fields."""

    type_code: str = Field(unique=True, index=True, max_length=50)
    type_name: str = Field(max_length=200)
    category_type: str = Field(
        max_length=50
    )  # Will be validated as enum in application logic
    tracks_hours: bool = Field(default=False)
    description: str | None = Field(default=None)
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class CostElementTypeCreate(CostElementTypeBase):
    """Schema for creating a new cost element type."""

    pass


class CostElementTypeUpdate(SQLModel):
    """Schema for updating a cost element type."""

    type_code: str | None = Field(default=None, max_length=50)
    type_name: str | None = Field(default=None, max_length=200)
    category_type: str | None = Field(default=None, max_length=50)
    tracks_hours: bool | None = None
    description: str | None = None
    display_order: int | None = None
    is_active: bool | None = None


class CostElementType(CostElementTypeBase, table=True):
    """Cost element type database model."""

    cost_element_type_id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True))
    )


class CostElementTypePublic(CostElementTypeBase):
    """Public cost element type schema for API responses."""

    cost_element_type_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
