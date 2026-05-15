"""UserRoleAssignment domain model - non-versioned entity.

Manages scoped role assignments for users across system, project, and
change_order contexts. Replaces User.role (global) and ProjectMember (project)
with a single unified role assignment model.

Satisfies SimpleEntityProtocol via SimpleEntityBase.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import SimpleEntityBase

if TYPE_CHECKING:
    from app.models.domain.rbac import RBACRole
    from app.models.domain.user import User


class ScopeType(str, Enum):
    """Scope types for role assignments.

    - GLOBAL: System-wide role (replaces User.role)
    - PROJECT: Project-scoped role (replaces ProjectMember)
    - CHANGE_ORDER: Change order scoped role (replaces ApprovalMatrixService)
    """

    GLOBAL = "global"
    PROJECT = "project"
    CHANGE_ORDER = "change_order"


class UserRoleAssignment(SimpleEntityBase):
    """UserRoleAssignment entity - non-versioned with audit timestamps.

    Manages scoped role assignments for users. Each user can have multiple
    roles per scope (global, project, change_order).

    Attributes:
        id: UUID primary key.
        user_id: UUID foreign key to users.user_id (root ID).
        role_id: UUID foreign key to rbac_roles.id.
        scope_type: Type of scope (global/project/change_order).
        scope_id: UUID of the scoped entity (NULL for global).
        metadata_: JSONB for additional data (e.g., authority_level).
        granted_by: UUID of the user who granted this role.
        granted_at: Timestamp when the role was granted.
        expires_at: Optional timestamp when the role expires.
    """

    __tablename__ = "user_role_assignments"

    # Foreign keys
    # No DB FK to users.user_id — it's a business key with duplicates across
    # EVCS versions. Application-level validation ensures referential integrity.
    # (See migration e584fd7a5320 for the established pattern.)
    user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)
    role_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("rbac_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scope
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    scope_id: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True, index=True)

    # Additional data
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    # Audit trail
    granted_by: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "app.models.domain.user.User",
        primaryjoin="UserRoleAssignment.user_id == User.user_id",
        foreign_keys=[user_id],
        viewonly=True,
    )
    role: Mapped["RBACRole"] = relationship(
        "app.models.domain.rbac.RBACRole",
        primaryjoin="UserRoleAssignment.role_id == RBACRole.id",
        foreign_keys=[role_id],
        viewonly=True,
    )
    granted_by_user: Mapped["User | None"] = relationship(
        "app.models.domain.user.User",
        primaryjoin="UserRoleAssignment.granted_by == User.user_id",
        foreign_keys=[granted_by],
        viewonly=True,
    )

    def __repr__(self) -> str:
        return (
            f"<UserRoleAssignment(id={self.id}, user_id={self.user_id}, "
            f"scope_type={self.scope_type!r}, scope_id={self.scope_id})>"
        )
