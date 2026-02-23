"""WBE (Work Breakdown Element) domain model - branchable versioned entity.

WBEs support branching and have parent-child relationship with Projects.
Satisfies BranchableProtocol via structural subtyping.
"""

from decimal import Decimal

# TYPE_CHECKING import to avoid circular dependency
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DECIMAL, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import EntityBase
from app.models.mixins import BranchableMixin, VersionableMixin

if TYPE_CHECKING:
    from app.models.domain.project import Project


class WBE(EntityBase, VersionableMixin, BranchableMixin):
    """WBE entity with full EVCS capabilities (Versioning + Branching).

    WBEs are hierarchical work breakdown elements linked to projects.

    Attributes:
        wbe_id: Root ID for the WBE aggregation.
        project_id: Foreign key to parent project (root project_id).
        code: WBS code (e.g., "1.2.3").
        name: WBE name.
        description: Optional description.
        budget_allocation: Budget allocated to this WBE.
        level: Hierarchy level (1 for top-level, 2+ for children).
        parent_wbe_id: Parent WBE root ID for hierarchy (optional).
    """

    __tablename__ = "wbes"

    # Root ID (stable identity across versions and branches)
    wbe_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Parent relationship - links to Project's root project_id
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because project_id is a root ID
        # that is not unique across versions. Integrity is enforced at application level.
    )

    # WBE hierarchy - parent WBE root ID
    parent_wbe_id: Mapped[UUID | None] = mapped_column(
        PG_UUID,
        nullable=True,
        index=True,
    )

    # Identity
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Financial
    budget_allocation: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), default=0)
    revenue_allocation: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True, default=None
    )

    # Metadata
    level: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    # Note: relationship to Project uses root ID join and is view-only
    project: Mapped["Project"] = relationship(
        "Project",
        primaryjoin="WBE.project_id == Project.project_id",
        foreign_keys=[project_id],
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
            f"<WBE(id={self.id}, wbe_id={self.wbe_id}, "
            f"project_id={self.project_id}, code={self.code}, name={self.name})>"
        )
