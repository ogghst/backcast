"""Cost Registration API routes - CRUD for actual cost tracking."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.user import User
from app.models.schemas.common import PaginatedResponse
from app.models.schemas.cost_registration import (
    CostRegistrationCreate,
    CostRegistrationRead,
    CostRegistrationUpdate,
)
from app.services.cost_registration_service import (
    CostRegistrationService,
)

router = APIRouter()


def get_cost_registration_service(
    session: AsyncSession = Depends(get_db),
) -> CostRegistrationService:
    """Dependency to get CostRegistrationService instance."""
    return CostRegistrationService(session)


@router.get(
    "",
    response_model=None,  # PaginatedResponse[CostRegistrationRead]
    operation_id="get_cost_registrations",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-read"))],
)
async def read_cost_registrations(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch to query (for context)"),
    mode: str = Query(
        "merged",
        pattern="^(merged|isolated)$",
        description="Branch mode: merged (combine with main) or isolated (current branch only)",
    ),
    cost_element_id: UUID | None = Query(None, description="Filter by Cost Element ID"),
    wbe_id: UUID | None = Query(
        None, description="Filter by WBE ID (returns all registrations under this WBE)"
    ),
    project_id: UUID | None = Query(
        None,
        description="Filter by Project ID (returns all registrations under this project)",
    ),
    search: str | None = Query(
        None, description="Search term (description, invoice, vendor)"
    ),
    filters: str | None = Query(
        None,
        description="Filters in format 'column:value;column:value1,value2'",
    ),
    sort_field: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query(
        "asc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get Cost Registrations as of this timestamp (ISO 8601)",
    ),
    service: CostRegistrationService = Depends(get_cost_registration_service),
) -> dict[str, Any]:
    """Retrieve cost registrations with server-side search, filtering, and sorting.

    Cost registrations track actual expenditures against cost elements.
    They are versionable but NOT branchable (costs are global facts).
    Branch and mode parameters are provided for API consistency and context,
    though cost registrations themselves are not branch-specific.

    Filtering hierarchy: cost_element_id > wbe_id > project_id.
    When multiple are provided, all applicable filters are applied (AND).
    """
    # Build filters dict
    query_filters: dict[str, Any] = {}
    if cost_element_id:
        query_filters["cost_element_id"] = cost_element_id

    skip = (page - 1) * per_page

    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    items, total = await service.get_cost_registrations(
        filters=query_filters,
        skip=skip,
        limit=per_page,
        as_of=as_of,
        wbe_id=wbe_id,
        project_id=project_id,
    )

    # Convert to Pydantic models
    items_out = [CostRegistrationRead.model_validate(i) for i in items]

    # Return paginated response
    response = PaginatedResponse[CostRegistrationRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    )

    return response.model_dump()


@router.post(
    "",
    response_model=CostRegistrationRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_cost_registration",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-create"))],
)
async def create_cost_registration(
    registration_in: CostRegistrationCreate,
    current_user: User = Depends(get_current_active_user),
    service: CostRegistrationService = Depends(get_cost_registration_service),
) -> CostRegistration:
    """Create a new cost registration.

    Validates that the cost does not exceed the cost element's budget.
    Raises BudgetExceededError if budget would be exceeded.

    The control_date parameter allows setting the valid_time start date,
    useful for backdated cost registrations or testing time-travel scenarios.
    """
    try:
        return await service.create_cost_registration(
            registration_in=registration_in,
            actor_id=current_user.user_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# CRITICAL: Specific routes must be defined BEFORE the generic /{cost_registration_id} route
# to avoid FastAPI matching "aggregated" or "cumulative" as a cost_registration_id UUID.


@router.get(
    "/budget-status/{cost_element_id}",
    operation_id="get_budget_status",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-read"))],
)
async def get_budget_status(
    cost_element_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get budget status as of this timestamp (ISO 8601)",
    ),
    branch: str = Query(
        "main", description="Branch context to resolve Cost Element budget"
    ),
    service: CostRegistrationService = Depends(get_cost_registration_service),
) -> dict[str, Any]:
    """Get budget status for a cost element with time-travel support.

    Returns the budget amount, used amount, remaining amount, and percentage used.
    Useful for displaying budget progress bars and warnings.

    The as_of parameter allows viewing the budget status at any historical point in time,
    showing only cost registrations that were valid as of that timestamp.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    try:
        budget_status = await service.get_budget_status(
            cost_element_id, as_of=as_of, branch=branch
        )
        return {
            "cost_element_id": str(budget_status.cost_element_id),
            "budget": str(budget_status.budget),
            "used": str(budget_status.used),
            "remaining": str(budget_status.remaining),
            "percentage": float(budget_status.percentage),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/aggregated",
    operation_id="get_aggregated_costs",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-read"))],
)
async def get_aggregated_costs(
    cost_element_id: UUID = Query(
        ..., description="Cost Element ID to aggregate costs for"
    ),
    period: str = Query(
        ...,
        pattern="^(daily|weekly|monthly)$",
        description="Aggregation period (daily, weekly, or monthly)",
    ),
    start_date: datetime = Query(
        ..., description="Start date for aggregation (ISO 8601)"
    ),
    end_date: datetime | None = Query(
        None, description="End date for aggregation (ISO 8601, defaults to now)"
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get costs as of this timestamp (ISO 8601)",
    ),
    service: CostRegistrationService = Depends(get_cost_registration_service),
) -> list[dict[str, Any]]:
    """Get cost aggregations by time period.

    Returns costs aggregated by day, week, or month for a cost element.
    Useful for generating cost charts and trend analysis.

    Example:
        - period=daily: One row per day with total costs
        - period=weekly: One row per week (starts Monday) with total costs
        - period=monthly: One row per month (starts 1st) with total costs

    All costs respect time-travel queries via the as_of parameter.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    try:
        costs = await service.get_costs_by_period(
            cost_element_id=cost_element_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
            as_of=as_of,
        )
        return costs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/cumulative",
    operation_id="get_cumulative_costs",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-read"))],
)
async def get_cumulative_costs(
    cost_element_id: UUID = Query(
        ..., description="Cost Element ID to get cumulative costs for"
    ),
    start_date: datetime = Query(
        ..., description="Start date for calculation (ISO 8601)"
    ),
    end_date: datetime | None = Query(
        None, description="End date for calculation (ISO 8601, defaults to now)"
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get costs as of this timestamp (ISO 8601)",
    ),
    service: CostRegistrationService = Depends(get_cost_registration_service),
) -> list[dict[str, Any]]:
    """Get cumulative costs over time.

    Returns a time series of costs with running cumulative totals.
    Useful for S-curve charts and cumulative cost tracking.

    Each entry includes:
    - registration_date: Date of the cost registration
    - amount: Cost amount for that registration
    - cumulative_amount: Running total of all costs to date

    All costs respect time-travel queries via the as_of parameter.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    try:
        costs = await service.get_cumulative_costs(
            cost_element_id=cost_element_id,
            start_date=start_date,
            end_date=end_date,
            as_of=as_of,
        )
        return costs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Generic routes with path parameters must come AFTER specific routes


