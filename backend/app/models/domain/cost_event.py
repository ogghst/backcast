"""Cost Event domain model - quality and cost event tracking.

Cost Events track quality events and cost impacts for projects.
They replace the old Work Package concept for quality/cost tracking.

Versionable but NOT branchable (events are global facts across branches).
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DECIMAL, DateTime, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

if TYPE_CHECKING:
    from app.models.domain.cost_event_type import CostEventType


class CostEvent(EntityBase, VersionableMixin):
    """Cost Event - quality and cost event tracking.

    Cost Events represent discrete events that impact project cost and schedule.
    They support Cost of Quality (COQ) tracking and categorization.

    Versionable but NOT branchable (events are global facts, not project-specific).

    Attributes:
        cost_event_id: Root ID for the Cost Event aggregation.
        project_id: Root ID of the parent project.
        wbs_element_id: WBS Element root ID where the event occurred (optional).
        name: Human-readable label for the event.
        cost_event_type_id: Root ID of the CostEventType category.
        description: Optional description of the event.
        status: Lifecycle state ('open' or 'closed').
        external_event_id: External reference identifier (e.g., QMS ID, PO number).
        event_date: When the event occurred.
        coq_category: Cost of Quality category (prevention, appraisal, internal_failure, external_failure).
        estimated_impact: Total estimated financial impact.
        schedule_impact_days: Days of schedule delay.

    Satisfies: VersionableProtocol
    """

    __tablename__ = "cost_events"

    # Root ID (stable identity across versions)
    cost_event_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Primary relationship -- project-scoped
    project_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # WBS Element association (optional)
    wbs_element_id: Mapped[UUID | None] = mapped_column(
        PG_UUID,
        nullable=True,
        index=True,
        # NOTE: No database-level ForeignKey constraint on root ID.
    )

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Event type
    cost_event_type_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because cost_event_type_id is a root ID.
    )

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", server_default="open"
    )

    # External reference identifier (e.g., QMS ID, PO number, work order)
    external_event_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )

    # When the event occurred
    event_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Cost of Quality category (nullable for non-quality event types)
    coq_category: Mapped[str | None] = mapped_column(
        String(30), nullable=True, default=None
    )

    # Financial impact (estimated)
    estimated_impact: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False,
        default=Decimal("0"),
    )

    # Schedule impact (nullable for non-quality event types)
    schedule_impact_days: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )

    # Relationships (view-only for navigation, no DB constraints)
    cost_event_type_ref: Mapped["CostEventType"] = relationship(
        "CostEventType",
        primaryjoin="CostEvent.cost_event_type_id == CostEventType.cost_event_type_id",
        foreign_keys=[cost_event_type_id],
        viewonly=True,
    )

    # Temporal fields inherited from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None
    # - created_by: UUID
    # - deleted_by: UUID | None

    # NOTE: Does NOT inherit BranchableMixin (no branch, parent_id, merge_from_branch)

    def __repr__(self) -> str:
        return (
            f"<CostEvent(id={self.id}, "
            f"cost_event_id={self.cost_event_id}, "
            f"name={self.name}, "
            f"project_id={self.project_id}, "
            f"status={self.status}, "
            f"estimated_impact={self.estimated_impact})>"
        )
