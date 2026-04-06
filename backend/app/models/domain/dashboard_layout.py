"""DashboardLayout domain model - non-versioned entity.

Stores per-user dashboard configurations including widget arrangements,
templates, and project-scoped layouts.
Satisfies SimpleEntityProtocol via SimpleEntityBase.
"""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class DashboardLayout(SimpleEntityBase):
    """DashboardLayout entity - non-versioned with audit timestamps.

    Stores a user's dashboard widget configuration. Layouts can be
    scoped to a specific project or be global (project_id is NULL).
    Template layouts are reusable starting configurations.

    Satisfies: SimpleEntityProtocol

    Attributes:
        id: UUID primary key.
        name: Human-readable layout name.
        description: Optional layout description.
        user_id: Owner of this layout (FK to users.user_id).
        project_id: Optional project scope (FK to projects.project_id).
        is_template: Whether this layout is a reusable template.
        is_default: Whether this is the user's default layout for its scope.
        widgets: JSONB array of widget configuration objects.
    """

    __tablename__ = "dashboard_layouts"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Root IDs without FK constraints: target columns (user_id, project_id)
    # have partial unique indexes with WHERE clauses, which PostgreSQL does not
    # accept as FK targets. Application-level referential integrity is enforced
    # in the service layer.
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID,
        nullable=True,
        index=True,
    )

    # Layout flags
    is_template: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        index=True,
        server_default=sa.text("false"),
    )
    is_default: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    )

    # Widget configuration stored as JSONB array
    widgets: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
    )

    def __repr__(self) -> str:
        return (
            f"<DashboardLayout(id={self.id}, name={self.name!r}, "
            f"user_id={self.user_id}, project_id={self.project_id})>"
        )
