"""ChangeOrderService for Change Order business logic.

Provides Change Order specific operations including automatic branch
creation on CO creation and workflow-driven branch locking.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

from sqlalchemy import cast as sql_cast
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import (
    CreateChangeOrderAuditLogCommand,
    CreateVersionCommand,
    UpdateChangeOrderStatusCommand,
)
from app.models.domain.branch import Branch
from app.models.domain.change_order import ChangeOrder
from app.models.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate
from app.services.branch_service import BranchService
from app.services.change_order_workflow_service import ChangeOrderWorkflowService
from app.services.cost_element_service import CostElementService
from app.services.entity_discovery_service import EntityDiscoveryService
from app.services.wbe import WBEService

if TYPE_CHECKING:
    from app.models.schemas.change_order import ChangeOrderPublic
    from app.models.schemas.impact_analysis import ImpactAnalysisResponse

logger = logging.getLogger(__name__)


class ChangeOrderService(BranchableService[ChangeOrder]):  # type: ignore[type-var]
    """Service for Change Order entity operations.

    Extends BranchableService with Change Order specific methods.
    Supports full EVCS capabilities including branching.

    Key Features:
    - Workflow state management: Draft → Submitted → Approved → Implemented
    - Project-scoped: All COs belong to a specific project
    - Automatic branch creation: Creates BR-{code} branch on CO creation
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

        Uses the same pattern as WBEService: finds the version with an open
        upper bound on valid_time, which represents the current/latest version
        on this branch. This works correctly regardless of the valid_time
        lower bound (past, present, or future dates).
        """
        stmt = (
            select(ChangeOrder)
            .where(
                ChangeOrder.change_order_id == root_id,
                ChangeOrder.branch == branch,
                func.upper(cast(Any, ChangeOrder).valid_time).is_(None),  # Open upper bound
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
        2. Creates a corresponding BR-{code} branch in the SAME transaction
        3. Returns the created Change Order (main branch version)

        Args:
            change_order_in: Change Order creation data
            actor_id: User creating the Change Order
            control_date: Optional control date for valid_time (defaults to now)

        Returns:
            Created ChangeOrder

        """
        # Extract control_date from schema if not provided
        if control_date is None:
            control_date = getattr(change_order_in, "control_date", None)
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
        branch_name = f"BR-{code}"

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

        # Create the corresponding branch entity using CreateVersionCommand
        # This ensures proper valid_time setting based on control_date
        branch_root_id = uuid4()

        branch_cmd = CreateVersionCommand(
            entity_class=Branch,
            root_id=branch_root_id,
            actor_id=actor_id,
            control_date=control_date,
            # branch="main", # REMOVED: Branch entity is not checking into a branch itself

            # Fields for Branch entity
            branch_id=branch_root_id,
            name=branch_name,
            project_id=project_id,
            type="change_order",
            locked=should_lock,
        )
        # Note: CreateVersionCommand handles session.add
        branch = await branch_cmd.execute(self.session)

        # Commit both CO and branch creation in single transaction
        await self.session.commit()
        await self.session.refresh(change_order)
        await self.session.refresh(branch)

        # Phase 6 Task #1: Trigger automatic impact analysis on creation
        # This runs impact analysis even in Draft status to provide early feedback
        # We do this AFTER commit so the change_order and branch exist in the database
        # Note: Impact analysis may fail if project data is incomplete (e.g., during seeding)
        # This is acceptable - the change order is still created successfully
        try:
            await self._run_impact_analysis(change_order, branch_name)
            await self.session.commit()
        except Exception as e:
            # Log but don't fail the change order creation
            logger.warning(
                f"Impact analysis failed for change order {change_order.code}: {e}. "
                f"Change order created successfully in Draft status."
            )
            await self.session.rollback()
        await self.session.refresh(change_order)

        return change_order

    async def update_change_order(
        self,
        change_order_id: UUID,
        change_order_in: ChangeOrderUpdate,
        actor_id: UUID,
        branch: str | None = None,
        control_date: datetime | None = None,
    ) -> ChangeOrder:
        """Update a Change Order's metadata with workflow validation and branch locking.

        Creates a new version with the updated metadata.
        If branch is specified, updates on that branch (auto-forking from main if needed).
        If branch is NOT specified, defaults to "main".

        Args:
            change_order_id: The change_order_id (UUID root identifier)
            change_order_in: The updated metadata
            actor_id: The user performing the update
            branch: Optional branch name to update on
            control_date: Optional control date for valid_time (defaults to now)

        Raises:
            ValueError: If Change Order not found, invalid branch, or invalid status transition
        """
        # Extract control_date from schema if not provided
        if control_date is None:
            control_date = getattr(change_order_in, "control_date", None)
        # Get the current version on any branch to find where it exists
        from sqlalchemy import select as sql_select

        # CRITICAL FIX: When control_date is provided (Time Machine mode), use it instead of clock_timestamp()
        # This ensures we find the Change Order that exists at the control_date, not at current time
        query_timestamp = control_date if control_date else func.clock_timestamp()
        query_timestamp_tstz = sql_cast(query_timestamp, TIMESTAMP(timezone=True))

        # First try to find the CO on any branch
        # Use control_date if provided (Time Machine), otherwise use clock_timestamp()
        stmt = (
            sql_select(ChangeOrder)
            .where(
                ChangeOrder.change_order_id == change_order_id,
                # Check if query_timestamp is within valid_time range
                cast(Any, ChangeOrder).valid_time.op("@>")(query_timestamp_tstz),
                func.lower(cast(Any, ChangeOrder).valid_time) <= query_timestamp_tstz,
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
                cast(Any, ChangeOrder).valid_time.op("@>")(query_timestamp_tstz),
                func.lower(cast(Any, ChangeOrder).valid_time) <= query_timestamp_tstz,
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
                    cast(Any, ChangeOrder).valid_time.op("@>")(query_timestamp_tstz),
                    func.lower(cast(Any, ChangeOrder).valid_time) <= query_timestamp_tstz,
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
            # Direct UpdateCommand usage to bypass branch lock check for status updates
            # (since ChangeOrder itself may lock the branch it resides on)
            from app.core.branching.commands import UpdateCommand

            cmd = UpdateCommand(  # type: ignore[type-var]
                entity_class=self.entity_class,
                root_id=change_order_id,
                actor_id=actor_id,
                branch=target_branch,
                control_date=control_date,
                updates=update_data,
            )
            updated_co = await cmd.execute(self.session)

        # Create audit log entry for status transition
        if old_status != new_status:
            # Use Command to create audit log entry (RSC compliance)
            audit_cmd = CreateChangeOrderAuditLogCommand(
                change_order_id=change_order_id,
                old_status=old_status,
                new_status=new_status,
                actor_id=actor_id,
                comment=comment,
            )
            await audit_cmd.execute(self.session)

        # Trigger branch lock/unlock based on status change
        if old_status != new_status and updated_co and updated_co.branch_name:
            if await self.workflow.should_lock_on_transition(old_status, new_status):
                await self.branch_service.lock(
                    name=updated_co.branch_name,
                    project_id=updated_co.project_id,
                    actor_id=actor_id,
                )
            elif await self.workflow.should_unlock_on_transition(
                old_status, new_status
            ):
                await self.branch_service.unlock(
                    name=updated_co.branch_name,
                    project_id=updated_co.project_id,
                    actor_id=actor_id,
                )
            # Refresh updated_co as it may be expired by commit in lock/unlock
            await self.session.refresh(updated_co)

        if not updated_co:
            raise ValueError(f"Failed to update Change Order {change_order_id}")

        return updated_co
    async def archive_change_order_branch(
        self,
        change_order_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        """Archive (soft-delete) a Change Order's branch.

        Only allowed for Change Orders in "Implemented" or "Rejected" status.
        Hides the branch from active lists while preserving history.

        Args:
            change_order_id: Change Order ID
            actor_id: User performing the archive
            control_date: Optional control date for bitemporal operations

        Raises:
            ValueError: If Change Order not found or not in allowed status
        """
        # Get current change order
        co = await self.get_current(change_order_id)
        if not co:
            raise ValueError(f"Change Order {change_order_id} not found")

        # Validate status
        # Validate status
        if co.status not in ["Implemented", "Rejected"]:  # pragma: no cover
            raise ValueError(
                f"Cannot archive active Change Order. "
                f"Current status: {co.status}. "
                f"Must be 'Implemented' or 'Rejected'."
            )

        # Get branch name
        if not co.branch_name:
             # Should not happen for valid COs, but handle gracefully
             logger.warning(
                 f"Change Order {co.code} has no branch_name. Nothing to archive."
             )
             return

        # Archive the branch using BranchService soft_delete
        # BranchService inherits from TemporalService which provides soft_delete
        # We need to find the branch first to get its ID, as soft_delete usually takes ID
        # But TemporalService soft_delete takes root_id.

        # Find the branch to get its root_id (branch_id)
        branch = await self.branch_service.get_by_name_and_project(
            co.branch_name, co.project_id
        )

        # Soft delete the branch
        await self.branch_service.soft_delete(
            entity_id=branch.branch_id,
            actor_id=actor_id,
            control_date=control_date
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
                func.upper(cast(Any, ChangeOrder).valid_time).is_(None),  # Open upper bound
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
        control_date: datetime | None = None,
    ) -> ChangeOrder:
        """Merge the Change Order's branch into the target branch.

        Orchestrates the merge of ALL branch content (Change Order, WBEs,
        CostElements, Projects) from the source branch to the target branch.

        Infers the source branch from the Change Order's code.

        Args:
            change_order_id: Change Order ID
            actor_id: User performing merge
            target_branch: Branch to merge INTO (default: main)

        Returns:
            The merged Change Order version on the target branch with status "Implemented"

        Raises:
            ValueError: If Change Order not found or no active version on source branch
            Exception: If merge fails (transaction is rolled back)
        """
        # 1. Get current version (from main or source) to find the code
        # We check "main" first to get the metadata
        current = await self.get_current(change_order_id, branch=target_branch)

        if not current:
            # Try to find it on any branch to get the code?
            # Or just require it to exist on target?
            # If it's a new CO branch not yet on main?
            # But create_change_order creates on main AND branch. So it should be on main.
            raise ValueError("Change Order not found on target branch")

        source_branch = f"BR-{current.code}"

        # Check if source branch has active version
        source_version = await self.get_current(change_order_id, branch=source_branch)
        if not source_version:
            raise ValueError(
                f"No active version found on source branch {source_branch}"
            )

        # Detect merge conflicts before proceeding
        conflicts = await self._detect_all_merge_conflicts(
            source_branch, target_branch
        )
        if conflicts:
            from app.core.branching.exceptions import MergeConflictError

            raise MergeConflictError(conflicts)

        # 2. Discover all entities in the source branch (including soft-deleted)
        discovery_service = EntityDiscoveryService(self.session)
        all_wbes = await discovery_service.discover_all_wbes(source_branch)
        all_cost_elements = await discovery_service.discover_all_cost_elements(
            source_branch
        )

        # 3. Merge each entity type, handling soft-deletes specially
        # Merge WBEs
        wbe_service = WBEService(self.session)
        for wbe in all_wbes:
            if wbe.deleted_at is not None:
                # Soft-deleted on source - soft-delete on target too
                await wbe_service.soft_delete(
                    root_id=wbe.wbe_id,
                    actor_id=actor_id,
                    branch=target_branch,
                    control_date=control_date,
                )
            else:
                # Active on source - merge normally
                await wbe_service.merge_branch(
                    root_id=wbe.wbe_id,
                    actor_id=actor_id,
                    source_branch=source_branch,
                    target_branch=target_branch,
                    control_date=control_date,
                )

        # Merge CostElements
        ce_service = CostElementService(self.session)
        for ce in all_cost_elements:
            if ce.deleted_at is not None:
                # Soft-deleted on source - soft-delete on target too
                await ce_service.soft_delete(
                    cost_element_id=ce.cost_element_id,
                    actor_id=actor_id,
                    branch=target_branch,
                    control_date=control_date,
                )
            else:
                # Active on source - merge normally
                await ce_service.merge_branch(
                    root_id=ce.cost_element_id,
                    actor_id=actor_id,
                    source_branch=source_branch,
                    target_branch=target_branch,
                    control_date=control_date,
                )

        # 4. Merge the Change Order entity itself
        merged_co = await self.merge_branch(
            root_id=change_order_id,
            actor_id=actor_id,
            source_branch=source_branch,
            target_branch=target_branch,
            control_date=control_date,
        )

        # 5. Update CO status to "Implemented" using Command (RSC compliance)
        status_cmd = UpdateChangeOrderStatusCommand(
            change_order_id=change_order_id,
            new_status="Implemented",
            branch=target_branch,
        )
        await status_cmd.execute(self.session)
        await self.session.refresh(merged_co)

        return merged_co

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

    async def submit_for_approval(
        self,
        change_order_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        comment: str | None = None,
    ) -> ChangeOrder:
        """Submit a change order for approval with impact calculation and approver assignment.

        Context: Workflow transition from Draft to Submitted for Approval.
        Calculates financial impact, assigns approver based on impact level,
        sets SLA deadline, and locks the branch.

        Args:
            change_order_id: UUID of the change order
            actor_id: User submitting for approval
            branch: Branch name (default: main)
            comment: Optional comment for audit log

        Returns:
            Updated ChangeOrder with impact level and approver assigned

        Raises:
            ValueError: If change order not found or invalid status transition
        """

        # Get current change order
        co = await self.get_current(change_order_id, branch=branch)
        if not co:
            raise ValueError(f"Change Order {change_order_id} not found")

        # Validate status transition
        if not await self.workflow.is_valid_transition(co.status, "Submitted for Approval"):
            raise ValueError(
                f"Cannot submit CO with status '{co.status}' for approval. "
                f"Current status must be 'Draft' or 'Rejected'."
            )

        # Phase 6 Task #3: Validate impact analysis completed
        if co.impact_analysis_status != "completed":
            raise ValueError(
                f"Cannot submit change order for approval: "
                f"impact analysis must be completed first. "
                f"Current status: {co.impact_analysis_status}"
            )

        if co.impact_level is None:
            raise ValueError(
                "Cannot submit change order for approval: "
                "impact level must be calculated first. "
                "Please ensure impact analysis has been completed."
            )

        if co.assigned_approver_id is None:
            raise ValueError(
                f"Cannot submit change order for approval: "
                f"no approver has been assigned for {co.impact_level} impact level. "
                f"Please contact your administrator to configure the approval matrix."
            )

        # Phase 6 Task #3: Use pre-calculated impact level and approver
        # These were already calculated during CO creation in _run_impact_analysis
        impact_level = co.impact_level

        # Calculate SLA deadline (business days)

        SLA_BUSINESS_DAYS = {
            "LOW": 3,
            "MEDIUM": 5,
            "HIGH": 7,
            "CRITICAL": 10,
        }

        sla_days = SLA_BUSINESS_DAYS.get(impact_level, 5)
        sla_due_date = self._add_business_days(datetime.now(), sla_days)

        # Update change order with SLA tracking
        old_status = co.status
        co.sla_assigned_at = datetime.now()
        co.sla_due_date = sla_due_date
        co.sla_status = "pending"
        co.status = "Submitted for Approval"

        # Record audit log using Command (RSC compliance)
        audit_cmd = CreateChangeOrderAuditLogCommand(
            change_order_id=change_order_id,
            old_status=old_status,
            new_status="Submitted for Approval",
            actor_id=actor_id,
            comment=comment or f"Submitted for approval with {impact_level} impact",
        )
        await audit_cmd.execute(self.session)

        # Lock the branch
        if co.branch_name:
            await self.branch_service.lock(
                name=co.branch_name,
                project_id=co.project_id,
                actor_id=actor_id,
            )

        await self.session.commit()
        await self.session.refresh(co)

        return co

    async def approve_change_order(
        self,
        change_order_id: UUID,
        approver_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        comments: str | None = None,
    ) -> ChangeOrder:
        """Approve a change order and transition to Approved status.

        Context: Workflow transition from Under Review to Approved.
        Validates approver authority, records approval, and updates status.

        Args:
            change_order_id: UUID of the change order
            approver_id: User ID of the approver (for validation)
            actor_id: User performing the approval (should match approver_id)
            branch: Branch name (default: main)
            comments: Optional approval comments

        Returns:
            Updated ChangeOrder with Approved status

        Raises:
            ValueError: If change order not found, invalid status, or insufficient authority
        """
        from app.services.approval_matrix_service import ApprovalMatrixService
        from app.services.user import UserService

        # Get current change order
        co = await self.get_current(change_order_id, branch=branch)
        if not co:
            raise ValueError(f"Change Order {change_order_id} not found")

        # Validate status transition
        if not await self.workflow.is_valid_transition(co.status, "Approved"):
            raise ValueError(
                f"Cannot approve CO with status '{co.status}'. "
                f"Current status must be 'Under Review'."
            )

        # Get approver user object
        user_service = UserService(self.session)
        approver = await user_service.get_user(approver_id)
        if not approver:
            raise ValueError(f"Approver with ID {approver_id} not found")

        # Validate approver authority
        approval_service = ApprovalMatrixService(self.session)
        can_approve = await approval_service.can_approve(approver, co)

        if not can_approve:
            raise ValueError(
                f"User {approver_id} does not have sufficient authority "
                f"to approve this change order with impact level {co.impact_level}."
            )

        # Verify the assigned approver is the one approving
        if co.assigned_approver_id != approver_id:
            raise ValueError(
                f"This change order is assigned to approver {co.assigned_approver_id}. "
                f"User {approver_id} is not authorized to approve it."
            )

        # Update status to Approved
        old_status = co.status
        co.status = "Approved"

        # Record audit log using Command (RSC compliance)
        audit_cmd = CreateChangeOrderAuditLogCommand(
            change_order_id=change_order_id,
            old_status=old_status,
            new_status="Approved",
            actor_id=actor_id,
            comment=comments or "Change order approved",
        )
        await audit_cmd.execute(self.session)

        await self.session.commit()
        await self.session.refresh(co)

        return co

    async def reject_change_order(
        self,
        change_order_id: UUID,
        rejecter_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        comments: str | None = None,
    ) -> ChangeOrder:
        """Reject a change order and transition to Rejected status.

        Context: Workflow transition from Under Review to Rejected.
        Validates rejecter authority, records rejection, unlocks the branch.

        Args:
            change_order_id: UUID of the change order
            rejecter_id: User ID of the rejecter (for validation)
            actor_id: User performing the rejection (should match rejecter_id)
            branch: Branch name (default: main)
            comments: Optional rejection comments

        Returns:
            Updated ChangeOrder with Rejected status and unlocked branch

        Raises:
            ValueError: If change order not found, invalid status, or insufficient authority
        """
        from app.services.approval_matrix_service import ApprovalMatrixService
        from app.services.user import UserService

        # Get current change order
        co = await self.get_current(change_order_id, branch=branch)
        if not co:
            raise ValueError(f"Change Order {change_order_id} not found")

        # Validate status transition
        if not await self.workflow.is_valid_transition(co.status, "Rejected"):
            raise ValueError(
                f"Cannot reject CO with status '{co.status}'. "
                f"Current status must be 'Under Review'."
            )

        # Get rejecter user object
        user_service = UserService(self.session)
        rejecter = await user_service.get_user(rejecter_id)
        if not rejecter:
            raise ValueError(f"Rejecter with ID {rejecter_id} not found")

        # Validate rejecter authority (same as approver authority)
        approval_service = ApprovalMatrixService(self.session)
        can_reject = await approval_service.can_approve(rejecter, co)

        if not can_reject:
            raise ValueError(
                f"User {rejecter_id} does not have sufficient authority "
                f"to reject this change order with impact level {co.impact_level}."
            )

        # Update status to Rejected
        old_status = co.status
        co.status = "Rejected"

        # Record audit log using Command (RSC compliance)
        audit_cmd = CreateChangeOrderAuditLogCommand(
            change_order_id=change_order_id,
            old_status=old_status,
            new_status="Rejected",
            actor_id=actor_id,
            comment=comments or "Change order rejected",
        )
        await audit_cmd.execute(self.session)

        # Unlock the branch
        if co.branch_name:
            await self.branch_service.unlock(
                name=co.branch_name,
                project_id=co.project_id,
                actor_id=actor_id,
            )

        await self.session.commit()
        await self.session.refresh(co)

        return co

    async def recover_change_order(
        self,
        change_order_id: UUID,
        impact_level: str,
        assigned_approver_id: UUID,
        skip_impact_analysis: bool,
        recovery_reason: str,
        actor_id: UUID,
        branch: str = "main",
    ) -> ChangeOrder:
        """Recover a stuck change order workflow (admin only).

        Context: Admin operation to recover stuck workflows when impact analysis
        fails or the change order gets stuck in an intermediate state. This allows
        manual override of impact level and approver assignment.

        Args:
            change_order_id: UUID of the stuck change order
            impact_level: Manual impact level (LOW/MEDIUM/HIGH/CRITICAL)
            assigned_approver_id: User to assign as approver (use User.id, not User.user_id)
            skip_impact_analysis: Skip impact analysis and use manual values
            recovery_reason: Explanation for recovery (audit trail)
            actor_id: Admin user performing recovery (use User.id, not User.user_id)
            branch: Branch name (default: main)

        Returns:
            Updated ChangeOrder with recovered workflow state

        Raises:
            ValueError: If change order not found, invalid state, or invalid data
        """
        from app.services.user import UserService

        # Get current change order
        co = await self.get_current(change_order_id, branch=branch)
        if not co:
            raise ValueError(f"Change Order {change_order_id} not found")

        # Validate stuck state (no available transitions or missing required fields)
        transitions = await self.workflow.get_available_transitions(co.status)
        is_stuck = (
            not transitions
            or not co.impact_level
            or not co.assigned_approver_id
            or co.impact_analysis_status == "in_progress"
        )

        if not is_stuck:
            raise ValueError(
                f"Change Order {change_order_id} is not stuck. "
                f"Current status: {co.status}, "
                f"Impact level: {co.impact_level}, "
                f"Approver: {co.assigned_approver_id}, "
                f"Analysis: {co.impact_analysis_status}, "
                f"Available transitions: {transitions}"
            )

        # Get approver user object
        user_service = UserService(self.session)
        approver = await user_service.get_by_id(assigned_approver_id)
        if not approver:
            raise ValueError(f"Approver with ID {assigned_approver_id} not found")

        # Validate impact level
        valid_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if impact_level not in valid_levels:
            raise ValueError(
                f"Invalid impact level: {impact_level}. Must be one of {valid_levels}"
            )

        # Store old values for audit
        old_status = co.status
        old_impact_level = co.impact_level
        old_approver = co.assigned_approver_id
        old_analysis_status = co.impact_analysis_status

        # Update change order with recovery values
        co.impact_level = impact_level
        co.assigned_approver_id = assigned_approver_id
        co.impact_analysis_status = "skipped" if skip_impact_analysis else "completed"

        # Transition to appropriate status for approval
        if co.status == "Draft":
            co.status = "Under Review"
        elif co.status in ("Submitted for Approval", "Under Review"):
            co.status = "Under Review"

        # Record audit log with detailed recovery information
        audit_comment = (
            f"Workflow recovery by admin. "
            f"Reason: {recovery_reason}. "
            f"Changes: "
            f"status '{old_status}' → '{co.status}', "
            f"impact_level '{old_impact_level}' → '{impact_level}', "
            f"approver '{old_approver}' → '{assigned_approver_id}', "
            f"analysis '{old_analysis_status}' → '{co.impact_analysis_status}'"
        )

        audit_cmd = CreateChangeOrderAuditLogCommand(
            change_order_id=change_order_id,
            old_status=old_status,
            new_status=co.status,
            actor_id=actor_id,
            comment=audit_comment,
        )
        await audit_cmd.execute(self.session)

        await self.session.commit()
        await self.session.refresh(co)

        logger.info(
            f"Change order {change_order_id} recovered by user {actor_id}. "
            f"Status: {old_status} → {co.status}, "
            f"Impact: {impact_level}, Approver: {assigned_approver_id}"
        )

        return co

    async def get_pending_approvals(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        branch: str = "main",
        branch_mode: Any | None = None,
    ) -> tuple[list[ChangeOrder], int]:
        """Get change orders pending approval for a specific user.

        Context: Used for dashboard showing pending approvals.
        Filters by assigned_approver_id and status in (Submitted for Approval, Under Review).

        Args:
            user_id: User ID to filter by (assigned approver)
            skip: Number of records to skip
            limit: Maximum records to return
            branch: Branch to query (default: "main")
            branch_mode: Optional BranchMode enum for merged/isolated filtering

        Returns:
            Tuple of (list of Change Orders, total count)
        """
        from typing import Any, cast

        from sqlalchemy import func

        # Build query for pending approvals
        stmt = select(ChangeOrder).where(
            ChangeOrder.assigned_approver_id == user_id,
            ChangeOrder.status.in_(["Submitted for Approval", "Under Review"]),
            ChangeOrder.branch == branch,
            func.upper(cast(Any, ChangeOrder).valid_time).is_(None),  # Current versions
            cast(Any, ChangeOrder).deleted_at.is_(None),
        )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)
        stmt = stmt.order_by(ChangeOrder.sla_due_date.asc())

        result = await self.session.execute(stmt)
        change_orders = result.scalars().all()

        return list(change_orders), total

    async def _run_impact_analysis(
        self, change_order: ChangeOrder, branch_name: str
    ) -> None:
        """Run automatic impact analysis for a change order.

        Context: Phase 6 Task #1 - Trigger impact analysis on CO creation.
        Analyzes financial and schedule impact by comparing main branch with
        change order branch. Stores results in impact_analysis_results field.

        Args:
            change_order: The ChangeOrder domain object (already created and committed)
            branch_name: Name of the change order branch (e.g., "BR-CO-2026-001")

        Side effects:
            - Updates change_order.impact_analysis_status in database
            - Updates change_order.impact_analysis_results (JSONB) in database
            - Handles errors gracefully without preventing CO creation
        """
        from sqlalchemy import update

        from app.services.impact_analysis_service import ImpactAnalysisService

        # Set initial status using direct UPDATE
        update_stmt = (
            update(ChangeOrder)
            .where(ChangeOrder.id == change_order.id)
            .values(impact_analysis_status="in_progress")
        )
        await self.session.execute(update_stmt)
        await self.session.commit()
        await self.session.refresh(change_order)

        try:
            # Run impact analysis
            impact_service = ImpactAnalysisService(self.session)
            impact_analysis = await impact_service.analyze_impact(
                change_order.change_order_id, branch_name
            )

            # Phase 6 Task #2: Calculate impact score and level
            impact_score = self._calculate_impact_score(impact_analysis)
            impact_level = self._map_score_to_impact_level(impact_score)

            # Phase 6 Task #3: Assign approver based on impact level
            assigned_approver_id = await self._assign_approver_for_impact(
                change_order.project_id, impact_level
            )

            # TODO: Send notification to assigned approver (email + in-app)
            # This is a placeholder for the notification system
            # Will be implemented in Phase 7: Notification System
            if assigned_approver_id:
                logger.info(
                    f"Approver {assigned_approver_id} assigned to change order {change_order.code} "
                    f"with {impact_level} impact. Notification pending."
                )

            # Store results as JSONB using direct UPDATE (convert Pydantic model to dict)
            # Use mode='json' to convert UUID objects to strings for JSON serialization
            update_stmt = (
                update(ChangeOrder)
                .where(ChangeOrder.id == change_order.id)
                .values(
                    impact_analysis_results=impact_analysis.model_dump(mode='json'),
                    impact_analysis_status="completed",
                    impact_score=impact_score,
                    impact_level=impact_level,
                    assigned_approver_id=assigned_approver_id,
                )
            )
            await self.session.execute(update_stmt)
            await self.session.commit()
            await self.session.refresh(change_order)

            logger.info(
                f"Impact analysis completed for change order {change_order.code}: "
                f"score={impact_score}, level={impact_level}, "
                f"approver={assigned_approver_id}, "
                f"budget_delta={impact_analysis.kpi_scorecard.budget_delta.delta}, "
                f"revenue_delta={impact_analysis.kpi_scorecard.revenue_delta.delta}"
            )

        except ValueError as e:
            # Expected errors (e.g., project not found, no data yet)
            update_stmt = (
                update(ChangeOrder)
                .where(ChangeOrder.id == change_order.id)
                .values(
                    impact_analysis_results={
                        "error": str(e),
                        "reason": "No project data available for analysis",
                    },
                    impact_analysis_status="skipped",
                )
            )
            await self.session.execute(update_stmt)
            await self.session.commit()
            await self.session.refresh(change_order)

            logger.warning(
                f"Impact analysis skipped for change order {change_order.code}: {e}"
            )

        except Exception as e:
            # Unexpected errors - don't prevent CO creation
            update_stmt = (
                update(ChangeOrder)
                .where(ChangeOrder.id == change_order.id)
                .values(
                    impact_analysis_results={
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    impact_analysis_status="failed",
                )
            )
            await self.session.execute(update_stmt)
            await self.session.commit()
            await self.session.refresh(change_order)

            logger.error(
                f"Impact analysis failed for change order {change_order.code}: {e}",
                exc_info=True,
            )

    async def _assign_approver_for_impact(
        self, project_id: UUID, impact_level: str
    ) -> UUID | None:
        """Assign an approver based on impact level using ApprovalMatrix.

        Context: Phase 6 Task #3 - Approver assignment on CO creation.
        Queries the ApprovalMatrixService to find an eligible approver for the
        given impact level within the project's department.

        Args:
            project_id: Project ID to find department for
            impact_level: Calculated impact level (LOW/MEDIUM/HIGH/CRITICAL)

        Returns:
            User ID of assigned approver, or None if no approver found

        Side effects:
            - Logs assignment success/failure
            - Returns None gracefully if no approver configured
        """
        from app.services.approval_matrix_service import ApprovalMatrixService

        try:
            approval_service = ApprovalMatrixService(self.session)
            approver_id = await approval_service.get_approver_for_impact(
                project_id, impact_level
            )

            if approver_id:
                logger.info(
                    f"Assigned approver {approver_id} for project {project_id} "
                    f"with {impact_level} impact level"
                )
            else:
                logger.warning(
                    f"No approver found for project {project_id} with {impact_level} impact level"
                )

            return approver_id

        except Exception as e:
            # Log error but don't fail the entire impact analysis
            logger.error(
                f"Failed to assign approver for project {project_id}: {e}",
                exc_info=True,
            )
            return None

    def _calculate_impact_score(self, impact_analysis: "ImpactAnalysisResponse") -> Decimal:
        """Calculate impact severity score from KPI scorecard.

        Context: Phase 6 Task #2 - Weighted impact score calculation.
        Combines budget, schedule, revenue, and EVM metrics into a single score.

        Args:
            impact_analysis: ImpactAnalysisResponse with KPI scorecard

        Returns:
            Impact severity score (Decimal). Higher = more severe impact.

        Algorithm:
            - Budget impact (40% weight): budget_delta.delta_percent
            - Schedule impact (30% weight): schedule_duration.delta_percent
            - Revenue impact (20% weight): revenue_delta.delta_percent
            - EVM degradation (10% weight): CPI + SPI negative deltas only

        Note:
            - Only negative EVM deltas contribute to score (degradation)
            - All values are absolute (magnitude matters, not direction)
        """
        kpi = impact_analysis.kpi_scorecard

        # Budget impact (40% weight)
        budget_delta_percent = float(kpi.budget_delta.delta_percent or 0.0)
        budget_score = abs(budget_delta_percent) * 0.4

        # Schedule impact (30% weight)
        schedule_delta_percent = (
            float(kpi.schedule_duration.delta_percent or 0.0)
            if kpi.schedule_duration
            else 0.0
        )
        schedule_score = abs(schedule_delta_percent) * 0.3

        # Revenue impact (20% weight)
        revenue_delta_percent = float(kpi.revenue_delta.delta_percent or 0.0)
        revenue_score = abs(revenue_delta_percent) * 0.2

        # EVM degradation (10% weight) - only negative deltas
        cpi_delta = float(kpi.cpi.delta if kpi.cpi else 0.0)
        spi_delta = float(kpi.spi.delta if kpi.spi else 0.0)
        # Only count negative EVM changes (degradation)
        evm_degradation = abs(min(cpi_delta, 0) + min(spi_delta, 0))
        evm_score = evm_degradation * 0.1

        # Calculate total score
        total_score = budget_score + schedule_score + revenue_score + evm_score

        # Round to 2 decimal places and return as Decimal
        return Decimal(str(round(total_score, 2)))

    def _map_score_to_impact_level(self, score: Decimal) -> str:
        """Map impact score to impact level.

        Context: Phase 6 Task #2 - Impact level classification.
        Maps numeric score to LOW/MEDIUM/HIGH/CRITICAL levels.

        Args:
            score: Impact severity score (Decimal)

        Returns:
            Impact level string: LOW, MEDIUM, HIGH, or CRITICAL

        Thresholds:
            - Score < 10: LOW
            - Score 10-30: MEDIUM
            - Score 30-50: HIGH
            - Score >= 50: CRITICAL
        """
        # Import ImpactLevel constants for consistency
        from app.models.domain.change_order import ImpactLevel

        if score < 10:
            return ImpactLevel.LOW
        elif score < 30:
            return ImpactLevel.MEDIUM
        elif score < 50:
            return ImpactLevel.HIGH
        else:
            return ImpactLevel.CRITICAL

    def _add_business_days(self, start_date: datetime, days: int) -> datetime:
        """Add business days to a date, excluding weekends.

        Args:
            start_date: Starting date
            days: Number of business days to add

        Returns:
            Date with business days added
        """
        from datetime import timedelta

        current_date = start_date
        days_added = 0

        while days_added < days:
            current_date += timedelta(days=1)
            # Monday=0, Friday=4 in Python weekday()
            if current_date.weekday() < 5:  # Monday through Friday
                days_added += 1

        return current_date

    def _calculate_business_days_remaining(
        self, from_date: datetime, to_date: datetime
    ) -> int:
        """Calculate the number of business days between two dates.

        Args:
            from_date: Starting date
            to_date: End date

        Returns:
            Number of business days (negative if to_date is before from_date)
        """
        from datetime import timedelta

        # Normalize timezones to prevent "can't subtract offset-naive and offset-aware datetimes" error
        # If one is aware and the other is naive, assume the naive one is in the same timezone
        if from_date.tzinfo is not None and to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=from_date.tzinfo)
        elif from_date.tzinfo is None and to_date.tzinfo is not None:
            from_date = from_date.replace(tzinfo=to_date.tzinfo)

        if from_date >= to_date:
            return 0

        current_date = from_date
        business_days = 0

        while current_date < to_date:
            current_date += timedelta(days=1)
            # Monday=0, Friday=4 in Python weekday()
            if current_date.weekday() < 5:  # Monday through Friday
                business_days += 1

        return business_days

    def _get_sla_days(self, impact_level: str | None) -> int:
        """Get the number of SLA business days for an impact level.

        Args:
            impact_level: Financial impact level (LOW/MEDIUM/HIGH/CRITICAL)

        Returns:
            Number of business days for SLA
        """
        SLA_BUSINESS_DAYS = {
            "LOW": 3,
            "MEDIUM": 5,
            "HIGH": 7,
            "CRITICAL": 10,
        }

        return SLA_BUSINESS_DAYS.get(impact_level or "LOW", 5)

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
        from app.services.user import UserService

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

        # Get assigned approver details
        assigned_approver = None
        if co.assigned_approver_id:
            user_service = UserService(self.session)
            approver = await user_service.get_by_id(co.assigned_approver_id)
            if approver:
                assigned_approver = {
                    "user_id": approver.user_id,
                    "full_name": approver.full_name,
                    "email": approver.email,
                    "role": approver.role,
                }

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
            # Approval Matrix & SLA Tracking fields
            "impact_level": co.impact_level,
            "assigned_approver_id": co.assigned_approver_id,
            "sla_assigned_at": co.sla_assigned_at,
            "sla_due_date": co.sla_due_date,
            "sla_status": co.sla_status,
            "assigned_approver": assigned_approver,
        }

        return ChangeOrderPublic(**public_data)

    async def _detect_all_merge_conflicts(
        self, source_branch: str, target_branch: str
    ) -> list[dict[str, Any]]:
        """Detect merge conflicts across all entities in the source branch.

        Checks for conflicts in WBEs, CostElements, and the Change Order itself.
        Only checks active (non-deleted) entities.

        Args:
            source_branch: Source branch name (e.g., "BR-123")
            target_branch: Target branch name (default: "main")

        Returns:
            List of conflict dictionaries. Empty if no conflicts.
        """
        conflicts: list[dict[str, Any]] = []

        # Discover active (non-deleted) entities in source branch
        discovery_service = EntityDiscoveryService(self.session)
        wbes = await discovery_service.discover_wbes(source_branch)
        cost_elements = await discovery_service.discover_cost_elements(source_branch)

        # Check conflicts for WBEs
        wbe_service = WBEService(self.session)
        for wbe in wbes:
            wbe_conflicts = await wbe_service._detect_merge_conflicts(
                root_id=wbe.wbe_id,
                source_branch=source_branch,
                target_branch=target_branch,
            )
            conflicts.extend(wbe_conflicts)

        # Check conflicts for CostElements
        ce_service = CostElementService(self.session)
        for ce in cost_elements:
            ce_conflicts = await ce_service._detect_merge_conflicts(
                root_id=ce.cost_element_id,
                source_branch=source_branch,
                target_branch=target_branch,
            )
            conflicts.extend(ce_conflicts)

        return conflicts
