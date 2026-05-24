"""Package Type domain model - configurable work package categorization.

Package Types are versionable (NOT branchable) reference data for categorizing
work packages. Admins can configure the available package types instead of
relying on a hardcoded enum.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

if TYPE_CHECKING:
    pass


class PackageType(EntityBase, VersionableMixin):
    """Package Type - configurable work package category.

    Package Types are organizational reference data that enable:
    - Consistent work package categorization across projects
    - Admin-configurable type registry (replaces hardcoded enum)
    - Color coding for visual differentiation

    Versionable but NOT branchable (organizational data, not project-specific).

    Attributes:
        package_type_id: Root ID for the Package Type aggregation.
        code: Type code (e.g., "quality_impact").
        name: Display name (e.g., "Quality Impact").
        color: Ant Design color name (e.g., "red", "blue").
        description: Optional description.

    Satisfies: VersionableProtocol
    """

    __tablename__ = "package_types"

    # Root ID (stable identity across versions)
    package_type_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Identity
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(30), nullable=False, default="blue")

    # Quality flag
    is_quality: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

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
            f"<PackageType(id={self.id}, "
            f"package_type_id={self.package_type_id}, "
            f"code={self.code}, name={self.name})>"
        )
