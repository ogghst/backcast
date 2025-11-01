"""Audit Log model and related schemas."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

# Import for forward references
from app.models.user import User


class AuditLogBase(SQLModel):
    """Base audit log schema with common fields."""

    entity_type: str = Field(max_length=50)
    entity_id: uuid.UUID
    action: str = Field(max_length=50)  # Will be validated as enum in application logic
    field_name: str | None = Field(default=None, max_length=100)
    old_value: str | None = Field(default=None)
    new_value: str | None = Field(default=None)
    reason: str | None = Field(default=None)
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=500)


class AuditLogCreate(AuditLogBase):
    """Schema for creating a new audit log entry."""

    user_id: uuid.UUID


class AuditLogUpdate(SQLModel):
    """Schema for updating an audit log entry (rarely used)."""

    entity_type: str | None = Field(default=None, max_length=50)
    entity_id: uuid.UUID | None = None
    action: str | None = Field(default=None, max_length=50)
    field_name: str | None = Field(default=None, max_length=100)
    old_value: str | None = None
    new_value: str | None = None
    reason: str | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=500)


class AuditLog(AuditLogBase, table=True):
    """Audit Log database model."""

    audit_log_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)

    # Relationships
    user: User | None = Relationship()

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class AuditLogPublic(AuditLogBase):
    """Public audit log schema for API responses."""

    audit_log_id: uuid.UUID
    user_id: uuid.UUID
    timestamp: datetime
