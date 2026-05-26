"""Work Package API routes - CRUD for project-scoped cost grouping."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.db.session import get_db
from app.models.domain.work_package import WorkPackage
from app.models.schemas.common import PaginatedResponse
from app.models.schemas.work_package import (
    COQMetrics,
    COQTrendGranularity,
    COQTrendResponse,
    QualityCostAllocation,
    QualityCostAllocationRead,
    WorkPackageCreate,
    WorkPackageRead,
    WorkPackageSummary,
    WorkPackageUpdate,
)
from app.services.work_package_service import WorkPackageService

router = APIRouter()


def get_work_package_service(
    session: AsyncSession = Depends(get_db),
) -> WorkPackageService:
    """Dependency to get WorkPackageService instance."""
    return WorkPackageService(session)


@router.get(
    "",
    response_model=None,  # PaginatedResponse[WorkPackageRead]
    operation_id="get_work_packages",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def read_work_packages(
    project_id: UUID = Query(..., description="Required project ID filter"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    coq_category: str | None = Query(
        None,
        pattern="^(prevention|appraisal|internal_failure|external_failure)$",
        description="Filter by COQ category",
    ),
    package_type_id: UUID | None = Query(
        None,
        description="Filter by package type root ID",
    ),
    quality_only: bool = Query(
        False,
        description="When true, only return quality-flagged package types",
    ),
    status: str | None = Query(
        None,
        pattern="^(open|closed)$",
        description="Filter by status",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get packages as of this timestamp (ISO 8601)",
    ),
    service: WorkPackageService = Depends(get_work_package_service),
) -> dict[str, Any]:
    """Retrieve work packages for a project with pagination and filtering.

    Work packages are versionable but NOT branchable (costs are global facts).
    """
    skip = (page - 1) * per_page

    items, total = await service.get_work_packages(
        project_id=project_id,
        skip=skip,
        limit=per_page,
        coq_category=coq_category,
        package_type_id=package_type_id,
        quality_only=quality_only,
        status=status,
        as_of=as_of,
    )

    items_out = []
    for i in items:
        read = WorkPackageRead.model_validate(i)
        read.actual_cost = await service.compute_actual_cost(i.work_package_id)
        items_out.append(read)

    response = PaginatedResponse[WorkPackageRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    )
    return response.model_dump()


@router.post(
    "",
    response_model=WorkPackageRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_work_package",
    dependencies=[Depends(RoleChecker(required_permission="work-package-create"))],
)
async def create_work_package(
    wp_in: WorkPackageCreate,
    current_user: UserIdentity = Depends(get_current_user),
    service: WorkPackageService = Depends(get_work_package_service),
) -> WorkPackage:
    """Create a new work package.

    Tracks the cost and schedule impact of an external event on a project.
    Optionally includes cost allocations to specific cost elements.
    """
    try:
        return await service.create_work_package(
            data=wp_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Specific routes must be defined BEFORE the generic /{work_package_id} route


@router.get(
    "/project/{project_id}/summary",
    response_model=WorkPackageSummary,
    operation_id="get_work_package_summary",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def get_work_package_summary(
    project_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get summary as of this timestamp (ISO 8601)",
    ),
    service: WorkPackageService = Depends(get_work_package_service),
) -> WorkPackageSummary:
    """Get aggregated COQ summary for a project.

    Returns total cost, conformance/nonconformance breakdown,
    total schedule impact days, and COQ ratio against project budget.
    Only includes quality-flagged types work packages.
    """
    try:
        return await service.get_summary(project_id=project_id, as_of=as_of)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/project/{project_id}/coq-metrics",
    response_model=COQMetrics,
    operation_id="get_coq_metrics",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def get_coq_metrics(
    project_id: UUID,
    as_of: datetime | None = Query(None, description="Time travel query"),
    service: WorkPackageService = Depends(get_work_package_service),
) -> COQMetrics:
    """Get COQ metrics for a project.

    Returns Cost of Quality metrics including CPQ, CPIq, QPI, and COQ ratio
    complementing standard EVM indicators.
    Only includes quality-flagged types work packages.
    """
    return await service.get_coq_metrics(project_id=project_id, as_of=as_of)


@router.get(
    "/project/{project_id}/coq-trend",
    response_model=COQTrendResponse,
    operation_id="get_coq_trend",
    summary="Get COQ trend time-series",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def get_coq_trend(
    project_id: UUID,
    granularity: COQTrendGranularity = Query(
        COQTrendGranularity.MONTH, description="Time granularity"
    ),
    as_of: datetime | None = Query(
        None, description="Point-in-time for historical query"
    ),
    service: WorkPackageService = Depends(get_work_package_service),
) -> COQTrendResponse:
    """Get COQ trend time-series for a project.

    Returns Cost of Quality costs aggregated into time buckets (week or month),
    broken down by the four COQ categories: prevention, appraisal,
    internal_failure, external_failure.
    Only includes quality-flagged types work packages.
    """
    return await service.get_coq_trend(project_id, granularity, as_of)


# Generic routes with path parameters


@router.get(
    "/{work_package_id}",
    response_model=WorkPackageRead,
    operation_id="get_work_package",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def read_work_package(
    work_package_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get package state as of this timestamp (ISO 8601)",
    ),
    service: WorkPackageService = Depends(get_work_package_service),
) -> WorkPackage:
    """Get a specific work package by root ID.

    Supports time-travel queries via the as_of parameter.
    """
    if as_of is not None:
        item = await service.get_as_of_with_relations(
            entity_id=work_package_id,
            as_of=as_of,
        )
    else:
        item = await service.get_by_id(work_package_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work Package not found",
        )
    return item


@router.put(
    "/{work_package_id}",
    response_model=WorkPackageRead,
    operation_id="update_work_package",
    dependencies=[Depends(RoleChecker(required_permission="work-package-update"))],
)
async def update_work_package(
    work_package_id: UUID,
    wp_in: WorkPackageUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: WorkPackageService = Depends(get_work_package_service),
) -> WorkPackage:
    """Update a work package.

    Creates a new version with updated values. Previous versions are
    preserved in the history. Cost allocations are replaced if provided.
    """
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
    """Soft delete a work package.

    Marks the work package as deleted but preserves it in the history.
    """
    item = await service.get_by_id(work_package_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work Package not found",
        )

    await service.soft_delete(
        work_package_id=work_package_id,
        actor_id=current_user.user_id,
        control_date=control_date,
    )


@router.get(
    "/{work_package_id}/history",
    response_model=list[WorkPackageRead],
    operation_id="get_work_package_history",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def get_work_package_history(
    work_package_id: UUID,
    service: WorkPackageService = Depends(get_work_package_service),
) -> list[WorkPackage]:
    """Get full version history for a work package.

    Returns all versions ordered by transaction time (newest first).
    """
    return await service.get_history(work_package_id)


@router.get(
    "/{work_package_id}/allocations",
    response_model=list[QualityCostAllocationRead],
    operation_id="get_work_package_allocations",
    dependencies=[Depends(RoleChecker(required_permission="work-package-read"))],
)
async def get_work_package_allocations(
    work_package_id: UUID,
    service: WorkPackageService = Depends(get_work_package_service),
) -> list[QualityCostAllocationRead]:
    """Get cost allocation entries for a work package.

    Returns CostRegistration entries linked to this work package,
    with cost element and WBE names for display.
    """
    return await service.get_allocations(work_package_id)


@router.put(
    "/{work_package_id}/allocations",
    response_model=list[QualityCostAllocationRead],
    operation_id="upsert_work_package_allocations",
    dependencies=[Depends(RoleChecker(required_permission="work-package-update"))],
)
async def upsert_work_package_allocations(
    work_package_id: UUID,
    allocations_in: list[QualityCostAllocation],
    current_user: UserIdentity = Depends(get_current_user),
    service: WorkPackageService = Depends(get_work_package_service),
) -> list[QualityCostAllocationRead]:
    """Replace all cost allocations for a work package.

    Soft-deletes existing linked CostRegistration entries and creates new ones.
    """
    return await service.upsert_allocations(
        work_package_id=work_package_id,
        allocations_data=allocations_in,
        actor_id=current_user.user_id,
    )
