"""Change Order Audit Log domain model.

Tracks status transitions for Change Orders with optional comments.
Provides full audit trail for who changed what, when, and why.
"""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase


class ChangeOrderAuditLog(EntityBase):
    """Audit log entry for Change Order status transitions.

    Each time a Change Order's status changes, an audit entry is created
    to track the transition, who made it, when, and any optional comment.

    Attributes:
        change_order_id: Root UUID of the Change Order
        old_status: Previous status value
        new_status: New status value
        comment: Optional comment explaining the transition
        changed_by: User who made the change
        changed_at: When the change was made
    """

    __tablename__ = "change_order_audit_log"

    # Change Order reference
    change_order_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Status transition tracking
    old_status: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Previous status value"
    )
    new_status: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="New status value"
    )

    # Optional comment
    comment: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional comment for the transition"
    )

    # Audit fields
    changed_by: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )

    def __repr__(self) -> str:
        return (
            f"<ChangeOrderAuditLog(id={self.id}, "
            f"change_order_id={self.change_order_id}, "
            f"{self.old_status} → {self.new_status})>"
        )
