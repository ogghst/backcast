"""Organizational Unit domain model - branchable versioned entity.

Organizational Units replace Departments with full EVCS branching support.
They represent organizational structures (departments, divisions, teams) that
own control accounts in the ANSI-748 matrix.
Satisfies BranchableProtocol via structural subtyping.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import EntityBase
from app.models.mixins import BranchableMixin, VersionableMixin

if TYPE_CHECKING:
    from app.models.domain.user import User


class OrganizationalUnit(EntityBase, VersionableMixin, BranchableMixin):
    """Organizational Unit entity with full EVCS capabilities (Versioning + Branching).

    Organizational Units represent the organizational side of the ANSI-748
    control account matrix (WBS Element x Organizational Unit).

    Attributes:
        organizational_unit_id: Root ID for the Organizational Unit aggregation.
        parent_unit_id: Parent Organizational Unit root ID for hierarchy (optional).
        code: Unit code (e.g., "MECH", "ELEC").
        name: Display name (e.g., "Mechanical Engineering").
        manager_id: User root ID of the unit manager.
        is_active: Whether this unit is currently active.
        description: Optional description.

    Satisfies: BranchableProtocol, VersionableProtocol
    """

    __tablename__ = "organizational_units"

    # Root ID (stable identity across versions and branches)
    organizational_unit_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, index=True
    )

    # Hierarchy - parent Organizational Unit root ID
    parent_unit_id: Mapped[UUID | None] = mapped_column(
        PG_UUID,
        nullable=True,
        index=True,
    )

    # Identity
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Management
    manager_id: Mapped[UUID | None] = mapped_column(
        PG_UUID,
        nullable=True,
        # NOTE: No database-level ForeignKey constraint because manager_id references
        # a root ID that is not unique across versions. Integrity is enforced at application level.
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Metadata
    description: Mapped[str | None] = mapped_column(String(5000), nullable=True)

    # Relationships (view-only for navigation, no DB constraints)
    manager: Mapped["User"] = relationship(
        "app.models.domain.user.User",
        primaryjoin="OrganizationalUnit.manager_id == User.user_id",
        foreign_keys=[manager_id],
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
            f"<OrganizationalUnit(id={self.id}, "
            f"organizational_unit_id={self.organizational_unit_id}, "
            f"code={self.code}, name={self.name})>"
        )
