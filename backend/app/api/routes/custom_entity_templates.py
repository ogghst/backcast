from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.db.session import get_db
from app.models.domain.custom_entity_template import CustomEntityTemplate
from app.models.schemas.custom_entity_template import (
    CustomEntityTemplateCreate,
    CustomEntityTemplateRead,
    CustomEntityTemplateUpdate,
)
from app.services.custom_entity_template_service import CustomEntityTemplateService

router = APIRouter()


def get_custom_entity_template_service(
    session: AsyncSession = Depends(get_db),
) -> CustomEntityTemplateService:
    return CustomEntityTemplateService(session)


@router.get(
    "",
    response_model=None,  # Will be PaginatedResponse[CustomEntityTemplateRead]
    operation_id="get_custom_entity_templates",
    dependencies=[
        Depends(RoleChecker(required_permission="custom-entity-template-read"))
    ],
)
async def read_custom_entity_templates(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    organizational_unit_id: UUID | None = Query(
        None, description="Filter by Organizational Unit ID"
    ),
    target_entity_type: str | None = Query(
        None,
        description="Filter by target entity type "
        "(PROJECT|WBS_ELEMENT|WORK_PACKAGE|CHANGE_ORDER)",
    ),
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
    service: CustomEntityTemplateService = Depends(get_custom_entity_template_service),
) -> dict[str, Any]:
    """Retrieve custom entity templates with server-side features."""
    from app.models.schemas.common import PaginatedResponse

    server_filters: dict[str, Any] = {}
    if organizational_unit_id:
        server_filters["organizational_unit_id"] = organizational_unit_id
    if target_entity_type:
        server_filters["target_entity_type"] = target_entity_type

    skip = (page - 1) * per_page

    items, total = await service.get_custom_entity_templates(
        filters=server_filters,
        skip=skip,
        limit=per_page,
        search=search,
        filter_string=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )

    items_out = [CustomEntityTemplateRead.model_validate(i) for i in items]

    return PaginatedResponse[CustomEntityTemplateRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    ).model_dump()


@router.post(
    "",
    response_model=CustomEntityTemplateRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_custom_entity_template",
    dependencies=[
        Depends(RoleChecker(required_permission="custom-entity-template-create"))
    ],
)
async def create_custom_entity_template(
    template_in: CustomEntityTemplateCreate,
    current_user: UserIdentity = Depends(get_current_user),
    service: CustomEntityTemplateService = Depends(get_custom_entity_template_service),
) -> CustomEntityTemplate:
    """Create a new custom entity template."""
    try:
        return await service.create(type_in=template_in, actor_id=current_user.user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{custom_entity_template_id}",
    response_model=CustomEntityTemplateRead,
    operation_id="get_custom_entity_template",
    dependencies=[
        Depends(RoleChecker(required_permission="custom-entity-template-read"))
    ],
)
async def read_custom_entity_template(
    custom_entity_template_id: UUID,
    service: CustomEntityTemplateService = Depends(get_custom_entity_template_service),
) -> CustomEntityTemplate:
    """Get a specific custom entity template by id."""
    item = await service.get_by_id(custom_entity_template_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom Entity Template not found",
        )
    return item


@router.put(
    "/{custom_entity_template_id}",
    response_model=CustomEntityTemplateRead,
    operation_id="update_custom_entity_template",
    dependencies=[
        Depends(RoleChecker(required_permission="custom-entity-template-update"))
    ],
)
async def update_custom_entity_template(
    custom_entity_template_id: UUID,
    template_in: CustomEntityTemplateUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: CustomEntityTemplateService = Depends(get_custom_entity_template_service),
) -> CustomEntityTemplate:
    """Update a custom entity template."""
    try:
        item = await service.get_by_id(custom_entity_template_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom Entity Template not found",
            )

        return await service.update(
            custom_entity_template_id=custom_entity_template_id,
            type_in=template_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete(
    "/{custom_entity_template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_custom_entity_template",
    dependencies=[
        Depends(RoleChecker(required_permission="custom-entity-template-delete"))
    ],
)
async def delete_custom_entity_template(
    custom_entity_template_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    service: CustomEntityTemplateService = Depends(get_custom_entity_template_service),
) -> None:
    """Soft delete a custom entity template."""
    try:
        item = await service.get_by_id(custom_entity_template_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom Entity Template not found",
            )

        await service.soft_delete(
            custom_entity_template_id=custom_entity_template_id,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{custom_entity_template_id}/history",
    response_model=list[CustomEntityTemplateRead],
    operation_id="get_custom_entity_template_history",
    dependencies=[
        Depends(RoleChecker(required_permission="custom-entity-template-read"))
    ],
)
async def get_custom_entity_template_history(
    custom_entity_template_id: UUID,
    service: CustomEntityTemplateService = Depends(get_custom_entity_template_service),
) -> Sequence[CustomEntityTemplate]:
    """Get version history for a custom entity template."""
    return await service.get_history(custom_entity_template_id)
