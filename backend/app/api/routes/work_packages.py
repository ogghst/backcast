"""Work Package API routes - PMI ANSI-748 work package (budget holder).

Work Packages are the lowest management level under Control Accounts where
budget is allocated, work is scheduled, and progress is measured.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from typing import cast as typing_cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.core.temporal_queries import is_current_version
from app.core.versioning.enums import BranchMode
from app.db.session import get_db
from app.models.domain.control_account import ControlAccount
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.work_package import WorkPackage
from app.models.schemas.cost_element import CostElementCreate, CostElementRead
from app.models.schemas.schedule_baseline import (
    ScheduleBaselineCreate,
    ScheduleBaselineRead,
    ScheduleBaselineUpdate,
)
from app.models.schemas.work_package import (
    WorkPackageCreate,
    WorkPackagePublic,
    WorkPackageUpdate,
)
from app.services.cost_element_service import CostElementService
from app.services.evm_service import EVMService
from app.services.forecast_service import ForecastService
from app.services.schedule_baseline_service import ScheduleBaselineService
from app.services.work_package_service import WorkPackageService

router = APIRouter()


def get_work_package_service(
    session: AsyncSession = Depends(get_db),
) -> WorkPackageService:
    return WorkPackageService(session)


def get_cost_element_service(
    session: AsyncSession = Depends(get_db),
) -> CostElementService:
    return CostElementService(session)


def get_schedule_baseline_service(
    session: AsyncSession = Depends(get_db),
) -> ScheduleBaselineService:
    return ScheduleBaselineService(session)


def get_forecast_service(
    session: AsyncSession = Depends(get_db),
) -> ForecastService:
    return ForecastService(session)


def get_evm_service(
    session: AsyncSession = Depends(get_db),
) -> EVMService:
    return EVMService(session)


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=None,
    operation_id="get_work_packages",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def read_work_packages(
    control_account_id: UUID | None = Query(
        None, description="Filter by Control Account root ID"
    ),
    status_filter: str | None = Query(
        None,
        alias="status",
        pattern="^(open|closed)$",
        description="Filter by status",
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch name"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGED,
        description="Branch mode: merged or isolated",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get work packages as of this timestamp (ISO 8601)",
    ),
    service: WorkPackageService = Depends(get_work_package_service),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve work packages with filtering and pagination.

    Work Packages are branchable (support change orders) and versionable.
    """
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.work_package import WorkPackagePublic

    if as_of is None:
        as_of = datetime.now(tz=UTC)

    skip = (page - 1) * per_page

    legacy_filters: dict[str, Any] = {}
    if control_account_id:
        legacy_filters["control_account_id"] = control_account_id
    if status_filter:
        legacy_filters["status"] = status_filter

    try:
        items, total = await service.get_work_packages(
            control_account_id=control_account_id,
            status=status_filter,
            branch=branch,
            branch_mode=branch_mode,
            skip=skip,
            limit=per_page,
            as_of=as_of,
        )

        # Batch-fetch ControlAccount names for enrichment
        ca_ids = {i.control_account_id for i in items if i.control_account_id}
        ca_lookup: dict[UUID, str] = {}
        if ca_ids:
            ca_result = await session.execute(
                select(
                    ControlAccount.control_account_id,
                    ControlAccount.name,
                ).where(
                    ControlAccount.control_account_id.in_(ca_ids),
                    is_current_version(
                        typing_cast(Any, ControlAccount).valid_time,
                        typing_cast(Any, ControlAccount).deleted_at,
                    ),
                )
            )
            ca_lookup = {row.control_account_id: row.name for row in ca_result.all()}

        items_out = []
        for i in items:
            read = WorkPackagePublic.model_validate(i)
            ca_name = ca_lookup.get(i.control_account_id)
            if ca_name:
                read.control_account_name = ca_name
            items_out.append(read)

        response = PaginatedResponse[WorkPackagePublic](
            items=items_out,
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
    response_model=WorkPackagePublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_work_package",
    dependencies=[Depends(RoleChecker(required_permission="work-package-create"))],
)
async def create_work_package(
    wp_in: WorkPackageCreate,
    current_user: UserIdentity = Depends(get_current_user),
    service: WorkPackageService = Depends(get_work_package_service),
) -> WorkPackage:
    """Create a new work package under a control account. Requires create permission."""
    try:
        return await service.create_work_package(
            data=wp_in, actor_id=current_user.user_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Specific routes BEFORE generic /{work_package_id} routes


@router.get(
    "/{work_package_id}",
    response_model=WorkPackagePublic,
    operation_id="get_work_package",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def read_work_package(
    work_package_id: UUID,
    branch: str = Query("main", description="Branch name"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGED,
        description="Branch mode: merged or isolated",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get work package state as of this timestamp (ISO 8601)",
    ),
    service: WorkPackageService = Depends(get_work_package_service),
    session: AsyncSession = Depends(get_db),
) -> WorkPackagePublic:
    """Get a specific work package by root ID. Requires read permission.

    Supports time-travel queries via the as_of parameter.
    """
    if as_of is None:
        as_of = datetime.now(tz=UTC)

    item = await service.get_as_of(
        entity_id=work_package_id,
        as_of=as_of,
        branch=branch,
        branch_mode=branch_mode,
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work Package not found",
        )

    result = WorkPackagePublic.model_validate(item)

    # Enrich with ControlAccount name
    if item.control_account_id:
        ca_result = await session.execute(
            select(ControlAccount.name)
            .where(
                ControlAccount.control_account_id == item.control_account_id,
                is_current_version(
                    typing_cast(Any, ControlAccount).valid_time,
                    typing_cast(Any, ControlAccount).deleted_at,
                ),
            )
            .limit(1)
        )
        ca_row = ca_result.first()
        if ca_row:
            result.control_account_name = ca_row.name

    return result


@router.put(
    "/{work_package_id}",
    response_model=WorkPackagePublic,
    operation_id="update_work_package",
    dependencies=[Depends(RoleChecker(required_permission="work-package-update"))],
)
async def update_work_package(
    work_package_id: UUID,
    wp_in: WorkPackageUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: WorkPackageService = Depends(get_work_package_service),
) -> WorkPackage:
    """Update a work package. Requires update permission."""
    try:
        return await service.update_work_package(
            work_package_id=work_package_id,
            data=wp_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{work_package_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_work_package",
    dependencies=[Depends(RoleChecker(required_permission="work-package-delete"))],
)
async def delete_work_package(
    work_package_id: UUID,
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: UserIdentity = Depends(get_current_user),
    service: WorkPackageService = Depends(get_work_package_service),
) -> None:
    """Soft delete a work package. Requires delete permission."""
    try:
        await service.soft_delete(
            root_id=work_package_id,
            actor_id=current_user.user_id,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/{work_package_id}/history",
    response_model=list[WorkPackagePublic],
    operation_id="get_work_package_history",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def read_work_package_history(
    work_package_id: UUID,
    service: WorkPackageService = Depends(get_work_package_service),
    session: AsyncSession = Depends(get_db),
) -> list[WorkPackagePublic]:
    """Get version history for a work package. Requires read permission."""
    history = await service.get_history(work_package_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No history found for this Work Package",
        )

    # Enrich with ControlAccount name (same CA for all history entries)
    ca_id = history[0].control_account_id if history else None
    ca_name: str | None = None
    if ca_id:
        ca_result = await session.execute(
            select(ControlAccount.name)
            .where(
                ControlAccount.control_account_id == ca_id,
                is_current_version(
                    typing_cast(Any, ControlAccount).valid_time,
                    typing_cast(Any, ControlAccount).deleted_at,
                ),
            )
            .limit(1)
        )
        ca_row = ca_result.first()
        if ca_row:
            ca_name = ca_row.name

    items_out = []
    for entry in history:
        read = WorkPackagePublic.model_validate(entry)
        if ca_name:
            read.control_account_name = ca_name
        items_out.append(read)

    return items_out


@router.get(
    "/{work_package_id}/breadcrumb",
    operation_id="get_work_package_breadcrumb",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def read_work_package_breadcrumb(
    work_package_id: UUID,
    branch: str = Query("main", description="Branch name"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGED,
        description="Branch mode: merged or isolated",
    ),
    service: WorkPackageService = Depends(get_work_package_service),
) -> dict[str, Any]:
    """Get breadcrumb trail for a Work Package (project -> WBS -> CA -> WP).

    Requires read permission.
    """
    try:
        return await service.get_breadcrumb(
            work_package_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/{work_package_id}/budget-status",
    operation_id="get_work_package_budget_status",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def read_work_package_budget_status(
    work_package_id: UUID,
    branch: str = Query("main", description="Branch name"),
    service: WorkPackageService = Depends(get_work_package_service),
) -> dict[str, Any]:
    """Get budget vs actual status for a work package.

    Returns the allocated budget and the sum of actual costs from cost registrations.
    Requires read permission.
    """
    try:
        return await service.get_budget_status(
            work_package_id=work_package_id, branch=branch
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


# ---------------------------------------------------------------------------
# Nested: Schedule Baseline (1:1)
# ---------------------------------------------------------------------------


@router.get(
    "/{work_package_id}/schedule-baseline",
    response_model=dict,
    operation_id="get_work_package_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-read"))],
)
async def get_work_package_schedule_baseline(
    work_package_id: UUID,
    branch: str = Query("main", description="Branch to query"),
    baseline_service: ScheduleBaselineService = Depends(get_schedule_baseline_service),
) -> dict[str, Any]:
    """Get the schedule baseline for a specific work package.

    Returns 404 if no baseline exists.
    """
    baseline = await baseline_service.get_for_work_package(
        work_package_id=work_package_id,
        branch=branch,
    )

    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule baseline not found for work package {work_package_id} "
            f"in branch '{branch}'",
        )

    baseline_dict = ScheduleBaselineRead.model_validate(baseline).model_dump(
        mode="json"
    )
    return baseline_dict


@router.post(
    "/{work_package_id}/schedule-baseline",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_work_package_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-create"))],
)
async def create_work_package_schedule_baseline(
    work_package_id: UUID,
    baseline_in: ScheduleBaselineCreate,
    current_user: UserIdentity = Depends(get_current_user),
    baseline_service: ScheduleBaselineService = Depends(get_schedule_baseline_service),
) -> dict[str, Any]:
    """Create a schedule baseline for a work package.

    Each work package can have only one schedule baseline per branch.
    """
    from app.services.schedule_baseline_service import BaselineAlreadyExistsError

    branch = baseline_in.branch or "main"
    control_date = baseline_in.control_date

    try:
        baseline = await baseline_service.create_for_work_package(
            work_package_id=work_package_id,
            actor_id=current_user.user_id,
            name=baseline_in.name,
            start_date=baseline_in.start_date,
            end_date=baseline_in.end_date,
            progression_type=baseline_in.progression_type,
            description=baseline_in.description,
            branch=branch,
            control_date=control_date,
        )

        return ScheduleBaselineRead.model_validate(baseline).model_dump(mode="json")

    except BaselineAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.put(
    "/{work_package_id}/schedule-baseline/{baseline_id}",
    response_model=dict,
    operation_id="update_work_package_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-update"))],
)
async def update_work_package_schedule_baseline(
    work_package_id: UUID,
    baseline_id: UUID,
    baseline_in: ScheduleBaselineUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    baseline_service: ScheduleBaselineService = Depends(get_schedule_baseline_service),
) -> dict[str, Any]:
    """Update the schedule baseline for a work package. Creates a new version."""
    branch = baseline_in.branch or "main"

    # Verify baseline exists and belongs to this work package
    baseline = await baseline_service.get_by_id(baseline_id, branch=branch)
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule baseline {baseline_id} not found",
        )

    updated = await baseline_service.update_schedule_baseline(
        root_id=baseline_id,
        baseline_in=baseline_in,
        actor_id=current_user.user_id,
    )

    return ScheduleBaselineRead.model_validate(updated).model_dump(mode="json")


