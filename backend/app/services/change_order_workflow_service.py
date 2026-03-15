"""Change Order Workflow Service - flexible state machine.

This service encapsulates Change Order workflow state transitions and business rules.
It is designed as a simple state machine that can be replaced with a full business
process workflow engine (e.g., Camunda, Temporal) in a future iteration.

Workflow States (from FR-8.3):
Draft → Submitted for Approval → Under Review → Approved/Rejected → Implemented

Context: This service orchestrates the approval workflow by integrating with
FinancialImpactService, ApprovalMatrixService, and SLAService to manage the
complete approval lifecycle from submission to approval/rejection.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder, SLAStatus
from app.models.domain.change_order_audit_log import ChangeOrderAuditLog
from app.models.domain.user import User
from app.services.approval_matrix_service import ApprovalMatrixService
from app.services.financial_impact_service import FinancialImpactService
from app.services.sla_service import SLAService

if TYPE_CHECKING:
    from app.services.change_order_service import ChangeOrderService  # noqa: F401


class ChangeOrderWorkflowService:
    """Encapsulates Change Order workflow state transitions and business rules.

    This service is designed as a simple state machine that can be replaced
    with a full business process workflow engine in future iterations.

    Workflow States (from FR-8.3):
    Draft → Submitted for Approval → Under Review → Approved/Rejected → Implemented

    Future Migration: Replace implementation with Camunda/Temporal while keeping
    the same interface methods.
    """

    # Define valid transitions
    _TRANSITIONS: dict[str, list[str]] = {
        "Draft": ["Submitted for Approval"],
        "Submitted for Approval": ["Under Review", "Approved", "Rejected"],
        "Under Review": ["Approved", "Rejected"],
        "Rejected": ["Draft", "Submitted for Approval"],
        "Approved": ["Implemented"],
        "Implemented": [],  # Terminal state
    }

    # Define which transitions trigger branch lock
    _LOCK_TRANSITIONS: set[tuple[str, str]] = {
        ("Draft", "Submitted for Approval"),
    }

    # Define which transitions trigger branch unlock
    _UNLOCK_TRANSITIONS: set[tuple[str, str]] = {
        ("Under Review", "Rejected"),
    }

    # Define which statuses allow editing
    _EDITABLE_STATUSES: set[str] = {"Draft", "Rejected"}

    async def get_next_status(self, current: str) -> str | None:
        """Get the single next status if the workflow is linear from current state.

        Returns None if multiple transitions are possible (e.g., from "Under Review").
        Use get_available_transitions() for non-linear branches.

        Args:
            current: Current workflow status

        Returns:
            Next status str if linear, None if multiple options
        """
        options = self._TRANSITIONS.get(current, [])
        return options[0] if len(options) == 1 else None

    async def get_available_transitions(self, current: str) -> list[str]:
        """Get all valid status transitions from the current state.

        Args:
            current: Current workflow status

        Returns:
            List of valid status strings that can be transitioned to
        """
        return self._TRANSITIONS.get(current, []).copy()

    async def should_lock_on_transition(self, from_status: str, to_status: str) -> bool:
        """Determine if a status transition should lock the branch.

        Args:
            from_status: Current workflow status
            to_status: Target workflow status

        Returns:
            True if branch should be locked after this transition
        """
        return (from_status, to_status) in self._LOCK_TRANSITIONS

    async def should_unlock_on_transition(
        self, from_status: str, to_status: str
    ) -> bool:
        """Determine if a status transition should unlock the branch.

        Args:
            from_status: Current workflow status
            to_status: Target workflow status

        Returns:
            True if branch should be unlocked after this transition
        """
        return (from_status, to_status) in self._UNLOCK_TRANSITIONS

    async def can_edit_on_status(self, status: str) -> bool:
        """Determine if Change Order details can be edited in this status.

        Args:
            status: Current workflow status

        Returns:
            True if CO fields can be modified, False if read-only
        """
        return status in self._EDITABLE_STATUSES

    async def is_valid_transition(self, from_status: str, to_status: str) -> bool:
        """Validate if a status transition is allowed.

        Args:
            from_status: Current workflow status
            to_status: Target workflow status

        Returns:
            True if transition is valid per workflow rules
        """
        valid_options = self._TRANSITIONS.get(from_status, [])
        return to_status in valid_options

    async def submit_for_approval(
        self,
        change_order_id: UUID,
        actor_id: UUID,
        db_session: AsyncSession,
    ) -> ChangeOrder:
        """Submit a change order for approval with automatic impact calculation and approver assignment.

        This method orchestrates the submission workflow by:
        1. Calculating financial impact level using FinancialImpactService
        2. Assigning appropriate approver using ApprovalMatrixService
        3. Setting SLA deadline using SLAService
        4. Transitioning status from "Draft" to "Submitted for Approval"
        5. Creating audit log entry

        Args:
            change_order_id: UUID of the change order to submit
            actor_id: UUID of the user submitting the change order
            db_session: Async database session for operations

        Returns:
            Updated ChangeOrder with impact level, approver, and SLA fields populated

        Raises:
            ValueError: If change order not found, not in Draft status, or no eligible approver

        Example:
            >>> workflow = ChangeOrderWorkflowService()
            >>> co = await workflow.submit_for_approval(co_id, user_id, session)
            >>> print(co.status)
            'Submitted for Approval'
            >>> print(co.impact_level)
            'MEDIUM'
        """
        # Import here to avoid circular import
        from app.services.change_order_service import ChangeOrderService

        # Get change order service for database operations
        co_service = ChangeOrderService(db_session)

        # Get current version of change order
        current_co = await co_service.get_as_of(change_order_id, branch="main")
        if current_co is None:
            raise ValueError(f"Change order {change_order_id} not found")

        # Validate current status is Draft
        if current_co.status != "Draft":
            raise ValueError(
                f"Cannot submit change order in status '{current_co.status}'. "
                "Only Draft change orders can be submitted for approval."
            )

        # Calculate financial impact level
        financial_service = FinancialImpactService(db_session)
        impact_level = await financial_service.calculate_impact_level(change_order_id)

        # Assign approver based on impact level
        approval_service = ApprovalMatrixService(db_session)
        approver_id = await approval_service.get_approver_for_impact(
            current_co.project_id, impact_level
        )

        if approver_id is None:
            raise ValueError(
                f"No eligible approver found for impact level '{impact_level}'. "
                "Please ensure users with appropriate roles exist."
            )

        # Calculate SLA deadline
        sla_service = SLAService(db_session)
        submission_time = datetime.now(UTC)
        sla_deadline = sla_service.calculate_sla_deadline(impact_level, submission_time)

        # Prepare update data
        update_data = {
            "status": "Submitted for Approval",
            "impact_level": impact_level,
            "assigned_approver_id": approver_id,
            "sla_assigned_at": submission_time,
            "sla_due_date": sla_deadline,
            "sla_status": SLAStatus.PENDING,
        }

        # Import Pydantic schema for update
        from app.models.schemas.change_order import ChangeOrderUpdate

        change_order_update = ChangeOrderUpdate(**update_data)

        # Update change order status and approval fields
        updated_co = await co_service.update_change_order(
            change_order_id=change_order_id,
            change_order_in=change_order_update,
            actor_id=actor_id,
            branch="main",
        )

        # Create audit log entry for submission
        audit_entry = ChangeOrderAuditLog(
            change_order_id=change_order_id,
            old_status="Draft",
            new_status="Submitted for Approval",
            comment=f"Submitted for approval. Impact level: {impact_level}, SLA deadline: {sla_deadline.isoformat()}",
            changed_by=actor_id,
        )
        db_session.add(audit_entry)
        await db_session.flush()

        return updated_co

    async def approve_change_order(
        self,
        change_order_id: UUID,
        actor_id: UUID,
        comments: str | None,
        db_session: AsyncSession,
    ) -> ChangeOrder:
        """Approve a change order after validating approver authority.

        This method validates that the actor has sufficient authority to approve
        the change order based on its impact level, then transitions the status
        to "Approved" and records the approval in the audit log.

        Args:
            change_order_id: UUID of the change order to approve
            actor_id: UUID of the user attempting to approve
            comments: Optional approval comments for audit trail
            db_session: Async database session for operations

        Returns:
            Updated ChangeOrder with status "Approved"

        Raises:
            ValueError: If change order not found, not submitted for approval,
                       or actor lacks authority to approve

        Example:
            >>> workflow = ChangeOrderWorkflowService()
            >>> co = await workflow.approve_change_order(
            ...     co_id, manager_id, "Approved as requested", session
            ... )
            >>> print(co.status)
            'Approved'
        """
        # Import here to avoid circular import
        from app.services.change_order_service import ChangeOrderService

        # Get change order service for database operations
        co_service = ChangeOrderService(db_session)

        # Get current version of change order
        current_co = await co_service.get_as_of(change_order_id, branch="main")
        if current_co is None:
            raise ValueError(f"Change order {change_order_id} not found")

        # Validate current status is "Submitted for Approval"
        if current_co.status not in ["Submitted for Approval", "Under Review"]:
            raise ValueError(
                f"Cannot approve change order in status '{current_co.status}'. "
                "Only change orders in 'Submitted for Approval' or 'Under Review' status can be approved."
            )

        # Get actor (approver) user object
        from sqlalchemy import select

        user_stmt = select(User).where(
            User.user_id == actor_id,
            User.deleted_at.is_(None),
        )
        user_result = await db_session.execute(user_stmt)
        actor = user_result.scalar_one_or_none()

        if actor is None:
            raise ValueError(f"User {actor_id} not found")

        # Validate approver authority
        approval_service = ApprovalMatrixService(db_session)
        can_approve = await approval_service.can_approve(actor, current_co)

        if not can_approve:
            # Get required authority for error message (handle None case)
            required_authority = (
                approval_service.get_authority_for_impact(current_co.impact_level)
                if current_co.impact_level
                else "UNKNOWN"
            )
            user_authority = approval_service.get_user_authority_level(actor)
            raise ValueError(
                f"User {actor_id} does not have sufficient authority to approve "
                f"change order with impact level '{current_co.impact_level}'. "
                f"Required authority: {required_authority}, "
                f"User authority: {user_authority}"
            )

        # Prepare update data with comment
        update_data = {
            "status": "Approved",
            "comment": comments,
        }

        # Import Pydantic schema for update
        from app.models.schemas.change_order import ChangeOrderUpdate

        change_order_update = ChangeOrderUpdate(**update_data)

        # Update change order status (comment is in the update schema)
        updated_co = await co_service.update_change_order(
            change_order_id=change_order_id,
            change_order_in=change_order_update,
            actor_id=actor_id,
            branch="main",
        )

        # Audit log entry is created by update_change_order if comment is provided
        # But we should create one without comment if none provided
        if not comments:
            audit_entry = ChangeOrderAuditLog(
                change_order_id=change_order_id,
                old_status="Submitted for Approval",
                new_status="Approved",
                comment=f"Approved by {actor.full_name}",
                changed_by=actor_id,
            )
            db_session.add(audit_entry)
            await db_session.flush()

        return updated_co

    async def reject_change_order(
        self,
        change_order_id: UUID,
        actor_id: UUID,
        comments: str | None,
        db_session: AsyncSession,
    ) -> ChangeOrder:
        """Reject a change order after validating approver authority.

        This method validates that the actor has sufficient authority to reject
        the change order based on its impact level, then transitions the status
        to "Rejected", clears SLA fields, unlocks the branch, and records the
        rejection in the audit log.

        Args:
            change_order_id: UUID of the change order to reject
            actor_id: UUID of the user attempting to reject
            comments: Optional rejection comments for audit trail
            db_session: Async database session for operations

        Returns:
            Updated ChangeOrder with status "Rejected" and SLA fields cleared

        Raises:
            ValueError: If change order not found, not submitted for approval,
                       or actor lacks authority to reject

        Example:
            >>> workflow = ChangeOrderWorkflowService()
            >>> co = await workflow.reject_change_order(
            ...     co_id, manager_id, "Insufficient justification", session
            ... )
            >>> print(co.status)
            'Rejected'
            >>> print(co.sla_due_date)
            None
        """
        # Import here to avoid circular import
        from app.services.change_order_service import ChangeOrderService

        # Get change order service for database operations
        co_service = ChangeOrderService(db_session)

        # Get current version of change order
        current_co = await co_service.get_as_of(change_order_id, branch="main")
        if current_co is None:
            raise ValueError(f"Change order {change_order_id} not found")

        # Validate current status is "Submitted for Approval"
        if current_co.status not in ["Submitted for Approval", "Under Review"]:
            raise ValueError(
                f"Cannot reject change order in status '{current_co.status}'. "
                "Only change orders in 'Submitted for Approval' or 'Under Review' status can be rejected."
            )

        # Get actor (approver) user object
        from sqlalchemy import select

        user_stmt = select(User).where(
            User.user_id == actor_id,
            User.deleted_at.is_(None),
        )
        user_result = await db_session.execute(user_stmt)
        actor = user_result.scalar_one_or_none()

        if actor is None:
            raise ValueError(f"User {actor_id} not found")

        # Validate approver authority
        approval_service = ApprovalMatrixService(db_session)
        can_approve = await approval_service.can_approve(actor, current_co)

        if not can_approve:
            # Get required authority for error message (handle None case)
            required_authority = (
                approval_service.get_authority_for_impact(current_co.impact_level)
                if current_co.impact_level
                else "UNKNOWN"
            )
            user_authority = approval_service.get_user_authority_level(actor)
            raise ValueError(
                f"User {actor_id} does not have sufficient authority to reject "
                f"change order with impact level '{current_co.impact_level}'. "
                f"Required authority: {required_authority}, "
                f"User authority: {user_authority}"
            )

        # Prepare update data - clear SLA fields and set status, include comment
        update_data = {
            "status": "Rejected",
            "assigned_approver_id": None,
            "sla_assigned_at": None,
            "sla_due_date": None,
            "sla_status": None,
            "comment": comments,
        }

        # Import Pydantic schema for update
        from app.models.schemas.change_order import ChangeOrderUpdate

        change_order_update = ChangeOrderUpdate(**update_data)

        # Update change order status (this will also unlock the branch via workflow transition)
        updated_co = await co_service.update_change_order(
            change_order_id=change_order_id,
            change_order_in=change_order_update,
            actor_id=actor_id,
            branch="main",
        )

        # Audit log entry is created by update_change_order if comment is provided
        # But we should create one without comment if none provided
        if not comments:
            audit_entry = ChangeOrderAuditLog(
                change_order_id=change_order_id,
                old_status="Submitted for Approval",
                new_status="Rejected",
                comment=f"Rejected by {actor.full_name}",
                changed_by=actor_id,
            )
            db_session.add(audit_entry)
            await db_session.flush()

        return updated_co
