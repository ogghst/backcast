"""Budget Summary model and related schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import computed_field
from sqlalchemy import DECIMAL, Column, DateTime
from sqlmodel import Field, SQLModel


class BudgetSummaryBase(SQLModel):
    """Base budget summary schema with common fields."""

    level: str = Field(max_length=20)  # "project" or "wbe"
    revenue_limit: Decimal = Field(
        sa_column=Column(DECIMAL(15, 2), nullable=False)
    )  # contract_value or wbe.revenue_allocation
    total_revenue_allocated: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )  # sum of wbe.revenue_allocation or cost_element.revenue_plan
    total_budget_bac: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )  # sum of cost_element.budget_bac
    total_revenue_plan: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )  # sum of cost_element.revenue_plan

    @computed_field  # type: ignore[prop-decorator]
    @property
    def remaining_revenue(self) -> Decimal:
        """Calculate remaining revenue (revenue_limit - total_revenue_allocated)."""
        return self.revenue_limit - self.total_revenue_allocated

    @computed_field  # type: ignore[prop-decorator]
    @property
    def revenue_utilization_percent(self) -> float:
        """Calculate revenue utilization percentage."""
        if self.revenue_limit == Decimal("0.00"):
            return 0.0
        return float((self.total_revenue_allocated / self.revenue_limit) * 100)


class BudgetSummaryPublic(BudgetSummaryBase):
    """Public schema for budget summary response."""

    project_id: str | None = None  # UUID as string, present if level == "project"
    wbe_id: str | None = None  # UUID as string, present if level == "wbe"
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )
