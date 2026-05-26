"""Work Package domain model - project-scoped cost grouping mechanism.

Work Packages are a generalized concept for grouping cost registrations under
a project. They support multiple types (quality_impact, site_visit, production_phase,
warranty_batch, commissioning) with quality-specific fields remaining as nullable
native columns for the quality_impact type.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

if TYPE_CHECKING:
    from app.models.domain.package_type import PackageType


class WorkPackage(EntityBase, VersionableMixin):
    """Project-scoped cost grouping mechanism.

    Generalizes the former QualityImpact entity to support multiple work package
    types. Quality-specific fields (coq_category, schedule_impact_days,
    external_event_id) remain as nullable columns populated only when
    package_type = 'quality_impact'.

    Versionable but NOT branchable (financial facts are global across branches).

    Attributes:
        work_package_id: Root ID for the WorkPackage aggregation.
        project_id: Root ID of the parent Backcast project.
        name: Human-readable label for the work package (required).
        package_type_id: Root ID of the PackageType category.
        description: Optional description of the work package.
        status: Lifecycle state -- 'open' or 'closed'.
        external_event_id: External reference identifier (e.g., QMS ID, PO number, work order).
        event_date: When the event occurred (nullable).
        coq_category: Cost of Quality category (quality-specific, nullable).
        cost_impact: Total financial impact (declared/estimated).
        schedule_impact_days: Days of schedule delay (quality-specific, nullable).
    """

    __tablename__ = "work_packages"

    # Root ID (stable identity across versions)
    work_package_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Primary relationship -- project-scoped
    project_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # New general fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    package_type_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint because package_type_id is
        # a root ID that is not unique across versions. Integrity is enforced at application level.
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", server_default="open"
    )

    # External reference identifier (e.g., QMS ID, PO number, work order number)
    external_event_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )

    # When the event occurred
    event_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Cost of Quality category (quality-specific, nullable for non-quality types)
    coq_category: Mapped[str | None] = mapped_column(
        String(30), nullable=True, default=None
    )

    # Financial impact (declared/estimated cost for the package)
    cost_impact: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False, default=Decimal("0")
    )

    # Schedule impact (quality-specific, nullable for non-quality types)
    schedule_impact_days: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )

    # Relationships (view-only, no DB constraints)
    package_type_ref: Mapped["PackageType"] = relationship(
        "PackageType",
        primaryjoin="WorkPackage.package_type_id == PackageType.package_type_id",
        foreign_keys=[package_type_id],
        viewonly=True,
    )

    # Temporal fields inherited from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None
    # - created_by: UUID
    # - deleted_by: UUID | None

    def __repr__(self) -> str:
        return (
            f"<WorkPackage(id={self.id}, "
            f"work_package_id={self.work_package_id}, "
            f"name={self.name}, "
            f"package_type_id={self.package_type_id}, "
            f"project_id={self.project_id}, "
            f"status={self.status}, "
            f"cost_impact={self.cost_impact})>"
        )
