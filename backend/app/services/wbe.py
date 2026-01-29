"""WBEService extending BranchableService for branchable entities.

Provides WBE-specific operations with parent-child project relationship.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import cast as sql_cast
from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand, UpdateVersionCommand
from app.core.versioning.enums import BranchMode
from app.models.domain.user import User
from app.models.domain.wbe import WBE
from app.models.schemas.wbe import WBECreate, WBEUpdate


class WBEService(BranchableService[WBE]):  # type: ignore[type-var,unused-ignore]
    """Service for WBE entity operations.

    Extends BranchableService with WBE-specific methods including
    project filtering and hierarchical queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WBE, session)

    async def get_current(self, root_id: UUID, branch: str = "main") -> WBE | None:
        """Get the current active version for a root entity on a specific branch.

        Override parent method to use 'wbe_id' field instead of
        the auto-generated field name.
        """
        from typing import cast as type_cast


        stmt = (
            select(WBE)
            .where(
                WBE.wbe_id == root_id,
                WBE.branch == branch,
                func.upper(type_cast(Any, WBE).valid_time).is_(None),
                type_cast(Any, WBE).deleted_at.is_(None),
            )
            .order_by(type_cast(Any, WBE).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_root(
        self,
        root_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
        branch: str = "main",
        **data: Any,
    ) -> WBE:
        """Create the initial version of a WBE.

        Override parent method to use 'wbe_id' field instead of
        the auto-generated field name.

        Args:
            root_id: Root UUID identifier for the WBE
            actor_id: User creating the WBE
            control_date: Optional control date for valid_time (defaults to now)
            branch: Branch name (default: "main")
            **data: Additional fields for the WBE

        Returns:
            Created WBE
        """
        data["wbe_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=WBE,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
        )
        return await cmd.execute(self.session)

    async def _resolve_parent_names(self, query_results: Sequence[Any]) -> list[WBE]:
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

    def _get_base_stmt(self, as_of: datetime | None = None) -> Any:
        """Get base select statement with parent name join.

        Args:
            as_of: Optional timestamp for time-travel queries on parent names
        """
        from typing import Any, cast


        Parent = aliased(WBE, name="parent_wbe")

        # Subquery for parent versions (current or as of specific time)
        parent_where_clauses = [cast(Any, Parent).deleted_at.is_(None)]

        if as_of:
            # Get parent version valid at as_of time
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            parent_where_clauses.append(cast(Any, Parent).valid_time.op("@>")(as_of_tstz))
            parent_where_clauses.append(func.lower(cast(Any, Parent).valid_time) <= as_of_tstz)
        else:
            # Get current parent version
            parent_where_clauses.append(
                func.upper(cast(Any, Parent).valid_time).is_(None)
            )

        parent_subq = (
            select(Parent.wbe_id, Parent.name)
            .where(*parent_where_clauses)
            .subquery("parent_lookup")
        )

        return select(WBE, parent_subq.c.name.label("parent_name")).outerjoin(
            parent_subq, WBE.parent_wbe_id == parent_subq.c.wbe_id
        )

    async def get_wbes(
        self,
        skip: int = 0,
        limit: int = 100000,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGE,
        search: str | None = None,
        filters: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
        project_id: UUID | None = None,
        parent_wbe_id: UUID | None = None,
        apply_parent_filter: bool = False,
        as_of: datetime | None = None,
    ) -> tuple[list[WBE], int]:
        """Get all WBEs with pagination, search, and filters.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            branch: Branch name to filter by (default: "main")
            branch_mode: Branch mode - MERGE (composite with main) or STRICT (isolated)
            search: Search term to match against code and name (case-insensitive)
            filters: Filter string in format "column:value;column:value1,value2"
                     Example: "level:1,2;code:1.1"
            sort_field: Field name to sort by (e.g., "name", "code", "level")
            sort_order: Sort order, either "asc" or "desc" (default: "asc")
            project_id: Optional project filter
            parent_wbe_id: Optional parent WBE filter
            as_of: Optional timestamp for time-travel queries

        Returns:
            Tuple of (list of WBEs with parent_name, total count matching filters)

        Raises:
            ValueError: If invalid filter field or sort field is provided
        """
        from typing import Any, cast

        from sqlalchemy import and_, or_

        from app.core.filtering import FilterParser

        # Build base query with all non-branch filters first
        # Start with base statement and join for parent names
        base_stmt = self._get_base_stmt(as_of=as_of)

        # Apply branch mode filter (handles STRICT vs MERGE logic)
        stmt = self._apply_branch_mode_filter(
            base_stmt, branch=branch, branch_mode=branch_mode, as_of=as_of
        )

        # Apply time-travel filter (for additional bitemporal constraints)
        # Note: _apply_branch_mode_filter already handles basic filtering
        if as_of:
            # Additional time-travel constraints if needed beyond branch mode
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            # Get current version (open upper bound) and not deleted
            stmt = stmt.where(
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )

        # Apply project filter
        if project_id:
            stmt = stmt.where(WBE.project_id == project_id)

        # Apply parent WBE filter
        if apply_parent_filter:
            stmt = stmt.where(WBE.parent_wbe_id == parent_wbe_id)

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
                cast(Any, WBE), parsed_filters, allowed_fields=allowed_fields
            )
            if filter_expressions:
                stmt = stmt.where(and_(*filter_expressions))

        # Get total count (before pagination)
        # For MERGE mode, count the distinct result
        count_from = stmt.subquery()
        count_stmt = select(func.count()).select_from(count_from)
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
        branch_mode: BranchMode = BranchMode.STRICT,
        as_of: datetime | None = None,
    ) -> list[WBE]:
        """Get WBEs filtered by parent_wbe_id.

        Args:
            project_id: Optional project filter
            parent_wbe_id: Parent WBE ID. None means root WBEs (parent_wbe_id IS NULL)
            branch: Branch name
            branch_mode: Branch mode - MERGE (composite with main) or STRICT (isolated)
            as_of: Optional timestamp for time-travel queries

        Returns:
            List of WBEs matching the parent filter
        """
        from typing import Any, cast


        # Build base statement with parent name join
        stmt = self._get_base_stmt(as_of=as_of)

        # Apply branch mode filter (handles STRICT vs MERGE logic)
        stmt = self._apply_branch_mode_filter(
            stmt, branch=branch, branch_mode=branch_mode, as_of=as_of
        )

        # Apply time-travel filter or current version filter
        if as_of:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )

        # Add project filter if provided
        if project_id:
            stmt = stmt.where(WBE.project_id == project_id)

        # Add parent filter
        if parent_wbe_id is None:
            # Query for root WBEs (parent_wbe_id IS NULL)
            stmt = stmt.where(cast(Any, WBE).parent_wbe_id.is_(None))
        else:
            # Query for children of specific parent
            stmt = stmt.where(WBE.parent_wbe_id == parent_wbe_id)

        stmt = stmt.order_by(WBE.code)
        result = await self.session.execute(stmt)
        return await self._resolve_parent_names(result.all())

    async def get_by_code(
        self, code: str, project_id: UUID, branch: str = "main"
    ) -> WBE | None:
        """Get WBE by code within a project (current version)."""
        from typing import Any, cast


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

    async def create_wbe(
        self, wbe_in: WBECreate, actor_id: UUID, control_date: datetime | None = None
    ) -> WBE:
        """Create new WBE using CreateVersionCommand."""
        wbe_data = wbe_in.model_dump(exclude_unset=True)
        # Remove control_date from wbe_data if present to avoid conflict with explicit arg
        wbe_data.pop("control_date", None)

        # Use provided wbe_id (for seeding) or generate new one
        root_id = wbe_in.wbe_id or uuid4()
        wbe_data["wbe_id"] = root_id

        # Infer level from parent
        if wbe_in.parent_wbe_id:
            parent = await self.get_by_root_id(wbe_in.parent_wbe_id)
            if not parent:
                raise ValueError(f"Parent WBE {wbe_in.parent_wbe_id} not found")
            wbe_data["level"] = parent.level + 1
        else:
            wbe_data["level"] = 1

        cmd = CreateVersionCommand(
            entity_class=WBE,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **wbe_data,
        )
        return await cmd.execute(self.session)

    async def update_wbe(
        self,
        wbe_id: UUID,
        wbe_in: WBEUpdate,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> WBE:
        """Update WBE using UpdateVersionCommand."""
        update_data = wbe_in.model_dump(exclude_unset=True)
        # Remove control_date from update_data if present to avoid conflict with explicit arg
        update_data.pop("control_date", None)

        # Handle re-leveling if parent changes
        if wbe_in.parent_wbe_id is not None:  # explicit check for field presence/value
            # Note: partial updates might send None to clear parent, or UUID to change it
            # But here we are checking if it's IN the update data.
            # However, since wbe_in fields are Optional, we need to check if it was set.
            # wbe_in.model_dump(exclude_unset=True) handled this for update_data,
            # but we need to check if "parent_wbe_id" is in update_data.
            pass

        if "parent_wbe_id" in update_data:
            new_parent_id = update_data["parent_wbe_id"]
            if new_parent_id:
                parent = await self.get_by_root_id(new_parent_id)
                if not parent:
                    raise ValueError(f"Parent WBE {new_parent_id} not found")
                update_data["level"] = parent.level + 1
            else:
                # Setting to root
                update_data["level"] = 1

        cmd = UpdateVersionCommand(
            entity_class=WBE,  # type: ignore[type-var,unused-ignore]
            root_id=wbe_id,
            actor_id=actor_id,
            control_date=control_date,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def delete_wbe(
        self, wbe_id: UUID, actor_id: UUID, control_date: datetime | None = None
    ) -> WBE:
        """Soft delete WBE with cascade to children.

        Deletes the WBE and all its descendants recursively.
        Returns the root WBE that was deleted.

        Args:
            wbe_id: Root WBE ID to delete
            actor_id: User performing the delete
            control_date: Optional control date for deletion

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
            await self.soft_delete(
                root_id=descendant.wbe_id,
                actor_id=actor_id,
                branch=descendant.branch,
                control_date=control_date,
            )

        # Finally, soft-delete the root WBE itself
        return await self.soft_delete(
            root_id=wbe_id,
            actor_id=actor_id,
            branch=wbe.branch,
            control_date=control_date,
        )

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

        from sqlalchemy import literal_column, select
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

        from sqlalchemy import select

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

    async def get_breadcrumb(
        self, wbe_id: UUID, branch: str = "main", as_of: datetime | None = None
    ) -> dict[str, Any]:
        """Get breadcrumb trail for a WBE including project and all ancestors.

        Uses recursive CTE to efficiently fetch the entire ancestor chain in a single query.

        Args:
            wbe_id: Root WBE ID
            branch: Branch name (default: "main")
            as_of: Optional timestamp for time-travel queries

        Returns:
            Dict with 'project' and 'wbe_path' keys

        Raises:
            ValueError: If WBE not found
        """
        from typing import Any, cast

        from sqlalchemy import literal_column, select
        from sqlalchemy.orm import aliased

        from app.models.domain.project import Project

        # First, get the target WBE
        if as_of:
            current_wbe = await self.get_wbe_as_of(wbe_id, as_of, branch=branch)
        else:
            current_wbe = await self.get_by_root_id(wbe_id, branch=branch)

        if not current_wbe:
            raise ValueError(f"WBE with id {wbe_id} not found")

        # Get the project
        # Get the project
        project_stmt = select(Project).where(
            Project.project_id == current_wbe.project_id,
            Project.branch.in_([current_wbe.branch, "main"]),
            cast(Any, Project).deleted_at.is_(None),
        )

        if as_of:
            # Time travel for project
            project_stmt = self._apply_bitemporal_filter_for_time_travel(
                project_stmt, as_of
            )
        else:
            # Current project version
            project_stmt = project_stmt.where(
                func.upper(cast(Any, Project).valid_time).is_(None)
            )

        # Order by branch priority (current > main) then time
        # We want to prefer the current branch if available
        project_stmt = project_stmt.order_by(
            case((Project.branch == current_wbe.branch, 0), else_=1),
            cast(Any, Project).valid_time.desc(),
        ).limit(1)

        project_result = await self.session.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {current_wbe.project_id} not found")

        # Build recursive CTE to get all ancestors
        # Base case: current WBE
        base_cte_stmt = select(
            WBE.id,
            WBE.wbe_id,
            WBE.code,
            WBE.name,
            WBE.parent_wbe_id,
            literal_column("0").label("depth"),
        ).where(
            WBE.wbe_id == wbe_id,
            WBE.branch == current_wbe.branch,
            cast(Any, WBE).deleted_at.is_(None),
        )

        if as_of:
            base_cte_stmt = self._apply_bitemporal_filter_for_time_travel(
                base_cte_stmt, as_of
            )
        else:
            base_cte_stmt = base_cte_stmt.where(
                func.upper(cast(Any, WBE).valid_time).is_(None)
            )

        wbe_cte = base_cte_stmt.cte(name="wbe_ancestors", recursive=True)

        # Recursive case: get parent WBEs
        wbe_alias = aliased(WBE, name="wbe_parent")
        recursive_stmt = select(
            wbe_alias.id,
            wbe_alias.wbe_id,
            wbe_alias.code,
            wbe_alias.name,
            wbe_alias.parent_wbe_id,
            (wbe_cte.c.depth + 1).label("depth"),
        ).where(
            wbe_alias.wbe_id == wbe_cte.c.parent_wbe_id,
            wbe_alias.branch == current_wbe.branch,
            cast(Any, wbe_alias).deleted_at.is_(None),
        )

        if as_of:
            recursive_stmt = self._apply_bitemporal_filter_for_time_travel(
                recursive_stmt, as_of
            )
        else:
            recursive_stmt = recursive_stmt.where(
                func.upper(cast(Any, wbe_alias).valid_time).is_(None)
            )

        wbe_cte = wbe_cte.union_all(recursive_stmt)

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
        return cast(WBE, wbe)

    async def get_wbe_history(self, wbe_id: UUID) -> list[WBE]:
        """Get all versions of a WBE by root wbe_id (with creator and parent name)."""
        from typing import Any, cast

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
                cast(Any, Parent).deleted_at.is_(None),
            )
            .subquery("parent_lookup")
        )

        stmt = (
            select(
                WBE,
                creator_subq.c.full_name.label("created_by_name"),
                parent_subq.c.name.label("parent_name"),
            )
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

    async def get_wbe_as_of(
        self,
        wbe_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> WBE | None:
        """Get WBE as it was at specific timestamp.

        Provides System Time Travel semantics for single-entity queries.
        Uses STRICT mode by default (only searches in specified branch).
        Use BranchMode.MERGE to fall back to main branch if not found.

        Args:
            wbe_id: The unique identifier of the WBE
            as_of: Timestamp to query (historical state)
            branch: Branch name to query (default: "main")
            branch_mode: Resolution mode for branches
                - None/STRICT: Only return from specified branch (default)
                - MERGE: Fall back to main if not found on branch

        Returns:
            WBE if found at the specified timestamp, None otherwise

        Example:
            >>> # Get WBE as of January 1st
            >>> from datetime import datetime
            >>> as_of = datetime(2026, 1, 1, 12, 0, 0)
            >>> wbe = await service.get_wbe_as_of(
            ...     wbe_id=uuid,
            ...     as_of=as_of
            ... )
        """
        return await self.get_as_of(wbe_id, as_of, branch, branch_mode)
