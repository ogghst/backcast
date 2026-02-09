"""Approval Matrix Service for change order approver validation and assignment.

This service manages the approval matrix for change orders, mapping impact levels
to required authority levels and assigning appropriate approvers based on user roles.

Context: Used by ChangeOrderWorkflowService to assign approvers on submission
and validate approval authority during the approval workflow.

Service Layer:
- Validates approver authority for change orders
- Assigns approvers based on impact level
- Maps user roles to approval authority levels
- Provides complete approval information for UI display
"""

from typing import Any
from uuid import UUID

from sqlalchemy import cast as sql_cast
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder, ImpactLevel
from app.models.domain.user import User


class ApprovalMatrixService:
    """Service for change order approval matrix management.

    Manages the approval matrix that maps impact levels to required authority
    and assigns appropriate approvers based on user roles and permissions.

    Authority Levels:
    - LOW: Can approve LOW impact changes (< €10,000)
    - MEDIUM: Can approve MEDIUM impact changes (€10,000 - €50,000)
    - HIGH: Can approve HIGH impact changes (€50,000 - €100,000)
    - CRITICAL: Can approve CRITICAL impact changes (> €100,000)

    Role to Authority Mapping:
    - admin role: CRITICAL authority
    - manager role: HIGH authority
    - viewer role: LOW authority
    """

    # Role to authority level mapping
    ROLE_AUTHORITY: dict[str, str] = {
        "admin": "CRITICAL",
        "manager": "HIGH",
        "viewer": "LOW",
    }

    # Impact level to required authority mapping
    IMPACT_AUTHORITY: dict[str, str] = {
        ImpactLevel.LOW: "LOW",
        ImpactLevel.MEDIUM: "MEDIUM",
        ImpactLevel.HIGH: "HIGH",
        ImpactLevel.CRITICAL: "CRITICAL",
    }

    # Authority hierarchy (higher index = higher authority)
    AUTHORITY_HIERARCHY: dict[str, int] = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service with a database session.

        Args:
            db_session: Async database session for queries
        """
        self._db = db_session

    def get_user_authority_level(self, user: User) -> str:
        """Get the user's approval authority level based on their role.

        Args:
            user: User domain object

        Returns:
            Authority level string: LOW, MEDIUM, HIGH, or CRITICAL

        Example:
            >>> service = ApprovalMatrixService(session)
            >>> authority = service.get_user_authority_level(admin_user)
            >>> print(authority)
            'CRITICAL'
        """
        # Map role to authority level
        authority = self.ROLE_AUTHORITY.get(user.role, "LOW")
        return authority

    def get_authority_for_impact(self, impact_level: str) -> str:
        """Get the required authority level for a given impact level.

        Args:
            impact_level: Financial impact level (LOW/MEDIUM/HIGH/CRITICAL)

        Returns:
            Required authority level string

        Raises:
            ValueError: If impact_level is invalid

        Example:
            >>> service = ApprovalMatrixService(session)
            >>> authority = service.get_authority_for_impact('HIGH')
            >>> print(authority)
            'HIGH'
        """
        if impact_level not in self.IMPACT_AUTHORITY:
            raise ValueError(
                f"Invalid impact level: {impact_level}. "
                f"Must be one of: {list(self.IMPACT_AUTHORITY.keys())}"
            )

        return self.IMPACT_AUTHORITY[impact_level]

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
        user_authority = self.get_user_authority_level(user)

        # Get required authority for this impact level
        required_authority = self.get_authority_for_impact(impact_level)

        # Compare authority levels using hierarchy
        user_level = self.AUTHORITY_HIERARCHY.get(user_authority, 0)
        required_level = self.AUTHORITY_HIERARCHY.get(required_authority, 0)

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
        required_authority = self.get_authority_for_impact(impact_level)

        # Find all users with sufficient authority
        eligible_roles = [
            role
            for role, authority in self.ROLE_AUTHORITY.items()
            if self.AUTHORITY_HIERARCHY.get(authority, 0)
            >= self.AUTHORITY_HIERARCHY.get(required_authority, 0)
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
            required_authority = self.get_authority_for_impact(impact_level)

        # Get current user's authority
        user_authority = self.get_user_authority_level(current_user)

        # Check if current user can approve
        can_approve = False
        if impact_level and current_user.is_active:
            user_level = self.AUTHORITY_HIERARCHY.get(user_authority, 0)
            required_level = (
                self.AUTHORITY_HIERARCHY.get(required_authority, 0)
                if required_authority
                else 0
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
