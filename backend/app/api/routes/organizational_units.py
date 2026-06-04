"""Organizational Unit API routes with RBAC and EVCS support."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.core.exceptions.hierarchy import CircularReferenceError
from app.db.session import get_db
from app.models.domain.organizational_unit import OrganizationalUnit
from app.models.schemas.organizational_unit import (
    OrganizationalUnitCreate,
    OrganizationalUnitPublic,
    OrganizationalUnitUpdate,
)
from app.services.organizational_unit_service import OrganizationalUnitService

router = APIRouter()


def get_organizational_unit_service(
    session: AsyncSession = Depends(get_db),
) -> OrganizationalUnitService:
    return OrganizationalUnitService(session)


@router.get(
    "",
    response_model=None,
    operation_id="get_organizational_units",
    dependencies=[Depends(RoleChecker(required_permission="organizational-unit-read"))],
)
async def read_organizational_units(
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
    service: OrganizationalUnitService = Depends(get_organizational_unit_service),
) -> dict[str, Any]:
    """Retrieve organizational units with server-side search, filtering, and sorting.

    Requires read permission.
    """
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.organizational_unit import OrganizationalUnitPublic

    skip = (page - 1) * per_page

    items, total = await service.list_organizational_units(
        skip=skip,
        limit=per_page,
    )

    items_out = [OrganizationalUnitPublic.model_validate(i) for i in items]

    return PaginatedResponse[OrganizationalUnitPublic](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    ).model_dump()


@router.post(
    "",
    response_model=OrganizationalUnitPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_organizational_unit",
    dependencies=[
        Depends(RoleChecker(required_permission="organizational-unit-create"))
    ],
)
async def create_organizational_unit(
    unit_in: OrganizationalUnitCreate,
    current_user: UserIdentity = Depends(get_current_user),
    service: OrganizationalUnitService = Depends(get_organizational_unit_service),
) -> OrganizationalUnit:
    """Create a new organizational unit. Requires create permission."""
    try:
        return await service.create_organizational_unit(
            unit_in=unit_in, actor_id=current_user.user_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/tree",
    response_model=list[OrganizationalUnitPublic],
    operation_id="get_organizational_unit_tree",
    dependencies=[Depends(RoleChecker(required_permission="organizational-unit-read"))],
)
async def read_organizational_unit_tree(
    service: OrganizationalUnitService = Depends(get_organizational_unit_service),
) -> list[OrganizationalUnitPublic]:
    """Get the full OBS (Organizational Breakdown Structure) tree.

    Returns all organizational units as a flat list with parent references.
    Requires read permission.
    """
    from app.models.schemas.organizational_unit import OrganizationalUnitPublic

    items, _total = await service.list_organizational_units()

    # Build name lookup map
    name_map: dict[str, str] = {
        str(item.organizational_unit_id): item.name for item in items
    }

    # Convert to Pydantic models and enrich with parent_unit_name
    result = []
    for item in items:
        unit_out = OrganizationalUnitPublic.model_validate(item)
        if unit_out.parent_unit_id and str(unit_out.parent_unit_id) in name_map:
            unit_out.parent_unit_name = name_map[str(unit_out.parent_unit_id)]
        result.append(unit_out)

    return result


@router.get(
    "/{organizational_unit_id}",
    response_model=OrganizationalUnitPublic,
    operation_id="get_organizational_unit",
    dependencies=[Depends(RoleChecker(required_permission="organizational-unit-read"))],
)
async def read_organizational_unit(
    organizational_unit_id: UUID,
    service: OrganizationalUnitService = Depends(get_organizational_unit_service),
) -> OrganizationalUnitPublic:
    """Get a specific organizational unit by root ID. Requires read permission."""
    unit = await service.get_as_of(entity_id=organizational_unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organizational Unit not found",
        )
    unit_out = OrganizationalUnitPublic.model_validate(unit)
    if unit_out.parent_unit_id:
        parent = await service.get_as_of(entity_id=unit_out.parent_unit_id)
        if parent:
            unit_out.parent_unit_name = parent.name
    return unit_out


@router.put(
    "/{organizational_unit_id}",
    response_model=OrganizationalUnitPublic,
    operation_id="update_organizational_unit",
    dependencies=[
        Depends(RoleChecker(required_permission="organizational-unit-update"))
    ],
)
async def update_organizational_unit(
    organizational_unit_id: UUID,
    unit_in: OrganizationalUnitUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: OrganizationalUnitService = Depends(get_organizational_unit_service),
) -> OrganizationalUnit:
    """Update an organizational unit. Requires update permission."""
    try:
        return await service.update_organizational_unit(
            organizational_unit_id=organizational_unit_id,
            unit_in=unit_in,
            actor_id=current_user.user_id,
        )
    except CircularReferenceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete(
    "/{organizational_unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_organizational_unit",
    dependencies=[
        Depends(RoleChecker(required_permission="organizational-unit-delete"))
    ],
)
async def delete_organizational_unit(
    organizational_unit_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    service: OrganizationalUnitService = Depends(get_organizational_unit_service),
) -> None:
    """Soft delete an organizational unit. Requires delete permission."""
    try:
        await service.delete_organizational_unit(
            organizational_unit_id=organizational_unit_id,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/{organizational_unit_id}/history",
    response_model=list[OrganizationalUnitPublic],
    operation_id="get_organizational_unit_history",
    dependencies=[Depends(RoleChecker(required_permission="organizational-unit-read"))],
)
async def read_organizational_unit_history(
    organizational_unit_id: UUID,
    service: OrganizationalUnitService = Depends(get_organizational_unit_service),
) -> Sequence[OrganizationalUnit]:
    """Get version history for an organizational unit. Requires read permission."""
    history = await service.get_history(organizational_unit_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No history found for this Organizational Unit",
        )
    return history
