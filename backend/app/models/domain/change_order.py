"""Change Order domain model - branchable versioned entity.

Change Orders support branching for change management workflows.
Satisfies BranchableProtocol via structural subtyping.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import BranchableMixin, VersionableMixin


class ImpactLevel:
    """Impact level classification for change order approval matrix.

    Financial impact thresholds determine required approval authority:
    - LOW: < €10,000 (Project Manager approval)
    - MEDIUM: €10,000 - €50,000 (Department Head approval)
    - HIGH: €50,000 - €100,000 (Director approval)
    - CRITICAL: > €100,000 (Executive Committee approval)
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def all(cls) -> list[str]:
        """Return all valid impact levels."""
        return [cls.LOW, cls.MEDIUM, cls.HIGH, cls.CRITICAL]


class SLAStatus:
    """SLA tracking status for change order approvals.

    Status progression:
    - pending: More than 50% of SLA time remaining
    - approaching: Less than 50% of SLA time remaining
    - overdue: Past SLA due date
    """

    PENDING = "pending"
    APPROACHING = "approaching"
    OVERDUE = "overdue"

    @classmethod
    def all(cls) -> list[str]:
        """Return all valid SLA statuses."""
        return [cls.PENDING, cls.APPROACHING, cls.OVERDUE]


class ChangeOrder(EntityBase, VersionableMixin, BranchableMixin):
    """Change Order entity with full EVCS capabilities (Versioning + Branching).

    A Change Order represents a proposed modification to a Project that must
    go through approval workflow before being merged into the main branch.

    Attributes:
        change_order_id: Root UUID identifier for the change order aggregation
        code: Business identifier (e.g., "CO-2026-001")
        project_id: Reference to the Project this change applies to
        title: Brief title of the change
        description: Detailed description of what the change entails
        justification: Business justification for the change
        effective_date: When the change should take effect (if approved)
        status: Workflow state (Draft, Submitted, Approved, Rejected, Implemented)
        impact_level: Financial impact classification (LOW/MEDIUM/HIGH/CRITICAL)
        assigned_approver_id: User ID responsible for approval
        sla_assigned_at: When approval SLA started
        sla_due_date: SLA deadline for approval
        sla_status: Current SLA tracking status (pending/approaching/overdue)

    Note: Following EVCS pattern, change_order_id is the UUID root identifier
    used for versioning/branching, while code is the human-readable business ID.
    """

    __tablename__ = "change_orders"

    # Root ID (stable identity across versions and branches) - UUID for EVCS
    change_order_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Business identifier (human-readable)
    # Not unique at table level - same code appears in multiple branches
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Project reference
    project_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Change Order Metadata
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    justification: Mapped[str] = mapped_column(Text, nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Workflow State
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Draft")

    # Branch reference (explicit link to branches table)
    branch_name: Mapped[str | None] = mapped_column(
        String(80), nullable=True, index=True
    )

    # Approval Matrix & SLA Tracking (E06-U09 to E06-U13)
    impact_level: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )
    assigned_approver_id: Mapped[UUID | None] = mapped_column(
        PG_UUID, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    sla_assigned_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    sla_due_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, index=True
    )
    sla_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=None
    )

    # Temporal and branching fields inherited from mixins:
    # - valid_time: TSTZRANGE (from VersionableMixin)
    # - transaction_time: TSTZRANGE (from VersionableMixin)
    # - deleted_at: datetime | None (from VersionableMixin)
    # - created_by: UUID (from VersionableMixin)
    # - deleted_by: UUID | None (from VersionableMixin)
    # - branch: str (from BranchableMixin, default 'main')
    # - parent_id: UUID | None (from BranchableMixin)
    # - merge_from_branch: str | None (from BranchableMixin)

    @hybrid_property
    def created_at(self) -> datetime | None:
        """Derive created_at from transaction_time.lower for API compatibility."""
        if self.transaction_time is not None:
            # Cast to Any to access PostgreSQL range lower bound
            lower_bound = getattr(self.transaction_time, 'lower', None)
            if isinstance(lower_bound, datetime):
                return lower_bound
        return None

    def __repr__(self) -> str:
        return (
            f"<ChangeOrder(id={self.id}, change_order_id={self.change_order_id}, "
            f"code={self.code}, project_id={self.project_id}, branch={self.branch}, "
            f"status={self.status}, impact_level={self.impact_level}, "
            f"sla_status={self.sla_status})>"
        )
