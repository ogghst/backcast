"""App Configuration model for storing default AI settings."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, UniqueConstraint
from sqlmodel import Field, SQLModel


# Shared properties
class AppConfigurationBase(SQLModel):
    """Base app configuration schema with common fields."""

    config_key: str = Field(
        unique=True,
        index=True,
        max_length=200,
        description="Configuration key (e.g., 'ai_default_openai_base_url')",
    )
    config_value: str = Field(
        description="Configuration value (plain text or encrypted)"
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional description of the configuration",
    )
    is_active: bool = Field(
        default=True, description="Whether this configuration is active"
    )


# Properties to receive via API on creation
class AppConfigurationCreate(AppConfigurationBase):
    """Schema for creating a new app configuration."""

    pass


# Properties to receive via API on update, all are optional
class AppConfigurationUpdate(SQLModel):
    """Schema for updating an app configuration."""

    config_key: str | None = Field(default=None, max_length=200)
    config_value: str | None = None
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class AppConfiguration(AppConfigurationBase, table=True):
    """App configuration database model."""

    __tablename__ = "app_configuration"

    config_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True))
    )

    __table_args__ = (
        # Unique constraint on config_key to ensure no duplicates
        UniqueConstraint("config_key", name="uq_app_configuration_config_key"),
        # Index on config_key for faster lookups (already covered by unique=True in Field)
        # but explicit index helps with query performance
        Index("ix_app_configuration_config_key", "config_key"),
    )


class AppConfigurationPublic(AppConfigurationBase):
    """Public app configuration schema for API responses."""

    config_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class AppConfigurationsPublic(SQLModel):
    """Schema for list of app configurations."""

    data: list[AppConfigurationPublic]
    count: int
