"""Work Package domain model - ANSI-748 PMI work package (budget holder).

Work Packages are the lowest level of the WBS where work is planned,
budgeted, and tracked. They belong to Control Accounts and hold budget.
Satisfies BranchableProtocol via structural subtyping.
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
    from app.models.domain.control_account import ControlAccount


class WorkPackage(EntityBase, VersionableMixin, BranchableMixin):
    """Work Package entity - PMI budget holder under a Control Account.

    Work Packages are the lowest management level where:
    - Budget is allocated and tracked
    - Work is planned and scheduled
    - Progress is measured (via progress entries against child Cost Elements)

    Branchable (supports change orders) and Versionable (tracks changes).

    Attributes:
        work_package_id: Root ID for the Work Package aggregation.
        control_account_id: Parent Control Account root ID.
        name: Work Package name.
        code: Work Package code (e.g., "WP-001").
        budget_amount: Allocated budget for this work package.
        schedule_baseline_id: 1:1 reference to schedule baseline (optional).
        forecast_id: 1:1 reference to forecast (optional).
        description: Optional description.
        status: Lifecycle state ('open' or 'closed').

    Satisfies: BranchableProtocol, VersionableProtocol
    """

    __tablename__ = "work_packages"

    # Root ID (stable identity across versions and branches)
    work_package_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Parent relationship
    control_account_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because control_account_id is a root ID.
    )

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Financial
    budget_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2), default=0, nullable=False
    )

    # Schedule Baseline (1:1 relationship per version)
    schedule_baseline_id: Mapped[UUID | None] = mapped_column(
        PG_UUID,
        nullable=True,
        index=True,
        comment="1:1 reference to schedule baseline",
    )

    # Forecast (1:1 relationship per version)
    forecast_id: Mapped[UUID | None] = mapped_column(
        PG_UUID,
        nullable=True,
        index=True,
        comment="1:1 reference to forecast",
    )

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", server_default="open"
    )

    # Relationships (view-only for navigation, no DB constraints)
    control_account: Mapped["ControlAccount"] = relationship(
        "ControlAccount",
        primaryjoin="WorkPackage.control_account_id == ControlAccount.control_account_id",
        foreign_keys=[control_account_id],
        viewonly=True,
    )

    # Temporal and branching fields inherited from mixins:
    # - valid_time: TSTZRANGE (from VersionableMixin)
    # - transaction_time: TSTZRANGE (from VersionableMixin)
    # - deleted_at: datetime | None (from VersionableMixin)
    # - branch: str (from BranchableMixin, default 'main')
    # - parent_id: UUID | None (from BranchableMixin)
    # - merge_from_branch: str | None (from BranchableMixin)

    def __repr__(self) -> str:
        return (
            f"<WorkPackage(id={self.id}, "
            f"work_package_id={self.work_package_id}, "
            f"control_account_id={self.control_account_id}, "
            f"code={self.code}, name={self.name}, "
            f"budget_amount={self.budget_amount})>"
        )
