"""ChangeOrderService for Change Order business logic.

Provides Change Order specific operations including automatic branch
creation on CO creation and workflow-driven branch locking.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

from sqlalchemy import cast as sql_cast
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.notifications import NotificationType
from app.core.temporal_queries import is_current_version_on_branch
from app.core.versioning.commands import (
    CreateChangeOrderAuditLogCommand,
    CreateVersionCommand,
    UpdateChangeOrderStatusCommand,
)
from app.core.versioning.enums import BranchMode
from app.models.domain.branch import Branch
from app.models.domain.change_order import ChangeOrder
from app.models.domain.wbs_element import WBSElement
from app.models.protocols import VersionableProtocol
from app.models.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate
from app.services.branch_service import BranchService
from app.services.change_order_workflow_service import ChangeOrderWorkflowService
from app.services.change_order_workflow_validation import ControlDateValidator
from app.services.custom_field_service import CustomFieldService
from app.services.entity_discovery_service import EntityDiscoveryService
from app.services.wbs_element_service import WBSElementService

if TYPE_CHECKING:
    from app.models.schemas.change_order import ChangeOrderPublic
    from app.models.schemas.impact_analysis import ImpactAnalysisResponse

logger = logging.getLogger(__name__)


# Maps the legacy change-order event strings used at the 6 ``_send_notification``
# call sites to their unified registry codes. All legacy strings map to existing
# codes; add a new entry (and a registry code) if a new event string is introduced.
_CO_EVENT_TYPE_MAP: dict[str, str] = {
    "co_submitted": NotificationType.CO_SUBMITTED.value,
    "co_approved": NotificationType.CO_APPROVED.value,
    "co_rejected": NotificationType.CO_REJECTED.value,
    "co_escalated": NotificationType.CO_ESCALATED.value,
}


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
        from app.services.change_order_config_service import ChangeOrderConfigService

        config_service = ChangeOrderConfigService(session)
        self.workflow = ChangeOrderWorkflowService(config_service=config_service)
        self.branch_service = BranchService(session)

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

        # Validate custom field values against active config definitions
        cfv = co_data.get("custom_field_values")
        if cfv and project_id is not None:
            await self._validate_custom_field_values(project_id, cfv)

        # Prevent duplicate drafts from AI agent loops
        title = co_data.get("title", "")
        if title:
            from app.core.enums import ChangeOrderStatus as COStatus

            existing_stmt = (
                select(ChangeOrder)
                .where(
                    ChangeOrder.project_id == project_id,
                    ChangeOrder.title == title,
                    ChangeOrder.branch == "main",
                    ChangeOrder.status == COStatus.DRAFT.value,
                    is_current_version_on_branch(
                        cast(Any, ChangeOrder).valid_time,
                        ChangeOrder.branch,
                        "main",
                        cast(Any, ChangeOrder).deleted_at,
                    ),
                )
                .limit(1)
            )
            existing_result = await self.session.execute(existing_stmt)
            existing_co = existing_result.scalar_one_or_none()
            if existing_co:
                logger.warning(
                    f"Draft change order with title '{title}' already exists: "
                    f"{existing_co.code}, returning existing"
                )
                return existing_co

        # Generate a UUID for the change_order root
        root_id = uuid4()

        # Generate branch name from code
        branch_name = f"BR-{code}"

        # Set branch_name in the data
        co_data["branch_name"] = branch_name

        # Log branch_name assignment for debugging
        logger.info(
            f"Creating change order {code} with branch_name={branch_name}, "
            f"project_id={project_id}, actor_id={actor_id}"
        )

        # Create the Change Order on main branch using create_root
        change_order = await self.create_root(
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch="main",
            **co_data,
        )

        # Verify branch_name was persisted correctly
        if change_order.branch_name != branch_name:
            logger.error(
                f"CRITICAL: branch_name mismatch after creation! "
                f"Expected: {branch_name}, Got: {change_order.branch_name}, "
                f"CO code: {code}, CO ID: {change_order.change_order_id}"
            )
            raise ValueError(
                f"Failed to persist branch_name for change order {code}. "
                f"Expected: {branch_name}, Got: {change_order.branch_name}"
            )

        logger.info(
            f"Successfully created change order {code} with branch_name={change_order.branch_name}"
        )

        # Create the corresponding branch in the SAME transaction
        from app.core.enums import ChangeOrderStatus as COStatus

        initial_status = co_data.get("status", COStatus.DRAFT.value)

        # Check if the initial status should lock the branch
        # (e.g., if CO is created directly with "Submitted for Approval" status)
        should_lock = initial_status != COStatus.DRAFT.value

        # Create the corresponding branch entity using CreateVersionCommand
        # This ensures proper valid_time setting based on control_date
        branch_root_id = uuid4()

        branch_cmd = CreateVersionCommand(
            entity_class=cast(type[VersionableProtocol], Branch),
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
        branch = cast(Branch, await branch_cmd.execute(self.session))

        # Commit both CO and branch creation in single transaction
        await self.session.commit()
        await self.session.refresh(change_order)
        await self.session.refresh(branch)

        # Final verification: Ensure branch_name is still set after commit and refresh
        if change_order.branch_name != branch_name:
            logger.error(
                f"CRITICAL: branch_name lost after commit/refresh! "
                f"Expected: {branch_name}, Got: {change_order.branch_name}, "
                f"CO code: {code}, CO ID: {change_order.change_order_id}"
            )
            raise ValueError(
                f"branch_name was lost after commit for change order {code}. "
                f"Expected: {branch_name}, Got: {change_order.branch_name}"
            )

        logger.info(
            f"Change order {code} creation complete. "
            f"branch_name={change_order.branch_name}, "
            f"branch_locked={branch.locked}"
        )

        # Note: Impact analysis is NOT run on CO creation anymore.
        # It will be run during submit_for_approval when actual changes exist.
        # This prevents comparing an empty isolation branch against main.

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

        # Determine the source branch - use provided branch or find where the CO exists
        source_branch = branch if branch else "main"

        # Get current version using standard get_as_of() pattern
        current = await self.get_as_of(
            entity_id=change_order_id,
            as_of=control_date,
            branch=source_branch,
            branch_mode=BranchMode.ISOLATED,
        )

        if not current:
            # Try without isolated mode to see if it exists on any branch
            current = await self.get_as_of(
                entity_id=change_order_id,
                as_of=control_date,
                branch=source_branch,
                branch_mode=BranchMode.MERGED,
            )

        if not current:
            raise ValueError(
                f"Change Order {change_order_id} not found or has been deleted"
            )

        # Filter None values from update data
        update_data = change_order_in.model_dump(exclude_unset=True)
        update_data.pop("control_date", None)
        update_data.pop(
            "branch", None
        )  # Remove branch from update data, we use it separately

        # Extract comment for audit log (not stored in ChangeOrder model)
        comment = update_data.pop("comment", None)

        # Validate custom field values against active config definitions
        cfv = update_data.get("custom_field_values")
        if cfv:
            await self._validate_custom_field_values(current.project_id, cfv)

        # Determine target branch
        target_branch = branch if branch is not None else current.branch

        # Check if version exists on target branch using standard get_as_of()
        target_current = await self.get_as_of(
            entity_id=change_order_id,
            as_of=control_date,
            branch=target_branch,
            branch_mode=BranchMode.ISOLATED,
        )

        # Track if we auto-forked to avoid creating duplicate versions
        auto_forked = False

        # If no version on target branch and target is not main, auto-fork from main
        if target_current is None and target_branch != "main":
            # Try to fork from main using standard get_as_of()
            main_version = await self.get_as_of(
                entity_id=change_order_id,
                as_of=control_date,
                branch="main",
                branch_mode=BranchMode.ISOLATED,
            )

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
            # CRITICAL FIX: UpdateCommand returns a cloned object, not a persistent entity
            # We need to fetch the actual persisted entity from the database using the returned id
            new_version = await cmd.execute(self.session)
            # Fetch the actual persisted entity from the database
            updated_co = await self.session.get(ChangeOrder, new_version.id)
            if not updated_co:
                raise ValueError(
                    f"Failed to retrieve updated Change Order {change_order_id}"
                )

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
            # CRITICAL FIX: Fetch updated_co from database after lock/unlock commits
            # The entity may be expired after the commit, so we need to reload it
            updated_co = await self.session.get(ChangeOrder, updated_co.id)

        # Dispatch notifications based on status transitions
        if old_status != new_status and updated_co:
            from app.core.enums import ChangeOrderStatus as COStatus

            # Transition to "Submitted for Approval" - notify assigned approver
            if (
                new_status == COStatus.SUBMITTED_FOR_APPROVAL.value
                and updated_co.assigned_approver_id
            ):
                await self._send_notification(
                    user_id=updated_co.assigned_approver_id,
                    actor_id=actor_id,
                    event_type="co_submitted",
                    title="Change Order Submitted for Approval",
                    message=f"Change order {updated_co.code} requires your approval. Impact level: {updated_co.impact_level}",
                    resource_type="change_order",
                    resource_id=change_order_id,
                )
            # Transition to "Approved" - notify submitter/creator
            elif new_status == COStatus.APPROVED.value:
                await self._send_notification(
                    user_id=updated_co.created_by,
                    actor_id=actor_id,
                    event_type="co_approved",
                    title="Change Order Approved",
                    message=f"Your change order {updated_co.code} has been approved",
                    resource_type="change_order",
                    resource_id=change_order_id,
                )
            # Transition to "Rejected" - notify submitter/creator
            elif new_status == COStatus.REJECTED.value:
                await self._send_notification(
                    user_id=updated_co.created_by,
                    actor_id=actor_id,
                    event_type="co_rejected",
                    title="Change Order Rejected",
                    message=f"Your change order {updated_co.code} has been rejected",
                    resource_type="change_order",
                    resource_id=change_order_id,
                )

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
        co = await self.get_as_of(change_order_id)
        if not co:
            raise ValueError(f"Change Order {change_order_id} not found")

        # Validate status
        from app.core.enums import ChangeOrderStatus as COStatus

        # Validate status
        if co.status not in [
            COStatus.IMPLEMENTED.value,
            COStatus.REJECTED.value,
        ]:  # pragma: no cover
            raise ValueError(
                f"Cannot archive active Change Order. "
                f"Current status: {co.status}. "
                f"Must be '{COStatus.IMPLEMENTED.value}' or '{COStatus.REJECTED.value}'."
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
            entity_id=branch.branch_id, actor_id=actor_id, control_date=control_date
        )

    async def delete_change_order(
        self,
        change_order_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> ChangeOrder:
        """Soft delete a Change Order.

        Only Draft and Rejected COs can be deleted. Active COs in the
        approval workflow must be rejected or implemented first.

        Args:
            change_order_id: The change_order_id (UUID root identifier)
            actor_id: User performing the deletion
            control_date: Optional control date for bitemporal operations

        Returns:
            The deleted ChangeOrder

        Raises:
            ValueError: If Change Order not found or not in a deletable status
        """
        co = await self.get_as_of(change_order_id, branch="main")
        if not co:
            raise ValueError(f"Change Order {change_order_id} not found")

        from app.core.enums import ChangeOrderStatus as COStatus

        if co.status not in (COStatus.DRAFT.value, COStatus.REJECTED.value):
            raise ValueError(
                f"Cannot delete Change Order in '{co.status}' status. "
                f"Only {COStatus.DRAFT.value} or {COStatus.REJECTED.value} COs can be deleted."
            )

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
                is_current_version_on_branch(
                    cast(Any, ChangeOrder).valid_time,
                    ChangeOrder.branch,
                    branch,
                    cast(Any, ChangeOrder).deleted_at,
                ),
                func.not_(func.isempty(ChangeOrder.valid_time)),  # Exclude empty ranges
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

        # Add creator-name outerjoin so created_by_name is populated per row.
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )
        fetch_stmt = stmt.with_only_columns(
            ChangeOrder,
            creator_subq.c.full_name.label("created_by_name"),
        ).outerjoin(
            creator_subq,
            ChangeOrder.created_by == creator_subq.c.user_id,
        )

        # Execute query
        result = await self.session.execute(fetch_stmt)
        change_orders: list[ChangeOrder] = []
        for row in result.all():
            entity = row[0]
            entity.created_by_name = row[1]
            change_orders.append(entity)

        return change_orders, total

    async def get_current_by_code(
        self, code: str, branch: str = "main", as_of: datetime | None = None
    ) -> ChangeOrder | None:
        """Get the active version for a business code as of a specific date.

        Args:
            code: The business code (e.g., "CO-2026-001")
            branch: Branch to query (default: "main")

        Returns:
            Current ChangeOrder or None
        """
        conditions = [
            ChangeOrder.code == code,
            ChangeOrder.branch == branch,
            cast(Any, ChangeOrder).deleted_at.is_(None),
        ]

        if as_of:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            conditions.extend(
                [
                    cast(Any, ChangeOrder).valid_time.op("@>")(as_of_tstz),
                    func.lower(cast(Any, ChangeOrder).valid_time) <= as_of_tstz,
                ]
            )
        else:
            conditions.append(
                is_current_version_on_branch(
                    cast(Any, ChangeOrder).valid_time,
                    ChangeOrder.branch,
                    branch,
                    cast(Any, ChangeOrder).deleted_at,
                )
            )

        stmt = (
            select(ChangeOrder)
            .where(*conditions)
            .order_by(cast(Any, ChangeOrder).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_code(self, project_id: UUID, year: int | None = None) -> str:
        """Get the next available change order code.

        Format: CO-YYYY-NNN (e.g., CO-2026-001)

        Codes are globally unique across all projects to prevent
        409 conflicts on create. The query finds the highest existing
        number for the given year across ALL projects and increments.

        Args:
            project_id: Project UUID (reserved for future use)
            year: Year for the code (defaults to current year)

        Returns:
            Next available code string
        """
        if year is None:
            year = datetime.now(UTC).year

        prefix = f"CO-{year}-"

        # Query max code number across ALL projects for the given year.
        # Codes must be globally unique because get_current_by_code (used
        # by the create endpoint for duplicate detection) does not filter
        # by project_id.
        stmt = select(ChangeOrder.code).where(
            ChangeOrder.code.like(f"{prefix}%"),
            ChangeOrder.branch == "main",
            is_current_version_on_branch(
                cast(Any, ChangeOrder).valid_time,
                ChangeOrder.branch,
                "main",
                cast(Any, ChangeOrder).deleted_at,
            ),
        )

        result = await self.session.execute(stmt)
        existing_codes = [row[0] for row in result.fetchall()]

        # Extract numeric parts from existing codes
        max_number = 0
        for code in existing_codes:
            try:
                num_str = code.replace(prefix, "")
                num = int(num_str)
                if num > max_number:
                    max_number = num
            except (ValueError, AttributeError):
                continue

        # Increment to next number and format with zero-padding
        next_number = max_number + 1
        return f"{prefix}{str(next_number).zfill(3)}"

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
        # 1. Get current version on target branch to find the code
        current = await self.get_as_of(change_order_id, branch=target_branch)

        if not current:
            raise ValueError(
                f"Change Order {change_order_id} not found on target branch '{target_branch}'. "
                f"Change orders must exist on main before they can be merged."
            )

        source_branch = f"BR-{current.code}"

        # Verify source branch has an active version (required for new workflow)
        source_version = await self.get_as_of(change_order_id, branch=source_branch)
        if source_version is None:
            raise ValueError(
                f"No active version found on isolation branch '{source_branch}'. "
                f"The change order must be submitted for approval (which forks to isolation branch) "
                f"before it can be merged. Current status: {current.status}"
            )

        # Detect merge conflicts before proceeding
        conflicts = await self._detect_all_merge_conflicts(source_branch, target_branch)
        if conflicts:
            from app.core.branching.exceptions import MergeConflictError

            raise MergeConflictError(conflicts)

        # 2. Discover all entities in the source branch (including soft-deleted)
        discovery_service = EntityDiscoveryService(self.session)
        all_wbes = await discovery_service.discover_all_wbes(source_branch)
        await discovery_service.discover_all_cost_elements(source_branch)

        # 3. Merge each entity type, handling soft-deletes specially
        # Merge WBEs
        wbe_service = WBSElementService(self.session)
        for wbe in all_wbes:
            if wbe.deleted_at is not None:
                # Soft-deleted on source - soft-delete on target too
                await wbe_service.soft_delete(
                    root_id=wbe.wbs_element_id,
                    actor_id=actor_id,
                    branch=target_branch,
                    control_date=control_date,
                )
            else:
                # Active on source - merge normally
                await wbe_service.merge_branch(
                    root_id=wbe.wbs_element_id,
                    actor_id=actor_id,
                    source_branch=source_branch,
                    target_branch=target_branch,
                    control_date=control_date,
                )

        # CostElements are versionable but NOT branchable (financial facts are global).
        # No merge needed - CostElements exist across all branches.

        # 4. Recalculate and update the Project's budget
        # Refresh current CO entity — attributes expired after merge operations above
        await self.session.refresh(current)
        # Sum all active work packages on the target branch for this project
        from app.models.domain.control_account import ControlAccount
        from app.models.domain.wbs_element import WBSElement
        from app.models.domain.work_package import WorkPackage

        budget_stmt = (
            select(func.sum(WorkPackage.budget_amount))
            .select_from(WorkPackage)
            .join(
                ControlAccount,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                WBSElement, ControlAccount.wbs_element_id == WBSElement.wbs_element_id
            )
            .where(
                WBSElement.project_id == current.project_id,
                is_current_version_on_branch(
                    cast(Any, WBSElement).valid_time,
                    WBSElement.branch,
                    target_branch,
                    cast(Any, WBSElement).deleted_at,
                ),
                is_current_version_on_branch(
                    cast(Any, ControlAccount).valid_time,
                    ControlAccount.branch,
                    target_branch,
                    cast(Any, ControlAccount).deleted_at,
                ),
                is_current_version_on_branch(
                    cast(Any, WorkPackage).valid_time,
                    WorkPackage.branch,
                    target_branch,
                    cast(Any, WorkPackage).deleted_at,
                ),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
        )
        budget_result = await self.session.execute(budget_stmt)
        new_budget = budget_result.scalar_one()

        # Update the project with the new budget
        from app.services.project import ProjectService

        project_service = ProjectService(self.session)
        from app.models.schemas.project import ProjectUpdate

        project_update = ProjectUpdate(
            budget=new_budget, branch=target_branch, control_date=control_date
        )
        await project_service.update_project(
            project_id=current.project_id,
            project_in=project_update,
            actor_id=actor_id,
        )

        # 5. Merge the Change Order entity from isolation branch to target branch
        # COs may or may not be forked to the isolation branch depending on workflow.
        # If the CO exists on the isolation branch, merge it; otherwise skip.
        isolation_branch_name = current.branch_name
        project_id = current.project_id

        co_on_isolation = await self.get_as_of(
            change_order_id, branch=source_branch, branch_mode=BranchMode.ISOLATED
        )
        if co_on_isolation:
            await self.merge_branch(
                root_id=change_order_id,
                actor_id=actor_id,
                source_branch=source_branch,
                target_branch=target_branch,
                control_date=control_date,
            )

        # Unlock the isolation branch after successful merge
        if isolation_branch_name:
            await self.branch_service.unlock(
                name=isolation_branch_name,
                project_id=project_id,
                actor_id=actor_id,
            )
            logger.info(
                f"Unlocked isolation branch {isolation_branch_name} after merge"
            )

        # 6. Update CO status to "Implemented" using Command (RSC compliance)
        from app.core.enums import ChangeOrderStatus as COStatus

        # Refresh current CO — attributes expired after merge/unlock operations
        await self.session.refresh(current)
        old_status = current.status
        status_cmd = UpdateChangeOrderStatusCommand(
            change_order_id=change_order_id,
            new_status=COStatus.IMPLEMENTED.value,
            actor_id=actor_id,
            branch=target_branch,
            control_date=control_date,
            additional_updates={
                "assigned_approver_id": None,
                "sla_assigned_at": None,
                "sla_due_date": None,
                "sla_status": None,
            },
        )
        updated_co = await status_cmd.execute(self.session)
        await self.session.refresh(updated_co)

        # Record audit log for Approved → Implemented transition (RSC compliance)
        audit_cmd = CreateChangeOrderAuditLogCommand(
            change_order_id=change_order_id,
            old_status=old_status,
            new_status=COStatus.IMPLEMENTED.value,
            actor_id=actor_id,
            comment="Change order implemented via merge",
            control_date=control_date,
        )
        await audit_cmd.execute(self.session)

        return updated_co

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
        control_date: datetime | None = None,
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
            control_date: Optional control date for the operation (defaults to now)

        Returns:
            Updated ChangeOrder with impact level and approver assigned

        Raises:
            ValueError: If change order not found or invalid status transition
            ControlDateSequenceViolationError: If control_date violates sequence
        """
        # Default control_date to now if not provided
        if control_date is None:
            control_date = datetime.now(UTC)

        # Validate control date sequence
        await ControlDateValidator.validate_control_date_sequence(
            change_order_id=change_order_id,
            new_control_date=control_date,
            session=self.session,
        )

        # Get current change order
        co = await self.get_as_of(change_order_id, branch=branch)
        if not co:
            raise ValueError(f"Change Order {change_order_id} not found")

        # Validate status transition
        from app.core.enums import ChangeOrderStatus as COStatus

        if not await self.workflow.is_valid_transition(
            co.status, COStatus.SUBMITTED_FOR_APPROVAL.value
        ):
            available = await self.workflow.get_available_transitions(co.status)
            raise ValueError(
                f"Cannot submit change order {co.code} (status: {co.status}) for approval by user {actor_id}. "
                f"Current status must be '{COStatus.DRAFT.value}' or '{COStatus.REJECTED.value}'. "
                f"Available transitions: {available}. "
                f"Project: {co.project_id}. "
                f"Action: submit_for_approval"
            )

        # Run impact analysis NOW (at submission time, not creation time)
        # This ensures we're comparing the actual changes made by the user
        if not co.branch_name:
            raise ValueError(
                f"Change order {co.code} has no isolation branch configured. "
                f"Cannot submit for approval. "
                f"Project: {co.project_id}. "
                f"User: {actor_id}. "
                f"Action: submit_for_approval"
            )

        logger.info(
            f"Running impact analysis for change order {co.code} at submission time"
        )
        try:
            await self._run_impact_analysis(co, co.branch_name)
            await self.session.commit()
            await self.session.refresh(co)
        except Exception as e:
            # Impact analysis failure should not prevent submission
            logger.warning(
                f"Impact analysis failed for change order {co.code}: {e}. "
                f"Proceeding with submission using default values."
            )
            # Set default impact level if analysis failed
            co.impact_level = "MEDIUM"
            await self.session.flush()

        # Verify impact analysis completed
        if co.impact_analysis_status != "completed":
            raise ValueError(
                f"Cannot submit change order {co.code} for approval by user {actor_id}: "
                f"impact analysis failed to complete. "
                f"Current status: {co.impact_analysis_status}. "
                f"Project: {co.project_id}. "
                f"Action: submit_for_approval"
            )

        if co.impact_level is None:
            raise ValueError(
                f"Cannot submit change order {co.code} for approval by user {actor_id}: "
                f"impact level calculation failed. "
                f"Project: {co.project_id}. "
                f"Action: submit_for_approval"
            )

        if co.assigned_approver_id is None:
            raise ValueError(
                f"Cannot submit change order {co.code} for approval by user {actor_id}: "
                f"no approver has been assigned for {co.impact_level} impact level. "
                f"Please contact your administrator to configure the approval matrix. "
                f"Project: {co.project_id}. "
                f"Action: submit_for_approval"
            )

        # Use the impact level calculated during submission
        impact_level = co.impact_level

        # Calculate SLA deadline from configurable workflow config
        sla_days = await self._get_sla_days(impact_level)
        sla_due_date = self._add_business_days(datetime.now(UTC), sla_days)

        # Snapshot workflow config at submission time (Decision 7 & 13)
        from app.services.change_order_config_service import (
            ChangeOrderConfigService,
        )

        config_service = ChangeOrderConfigService(self.session)
        config_snapshot = await config_service.generate_snapshot(
            project_id=co.project_id
        )

        # Store old status for audit log
        old_status = co.status

        # Update change order with SLA tracking using versioned command
        sla_assigned_at = datetime.now(UTC)
        status_cmd = UpdateChangeOrderStatusCommand(
            change_order_id=change_order_id,
            new_status=COStatus.SUBMITTED_FOR_APPROVAL.value,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            additional_updates={
                "sla_assigned_at": sla_assigned_at,
                "sla_due_date": sla_due_date,
                "sla_status": "pending",
                "config_snapshot": config_snapshot,
            },
        )
        updated_co = await status_cmd.execute(self.session)

        # Record audit log using Command (RSC compliance)
        audit_cmd = CreateChangeOrderAuditLogCommand(
            change_order_id=change_order_id,
            old_status=old_status,
            new_status=COStatus.SUBMITTED_FOR_APPROVAL.value,
            actor_id=actor_id,
            comment=comment or f"Submitted for approval with {impact_level} impact",
            control_date=control_date,
        )
        await audit_cmd.execute(self.session)

        # Fork all project data to the isolation branch for proper branch isolation workflow
        # This ensures that changes made during approval workflow are isolated from main
        # The isolation branch should already exist (created during CO creation)
        if updated_co.branch_name:
            # Fork from main to isolation branch (lazy branching pattern)
            # This creates a copy of the CO on the isolation branch
            from app.core.branching.commands import CreateBranchCommand

            isolation_branch = updated_co.branch_name

            # Check if version already exists on isolation branch
            existing_isolation_version = await self.get_as_of(
                change_order_id, branch=isolation_branch
            )

            if existing_isolation_version is None:
                # Fork the CO to the isolation branch
                fork_cmd = CreateBranchCommand(  # type: ignore[type-var]
                    entity_class=ChangeOrder,
                    root_id=change_order_id,
                    actor_id=actor_id,
                    new_branch=isolation_branch,
                    from_branch="main",
                    control_date=control_date,
                )
                await fork_cmd.execute(self.session)
                logger.info(
                    f"Forked change order {updated_co.code} to isolation branch {isolation_branch}"
                )

            # Fork all WBEs and CostElements to the isolation branch
            # This ensures the isolation branch has complete project data for making changes
            await self._fork_project_entities_to_isolation_branch(
                project_id=updated_co.project_id,
                isolation_branch=isolation_branch,
                actor_id=actor_id,
                control_date=control_date,
            )
            logger.info(
                f"Forked all project entities to isolation branch {isolation_branch}"
            )

            # Lock the isolation branch to prevent concurrent modifications
            await self.branch_service.lock(
                name=isolation_branch,
                project_id=updated_co.project_id,
                actor_id=actor_id,
            )
            logger.info(f"Locked isolation branch {isolation_branch}")

        # Send notification to assigned approver
        if updated_co.assigned_approver_id:
            await self._send_notification(
                user_id=updated_co.assigned_approver_id,
                actor_id=actor_id,
                event_type="co_submitted",
                title="Change Order Submitted for Approval",
                message=f"Change order {updated_co.code} requires your approval. Impact level: {impact_level}",
                resource_type="change_order",
                resource_id=change_order_id,
            )

        await self.session.commit()
        await self.session.refresh(updated_co)

        return updated_co

    async def approve_change_order(
        self,
        change_order_id: UUID,
        approver_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        comments: str | None = None,
        control_date: datetime | None = None,
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
            control_date: Optional control date for the operation (defaults to now)

        Returns:
            Updated ChangeOrder with Approved status

        Raises:
            ValueError: If change order not found, invalid status, or insufficient authority
            ControlDateSequenceViolationError: If control_date violates sequence
        """
        from app.core.rbac_unified import (
            get_unified_rbac_service,
            set_unified_rbac_session,
        )
        from app.services.user import UserService

        # Default control_date to now if not provided
        if control_date is None:
            control_date = datetime.now(UTC)

        # Validate control date sequence
        await ControlDateValidator.validate_control_date_sequence(
            change_order_id=change_order_id,
            new_control_date=control_date,
            session=self.session,
        )

        # Get current change order
        co = await self.get_as_of(change_order_id, branch=branch)
        if not co:
            raise ValueError(f"Change Order {change_order_id} not found")

        # Validate status transition
        from app.core.enums import ChangeOrderStatus as COStatus

        if not await self.workflow.is_valid_transition(
            co.status, COStatus.APPROVED.value
        ):
            available = await self.workflow.get_available_transitions(co.status)
            raise ValueError(
                f"Cannot approve CO with status '{co.status}'. "
                f"Available transitions: {available}"
            )

        # Get approver user object
        user_service = UserService(self.session)
        approver = await user_service.get_user(approver_id)
        if not approver:
            raise ValueError(f"Approver with ID {approver_id} not found")

        # Validate approver authority via unified RBAC
        set_unified_rbac_session(self.session)
        try:
            unified_rbac = get_unified_rbac_service()
            can_approve = await unified_rbac.has_permission(
                user_id=approver_id,
                required_permission="change-order-approve",
                scope_type="project",
                scope_id=co.project_id,
            )
        finally:
            set_unified_rbac_session(None)

        if not can_approve:
            # Get required authority for better error context
            from app.services.change_order_config_service import (
                ChangeOrderConfigService,
            )

            config_service = ChangeOrderConfigService(self.session)
            impact_authority = await config_service.get_impact_authority_mapping()
            required_authority = impact_authority.get(
                co.impact_level or "LOW", "UNKNOWN"
            )

            set_unified_rbac_session(self.session)
            try:
                user_authority = await unified_rbac.get_user_authority_level(
                    approver_id
                )
                approver_roles = await unified_rbac.get_user_roles(
                    approver_id, "global", None
                )
                approver_role_str = approver_roles[0] if approver_roles else "unknown"
            finally:
                set_unified_rbac_session(None)

            raise ValueError(
                f"User {approver_id} (role: {approver_role_str}, authority: {user_authority}) does not have sufficient authority "
                f"to approve change order {co.code} with impact level {co.impact_level}. "
                f"Required authority: {required_authority}. "
                f"Project: {co.project_id}. "
                f"Action: approve_change_order"
            )

        # Verify the assigned approver is the one approving
        if co.assigned_approver_id != approver_id:
            raise ValueError(
                f"This change order is assigned to approver {co.assigned_approver_id}. "
                f"User {approver_id} is not authorized to approve it."
            )

        # Store old status for audit log
        old_status = co.status

        # Update status to Approved using versioned command
        status_cmd = UpdateChangeOrderStatusCommand(
            change_order_id=change_order_id,
            new_status=COStatus.APPROVED.value,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
        )
        updated_co = await status_cmd.execute(self.session)

        # Record audit log using Command (RSC compliance)
        audit_cmd = CreateChangeOrderAuditLogCommand(
            change_order_id=change_order_id,
            old_status=old_status,
            new_status=COStatus.APPROVED.value,
            actor_id=actor_id,
            comment=comments or "Change order approved",
            control_date=control_date,
        )
        await audit_cmd.execute(self.session)

        # Send notification to the submitter/creator
        from app.services.user import UserService

        user_service = UserService(self.session)
        approver = await user_service.get_user(actor_id)
        approver_name = approver.full_name if approver else "Unknown"

        await self._send_notification(
            user_id=updated_co.created_by,
            actor_id=actor_id,
            event_type="co_approved",
            title="Change Order Approved",
            message=f"Your change order {updated_co.code} has been approved by {approver_name}",
            resource_type="change_order",
            resource_id=change_order_id,
        )

        await self.session.commit()
        await self.session.refresh(updated_co)

        return updated_co

    async def reject_change_order(
        self,
        change_order_id: UUID,
        rejecter_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        comments: str | None = None,
        control_date: datetime | None = None,
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
            control_date: Optional control date for the operation (defaults to now)

        Returns:
            Updated ChangeOrder with Rejected status and unlocked branch

        Raises:
            ValueError: If change order not found, invalid status, or insufficient authority
            ControlDateSequenceViolationError: If control_date violates sequence
        """
        from app.core.rbac_unified import (
            get_unified_rbac_service,
            set_unified_rbac_session,
        )
        from app.services.user import UserService

        # Default control_date to now if not provided
        if control_date is None:
            control_date = datetime.now(UTC)

        # Validate control date sequence
        await ControlDateValidator.validate_control_date_sequence(
            change_order_id=change_order_id,
            new_control_date=control_date,
            session=self.session,
        )

        # Get current change order
        co = await self.get_as_of(change_order_id, branch=branch)
        if not co:
            raise ValueError(f"Change Order {change_order_id} not found")

        # Validate status transition
        from app.core.enums import ChangeOrderStatus as COStatus

        if not await self.workflow.is_valid_transition(
            co.status, COStatus.REJECTED.value
        ):
            available = await self.workflow.get_available_transitions(co.status)
            raise ValueError(
                f"Cannot reject CO with status '{co.status}'. "
                f"Available transitions: {available}"
            )

        # Get rejecter user object
        user_service = UserService(self.session)
        rejecter = await user_service.get_user(rejecter_id)
        if not rejecter:
            raise ValueError(f"Rejecter with ID {rejecter_id} not found")

        # Validate rejecter authority via unified RBAC
        set_unified_rbac_session(self.session)
        try:
            unified_rbac = get_unified_rbac_service()
            can_reject = await unified_rbac.has_permission(
                user_id=rejecter_id,
                required_permission="change-order-approve",
                scope_type="project",
                scope_id=co.project_id,
            )
        finally:
            set_unified_rbac_session(None)

        if not can_reject:
            # Get required authority for better error context
            from app.services.change_order_config_service import (
                ChangeOrderConfigService,
            )

            config_service = ChangeOrderConfigService(self.session)
            impact_authority = await config_service.get_impact_authority_mapping()
            required_authority = impact_authority.get(
                co.impact_level or "LOW", "UNKNOWN"
            )

            set_unified_rbac_session(self.session)
            try:
                user_authority = await unified_rbac.get_user_authority_level(
                    rejecter_id
                )
                rejecter_roles = await unified_rbac.get_user_roles(
                    rejecter_id, "global", None
                )
                rejecter_role_str = rejecter_roles[0] if rejecter_roles else "unknown"
            finally:
                set_unified_rbac_session(None)

            raise ValueError(
                f"User {rejecter_id} (role: {rejecter_role_str}, authority: {user_authority}) does not have sufficient authority "
                f"to reject change order {co.code} with impact level {co.impact_level}. "
                f"Required authority: {required_authority}. "
                f"Project: {co.project_id}. "
                f"Action: reject_change_order"
            )

        # Store old status for audit log
        old_status = co.status

        # Update status to Rejected using versioned command
        status_cmd = UpdateChangeOrderStatusCommand(
            change_order_id=change_order_id,
            new_status=COStatus.REJECTED.value,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
        )
        updated_co = await status_cmd.execute(self.session)

        # Clear SLA fields on rejection
        await self.update(
            root_id=change_order_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            assigned_approver_id=None,
            sla_assigned_at=None,
            sla_due_date=None,
            sla_status=None,
        )

        # Record audit log using Command (RSC compliance)
        audit_cmd = CreateChangeOrderAuditLogCommand(
            change_order_id=change_order_id,
            old_status=old_status,
            new_status=COStatus.REJECTED.value,
            actor_id=actor_id,
            comment=comments or "Change order rejected",
            control_date=control_date,
        )
        await audit_cmd.execute(self.session)

        # Send notification to the submitter/creator
        from app.services.user import UserService

        user_service = UserService(self.session)
        rejecter = await user_service.get_user(actor_id)
        rejecter_name = rejecter.full_name if rejecter else "Unknown"

        await self._send_notification(
            user_id=updated_co.created_by,
            actor_id=actor_id,
            event_type="co_rejected",
            title="Change Order Rejected",
            message=f"Your change order {updated_co.code} has been rejected by {rejecter_name}",
            resource_type="change_order",
            resource_id=change_order_id,
        )

        # Unlock the branch
        if updated_co.branch_name:
            await self.branch_service.unlock(
                name=updated_co.branch_name,
                project_id=updated_co.project_id,
                actor_id=actor_id,
            )

        await self.session.commit()
        await self.session.refresh(updated_co)

        return updated_co

    async def recover_change_order(
        self,
        change_order_id: UUID,
        impact_level: str,
        assigned_approver_id: UUID,
        skip_impact_analysis: bool,
        recovery_reason: str,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> ChangeOrder:
        """Recover a stuck change order workflow (admin only).

        Context: Admin operation to recover stuck workflows when impact analysis
        fails or the change order gets stuck in an intermediate state. This allows
        manual override of impact level and approver assignment.

        Args:
            change_order_id: UUID of the stuck change order
            impact_level: Manual impact level (LOW/MEDIUM/HIGH/CRITICAL)
            assigned_approver_id: User to assign as approver (use User.user_id, the EVCS root ID)
            skip_impact_analysis: Skip impact analysis and use manual values
            recovery_reason: Explanation for recovery (audit trail)
            actor_id: Admin user performing recovery (use User.user_id, the EVCS root ID)
            branch: Branch name (default: main)
            control_date: Optional control date for the operation (defaults to now)

        Returns:
            Updated ChangeOrder with recovered workflow state

        Raises:
            ValueError: If change order not found, invalid state, or invalid data
            ControlDateSequenceViolationError: If control_date violates sequence
        """
        from app.services.user import UserService

        # Default control_date to now if not provided
        if control_date is None:
            control_date = datetime.now(UTC)

        # Validate control date sequence
        await ControlDateValidator.validate_control_date_sequence(
            change_order_id=change_order_id,
            new_control_date=control_date,
            session=self.session,
        )

        # Get current change order
        co = await self.get_as_of(change_order_id, branch=branch)
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
                f"Change order {co.code} is not stuck and does not require recovery. "
                f"Current status: {co.status}, "
                f"Impact level: {co.impact_level}, "
                f"Approver: {co.assigned_approver_id}, "
                f"Analysis: {co.impact_analysis_status}, "
                f"Available transitions: {transitions}. "
                f"Project: {co.project_id}. "
                f"User: {actor_id}. "
                f"Action: recover_change_order"
            )

        # Get approver user object
        # NOTE: assigned_approver_id is user.user_id (EVCS root ID), not user.id (PK)
        # Use get_user(user_id) for standard EVCS lookups, not get_by_id(id)
        user_service = UserService(self.session)
        approver = await user_service.get_user(assigned_approver_id)
        if not approver:
            raise ValueError(
                f"Approver with ID {assigned_approver_id} not found. "
                f"Cannot recover change order {co.code}. "
                f"Project: {co.project_id}. "
                f"User: {actor_id}. "
                f"Action: recover_change_order"
            )

        # Validate impact level
        valid_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if impact_level not in valid_levels:
            raise ValueError(
                f"Invalid impact level: {impact_level}. Must be one of {valid_levels}. "
                f"Cannot recover change order {co.code}. "
                f"Project: {co.project_id}. "
                f"User: {actor_id}. "
                f"Action: recover_change_order"
            )

        # Store old values for audit
        old_status = co.status
        old_impact_level = co.impact_level
        old_approver = co.assigned_approver_id
        old_analysis_status = co.impact_analysis_status

        # Determine new status for recovery
        from app.core.enums import ChangeOrderStatus as COStatus

        new_status = co.status
        if co.status == COStatus.DRAFT.value:
            new_status = COStatus.UNDER_REVIEW.value
        elif co.status in (
            COStatus.SUBMITTED_FOR_APPROVAL.value,
            COStatus.UNDER_REVIEW.value,
        ):
            new_status = COStatus.UNDER_REVIEW.value

        # Update change order with recovery values using versioned command
        new_analysis_status = "skipped" if skip_impact_analysis else "completed"
        status_cmd = UpdateChangeOrderStatusCommand(
            change_order_id=change_order_id,
            new_status=new_status,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            additional_updates={
                "impact_level": impact_level,
                "assigned_approver_id": assigned_approver_id,
                "impact_analysis_status": new_analysis_status,
            },
        )
        updated_co = await status_cmd.execute(self.session)

        # Record audit log with detailed recovery information
        audit_comment = (
            f"Workflow recovery by admin. "
            f"Reason: {recovery_reason}. "
            f"Changes: "
            f"status '{old_status}' → '{new_status}', "
            f"impact_level '{old_impact_level}' → '{impact_level}', "
            f"approver '{old_approver}' → '{assigned_approver_id}', "
            f"analysis '{old_analysis_status}' → '{new_analysis_status}'"
        )

        audit_cmd = CreateChangeOrderAuditLogCommand(
            change_order_id=change_order_id,
            old_status=old_status,
            new_status=new_status,
            actor_id=actor_id,
            comment=audit_comment,
            control_date=control_date,
        )
        await audit_cmd.execute(self.session)

        await self.session.commit()
        await self.session.refresh(updated_co)

        logger.info(
            f"Change order {change_order_id} recovered by user {actor_id}. "
            f"Status: {old_status} → {new_status}, "
            f"Impact: {impact_level}, Approver: {assigned_approver_id}"
        )

        return updated_co

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
        from app.core.enums import ChangeOrderStatus as COStatus

        stmt = select(ChangeOrder).where(
            ChangeOrder.assigned_approver_id == user_id,
            ChangeOrder.status.in_(
                [COStatus.SUBMITTED_FOR_APPROVAL.value, COStatus.UNDER_REVIEW.value]
            ),
            ChangeOrder.branch == branch,
            is_current_version_on_branch(
                cast(Any, ChangeOrder).valid_time,
                ChangeOrder.branch,
                branch,
                cast(Any, ChangeOrder).deleted_at,
            ),  # Current versions
            cast(Any, ChangeOrder).deleted_at.is_(None),
        )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)
        stmt = stmt.order_by(ChangeOrder.sla_due_date.asc())

        # Add creator-name outerjoin so created_by_name is populated per row.
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )
        fetch_stmt = stmt.with_only_columns(
            ChangeOrder,
            creator_subq.c.full_name.label("created_by_name"),
        ).outerjoin(
            creator_subq,
            ChangeOrder.created_by == creator_subq.c.user_id,
        )

        result = await self.session.execute(fetch_stmt)
        change_orders: list[ChangeOrder] = []
        for row in result.all():
            entity = row[0]
            entity.created_by_name = row[1]
            change_orders.append(entity)

        return change_orders, total

    async def _send_notification(
        self,
        user_id: UUID,
        actor_id: UUID,
        event_type: str,
        title: str,
        message: str,
        resource_type: str = "change_order",
        resource_id: UUID | None = None,
    ) -> None:
        """Send a change-order notification to a user via the dispatcher.

        Routes the legacy ``co_submitted``/``co_approved``/``co_rejected``
        event strings through the unified :class:`EventEmitter` so the
        notification persists with the new ``actor_type``/``severity`` columns
        and delivers real-time to the bell (+ Telegram when enabled). Never
        raises: failures are logged (belt-and-suspenders; the emitter already
        swallows).

        Args:
            user_id: UUID of the user to notify.
            actor_id: UUID of the user triggering the change order action.
            event_type: Legacy event string (``co_submitted`` | ``co_approved``
                | ``co_rejected`` | ``co_escalated``).
            title: Short headline for notification lists.
            message: Full notification body text.
            resource_type: Type of related entity (default: 'change_order').
            resource_id: UUID of the related entity.
        """
        from app.core.notifications import user_emitter

        code = _CO_EVENT_TYPE_MAP.get(event_type)
        if code is None:
            logger.warning(
                "Unknown change-order notification event_type %r; skipping", event_type
            )
            return
        try:
            await user_emitter(actor_id, self.session).emit(
                code,
                title=title,
                message=message,
                target_user_ids=[user_id],
                resource_type=resource_type,
                resource_id=resource_id,
                idempotency_key=f"co:{resource_id}:{code}" if resource_id else None,
            )
        except Exception:
            logger.exception("Failed to send change-order notification")

    async def _validate_custom_field_values(
        self, project_id: UUID, values: dict[str, Any]
    ) -> None:
        """Validate custom field values against the active config's field definitions.

        Loads the workflow config's custom_fields, parses them into
        CustomFieldDefinition objects, and runs validation. Raises ValueError
        if any validation errors are found.

        Args:
            project_id: Project UUID to resolve the active config
            values: Custom field values dict to validate

        Raises:
            ValueError: If validation errors exist
        """
        from app.models.schemas.custom_field import CustomFieldDefinition
        from app.services.change_order_config_service import (
            ChangeOrderConfigService,
        )

        config_service = ChangeOrderConfigService(self.session)
        config = await config_service.get_active_config(project_id)

        raw_fields = config.custom_fields or []
        definitions = [CustomFieldDefinition(**f) for f in raw_fields]

        validator = CustomFieldService()
        errors = validator.validate_field_values(definitions, values)
        if errors:
            raise ValueError(f"Custom field validation failed: {'; '.join(errors)}")

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
            impact_level = await self._map_score_to_impact_level(impact_score)

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
                    impact_analysis_results=impact_analysis.model_dump(mode="json"),
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
            # Expected errors (e.g., project not found, empty branch, no data yet)
            # Set reasonable defaults for empty branch scenario
            # Empty branch means no changes = LOW impact, zero financial impact
            default_impact_level = "LOW"
            default_impact_score = Decimal("0")

            # Try to assign approver for default impact level
            default_approver_id = await self._assign_approver_for_impact(
                change_order.project_id, default_impact_level
            )

            update_stmt = (
                update(ChangeOrder)
                .where(ChangeOrder.id == change_order.id)
                .values(
                    impact_analysis_results={
                        "error": str(e),
                        "reason": "No project data available for analysis - using defaults",
                        "note": "Empty branch or no data detected - treating as LOW impact",
                    },
                    impact_analysis_status="completed",
                    impact_level=default_impact_level,
                    impact_score=default_impact_score,
                    assigned_approver_id=default_approver_id,
                )
            )
            await self.session.execute(update_stmt)
            await self.session.commit()
            await self.session.refresh(change_order)

            logger.warning(
                f"Impact analysis for change order {change_order.code} encountered no data "
                f"(empty branch or no project data). Using defaults: "
                f"impact_level={default_impact_level}, impact_score={default_impact_score}. "
                f"Reason: {e}"
            )

        except Exception as e:
            # Unexpected errors - use conservative defaults to allow workflow to continue
            # MEDIUM impact is a reasonable conservative default for unexpected errors
            default_impact_level = "MEDIUM"
            default_impact_score = Decimal("50")  # Moderate impact score

            # Try to assign approver for default impact level
            default_approver_id = await self._assign_approver_for_impact(
                change_order.project_id, default_impact_level
            )

            update_stmt = (
                update(ChangeOrder)
                .where(ChangeOrder.id == change_order.id)
                .values(
                    impact_analysis_results={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "note": "Impact analysis service failed - using conservative defaults",
                    },
                    impact_analysis_status="completed",
                    impact_level=default_impact_level,
                    impact_score=default_impact_score,
                    assigned_approver_id=default_approver_id,
                )
            )
            await self.session.execute(update_stmt)
            await self.session.commit()
            await self.session.refresh(change_order)

            logger.error(
                f"Impact analysis failed for change order {change_order.code}: {e}. "
                f"Using conservative defaults: impact_level={default_impact_level}, "
                f"impact_score={default_impact_score}. Approver: {default_approver_id}",
                exc_info=True,
            )

    async def _assign_approver_for_impact(
        self, project_id: UUID, impact_level: str
    ) -> UUID | None:
        """Assign an approver based on impact level using UnifiedRBACService.

        Context: Phase 6 Task #3 - Approver assignment on CO creation.
        Queries the UnifiedRBACService to find an eligible approver for the
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
        from app.core.rbac_unified import (
            get_unified_rbac_service,
            set_unified_rbac_session,
        )

        try:
            set_unified_rbac_session(self.session)
            try:
                unified_rbac = get_unified_rbac_service()
                approver_id = await unified_rbac.get_approver_for_impact(
                    project_id, impact_level
                )
            finally:
                set_unified_rbac_session(None)

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

    def _calculate_impact_score(
        self, impact_analysis: "ImpactAnalysisResponse"
    ) -> Decimal:
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

    async def _map_score_to_impact_level(self, score: Decimal) -> str:
        """Map impact score to impact level using configurable boundaries.

        Context: Phase 6 Task #2 - Impact level classification.
        Maps numeric score to LOW/MEDIUM/HIGH/CRITICAL levels.

        Args:
            score: Impact severity score (Decimal)

        Returns:
            Impact level string: LOW, MEDIUM, HIGH, or CRITICAL
        """
        from app.services.change_order_config_service import (
            ChangeOrderConfigService,
        )

        config_service = ChangeOrderConfigService(self.session)
        boundaries = await config_service.get_score_boundaries()
        return config_service.classify_impact_by_score(score, boundaries)

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

        if from_date.tzinfo is None:
            from_date = from_date.replace(tzinfo=UTC)
        if to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=UTC)

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

    async def _fork_project_entities_to_isolation_branch(
        self,
        project_id: UUID,
        isolation_branch: str,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        """Fork all project entities (WBEs, CostElements) to the isolation branch.

        This ensures the isolation branch has complete project data for making changes
        during the approval workflow. Uses lazy forking to avoid unnecessary copies.

        Args:
            project_id: Project ID to fork entities for
            isolation_branch: Target isolation branch name
            actor_id: User performing the fork
            control_date: Optional control date for temporal operations
        """
        # Discover all WBSElements on main branch for this project
        from typing import Any, cast

        from sqlalchemy import select as sql_select

        from app.core.branching.commands import CreateBranchCommand

        wbe_stmt = sql_select(WBSElement).where(
            WBSElement.project_id == project_id,
            WBSElement.branch == "main",
            is_current_version_on_branch(
                cast(Any, WBSElement).valid_time,
                WBSElement.branch,
                "main",
                cast(Any, WBSElement).deleted_at,
            ),
        )
        wbe_result = await self.session.execute(wbe_stmt)
        wbes = wbe_result.scalars().all()

        # Fork each WBSElement to isolation branch
        for wbe in wbes:
            # Check if already exists on isolation branch
            existing_stmt = sql_select(WBSElement).where(
                WBSElement.wbs_element_id == wbe.wbs_element_id,
                WBSElement.branch == isolation_branch,
                is_current_version_on_branch(
                    cast(Any, WBSElement).valid_time,
                    WBSElement.branch,
                    isolation_branch,
                    cast(Any, WBSElement).deleted_at,
                ),
                cast(Any, WBSElement).deleted_at.is_(None),
            )
            existing_result = await self.session.execute(existing_stmt)
            if existing_result.scalar_one_or_none() is None:
                # Fork this WBSElement
                wbe_fork_cmd = CreateBranchCommand(
                    entity_class=cast(Any, WBSElement),
                    root_id=wbe.wbs_element_id,
                    actor_id=actor_id,
                    new_branch=isolation_branch,
                    from_branch="main",
                    control_date=control_date,
                )
                await wbe_fork_cmd.execute(self.session)

        # CostElements are versionable but NOT branchable (financial facts are global).
        # No forking needed.

    async def _get_sla_days(self, impact_level: str | None) -> int:
        """Get the number of SLA business days for an impact level.

        Reads from the configurable workflow configuration.

        Args:
            impact_level: Financial impact level (LOW/MEDIUM/HIGH/CRITICAL)

        Returns:
            Number of business days for SLA
        """
        from app.services.change_order_config_service import (
            ChangeOrderConfigService,
        )

        config_service = ChangeOrderConfigService(self.session)
        sla_days_map = await config_service.get_sla_days()
        return sla_days_map.get(impact_level or "LOW", 5)

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
            approver = await user_service.get_user(co.assigned_approver_id)
            if approver:
                from app.core.rbac_unified import (
                    get_unified_rbac_service,
                    set_unified_rbac_session,
                )

                set_unified_rbac_session(self.session)
                try:
                    approver_rbac = get_unified_rbac_service()
                    approver_roles = await approver_rbac.get_user_roles(
                        approver.user_id, "global", None
                    )
                    approver_role = approver_roles[0] if approver_roles else "unknown"
                finally:
                    set_unified_rbac_session(None)

                assigned_approver = {
                    "user_id": approver.user_id,
                    "full_name": approver.full_name,
                    "email": approver.email,
                    "role": approver_role,
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
            "config_snapshot": co.config_snapshot,
            "custom_field_values": co.custom_field_values,
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

        # Check conflicts for WBEs
        wbe_service = WBSElementService(self.session)
        for wbe in wbes:
            wbe_conflicts = await wbe_service._detect_merge_conflicts(
                root_id=wbe.wbs_element_id,
                source_branch=source_branch,
                target_branch=target_branch,
            )
            conflicts.extend(wbe_conflicts)

        # CostElements are versionable but NOT branchable - no merge conflicts possible.

        return conflicts
