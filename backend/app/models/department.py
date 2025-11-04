"""Department lookup model."""
import uuid

from sqlmodel import Field, SQLModel


class DepartmentBase(SQLModel):
    """Base department schema with common fields."""

    department_code: str = Field(unique=True, index=True, max_length=20)
    department_name: str = Field(max_length=100)
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)


class DepartmentCreate(DepartmentBase):
    """Schema for creating a new department."""

    pass


class DepartmentUpdate(SQLModel):
    """Schema for updating a department."""

    department_code: str | None = Field(default=None, max_length=20)
    department_name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class Department(DepartmentBase, table=True):
    """Department database model."""

    department_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class DepartmentPublic(DepartmentBase):
    """Public department schema for API responses."""

    department_id: uuid.UUID
