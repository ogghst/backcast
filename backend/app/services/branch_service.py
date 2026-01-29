"""Service for Branch entity operations."""

from uuid import UUID

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.service import TemporalService
from app.models.domain.branch import Branch


class BranchService(TemporalService[Branch]):
    """Service for Branch CRUD operations and lock/unlock functionality.

    Provides methods for:
    - Locking branches (prevent writes)
    - Unlocking branches (allow writes)
    - Retrieving branches by composite key (name, project_id)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize BranchService with database session."""
        super().__init__(Branch, session)

    async def lock(self, name: str, project_id: UUID, actor_id: UUID) -> Branch:
        """Lock a branch to prevent writes.
        
        Creates a new version of the branch with locked=True.

        Args:
            name: Branch name
            project_id: Project ID (composite key component)
            actor_id: User locking the branch
            
        Returns:
            The locked Branch entity

        Raises:
            NoResultFound: If branch doesn't exist
        """
        branch = await self.get_by_name_and_project(name, project_id)
        
        # Use UpdateVersionCommand to create a new version with locked status
        from app.core.versioning.commands import UpdateVersionCommand
        
        current_actor = actor_id
        
        cmd = UpdateVersionCommand(
            entity_class=Branch,
            root_id=branch.branch_id,
            actor_id=current_actor,
            locked=True
        )
        return await cmd.execute(self.session)

    async def unlock(self, name: str, project_id: UUID, actor_id: UUID) -> Branch:
        """Unlock a branch to allow writes.
        
        Creates a new version of the branch with locked=False.

        Args:
            name: Branch name
            project_id: Project ID (composite key component)
            actor_id: User unlocking the branch
            
        Returns:
            The unlocked Branch entity

        Raises:
            NoResultFound: If branch doesn't exist
        """
        branch = await self.get_by_name_and_project(name, project_id)
        
        # Use UpdateVersionCommand to create a new version with unlocked status
        from app.core.versioning.commands import UpdateVersionCommand
        
        current_actor = actor_id
        
        cmd = UpdateVersionCommand(
            entity_class=Branch,
            root_id=branch.branch_id,
            actor_id=current_actor,
            locked=False
        )
        return await cmd.execute(self.session)

    async def get_by_name_and_project(self, name: str, project_id: UUID) -> Branch:
        """Get a branch by composite key (name, project_id).

        Args:
            name: Branch name
            project_id: Project ID (composite key component)

        Returns:
            The Branch entity

        Raises:
            NoResultFound: If branch doesn't exist
        """
        stmt = select(Branch).where(
            Branch.name == name,
            Branch.project_id == project_id,
            Branch.deleted_at.is_(None),
            func.upper(Branch.valid_time).is_(None),  # Only current versions
        )
        result = await self.session.execute(stmt)
        branch = result.scalar_one_or_none()
        
        if branch is None:
            raise NoResultFound(
                f"Branch not found: name={name}, project_id={project_id}"
            )
            
        return branch

    async def get_as_of(
        self, name: str, project_id: UUID, as_of: datetime
    ) -> Branch | None:
        """Get branch state at specific timestamp.

        Args:
            name: Branch name
            project_id: Project ID
            as_of: Timestamp to query

        Returns:
            Branch entity at that time or None
        """
        stmt = select(Branch).where(
            Branch.name == name,
            Branch.project_id == project_id,
        )
        stmt = self._apply_bitemporal_filter_for_time_travel(stmt, as_of)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_branches_as_of(
        self, project_id: UUID, as_of: datetime | None = None
    ) -> list[Branch]:
        """List all branches for a project at specific timestamp.

        Args:
            project_id: Project ID
            as_of: Optional timestamp (defaults to current)

        Returns:
            List of branches valid at that time
        """
        stmt = select(Branch).where(Branch.project_id == project_id)

        if as_of:
            stmt = self._apply_bitemporal_filter_for_time_travel(stmt, as_of)
        else:
            # Current versions
            stmt = stmt.where(
                func.upper(Branch.valid_time).is_(None), Branch.deleted_at.is_(None)
            )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
