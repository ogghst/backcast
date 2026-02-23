"""Cost Registration domain model - actual cost tracking against cost elements.

Cost Registrations track actual expenditures against cost elements with bitemporal versioning.
They are versionable (NOT branchable) - costs are global facts across all branches.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

if TYPE_CHECKING:
    pass


class CostRegistration(EntityBase, VersionableMixin):
    """Cost Registration - actual cost incurred against a cost element.

    Cost Registrations track actual expenditures for EVM (Earned Value Management).
    They represent single cost entries against cost elements.

    Versionable but NOT branchable (costs are global facts, not project-specific).
    This allows change orders to compare branch budgets vs global actual costs.

    Attributes:
        cost_registration_id: Root ID for the Cost Registration aggregation.
        cost_element_id: Reference to the cost element being charged.
        amount: The cost amount (decimal with 2 precision).
        quantity: Optional quantity of units consumed (e.g., labor hours, material quantity).
        unit_of_measure: Optional unit type (e.g., "hours", "kg", "m", "each").
        registration_date: When the cost was incurred (business date, defaults to control date).
        description: Optional description of the cost.
        invoice_number: Optional invoice reference.
        vendor_reference: Optional vendor/supplier reference.

    Examples:
        - Amount: $1500.00, Quantity: 10.0, Unit: "hours", Date: 2026-01-15
        - Amount: $850.00, Quantity: 5.0, Unit: "each", Date: 2026-01-16

    Satisfies: VersionableProtocol
    """

    __tablename__ = "cost_registrations"

    # Root ID (stable identity across versions)
    cost_registration_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, index=True
    )

    # Foreign key to cost element
    cost_element_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint on root ID.
    )

    # Cost amount (decimal with 2 decimal places for currency)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False
    )

    # Optional quantity of units consumed
    quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=15, scale=2), nullable=True
    )

    # Optional unit of measure (e.g., "hours", "kg", "m", "each")
    unit_of_measure: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Business date when cost was incurred (optional, defaults to control date)
    registration_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Optional fields
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vendor_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Temporal fields inherited from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None
    # - created_by: UUID
    # - deleted_by: UUID | None

    # NOTE: Does NOT inherit BranchableMixin (no branch, parent_id, merge_from_branch)

    def __repr__(self) -> str:
        return (
            f"<CostRegistration(id={self.id}, "
            f"cost_registration_id={self.cost_registration_id}, "
            f"cost_element_id={self.cost_element_id}, "
            f"amount={self.amount}, "
            f"quantity={self.quantity}, "
            f"unit_of_measure={self.unit_of_measure}, "
            f"registration_date={self.registration_date})>"
        )
