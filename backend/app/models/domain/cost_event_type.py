"""Cost Event Type domain model - configurable cost event categorization.

Cost Event Types are versionable (NOT branchable) reference data for categorizing
cost events. Admins configure the available event types instead of relying on
hardcoded enums.
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


class CostEventType(EntityBase, VersionableMixin):
    """Cost Event Type - configurable cost event category.

    Cost Event Types are organizational reference data that enable:
    - Consistent cost event categorization across projects
    - Admin-configurable type registry
    - Color coding for visual differentiation
    - Quality flag for COQ metric inclusion

    Versionable but NOT branchable (organizational data, not project-specific).

    Attributes:
        cost_event_type_id: Root ID for the Cost Event Type aggregation.
        code: Type code (e.g., "quality_impact").
        name: Display name (e.g., "Quality Impact").
        color: Ant Design color name (e.g., "red", "blue").
        is_quality: Whether this type contributes to COQ metrics.
        description: Optional description.

    Satisfies: VersionableProtocol
    """

    __tablename__ = "cost_event_types"

    # Root ID (stable identity across versions)
    cost_event_type_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, index=True
    )

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
            f"<CostEventType(id={self.id}, "
            f"cost_event_type_id={self.cost_event_type_id}, "
            f"code={self.code}, name={self.name})>"
        )
