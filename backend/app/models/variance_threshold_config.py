"""Variance Threshold Configuration model."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import field_validator
from sqlalchemy import DECIMAL, CheckConstraint, Column, DateTime, Index, text
from sqlmodel import Field, SQLModel


class VarianceThresholdType(str, Enum):
    """Variance threshold type enumeration."""

    critical_cv = "critical_cv"
    warning_cv = "warning_cv"
    critical_sv = "critical_sv"
    warning_sv = "warning_sv"


# Shared properties
class VarianceThresholdConfigBase(SQLModel):
    """Base variance threshold configuration schema with common fields."""

    threshold_type: VarianceThresholdType
    threshold_percentage: Decimal = Field(
        sa_column=Column(DECIMAL(5, 2), nullable=False),
        description="Threshold percentage (-100 to 0)",
    )
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)

    @field_validator("threshold_percentage")
    @classmethod
    def validate_threshold_percentage(cls, v: Decimal) -> Decimal:
        """Validate that threshold_percentage is between -100 and 0."""
        if v > 0:
            raise ValueError("threshold_percentage must be negative or zero")
        if v < -100:
            raise ValueError("threshold_percentage must be >= -100")
        return v


# Properties to receive via API on creation
class VarianceThresholdConfigCreate(VarianceThresholdConfigBase):
    """Schema for creating a new variance threshold configuration."""

    pass


# Properties to receive via API on update, all are optional
class VarianceThresholdConfigUpdate(SQLModel):
    """Schema for updating a variance threshold configuration."""

    threshold_type: VarianceThresholdType | None = None
    threshold_percentage: Decimal | None = Field(
        default=None,
        sa_column=Column(DECIMAL(5, 2), nullable=True),
        description="Threshold percentage (-100 to 0)",
    )
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class VarianceThresholdConfig(VarianceThresholdConfigBase, table=True):
    """Variance threshold configuration database model."""

    __tablename__ = "variance_threshold_config"

    variance_threshold_config_id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True))
    )

    __table_args__ = (
        # Partial unique index: only one active threshold per type
        # This ensures that for each threshold_type, only one row with is_active=True can exist
        Index(
            "ix_variance_threshold_config_type_active_unique",
            "threshold_type",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
        # Check constraint: threshold_percentage must be between -100 and 0
        CheckConstraint(
            "threshold_percentage >= -100 AND threshold_percentage <= 0",
            name="ck_variance_threshold_config_percentage_range",
        ),
    )


class VarianceThresholdConfigPublic(VarianceThresholdConfigBase):
    """Public variance threshold configuration schema for API responses."""

    variance_threshold_config_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class VarianceThresholdConfigsPublic(SQLModel):
    """Schema for list of variance threshold configurations."""

    data: list[VarianceThresholdConfigPublic]
    count: int
