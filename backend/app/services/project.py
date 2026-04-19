"""ProjectService extending TemporalService for branchable entities.

Provides Project-specific operations on top of generic temporal service.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.commands import UpdateCommand
from app.core.branching.service import BranchableService
from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
)
from app.core.versioning.enums import BranchMode
from app.models.domain.cost_element import CostElement
from app.models.domain.project import Project
from app.models.domain.user import User
from app.models.domain.wbe import WBE
from app.models.schemas.project import ProjectCreate, ProjectUpdate

if TYPE_CHECKING:
    from app.models.schemas.branch import BranchPublic


class ProjectService(BranchableService[Project]):  # type: ignore[type-var,unused-ignore]
    """Service for Project entity operations.

    Extends TemporalService with project-specific methods.
    Supports full EVCS capabilities including branching.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Project, session)

    async def get_as_of(
        self,
        entity_id: UUID,
        as_of: datetime | None = None,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> Project | None:
        """Override parent to compute and attach budget after fetch."""
        project = await super().get_as_of(
            entity_id=entity_id,
            as_of=as_of,
            branch=branch,
            branch_mode=branch_mode,
        )
        if project:
            project.budget = await self._compute_project_budget(
                entity_id, branch=branch
            )
        return project

    async def _compute_project_budget(
        self, project_id: UUID, branch: str = "main"
    ) -> Decimal:
        """Compute project budget as sum of all cost element budgets.

        Joins WBE + CostElement to sum budget_amount across all WBEs
        belonging to this project on the specified branch.

        Args:
            project_id: Root project ID
            branch: Branch name (default: "main")

        Returns:
            Sum of all cost element budgets in the project
        """
        from typing import cast

        stmt = (
            select(func.coalesce(func.sum(CostElement.budget_amount), Decimal("0")))
            .join(WBE, CostElement.wbe_id == WBE.wbe_id)
            .where(
                WBE.project_id == project_id,
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
                CostElement.branch == branch,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar() or Decimal("0")

    async def _populate_computed_budgets(
        self, projects: list[Project], branch: str = "main"
    ) -> list[Project]:
        """Populate computed budget for a list of projects.

        Uses a batch query to compute all project budgets in one SQL call
        to avoid N+1 queries.

        Args:
            projects: List of Project objects to populate
            branch: Branch name for budget computation

        Returns:
            Same list with budget populated on each Project
        """
        from typing import cast

        if not projects:
            return projects

        # Batch query: compute budget for all projects at once
        stmt = (
            select(
                WBE.project_id,
                func.coalesce(func.sum(CostElement.budget_amount), Decimal("0")).label(
                    "total_budget"
                ),
            )
            .join(CostElement, CostElement.wbe_id == WBE.wbe_id)
            .where(
                WBE.project_id.in_([p.project_id for p in projects]),
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
                CostElement.branch == branch,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .group_by(WBE.project_id)
        )

        result = await self.session.execute(stmt)
        budget_map: dict[UUID, Decimal] = {row[0]: row[1] for row in result.all()}

        for project in projects:
            project.budget = budget_map.get(project.project_id, Decimal("0"))

        return projects

    async def get_projects(
        self,
        skip: int = 0,
        limit: int = 100000,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGE,
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
            branch_mode: Branch resolution mode (default: MERGE)
                - MERGE: Combine current branch with main (current branch takes precedence)
                - STRICT: Only return entities from current branch
            search: Search term to match against code and name (case-insensitive)
            filters: Filter string in format "column:value;column:value1,value2"
                     Example: "status:Active;code:PRJ"
            sort_field: Field name to sort by (e.g., "name", "code")
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
        from typing import cast

        from sqlalchemy import and_, func, or_

        from app.core.filtering import FilterParser
        from app.models.domain.user import User

        # Creator lookup subquery - get the most recent version of each user
        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )

        # Base query: versions in specified branch(es) with creator name
        stmt = select(Project, creator_subq.c.full_name.label("created_by_name"))
        stmt = stmt.outerjoin(
            creator_subq,
            cast(Any, Project).created_by == creator_subq.c.user_id,
        )

        # Apply branch mode filter (STRICT vs MERGE)
        stmt = self._apply_branch_mode_filter(
            stmt, branch=branch, branch_mode=branch_mode, as_of=as_of
        )

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
            # Validate sort field is a mapped column (not computed attributes)
            if not hasattr(Project, sort_field):
                raise ValueError(f"Invalid sort field: {sort_field}")

            column = getattr(Project, sort_field)
            if not hasattr(column, "desc"):
                raise ValueError(f"Invalid sort field: {sort_field}")
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
        projects = []
        for row in result.all():
            project = row[0]
            created_by_name = row[1]
            project.created_by_name = created_by_name

            # Populate created_at from transaction_time lower bound
            if hasattr(project, "transaction_time") and project.transaction_time:
                if hasattr(project.transaction_time, "lower"):
                    project.created_at = project.transaction_time.lower

            projects.append(project)

        # Populate computed budgets for all projects (batch query)
        await self._populate_computed_budgets(projects, branch=branch)

        return projects, total

    async def get_by_code(self, code: str, branch: str = "main") -> Project | None:
        """Get project by code (current version in specified branch)."""
        from typing import cast

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
        project = result.scalar_one_or_none()
        if project:
            project.budget = await self._compute_project_budget(
                project.project_id, branch=branch
            )
        return project

    async def create_project(
        self,
        project_in: ProjectCreate,
        actor_id: UUID,
    ) -> Project:
        """Create new project using CreateVersionCommand."""
        project_data = project_in.model_dump(exclude_unset=True)

        # Extract control_date from schema if present (for seeding/time-travel)
        control_date = getattr(project_in, "control_date", None)

        # Remove control_date from data to avoid duplicate kwarg error
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
        project = await cmd.execute(self.session)

        await self._apply_project_creation_defaults(root_id, actor_id)

        await self._populate_project_metadata_from_db(project)
        await self._populate_project_metadata_from_db(project)

        # New projects have no cost elements, budget is 0
        project.budget = Decimal("0")

        return project

    async def update_project(
        self,
        project_id: UUID,
        project_in: ProjectUpdate,
        actor_id: UUID,
    ) -> Project:
        # Extract control_date and branch from schema
        control_date = project_in.control_date
        branch = project_in.branch or "main"

        # Filter None values from update data
        update_data = project_in.model_dump(exclude_unset=True)
        update_data.pop("control_date", None)
        update_data.pop("branch", None)

        cmd = UpdateCommand(
            entity_class=Project,  # type: ignore[type-var,unused-ignore]
            root_id=project_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            updates=update_data,
        )
        project = await cmd.execute(self.session)

        # Populate created_by_name and created_at
        await self._populate_project_metadata_from_db(project)

        # Populate computed budget
        project.budget = await self._compute_project_budget(project_id, branch=branch)

        return project

    async def delete_project(
        self, project_id: UUID, actor_id: UUID, control_date: datetime | None = None
    ) -> Project:
        """Soft delete project using SoftDeleteCommand."""
        cmd = SoftDeleteCommand(
            entity_class=Project,  # type: ignore[type-var,unused-ignore]
            root_id=project_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        project = await cmd.execute(self.session)

        # Populate created_by_name and created_at
        await self._populate_project_metadata_from_db(project)

        # Populate computed budget
        project.budget = await self._compute_project_budget(project_id)

        return project

    async def get_project_history(self, project_id: UUID) -> list[Project]:
        """Get all versions of a project by root project_id (with creator name)."""
        versions = await self.get_history(project_id)
        for v in versions:
            v.budget = Decimal("0")
        return versions

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

        project = await self.get_as_of(project_id, as_of, branch, branch_mode)
        if project:
            await self._populate_project_metadata_from_db(project)
        return project

    async def _populate_project_metadata_from_db(self, project: Project) -> None:
        """Populate created_by_name and created_at for a single project.

        Performs a separate query to fetch the creator's name.

        Args:
            project: The project entity to populate
        """
        from typing import cast

        if not project.created_by:
            return

        # Query the user table to get the creator's name
        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )

        stmt = select(creator_subq.c.full_name).where(
            creator_subq.c.user_id == project.created_by
        )

        result = await self.session.execute(stmt)
        creator_name = result.scalar_one_or_none()
        project.created_by_name = creator_name  # type: ignore

        # Populate created_at from transaction_time lower bound
        if hasattr(project, "transaction_time") and project.transaction_time:
            if hasattr(project.transaction_time, "lower"):
                project.created_at = project.transaction_time.lower  # type: ignore

    async def _apply_project_creation_defaults(
        self, project_id: UUID, actor_id: UUID
    ) -> None:
        """Apply default configurations to a newly created project."""
        from app.core.project_defaults import apply_project_creation_defaults
        from app.services.project_budget_settings_service import (
            ProjectBudgetSettingsService,
        )

        budget_service = ProjectBudgetSettingsService(self.session)
        await apply_project_creation_defaults(
            project_id=project_id,
            actor_id=actor_id,
            budget_settings_service=budget_service,
        )

    async def get_project_branches(
        self, project_id: UUID, as_of: datetime | None = None
    ) -> list["BranchPublic"]:
        """Get all branches for a project.

        Returns:
            List of BranchPublic objects, always including "main" plus any
            change order branches (BR-{code}) for this project.

        Requires read permission.
        """
        from typing import cast

        from sqlalchemy import func

        from app.models.domain.branch import Branch
        from app.models.domain.change_order import ChangeOrder
        from app.models.schemas.branch import BranchPublic

        # Always include main branch
        branches: list[BranchPublic] = [
            BranchPublic(name="main", type="main", is_default=True)
        ]

        # Get all branches for this project from the branches table
        stmt = select(Branch).where(Branch.project_id == project_id)

        if as_of:
            # Time travel filter
            # Cast as_of to TIMESTAMP(timezone=True)
            from sqlalchemy import cast as sql_cast
            from sqlalchemy import or_
            from sqlalchemy.dialects.postgresql import TIMESTAMP

            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            stmt = stmt.where(
                Branch.valid_time.op("@>")(as_of_tstz),
                func.lower(Branch.valid_time) <= as_of_tstz,
                or_(Branch.deleted_at.is_(None), Branch.deleted_at > as_of_tstz),
            )
        else:
            # Current versions
            stmt = stmt.where(
                func.upper(Branch.valid_time).is_(None),
                Branch.deleted_at.is_(None),
            )

        stmt = stmt.order_by(func.lower(Branch.valid_time).desc())

        result = await self.session.execute(stmt)
        branch_entities = result.scalars().all()

        for branch_entity in branch_entities:
            # Skip main branch as it's already added
            if branch_entity.name == "main":
                continue

            # For change order branches, fetch the current status from ChangeOrder
            change_order_status = None
            change_order_code = None
            change_order_id = None

            if branch_entity.type == "change_order":
                # Extract code from branch name (e.g., "BR-CO-2026-001" -> "CO-2026-001")
                code = branch_entity.name.replace("BR-", "", 1)

                # Get the current change order on main branch to get its status
                co_stmt = select(ChangeOrder).where(
                    ChangeOrder.project_id == project_id,
                    ChangeOrder.code == code,
                    ChangeOrder.branch == "main",
                )

                if as_of:
                    # Time travel check for CO
                    co_stmt = co_stmt.where(
                        cast(Any, ChangeOrder).valid_time.op("@>")(as_of_tstz),
                        func.lower(cast(Any, ChangeOrder).valid_time) <= as_of_tstz,
                        or_(
                            cast(Any, ChangeOrder).deleted_at.is_(None),
                            cast(Any, ChangeOrder).deleted_at > as_of_tstz,
                        ),
                    )
                else:
                    co_stmt = co_stmt.where(
                        func.upper(cast(Any, ChangeOrder).valid_time).is_(None),
                        cast(Any, ChangeOrder).deleted_at.is_(None),
                    )

                co_stmt = co_stmt.order_by(
                    cast(Any, ChangeOrder).valid_time.desc()
                ).limit(1)
                co_result = await self.session.execute(co_stmt)
                co = co_result.scalar_one_or_none()

                if co:
                    change_order_status = co.status
                    change_order_code = co.code
                    change_order_id = co.change_order_id

            branches.append(
                BranchPublic(
                    branch_id=branch_entity.branch_id,
                    name=branch_entity.name,
                    type=branch_entity.type,
                    is_default=False,
                    created_at=branch_entity.valid_time.lower,
                    change_order_id=change_order_id,
                    change_order_code=change_order_code,
                    change_order_status=change_order_status,
                )
            )

        return branches

    async def get_recently_updated(
        self,
        user_id: UUID | None = None,
        limit: int = 10,
        branch: str = "main",
    ) -> list[Project]:
        """Get recently updated projects, optionally filtered by user.

        Args:
            user_id: Optional user ID to filter by (only projects updated by this user)
            limit: Maximum number of projects to return
            branch: Branch name to query (default: "main")

        Returns:
            List of recently updated projects ordered by transaction_time descending
        """
        from typing import cast

        from sqlalchemy import desc

        stmt = select(Project).where(Project.branch == branch)

        if user_id:
            stmt = stmt.where(cast(Any, Project).created_by == user_id)

        # Get current versions (not deleted)
        stmt = stmt.where(
            func.upper(cast(Any, Project).valid_time).is_(None),
            cast(Any, Project).deleted_at.is_(None),
        )

        # Order by transaction_time descending (most recent first)
        stmt = stmt.order_by(desc(cast(Any, Project).transaction_time)).limit(limit)

        result = await self.session.execute(stmt)
        projects = list(result.scalars().all())

        # Populate computed budgets (batch query)
        await self._populate_computed_budgets(projects, branch=branch)

        return projects
