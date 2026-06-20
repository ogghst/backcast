"""Change Order Workflow Service - configurable state machine.

This service encapsulates Change Order workflow state transitions and business rules.
Transition rules are loaded from the workflow configuration (co_workflow_config table)
with fallback to hardcoded defaults when no config is available.

Workflow States (from FR-8.3):
Draft -> Submitted for Approval -> Under Review -> Approved/Rejected -> Implemented

Context: This service orchestrates the approval workflow by integrating with
FinancialImpactService, UnifiedRBACService, and SLAService to manage the
complete approval lifecycle from submission to approval/rejection.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ChangeOrderStatus
from app.core.notifications import NotificationType
from app.core.rbac_unified import (
    get_unified_rbac_service,
    set_unified_rbac_session,
)
from app.models.domain.change_order import ChangeOrder, SLAStatus
from app.models.domain.change_order_audit_log import ChangeOrderAuditLog
from app.models.domain.user import User
from app.services.financial_impact_service import FinancialImpactService
from app.services.sla_service import SLAService

logger = logging.getLogger(__name__)


# Maps the legacy change-order event strings to unified registry codes. Kept in
# sync with ``change_order_service._CO_EVENT_TYPE_MAP``.
_CO_EVENT_TYPE_MAP: dict[str, str] = {
    "co_submitted": NotificationType.CO_SUBMITTED.value,
    "co_approved": NotificationType.CO_APPROVED.value,
    "co_rejected": NotificationType.CO_REJECTED.value,
    "co_escalated": NotificationType.CO_ESCALATED.value,
}

if TYPE_CHECKING:
    from app.services.change_order_config_service import ChangeOrderConfigService
    from app.services.change_order_service import ChangeOrderService  # noqa: F401


class ChangeOrderWorkflowService:
    """Encapsulates Change Order workflow state transitions and business rules.

    Transitions are loaded from config when a config_service is provided,
    otherwise falls back to hardcoded defaults.
    """

    # Default transition rules (used when no config available)
    _DEFAULT_TRANSITIONS: dict[str, list[str]] = {
        ChangeOrderStatus.DRAFT.value: [ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value],
        ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value: [
            ChangeOrderStatus.UNDER_REVIEW.value,
            ChangeOrderStatus.APPROVED.value,
            ChangeOrderStatus.REJECTED.value,
        ],
        ChangeOrderStatus.UNDER_REVIEW.value: [
            ChangeOrderStatus.APPROVED.value,
            ChangeOrderStatus.REJECTED.value,
        ],
        ChangeOrderStatus.REJECTED.value: [
            ChangeOrderStatus.DRAFT.value,
            ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
        ],
        ChangeOrderStatus.APPROVED.value: [ChangeOrderStatus.IMPLEMENTED.value],
        ChangeOrderStatus.IMPLEMENTED.value: [],
    }

    _DEFAULT_LOCK_TRANSITIONS: set[tuple[str, str]] = {
        (ChangeOrderStatus.DRAFT.value, ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value),
    }

    _DEFAULT_UNLOCK_TRANSITIONS: set[tuple[str, str]] = {
        (ChangeOrderStatus.UNDER_REVIEW.value, ChangeOrderStatus.REJECTED.value),
    }

    _DEFAULT_EDITABLE_STATUSES: set[str] = {
        ChangeOrderStatus.DRAFT.value,
        ChangeOrderStatus.REJECTED.value,
    }

    def __init__(
        self,
        config_service: ChangeOrderConfigService | None = None,
        project_id: UUID | None = None,
    ) -> None:
        self._config_service = config_service
        self._project_id = project_id
        self._loaded_transitions: dict[str, Any] | None = None

    async def _load_transitions(self) -> dict[str, Any]:
        """Load workflow transitions from config, fallback to defaults."""
        if self._loaded_transitions is not None:
            return self._loaded_transitions

        if self._config_service is not None:
            from app.services.change_order_config_service import ConfigurationError

            try:
                transitions = await self._config_service.get_workflow_transitions(
                    self._project_id
                )
                if transitions is not None:
                    self._loaded_transitions = transitions
                    return transitions
            except ConfigurationError:
                pass

        self._loaded_transitions = {
            "transitions": self._DEFAULT_TRANSITIONS,
            "lock_transitions": [[p[0], p[1]] for p in self._DEFAULT_LOCK_TRANSITIONS],
            "unlock_transitions": [
                [p[0], p[1]] for p in self._DEFAULT_UNLOCK_TRANSITIONS
            ],
            "editable_statuses": list(self._DEFAULT_EDITABLE_STATUSES),
        }
        return self._loaded_transitions

    async def get_next_status(self, current: str) -> str | None:
        """Get the single next status if the workflow is linear from current state.

        Returns None if multiple transitions are possible (e.g., from "Under Review").
        Use get_available_transitions() for non-linear branches.

        Args:
            current: Current workflow status

        Returns:
            Next status str if linear, None if multiple options
        """
        config = await self._load_transitions()
        options = config["transitions"].get(current, [])
        return options[0] if len(options) == 1 else None

    async def get_available_transitions(self, current: str) -> list[str]:
        """Get all valid status transitions from the current state.

        Args:
            current: Current workflow status

        Returns:
            List of valid status strings that can be transitioned to
        """
        config = await self._load_transitions()
        return config["transitions"].get(current, []).copy()

    async def should_lock_on_transition(self, from_status: str, to_status: str) -> bool:
        """Determine if a status transition should lock the branch.

        Args:
            from_status: Current workflow status
            to_status: Target workflow status

        Returns:
            True if branch should be locked after this transition
        """
        config = await self._load_transitions()
        lock_pairs = config.get("lock_transitions", [])
        return [from_status, to_status] in lock_pairs

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
        config = await self._load_transitions()
        unlock_pairs = config.get("unlock_transitions", [])
        return [from_status, to_status] in unlock_pairs

    async def can_edit_on_status(self, status: str) -> bool:
        """Determine if Change Order details can be edited in this status.

        Args:
            status: Current workflow status

        Returns:
            True if CO fields can be modified, False if read-only
        """
        config = await self._load_transitions()
        return status in config.get("editable_statuses", [])

    async def is_valid_transition(self, from_status: str, to_status: str) -> bool:
        """Validate if a status transition is allowed.

        Args:
            from_status: Current workflow status
            to_status: Target workflow status

        Returns:
            True if transition is valid per workflow rules
        """
        config = await self._load_transitions()
        valid_options = config["transitions"].get(from_status, [])
        return to_status in valid_options

    async def _send_notification(
        self,
        db_session: AsyncSession,
        user_id: UUID,
        actor_id: UUID,
        event_type: str,
        title: str,
        message: str,
        resource_type: str = "change_order",
        resource_id: UUID | None = None,
    ) -> None:
        """Send a change-order notification via the unified dispatcher.

        Routes legacy ``co_*`` event strings through :func:`user_emitter` so the
        notification persists with the new ``actor_type``/``severity`` columns
        and delivers real-time. Never raises: failures are logged.

        Args:
            db_session: Async database session (caller's transaction).
            user_id: UUID of the recipient user.
            actor_id: UUID of the user triggering the workflow action.
            event_type: Legacy event string (``co_submitted`` | ``co_approved``
                | ``co_rejected`` | ``co_escalated``).
            title: Short headline.
            message: Full body text.
            resource_type: Related entity type (default: 'change_order').
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
            await user_emitter(actor_id, db_session).emit(
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

    async def submit_for_approval(
        self,
        change_order_id: UUID,
        actor_id: UUID,
        db_session: AsyncSession,
    ) -> ChangeOrder:
        """Submit a change order for approval with automatic impact calculation and approver assignment.

        This method orchestrates the submission workflow by:
        1. Calculating financial impact level using FinancialImpactService
        2. Assigning appropriate approver using UnifiedRBACService
        3. Setting SLA deadline using SLAService
        4. Transitioning status from "Draft" to "Submitted for Approval" (using enum values)
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
        if current_co.status != ChangeOrderStatus.DRAFT.value:
            raise ValueError(
                f"Cannot submit change order in status '{current_co.status}'. "
                f"Only {ChangeOrderStatus.DRAFT.value} change orders can be submitted for approval."
            )

        # Calculate financial impact level
        financial_service = FinancialImpactService(db_session)
        impact_level = await financial_service.calculate_impact_level(change_order_id)

        # Assign approver based on impact level (excluding CO creator for SoD)
        set_unified_rbac_session(db_session)
        try:
            unified_rbac = get_unified_rbac_service()
            approver_id = await unified_rbac.get_approver_for_impact(
                current_co.project_id,
                impact_level,
                exclude_user_id=current_co.created_by,
            )
        finally:
            set_unified_rbac_session(None)

        if approver_id is None:
            raise ValueError(
                f"No eligible approver found for impact level '{impact_level}'. "
                "Please ensure users with appropriate roles exist."
            )

        # Calculate SLA deadline
        sla_service = SLAService(db_session)
        submission_time = datetime.now(UTC)
        sla_deadline = await sla_service.calculate_sla_deadline(
            impact_level, submission_time
        )

        # Prepare update data
        update_data = {
            "status": ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
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
            old_status=ChangeOrderStatus.DRAFT.value,
            new_status=ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
            comment=f"Submitted for approval. Impact level: {impact_level}, SLA deadline: {sla_deadline.isoformat()}",
            changed_by=actor_id,
        )
        db_session.add(audit_entry)
        await db_session.flush()

        await self._send_notification(
            db_session,
            approver_id,
            actor_id,
            "co_submitted",
            "Change Order Submitted for Approval",
            f"Change order requires your approval. Impact level: {impact_level}",
            resource_id=change_order_id,
        )

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

        # Separation of duties: creator cannot approve their own CO
        if current_co.created_by == actor_id:
            raise ValueError(
                "Cannot approve your own change order. "
                "Separation of duties requires a different approver."
            )

        # Validate current status is "Submitted for Approval"
        if current_co.status not in [
            ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
            ChangeOrderStatus.UNDER_REVIEW.value,
        ]:
            raise ValueError(
                f"Cannot approve change order in status '{current_co.status}'. "
                f"Only change orders in '{ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value}' or "
                f"'{ChangeOrderStatus.UNDER_REVIEW.value}' status can be approved."
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

        # Validate approver authority via unified RBAC
        set_unified_rbac_session(db_session)
        try:
            unified_rbac = get_unified_rbac_service()

            # Check if user has permission to approve change orders
            can_approve = await unified_rbac.has_permission(
                user_id=actor_id,
                required_permission="change-order-approve",
                scope_type="project",
                scope_id=current_co.project_id,
            )
        finally:
            set_unified_rbac_session(None)

        if not can_approve:
            # Get required authority for detailed error message
            from app.services.change_order_config_service import (
                ChangeOrderConfigService,
            )

            config_service = ChangeOrderConfigService(db_session)
            impact_authority = await config_service.get_impact_authority_mapping()
            required_authority = (
                impact_authority.get(current_co.impact_level, "UNKNOWN")
                if current_co.impact_level
                else "UNKNOWN"
            )
            raise ValueError(
                f"User {actor_id} does not have sufficient authority to approve "
                f"change order with impact level '{current_co.impact_level}'. "
                f"Required authority: {required_authority}"
            )

        # Prepare update data with comment
        update_data = {
            "status": ChangeOrderStatus.APPROVED.value,
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
                old_status=ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
                new_status=ChangeOrderStatus.APPROVED.value,
                comment=f"Approved by {actor.full_name}",
                changed_by=actor_id,
            )
            db_session.add(audit_entry)
            await db_session.flush()

        await self._send_notification(
            db_session,
            current_co.created_by,
            actor_id,
            "co_approved",
            "Change Order Approved",
            f"Your change order has been approved by {actor.full_name}",
            resource_id=change_order_id,
        )

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
        if current_co.status not in [
            ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
            ChangeOrderStatus.UNDER_REVIEW.value,
        ]:
            raise ValueError(
                f"Cannot reject change order in status '{current_co.status}'. "
                f"Only change orders in '{ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value}' or "
                f"'{ChangeOrderStatus.UNDER_REVIEW.value}' status can be rejected."
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

        # Validate approver authority via unified RBAC
        set_unified_rbac_session(db_session)
        try:
            unified_rbac = get_unified_rbac_service()
            can_approve = await unified_rbac.has_permission(
                user_id=actor_id,
                required_permission="change-order-approve",
                scope_type="project",
                scope_id=current_co.project_id,
            )
        finally:
            set_unified_rbac_session(None)

        if not can_approve:
            # Get required authority for detailed error message
            from app.services.change_order_config_service import (
                ChangeOrderConfigService,
            )

            config_service = ChangeOrderConfigService(db_session)
            impact_authority = await config_service.get_impact_authority_mapping()
            required_authority = (
                impact_authority.get(current_co.impact_level, "UNKNOWN")
                if current_co.impact_level
                else "UNKNOWN"
            )
            raise ValueError(
                f"User {actor_id} does not have sufficient authority to reject "
                f"change order with impact level '{current_co.impact_level}'. "
                f"Required authority: {required_authority}"
            )

        # Prepare update data - clear SLA fields and set status, include comment
        update_data = {
            "status": ChangeOrderStatus.REJECTED.value,
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
                old_status=ChangeOrderStatus.SUBMITTED_FOR_APPROVAL.value,
                new_status=ChangeOrderStatus.REJECTED.value,
                comment=f"Rejected by {actor.full_name}",
                changed_by=actor_id,
            )
            db_session.add(audit_entry)
            await db_session.flush()

        await self._send_notification(
            db_session,
            current_co.created_by,
            actor_id,
            "co_rejected",
            "Change Order Rejected",
            f"Your change order has been rejected by {actor.full_name}",
            resource_id=change_order_id,
        )

        return updated_co
