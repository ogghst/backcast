"""Cost Element domain model - project-specific budget allocation.

Cost Elements are branchable and versionable, representing instances of Cost Element Types
within specific WBEs where budgets are allocated and costs are tracked.
"""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DECIMAL, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import EntityBase
from app.models.mixins import BranchableMixin, VersionableMixin

if TYPE_CHECKING:
    from app.models.domain.cost_element_type import CostElementType
    from app.models.domain.wbe import WBE


class CostElement(EntityBase, VersionableMixin, BranchableMixin):
    """Cost Element - project-specific instance of a Cost Element Type.

    Cost Elements are the leaf level of the project hierarchy where:
    - Budgets are allocated
    - Actual costs are tracked
    - Earned value is calculated

    Branchable (supports change orders) and Versionable (tracks changes).

    Attributes:
        cost_element_id: Root ID for the Cost Element aggregation.
        wbe_id: Parent WBE root ID.
        cost_element_type_id: Reference to standardized cost type.
        code: Project-specific code (e.g., "001", "LAB-PHASE1").
        name: Display name (can be instance-specific, e.g., "Phase 1 Mechanical").
        budget_amount: Allocated budget for this cost element.
        description: Optional description.

    Note: Department is DERIVED from Cost Element Type, not stored here.

    Examples:
        - WBE: "1.2 - Site Preparation"
          └── Cost Element: "MECH-001" (Type: "Mechanical Installation", Budget: $50,000)
        - WBE: "2.1 - Software Module A"
          └── Cost Element: "SW-DEV-001" (Type: "Software Development", Budget: $120,000)

    Satisfies: BranchableProtocol, VersionableProtocol
    """

    __tablename__ = "cost_elements"

    # Root ID
    cost_element_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Parent relationships
    wbe_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because wbe_id is a root ID
        # that is not unique across versions. Integrity is enforced at application level.
    )
    cost_element_type_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because cost_element_type_id is
        # a root ID that is not unique across versions. Integrity is enforced at application level.
    )

    # Identity
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Financial
    budget_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2), default=0, nullable=False
    )

    # Schedule Baseline (1:1 relationship per version)
    # NOTE: No FK constraint defined because schedule_baseline_id is not unique across
    # version rows in the bitemporal schedule_baselines table.
    # PREVIOUSLY: Referential integrity was enforced by uq_cost_elements_schedule_baseline_id.
    # NOW: This unique constraint was removed to allow multiple CostElement versions to
    # share the same ScheduleBaseline root ID (stable identity).
    schedule_baseline_id: Mapped[UUID | None] = mapped_column(
        PG_UUID,
        nullable=True,
        index=True,
        comment="Reference to the single schedule baseline for this cost element",
    )

    # Forecast (1:1 relationship per version)
    # NOTE: No FK constraint defined because forecast_id is not unique across
    # version rows in the bitemporal forecasts table.
    # PREVIOUSLY: Referential integrity was enforced by uq_cost_elements_forecast_id.
    # NOW: This unique constraint was removed to allow multiple CostElement versions to
    # share the same Forecast root ID (stable identity).
    forecast_id: Mapped[UUID | None] = mapped_column(
        PG_UUID,
        nullable=True,
        index=True,
        comment="Reference to the single forecast for this cost element",
    )

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Mixins provide:
    # - valid_time, transaction_time, deleted_at, created_by, deleted_by (VersionableMixin)
    # - branch, parent_id, merge_from_branch (BranchableMixin)

    # Relationships (View-only for navigation, no DB constraints)
    wbe: Mapped["WBE"] = relationship(
        "WBE",
        primaryjoin="CostElement.wbe_id == WBE.wbe_id",
        foreign_keys=[wbe_id],
        viewonly=True,
    )
    cost_element_type: Mapped["CostElementType"] = relationship(
        "CostElementType",
        primaryjoin="CostElement.cost_element_type_id == CostElementType.cost_element_type_id",
        foreign_keys=[cost_element_type_id],
        viewonly=True,
    )

    def __repr__(self) -> str:
        return (
            f"<CostElement(id={self.id}, cost_element_id={self.cost_element_id}, "
            f"wbe_id={self.wbe_id}, code={self.code}, name={self.name})>"
        )
