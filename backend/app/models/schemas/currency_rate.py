"""Pydantic schemas for CurrencyRate (non-versioned FX reference ledger)."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CurrencyRateBase(BaseModel):
    """Shared properties for CurrencyRate."""

    currency: str = Field(..., min_length=3, max_length=3, description="ISO-4217 code")
    rate_to_base: Decimal = Field(
        ..., description="1 unit of currency = rate_to_base base"
    )
    effective_date: date = Field(..., description="Date from which the rate is valid")


class CurrencyRateCreate(CurrencyRateBase):
    """Properties required for creating a CurrencyRate."""


class CurrencyRateUpdate(BaseModel):
    """Properties that can be updated."""

    rate_to_base: Decimal | None = None
    effective_date: date | None = None


class CurrencyRateRead(CurrencyRateBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
