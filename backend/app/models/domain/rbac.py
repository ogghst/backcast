"""RBAC domain models for database-backed role-based access control.

All entities use SimpleEntityBase pattern (non-versioned).
Provides:
- RBACRole: Role definitions with system-role flag
- RBACRolePermission: Permission assignments per role
"""

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import SimpleEntityBase


class RBACRole(SimpleEntityBase):
    """RBAC Role entity - non-versioned with audit timestamps.

    Stores role definitions used for access control across the system.
    System roles (is_system=True) are seed-managed and cannot be deleted
    through the API.

    Satisfies: SimpleEntityProtocol

    Attributes:
        id: UUID primary key.
        name: Unique role name (e.g., 'admin', 'project-manager').
        description: Optional human-readable role description.
        is_system: Whether this is a system-managed role.
    """

    __tablename__ = "rbac_roles"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Relationships
    permissions: Mapped[list["RBACRolePermission"]] = relationship(
        "RBACRolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        foreign_keys="[RBACRolePermission.role_id]",
    )

    def __repr__(self) -> str:
        return f"<RBACRole(id={self.id}, name={self.name!r}, is_system={self.is_system})>"


class RBACRolePermission(SimpleEntityBase):
    """RBAC Role-Permission assignment - non-versioned with audit timestamps.

    Stores permission strings assigned to roles. Each (role_id, permission)
    pair must be unique.

    Satisfies: SimpleEntityProtocol

    Attributes:
        id: UUID primary key.
        role_id: Foreign key to rbac_roles.id (CASCADE delete).
        permission: Permission string (e.g., 'dashboard-read', 'cost-element-write').
    """

    __tablename__ = "rbac_role_permissions"

    role_id: Mapped[str] = mapped_column(
        PG_UUID,
        ForeignKey("rbac_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    role: Mapped["RBACRole"] = relationship(
        "RBACRole", back_populates="permissions", foreign_keys=[role_id]
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("role_id", "permission", name="uq_role_permission"),
    )

    def __repr__(self) -> str:
        return f"<RBACRolePermission(id={self.id}, role_id={self.role_id}, permission={self.permission!r})>"
