"""DashboardLayout domain model - non-versioned entity.

Stores per-user dashboard configurations including widget arrangements,
templates, and project-scoped layouts.
Satisfies SimpleEntityProtocol via SimpleEntityBase.
"""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import Index, String, Text
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
        role: Which role this portfolio template defaults to (templates only).
            ``NULL`` on user layouts and on the generic portfolio fallback
            template. Set only on portfolio-scope templates.
        scope: Template audience discriminator: ``"project"`` (project-content
            widgets) or ``"portfolio"`` (portfolio widgets). ``NULL`` on
            non-template user layouts (those are distinguished by
            ``project_id``, not ``scope``).
    """

    __tablename__ = "dashboard_layouts"

    __table_args__ = (
        # G8 structural fix: NULL-safe unique partial indexes so a concurrent
        # first-visit clone cannot leave two is_default=True non-template
        # layouts in the same scope. Postgres treats NULL != NULL in unique
        # indexes, so a single (user_id, project_id) index would NOT prevent
        # duplicate GLOBAL defaults (project_id IS NULL). Two partial indexes
        # are required: one for the global scope (project_id IS NULL, keyed on
        # user_id alone) and one per (user, project) for project-scoped layouts.
        Index(
            "uq_dashboard_layouts_default_global",
            "user_id",
            unique=True,
            postgresql_where=sa.text(
                "is_template = false AND is_default = true AND project_id IS NULL"
            ),
        ),
        Index(
            "uq_dashboard_layouts_default_project",
            "user_id",
            "project_id",
            unique=True,
            postgresql_where=sa.text(
                "is_template = false AND is_default = true AND project_id IS NOT NULL"
            ),
        ),
    )

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

    # Template tagging (templates only). ``role`` selects which role a portfolio
    # template defaults to; ``scope`` separates project vs portfolio templates.
    # Both are NULL on user layouts.
    role: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    scope: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)

    def __repr__(self) -> str:
        return (
            f"<DashboardLayout(id={self.id}, name={self.name!r}, "
            f"user_id={self.user_id}, project_id={self.project_id})>"
        )
