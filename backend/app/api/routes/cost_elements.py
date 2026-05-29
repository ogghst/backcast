"""Cost Element (EOC) API routes - standalone endpoints.

Cost Elements are the leaf level of the budget hierarchy (Element of Cost).
Versionable but NOT branchable (financial facts are global).
"""

from datetime import UTC, datetime
from typing import Any
from typing import cast as typing_cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.core.temporal_queries import is_current_version
from app.db.session import get_db
from app.models.domain.control_account import ControlAccount
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.wbs_element import WBSElement
from app.models.domain.work_package import WorkPackage
from app.models.schemas.cost_element import (
    CostElementRead,
    CostElementUpdate,
)
from app.services.cost_element_service import CostElementService

router = APIRouter()


def get_cost_element_service(
    session: AsyncSession = Depends(get_db),
) -> CostElementService:
    return CostElementService(session)


@router.get(
    "",
    response_model=None,
    operation_id="get_cost_elements",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def read_cost_elements(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    work_package_id: UUID | None = Query(
        None, description="Filter by Work Package root ID"
    ),
    cost_element_type_id: UUID | None = Query(
        None, description="Filter by Cost Element Type ID"
    ),
    search: str | None = Query(None, description="Search term"),
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
        description="Time travel: get Cost Elements as of this timestamp (ISO 8601)",
    ),
    service: CostElementService = Depends(get_cost_element_service),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve cost elements (EOCs) with server-side search, filtering, and sorting.

    Cost Elements are versionable but NOT branchable.
    """
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.cost_element import CostElementRead

    if as_of is None:
        as_of = datetime.now(tz=UTC)

    legacy_filters: dict[str, Any] = {}
    if work_package_id:
        legacy_filters["work_package_id"] = work_package_id
    if cost_element_type_id:
        legacy_filters["cost_element_type_id"] = cost_element_type_id

    skip = (page - 1) * per_page

    items, total = await service.get_cost_elements(
        work_package_id=work_package_id,
        cost_element_type_id=cost_element_type_id,
        skip=skip,
        limit=per_page,
        as_of=as_of,
    )

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

    # Batch-resolve project_id through: work_package -> control_account -> wbs_element
    wp_ids = {i.work_package_id for i in items if i.work_package_id}
    project_lookup: dict[UUID, UUID] = {}
    if wp_ids:
        project_result = await session.execute(
            select(
                WorkPackage.work_package_id,
                WBSElement.project_id,
            )
            .join(
                ControlAccount,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                WBSElement, ControlAccount.wbs_element_id == WBSElement.wbs_element_id
            )
            .where(WorkPackage.work_package_id.in_(wp_ids))
        )
        project_lookup = {
            row.work_package_id: row.project_id for row in project_result.all()
        }

    items_out = []
    for i in items:
        read = CostElementRead.model_validate(i)
        type_data = type_lookup.get(i.cost_element_type_id)
        if type_data:
            read.cost_element_type_code = type_data[0]
            read.cost_element_type_name = type_data[1]
        pid = project_lookup.get(i.work_package_id)
        if pid:
            read.project_id = pid
        items_out.append(read)

    response = PaginatedResponse[CostElementRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    )

    return response.model_dump()


@router.get(
    "/{cost_element_id}",
    response_model=CostElementRead,
    operation_id="get_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def read_cost_element(
    cost_element_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get cost element state as of this timestamp (ISO 8601)",
    ),
    service: CostElementService = Depends(get_cost_element_service),
    session: AsyncSession = Depends(get_db),
) -> CostElementRead:
    """Get a specific cost element by root ID. Requires read permission.

    Supports time-travel queries via the as_of parameter.
    """
    from app.models.schemas.cost_element import CostElementRead

    if as_of is None:
        as_of = datetime.now(tz=UTC)

    item = await service.get_as_of(entity_id=cost_element_id, as_of=as_of)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost Element not found" + (f" as of {as_of}" if as_of else ""),
        )

    read = CostElementRead.model_validate(item)

    # Enrich with CostElementType name/code
    if item.cost_element_type_id:
        result = await session.execute(
            select(
                CostElementType.code,
                CostElementType.name,
            ).where(
                CostElementType.cost_element_type_id == item.cost_element_type_id,
                is_current_version(
                    typing_cast(Any, CostElementType).valid_time,
                    typing_cast(Any, CostElementType).deleted_at,
                ),
            )
        )
        row = result.first()
        if row:
            read.cost_element_type_code = row.code
            read.cost_element_type_name = row.name

    # Enrich with project_id through: work_package -> control_account -> wbs_element
    if item.work_package_id:
        project_result = await session.execute(
            select(WBSElement.project_id)
            .join(
                ControlAccount,
                ControlAccount.wbs_element_id == WBSElement.wbs_element_id,
            )
            .join(
                WorkPackage,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .where(WorkPackage.work_package_id == item.work_package_id)
            .limit(1)
        )
        pid = project_result.scalar_one_or_none()
        if pid:
            read.project_id = pid

    return read


@router.put(
    "/{cost_element_id}",
    response_model=CostElementRead,
    operation_id="update_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-update"))],
)
async def update_cost_element(
    cost_element_id: UUID,
    element_in: CostElementUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Update a cost element. Creates a new version. Requires update permission."""
    try:
        return await service.update_cost_element(
            cost_element_id=cost_element_id,
            element_in=element_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{cost_element_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-delete"))],
)
async def delete_cost_element(
    cost_element_id: UUID,
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: UserIdentity = Depends(get_current_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> None:
    """Soft delete a cost element. Requires delete permission."""
    try:
        item = await service.get_by_id(cost_element_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cost Element not found",
            )

        await service.soft_delete_cost_element(
            cost_element_id=cost_element_id,
            actor_id=current_user.user_id,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
