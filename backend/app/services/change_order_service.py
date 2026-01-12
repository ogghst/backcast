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
    - Auto-branch creation: co-{code} branch created on CO creation
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
        """Create a new Change Order with automatic branch creation.

        This method:
        1. Creates the Change Order on the main branch
        2. Automatically creates a co-{code} branch for isolated work
        3. Returns the created Change Order

        Args:
            change_order_in: Change Order creation data
            actor_id: User creating the Change Order
            control_date: Optional control date for bitemporal operations

        Returns:
            Created ChangeOrder

        Raises:
            ValueError: If branch creation fails
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

        # Auto-create the CO branch for isolated work
        # Branch name format: co-{code}
        branch_name = f"co-{change_order_in.code}"

        try:
            await self.create_branch(
                root_id=root_id,
                actor_id=actor_id,
                new_branch=branch_name,
                from_branch="main",
            )
        except Exception as e:
            raise ValueError(
                f"Failed to create branch {branch_name} for Change Order: {e}"
            ) from e

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
            **update_data,
        )

    async def delete_change_order(
        self,
        change_order_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> ChangeOrder:
        """Soft delete a Change Order.

        Marks the current version as deleted.

        Args:
            change_order_id: The change_order_id (UUID root identifier)
            actor_id: User performing the deletion
            control_date: Optional control date for bitemporal operations

        Returns:
            The deleted ChangeOrder

        Raises:
            ValueError: If Change Order not found
        """
        from app.core.versioning.commands import SoftDeleteCommand

        # Use SoftDeleteCommand directly
        cmd = SoftDeleteCommand(
            entity_class=ChangeOrder,
            root_id=change_order_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        return await cmd.execute(self.session)

    async def get_change_orders(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100,
        branch: str = "main",
    ) -> tuple[list[ChangeOrder], int]:
        """Get all Change Orders for a project with pagination.

        Args:
            project_id: Filter by project ID
            skip: Number of records to skip
            limit: Maximum records to return
            branch: Branch to query (default: "main")

        Returns:
            Tuple of (list of Change Orders, total count)
        """
        from typing import Any, cast

        from sqlalchemy import func

        # Base query: versions in specified branch for this project
        stmt = select(ChangeOrder).where(
            ChangeOrder.project_id == project_id,
            ChangeOrder.branch == branch,
            cast(Any, ChangeOrder).deleted_at.is_(None),
        )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

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