@router.delete(
    "/{work_package_id}/schedule-baseline/{baseline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_work_package_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-delete"))],
)
async def delete_work_package_schedule_baseline(
    work_package_id: UUID,
    baseline_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    branch: str = Query("main", description="Branch to delete from"),
    baseline_service: ScheduleBaselineService = Depends(get_schedule_baseline_service),
) -> None:
    """Soft delete the schedule baseline for a work package."""
    baseline = await baseline_service.get_by_id(baseline_id, branch=branch)
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule baseline {baseline_id} not found",
        )

    await baseline_service.soft_delete(
        root_id=baseline_id,
        actor_id=current_user.user_id,
        branch=branch,
        control_date=None,
    )


# ---------------------------------------------------------------------------
# Nested: Forecast (1:1)
# ---------------------------------------------------------------------------


@router.get(
    "/{work_package_id}/forecast",
    response_model=dict,
    operation_id="get_work_package_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-read"))],
)
async def get_work_package_forecast(
    work_package_id: UUID,
    branch: str = Query("main", description="Branch to query"),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get forecast state as of this timestamp (ISO 8601)",
    ),
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> dict[str, Any]:
    """Get the forecast for a specific work package.

    Returns 404 if no forecast exists.
    """
    if as_of is None:
        as_of = datetime.now(tz=UTC)

    forecast = await forecast_service.get_for_work_package(
        work_package_id=work_package_id,
        branch=branch,
    )

    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast not found for work package {work_package_id} "
            f"in branch '{branch}'",
        )

    from app.models.schemas.forecast import ForecastRead

    return ForecastRead.model_validate(forecast).model_dump(mode="json")


