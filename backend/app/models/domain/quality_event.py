"""Quality Event domain model - track rework costs and quality issues.

Quality Events track rework costs and quality issues against cost elements.
They are versionable (NOT branchable) - quality events are global facts.
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


class QualityEvent(EntityBase, VersionableMixin):
    """Quality Event - tracking rework costs and quality issues.

    Quality Events track the cost impact of quality problems (defects, rework,
    scrap, warranty claims) against cost elements. This enables project managers
    to track and analyze quality-related costs separately from normal cost registrations.

    Versionable but NOT branchable (quality events are global facts, not project-specific).
    This allows change orders to compare branch budgets vs global quality events.

    Attributes:
        quality_event_id: Root ID for the Quality Event aggregation.
        cost_element_id: Reference to the cost element being charged for the rework.
        description: Description of the quality issue or event.
        cost_impact: Financial impact of the quality event (positive = additional cost).
        event_date: When the quality event occurred (business date, defaults to control date).
        event_type: Category of quality event (defect, rework, scrap, warranty, other).
        severity: Impact level of the quality event (low, medium, high, critical).
        root_cause: Optional root cause analysis of the quality issue.
        resolution_notes: Optional description of how the issue was resolved.

    Examples:
        - Defect in welding: $500 rework cost, severity: high
        - Scrap material: $1200 waste cost, severity: medium
        - Warranty claim: $3000 replacement cost, severity: critical

    Satisfies: VersionableProtocol
    """

    __tablename__ = "quality_events"

    # Root ID (stable identity across versions)
    quality_event_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Foreign key to cost element (application-level integrity, no DB FK)
    cost_element_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint on root ID.
    )

    # Description of the quality issue (required)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Financial impact of the quality event (decimal with 2 precision for currency)
    cost_impact: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False
    )

    # Business date when the quality event occurred (optional, defaults to control date)
    event_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Category of quality event
    event_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Impact severity level
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Optional root cause analysis
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional resolution description
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Temporal fields inherited from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None
    # - created_by: UUID
    # - deleted_by: UUID | None

    # NOTE: Does NOT inherit BranchableMixin (no branch, parent_id, merge_from_branch)

    def __repr__(self) -> str:
        return (
            f"<QualityEvent(id={self.id}, "
            f"quality_event_id={self.quality_event_id}, "
            f"cost_element_id={self.cost_element_id}, "
            f"cost_impact={self.cost_impact}, "
            f"event_type={self.event_type}, "
            f"severity={self.severity}, "
            f"event_date={self.event_date})>"
        )
