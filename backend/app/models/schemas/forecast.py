"""Pydantic schemas for Forecast."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ForecastBase(BaseModel):
    """Shared properties for Forecast."""

    eac_amount: Decimal = Field(
        ..., ge=0, decimal_places=2, description="Estimate at Complete"
    )
    basis_of_estimate: str = Field(
        ..., min_length=1, max_length=5000, description="Basis for the estimate"
    )


class ForecastCreate(ForecastBase):
    """Properties required for creating a Forecast."""

    cost_element_id: UUID = Field(..., description="Parent Cost Element ID")
    forecast_id: UUID | None = Field(
        None,
        description="Root Forecast ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )
    branch: str = Field(
        "main",
        description="Branch name for creation (defaults to main if not specified)",
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class ForecastUpdate(BaseModel):
    """Properties that can be updated."""

    eac_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    basis_of_estimate: str | None = Field(None, min_length=1, max_length=5000)
    approved_date: datetime | None = None
    approved_by: UUID | None = None
    branch: str | None = Field(
        None, description="Branch name for update (defaults to current branch)"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class ForecastRead(ForecastBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    forecast_id: UUID
    cost_element_id: UUID
    branch: str
    created_by: UUID
    approved_date: datetime | None = None
    approved_by: UUID | None = None
    valid_time: str | None = None
    transaction_time: str | None = None

    @field_validator("valid_time", "transaction_time", mode="before")
    @classmethod
    def convert_range_to_str(cls, v: object) -> str | None:
        if v and not isinstance(v, str):
            return str(v)
        return v  # type: ignore


class ForecastComparison(BaseModel):
    """EVM comparison metrics for a forecast.

    Provides:
    - VAC (Variance at Complete): BAC - EAC
    - ETC (Estimate to Complete): EAC - AC
    """

    model_config = ConfigDict(from_attributes=True)

    forecast_id: UUID
    cost_element_id: UUID
    bac_amount: Decimal = Field(
        ..., description="Budget at Complete (from CostElement)"
    )
    eac_amount: Decimal = Field(..., description="Estimate at Complete")
    ac_amount: Decimal = Field(
        ..., description="Actual Cost (sum of CostRegistrations)"
    )
    vac_amount: Decimal = Field(..., description="Variance at Complete (BAC - EAC)")
    etc_amount: Decimal = Field(..., description="Estimate to Complete (EAC - AC)")
