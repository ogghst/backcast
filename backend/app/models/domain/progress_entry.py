"""Progress Entry domain model - tracking work completion percentage for cost elements.

Progress Entries track the percentage of work completed for cost elements over time.
They are versionable (NOT branchable) - progress is a global fact across all branches.
This allows change orders to compare branch budgets vs actual progress.
"""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

if TYPE_CHECKING:
    pass


class ProgressEntry(EntityBase, VersionableMixin):
    """Progress Entry - work completion tracking for cost elements.

    Progress Entries track the percentage of work completed for cost elements,
    enabling Earned Value Management (EVM) calculations.

    Versionable but NOT branchable (progress is global facts, not project-specific).
    This allows change orders to compare branch budgets vs actual progress.

    Attributes:
        progress_entry_id: Root ID for the Progress Entry aggregation.
        cost_element_id: Reference to the cost element being tracked.
        progress_percentage: Progress value (0.00 to 100.00).
        notes: Optional notes about progress (e.g., justification for decrease).

    Temporal fields (from VersionableMixin):
        valid_time: When progress was measured (business time).
        created_by: User who reported the progress.

    Examples:
        - Percentage: 50.00, Date: 2026-01-15, Notes: "Foundation complete"
        - Percentage: 75.00, Date: 2026-01-20, Notes: "Framing 50% complete"

    Satisfies: VersionableProtocol
    """

    __tablename__ = "progress_entries"

    # Root ID (stable identity across versions)
    progress_entry_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, index=True
    )

    # Foreign key to cost element
    cost_element_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("cost_elements.cost_element_id"),
        nullable=False,
        index=True,
    )

    # Progress percentage (decimal with 2 decimal places, range 0.00 to 100.00)
    progress_percentage: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2), nullable=False
    )



    # Optional notes (e.g., justification for progress decrease)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Temporal fields inherited from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None
    # - created_by: UUID
    # - deleted_by: UUID | None

    # NOTE: Does NOT inherit BranchableMixin (no branch, parent_id, merge_from_branch)

    def __repr__(self) -> str:
        return (
            f"<ProgressEntry(id={self.id}, "
            f"progress_entry_id={self.progress_entry_id}, "
            f"cost_element_id={self.cost_element_id}, "
            f"progress_percentage={self.progress_percentage})>"
        )
