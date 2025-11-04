"""Cost Summary model and related schemas."""
from datetime import datetime
from decimal import Decimal

from pydantic import computed_field
from sqlalchemy import DECIMAL, Column, DateTime
from sqlmodel import Field, SQLModel


class CostSummaryBase(SQLModel):
    """Base cost summary schema with common fields."""

    level: str = Field(max_length=20)  # "cost-element", "wbe", or "project"
    total_cost: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )  # Sum of cost_registration.amount
    budget_bac: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )  # Budget at Completion for computed fields (cost_element.budget_bac or sum)
    cost_registration_count: int = Field(
        default=0, ge=0
    )  # Number of cost registrations aggregated

    @computed_field
    @property
    def cost_percentage_of_budget(self) -> float:
        """Calculate cost percentage of budget (total_cost / budget_bac) * 100."""
        if self.budget_bac is None or self.budget_bac == Decimal("0.00"):
            return 0.0
        return float((self.total_cost / self.budget_bac) * 100)


class CostSummaryPublic(CostSummaryBase):
    """Public schema for cost summary response."""

    cost_element_id: str | None = (
        None  # UUID as string, present if level == "cost-element"
    )
    wbe_id: str | None = None  # UUID as string, present if level == "wbe"
    project_id: str | None = None  # UUID as string, present if level == "project"
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )
