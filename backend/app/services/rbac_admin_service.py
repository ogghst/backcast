"""Admin service for RBAC role and permission management.

Provides CRUD operations for RBACRole with permission management
through the RBACRolePermission relationship.  Invalidates the
DatabaseRBACService cache after every write.
"""

from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rbac_database import DatabaseRBACService
from app.models.domain.rbac import RBACRole, RBACRolePermission


class RBACAdminService:
    """Service for administering RBAC roles and permissions.

    Intended for use by admin API routes only.  Not a generic
    SimpleService because role creation involves two tables
    (RBACRole + RBACRolePermission).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def list_roles(self) -> list[RBACRole]:
        """List all roles with their permissions eagerly loaded."""
        stmt = (
            select(RBACRole)
            .options(selectinload(RBACRole.permissions))
            .order_by(RBACRole.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_role(self, role_id: UUID) -> RBACRole | None:
        """Get a single role by ID with permissions eagerly loaded."""
        stmt = (
            select(RBACRole)
            .options(selectinload(RBACRole.permissions))
            .where(RBACRole.id == role_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_permissions(self) -> list[str]:
        """Return distinct permission strings across all roles."""
        stmt = (
            select(RBACRolePermission.permission)
            .distinct()
            .order_by(RBACRolePermission.permission)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create_role(
        self,
        name: str,
        description: str | None,
        permissions: list[str],
    ) -> RBACRole:
        """Create a new role with the given permissions.

        Args:
            name: Unique role name.
            description: Optional human-readable description.
            permissions: Non-empty list of permission strings.

        Returns:
            The newly created RBACRole with permissions loaded.
        """
        role = RBACRole(name=name, description=description, is_system=False)
        self.session.add(role)
        await self.session.flush()

        for perm in permissions:
            self.session.add(
                RBACRolePermission(role_id=role.id, permission=perm)
            )
        await self.session.flush()
        await self._invalidate_cache()

        # Eagerly load permissions for response serialisation
        await self.session.refresh(role, ["permissions"])
        return role

    async def update_role(
        self,
        role_id: UUID,
        name: str | None,
        description: str | None,
        permissions: list[str] | None,
    ) -> RBACRole | None:
        """Update a role's name, description, and/or permissions.

        Args:
            role_id: UUID of the role to update.
            name: New name (or None to keep existing).
            description: New description (or None to keep existing).
            permissions: New permission list (or None to keep existing).

        Returns:
            Updated RBACRole, or None if role not found.
        """
        role = await self.session.get(RBACRole, role_id)
        if role is None:
            return None

        if name is not None:
            role.name = name
        if description is not None:
            role.description = description

        if permissions is not None:
            await self.session.execute(
                sa_delete(RBACRolePermission).where(
                    RBACRolePermission.role_id == role_id
                )
            )
            await self.session.flush()

            for perm in permissions:
                self.session.add(
                    RBACRolePermission(role_id=role_id, permission=perm)
                )

        await self.session.flush()
        await self._invalidate_cache()

        # Refresh role: columns (e.g. updated_at) and permissions relationship
        await self.session.refresh(role)
        await self.session.refresh(role, ["permissions"])
        return role

    async def delete_role(self, role_id: UUID) -> bool:
        """Delete a non-system role.

        Args:
            role_id: UUID of the role to delete.

        Returns:
            True if deleted, False if role not found.

        Raises:
            ValueError: If attempting to delete a system role.
        """
        role = await self.session.get(RBACRole, role_id)
        if role is None:
            return False
        if role.is_system:
            raise ValueError("Cannot delete system role")

        await self.session.delete(role)  # cascade deletes permissions
        await self.session.flush()
        await self._invalidate_cache()
        return True

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    async def _invalidate_cache(self) -> None:
        """Invalidate RBAC permissions cache if using DatabaseRBACService."""
        from app.core.rbac import get_rbac_service

        service = get_rbac_service()
        if isinstance(service, DatabaseRBACService):
            service.invalidate_cache()
