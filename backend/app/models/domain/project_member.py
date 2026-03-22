"""ProjectMember domain model - non-versioned entity.

Manages project-level role assignments for users.
Satisfies SimpleEntityProtocol via SimpleEntityBase.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import SimpleEntityBase

if TYPE_CHECKING:
    from app.models.domain.project import Project
    from app.models.domain.user import User


class ProjectMember(SimpleEntityBase):
    """ProjectMember entity - non-versioned with audit timestamps.

    Manages many-to-many relationship between Users and Projects with role-based access.

    Satisfies: SimpleEntityProtocol

    Attributes:
        id: UUID primary key (version identifier).
        user_id: UUID foreign key to users.user_id (root ID).
        project_id: UUID foreign key to projects.project_id (root ID).
        role: ProjectRole enum value (e.g., 'project_admin', 'project_viewer').
        assigned_at: Timestamp when the role was assigned.
        assigned_by: UUID of the user who assigned this role.
    """

    __tablename__ = "project_members"
    __table_args__ = (
        # Ensure one role per user per project
        UniqueConstraint("user_id", "project_id", name="uq_project_members_user_project"),
    )

    # Foreign keys to root IDs (not version PKs)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role assignment details
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # ProjectRole enum value
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    assigned_by: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "app.models.domain.user.User",
        primaryjoin="ProjectMember.user_id == User.user_id",
        foreign_keys=[user_id],
        viewonly=True,
    )
    project: Mapped["Project"] = relationship(
        "app.models.domain.project.Project",
        primaryjoin="ProjectMember.project_id == Project.project_id",
        foreign_keys=[project_id],
        viewonly=True,
    )
    assigner: Mapped["User"] = relationship(
        "app.models.domain.user.User",
        primaryjoin="ProjectMember.assigned_by == User.user_id",
        foreign_keys=[assigned_by],
        viewonly=True,
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectMember(id={self.id}, user_id={self.user_id}, "
            f"project_id={self.project_id}, role={self.role})>"
        )
