"""WBS Element Service - branchable entity management.

Extends BranchableService for WBS Element operations within the ANSI-748 model.
Provides WBS-specific queries including hierarchical budget computation through
the new WorkPackage -> ControlAccount -> WBSElement hierarchy.
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, literal_column, or_, select, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.branching.commands import UpdateCommand
from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand
from app.core.versioning.enums import BranchMode
from app.models.domain.control_account import ControlAccount
from app.models.domain.user import User
from app.models.domain.wbs_element import WBSElement
from app.models.domain.work_package import WorkPackage
from app.models.schemas.wbs_element import WBSElementCreate, WBSElementUpdate

# Type alias for the WBE model during migration
# Old code references WBE and wbe_id; new model uses WBSElement and wbs_element_id
WBE = WBSElement


class WBSElementService(BranchableService[WBSElement]):  # type: ignore[type-var,unused-ignore]
    """Service for WBS Element entity operations.

    Extends BranchableService with WBS-specific methods including
    project filtering, hierarchical queries, and recursive budget
    computation through ControlAccount -> WorkPackage.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WBSElement, session)

    async def _validate_revenue_allocation(
        self,
        project_id: UUID,
        branch: str = "main",
        exclude_wbs_id: UUID | None = None,
    ) -> None:
        """Validate total revenue allocation does not exceed project contract value.

        Args:
            project_id: Project to validate.
            branch: Branch to check (default: "main").
            exclude_wbs_id: Optional WBS Element ID to exclude (for update validation).

        Raises:
            ValueError: If total allocations exceed contract value.
        """
        from app.models.domain.project import Project

        project_stmt = select(Project.contract_value).where(
            Project.project_id == project_id,
            Project.branch == "main",
            func.upper(cast(Any, Project).valid_time).is_(None),
            cast(Any, Project).deleted_at.is_(None),
        )
        project_result = await self.session.execute(project_stmt)
        contract_value = project_result.scalar_one_or_none()

        if contract_value is None:
            return

        stmt = select(func.sum(cast(Any, WBSElement).revenue_allocation)).where(
            WBSElement.project_id == project_id,
            WBSElement.branch == branch,
            func.upper(cast(Any, WBSElement).valid_time).is_(None),
            cast(Any, WBSElement).deleted_at.is_(None),
            cast(Any, WBSElement).revenue_allocation.is_not(None),
        )

        if exclude_wbs_id:
            stmt = stmt.where(WBSElement.wbs_element_id != exclude_wbs_id)

        result = await self.session.execute(stmt)
        total_allocated = result.scalar() or Decimal("0")

        if total_allocated == Decimal("0"):
            return

        if total_allocated.quantize(Decimal("0.01")) > contract_value.quantize(
            Decimal("0.01")
        ):
            difference = total_allocated - contract_value
            raise ValueError(
                f"Total revenue allocation ({total_allocated:,.2f}) exceeds "
                f"project contract value ({contract_value:,.2f}). "
                f"Over-allocation: {difference:,.2f}"
            )

    async def _compute_wbs_budget(
        self, wbs_element_id: UUID, branch: str = "main"
    ) -> Decimal:
        """Compute WBS Element budget as recursive sum of WorkPackage.budget_amount.

        Budget = sum of all WorkPackage.budget_amount under ControlAccounts that
        belong to this WBS Element and all its descendant WBS Elements.

        Uses recursive CTE for efficient single-query calculation.

        Args:
            wbs_element_id: Root WBS Element ID.
            branch: Branch name (default: "main").

        Returns:
            Sum of all work package budgets in the WBS hierarchy.
        """
        # Recursive CTE: WBS Element + all descendants
        wbs_hierarchy = (
            select(
                WBSElement.wbs_element_id,
                literal_column("0").label("depth"),
            )
            .where(
                WBSElement.wbs_element_id == wbs_element_id,
                WBSElement.branch == branch,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
            )
            .cte(name="wbs_hierarchy", recursive=True)
        )

        child_wbs = aliased(WBSElement, name="child_wbs")
        wbs_hierarchy = wbs_hierarchy.union_all(
            select(
                child_wbs.wbs_element_id,
                (wbs_hierarchy.c.depth + 1).label("depth"),
            ).where(
                child_wbs.parent_wbs_element_id == wbs_hierarchy.c.wbs_element_id,
                child_wbs.branch == branch,
                func.upper(cast(Any, child_wbs).valid_time).is_(None),
                cast(Any, child_wbs).deleted_at.is_(None),
            )
        )

        # Sum WorkPackage.budget_amount through ControlAccounts in the hierarchy
        stmt = (
            select(func.coalesce(func.sum(WorkPackage.budget_amount), Decimal("0")))
            .select_from(wbs_hierarchy)
            .join(
                ControlAccount,
                ControlAccount.wbs_element_id == wbs_hierarchy.c.wbs_element_id,
            )
            .join(
                WorkPackage,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .where(
                ControlAccount.branch == branch,
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
                WorkPackage.branch == branch,
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar() or Decimal("0")

    async def _populate_computed_budgets(
        self, elements: list[WBSElement], branch: str = "main"
    ) -> list[WBSElement]:
        """Populate computed budget_allocation for a list of WBS Elements.

        Args:
            elements: List of WBS Element objects to populate.
            branch: Branch name for budget computation.

        Returns:
            Same list with budget_allocation populated on each element.
        """
        for element in elements:
            element.budget_allocation = await self._compute_wbs_budget(
                element.wbs_element_id, branch=element.branch
            )
        return elements

    async def get_as_of(
        self,
        entity_id: UUID,
        as_of: datetime | None = None,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> WBSElement | None:
        """Get the active version of a WBS Element as of a specific date.

        Override parent method to compute and attach budget_allocation.
        """
        element = await super().get_as_of(
            entity_id=entity_id,
            as_of=as_of,
            branch=branch,
            branch_mode=branch_mode,
        )
        if element:
            element.budget_allocation = await self._compute_wbs_budget(
                entity_id, branch=branch
            )
        return element

    async def create_root(
        self,
        root_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
        branch: str = "main",
        **data: Any,
    ) -> WBSElement:
        """Create the initial version of a WBS Element."""
        data["wbs_element_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=WBSElement,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
        )
        return await cmd.execute(self.session)

    async def _resolve_parent_names(
        self, query_results: Sequence[Any]
    ) -> list[WBSElement]:
        """Resolve parent names for a list of WBS Element results.

        Also batch-derives `created_at` (true creation = MIN over all versions)
        and `updated_at` (MAX over all versions), and batch-resolves
        `created_by_name` from the User table. Centralizing this here means
        every WBS list path (get_wbs_elements, get_by_project, get_by_parent,
        get_by_code, ...) emits all fields populated.
        """
        from app.core.versioning.creator_resolver import (
            populate_creator_names,
            populate_entity_timestamps,
        )

        resolved = []
        for item in query_results:
            if hasattr(item, "__iter__") and not isinstance(item, (str, bytes)):
                item_list = list(item)
                if len(item_list) >= 2:
                    entity, parent_name = item_list[0], item_list[1]
                    entity.parent_name = parent_name
                    resolved.append(entity)
                elif len(item_list) == 1:
                    resolved.append(item_list[0])
                else:
                    resolved.append(item)
            else:
                resolved.append(item)

        await populate_creator_names(self.session, resolved)
        await populate_entity_timestamps(self.session, resolved)
        return resolved

    def _get_base_stmt(self, as_of: datetime | None = None) -> Any:
        """Get base select statement with parent name resolution.

        Uses correlated scalar subquery to resolve parent names.
        """
        Parent = aliased(WBSElement, name="parent_wbs")

        parent_where_clauses = [
            Parent.wbs_element_id == WBSElement.parent_wbs_element_id,
            cast(Any, Parent).deleted_at.is_(None),
        ]

        if as_of:
            from sqlalchemy import cast as sql_cast

            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            parent_where_clauses.append(
                cast(Any, Parent).valid_time.op("@>")(as_of_tstz)
            )
            parent_where_clauses.append(
                func.lower(cast(Any, Parent).valid_time) <= as_of_tstz
            )
        else:
            parent_where_clauses.append(
                func.upper(cast(Any, Parent).valid_time).is_(None)
            )

        parent_name_subq = (
            select(Parent.name).where(*parent_where_clauses).limit(1).scalar_subquery()
        )

        return select(WBSElement, parent_name_subq.label("parent_name"))

    async def get_wbs_elements(
        self,
        project_id: UUID | None = None,
        parent_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100000,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
        search: str | None = None,
        filters: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
        as_of: datetime | None = None,
        apply_parent_filter: bool = False,
    ) -> tuple[list[WBSElement], int]:
        """Get WBS Elements with pagination, search, and filters.

        Args:
            project_id: Optional project filter.
            parent_id: Optional parent WBS Element filter.
            skip: Records to skip.
            limit: Maximum records to return.
            branch: Branch name to filter by.
            branch_mode: ISOLATED or MERGED.
            search: Search term for code and name.
            filters: Filter string.
            sort_field: Field to sort by.
            sort_order: "asc" or "desc".
            as_of: Optional timestamp for time-travel.
            apply_parent_filter: Whether to apply parent_id filter.

        Returns:
            Tuple of (list of WBS Elements, total count).
        """
        from sqlalchemy import and_

        from app.core.filtering import FilterParser

        base_stmt = self._get_base_stmt(as_of=as_of)

        stmt = self._apply_branch_mode_filter(
            base_stmt, branch=branch, branch_mode=branch_mode, as_of=as_of
        )

        if as_of:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
            )

        if project_id:
            stmt = stmt.where(WBSElement.project_id == project_id)

        if apply_parent_filter:
            stmt = stmt.where(WBSElement.parent_wbs_element_id == parent_id)

        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    WBSElement.code.ilike(search_term),
                    WBSElement.name.ilike(search_term),
                )
            )

        if filters:
            allowed_fields = ["level", "code", "name"]
            parsed_filters = FilterParser.parse_filters(filters)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, WBSElement), parsed_filters, allowed_fields=allowed_fields
            )
            if filter_expressions:
                stmt = stmt.where(and_(*filter_expressions))

        count_from = stmt.subquery()
        count_stmt = select(func.count()).select_from(count_from)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        if sort_field:
            if not hasattr(WBSElement, sort_field):
                raise ValueError(f"Invalid sort field: {sort_field}")
            column = getattr(WBSElement, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            stmt = stmt.order_by(cast(Any, WBSElement).valid_time.desc())

        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        elements = await self._resolve_parent_names(result.all())
        elements = await self._populate_computed_budgets(elements, branch=branch)

        return elements, total

    async def get_wbs_elements_for_projects(
        self,
        project_ids: list[UUID],
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
    ) -> tuple[list[WBSElement], int]:
        """Get WBS Elements for multiple projects in a single query.

        Batch alternative to calling get_wbs_elements() N times.
        """
        if not project_ids:
            return [], 0

        stmt = self._get_base_stmt()
        stmt = self._apply_branch_mode_filter(
            stmt, branch=branch, branch_mode=branch_mode
        )
        stmt = stmt.where(
            func.upper(cast(Any, WBSElement).valid_time).is_(None),
            cast(Any, WBSElement).deleted_at.is_(None),
        )
        stmt = stmt.where(WBSElement.project_id.in_(project_ids))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        result = await self.session.execute(stmt)
        elements = await self._resolve_parent_names(result.all())
        elements = await self._populate_computed_budgets(elements, branch=branch)

        return elements, total

    # --- Backward-compatible alias methods for gradual migration ---

    async def get_wbes(
        self,
        skip: int = 0,
        limit: int = 100000,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
        search: str | None = None,
        filters: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
        project_id: UUID | None = None,
        parent_wbe_id: UUID | None = None,
        apply_parent_filter: bool = False,
        as_of: datetime | None = None,
    ) -> tuple[list[WBSElement], int]:
        """Backward-compatible alias for get_wbs_elements().

        Preserves the old WBEService.get_wbes() signature during migration.
        """
        return await self.get_wbs_elements(
            project_id=project_id,
            parent_id=parent_wbe_id,
            skip=skip,
            limit=limit,
            branch=branch,
            branch_mode=branch_mode,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order,
            as_of=as_of,
            apply_parent_filter=apply_parent_filter,
        )

    async def get_by_project(
        self, project_id: UUID, branch: str = "main"
    ) -> list[WBSElement]:
        """Get all WBS Elements for a specific project (current versions)."""
        stmt = (
            self._get_base_stmt()
            .where(
                WBSElement.project_id == project_id,
                WBSElement.branch == branch,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
            )
            .order_by(WBSElement.code)
        )
        result = await self.session.execute(stmt)
        elements = await self._resolve_parent_names(result.all())
        return await self._populate_computed_budgets(elements, branch=branch)

    async def get_by_parent(
        self,
        project_id: UUID | None = None,
        parent_wbe_id: UUID | None = None,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.ISOLATED,
        as_of: datetime | None = None,
    ) -> list[WBSElement]:
        """Get WBS Elements filtered by parent_wbs_element_id.

        Args:
            project_id: Optional project filter.
            parent_wbe_id: Parent WBS Element ID. None means root elements.
            branch: Branch name.
            branch_mode: Branch isolation mode.
            as_of: Optional timestamp for time-travel.
        """
        stmt = self._get_base_stmt(as_of=as_of)

        stmt = self._apply_branch_mode_filter(
            stmt, branch=branch, branch_mode=branch_mode, as_of=as_of
        )

        if as_of:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
            )

        if project_id:
            stmt = stmt.where(WBSElement.project_id == project_id)

        if parent_wbe_id is None:
            stmt = stmt.where(cast(Any, WBSElement).parent_wbs_element_id.is_(None))
        else:
            stmt = stmt.where(WBSElement.parent_wbs_element_id == parent_wbe_id)

        stmt = stmt.order_by(WBSElement.code)
        result = await self.session.execute(stmt)
        elements = await self._resolve_parent_names(result.all())
        return await self._populate_computed_budgets(elements, branch=branch)

    async def get_by_code(
        self, code: str, project_id: UUID, branch: str = "main"
    ) -> WBSElement | None:
        """Get WBS Element by code within a project (current version)."""
        stmt = (
            self._get_base_stmt()
            .where(
                WBSElement.code == code,
                WBSElement.project_id == project_id,
                WBSElement.branch == branch,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        resolved = await self._resolve_parent_names(result.all())
        if resolved:
            resolved = await self._populate_computed_budgets(resolved, branch=branch)
            return resolved[0]
        return None

    async def create_wbe(self, wbe_in: WBSElementCreate, actor_id: UUID) -> WBSElement:
        """Create new WBS Element.

        Args:
            wbe_in: WBS Element creation data.
            actor_id: User creating the element.

        Returns:
            Created WBS Element entity.

        Raises:
            ValueError: If project not found or revenue allocation validation fails.
        """
        from app.models.domain.project import Project

        element_data = wbe_in.model_dump(exclude_unset=True)
        control_date = getattr(wbe_in, "control_date", None)
        element_data.pop("control_date", None)

        root_id = wbe_in.wbs_element_id or uuid4()
        element_data["wbs_element_id"] = root_id

        # Phase 1C: custom_fields chokepoint — resolve template, validate,
        # capture the IMMUTABLE snapshot. ValueError propagates to the route
        # (400 on create).
        from app.services.custom_field_service import CustomFieldService

        template_root_id = element_data.get("custom_entity_template_root_id")
        cf = element_data.get("custom_fields")
        cf_to_store, snapshot = await CustomFieldService(
            self.session
        ).prepare_for_create(
            template_root_id=template_root_id,
            custom_fields=cf,
            actor_id=actor_id,
        )
        element_data["custom_fields"] = cf_to_store
        if snapshot is not None:
            element_data["custom_field_definitions_snapshot"] = snapshot
        else:
            element_data.pop("custom_field_definitions_snapshot", None)

        # Validate Parent Project existence
        project_exists = await self.session.execute(
            select(Project.id)
            .where(
                Project.project_id == wbe_in.project_id,
                func.upper(cast(Any, Project).valid_time).is_(None),
                cast(Any, Project).deleted_at.is_(None),
            )
            .limit(1)
        )
        if not project_exists.scalar_one_or_none():
            raise ValueError(f"Project {wbe_in.project_id} not found or inactive")

        # Infer level from parent
        if wbe_in.parent_wbs_element_id:
            branch = element_data.get("branch", "main")
            parent = await self.get_as_of(wbe_in.parent_wbs_element_id, branch=branch)

            if not parent and branch != "main":
                parent = await self.get_as_of(
                    wbe_in.parent_wbs_element_id, branch="main"
                )

            if not parent:
                raise ValueError(
                    f"Parent WBS Element {wbe_in.parent_wbs_element_id} not found"
                )
            element_data["level"] = parent.level + 1
        else:
            element_data["level"] = 1

        cmd = CreateVersionCommand(
            entity_class=WBSElement,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **element_data,
        )
        element = await cmd.execute(self.session)

        # The revenue cap is a project-wide pool. A new element with no (or zero)
        # revenue allocation contributes nothing to it, so it must be allowed even
        # when the project is already over-allocated. Only enforce the cap when the
        # new element actually carries a positive allocation.
        if wbe_in.revenue_allocation:
            await self._validate_revenue_allocation(
                project_id=wbe_in.project_id,
                branch=element_data.get("branch", "main"),
            )

        element.budget_allocation = await self._compute_wbs_budget(
            root_id, branch=element_data.get("branch", "main")
        )
        return element

    async def update_wbe(
        self,
        wbe_id: UUID,
        wbe_in: WBSElementUpdate,
        actor_id: UUID,
    ) -> WBSElement:
        """Update WBS Element.

        Args:
            wbe_id: Root WBS Element ID to update.
            wbe_in: Update data.
            actor_id: User performing the update.

        Returns:
            Updated WBS Element entity.
        """
        update_data = wbe_in.model_dump(exclude_unset=True)
        update_data.pop("control_date", None)

        control_date = wbe_in.control_date
        branch = wbe_in.branch or "main"
        update_data.pop("branch", None)

        current = await self.get_as_of(wbe_id, branch=branch)
        if not current:
            if branch != "main":
                current = await self.get_as_of(wbe_id, branch="main")
            if not current:
                raise ValueError(f"WBS Element {wbe_id} not found")

        project_id = current.project_id

        # Phase 1C: validate custom_fields against the IMMUTABLE snapshot
        # captured at create (D11: only when the key is present; absent = skip).
        # ``current`` was already resolved above via get_as_of.
        if "custom_fields" in update_data:
            from app.services.custom_field_service import CustomFieldService

            await CustomFieldService(self.session).validate_for_update(
                snapshot=current.custom_field_definitions_snapshot,
                custom_fields=update_data["custom_fields"],
                actor_id=actor_id,
            )

        # Handle re-leveling if parent changes
        if "parent_wbs_element_id" in update_data:
            new_parent_id = update_data["parent_wbs_element_id"]
            if new_parent_id:
                parent = await self.get_as_of(new_parent_id, branch=branch)
                if not parent and branch != "main":
                    parent = await self.get_as_of(new_parent_id, branch="main")
                if not parent:
                    raise ValueError(f"Parent WBS Element {new_parent_id} not found")
                update_data["level"] = parent.level + 1
            else:
                update_data["level"] = 1

        cmd = UpdateCommand(  # type: ignore[type-var]
            entity_class=WBSElement,
            root_id=wbe_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            updates=update_data,
        )
        updated = await cmd.execute(self.session)

        # Revenue allocation is a project-wide invariant. Only re-validate it when
        # this update actually changes a revenue_allocation value; otherwise a plain
        # text edit (e.g. description) would be blocked by a pre-existing
        # over-allocation in the project.
        if "revenue_allocation" in update_data:
            await self._validate_revenue_allocation(
                project_id=project_id,
                branch=branch,
            )

        updated.budget_allocation = await self._compute_wbs_budget(
            wbe_id, branch=branch
        )
        return updated

    async def delete_wbe(
        self, wbe_id: UUID, actor_id: UUID, control_date: datetime | None = None
    ) -> WBSElement:
        """Soft delete WBS Element with cascade to children.

        Args:
            wbe_id: Root WBS Element ID to delete.
            actor_id: User performing the delete.
            control_date: Optional control date for deletion.

        Returns:
            The deleted root WBS Element.
        """
        element = await self.get_as_of(wbe_id)
        if not element:
            raise ValueError(f"WBS Element with id {wbe_id} not found")

        descendants = await self._get_all_descendants(wbe_id, element.branch)

        for descendant in reversed(descendants):
            await self.soft_delete(
                root_id=descendant.wbs_element_id,
                actor_id=actor_id,
                branch=descendant.branch,
                control_date=control_date,
            )

        return await self.soft_delete(
            root_id=wbe_id,
            actor_id=actor_id,
            branch=element.branch,
            control_date=control_date,
        )

    async def _get_all_descendants(
        self,
        parent_wbe_id: UUID,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
    ) -> list[WBSElement]:
        """Recursively get all descendants of a WBS Element using recursive CTE."""
        if branch_mode == BranchMode.MERGED and branch != "main":
            descendant_rows = await self._get_descendants_merged(parent_wbe_id, branch)
        else:
            descendant_rows = await self._get_descendants_isolated(
                parent_wbe_id, branch
            )

        descendant_list = []
        for wbs_id in descendant_rows:
            descendant = await self.get_as_of(
                entity_id=wbs_id,
                as_of=None,
                branch=branch,
                branch_mode=branch_mode,
            )
            if descendant:
                descendant_list.append(descendant)

        return descendant_list

    async def _get_descendants_isolated(
        self, parent_wbe_id: UUID, branch: str
    ) -> list[UUID]:
        """Get descendant WBS Element IDs for ISOLATED mode or main branch."""
        wbs_cte = (
            select(
                WBSElement.wbs_element_id,
                literal_column("1").label("depth"),
            )
            .where(
                WBSElement.parent_wbs_element_id == parent_wbe_id,
                WBSElement.branch == branch,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
            )
            .cte(name="wbs_descendants", recursive=True)
        )

        child_alias = aliased(WBSElement, name="wbs_child")
        wbs_cte = wbs_cte.union_all(
            select(
                child_alias.wbs_element_id,
                (wbs_cte.c.depth + 1).label("depth"),
            ).where(
                child_alias.parent_wbs_element_id == wbs_cte.c.wbs_element_id,
                child_alias.branch == branch,
                func.upper(cast(Any, child_alias).valid_time).is_(None),
                cast(Any, child_alias).deleted_at.is_(None),
            )
        )

        stmt = select(wbs_cte.c.wbs_element_id).order_by(wbs_cte.c.depth.asc())
        result = await self.session.execute(stmt)
        return [row.wbs_element_id for row in result.all()]

    async def _get_descendants_merged(
        self, parent_wbe_id: UUID, branch: str
    ) -> list[UUID]:
        """Get descendant WBS Element IDs for MERGED mode on non-main branch."""
        raw_sql = text("""
            WITH RECURSIVE wbs_descendants AS (
                SELECT DISTINCT ON (wbs_element_id) wbs_element_id, 1 as depth
                FROM wbs_elements
                WHERE parent_wbs_element_id = :parent_wbe_id
                    AND branch IN (:current_branch, 'main')
                    AND deleted_at IS NULL
                    AND upper(valid_time) IS NULL
                    AND NOT (
                        branch = 'main'
                        AND wbs_element_id IN (
                            SELECT w.wbs_element_id FROM wbs_elements w
                            WHERE w.branch = :current_branch
                              AND w.deleted_at IS NOT NULL
                        )
                    )
                ORDER BY wbs_element_id, CASE WHEN branch = :current_branch THEN 0 ELSE 1 END

                UNION ALL

                SELECT child.wbs_element_id, wd.depth + 1
                FROM wbs_descendants wd
                INNER JOIN LATERAL (
                    SELECT DISTINCT ON (wbs_element_id) wbs_element_id
                    FROM wbs_elements w
                    WHERE w.parent_wbs_element_id = wd.wbs_element_id
                        AND branch IN (:current_branch, 'main')
                        AND w.deleted_at IS NULL
                        AND upper(valid_time) IS NULL
                        AND NOT (
                            branch = 'main'
                            AND wbs_element_id IN (
                                SELECT ww.wbs_element_id FROM wbs_elements ww
                                WHERE ww.branch = :current_branch
                                  AND ww.deleted_at IS NOT NULL
                            )
                        )
                    ORDER BY wbs_element_id, CASE WHEN branch = :current_branch THEN 0 ELSE 1 END
                ) child ON true
            )
            SELECT wbs_element_id FROM wbs_descendants ORDER BY depth ASC
        """)

        result = await self.session.execute(
            raw_sql,
            {"parent_wbe_id": str(parent_wbe_id), "current_branch": branch},
        )
        return [row.wbs_element_id for row in result.all()]

    async def get_children_count(self, wbe_id: UUID, branch: str = "main") -> int:
        """Get count of direct children for a WBS Element."""
        stmt = (
            select(func.count())
            .select_from(WBSElement)
            .where(
                WBSElement.parent_wbs_element_id == wbe_id,
                WBSElement.branch == branch,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_breadcrumb(
        self,
        wbe_id: UUID,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
        as_of: datetime | None = None,
    ) -> dict[str, Any]:
        """Get breadcrumb trail for a WBS Element including project and ancestors.

        Uses recursive CTE to efficiently fetch the ancestor chain in one query.

        Args:
            wbe_id: Root WBS Element ID.
            branch: Branch name.
            branch_mode: Branch resolution mode.
            as_of: Optional timestamp for time-travel.

        Returns:
            Dict with 'project' and 'wbe_path' keys.

        Raises:
            ValueError: If WBS Element not found.
        """
        from app.models.domain.project import Project

        if as_of:
            current = await self.get_wbe_as_of(wbe_id, as_of, branch=branch)
        else:
            current = await self.get_as_of(wbe_id, branch=branch)

        if not current:
            raise ValueError(f"WBS Element with id {wbe_id} not found")

        # Get the project
        project = None
        project_stmt = select(Project).where(
            Project.project_id == current.project_id,
            Project.branch == current.branch,
            cast(Any, Project).deleted_at.is_(None),
        )

        if as_of:
            project_stmt = self._apply_bitemporal_filter_for_time_travel(
                project_stmt, as_of
            )
        else:
            project_stmt = project_stmt.where(
                func.upper(cast(Any, Project).valid_time).is_(None)
            )

        project_stmt = project_stmt.order_by(
            cast(Any, Project).valid_time.desc()
        ).limit(1)

        project_result = await self.session.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        if (
            not project
            and branch_mode == BranchMode.MERGED
            and current.branch != "main"
        ):
            project_stmt = select(Project).where(
                Project.project_id == current.project_id,
                Project.branch == "main",
                cast(Any, Project).deleted_at.is_(None),
            )
            if as_of:
                project_stmt = self._apply_bitemporal_filter_for_time_travel(
                    project_stmt, as_of
                )
            else:
                project_stmt = project_stmt.where(
                    func.upper(cast(Any, Project).valid_time).is_(None)
                )
            project_stmt = project_stmt.order_by(
                cast(Any, Project).valid_time.desc()
            ).limit(1)
            project_result = await self.session.execute(project_stmt)
            project = project_result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {current.project_id} not found")

        # Build recursive CTE for ancestors
        if as_of:
            as_of_ts = as_of.isoformat()
            time_filter = f"AND valid_time @> '{as_of_ts}'::timestamptz AND lower(valid_time) <= '{as_of_ts}'::timestamptz"
        else:
            time_filter = "AND upper(valid_time) IS NULL"

        if branch_mode == BranchMode.MERGED and current.branch != "main":
            recursive_sql = f"""
                SELECT best_parent.id, best_parent.wbs_element_id, best_parent.code, best_parent.name, best_parent.parent_wbs_element_id, wa.depth + 1
                FROM wbe_ancestors wa
                , LATERAL (
                    SELECT id, wbs_element_id, code, name, parent_wbs_element_id
                    FROM wbs_elements w
                    WHERE w.wbs_element_id = wa.parent_wbs_element_id
                        AND branch IN (:current_branch, 'main')
                        AND w.deleted_at IS NULL
                        {time_filter}
                    ORDER BY
                        CASE WHEN branch = :current_branch THEN 0
                             WHEN branch = 'main' THEN 1 ELSE 2 END
                    LIMIT 1
                ) best_parent
            """
        else:
            recursive_sql = f"""
                SELECT w.id, w.wbs_element_id, w.code, w.name, w.parent_wbs_element_id, wa.depth + 1
                FROM wbe_ancestors wa
                INNER JOIN wbs_elements w ON w.wbs_element_id = wa.parent_wbs_element_id
                    AND w.branch = :current_branch
                    AND w.deleted_at IS NULL
                    {time_filter}
            """

        raw_sql = text(f"""
            WITH RECURSIVE wbe_ancestors AS (
                SELECT id, wbs_element_id, code, name, parent_wbs_element_id, 0 as depth
                FROM wbs_elements
                WHERE wbs_element_id = :wbe_id
                    AND branch = :current_branch
                    AND deleted_at IS NULL
                    {time_filter}

                UNION ALL

                {recursive_sql}
            )
            SELECT id, wbs_element_id, code, name
            FROM wbe_ancestors
            ORDER BY depth DESC
        """)

        params = {
            "wbe_id": str(wbe_id),
            "current_branch": current.branch,
        }

        ancestors_result = await self.session.execute(raw_sql, params)
        ancestors = ancestors_result.all()

        return {
            "project": {
                "id": project.id,
                "project_id": project.project_id,
                "code": project.code,
                "name": project.name,
            },
            "wbe_path": [
                {
                    "id": ancestor.wbs_element_id,
                    "wbs_element_id": ancestor.wbs_element_id,
                    "wbe_id": ancestor.wbs_element_id,  # Backward compat
                    "code": ancestor.code,
                    "name": ancestor.name,
                }
                for ancestor in ancestors
            ],
        }

    async def get_wbe_history(self, wbe_id: UUID) -> list[WBSElement]:
        """Get all versions of a WBS Element (with creator and parent name)."""
        creator_name_subq = (
            select(User.full_name)
            .where(User.user_id == WBSElement.created_by)
            .distinct(User.user_id)
            .order_by(User.user_id, User.transaction_time.desc())
            .limit(1)
            .scalar_subquery()
        )

        Parent = aliased(WBSElement, name="parent_wbs")
        parent_name_subq = (
            select(Parent.name)
            .where(
                Parent.wbs_element_id == WBSElement.parent_wbs_element_id,
                func.upper(cast(Any, Parent).valid_time).is_(None),
                cast(Any, Parent).deleted_at.is_(None),
            )
            .limit(1)
            .scalar_subquery()
        )

        stmt = (
            select(
                WBSElement,
                creator_name_subq.label("created_by_name"),
                parent_name_subq.label("parent_name"),
            )
            .where(
                WBSElement.wbs_element_id == wbe_id,
                cast(Any, WBSElement).deleted_at.is_(None),
            )
            .order_by(cast(Any, WBSElement).transaction_time.desc())
        )

        result = await self.session.execute(stmt)
        history = []
        for row in result.all():
            element, creator_name, parent_name = row
            element.created_by_name = creator_name
            element.parent_name = parent_name
            element.budget_allocation = await self._compute_wbs_budget(
                wbe_id, branch=element.branch
            )
            history.append(element)

        # Derive created_at (true creation) + updated_at across all versions.
        from app.core.versioning.creator_resolver import populate_entity_timestamps

        await populate_entity_timestamps(self.session, history)

        return history

    async def get_wbe_as_of(
        self,
        wbe_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> WBSElement | None:
        """Get WBS Element as it was at specific timestamp."""
        return await self.get_as_of(wbe_id, as_of, branch, branch_mode)

    async def compute_budget_allocation(self, wbs_element_id: UUID) -> Decimal:
        """Public interface for budget computation.

        Args:
            wbs_element_id: Root WBS Element ID.

        Returns:
            Recursive sum of WorkPackage.budget_amount in the hierarchy.
        """
        return await self._compute_wbs_budget(wbs_element_id)
