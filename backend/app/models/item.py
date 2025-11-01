"""Item model and related schemas."""
import uuid

from sqlmodel import Field, Relationship, SQLModel

# Import User for forward reference
from app.models.user import User


# Shared properties
class ItemBase(SQLModel):
    """Base item schema with common fields."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    """Schema for creating a new item."""

    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    """Schema for updating an item."""

    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    """Item database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    """Public item schema for API responses."""

    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    """Schema for list of items."""

    data: list[ItemPublic]
    count: int
