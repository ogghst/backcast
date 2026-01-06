from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


class DepartmentBase(BaseModel):
    name: str = Field(..., max_length=255, description="Department display name")
    manager_id: UUID | None = Field(None, description="UUID of the department manager")
    is_active: bool = Field(True, description="Whether the department is active")
    description: str | None = Field(None, max_length=5000, description="Department description")


class DepartmentCreate(DepartmentBase):
    code: str = Field(
        ...,
        max_length=50,
        pattern="^[A-Z0-9_-]+$",
        description="Unique department code (immutable)",
    )


class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    code: str | None = Field(None, max_length=50, pattern="^[A-Z0-9_-]+$")
    manager_id: UUID | None = None
    is_active: bool | None = None
    description: str | None = Field(None, max_length=5000)


class DepartmentRead(DepartmentBase):
    """Schema for reading department data."""

    id: UUID
    department_id: UUID
    code: str
    is_active: bool
    created_at: datetime | None = None  # For temporal compatibility
    created_by: UUID
    created_by_name: str | None = None
    deleted_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
DepartmentPublic = DepartmentRead
