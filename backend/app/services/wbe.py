"""WBEService extending TemporalService for branchable entities.

Provides WBE-specific operations with parent-child project relationship.
"""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.service import TemporalService
from app.models.domain.user import User
from app.models.domain.wbe import WBE
from app.models.schemas.wbe import WBECreate, WBEUpdate


class WBEService(TemporalService[WBE]):  # type: ignore[type-var]
    """Service for WBE entity operations.

    Extends TemporalService with WBE-specific methods including
    project filtering and hierarchical queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WBE, session)

    async def _resolve_parent_names(self, query_results: list[Any]) -> list[WBE]:
        """Helper to resolve parent names for a list of WBE results.
        
        Args:
            query_results: List of Row objects (WBE, parent_name) or WBE objects
            
        Returns:
            List of WBE objects with parent_name attached
        """
        resolved = []
        for item in query_results:
            # SQLAlchemy Row objects behave like tuples but may not be instances of tuple type
            # They also have a __composite_values__ or other ways to check, but checking
            # for length and attribute access is safer.
            if hasattr(item, "__iter__") and not isinstance(item, (str, bytes)):
                # Convert to list to ensure we can unpack if it's a Row
                item_list = list(item)
                if len(item_list) >= 2:
                    wbe, parent_name = item_list[0], item_list[1]
                    wbe.parent_name = parent_name
                    resolved.append(wbe)
                elif len(item_list) == 1:
                    resolved.append(item_list[0])
                else:
                    resolved.append(item)
            else:
                resolved.append(item)
        return resolved

    def _get_base_stmt(self) -> Any:
        """Get base select statement with parent name join."""
        from typing import Any, cast

        from sqlalchemy import func

        Parent = aliased(WBE, name="parent_wbe")

        # Subquery for current parent versions to avoid multiple rows
        parent_subq = (
            select(Parent.wbe_id, Parent.name)
            .where(
                func.upper(cast(Any, Parent).valid_time).is_(None),
                cast(Any, Parent).deleted_at.is_(None)
            )
            .subquery("parent_lookup")
        )

        return (
            select(WBE, parent_subq.c.name.label("parent_name"))
            .outerjoin(parent_subq, WBE.parent_wbe_id == parent_subq.c.wbe_id)
        )

    async def get_wbes(
        self,
        skip: int = 0,
        limit: int = 100,
        branch: str = "main",
        search: str | None = None,
        filters: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[WBE], int]:
        """Get all WBEs with pagination, search, and filters.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            branch: Branch name to filter by (default: "main")
            search: Search term to match against code and name (case-insensitive)
            filters: Filter string in format "column:value;column:value1,value2"
                     Example: "level:1,2;code:1.1"
            sort_field: Field name to sort by (e.g., "name", "code", "level")
            sort_order: Sort order, either "asc" or "desc" (default: "asc")

        Returns:
            Tuple of (list of WBEs with parent_name, total count matching filters)

        Raises:
            ValueError: If invalid filter field or sort field is provided
        """
        from typing import Any, cast

        from sqlalchemy import and_, func, or_

        from app.core.filtering import FilterParser

        # Base query with parent name join
        stmt = self._get_base_stmt().where(
            WBE.branch == branch,
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )

        # Apply search (across code and name)
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    WBE.code.ilike(search_term),
                    WBE.name.ilike(search_term),
                )
            )

        # Apply filters
        if filters:
            # Define allowed filterable fields for security
            allowed_fields = ["level", "code", "name"]

            parsed_filters = FilterParser.parse_filters(filters)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                WBE, parsed_filters, allowed_fields=allowed_fields
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
            if not hasattr(WBE, sort_field):
                raise ValueError(f"Invalid sort field: {sort_field}")

            column = getattr(WBE, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            # Default sort by valid_time descending
            stmt = stmt.order_by(cast(Any, WBE).valid_time.desc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        # Execute query
        result = await self.session.execute(stmt)
        wbes = await self._resolve_parent_names(result.all())

        return wbes, total

    async def get_by_project(self, project_id: UUID, branch: str = "main") -> list[WBE]:
        """Get all WBEs for a specific project (current versions)."""
        from typing import Any, cast

        from sqlalchemy import func

        stmt = (
            self._get_base_stmt()
            .where(
                WBE.project_id == project_id,
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .order_by(WBE.code)
        )
        result = await self.session.execute(stmt)
        return await self._resolve_parent_names(result.all())

    async def get_by_parent(
        self,
        project_id: UUID | None = None,
        parent_wbe_id: UUID | None = None,
        branch: str = "main",
    ) -> list[WBE]:
        """Get WBEs filtered by parent_wbe_id.
        
        Args:
            project_id: Optional project filter
            parent_wbe_id: Parent WBE ID. None means root WBEs (parent_wbe_id IS NULL)
            branch: Branch name
            
        Returns:
            List of WBEs matching the parent filter
        """
        from typing import Any, cast

        from sqlalchemy import func

        # Build base query
        conditions = [
            WBE.branch == branch,
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        ]

        # Add project filter if provided
        if project_id:
            conditions.append(WBE.project_id == project_id)

        # Add parent filter
        if parent_wbe_id is None:
            # Query for root WBEs (parent_wbe_id IS NULL)
            conditions.append(cast(Any, WBE).parent_wbe_id.is_(None))
        else:
            # Query for children of specific parent
            conditions.append(WBE.parent_wbe_id == parent_wbe_id)

        stmt = self._get_base_stmt().where(*conditions).order_by(WBE.code)
        result = await self.session.execute(stmt)
        return await self._resolve_parent_names(result.all())

    async def get_by_code(
        self, code: str, project_id: UUID, branch: str = "main"
    ) -> WBE | None:
        """Get WBE by code within a project (current version)."""
        from typing import Any, cast

        from sqlalchemy import func

        stmt = (
            self._get_base_stmt()
            .where(
                WBE.code == code,
                WBE.project_id == project_id,
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        resolved = await self._resolve_parent_names(result.all())
        return resolved[0] if resolved else None

    async def create_wbe(self, wbe_in: WBECreate, actor_id: UUID) -> WBE:
        """Create new WBE using CreateVersionCommand."""
        wbe_data = wbe_in.model_dump()

        # Generate root wbe_id
        root_id = uuid4()
        wbe_data["wbe_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=WBE,  # type: ignore[type-var]
            root_id=root_id,
            actor_id=actor_id,
            **wbe_data,
        )
        return await cmd.execute(self.session)

    async def update_wbe(self, wbe_id: UUID, wbe_in: WBEUpdate, actor_id: UUID) -> WBE:
        """Update WBE using UpdateVersionCommand."""
        update_data = wbe_in.model_dump(exclude_unset=True)

        cmd = UpdateVersionCommand(
            entity_class=WBE,  # type: ignore[type-var]
            root_id=wbe_id,
            actor_id=actor_id,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def delete_wbe(self, wbe_id: UUID, actor_id: UUID) -> WBE:
        """Soft delete WBE with cascade to children.
        
        Deletes the WBE and all its descendants recursively.
        Returns the root WBE that was deleted.
        
        Args:
            wbe_id: Root WBE ID to delete
            actor_id: User performing the delete
            
        Returns:
            The deleted WBE (root)
            
        Raises:
            ValueError: If WBE not found
        """


        # First, check if WBE exists and get current children count
        wbe = await self.get_by_root_id(wbe_id)
        if not wbe:
            raise ValueError(f"WBE with id {wbe_id} not found")

        # Get all descendants (direct children + nested)
        descendants = await self._get_all_descendants(wbe_id, wbe.branch)

        # Soft-delete all descendants first (bottom-up to avoid FK issues)
        for descendant in reversed(descendants):  # Reverse to delete deepest first
            cmd = SoftDeleteCommand(
                entity_class=WBE,  # type: ignore[type-var]
                root_id=descendant.wbe_id,
                actor_id=actor_id,
            )
            await cmd.execute(self.session)

        # Finally, soft-delete the root WBE itself
        cmd = SoftDeleteCommand(
            entity_class=WBE,  # type: ignore[type-var]
            root_id=wbe_id,
            actor_id=actor_id,
        )
        return await cmd.execute(self.session)

    async def _get_all_descendants(
        self, parent_wbe_id: UUID, branch: str = "main"
    ) -> list[WBE]:
        """Recursively get all descendants of a WBE using recursive CTE.
        
        Args:
            parent_wbe_id: Root WBE ID to get descendants for
            branch: Branch name
            
        Returns:
            List of all descendant WBEs (ordered depth-first)
        """
        from typing import Any, cast

        from sqlalchemy import func, literal_column, select
        from sqlalchemy.orm import aliased

        # Build recursive CTE to get all descendants
        # Base case: direct children
        wbe_cte = (
            select(
                WBE.id,
                WBE.wbe_id,
                WBE.code,
                WBE.name,
                WBE.parent_wbe_id,
                literal_column("1").label("depth"),  # Depth 1 = direct children
            )
            .where(
                WBE.parent_wbe_id == parent_wbe_id,
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .cte(name="wbe_descendants", recursive=True)
        )

        # Recursive case: children of children
        wbe_alias = aliased(WBE, name="wbe_child")
        wbe_cte = wbe_cte.union_all(
            select(
                wbe_alias.id,
                wbe_alias.wbe_id,
                wbe_alias.code,
                wbe_alias.name,
                wbe_alias.parent_wbe_id,
                (wbe_cte.c.depth + 1).label("depth"),
            ).where(
                wbe_alias.parent_wbe_id == wbe_cte.c.wbe_id,
                wbe_alias.branch == branch,
                func.upper(cast(Any, wbe_alias).valid_time).is_(None),
                cast(Any, wbe_alias).deleted_at.is_(None),
            )
        )

        # Execute CTE query ordered by depth (parents before children)
        descendants_stmt = select(wbe_cte).order_by(wbe_cte.c.depth.asc())
        descendants_result = await self.session.execute(descendants_stmt)
        descendant_rows = descendants_result.all()

        # Fetch full WBE objects for each descendant
        descendant_list = []
        for row in descendant_rows:
            descendant = await self.get_by_root_id(row.wbe_id)
            if descendant:
                descendant_list.append(descendant)

        return descendant_list

    async def get_children_count(self, wbe_id: UUID, branch: str = "main") -> int:
        """Get count of direct children for a WBE.
        
        Useful for UI to show children count indicator.
        
        Args:
            wbe_id: Parent WBE ID
            branch: Branch name
            
        Returns:
            Count of direct children
        """
        from typing import Any, cast

        from sqlalchemy import func, select

        stmt = (
            select(func.count())
            .select_from(WBE)
            .where(
                WBE.parent_wbe_id == wbe_id,
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


    async def get_breadcrumb(self, wbe_id: UUID) -> dict:
        """Get breadcrumb trail for a WBE including project and all ancestors.
        
        Uses recursive CTE to efficiently fetch the entire ancestor chain in a single query.
        
        Args:
            wbe_id: Root WBE ID
            
        Returns:
            Dict with 'project' and 'wbe_path' keys
            
        Raises:
            ValueError: If WBE not found
        """
        from typing import Any, cast

        from sqlalchemy import func, literal_column, select
        from sqlalchemy.orm import aliased

        from app.models.domain.project import Project

        # First, get the current WBE
        current_wbe = await self.get_by_root_id(wbe_id)
        if not current_wbe:
            raise ValueError(f"WBE with id {wbe_id} not found")

        # Get the project
        project_stmt = (
            select(Project)
            .where(
                Project.project_id == current_wbe.project_id,
                Project.branch == current_wbe.branch,
                func.upper(cast(Any, Project).valid_time).is_(None),
                cast(Any, Project).deleted_at.is_(None),
            )
            .limit(1)
        )
        project_result = await self.session.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {current_wbe.project_id} not found")

        # Build recursive CTE to get all ancestors
        # Base case: current WBE
        wbe_cte = (
            select(
                WBE.id,
                WBE.wbe_id,
                WBE.code,
                WBE.name,
                WBE.parent_wbe_id,
                literal_column("0").label("depth"),  # Depth 0 is the current WBE
            )
            .where(
                WBE.wbe_id == wbe_id,
                WBE.branch == current_wbe.branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .cte(name="wbe_ancestors", recursive=True)
        )

        # Recursive case: get parent WBEs
        wbe_alias = aliased(WBE, name="wbe_parent")
        wbe_cte = wbe_cte.union_all(
            select(
                wbe_alias.id,
                wbe_alias.wbe_id,
                wbe_alias.code,
                wbe_alias.name,
                wbe_alias.parent_wbe_id,
                (wbe_cte.c.depth + 1).label("depth"),
            ).where(
                wbe_alias.wbe_id == wbe_cte.c.parent_wbe_id,
                wbe_alias.branch == current_wbe.branch,
                func.upper(cast(Any, wbe_alias).valid_time).is_(None),
                cast(Any, wbe_alias).deleted_at.is_(None),
            )
        )

        # Execute CTE query ordered by depth (root first)
        ancestors_stmt = select(wbe_cte).order_by(wbe_cte.c.depth.desc())
        ancestors_result = await self.session.execute(ancestors_stmt)
        ancestors = ancestors_result.all()

        # Build breadcrumb response
        return {
            "project": {
                "id": project.id,
                "project_id": project.project_id,
                "code": project.code,
                "name": project.name,
            },
            "wbe_path": [
                {
                    "id": ancestor.id,
                    "wbe_id": ancestor.wbe_id,
                    "code": ancestor.code,
                    "name": ancestor.name,
                }
                for ancestor in ancestors
            ],
        }

    async def get_by_root_id(self, root_id: UUID, branch: str = "main") -> WBE | None:
        """Override to include parent_name."""
        from typing import Any, cast

        from sqlalchemy import func

        stmt = (
            self._get_base_stmt()
            .where(
                WBE.wbe_id == root_id,
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if not row:
            return None

        wbe, parent_name = row
        wbe.parent_name = parent_name
        return wbe

    async def get_wbe_history(self, wbe_id: UUID) -> list[WBE]:
        """Get all versions of a WBE by root wbe_id (with creator and parent name)."""
        from typing import Any, cast

        from sqlalchemy import func
        from sqlalchemy.orm import aliased

        # User lookup subquery
        creator_subq = (
            select(User.user_id, User.full_name)
            .distinct(User.user_id)
            .order_by(User.user_id, User.transaction_time.desc())
            .subquery("creator_lookup")
        )

        # Parent lookup subquery
        Parent = aliased(WBE, name="parent_wbe")
        parent_subq = (
            select(Parent.wbe_id, Parent.name)
            .where(
                func.upper(cast(Any, Parent).valid_time).is_(None),
                cast(Any, Parent).deleted_at.is_(None)
            )
            .subquery("parent_lookup")
        )

        stmt = (
            select(WBE, creator_subq.c.full_name.label("created_by_name"), parent_subq.c.name.label("parent_name"))
            .outerjoin(creator_subq, WBE.created_by == creator_subq.c.user_id)
            .outerjoin(parent_subq, WBE.parent_wbe_id == parent_subq.c.wbe_id)
            .where(
                WBE.wbe_id == wbe_id,
                cast(Any, WBE).deleted_at.is_(None),
            )
            .order_by(cast(Any, WBE).transaction_time.desc())
        )

        result = await self.session.execute(stmt)
        history = []
        for row in result.all():
            wbe, creator_name, parent_name = row
            wbe.created_by_name = creator_name
            wbe.parent_name = parent_name
            history.append(wbe)

        return history
