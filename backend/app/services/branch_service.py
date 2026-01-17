"""Service for Branch entity operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.branch import Branch


class BranchService:
    """Service for Branch CRUD operations and lock/unlock functionality.

    Provides methods for:
    - Locking branches (prevent writes)
    - Unlocking branches (allow writes)
    - Retrieving branches by composite key (name, project_id)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize BranchService with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def lock(self, name: str, project_id: UUID) -> Branch:
        """Lock a branch to prevent writes.

        Args:
            name: Branch name
            project_id: Project ID (composite key component)

        Returns:
            The locked Branch entity

        Raises:
            NoResultFound: If branch doesn't exist
        """
        branch = await self.get_by_name_and_project(name, project_id)
        branch.locked = True
        await self.session.commit()
        await self.session.refresh(branch)
        return branch

    async def unlock(self, name: str, project_id: UUID) -> Branch:
        """Unlock a branch to allow writes.

        Args:
            name: Branch name
            project_id: Project ID (composite key component)

        Returns:
            The unlocked Branch entity

        Raises:
            NoResultFound: If branch doesn't exist
        """
        branch = await self.get_by_name_and_project(name, project_id)
        branch.locked = False
        await self.session.commit()
        await self.session.refresh(branch)
        return branch

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
            Branch.deleted_at.is_(None),  # Only return non-deleted branches
        )
        result = await self.session.execute(stmt)
        branch = result.scalar_one()

        if branch is None:
            raise NoResultFound(
                f"Branch not found: name={name}, project_id={project_id}"
            )

        return branch
