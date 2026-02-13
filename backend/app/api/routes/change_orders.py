"""Change Order API routes with RBAC."""

import logging
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user

if TYPE_CHECKING:
    from app.services.approval_matrix_service import ApprovalMatrixService
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.change_order import (
    ApprovalInfoPublic,
    ChangeOrderApproval,
    ChangeOrderCreate,
    ChangeOrderPublic,
    ChangeOrderRecoveryRequest,
    ChangeOrderUpdate,
    MergeRequest,
)
from app.models.schemas.impact_analysis import ImpactAnalysisResponse
from app.services.change_order_service import ChangeOrderService
from app.services.impact_analysis_service import ImpactAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_change_order_service(
    session: AsyncSession = Depends(get_db),
) -> ChangeOrderService:
    return ChangeOrderService(session)


def get_impact_analysis_service(
    session: AsyncSession = Depends(get_db),
) -> ImpactAnalysisService:
    return ImpactAnalysisService(session)


def get_approval_matrix_service(
    session: AsyncSession = Depends(get_db),
) -> "ApprovalMatrixService":
    """Get ApprovalMatrixService instance."""
    from app.services.approval_matrix_service import ApprovalMatrixService

    return ApprovalMatrixService(session)


@router.get(
    "",
    response_model=None,  # Will be PaginatedResponse[ChangeOrderPublic]
    operation_id="get_change_orders",
    dependencies=[Depends(RoleChecker(required_permission="change-order-read"))],
)
async def read_change_orders(
    project_id: UUID = Query(..., description="Filter by project ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch name"),
    mode: str = Query(
        "merged",
        pattern="^(merged|isolated)$",
        description="Branch mode: merged (combine with main) or isolated (current branch only)",
    ),
    search: str | None = Query(None, description="Search term (code, title)"),
    filters: str | None = Query(
        None,
        description="Filters in format 'column:value;column:value1,value2'",
        examples={"status_filter": {"value": "status:Draft"}},
    ),
    sort_field: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query(
        "asc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get Change Orders as of this timestamp (ISO 8601)",
    ),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> dict[str, Any]:
    """Retrieve change orders for a project with pagination.

    Change Orders are always scoped to a specific project.
    The auto-created branch for each CO is named `BR-{code}`.

    Requires read permission.
    """
    from app.core.versioning.enums import BranchMode
    from app.models.schemas.common import PaginatedResponse

    # Parse mode string to BranchMode enum
    # Note: branch_mode is parsed but not currently used by get_change_orders service
    # This is reserved for future implementation of MERGE/STRICT mode filtering
    branch_mode = BranchMode.MERGE if mode == "merged" else BranchMode.STRICT  # noqa: F841

    # Calculate skip from page number
    skip = (page - 1) * per_page

    try:
        # Default to current time if as_of is not provided
        if as_of is None:
            from datetime import UTC
            as_of = datetime.now(tz=UTC)

        # Get change orders for the project
        change_orders, total = await service.get_change_orders(
            project_id=project_id,
            skip=skip,
            limit=per_page,
            branch=branch,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order,
            as_of=as_of,
        )

        # Convert to Pydantic models with workflow metadata
        items = [await service._to_public(co) for co in change_orders]

        # Return paginated response
        response = PaginatedResponse[ChangeOrderPublic](
            items=items,
            total=total,
            page=page,
            per_page=per_page,
        )

        return response.model_dump()

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "",
    response_model=ChangeOrderPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_change_order",
    dependencies=[Depends(RoleChecker(required_permission="change-order-create"))],
)
async def create_change_order(
    change_order_in: ChangeOrderCreate,
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderPublic:
    """Create a new change order with automatic branch creation.

    This endpoint:
    1. Creates the Change Order on the main branch
    2. Automatically creates a `BR-{code}` branch for isolated work
    3. Returns the created Change Order

    The auto-created branch allows changes to be developed in isolation
    before merging to main when approved.

    Requires create permission.
    """
    try:
        # Check if change order code already exists (on main branch)
        existing = await service.get_current_by_code(
            change_order_in.code, branch="main"
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Change Order with code '{change_order_in.code}' already exists",
            )

        change_order = await service.create_change_order(
            change_order_in=change_order_in,
            actor_id=current_user.user_id,
        )
        return await service._to_public(change_order)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{change_order_id}",
    response_model=ChangeOrderPublic,
    operation_id="get_change_order",
    dependencies=[Depends(RoleChecker(required_permission="change-order-read"))],
)
async def read_change_order(
    change_order_id: UUID,
    branch: str = Query("main", description="Branch name"),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get change order state as of this timestamp (ISO 8601)",
    ),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderPublic:
    """Get a specific change order by change_order_id (UUID root identifier).

    Supports time-travel queries via the as_of parameter to view
    the change order's state at any historical point in time.

    Requires read permission.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC
        as_of = datetime.now(tz=UTC)

    if as_of:
        # Time travel query
        change_order = await service.get_as_of(change_order_id, as_of, branch=branch)

    if not change_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change Order not found" + (f" as of {as_of}" if as_of else ""),
        )
    return await service._to_public(change_order)


@router.get(
    "/by-code/{code}",
    response_model=ChangeOrderPublic,
    operation_id="get_change_order_by_code",
    dependencies=[Depends(RoleChecker(required_permission="change-order-read"))],
)
async def read_change_order_by_code(
    code: str,
    branch: str = Query("main", description="Branch name"),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderPublic:
    """Get a change order by business code (e.g., "CO-2026-001").

    Returns the current active version on the specified branch.

    Requires read permission.
    """
    change_order = await service.get_current_by_code(code, branch=branch)

    if not change_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change Order with code '{code}' not found",
        )
    return await service._to_public(change_order)


@router.put(
    "/{change_order_id}",
    response_model=ChangeOrderPublic,
    operation_id="update_change_order",
    dependencies=[Depends(RoleChecker(required_permission="change-order-update"))],
)
async def update_change_order(
    change_order_id: UUID,
    change_order_in: ChangeOrderUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderPublic:
    """Update a change order's metadata.

    Creates a new version with the updated metadata. Optionally specify a branch
    to update on a specific branch (will auto-fork from main if no version exists
    on the target branch).

    Requires update permission.
    """
    logger.info(
        f"[API DEBUG] update_change_order START - change_order_id={change_order_id}, user_id={current_user.user_id}, branch={change_order_in.branch}"
    )
    try:
        updated_change_order = await service.update_change_order(
            change_order_id=change_order_id,
            change_order_in=change_order_in,
            actor_id=current_user.user_id,
            branch=change_order_in.branch,
        )
        logger.info(
            f"[API DEBUG] update_change_order SUCCESS - updated_co id={updated_change_order.id}, branch={updated_change_order.branch}"
        )
        return await service._to_public(updated_change_order)
    except ValueError as e:
        # Include more context in the error response
        error_detail = f"{str(e)} (change_order_id={change_order_id}, user_id={current_user.user_id})"
        logger.error(f"[API DEBUG] update_change_order ERROR - {error_detail}")
        raise HTTPException(status_code=404, detail=error_detail) from e
    except Exception as e:
        # Catch any unexpected errors and include them
        error_detail = f"Unexpected error: {str(e)} (change_order_id={change_order_id})"
        logger.error(
            f"[API DEBUG] update_change_order UNEXPECTED ERROR - {error_detail}"
        )
        raise HTTPException(status_code=500, detail=error_detail) from e


@router.delete(
    "/{change_order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_change_order",
    dependencies=[Depends(RoleChecker(required_permission="change-order-delete"))],
)
async def delete_change_order(
    change_order_id: UUID,
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> None:
    """Soft delete a change order.

    Marks the current version as deleted.

    Requires delete permission.
    """
    try:
        await service.delete_change_order(
            change_order_id=change_order_id,
            actor_id=current_user.user_id,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/{change_order_id}/history",
    response_model=list[ChangeOrderPublic],
    operation_id="get_change_order_history",
    dependencies=[Depends(RoleChecker(required_permission="change-order-read"))],
)
async def read_change_order_history(
    change_order_id: UUID,
    service: ChangeOrderService = Depends(get_change_order_service),
) -> Sequence[ChangeOrderPublic]:
    """Get version history for a change order.

    Returns all versions across all branches, showing the complete
    audit trail of changes.

    Requires read permission.
    """
    history = await service.get_history(change_order_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No history found for this change order",
        )
    return [await service._to_public(co) for co in history]


@router.get(
    "/{change_order_id}/merge-conflicts",
    operation_id="get_merge_conflicts",
    dependencies=[Depends(RoleChecker(required_permission="change-order-read"))],
)
async def get_merge_conflicts(
    change_order_id: UUID,
    source_branch: str = Query(..., description="Source branch name (e.g., 'BR-123')"),
    target_branch: str = Query(
        "main", description="Target branch name (default: 'main')"
    ),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> list[dict[str, Any]]:
    """Check for merge conflicts between source and target branches.

    Returns a list of conflict details if conflicts exist, or an empty list if no conflicts.

    Requires read permission.
    """
    try:
        conflicts = await service._detect_merge_conflicts(
            root_id=change_order_id,
            source_branch=source_branch,
            target_branch=target_branch,
        )
        return conflicts
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/{change_order_id}/merge",
    response_model=ChangeOrderPublic,
    operation_id="merge_change_order",
    dependencies=[Depends(RoleChecker(required_permission="change-order-update"))],
)
async def merge_change_order(
    change_order_id: UUID,
    merge_request: MergeRequest,
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderPublic:
    """Merge a Change Order's branch into the target branch.

    Infers the source branch from the Change Order code (e.g., `BR-{code}`).

    Checks for merge conflicts before proceeding. If conflicts exist,
    returns 409 with conflict details.

    Requires update permission.
    """
    try:
        # Get current CO to find source branch
        current = await service.get_current(
            change_order_id, branch=merge_request.target_branch
        )
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Change Order {change_order_id} not found",
            )

        source_branch = f"BR-{current.code}"

        # Check for conflicts
        conflicts = await service._detect_merge_conflicts(
            root_id=change_order_id,
            source_branch=source_branch,
            target_branch=merge_request.target_branch,
        )

        if conflicts:
            # Return 409 with conflict details
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Merge blocked by conflicts",
                    "conflicts": conflicts,
                },
            )

        # Perform merge
        merged_co = await service.merge_change_order(
            change_order_id=change_order_id,
            actor_id=current_user.user_id,
            target_branch=merge_request.target_branch,
        )

        # If comment provided, store in audit log
        if merge_request.comment:
            from sqlalchemy import select

            from app.models.domain.change_order_audit_log import ChangeOrderAuditLog

            # Check if status transition occurred (Approved -> Implemented)
            stmt = (
                select(ChangeOrderAuditLog)
                .where(
                    ChangeOrderAuditLog.change_order_id == change_order_id,
                    ChangeOrderAuditLog.new_status == "Implemented",
                )
                .order_by(ChangeOrderAuditLog.changed_at.desc())
            )

            result = await service.session.execute(stmt)
            audit_entry = result.scalar_one_or_none()

            if audit_entry:
                audit_entry.comment = merge_request.comment
                await service.session.flush()

        return await service._to_public(merged_co)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{change_order_id}/revert",
    response_model=ChangeOrderPublic,
    operation_id="revert_change_order",
    dependencies=[Depends(RoleChecker(required_permission="change-order-update"))],
)
async def revert_change_order(
    change_order_id: UUID,
    branch: str = Query("main", description="Branch to revert on"),
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderPublic:
    """Revert a Change Order to its previous version.

    Requires update permission.
    """
    try:
        reverted_co = await service.revert_change_order_version(
            change_order_id=change_order_id,
            actor_id=current_user.user_id,
            branch=branch,
        )
        return await service._to_public(reverted_co)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{change_order_id}/impact",
    response_model=ImpactAnalysisResponse,
    operation_id="get_change_order_impact",
    dependencies=[Depends(RoleChecker(required_permission="change-order-read"))],
)
async def get_change_order_impact(
    change_order_id: UUID,
    branch_name: str = Query(
        ..., description="Branch name to compare (e.g., 'BR-CO-2026-001')"
    ),
    mode: str = Query(
        "merged",
        pattern="^(merged|isolated)$",
        description="Comparison mode: merged (main+change) or isolated (change only)",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get impact analysis as of this timestamp (ISO 8601)",
    ),
    service: ImpactAnalysisService = Depends(get_impact_analysis_service),
) -> ImpactAnalysisResponse:
    """Get impact analysis for a change order by comparing branches.

    Analyzes the financial and schedule impact of a change order by comparing
    data between the main branch and the specified change branch.

    Modes:
    - merged: Shows merged result (main + change delta) - most intuitive for users
    - isolated: Shows isolated comparison (delta only) - for detailed analysis

    Returns:
        - KPI Scorecard: BAC, Budget Delta, Gross Margin comparison
        - Entity Changes: Added/Modified/Removed WBEs and Cost Elements
        - Waterfall Chart: Cost bridge visualization
        - Time Series: Weekly S-curve budget comparison

    Requires read permission.
    """
    from app.core.versioning.enums import BranchMode

    # Parse mode string to BranchMode enum
    branch_mode = BranchMode.MERGE if mode == "merged" else BranchMode.STRICT

    try:
        impact_analysis = await service.analyze_impact(
            change_order_id, branch_name, branch_mode=branch_mode, as_of=as_of
        )
        return impact_analysis
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.put(
    "/{change_order_id}/submit-for-approval",
    response_model=ChangeOrderPublic,
    operation_id="submit_change_order_for_approval",
    dependencies=[Depends(RoleChecker(required_permission="change-order-update"))],
)
async def submit_change_order_for_approval(
    change_order_id: UUID,
    branch: str = Query("main", description="Branch name"),
    comment: str | None = Query(None, description="Optional comment for audit log"),
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderPublic:
    """Submit a change order for approval with impact calculation and approver assignment.

    This endpoint:
    1. Calculates financial impact by comparing branches
    2. Determines impact level (LOW/MEDIUM/HIGH/CRITICAL)
    3. Assigns appropriate approver based on impact level
    4. Sets SLA deadline based on impact level
    5. Locks the branch to prevent further modifications
    6. Transitions status to "Submitted for Approval"

    Requires update permission.
    """
    try:
        submitted_co = await service.submit_for_approval(
            change_order_id=change_order_id,
            actor_id=current_user.user_id,
            branch=branch,
            comment=comment,
        )
        return await service._to_public(submitted_co)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.put(
    "/{change_order_id}/approve",
    response_model=ChangeOrderPublic,
    operation_id="approve_change_order",
    dependencies=[Depends(RoleChecker(required_permission="change-order-approve"))],
)
async def approve_change_order(
    change_order_id: UUID,
    approval: ChangeOrderApproval,
    branch: str = Query("main", description="Branch name"),
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderPublic:
    """Approve a change order and transition to Approved status.

    Validates that the current user has sufficient authority to approve
    this change order based on its impact level. Records approval with
    optional comments in the audit log.

    Requires approve permission.
    """
    try:
        approved_co = await service.approve_change_order(
            change_order_id=change_order_id,
            approver_id=current_user.user_id,
            actor_id=current_user.user_id,
            branch=branch,
            comments=approval.comments,
        )
        return await service._to_public(approved_co)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.put(
    "/{change_order_id}/reject",
    response_model=ChangeOrderPublic,
    operation_id="reject_change_order",
    dependencies=[Depends(RoleChecker(required_permission="change-order-approve"))],
)
async def reject_change_order(
    change_order_id: UUID,
    approval: ChangeOrderApproval,
    branch: str = Query("main", description="Branch name"),
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderPublic:
    """Reject a change order and transition to Rejected status.

    Validates that the current user has sufficient authority to reject
    this change order based on its impact level. Records rejection with
    optional comments in the audit log and unlocks the branch.

    Requires approve permission.
    """
    try:
        rejected_co = await service.reject_change_order(
            change_order_id=change_order_id,
            rejecter_id=current_user.user_id,
            actor_id=current_user.user_id,
            branch=branch,
            comments=approval.comments,
        )
        return await service._to_public(rejected_co)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{change_order_id}/recover",
    response_model=ChangeOrderPublic,
    operation_id="recover_change_order",
    dependencies=[Depends(RoleChecker(required_permission="change-order-recover"))],
)
async def recover_change_order(
    change_order_id: UUID,
    recovery_data: ChangeOrderRecoveryRequest,
    branch: str = Query("main", description="Branch name"),
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ChangeOrderPublic:
    """Recover a stuck change order workflow (admin only).

    Admin-only endpoint to recover stuck workflows when impact analysis
    fails or the change order gets stuck in an intermediate state.
    Allows manual override of impact level and approver assignment.

    Requires change-order-recover permission (admin only).

    Args:
        change_order_id: UUID of the stuck change order
        recovery_data: Recovery request with impact level, approver, and reason

    Returns:
        Updated ChangeOrder with recovered workflow state

    Raises:
        HTTPException: If change order not stuck, invalid data, or not authorized
    """
    try:
        recovered_co = await service.recover_change_order(
            change_order_id=change_order_id,
            impact_level=recovery_data.impact_level,
            assigned_approver_id=recovery_data.assigned_approver_id,
            skip_impact_analysis=recovery_data.skip_impact_analysis,
            recovery_reason=recovery_data.recovery_reason,
            actor_id=current_user.id,  # Use User.id, not User.user_id for FK
            branch=branch,
        )
        return await service._to_public(recovered_co)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{change_order_id}/approval-info",
    response_model=ApprovalInfoPublic,
    operation_id="get_change_order_approval_info",
    dependencies=[Depends(RoleChecker(required_permission="change-order-read"))],
)
async def get_change_order_approval_info(
    change_order_id: UUID,
    branch: str = Query("main", description="Branch name"),
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> ApprovalInfoPublic:
    """Get approval information for a change order.

    Returns comprehensive approval information including:
    - Impact level and financial impact details
    - Assigned approver details
    - SLA tracking (assigned date, due date, status, business days remaining)
    - Whether the current user can approve this change order
    - Current user's authority level

    Requires read permission.
    """
    from app.services.approval_matrix_service import ApprovalMatrixService
    from app.services.impact_analysis_service import ImpactAnalysisService

    try:
        # Get change order
        co = await service.get_current(change_order_id, branch=branch)
        if not co:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Change Order {change_order_id} not found",
            )

        # Get approval matrix service
        approval_service = ApprovalMatrixService(service.session)

        # Calculate financial impact
        financial_impact = None
        financial_impact = None
        if co.impact_level:
            branch_name = f"BR-{co.code}"
            impact_service = ImpactAnalysisService(service.session)
            # Optimization: Skip EVM metrics calculation as only financial delta is needed here
            impact_analysis = await impact_service.analyze_impact(
                change_order_id, branch_name, include_evm_metrics=False
            )
            financial_impact = {
                "budget_delta": impact_analysis.kpi_scorecard.budget_delta.delta,
                "revenue_delta": impact_analysis.kpi_scorecard.gross_margin.delta,
            }

        # Get assigned approver details
        assigned_approver = None
        if co.assigned_approver_id:
            from app.services.user import UserService

            user_service = UserService(service.session)
            approver = await user_service.get_by_id(co.assigned_approver_id)
            if approver:
                assigned_approver = {
                    "user_id": approver.user_id,
                    "full_name": approver.full_name,
                    "email": approver.email,
                    "role": approver.role,
                }

        # Get current user's authority level
        user_authority = approval_service.get_user_authority_level(current_user)

        # Check if current user can approve
        can_approve = await approval_service.can_approve(current_user, co)

        # Calculate business days remaining until SLA deadline
        sla_business_days_remaining = None
        if co.sla_due_date:
            from datetime import UTC, datetime

            sla_business_days_remaining = service._calculate_business_days_remaining(
                datetime.now(UTC), co.sla_due_date
            )

        # Determine SLA status
        sla_status = co.sla_status
        if co.sla_due_date:
            from datetime import UTC, datetime

            now = datetime.now(UTC)
            # Normalize sla_due_date to UTC if it's naive
            sla_due = co.sla_due_date
            if sla_due.tzinfo is None:
                sla_due = sla_due.replace(tzinfo=UTC)
            time_remaining = (sla_due - now).total_seconds() / 86400  # days

            if time_remaining < 0:
                sla_status = "overdue"
            elif time_remaining < (service._get_sla_days(co.impact_level) / 2):
                sla_status = "approaching"
            else:
                sla_status = "pending"

        return ApprovalInfoPublic(
            impact_level=co.impact_level,
            financial_impact=financial_impact,
            assigned_approver=assigned_approver,
            sla_assigned_at=co.sla_assigned_at,
            sla_due_date=co.sla_due_date,
            sla_status=sla_status,
            sla_business_days_remaining=sla_business_days_remaining,
            user_can_approve=can_approve,
            user_authority=user_authority,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving approval info: {str(e)}",
        ) from e


@router.get(
    "/pending-approvals",
    response_model=None,  # Will be PaginatedResponse[ChangeOrderPublic]
    operation_id="get_pending_approvals",
    dependencies=[Depends(RoleChecker(required_permission="change-order-read"))],
)
async def get_pending_approvals(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch name"),
    mode: str = Query(
        "merged",
        pattern="^(merged|isolated)$",
        description="Branch mode: merged (combine with main) or isolated (current branch only)",
    ),
    current_user: User = Depends(get_current_active_user),
    service: ChangeOrderService = Depends(get_change_order_service),
) -> dict[str, Any]:
    """Get change orders pending approval for the current user.

    Filters change orders by:
    - assigned_approver_id = current_user.user_id
    - status in ("Submitted for Approval", "Under Review")
    - branch name (default: "main")

    Returns paginated list of change orders awaiting the user's approval.

    Requires read permission.
    """
    from app.core.versioning.enums import BranchMode
    from app.models.schemas.common import PaginatedResponse

    # Parse mode string to BranchMode enum
    branch_mode = BranchMode.MERGE if mode == "merged" else BranchMode.STRICT

    # Calculate skip from page number
    skip = (page - 1) * per_page

    try:
        # Get pending approvals for current user
        change_orders, total = await service.get_pending_approvals(
            user_id=current_user.user_id,
            skip=skip,
            limit=per_page,
            branch=branch,
            branch_mode=branch_mode,
        )

        # Convert to Pydantic models with workflow metadata
        items = [await service._to_public(co) for co in change_orders]

        # Return paginated response
        response = PaginatedResponse[ChangeOrderPublic](
            items=items,
            total=total,
            page=page,
            per_page=per_page,
        )

        return response.model_dump()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving pending approvals: {str(e)}",
        ) from e
