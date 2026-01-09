from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.department import Department
from app.models.domain.user import User
from app.models.schemas.department import (
    DepartmentCreate,
    DepartmentPublic,
    DepartmentUpdate,
)
from app.services.department import DepartmentService

router = APIRouter()


def get_department_service(
    session: AsyncSession = Depends(get_db),
) -> DepartmentService:
    return DepartmentService(session)


@router.get(
    "",
    response_model=None,  # Will be PaginatedResponse[DepartmentPublic]
    operation_id="get_departments",
    dependencies=[Depends(RoleChecker(required_permission="department-read"))],
)
async def read_departments(
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
    service: DepartmentService = Depends(get_department_service),
) -> dict[str, Any]:
    """Retrieve departments with server-side features. Requires read permission."""
    from app.models.schemas.common import PaginatedResponse

    skip = (page - 1) * per_page

    items, total = await service.get_departments(
        skip=skip,
        limit=per_page,
        search=search,
        filter_string=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )

    items_out = [DepartmentPublic.model_validate(i) for i in items]

    return PaginatedResponse[DepartmentPublic](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    ).model_dump()


@router.post(
    "",
    response_model=DepartmentPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_department",
    dependencies=[Depends(RoleChecker(required_permission="department-create"))],
)
async def create_department(
    dept_in: DepartmentCreate,
    current_user: User = Depends(get_current_active_user),
    service: DepartmentService = Depends(get_department_service),
) -> Department:
    """Create a new department. Admin only."""
    try:
        dept = await service.create_department(
            dept_in=dept_in, actor_id=current_user.user_id
        )
        return dept
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{department_id}",
    response_model=DepartmentPublic,
    operation_id="get_department",
    dependencies=[Depends(RoleChecker(required_permission="department-read"))],
)
async def read_department(
    department_id: UUID,
    service: DepartmentService = Depends(get_department_service),
) -> Department:
    """Get a specific department by id. Requires read permission."""
    dept = await service.get_department(department_id)
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )
    return dept


@router.put(
    "/{department_id}",
    response_model=DepartmentPublic,
    operation_id="update_department",
    dependencies=[Depends(RoleChecker(required_permission="department-update"))],
)
async def update_department(
    department_id: UUID,
    dept_in: DepartmentUpdate,
    current_user: User = Depends(get_current_active_user),
    service: DepartmentService = Depends(get_department_service),
) -> Department:
    """Update a department. Admin only."""
    try:
        updated_dept = await service.update_department(
            department_id=department_id,
            dept_in=dept_in,
            actor_id=current_user.user_id,
        )
        return updated_dept
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_department",
    dependencies=[Depends(RoleChecker(required_permission="department-delete"))],
)
async def delete_department(
    department_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: DepartmentService = Depends(get_department_service),
) -> None:
    """Soft delete a department. Admin only."""
    try:
        await service.delete_department(
            department_id=department_id, actor_id=current_user.user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/{department_id}/history",
    response_model=list[DepartmentPublic],
    operation_id="get_department_history",
    dependencies=[Depends(RoleChecker(required_permission="department-read"))],
)
async def get_department_history(
    department_id: UUID,
    service: DepartmentService = Depends(get_department_service),
) -> Sequence[Department]:
    """Get version history for a department. Requires read permission."""
    return await service.get_department_history(department_id)