@router.put(
    "/{work_package_id}/forecast",
    response_model=dict,
    operation_id="update_work_package_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-update"))],
)
async def update_work_package_forecast(
    work_package_id: UUID,
    forecast_in: dict[str, Any],
    current_user: UserIdentity = Depends(get_current_user),
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> dict[str, Any]:
    """Update or create the forecast for a work package.

    If a forecast exists, updates it. If none exists, creates a new one.
    """
    from app.models.schemas.forecast import ForecastRead, ForecastUpdate

    branch = forecast_in.get("branch", "main")
    control_date = forecast_in.get("control_date")
    if control_date and isinstance(control_date, str):
        control_date = datetime.fromisoformat(control_date.replace("Z", "+00:00"))

    update_schema = ForecastUpdate(
        eac_amount=forecast_in.get("eac_amount"),
        basis_of_estimate=forecast_in.get("basis_of_estimate"),
        branch=branch,
        control_date=control_date,
    )

    existing = await forecast_service.get_for_work_package(
        work_package_id=work_package_id,
        branch=branch,
    )

    if existing:
        updated = await forecast_service.update_forecast(
            forecast_id=existing.forecast_id,
            forecast_in=update_schema,
            actor_id=current_user.user_id,
        )
    else:
        from app.services.forecast_service import ForecastAlreadyExistsError

        try:
            updated = await forecast_service.create_for_work_package(
                work_package_id=work_package_id,
                actor_id=current_user.user_id,
                branch=branch,
                control_date=control_date,
                eac_amount=forecast_in.get("eac_amount", Decimal("0")),
                basis_of_estimate=forecast_in.get(
                    "basis_of_estimate", "Initial forecast"
                ),
            )
        except ForecastAlreadyExistsError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

    return ForecastRead.model_validate(updated).model_dump(mode="json")


@router.delete(
    "/{work_package_id}/forecast",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_work_package_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-delete"))],
)
async def delete_work_package_forecast(
    work_package_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    branch: str = Query("main", description="Branch to delete from"),
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> None:
    """Delete the forecast for a work package."""
    forecast = await forecast_service.get_for_work_package(
        work_package_id=work_package_id,
        branch=branch,
    )

    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast not found for work package {work_package_id} "
            f"in branch '{branch}'",
        )

    await forecast_service.soft_delete(
        forecast_id=forecast.forecast_id,
        actor_id=current_user.user_id,
        branch=branch,
        control_date=None,
    )


# ---------------------------------------------------------------------------
# Nested: EVM Metrics
# ---------------------------------------------------------------------------


@router.get(
    "/{work_package_id}/evm",
    response_model=None,
    operation_id="get_work_package_evm",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def read_work_package_evm(
    work_package_id: UUID,
    control_date: datetime | None = Query(
        None,
        description="Control date for time-travel query (ISO 8601, defaults to now)",
    ),
    branch: str = Query("main", description="Branch to query"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGED,
        description="Branch mode: ISOLATED or MERGE",
    ),
    service: EVMService = Depends(get_evm_service),
) -> dict[str, Any]:
    """Calculate EVM metrics for a work package.

    Returns comprehensive EVM analysis including BAC, PV, AC, EV, CV, SV, CPI, SPI.
    Metrics respect time-travel and branch isolation.
    """
    if control_date is None:
        control_date = datetime.now(tz=UTC)

    try:
        metrics = await service.calculate_evm_metrics(
            work_package_id=work_package_id,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )
        return metrics  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


# ---------------------------------------------------------------------------
# Nested: Cost Elements (EOC)
# ---------------------------------------------------------------------------


@router.get(
    "/{work_package_id}/cost-elements",
    response_model=list[CostElementRead],
    operation_id="get_work_package_cost_elements",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def read_work_package_cost_elements(
    work_package_id: UUID,
    ce_service: CostElementService = Depends(get_cost_element_service),
    session: AsyncSession = Depends(get_db),
) -> list[CostElementRead]:
    """List all cost elements (EOCs) under this work package.

    Requires cost-element-read permission.
    """
    items, _total = await ce_service.get_cost_elements(work_package_id=work_package_id)

    # Batch-fetch CostElementType names for enrichment
    type_ids = {i.cost_element_type_id for i in items if i.cost_element_type_id}
    type_lookup: dict[UUID, tuple[str, str]] = {}
    if type_ids:
        result = await session.execute(
            select(
                CostElementType.cost_element_type_id,
                CostElementType.code,
                CostElementType.name,
            ).where(
                CostElementType.cost_element_type_id.in_(type_ids),
                is_current_version(
                    typing_cast(Any, CostElementType).valid_time,
                    typing_cast(Any, CostElementType).deleted_at,
                ),
            )
        )
        type_lookup = {
            row.cost_element_type_id: (row.code, row.name) for row in result.all()
        }

    items_out = []
    for i in items:
        read = CostElementRead.model_validate(i)
        type_data = type_lookup.get(i.cost_element_type_id)
        if type_data:
            read.cost_element_type_code = type_data[0]
            read.cost_element_type_name = type_data[1]
        items_out.append(read)

    return items_out


@router.post(
    "/{work_package_id}/cost-elements",
    response_model=CostElementRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_work_package_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-create"))],
)
async def create_work_package_cost_element(
    work_package_id: UUID,
    ce_in: CostElementCreate,
    current_user: UserIdentity = Depends(get_current_user),
    ce_service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Create a new cost element (EOC) under this work package.

    Requires cost-element-create permission.
    """
    # Ensure the work_package_id from URL matches the schema
    ce_in.work_package_id = work_package_id
    try:
        return await ce_service.create_cost_element(
            element_in=ce_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
