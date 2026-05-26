"""Pydantic schemas for Package Type."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PackageTypeBase(BaseModel):
    """Shared properties for Package Type."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    color: str = Field("blue", max_length=30)
    is_quality: bool = Field(
        False, description="Whether this type contributes to COQ metrics"
    )
    description: str | None = None


class PackageTypeCreate(PackageTypeBase):
    """Properties required for creating a Package Type."""

    package_type_id: UUID | None = Field(
        None,
        description="Root Package Type ID (internal use only for seeding)",
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class PackageTypeUpdate(BaseModel):
    """Properties that can be updated."""

    code: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=255)
    color: str | None = Field(None, max_length=30)
    is_quality: bool | None = None
    description: str | None = None


class PackageTypeRead(PackageTypeBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    package_type_id: UUID
    created_by: UUID
