"""ChangeOrderService for Change Order business logic.

Provides Change Order specific operations including automatic branch
creation on CO creation and workflow-driven branch locking.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.branch import Branch
from app.models.domain.change_order import ChangeOrder
from app.models.domain.change_order_audit_log import ChangeOrderAuditLog
from app.models.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate
from app.services.branch_service import BranchService
from app.services.change_order_workflow_service import ChangeOrderWorkflowService

if TYPE_CHECKING:
    from app.models.schemas.change_order import ChangeOrderPublic

logger = logging.getLogger(__name__)


class ChangeOrderService(BranchableService[ChangeOrder]):  # type: ignore[type-var]
    """Service for Change Order entity operations.

    Extends BranchableService with Change Order specific methods.
    Supports full EVCS capabilities including branching.

    Key Features:
    - Workflow state management: Draft → Submitted → Approved → Implemented
    - Project-scoped: All COs belong to a specific project
    - Automatic branch creation: Creates co-{code} branch on CO creation
    - Workflow-driven locking: Status changes trigger branch lock/unlock

    Note: Change Orders use change_order_id (UUID) as the EVCS root identifier,
    and code (str) as the human-readable business identifier.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ChangeOrder, session)
        self.workflow = ChangeOrderWorkflowService()
        self.branch_service = BranchService(session)

    async def get_current(
        self, root_id: UUID, branch: str = "main"
    ) -> ChangeOrder | None:
        """Get the current active version for a root entity on a specific branch.

        Override parent method to use 'change_order_id' field instead of
        the auto-generated 'changeorder_id'.

        Uses clock_timestamp() instead of current_timestamp() because within
        a transaction, current_timestamp() returns the transaction start time,
        which may be before the valid_time lower bound of recently created records.
        """
        stmt = (
            select(ChangeOrder)
            .where(
                ChangeOrder.change_order_id == root_id,
                ChangeOrder.branch == branch,
                # Check if current actual timestamp is within valid_time range
                # clock_timestamp() returns the actual current time, not transaction start time
                cast(Any, ChangeOrder).valid_time.op("@>")(func.clock_timestamp()),
                cast(Any, ChangeOrder).deleted_at.is_(None),
            )
            .order_by(cast(Any, ChangeOrder).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        co = result.scalar_one_or_none()

        return co

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
        2. Creates a corresponding co-{code} branch in the SAME transaction
        3. Sets the branch_name field on the Change Order
        4. Returns the created Change Order

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
        code = co_data.get("code")
        project_id = co_data.get(
            "project_id"
        )  # Already a UUID from Pydantic validation

        # Generate a UUID for the change_order root
        root_id = uuid4()

        # Generate branch name from code
        branch_name = f"co-{code}"

        # Set branch_name in the data
        co_data["branch_name"] = branch_name

        # Create the Change Order on main branch using create_root
        change_order = await self.create_root(
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch="main",
            **co_data,
        )

        # Create the corresponding branch in the SAME transaction
        initial_status = co_data.get("status", "Draft")

        # Check if the initial status should lock the branch
        # (e.g., if CO is created directly with "Submitted for Approval" status)
        should_lock = initial_status != "Draft"

        branch = Branch(
            name=branch_name,
            project_id=project_id,
            type="change_order",
            locked=should_lock,
            created_by=actor_id,
        )
        self.session.add(branch)

        # Commit both CO and branch creation in single transaction
        await self.session.commit()
        await self.session.refresh(change_order)
        await self.session.refresh(branch)

        return change_order

    async def update_change_order(
        self,
        change_order_id: UUID,
        change_order_in: ChangeOrderUpdate,
        actor_id: UUID,
        control_date: datetime | None = None,
        branch: str | None = None,
    ) -> ChangeOrder:
        """Update a Change Order's metadata with workflow validation and branch locking.

        Creates a new version with the updated metadata.
        If branch is specified, updates on that branch (auto-forking from main if needed).
        If branch is not specified, updates on the current active branch.
        Validates status transitions via workflow service.
        Triggers branch lock/unlock based on status changes.

        Args:
            change_order_id: The change_order_id (UUID root identifier)
            change_order_in: Update data (partial)
            actor_id: User making the update
            control_date: Optional control date for bitemporal operations
            branch: Optional branch name to update on (defaults to current branch)

        Returns:
            Updated ChangeOrder

        Raises:
            ValueError: If Change Order not found, invalid branch, or invalid status transition
        """
        # Get the current version on any branch to find where it exists
        from sqlalchemy import select as sql_select

        # CRITICAL FIX: When control_date is provided (Time Machine mode), use it instead of clock_timestamp()
        # This ensures we find the Change Order that exists at the control_date, not at current time
        query_timestamp = control_date if control_date else func.clock_timestamp()

        # First try to find the CO on any branch
        # Use control_date if provided (Time Machine), otherwise use clock_timestamp()
        stmt = (
            sql_select(ChangeOrder)
            .where(
                ChangeOrder.change_order_id == change_order_id,
                # Check if query_timestamp is within valid_time range
                cast(Any, ChangeOrder).valid_time.op("@>")(query_timestamp),
                cast(Any, ChangeOrder).deleted_at.is_(None),
            )
            .order_by(cast(Any, ChangeOrder).valid_time.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        current = result.scalar_one_or_none()

        if not current:
            raise ValueError(
                f"Change Order {change_order_id} not found or has been deleted (query_timestamp={query_timestamp})"
            )

        # Filter None values from update data
        update_data = change_order_in.model_dump(exclude_unset=True)
        update_data.pop("control_date", None)
        update_data.pop(
            "branch", None
        )  # Remove branch from update data, we use it separately

        # Extract comment for audit log (not stored in ChangeOrder model)
        comment = update_data.pop("comment", None)

        # Determine target branch
        target_branch = branch if branch is not None else current.branch

        # Check if version exists on target branch
        stmt_target = (
            sql_select(ChangeOrder)
            .where(
                ChangeOrder.change_order_id == change_order_id,
                ChangeOrder.branch == target_branch,
                cast(Any, ChangeOrder).valid_time.op("@>")(query_timestamp),
                cast(Any, ChangeOrder).deleted_at.is_(None),
            )
            .order_by(cast(Any, ChangeOrder).valid_time.desc())
            .limit(1)
        )

        result_target = await self.session.execute(stmt_target)
        target_current = result_target.scalar_one_or_none()

        # Track if we auto-forked to avoid creating duplicate versions
        auto_forked = False

        # If no version on target branch and target is not main, auto-fork from main
        if target_current is None and target_branch != "main":
            # Try to fork from main
            stmt_main = (
                sql_select(ChangeOrder)
                .where(
                    ChangeOrder.change_order_id == change_order_id,
                    ChangeOrder.branch == "main",
                    cast(Any, ChangeOrder).valid_time.op("@>")(query_timestamp),
                    cast(Any, ChangeOrder).deleted_at.is_(None),
                )
                .order_by(cast(Any, ChangeOrder).valid_time.desc())
                .limit(1)
            )

            result_main = await self.session.execute(stmt_main)
            main_version = result_main.scalar_one_or_none()

            if main_version is None:
                raise ValueError(
                    f"Cannot update on branch '{target_branch}': no version found on main to fork from"
                )

            # Fork from main to target branch
            from app.core.branching.commands import CreateBranchCommand

            fork_cmd = CreateBranchCommand(  # type: ignore[type-var]
                entity_class=ChangeOrder,
                root_id=change_order_id,
                actor_id=actor_id,
                new_branch=target_branch,
                from_branch="main",
                control_date=control_date,
            )
            target_current = await fork_cmd.execute(self.session)
            auto_forked = True

            # Refresh the session to ensure the forked version is visible
            await self.session.refresh(target_current)

        # Check if status is being updated (use target_current if available, else current)
        old_status = target_current.status if target_current else current.status
        new_status = update_data.get("status", old_status)

        # Validate status transition via workflow service
        if old_status != new_status:
            is_valid = await self.workflow.is_valid_transition(old_status, new_status)
            if not is_valid:
                raise ValueError(
                    f"Invalid status transition: {old_status} → {new_status}"
                )

            # Check if editing is allowed in current status
            can_edit = await self.workflow.can_edit_on_status(old_status)

            # Check if title or description are being updated
            has_title = "title" in update_data
            has_description = "description" in update_data

            # Only check edit permission if title/description are being modified
            # CRITICAL FIX: Use proper parentheses to check (has_title OR has_description) AND (not can_edit)
            if (has_title or has_description) and not can_edit:
                raise ValueError(
                    f"Cannot edit Change Order details in status: {old_status}"
                )

        # If we auto-forked, directly update the forked version instead of creating a new one
        # This avoids creating 2 current versions on the branch
        if auto_forked:
            # Apply updates directly to the auto-forked version
            for field, value in update_data.items():
                setattr(target_current, field, value)

            await self.session.flush()
            await self.session.refresh(target_current)
            updated_co = target_current
        else:
            # Use update method from BranchableService (creates new version)
            updated_co = await self.update(
                root_id=change_order_id,
                actor_id=actor_id,
                branch=target_branch,
                control_date=control_date,
                **update_data,
            )

        # Create audit log entry for status transition
        if old_status != new_status:
            # Create audit log entry
            audit_entry = ChangeOrderAuditLog(
                change_order_id=change_order_id,
                old_status=old_status,
                new_status=new_status,
                comment=comment,
                changed_by=actor_id,
            )
            self.session.add(audit_entry)

        # Trigger branch lock/unlock based on status change
        if old_status != new_status and updated_co and updated_co.branch_name:
            if await self.workflow.should_lock_on_transition(old_status, new_status):
                await self.branch_service.lock(
                    name=updated_co.branch_name,
                    project_id=updated_co.project_id,
                )
            elif await self.workflow.should_unlock_on_transition(
                old_status, new_status
            ):
                await self.branch_service.unlock(
                    name=updated_co.branch_name,
                    project_id=updated_co.project_id,
                )

        if not updated_co:
            raise ValueError(f"Failed to update Change Order {change_order_id}")

        return updated_co

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
            # Get current active versions (exclude empty ranges)
            stmt = stmt.where(
                func.upper(cast(Any, ChangeOrder).valid_time).is_(None),
                func.not_(func.isempty(ChangeOrder.valid_time)),  # Exclude empty ranges
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
                # Check if actual current timestamp is within valid_time range
                cast(Any, ChangeOrder).valid_time.op("@>")(func.clock_timestamp()),
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
            raise ValueError(
                f"No active version found on source branch {source_branch}"
            )

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

    async def _to_public(self, co: ChangeOrder) -> "ChangeOrderPublic":
        """Convert a ChangeOrder domain model to ChangeOrderPublic schema with workflow metadata.

        This method enriches the domain model with workflow information from the workflow service
        and branch lock status, providing the frontend with all data needed for workflow-aware UI.

        Args:
            co: ChangeOrder domain model

        Returns:
            ChangeOrderPublic schema with workflow metadata populated
        """
        from app.models.schemas.change_order import ChangeOrderPublic

        # Get available transitions from workflow service
        available_transitions = await self.workflow.get_available_transitions(co.status)

        # Check if editing is allowed in current status
        can_edit_status = await self.workflow.can_edit_on_status(co.status)

        # Check if branch is locked
        branch_locked = False
        if co.branch_name:
            try:
                branch = await self.branch_service.get_by_name_and_project(
                    name=co.branch_name,
                    project_id=co.project_id,
                )
                branch_locked = branch.locked
            except Exception:
                # If branch lookup fails, assume not locked
                branch_locked = False

        # Convert domain model to schema
        public_data = {
            "code": co.code,
            "project_id": co.project_id,
            "title": co.title,
            "description": co.description,
            "justification": co.justification,
            "effective_date": co.effective_date,
            "status": co.status,
            "change_order_id": co.change_order_id,
            "id": co.id,
            "created_by": co.created_by,
            "created_at": co.created_at,
            "updated_by": None,
            "updated_at": None,
            "branch": co.branch,
            "parent_id": co.parent_id,
            "deleted_at": co.deleted_at,
            "available_transitions": available_transitions,
            "can_edit_status": can_edit_status,
            "branch_locked": branch_locked,
        }

        return ChangeOrderPublic(**public_data)
