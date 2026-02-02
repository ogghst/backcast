"""Change Order API routes with RBAC."""

import logging
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.change_order import (
    ChangeOrderCreate,
    ChangeOrderPublic,
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
    search: str | None = Query(None, description="Search term (code, title)"),
    filters: str | None = Query(
        None,
        description="Filters in format 'column:value;column:value1,value2'",
        example="status:Draft",
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
    The auto-created branch for each CO is named `co-{code}`.

    Requires read permission.
    """
    from app.models.schemas.common import PaginatedResponse

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
    2. Automatically creates a `co-{code}` branch for isolated work
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
    source_branch: str = Query(..., description="Source branch name (e.g., 'co-123')"),
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

    Infers the source branch from the Change Order code (e.g., `co-{code}`).

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

        source_branch = f"co-{current.code}"

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
        ..., description="Branch name to compare (e.g., 'co-CO-2026-001')"
    ),
    service: ImpactAnalysisService = Depends(get_impact_analysis_service),
) -> ImpactAnalysisResponse:
    """Get impact analysis for a change order by comparing branches.

    Analyzes the financial and schedule impact of a change order by comparing
    data between the main branch and the specified change branch.

    Returns:
        - KPI Scorecard: BAC, Budget Delta, Gross Margin comparison
        - Entity Changes: Added/Modified/Removed WBEs and Cost Elements
        - Waterfall Chart: Cost bridge visualization
        - Time Series: Weekly S-curve budget comparison

    Requires read permission.
    """
    try:
        impact_analysis = await service.analyze_impact(change_order_id, branch_name)
        return impact_analysis
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
