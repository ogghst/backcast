"""Project Phase lookup model."""
import uuid

from sqlmodel import Field, SQLModel


class ProjectPhaseBase(SQLModel):
    """Base project phase schema with common fields."""

    phase_code: str = Field(unique=True, index=True, max_length=50)
    phase_name: str = Field(max_length=100)
    description: str | None = Field(default=None)
    display_order: int = Field(default=0)


class ProjectPhaseCreate(ProjectPhaseBase):
    """Schema for creating a new project phase."""

    pass


class ProjectPhaseUpdate(SQLModel):
    """Schema for updating a project phase."""

    phase_code: str | None = Field(default=None, max_length=50)
    phase_name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    display_order: int | None = None


class ProjectPhase(ProjectPhaseBase, table=True):
    """Project phase database model."""

    phase_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class ProjectPhasePublic(ProjectPhaseBase):
    """Public project phase schema for API responses."""

    phase_id: uuid.UUID
