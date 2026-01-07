"""ProjectService extending TemporalService for branchable entities.

Provides Project-specific operations on top of generic temporal service.
"""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.service import TemporalService
from app.models.domain.project import Project
from app.models.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService(TemporalService[Project]):  # type: ignore[type-var]
    """Service for Project entity operations.

    Extends TemporalService with project-specific methods.
    Supports full EVCS capabilities including branching.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Project, session)

    async def get_projects(
        self, skip: int = 0, limit: int = 100, branch: str = "main"
    ) -> list[Project]:
        """Get all projects with pagination (filtered by branch)."""
        from typing import Any, cast

        from sqlalchemy import func

        stmt = (
            select(Project)
            .where(
                Project.branch == branch,
                func.upper(cast(Any, Project).valid_time).is_(None),
                cast(Any, Project).deleted_at.is_(None),
            )
            .order_by(cast(Any, Project).valid_time.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_code(self, code: str, branch: str = "main") -> Project | None:
        """Get project by code (current version in specified branch)."""
        from typing import Any, cast

        from sqlalchemy import func

        stmt = (
            select(Project)
            .where(
                Project.code == code,
                Project.branch == branch,
                func.upper(cast(Any, Project).valid_time).is_(None),
                cast(Any, Project).deleted_at.is_(None),
            )
            .order_by(cast(Any, Project).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_project(
        self, project_in: ProjectCreate, actor_id: UUID
    ) -> Project:
        """Create new project using CreateVersionCommand."""
        project_data = project_in.model_dump()

        # Generate root project_id
        root_id = uuid4()
        project_data["project_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=Project,  # type: ignore[type-var]
            root_id=root_id,
            actor_id=actor_id,
            **project_data,
        )
        return await cmd.execute(self.session)

    async def update_project(
        self, project_id: UUID, project_in: ProjectUpdate, actor_id: UUID
    ) -> Project:
        """Update project using UpdateVersionCommand."""
        # Filter None values from update data
        update_data = project_in.model_dump(exclude_unset=True)

        cmd = UpdateVersionCommand(
            entity_class=Project,  # type: ignore[type-var]
            root_id=project_id,
            actor_id=actor_id,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def delete_project(self, project_id: UUID, actor_id: UUID) -> Project:
        """Soft delete project using SoftDeleteCommand."""
        cmd = SoftDeleteCommand(
            entity_class=Project,  # type: ignore[type-var]
            root_id=project_id,
            actor_id=actor_id,
        )
        return await cmd.execute(self.session)

    async def get_project_history(self, project_id: UUID) -> list[Project]:
        """Get all versions of a project by root project_id (with creator name)."""
        return await self.get_history(project_id)

