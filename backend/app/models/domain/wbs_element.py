"""WBS Element domain model - branchable versioned entity.

WBS Elements are hierarchical work breakdown structures linked to projects.
Satisfies BranchableProtocol via structural subtyping.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DECIMAL, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import EntityBase

# Import Project to ensure SQLAlchemy can resolve the relationship
from app.models.domain.project import Project  # noqa: F401 (import for side effect)
from app.models.mixins import BranchableMixin, VersionableMixin

if TYPE_CHECKING:
    from app.models.domain.project import Project


class WBSElement(EntityBase, VersionableMixin, BranchableMixin):
    """WBS Element entity with full EVCS capabilities (Versioning + Branching).

    WBS Elements are hierarchical work breakdown structures linked to projects.
    They represent the structural decomposition of project scope.

    Attributes:
        wbs_element_id: Root ID for the WBS Element aggregation.
        project_id: Foreign key to parent project (root project_id).
        parent_wbs_element_id: Parent WBS Element root ID for hierarchy (optional).
        code: WBS code (e.g., "1.2.3").
        name: WBS Element name.
        revenue_allocation: Revenue allocated to this WBS Element from project contract value.
        level: Hierarchy level (1 for top-level, 2+ for children).
        description: Optional description.
        budget_allocation: Computed budget (sum of cost element budgets in full hierarchy).
            Not stored in database; computed on-the-fly.

    Note: Budget is computed from CostElement.budget_amount values in the full
    WBS Element hierarchy (direct cost elements + all descendant WBS Elements'
    cost elements).
    """

    __tablename__ = "wbs_elements"
    __allow_unmapped__ = True  # Allow non-mapped attribute: budget_allocation

    __table_args__ = (
        # C1: exactly one current (open valid_time, non-deleted) version per
        # (root, branch). Mirrors the migration's unique partial index.
        Index(
            "ix_wbs_elements_current_version",
            "wbs_element_id",
            "branch",
            unique=True,
            postgresql_where=text("upper(valid_time) IS NULL AND deleted_at IS NULL"),
        ),
    )

    # Root ID (stable identity across versions and branches)
    wbs_element_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Parent relationship - links to Project's root project_id
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because project_id is a root ID
        # that is not unique across versions. Integrity is enforced at application level.
    )

    # WBS hierarchy - parent WBS Element root ID
    parent_wbs_element_id: Mapped[UUID | None] = mapped_column(
        PG_UUID,
        nullable=True,
        index=True,
    )

    # Identity
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Financial
    revenue_allocation: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True, default=None
    )

    # Metadata
    level: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Computed attribute (not stored in DB, populated by service layer)
    budget_allocation: Decimal | None = None

    # Custom fields (admin-defined via CustomEntityTemplate)
    custom_fields: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    custom_entity_template_root_id: Mapped[UUID | None] = mapped_column(
        PG_UUID, nullable=True
    )
    custom_field_definitions_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

    # Relationships (view-only for navigation, no DB constraints)
    project: Mapped["Project"] = relationship(
        "Project",
        primaryjoin="WBSElement.project_id == Project.project_id",
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
            f"<WBSElement(id={self.id}, wbs_element_id={self.wbs_element_id}, "
            f"project_id={self.project_id}, code={self.code}, name={self.name})>"
        )
