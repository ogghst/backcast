"""Cost Element Type domain model - organizational cost categorization.

Cost Element Types are versionable (NOT branchable) reference data owned by departments.
They enable cost standardization and cross-project comparability.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

if TYPE_CHECKING:
    pass


class CostElementType(EntityBase, VersionableMixin):
    """Cost Element Type - standardized cost category owned by a department.

    Cost Element Types are organizational reference data that enable:
    - Consistent cost categorization across projects
    - Cross-project cost comparability
    - Department ownership of cost types

    Versionable but NOT branchable (organizational data, not project-specific).

    Attributes:
        cost_element_type_id: Root ID for the Cost Element Type aggregation.
        department_id: Owning department (e.g., Mechanical Dept owns "Mechanical Installation").
        code: Cost type code (e.g., "MECH-INST").
        name: Display name (e.g., "Mechanical Installation").
        description: Optional description.

    Examples:
        - Code: "ELECT-INST", Name: "Electrical Installation", Dept: Electrical Engineering
        - Code: "SW-DEV", Name: "Software Development", Dept: Software Engineering
        - Code: "QA-TEST", Name: "Quality Assurance Testing", Dept: Quality Assurance

    Satisfies: VersionableProtocol
    """

    __tablename__ = "cost_element_types"

    # Root ID (stable identity across versions)
    cost_element_type_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, index=True
    )

    # Department ownership
    department_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because department_id is a root ID.
    )

    # Identity
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Temporal fields inherited from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None
    # - created_by: UUID
    # - deleted_by: UUID | None

    def __repr__(self) -> str:
        return (
            f"<CostElementType(id={self.id}, "
            f"cost_element_type_id={self.cost_element_type_id}, "
            f"code={self.code}, name={self.name})>"
        )
