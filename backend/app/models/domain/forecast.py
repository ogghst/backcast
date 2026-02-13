"""Forecast domain model - Estimate at Complete (EAC) tracking.

Forecasts track projected total costs for cost elements with full versioning + branching.
They enable "What-if" scenarios for Change Orders.

Key EVM Concepts:
- EAC (Estimate at Complete): Projected total cost
- BAC (Budget at Complete): Original budget (from CostElement)
- VAC (Variance at Complete): VAC = BAC - EAC (positive = under budget)
- ETC (Estimate to Complete): ETC = EAC - AC (remaining work)
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import BranchableMixin, VersionableMixin

if TYPE_CHECKING:
    pass


class Forecast(EntityBase, VersionableMixin, BranchableMixin):
    """Forecast - Estimate at Complete for a Cost Element.

    Forecasts represent the projected total cost for completing a cost element.
    They are branchable to enable "What-if" scenarios during Change Order evaluation.

    Attributes:
        forecast_id: Root ID for the Forecast aggregation.
        eac_amount: Estimate at Complete - projected total cost (decimal with 2 precision).
        basis_of_estimate: Explanation of how the EAC was calculated.
        approved_date: When this forecast was officially approved (optional).
        approved_by: User who approved this forecast (optional).

    Examples:
        - EAC: $95000.00 (original budget was $100000, now under budget)
        - EAC: $120000.00 (cost overruns expected)

    Satisfies: BranchableProtocol
    """

    __tablename__ = "forecasts"

    # Root ID (stable identity across versions)
    forecast_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Estimate at Complete (decimal with 2 decimal places for currency)
    eac_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False
    )

    # Basis for the estimate (required)
    basis_of_estimate: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional approval fields
    approved_date: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    approved_by: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True)

    # Temporal fields inherited from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None
    # - created_by: UUID
    # - deleted_by: UUID | None

    # Branching fields inherited from BranchableMixin:
    # - branch: str (default "main")
    # - parent_id: UUID | None
    # - merge_from_branch: str | None

    def __repr__(self) -> str:
        return (
            f"<Forecast(id={self.id}, "
            f"forecast_id={self.forecast_id}, "
            f"eac_amount={self.eac_amount}, "
            f"branch={self.branch})>"
        )
