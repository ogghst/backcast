from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.db.session import get_db
from app.models.domain.package_type import PackageType
from app.models.schemas.package_type import (
    PackageTypeCreate,
    PackageTypeRead,
    PackageTypeUpdate,
)
from app.services.package_type_service import PackageTypeService

router = APIRouter()


def get_package_type_service(
    session: AsyncSession = Depends(get_db),
) -> PackageTypeService:
    return PackageTypeService(session)


@router.get(
    "",
    response_model=None,  # Will be PaginatedResponse[PackageTypeRead]
    operation_id="get_package_types",
    dependencies=[Depends(RoleChecker(required_permission="package-type-read"))],
)
async def read_package_types(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    search: str | None = Query(None, description="Search term (code, name)"),
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
    service: PackageTypeService = Depends(get_package_type_service),
) -> dict[str, Any]:
    """Retrieve package types with server-side features."""
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.package_type import PackageTypeRead

    skip = (page - 1) * per_page

    items, total = await service.get_package_types(
        skip=skip,
        limit=per_page,
        search=search,
        filter_string=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )

    items_out = [PackageTypeRead.model_validate(i) for i in items]

    return PaginatedResponse[PackageTypeRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    ).model_dump()


@router.post(
    "",
    response_model=PackageTypeRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_package_type",
    dependencies=[Depends(RoleChecker(required_permission="package-type-create"))],
)
async def create_package_type(
    type_in: PackageTypeCreate,
    current_user: UserIdentity = Depends(get_current_user),
    service: PackageTypeService = Depends(get_package_type_service),
) -> PackageType:
    """Create a new package type."""
    try:
        return await service.create(type_in=type_in, actor_id=current_user.user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{package_type_id}",
    response_model=PackageTypeRead,
    operation_id="get_package_type",
    dependencies=[Depends(RoleChecker(required_permission="package-type-read"))],
)
async def read_package_type(
    package_type_id: UUID,
    service: PackageTypeService = Depends(get_package_type_service),
) -> PackageType:
    """Get a specific package type by id."""
    item = await service.get_by_id(package_type_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package Type not found",
        )
    return item


@router.put(
    "/{package_type_id}",
    response_model=PackageTypeRead,
    operation_id="update_package_type",
    dependencies=[Depends(RoleChecker(required_permission="package-type-update"))],
)
async def update_package_type(
    package_type_id: UUID,
    type_in: PackageTypeUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: PackageTypeService = Depends(get_package_type_service),
) -> PackageType:
    """Update a package type."""
    try:
        item = await service.get_by_id(package_type_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Package Type not found",
            )

        return await service.update(
            package_type_id=package_type_id,
            type_in=type_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete(
    "/{package_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_package_type",
    dependencies=[Depends(RoleChecker(required_permission="package-type-delete"))],
)
async def delete_package_type(
    package_type_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    service: PackageTypeService = Depends(get_package_type_service),
) -> None:
    """Soft delete a package type."""
    try:
        item = await service.get_by_id(package_type_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Package Type not found",
            )

        await service.soft_delete(
            package_type_id=package_type_id, actor_id=current_user.user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{package_type_id}/history",
    response_model=list[PackageTypeRead],
    operation_id="get_package_type_history",
    dependencies=[Depends(RoleChecker(required_permission="package-type-read"))],
)
async def get_package_type_history(
    package_type_id: UUID,
    service: PackageTypeService = Depends(get_package_type_service),
) -> Sequence[PackageType]:
    """Get version history for a package type."""
    return await service.get_history(package_type_id)
