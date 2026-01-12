"""ChangeOrderService for Change Order business logic.

Provides Change Order specific operations including automatic branch
creation on CO creation.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.change_order import ChangeOrder
from app.models.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate


class ChangeOrderService(BranchableService[ChangeOrder]):
    """Service for Change Order entity operations.

    Extends BranchableService with Change Order specific methods.
    Supports full EVCS capabilities including branching.

    Key Features:
    - Workflow state management: Draft → Submitted → Approved → Implemented
    - Project-scoped: All COs belong to a specific project

    Note: Change Orders use change_order_id (UUID) as the EVCS root identifier,
    and code (str) as the human-readable business identifier.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ChangeOrder, session)

    async def get_current(
        self, root_id: UUID, branch: str = "main"
    ) -> ChangeOrder | None:
        """Get the current active version for a root entity on a specific branch.

        Override parent method to use 'change_order_id' field instead of
        the auto-generated 'changeorder_id'.
        """
        stmt = (
            select(ChangeOrder)
            .where(
                ChangeOrder.change_order_id == root_id,
                ChangeOrder.branch == branch,
                func.upper(cast(Any, ChangeOrder).valid_time).is_(None),
                cast(Any, ChangeOrder).deleted_at.is_(None),
            )
            .order_by(cast(Any, ChangeOrder).valid_time.desc())
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
    ) -> ChangeOrder:
        """Create the initial version of a Change Order.

        Override parent method to use 'change_order_id' field instead of
        the auto-generated 'changeorder_id'.

        Args:
            root_id: Root UUID identifier for the change order
            actor_id: User creating the change order
            control_date: Optional control date for valid_time (defaults to now)
            branch: Branch name (default: "main")
            **data: Additional fields for the change order

        Returns:
            Created ChangeOrder
        """
        data["change_order_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=ChangeOrder,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
        )
        return await cmd.execute(self.session)

    async def create_change_order(
        self,
        change_order_in: ChangeOrderCreate,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> ChangeOrder:
        """Create a new Change Order.

        This method:
        1. Creates the Change Order on the main branch
        2. Returns the created Change Order

        Args:
            change_order_in: Change Order creation data
            actor_id: User creating the Change Order
            control_date: Optional control date for bitemporal operations

        Returns:
            Created ChangeOrder

        """
        # Extract data from Pydantic model
        co_data = change_order_in.model_dump(exclude_unset=True)
        co_data.pop("control_date", None)

        # Generate a UUID for the change_order root
        root_id = uuid4()

        # Create the Change Order on main branch using create_root
        change_order = await self.create_root(
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch="main",
            **co_data,
        )

        return change_order

    async def update_change_order(
        self,
        change_order_id: UUID,
        change_order_in: ChangeOrderUpdate,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> ChangeOrder:
        """Update a Change Order's metadata.

        Creates a new version with the updated metadata.
        Always updates on the current active branch.

        Args:
            change_order_id: The change_order_id (UUID root identifier)
            change_order_in: Update data (partial)
            actor_id: User making the update
            control_date: Optional control date for bitemporal operations

        Returns:
            Updated ChangeOrder

        Raises:
            ValueError: If Change Order not found or invalid branch
        """
        # Get the current version to find its branch
        current = await self.get_current(change_order_id)
        if not current:
            raise ValueError(
                f"Change Order {change_order_id} not found or has been deleted"
            )

        # Filter None values from update data
        update_data = change_order_in.model_dump(exclude_unset=True)
        update_data.pop("control_date", None)

        # Use update method from BranchableService
        return await self.update(
            root_id=change_order_id,
            actor_id=actor_id,
            branch=current.branch,
            control_date=control_date,
            **update_data,
        )

    async def delete_change_order(
        self,
        change_order_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> ChangeOrder:
        """Soft delete a Change Order.

        Marks the current version on the main branch as deleted.

        Args:
            change_order_id: The change_order_id (UUID root identifier)
            actor_id: User performing the deletion
            control_date: Optional control date for bitemporal operations

        Returns:
            The deleted ChangeOrder

        Raises:
            ValueError: If Change Order not found
        """
        # Use BranchableService.soft_delete which is branch-aware
        return await self.soft_delete(
            root_id=change_order_id,
            actor_id=actor_id,
            branch="main",
            control_date=control_date,
        )

    async def get_change_orders(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100,
        branch: str = "main",
        search: str | None = None,
        filters: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
        as_of: datetime | None = None,
    ) -> tuple[list[ChangeOrder], int]:
        """Get all Change Orders for a project with pagination, search, and filters.

        Args:
            project_id: Filter by project ID
            skip: Number of records to skip
            limit: Maximum records to return
            branch: Branch to query (default: "main")
            search: Search term to match against code and title (case-insensitive)
            filters: Filter string in format "column:value;column:value1,value2"
            sort_field: Field name to sort by
            sort_order: Sort order, either "asc" or "desc" (default: "asc")
            as_of: Optional timestamp for time-travel queries

        Returns:
            Tuple of (list of Change Orders, total count)
        """
        from typing import Any, cast

        from sqlalchemy import and_, func, or_

        from app.core.filtering import FilterParser

        # Base query: versions in specified branch for this project
        stmt = select(ChangeOrder).where(
            ChangeOrder.project_id == project_id,
            ChangeOrder.branch == branch,
        )

        # Apply time-travel filter
        if as_of:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            # Get current active versions
            stmt = stmt.where(
                func.upper(cast(Any, ChangeOrder).valid_time).is_(None),
                cast(Any, ChangeOrder).deleted_at.is_(None),
            )

        # Apply search (across code and title)
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    ChangeOrder.code.ilike(search_term),
                    ChangeOrder.title.ilike(search_term),
                )
            )

        # Apply filters
        if filters:
            # Define allowed filterable fields for security
            allowed_fields = ["status", "code", "title"]

            parsed_filters = FilterParser.parse_filters(filters)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, ChangeOrder), parsed_filters, allowed_fields=allowed_fields
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
            if not hasattr(ChangeOrder, sort_field):
                raise ValueError(f"Invalid sort field: {sort_field}")

            column = getattr(ChangeOrder, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            # Default sort by valid_time descending (newest versions first)
            # Or usually for lists, maybe created_at/transaction_time or valid_time is best.
            stmt = stmt.order_by(cast(Any, ChangeOrder).valid_time.desc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        # Execute query
        result = await self.session.execute(stmt)
        change_orders = list(result.scalars().all())

        return change_orders, total

    async def get_current_by_code(
        self, code: str, branch: str = "main"
    ) -> ChangeOrder | None:
        """Get the current active version for a business code.

        Args:
            code: The business code (e.g., "CO-2026-001")
            branch: Branch to query (default: "main")

        Returns:
            Current ChangeOrder or None
        """
        stmt = (
            select(ChangeOrder)
            .where(
                ChangeOrder.code == code,
                ChangeOrder.branch == branch,
                func.upper(cast(Any, ChangeOrder).valid_time).is_(None),
                cast(Any, ChangeOrder).deleted_at.is_(None),
            )
            .order_by(cast(Any, ChangeOrder).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def merge_change_order(
        self,
        change_order_id: UUID,
        actor_id: UUID,
        target_branch: str = "main",
    ) -> ChangeOrder:
        """Merge the Change Order's branch into the target branch.

        Infers the source branch from the Change Order's code.

        Args:
            change_order_id: Change Order ID
            actor_id: User performing merge
            target_branch: Branch to merge INTO (default: main)

        Returns:
            The merged Change Order version on the target branch
        """
        # 1. Get current version (from main or source) to find the code
        # We check "main" first to get the metadata
        current = await self.get_current(change_order_id, branch=target_branch)

        # If not found on target, try finding it on any branch?
        # Actually, if we are merging, the CO *definition* usually exists on main (Draft),
        # and we are merging the *changes* from the branch.
        # But wait, Change Order Entity *itself* is branchable.
        # If I edit CO description on `co-123`, I am creating a version on `co-123`.
        # Merging `co-123` to `main` means bringing that description to `main`.

        if not current:
            # Try to find it on any branch to get the code?
            # Or just require it to exist on target?
            # If it's a new CO branch not yet on main?
            # But create_change_order creates on main AND branch. So it should be on main.
            raise ValueError("Change Order not found on target branch")

        source_branch = f"co-{current.code}"

        # Check if source branch has active version
        source_version = await self.get_current(change_order_id, branch=source_branch)
        if not source_version:
             raise ValueError(f"No active version found on source branch {source_branch}")

        return await self.merge_branch(
            root_id=change_order_id,
            actor_id=actor_id,
            source_branch=source_branch,
            target_branch=target_branch,
        )

    async def revert_change_order_version(
        self,
        change_order_id: UUID,
        actor_id: UUID,
        branch: str = "main",
    ) -> ChangeOrder:
        """Revert the Change Order to its previous version on the specified branch.

        Args:
            change_order_id: Change Order ID
            actor_id: User performing revert
            branch: Branch to revert on

        Returns:
            The new current version (which is a clone of the previous)
        """
        return await self.revert(
            root_id=change_order_id,
            actor_id=actor_id,
            branch=branch,
        )
