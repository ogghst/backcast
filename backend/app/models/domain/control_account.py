"""Control Account domain model - ANSI-748 control account.

Control Accounts are the intersection of WBS Elements and Organizational Units,
representing the management control point where budget authority is delegated.
Satisfies BranchableProtocol via structural subtyping.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import EntityBase
from app.models.mixins import BranchableMixin, VersionableMixin

if TYPE_CHECKING:
    from app.models.domain.organizational_unit import OrganizationalUnit
    from app.models.domain.wbs_element import WBSElement


class ControlAccount(EntityBase, VersionableMixin, BranchableMixin):
    """Control Account entity with full EVCS capabilities (Versioning + Branching).

    A Control Account is the ANSI-748 management control point where:
    - A WBS Element meets an Organizational Unit
    - Budget authority is delegated and tracked
    - Work Packages are grouped for execution

    Attributes:
        control_account_id: Root ID for the Control Account aggregation.
        wbs_element_id: WBS Element root ID (the "what" side).
        organizational_unit_id: Organizational Unit root ID (the "who" side).
        name: Control Account name.
        code: Optional code for identification.
        description: Optional description.

    Satisfies: BranchableProtocol, VersionableProtocol
    """

    __tablename__ = "control_accounts"

    # Root ID (stable identity across versions and branches)
    control_account_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, index=True
    )

    # Matrix dimensions
    wbs_element_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because wbs_element_id is a root ID.
    )
    organizational_unit_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because organizational_unit_id is a root ID.
    )

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships (view-only for navigation, no DB constraints)
    wbs_element: Mapped["WBSElement"] = relationship(
        "WBSElement",
        primaryjoin="ControlAccount.wbs_element_id == WBSElement.wbs_element_id",
        foreign_keys=[wbs_element_id],
        viewonly=True,
    )
    organizational_unit: Mapped["OrganizationalUnit"] = relationship(
        "OrganizationalUnit",
        primaryjoin="ControlAccount.organizational_unit_id == OrganizationalUnit.organizational_unit_id",
        foreign_keys=[organizational_unit_id],
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
            f"<ControlAccount(id={self.id}, "
            f"control_account_id={self.control_account_id}, "
            f"wbs_element_id={self.wbs_element_id}, "
            f"organizational_unit_id={self.organizational_unit_id}, "
            f"name={self.name})>"
        )
