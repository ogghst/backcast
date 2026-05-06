"""Approval Matrix Service for change order approver validation and assignment.

This service manages the approval matrix for change orders, mapping impact levels
to required authority levels and assigning appropriate approvers based on user roles.

Context: Used by ChangeOrderWorkflowService to assign approvers on submission
and validate approval authority during the approval workflow.

Authority and role mappings are now read from the configurable workflow
configuration service (ChangeOrderConfigService), supporting the 5-role system
(viewer, editor_pm, dept_head, director, admin).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import cast as sql_cast
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.models.domain.user import User

if TYPE_CHECKING:
    from app.services.change_order_config_service import ChangeOrderConfigService


class ApprovalMatrixService:
    """Service for change order approval matrix management.

    Manages the approval matrix that maps impact levels to required authority
    and assigns appropriate approvers based on user roles and permissions.
    All mappings are read from the configurable workflow configuration.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        config_service: ChangeOrderConfigService | None = None,
    ) -> None:
        """Initialize the service with a database session.

        Args:
            db_session: Async database session for queries
            config_service: Optional config service for approval matrix lookup.
        """
        self._db = db_session
        self._config_service = config_service

    async def get_user_authority_level(self, user: User) -> str:
        """Get the user's approval authority level based on their role.

        Reads role-to-authority mapping from workflow configuration.

        Args:
            user: User domain object

        Returns:
            Authority level string: LOW, MEDIUM, HIGH, or CRITICAL
        """
        role_authority = await self._get_role_authority()
        return role_authority.get(user.role, "LOW")

    async def get_authority_for_impact(self, impact_level: str) -> str:
        """Get the required authority level for a given impact level.

        Reads impact-to-authority mapping from workflow configuration.

        Args:
            impact_level: Financial impact level (LOW/MEDIUM/HIGH/CRITICAL)

        Returns:
            Required authority level string

        Raises:
            ValueError: If impact_level is invalid
        """
        impact_authority = await self._get_impact_authority()
        if impact_level not in impact_authority:
            raise ValueError(
                f"Invalid impact level: {impact_level}. "
                f"Must be one of: {list(impact_authority.keys())}"
            )
        return impact_authority[impact_level]

    async def can_approve(self, user: User, change_order: ChangeOrder) -> bool:
        """Check if a user has authority to approve a change order.

        Compares the user's authority level with the required authority
        level for the change order's impact level. Also checks if the user
        is active.

        Args:
            user: User domain object
            change_order: ChangeOrder domain object

        Returns:
            True if user can approve, False otherwise

        Example:
            >>> service = ApprovalMatrixService(session)
            >>> can = await service.can_approve(manager, change_order)
            >>> print(can)
            True
        """
        # Inactive users cannot approve
        if not user.is_active:
            return False

        # Get impact level from change order
        impact_level = change_order.impact_level
        if impact_level is None:
            # No impact level means no approval required yet
            return False

        # Get user's authority level
        user_authority = await self.get_user_authority_level(user)

        # Get required authority for this impact level
        required_authority = await self.get_authority_for_impact(impact_level)

        # Compare authority levels using hierarchy from config
        hierarchy = await self._get_authority_hierarchy()
        user_level = hierarchy.get(user_authority, 0)
        required_level = hierarchy.get(required_authority, 0)

        return user_level >= required_level

    async def get_approver_for_impact(
        self, project_id: UUID, impact_level: str
    ) -> UUID | None:
        """Find an appropriate approver for a given impact level.

        Selects an active user with sufficient authority to approve the
        change order. For now, uses a simplified approach to find the first
        eligible user.

        Args:
            project_id: Project ID (for future project-specific assignment)
            impact_level: Financial impact level

        Returns:
            User ID of eligible approver, or None if no eligible approver found

        Example:
            >>> service = ApprovalMatrixService(session)
            >>> approver_id = await service.get_approver_for_impact(
            ...     project_id, 'HIGH'
            ... )
        """
        from typing import cast as typing_cast

        # Get required authority for this impact level
        required_authority = await self.get_authority_for_impact(impact_level)

        # Get role-to-authority mapping and hierarchy from config
        role_authority = await self._get_role_authority()
        hierarchy = await self._get_authority_hierarchy()

        # Find all roles with sufficient authority
        eligible_roles = [
            role
            for role, authority in role_authority.items()
            if hierarchy.get(authority, 0) >= hierarchy.get(required_authority, 0)
        ]

        if not eligible_roles:
            return None

        # Query for active users with eligible roles
        # Use first match for now (can be enhanced later for project-specific assignment)
        as_of_tstz = sql_cast(func.clock_timestamp(), TIMESTAMP(timezone=True))
        stmt = (
            select(User)
            .where(
                User.role.in_(eligible_roles),
                User.is_active == True,  # noqa: E712
                typing_cast(Any, User).valid_time.op("@>")(as_of_tstz),
                func.lower(typing_cast(Any, User).valid_time) <= as_of_tstz,
                typing_cast(Any, User).deleted_at.is_(None),
            )
            .order_by(User.role.desc())  # Prefer higher authority roles
            .limit(1)
        )

        result = await self._db.execute(stmt)
        approver = result.scalar_one_or_none()

        return approver.user_id if approver else None

    async def get_approval_info(
        self, change_order_id: UUID, current_user: User
    ) -> dict[str, Any] | None:
        """Get complete approval information for a change order.

        Provides comprehensive information about approval requirements,
        assigned approver, and whether the current user can approve.

        Args:
            change_order_id: UUID of the change order
            current_user: User requesting the information

        Returns:
            Dictionary with approval information or None if not found

            Keys:
                - change_order_id: UUID of change order
                - impact_level: Financial impact level
                - required_authority: Authority level required to approve
                - assigned_approver_id: User ID of assigned approver
                - can_approve: Whether current user can approve
                - user_authority: Current user's authority level

        Raises:
            No explicit raises - returns None for not found

        Example:
            >>> service = ApprovalMatrixService(session)
            >>> info = await service.get_approval_info(co_id, current_user)
            >>> print(info["can_approve"])
            True
        """
        from typing import cast as typing_cast

        # Get change order
        as_of_tstz = sql_cast(func.clock_timestamp(), TIMESTAMP(timezone=True))
        stmt = (
            select(ChangeOrder)
            .where(
                ChangeOrder.change_order_id == change_order_id,
                ChangeOrder.branch == "main",
                typing_cast(Any, ChangeOrder).valid_time.op("@>")(as_of_tstz),
                func.lower(typing_cast(Any, ChangeOrder).valid_time) <= as_of_tstz,
                typing_cast(Any, ChangeOrder).deleted_at.is_(None),
            )
            .order_by(typing_cast(Any, ChangeOrder).valid_time.desc())
            .limit(1)
        )

        result = await self._db.execute(stmt)
        change_order = result.scalar_one_or_none()

        if change_order is None:
            return None

        # Get impact level and required authority
        impact_level = change_order.impact_level
        if impact_level is None:
            required_authority = None
        else:
            required_authority = await self.get_authority_for_impact(impact_level)

        # Get current user's authority
        user_authority = await self.get_user_authority_level(current_user)

        # Check if current user can approve
        can_approve = False
        if impact_level and current_user.is_active:
            hierarchy = await self._get_authority_hierarchy()
            user_level = hierarchy.get(user_authority, 0)
            required_level = (
                hierarchy.get(required_authority, 0) if required_authority else 0
            )
            can_approve = user_level >= required_level

        return {
            "change_order_id": change_order.change_order_id,
            "impact_level": impact_level,
            "required_authority": required_authority,
            "assigned_approver_id": change_order.assigned_approver_id,
            "can_approve": can_approve,
            "user_authority": user_authority,
        }

    # --- Private helpers for config-based lookups ---

    async def _get_config_service(self) -> ChangeOrderConfigService:
        """Get or create the config service."""
        from app.services.change_order_config_service import (
            ChangeOrderConfigService,
        )

        if self._config_service is not None:
            return self._config_service
        return ChangeOrderConfigService(self._db)

    async def _get_role_authority(self) -> dict[str, str]:
        """Get role-to-authority mapping from config."""
        config_service = await self._get_config_service()
        return await config_service.get_role_authority_mapping()

    async def _get_impact_authority(self) -> dict[str, str]:
        """Get impact-level-to-required-authority mapping from config."""
        config_service = await self._get_config_service()
        return await config_service.get_impact_authority_mapping()

    async def _get_authority_hierarchy(self) -> dict[str, int]:
        """Get authority hierarchy from config."""
        config_service = await self._get_config_service()
        return await config_service.get_authority_hierarchy()
