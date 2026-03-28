"""ProjectMember service - handles project-level role assignments.

Provides CRUD operations for managing user roles within projects.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.domain.project_member import ProjectMember


class ProjectMemberService:
    """Service for managing project member role assignments.

    Provides CRUD operations with project-specific queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: Async database session
        """
        self.session = session

    async def get(self, entity_id: UUID) -> ProjectMember | None:
        """Get entity by ID.

        Args:
            entity_id: UUID of the project member

        Returns:
            ProjectMember if found, None otherwise
        """
        return await self.session.get(ProjectMember, entity_id)

    async def create(self, **fields: object) -> ProjectMember:
        """Create new project member.

        Args:
            **fields: Field values for the new entity

        Returns:
            Created ProjectMember entity
        """
        member = ProjectMember(**fields)
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def update(self, entity_id: UUID, **updates: object) -> ProjectMember:
        """Update project member in place.

        Args:
            entity_id: UUID of the project member
            **updates: Field values to update

        Returns:
            Updated ProjectMember entity

        Raises:
            ValueError: If entity not found
        """
        member = await self.get(entity_id)
        if member is None:
            raise ValueError(f"ProjectMember with id {entity_id} not found")

        for key, value in updates.items():
            setattr(member, key, value)

        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def delete(self, entity_id: UUID) -> bool:
        """Hard delete project member.

        Args:
            entity_id: UUID of the project member

        Returns:
            True if deleted, False if not found
        """
        member = await self.get(entity_id)
        if member is None:
            return False

        await self.session.delete(member)
        await self.session.flush()
        return True

    async def get_by_user_and_project(
        self, user_id: UUID, project_id: UUID
    ) -> ProjectMember | None:
        """Get a project member by user_id and project_id.

        Args:
            user_id: UUID of the user
            project_id: UUID of the project

        Returns:
            ProjectMember if found, None otherwise
        """
        stmt = select(ProjectMember).where(
            ProjectMember.user_id == user_id,
            ProjectMember.project_id == project_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_project(
        self, project_id: UUID, skip: int = 0, limit: int = 1000
    ) -> list[ProjectMember]:
        """List all members of a project with pagination.

        Args:
            project_id: UUID of the project
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ProjectMember entities
        """
        stmt = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 1000
    ) -> list[ProjectMember]:
        """List all projects a user is a member of.

        Args:
            user_id: UUID of the user
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ProjectMember entities
        """
        stmt = (
            select(ProjectMember)
            .where(ProjectMember.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_details(self, member_id: UUID) -> ProjectMember | None:
        """Get a project member with related user and project details.

        Args:
            member_id: UUID of the project member

        Returns:
            ProjectMember with eager-loaded relationships, or None
        """
        stmt = (
            select(ProjectMember)
            .options(
                selectinload(ProjectMember.user),
                selectinload(ProjectMember.project),
                selectinload(ProjectMember.assigner),
            )
            .where(ProjectMember.id == member_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_project_with_details(
        self, project_id: UUID, skip: int = 0, limit: int = 1000
    ) -> list[ProjectMember]:
        """List all members of a project with related details.

        Args:
            project_id: UUID of the project
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ProjectMember entities with eager-loaded relationships
        """
        stmt = (
            select(ProjectMember)
            .options(
                selectinload(ProjectMember.user),
                selectinload(ProjectMember.project),
                selectinload(ProjectMember.assigner),
            )
            .where(ProjectMember.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def check_membership(
        self, user_id: UUID, project_id: UUID
    ) -> ProjectMember | None:
        """Check if a user is a member of a project.

        Args:
            user_id: UUID of the user
            project_id: UUID of the project

        Returns:
            ProjectMember if user is a member, None otherwise
        """
        return await self.get_by_user_and_project(user_id, project_id)

    async def remove_member(self, member_id: UUID) -> bool:
        """Remove a project member (hard delete).

        Args:
            member_id: UUID of the project member to remove

        Returns:
            True if removed, False if not found
        """
        return await self.delete(member_id)
