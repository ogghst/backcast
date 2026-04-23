"""Admin API routes for RBAC role and permission management.

All endpoints require the ``admin`` role.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker
from app.core.config import settings
from app.db.session import get_db
from app.models.schemas.rbac import (
    RBACProviderStatus,
    RBACRoleCreate,
    RBACRoleRead,
    RBACRoleUpdate,
)
from app.services.rbac_admin_service import RBACAdminService

router = APIRouter()

_admin_guard = Depends(RoleChecker(allowed_roles=["admin"]))


def _get_service(session: AsyncSession = Depends(get_db)) -> RBACAdminService:
    return RBACAdminService(session)


@router.get(
    "/roles",
    response_model=list[RBACRoleRead],
    dependencies=[_admin_guard],
    operation_id="list_rbac_roles",
)
async def list_roles(
    service: RBACAdminService = Depends(_get_service),
) -> list[RBACRoleRead]:
    """List all RBAC roles with their permissions."""
    roles = await service.list_roles()
    return [RBACRoleRead.model_validate(r) for r in roles]


@router.post(
    "/roles",
    response_model=RBACRoleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_guard],
    operation_id="create_rbac_role",
)
async def create_role(
    role_in: RBACRoleCreate,
    service: RBACAdminService = Depends(_get_service),
) -> RBACRoleRead:
    """Create a new RBAC role with permissions."""
    try:
        role = await service.create_role(
            name=role_in.name,
            description=role_in.description,
            permissions=role_in.permissions,
        )
        await service.session.commit()
        return RBACRoleRead.model_validate(role)
    except Exception as e:
        await service.session.rollback()
        msg = str(e).lower()
        if "unique" in msg or "duplicate" in msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_in.name}' already exists",
            ) from e
        raise


@router.get(
    "/roles/{role_id}",
    response_model=RBACRoleRead,
    dependencies=[_admin_guard],
    operation_id="get_rbac_role",
)
async def get_role(
    role_id: UUID,
    service: RBACAdminService = Depends(_get_service),
) -> RBACRoleRead:
    """Get a single RBAC role by ID."""
    role = await service.get_role(role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )
    return RBACRoleRead.model_validate(role)


@router.put(
    "/roles/{role_id}",
    response_model=RBACRoleRead,
    dependencies=[_admin_guard],
    operation_id="update_rbac_role",
)
async def update_role(
    role_id: UUID,
    role_in: RBACRoleUpdate,
    service: RBACAdminService = Depends(_get_service),
) -> RBACRoleRead:
    """Update an existing RBAC role."""
    try:
        role = await service.update_role(
            role_id=role_id,
            name=role_in.name,
            description=role_in.description,
            permissions=role_in.permissions,
        )
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found",
            )
        await service.session.commit()
        return RBACRoleRead.model_validate(role)
    except HTTPException:
        raise
    except Exception:
        await service.session.rollback()
        raise


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_guard],
    operation_id="delete_rbac_role",
)
async def delete_role(
    role_id: UUID,
    service: RBACAdminService = Depends(_get_service),
) -> None:
    """Delete a non-system RBAC role."""
    try:
        deleted = await service.delete_role(role_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found",
            )
        await service.session.commit()
    except ValueError as e:
        await service.session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception:
        await service.session.rollback()
        raise


@router.get(
    "/permissions",
    response_model=list[str],
    dependencies=[_admin_guard],
    operation_id="list_rbac_permissions",
)
async def list_permissions(
    service: RBACAdminService = Depends(_get_service),
) -> list[str]:
    """List all distinct permission strings across all roles."""
    return await service.get_all_permissions()


@router.get(
    "/provider-status",
    response_model=RBACProviderStatus,
    dependencies=[_admin_guard],
    operation_id="get_rbac_provider_status",
)
async def get_provider_status() -> RBACProviderStatus:
    """Return the current RBAC provider and whether it is editable."""
    return RBACProviderStatus(
        provider=settings.RBAC_PROVIDER,
        editable=settings.RBAC_PROVIDER == "database",
    )
