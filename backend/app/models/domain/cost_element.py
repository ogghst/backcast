"""Cost Element domain model - EOC (Element of Cost) under a Work Package.

Cost Elements are categorization entities linking a Work Package to a Cost
Element Type. Budget is managed at the WorkPackage.budget_amount level (BAC).

Versionable but NOT branchable (financial facts are global across branches).
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

if TYPE_CHECKING:
    from app.models.domain.cost_element_type import CostElementType
    from app.models.domain.work_package import WorkPackage


class CostElement(EntityBase, VersionableMixin):
    """Cost Element - EOC (Element of Cost) under a Work Package.

    Cost Elements are categorization entities linking a Work Package to a
    Cost Element Type. Budget is held on WorkPackage.budget_amount (the BAC
    in ANSI-748/EVM), not on CostElement.

    Actual costs are tracked via Cost Registrations against Cost Elements.

    Versionable but NOT branchable (cost data is global facts across branches).

    Attributes:
        cost_element_id: Root ID for the Cost Element aggregation.
        work_package_id: Parent Work Package root ID.
        cost_element_type_id: Reference to standardized cost type.
        description: Optional description.

    Satisfies: VersionableProtocol
    """

    __tablename__ = "cost_elements"

    # Root ID (stable identity across versions)
    cost_element_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Parent relationships
    work_package_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because work_package_id is a root ID
        # that is not unique across versions. Integrity is enforced at application level.
    )
    cost_element_type_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because cost_element_type_id is
        # a root ID that is not unique across versions. Integrity is enforced at application level.
    )

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships (View-only for navigation, no DB constraints)
    work_package: Mapped["WorkPackage"] = relationship(
        "WorkPackage",
        primaryjoin="CostElement.work_package_id == WorkPackage.work_package_id",
        foreign_keys=[work_package_id],
        viewonly=True,
    )
    cost_element_type: Mapped["CostElementType"] = relationship(
        "CostElementType",
        primaryjoin="CostElement.cost_element_type_id == CostElementType.cost_element_type_id",
        foreign_keys=[cost_element_type_id],
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
            f"<CostElement(id={self.id}, cost_element_id={self.cost_element_id}, "
            f"work_package_id={self.work_package_id})>"
        )
