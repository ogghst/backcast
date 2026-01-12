"""ProjectService extending TemporalService for branchable entities.

Provides Project-specific operations on top of generic temporal service.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.enums import BranchMode
from app.core.versioning.service import TemporalService
from app.models.domain.project import Project
from app.models.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService(TemporalService[Project]):  # type: ignore[type-var,unused-ignore]
    """Service for Project entity operations.

    Extends TemporalService with project-specific methods.
    Supports full EVCS capabilities including branching.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Project, session)

    async def get_projects(
        self,
        skip: int = 0,
        limit: int = 100000,
        branch: str = "main",
        search: str | None = None,
        filters: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
        as_of: datetime | None = None,
    ) -> tuple[list[Project], int]:
        """Get all projects with pagination, search, and filters.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            branch: Branch name to filter by (default: "main")
            search: Search term to match against code and name (case-insensitive)
            filters: Filter string in format "column:value;column:value1,value2"
                     Example: "status:Active;budget:>100000"
            sort_field: Field name to sort by (e.g., "name", "code", "budget")
            sort_order: Sort order, either "asc" or "desc" (default: "asc")
            as_of: Optional timestamp for time-travel queries

        Returns:
            Tuple of (list of projects, total count matching filters)

        Raises:
            ValueError: If invalid filter field or sort field is provided

        Examples:
            >>> # Get active projects with budget > 100000, sorted by name
            >>> projects, total = await service.get_projects(
            ...     filters="status:Active",
            ...     sort_field="name",
            ...     sort_order="asc"
            ... )

            >>> # Search for projects containing "Alpha"
            >>> projects, total = await service.get_projects(
            ...     search="Alpha",
            ...     limit=20
            ... )
        """
        from typing import Any, cast

        from sqlalchemy import and_, func, or_

        from app.core.filtering import FilterParser

        # Base query: versions in specified branch, not deleted
        # Base query: versions in specified branch
        stmt = select(Project).where(Project.branch == branch)

        # Apply time-travel filter
        if as_of:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            # Get current version (open upper bound) and not deleted
            stmt = stmt.where(
                func.upper(cast(Any, Project).valid_time).is_(None),
                cast(Any, Project).deleted_at.is_(None),
            )

        # Apply search (across code and name)
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Project.code.ilike(search_term),
                    Project.name.ilike(search_term),
                )
            )

        # Apply filters
        if filters:
            # Define allowed filterable fields for security
            allowed_fields = ["status", "code", "name"]

            parsed_filters = FilterParser.parse_filters(filters)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, Project), parsed_filters, allowed_fields=allowed_fields
            )
            if filter_expressions:
                stmt = stmt.where(and_(*filter_expressions))

        # Get total count (before pagination)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply sorting
        if sort_field:
            # Validate sort field exists on model
            if not hasattr(Project, sort_field):
                raise ValueError(f"Invalid sort field: {sort_field}")

            column = getattr(Project, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            # Default sort by valid_time descending
            stmt = stmt.order_by(cast(Any, Project).valid_time.desc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        # Execute query
        result = await self.session.execute(stmt)
        projects = list(result.scalars().all())

        return projects, total

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
        self,
        project_in: ProjectCreate,
        actor_id: UUID,
        control_date: datetime | None = None
    ) -> Project:
        """Create new project using CreateVersionCommand."""
        project_data = project_in.model_dump(exclude_unset=True)
        project_data.pop("control_date", None)

        # Use provided project_id (for seeding) or generate new one
        root_id = project_in.project_id or uuid4()
        project_data["project_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=Project,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **project_data,
        )
        return await cmd.execute(self.session)

    async def update_project(
        self,
        project_id: UUID,
        project_in: ProjectUpdate,
        actor_id: UUID,
        control_date: datetime | None = None
    ) -> Project:
        """Update project using UpdateVersionCommand."""
        # Filter None values from update data
        update_data = project_in.model_dump(exclude_unset=True)
        update_data.pop("control_date", None)

        cmd = UpdateVersionCommand(
            entity_class=Project,  # type: ignore[type-var,unused-ignore]
            root_id=project_id,
            actor_id=actor_id,
            control_date=control_date,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def delete_project(
        self,
        project_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None
    ) -> Project:
        """Soft delete project using SoftDeleteCommand."""
        cmd = SoftDeleteCommand(
            entity_class=Project,  # type: ignore[type-var,unused-ignore]
            root_id=project_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        return await cmd.execute(self.session)

    async def get_project_history(self, project_id: UUID) -> list[Project]:
        """Get all versions of a project by root project_id (with creator name)."""
        return await self.get_history(project_id)

    async def get_project_as_of(
        self,
        project_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> Project | None:
        """Get project as it was at specific timestamp.

        Provides System Time Travel semantics for single-entity queries.
        Uses STRICT mode by default (only searches in specified branch).
        Use BranchMode.MERGE to fall back to main branch if not found.

        Args:
            project_id: The unique identifier of the project
            as_of: Timestamp to query (historical state)
            branch: Branch name to query (default: "main")
            branch_mode: Resolution mode for branches
                - None/STRICT: Only return from specified branch (default)
                - MERGE: Fall back to main if not found on branch

        Returns:
            Project if found at the specified timestamp, None otherwise

        Example:
            >>> # Get project as of January 1st
            >>> from datetime import datetime
            >>> as_of = datetime(2026, 1, 1, 12, 0, 0)
            >>> project = await service.get_project_as_of(
            ...     project_id=uuid,
            ...     as_of=as_of
            ... )
        """
        return await self.get_as_of(project_id, as_of, branch, branch_mode)

    async def get_project_branches(self, project_id: UUID) -> list[str]:
        """Get all branches for a project.

        Returns:
            List of branch names, always including "main" plus any
            change order branches (co-{code}) for this project.
        """
        from app.models.domain.change_order import ChangeOrder

        # Always include main branch
        branches = ["main"]

        # Get all unique change order branches for this project
        # CO branches are named co-{code}, we can get them from the branch column
        stmt = select(ChangeOrder.branch).where(
            ChangeOrder.project_id == project_id,
            ChangeOrder.branch != "main",  # Exclude main branch
        ).distinct()

        result = await self.session.execute(stmt)
        co_branches = [row[0] for row in result.all()]

        branches.extend(co_branches)
        return branches