@router.get(
    "/{cost_registration_id}",
    response_model=CostRegistrationRead,
    operation_id="get_cost_registration",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-read"))],
)
async def read_cost_registration(
    cost_registration_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get cost registration state as of this timestamp (ISO 8601)",
    ),
    service: CostRegistrationService = Depends(get_cost_registration_service),
) -> CostRegistration:
    """Get a specific cost registration by id.

    Supports time-travel queries via the as_of parameter to view
    the cost registration's state at any historical point in time.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    if as_of:
        # Time travel query
        item = await service.get_cost_registration_as_of(
            cost_registration_id=cost_registration_id,
            as_of=as_of,
        )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost Registration not found" + (f" as of {as_of}" if as_of else ""),
        )
    return item


@router.put(
    "/{cost_registration_id}",
    response_model=CostRegistrationRead,
    operation_id="update_cost_registration",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-update"))],
)
async def update_cost_registration(
    cost_registration_id: UUID,
    registration_in: CostRegistrationUpdate,
    current_user: User = Depends(get_current_active_user),
    service: CostRegistrationService = Depends(get_cost_registration_service),
) -> CostRegistration:
    """Update a cost registration.

    Creates a new version of the cost registration with the updated values.
    Previous versions are preserved in the history.

    The control_date parameter allows setting the valid_time start date for
    the new version, useful for backdating updates or testing time-travel.
    """
    try:
        return await service.update_cost_registration(
            cost_registration_id=cost_registration_id,
            registration_in=registration_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{cost_registration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_cost_registration",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-delete"))],
)
async def delete_cost_registration(
    cost_registration_id: UUID,
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: User = Depends(get_current_active_user),
    service: CostRegistrationService = Depends(get_cost_registration_service),
) -> None:
    """Soft delete a cost registration.

    Marks the cost registration as deleted but preserves it in the history.
    """
    try:
        item = await service.get_by_id(cost_registration_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cost Registration not found",
            )

        await service.soft_delete(
            cost_registration_id=cost_registration_id,
            actor_id=current_user.user_id,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{cost_registration_id}/history",
    response_model=list[CostRegistrationRead],
    operation_id="get_cost_registration_history",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-read"))],
)
async def get_cost_registration_history(
    cost_registration_id: UUID,
    service: CostRegistrationService = Depends(get_cost_registration_service),
) -> Sequence[CostRegistration]:
    """Get full version history for a cost registration.

    Returns all versions of the cost registration, ordered by transaction time.
    Includes both current and historical versions.
    """
    return await service.get_history(cost_registration_id)
