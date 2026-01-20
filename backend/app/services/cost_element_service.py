"""Cost Element Service - branchable entity management."""

import builtins
from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand, UpdateVersionCommand
from app.core.versioning.enums import BranchMode
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.wbe import WBE
from app.models.schemas.cost_element import CostElementCreate, CostElementUpdate


class CostElementService(BranchableService[CostElement]):  # type: ignore[type-var,unused-ignore]
    """Service for Cost Element management (branchable + versionable)."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(CostElement, db)

    async def get_current(
        self, root_id: UUID, branch: str = "main"
    ) -> CostElement | None:
        """Get the current active version for a root entity on a specific branch.

        Override parent method to use 'cost_element_id' field instead of
        the auto-generated field name.
        """
        stmt = (
            select(CostElement)
            .where(
                CostElement.cost_element_id == root_id,
                CostElement.branch == branch,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .order_by(cast(Any, CostElement).valid_time.desc())
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
    ) -> CostElement:
        """Create the initial version of a CostElement.

        Override parent method to use 'cost_element_id' field instead of
        the auto-generated field name.

        Args:
            root_id: Root UUID identifier for the CostElement
            actor_id: User creating the CostElement
            control_date: Optional control date for valid_time (defaults to now)
            branch: Branch name (default: "main")
            **data: Additional fields for the CostElement

        Returns:
            Created CostElement
        """
        data["cost_element_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=CostElement,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
        )
        return await cmd.execute(self.session)

    def _get_base_stmt(self) -> Any:
        """Get base select statement with WBE name and CostElementType joins."""
        from sqlalchemy.orm import aliased

        WBEAlias = aliased(WBE, name="wbe_lookup")
        TypeAlias = aliased(CostElementType, name="type_lookup")

        # Subquery for current WBE versions
        wbe_subq = (
            select(WBEAlias.wbe_id, WBEAlias.name.label("wbe_name"))
            .where(
                func.upper(cast(Any, WBEAlias).valid_time).is_(None),
                cast(Any, WBEAlias).deleted_at.is_(None),
            )
            .subquery("wbe_lookup_subq")
        )

        # Subquery for current CostElementType versions
        type_subq = (
            select(
                TypeAlias.cost_element_type_id,
                TypeAlias.name.label("type_name"),
                TypeAlias.code.label("type_code"),
            )
            .where(
                func.upper(cast(Any, TypeAlias).valid_time).is_(None),
                cast(Any, TypeAlias).deleted_at.is_(None),
            )
            .subquery("type_lookup_subq")
        )

        return (
            select(
                CostElement,
                wbe_subq.c.wbe_name,
                type_subq.c.type_name,
                type_subq.c.type_code,
            )
            .outerjoin(wbe_subq, CostElement.wbe_id == wbe_subq.c.wbe_id)
            .outerjoin(
                type_subq,
                CostElement.cost_element_type_id == type_subq.c.cost_element_type_id,
            )
        )

    async def _resolve_relations(
        self, query_results: Sequence[Any]
    ) -> list[CostElement]:
        """Helper to resolve related names for a list of results."""
        resolved = []
        for item in query_results:
            if hasattr(item, "__iter__") and not isinstance(item, (str, bytes)):
                item_list = list(item)
                if len(item_list) >= 4:
                    # entity, wbe_name, type_name, type_code
                    entity = item_list[0]
                    entity.wbe_name = item_list[1]
                    entity.cost_element_type_name = item_list[2]
                    entity.cost_element_type_code = item_list[3]
                    resolved.append(entity)
                elif len(item_list) >= 2:
                    # Fallback for backwards compatibility
                    entity, wbe_name = item_list[0], item_list[1]
                    entity.wbe_name = wbe_name
                    resolved.append(entity)
                else:
                    resolved.append(item_list[0])
            else:
                resolved.append(item)
        return resolved

    async def create(
        self,
        element_in: CostElementCreate,
        actor_id: UUID,
        branch: str | None = None,
        control_date: datetime | None = None,
    ) -> CostElement:
        """Create new cost element using CreateVersionCommand.

        Auto-creates a default schedule baseline for the cost element.
        """
        element_data = element_in.model_dump(exclude_unset=True)
        element_data.pop("control_date", None)

        # Use provided cost_element_id (for seeding) or generate new one
        root_id = element_in.cost_element_id or uuid4()
        element_data["cost_element_id"] = root_id

        # Use schema branch if provided, otherwise use parameter (for backward compatibility)
        target_branch = branch or "main"
        if "branch" not in element_data or element_data["branch"] == "main":
            element_data["branch"] = target_branch

        # Create the cost element
        cmd = CreateVersionCommand(
            entity_class=CostElement,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **element_data,
        )
        cost_element = await cmd.execute(self.session)

        # Auto-create default schedule baseline
        from app.services.schedule_baseline_service import ScheduleBaselineService

        sb_service = ScheduleBaselineService(self.session)
        baseline = await sb_service.ensure_exists(
            cost_element_id=root_id,
            actor_id=actor_id,
            branch=target_branch,
            control_date=control_date,
        )

        # Update cost element with baseline reference
        cost_element.schedule_baseline_id = baseline.schedule_baseline_id

        # Auto-create default forecast
        from app.services.forecast_service import ForecastService

        forecast_service = ForecastService(self.session)
        forecast = await forecast_service.ensure_exists(
            cost_element_id=root_id,
            actor_id=actor_id,
            branch=target_branch,
            budget_amount=cost_element.budget_amount,
        )

        # Update cost element with forecast reference
        cost_element.forecast_id = forecast.forecast_id
        await self.session.flush()

        return cost_element

    async def update(  # type: ignore[override]
        self,
        cost_element_id: UUID,
        element_in: CostElementUpdate,
        actor_id: UUID,
        branch: str | None = None,
        control_date: datetime | None = None,
    ) -> CostElement:
        """Update cost element using UpdateVersionCommand or Fork if new branch."""
        update_data = element_in.model_dump(exclude_unset=True)
        update_data.pop("control_date", None)

        # Use schema branch if provided, otherwise use parameter (for backward compatibility)
        target_branch = update_data.pop("branch", None) or branch or "main"
        update_data["branch"] = target_branch

        # Check if version exists in target branch
        # We need to manage the query manually to avoid TemporalService issues and handle branching
        current = await self.get_by_id(cost_element_id, branch=target_branch)

        if current:
            # Linear update in same branch: Close old, Open new

            # Custom command class to handle multi-word entity name AND branch filtering
            class CostElementUpdateCommand(UpdateVersionCommand[CostElement]):  # type: ignore[type-var,unused-ignore]
                def __init__(
                    self,
                    entity_class: type[CostElement],
                    root_id: UUID,
                    actor_id: UUID,
                    branch: str = "main",
                    control_date: datetime | None = None,
                    **updates: Any,
                ) -> None:
                    super().__init__(
                        entity_class,
                        root_id,
                        actor_id,
                        control_date=control_date,
                        **updates,
                    )
                    self.branch = branch

                def _root_field_name(self) -> str:
                    return "cost_element_id"

                async def _get_current(self, session: AsyncSession) -> Any | None:
                    stmt = (
                        select(self.entity_class)
                        .where(
                            getattr(self.entity_class, self._root_field_name())
                            == self.root_id,
                            self.entity_class.branch == self.branch,
                            func.upper(cast(Any, self.entity_class).valid_time).is_(
                                None
                            ),
                            cast(Any, self.entity_class).deleted_at.is_(None),
                        )
                        .order_by(cast(Any, self.entity_class).valid_time.desc())
                        .limit(1)
                    )
                    result = await session.execute(stmt)
                    return result.scalar_one_or_none()

            cmd = CostElementUpdateCommand(
                entity_class=CostElement,  # type: ignore[type-var,unused-ignore]
                root_id=cost_element_id,
                actor_id=actor_id,
                control_date=control_date,
                # Branch is passed via update_data unpacking to match signature
                **update_data,
            )
            return await cmd.execute(self.session)

        else:
            # Version not found in target branch -> Fork from main (or parent)
            # This handles "Create Branch" scenario implicitly on update

            # Try to find source in 'main' to fork from
            # Note: In a real system we might want to let the caller specify the source branch
            source_version = await self.get_by_id(cost_element_id, branch="main")
            if not source_version:
                # If not found in main either, we can't update a non-existent entity
                raise ValueError(
                    f"Cost Element {cost_element_id} not found in {branch} or main."
                )

            # Clone data from source
            data = {
                c.name: getattr(source_version, c.name)
                for c in source_version.__table__.columns
            }

            # Remove system/audit fields to let DB/Command handle them
            system_fields = [
                "valid_time",
                "transaction_time",
                "created_by",
                "deleted_by",
                "deleted_at",
                "id",  # New version needs new ID
                "schedule_baseline_id",  # Don't copy baseline ID - will create new one
                "forecast_id",  # Don't copy forecast ID - will create new one
            ]
            for field in system_fields:
                data.pop(field, None)

            # Apply updates
            data.update(update_data)

            # Set branching metadata
            data["branch"] = branch
            data["parent_id"] = source_version.id  # Link to parent version

            # Create new version (Insert only, do not close parent)
            create_cmd = CreateVersionCommand(
                entity_class=CostElement,  # type: ignore[type-var,unused-ignore]
                root_id=cost_element_id,
                actor_id=actor_id,
                control_date=control_date,
                **data,
            )
            new_element = await create_cmd.execute(self.session)

            # Auto-create schedule baseline for the new branch
            from app.services.schedule_baseline_service import ScheduleBaselineService

            sb_service = ScheduleBaselineService(self.session)
            baseline = await sb_service.ensure_exists(
                cost_element_id=cost_element_id,
                actor_id=actor_id,
                branch=target_branch,
                control_date=control_date,
            )

            # Update cost element with baseline reference
            new_element.schedule_baseline_id = baseline.schedule_baseline_id

            # Auto-create forecast for the new branch
            from app.services.forecast_service import ForecastService

            forecast_service = ForecastService(self.session)
            forecast = await forecast_service.ensure_exists(
                cost_element_id=cost_element_id,
                actor_id=actor_id,
                branch=target_branch,
                budget_amount=new_element.budget_amount,
            )

            # Update cost element with forecast reference
            new_element.forecast_id = forecast.forecast_id
            await self.session.flush()

            return new_element

    async def soft_delete(  # type: ignore[override]
        self,
        cost_element_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> None:
        """Soft delete cost element using BranchableService.soft_delete.

        Cascades the delete to the associated schedule baseline and forecast.

        This uses the BranchableSoftDeleteCommand which is branch-aware.
        """
        # Get the cost element to find its schedule baseline and forecast
        cost_element = await self.get_by_id(cost_element_id, branch=branch)

        if cost_element and cost_element.schedule_baseline_id:
            # Cascade delete to schedule baseline
            from app.services.schedule_baseline_service import ScheduleBaselineService

            sb_service = ScheduleBaselineService(self.session)
            await sb_service.soft_delete(
                root_id=cost_element.schedule_baseline_id,
                actor_id=actor_id,
                branch=branch,
                control_date=control_date,
            )

        if cost_element and cost_element.forecast_id:
            # Cascade delete to forecast
            from app.services.forecast_service import ForecastService

            forecast_service = ForecastService(self.session)
            await forecast_service.soft_delete(
                forecast_id=cost_element.forecast_id,
                actor_id=actor_id,
                branch=branch,
                control_date=control_date,
            )

        # Call parent method from BranchableService
        await super().soft_delete(
            root_id=cost_element_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
        )

    async def get_by_id(
        self, cost_element_id: UUID, branch: str = "main"
    ) -> CostElement | None:
        """Get cost element by root ID and branch with WBE name."""
        stmt = (
            self._get_base_stmt()
            .where(
                CostElement.cost_element_id == cost_element_id,
                CostElement.branch == branch,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .order_by(cast(Any, CostElement).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        resolved = await self._resolve_relations(result.all())
        return resolved[0] if resolved else None

    async def get_cost_elements(
        self,
        filters: dict[str, Any] | None = None,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGE,
        skip: int = 0,
        limit: int = 100000,
        search: str | None = None,
        filter_string: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
        as_of: datetime | None = None,
    ) -> tuple[list[CostElement], int]:
        """Get all cost elements with search, filtering, and sorting.

        Args:
            filters: Legacy dict filters (for backward compatibility)
            branch: Branch name to filter by (default: "main")
            branch_mode: Branch resolution mode (default: MERGE)
                - MERGE: Combine current branch with main (current branch takes precedence)
                - STRICT: Only return entities from current branch
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            search: Search term to match against code and name (case-insensitive)
            filter_string: Filter string in format "column:value;column:value1,value2"
                          Example: "code:LAB;name:Phase"
            sort_field: Field name to sort by (e.g., "name", "code", "budget_amount")
            sort_order: Sort order, either "asc" or "desc" (default: "asc")
            as_of: Optional timestamp for time-travel queries

        Returns:
            Tuple of (list of cost elements with relations, total count matching filters)

        Raises:
            ValueError: If invalid filter field or sort field is provided

        Examples:
            >>> # Get cost elements for a specific WBE
            >>> elements, total = await service.get_cost_elements(
            ...     filters={"wbe_id": wbe_id},
            ...     search="Mechanical",
            ...     sort_field="budget_amount",
            ...     sort_order="desc"
            ... )
        """
        from sqlalchemy import and_, or_

        from app.core.filtering import FilterParser

        # Base query with WBE name and type joins
        stmt = self._get_base_stmt()

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
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )

        # Apply legacy dict filters (for backward compatibility)
        if filters:
            if "wbe_id" in filters:
                stmt = stmt.where(CostElement.wbe_id == filters["wbe_id"])
            if "cost_element_type_id" in filters:
                stmt = stmt.where(
                    CostElement.cost_element_type_id == filters["cost_element_type_id"]
                )

        # Apply search (across code and name)
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    CostElement.code.ilike(search_term),
                    CostElement.name.ilike(search_term),
                )
            )

        # Apply new filter string format
        if filter_string:
            # Define allowed filterable fields for security
            allowed_fields = ["code", "name"]

            parsed_filters = FilterParser.parse_filters(filter_string)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, CostElement), parsed_filters, allowed_fields=allowed_fields
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
            if not hasattr(CostElement, sort_field):
                raise ValueError(f"Invalid sort field: {sort_field}")

            column = getattr(CostElement, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            # Default sort by valid_time descending
            stmt = stmt.order_by(cast(Any, CostElement).valid_time.desc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        # Execute query
        result = await self.session.execute(stmt)
        cost_elements = await self._resolve_relations(result.all())

        return cost_elements, total

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        branch: str = "main",
        skip: int = 0,
        limit: int = 100000,
    ) -> list[CostElement]:
        """Alias for get_cost_elements() to maintain backward compatibility.

        Note: Returns only items, not total count. Use get_cost_elements() for pagination.
        Uses STRICT mode (only current branch) for backward compatibility.
        """
        items, _ = await self.get_cost_elements(
            filters=filters,
            branch=branch,
            branch_mode=BranchMode.STRICT,
            skip=skip,
            limit=limit,
        )
        return items

    async def get_history(
        self, root_id: UUID, branch: str = "main"
    ) -> builtins.list[CostElement]:
        """Get all versions of a cost element with creator, WBE name, and type info.

        Args:
            root_id: Root cost_element_id
            branch: Branch to query history from (default: "main")

        Returns:
            List of cost element versions in the specified branch, ordered by transaction_time descending
        """
        from sqlalchemy.orm import aliased

        from app.models.domain.user import User

        # User lookup subquery
        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )

        # WBE lookup subquery
        WBEAlias = aliased(WBE, name="wbe_history_lookup")
        wbe_subq = (
            select(WBEAlias.wbe_id, WBEAlias.name.label("wbe_name"))
            .where(
                func.upper(cast(Any, WBEAlias).valid_time).is_(None),
                cast(Any, WBEAlias).deleted_at.is_(None),
            )
            .subquery("wbe_history_lookup_subq")
        )

        # CostElementType lookup subquery
        TypeAlias = aliased(CostElementType, name="type_history_lookup")
        type_subq = (
            select(
                TypeAlias.cost_element_type_id,
                TypeAlias.name.label("type_name"),
                TypeAlias.code.label("type_code"),
            )
            .where(
                func.upper(cast(Any, TypeAlias).valid_time).is_(None),
                cast(Any, TypeAlias).deleted_at.is_(None),
            )
            .subquery("type_history_lookup_subq")
        )

        stmt = (
            select(
                CostElement,
                creator_subq.c.full_name.label("created_by_name"),
                wbe_subq.c.wbe_name,
                type_subq.c.type_name,
                type_subq.c.type_code,
            )
            .outerjoin(creator_subq, CostElement.created_by == creator_subq.c.user_id)
            .outerjoin(wbe_subq, CostElement.wbe_id == wbe_subq.c.wbe_id)
            .outerjoin(
                type_subq,
                CostElement.cost_element_type_id == type_subq.c.cost_element_type_id,
            )
            .where(
                CostElement.cost_element_id == root_id,
                CostElement.branch == branch,
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .order_by(cast(Any, CostElement).transaction_time.desc())
        )

        result = await self.session.execute(stmt)
        history = []
        for row in result.all():
            entity, creator_name, wbe_name, type_name, type_code = row
            entity.created_by_name = creator_name
            entity.wbe_name = wbe_name
            entity.cost_element_type_name = type_name
            entity.cost_element_type_code = type_code
            history.append(entity)

        return history

    async def get_cost_element_as_of(
        self,
        cost_element_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> CostElement | None:
        """Get cost element as it was at specific timestamp.

        Provides System Time Travel semantics for single-entity queries.
        Includes parent_name and cost_element_type_name relations.
        Uses STRICT mode by default (only searches in specified branch).
        Use BranchMode.MERGE to fall back to main branch if not found.

        Args:
            cost_element_id: The unique identifier of the cost element
            as_of: Timestamp to query (historical state)
            branch: Branch name to query (default: "main")
            branch_mode: Resolution mode for branches
                - None/STRICT: Only return from specified branch (default)
                - MERGE: Fall back to main if not found on branch

        Returns:
            CostElement if found at the specified timestamp, None otherwise

        Example:
            >>> # Get cost element as of January 1st
            >>> from datetime import datetime
            >>> as_of = datetime(2026, 1, 1, 12, 0, 0)
            >>> element = await service.get_cost_element_as_of(
            ...     cost_element_id=uuid,
            ...     as_of=as_of
            ... )
        """
        from sqlalchemy.orm import aliased

        WBEAlias = aliased(WBE, name="wbe_lookup")
        TypeAlias = aliased(CostElementType, name="type_lookup")

        # Subqueries for parent versions (as of specific time)
        wbe_where_clauses = [cast(Any, WBEAlias).deleted_at.is_(None)]
        if as_of:
            wbe_where_clauses.append(cast(Any, WBEAlias).valid_time.contains(as_of))
        else:
            wbe_where_clauses.append(
                func.upper(cast(Any, WBEAlias).valid_time).is_(None)
            )

        wbe_subq = (
            select(WBEAlias.wbe_id, WBEAlias.name.label("wbe_name"))
            .where(*wbe_where_clauses)
            .subquery("wbe_lookup_subq")
        )

        type_where_clauses = [cast(Any, TypeAlias).deleted_at.is_(None)]
        if as_of:
            type_where_clauses.append(cast(Any, TypeAlias).valid_time.contains(as_of))
        else:
            type_where_clauses.append(
                func.upper(cast(Any, TypeAlias).valid_time).is_(None)
            )

        type_subq = (
            select(
                TypeAlias.cost_element_type_id,
                TypeAlias.name.label("type_name"),
                TypeAlias.code.label("type_code"),
            )
            .where(*type_where_clauses)
            .subquery("type_lookup_subq")
        )

        # Build query with joins
        stmt = (
            select(
                CostElement,
                wbe_subq.c.wbe_name,
                type_subq.c.type_name,
                type_subq.c.type_code,
            )
            .outerjoin(wbe_subq, CostElement.wbe_id == wbe_subq.c.wbe_id)
            .outerjoin(
                type_subq,
                CostElement.cost_element_type_id == type_subq.c.cost_element_type_id,
            )
            .where(
                CostElement.cost_element_id == cost_element_id,
                CostElement.branch == branch,
            )
        )

        # Apply time-travel filter
        stmt = self._apply_bitemporal_filter_for_time_travel(stmt, as_of)

        stmt = stmt.limit(1)
        result = await self.session.execute(stmt)
        resolved = await self._resolve_relations(result.all())
        return resolved[0] if resolved else None

    async def get_breadcrumb(self, cost_element_id: UUID) -> dict[str, Any]:
        """Get breadcrumb trail for a Cost Element including project and WBE.

        For cost elements, the hierarchy is: Project -> WBE -> Cost Element
        This returns the project and WBE information for navigation.

        Args:
            cost_element_id: Cost Element ID

        Returns:
            Dict with 'project', 'wbe', and 'cost_element' keys

        Raises:
            ValueError: If Cost Element not found
        """
        from typing import Any, cast

        from sqlalchemy import func

        from app.models.domain.project import Project
        from app.models.domain.wbe import WBE

        # Get the current cost element
        current_element = await self.get_by_id(cost_element_id)
        if not current_element:
            raise ValueError(f"Cost Element with id {cost_element_id} not found")

        # Get the WBE first (cost element only has wbe_id)
        wbe_stmt = (
            select(WBE)
            .where(
                WBE.wbe_id == current_element.wbe_id,
                WBE.branch == current_element.branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .order_by(cast(Any, WBE).valid_time.desc())
            .limit(1)
        )
        wbe_result = await self.session.execute(wbe_stmt)
        wbe = wbe_result.scalar_one_or_none()

        if not wbe:
            raise ValueError(f"WBE {current_element.wbe_id} not found")

        # Get the project from the WBE
        project_stmt = (
            select(Project)
            .where(
                Project.project_id == wbe.project_id,
                Project.branch == wbe.branch,
                func.upper(cast(Any, Project).valid_time).is_(None),
                cast(Any, Project).deleted_at.is_(None),
            )
            .order_by(cast(Any, Project).valid_time.desc())
            .limit(1)
        )
        project_result = await self.session.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {wbe.project_id} not found")

        # Build breadcrumb response
        return {
            "project": {
                "id": project.id,
                "project_id": project.project_id,
                "code": project.code,
                "name": project.name,
            },
            "wbe": {
                "id": wbe.id,
                "wbe_id": wbe.wbe_id,
                "code": wbe.code,
                "name": wbe.name,
            },
            "cost_element": {
                "id": current_element.id,
                "cost_element_id": current_element.cost_element_id,
                "code": current_element.code,
                "name": current_element.name,
            },
        }
