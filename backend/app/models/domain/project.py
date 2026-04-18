"""Project domain model - branchable versioned entity.

Projects support branching for change order workflows.
Satisfies BranchableProtocol via structural subtyping.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DECIMAL, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import BranchableMixin, VersionableMixin


class Project(EntityBase, VersionableMixin, BranchableMixin):
    """Project entity with full EVCS capabilities (Versioning + Branching).

    Attributes:
        project_id: Root ID for the project aggregation.
        name: Project name.
        code: Unique project code.
        description: Optional description.
        budget: Computed budget (sum of all cost element budgets in the project).
            Not stored in database; computed on-the-fly by ProjectService.
        contract_value: Contract value (if different from budget).
        start_date: Project start date.
        end_date: Project end date.

    Note: Budget is computed from CostElement.budget_amount values across all
    WBEs in the project. The service layer populates this on read.
    """

    __tablename__ = "projects"
    __allow_unmapped__ = True  # Allow non-mapped attribute: budget

    # Root ID (stable identity across versions and branches)
    project_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Computed attribute (not stored in DB, populated by service layer)
    budget: Decimal | None = None

    # Financial
    contract_value: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Draft")

    # Schedule
    start_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    end_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Temporal and branching fields inherited from mixins:
    # - valid_time: TSTZRANGE (from VersionableMixin)
    # - transaction_time: TSTZRANGE (from VersionableMixin)
    # - deleted_at: datetime | None (from VersionableMixin)
    # - branch: str (from BranchableMixin, default 'main')
    # - parent_id: UUID | None (from BranchableMixin)
    # - merge_from_branch: str | None (from BranchableMixin)

    def __repr__(self) -> str:
        return (
            f"<Project(id={self.id}, project_id={self.project_id}, "
            f"branch={self.branch}, name={self.name}, code={self.code})>"
        )
