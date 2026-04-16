"""Pydantic schemas for Cost Registration."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class CostRegistrationBase(BaseModel):
    """Shared properties for Cost Registration."""

    amount: Decimal = Field(
        ..., gt=0, decimal_places=2, description="Cost amount (must be positive)"
    )
    quantity: Decimal | None = Field(
        None,
        ge=0,
        decimal_places=2,
        description="Quantity of units consumed (optional)",
    )
    unit_of_measure: str | None = Field(
        None,
        max_length=50,
        description="Unit of measure (e.g., 'hours', 'kg', 'm', 'each')",
    )
    registration_date: datetime | None = Field(
        None,
        description="When the cost was incurred (defaults to control date if not provided)",
    )
    description: str | None = Field(
        None, description="Optional description of the cost"
    )
    invoice_number: str | None = Field(
        None, max_length=100, description="Optional invoice reference"
    )
    vendor_reference: str | None = Field(
        None, max_length=255, description="Optional vendor/supplier reference"
    )


class CostRegistrationCreate(CostRegistrationBase):
    """Properties required for creating a Cost Registration."""

    cost_registration_id: UUID | None = Field(
        None,
        description="Root Cost Registration ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )
    cost_element_id: UUID = Field(..., description="ID of the cost element to charge")
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class CostRegistrationUpdate(BaseModel):
    """Properties that can be updated on a Cost Registration."""

    amount: Decimal | None = Field(None, gt=0, decimal_places=2)
    quantity: Decimal | None = Field(None, ge=0, decimal_places=2)
    unit_of_measure: str | None = Field(None, max_length=50)
    registration_date: datetime | None = None
    description: str | None = None
    invoice_number: str | None = Field(None, max_length=100)
    vendor_reference: str | None = Field(None, max_length=255)
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class CostRegistrationRead(CostRegistrationBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cost_registration_id: UUID
    cost_element_id: UUID
    created_by: UUID

    @computed_field  # type: ignore[prop-decorator]
    @property
    def registration_date_formatted(self) -> dict[str, str | None]:
        """Display-ready registration date data.

        Returns pre-formatted date information including:
        - ISO timestamp for machine processing
        - Formatted display string for UI

        This allows the frontend to display dates without additional formatting.

        Example:
            {
                "iso": "2026-01-15T10:00:00+00:00",
                "formatted": "January 15, 2026"
            }
        """
        if not self.registration_date:
            return {"iso": None, "formatted": "Unknown"}

        return {
            "iso": self.registration_date.isoformat(),
            "formatted": self.registration_date.strftime("%B %d, %Y"),
        }
