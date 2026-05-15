"""API routes for UserRoleAssignment CRUD management.

All endpoints require admin role for write operations.
Read endpoints allow admin and manager roles.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker
from app.core.rbac_unified import (
    get_unified_rbac_service,
    set_unified_rbac_session,
)
from app.db.session import get_db
from app.models.domain.rbac import RBACRole
from app.models.domain.user import User
from app.models.domain.user_role_assignment import UserRoleAssignment
from app.models.schemas.user_role_assignment import (
    UserRoleAssignmentCreate,
    UserRoleAssignmentRead,
    UserRoleAssignmentResponse,
    UserRoleAssignmentUpdate,
)

router = APIRouter()

_admin_guard = Depends(RoleChecker(allowed_roles=["admin"]))


@router.post(
    "/",
    response_model=UserRoleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_guard],
    operation_id="create_role_assignment",
)
async def create_assignment(
    assignment_in: UserRoleAssignmentCreate,
    session: AsyncSession = Depends(get_db),
) -> UserRoleAssignmentResponse:
    """Create a new role assignment."""
    set_unified_rbac_session(session)
    try:
        service = get_unified_rbac_service()
        assignment = await service.assign_role(
            user_id=assignment_in.user_id,
            role_id=assignment_in.role_id,
            scope_type=assignment_in.scope_type.value,
            scope_id=assignment_in.scope_id,
            metadata=assignment_in.metadata_,
            granted_by=assignment_in.granted_by,
            expires_at=assignment_in.expires_at,
        )
        await session.commit()
        return UserRoleAssignmentResponse.model_validate(assignment)
    except ValueError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except Exception:
        await session.rollback()
        raise


@router.get(
    "/",
    response_model=list[UserRoleAssignmentRead],
    dependencies=[Depends(RoleChecker(allowed_roles=["admin"]))],
    operation_id="list_role_assignments",
)
async def list_assignments(
    user_id: UUID | None = Query(None, alias="userId"),
    role_id: UUID | None = Query(None, alias="roleId"),
    scope_type: str | None = Query(None, alias="scopeType"),
    scope_id: UUID | None = Query(None, alias="scopeId"),
    session: AsyncSession = Depends(get_db),
) -> list[UserRoleAssignmentRead]:
    """List role assignments with optional filters."""
    set_unified_rbac_session(session)
    try:
        service = get_unified_rbac_service()

        if user_id is not None:
            assignments = await service.get_all_user_assignments(user_id)
        elif role_id is not None:
            result = await session.execute(
                select(UserRoleAssignment)
                .where(UserRoleAssignment.role_id == role_id)
                .limit(100)
            )
            assignments = list(result.scalars().all())
        elif scope_type is not None:
            assignments = await service.get_assignments_by_scope(scope_type, scope_id)
        else:
            # Return all assignments
            result = await session.execute(select(UserRoleAssignment).limit(100))
            assignments = list(result.scalars().all())

        # Enrich with role names (batch query to avoid N+1)
        role_name_map: dict[UUID, str] = {}
        user_name_map: dict[UUID, str] = {}
        granted_by_name_map: dict[UUID, str] = {}

        if assignments:
            # Batch query role names
            role_ids = {a.role_id for a in assignments}
            role_result = await session.execute(
                select(RBACRole.id, RBACRole.name).where(RBACRole.id.in_(role_ids))
            )
            for row in role_result.all():
                role_name_map[row[0]] = row[1]

            # Batch query user names
            user_ids = {a.user_id for a in assignments}
            user_result = await session.execute(
                select(User.user_id, User.full_name).where(User.user_id.in_(user_ids))
            )
            for row in user_result.all():
                user_name_map[row[0]] = row[1]

            # Batch query granted_by names
            granted_by_ids = {
                a.granted_by for a in assignments if a.granted_by is not None
            }
            if granted_by_ids:
                granted_by_result = await session.execute(
                    select(User.user_id, User.full_name).where(
                        User.user_id.in_(granted_by_ids)
                    )
                )
                for row in granted_by_result.all():
                    granted_by_name_map[row[0]] = row[1]

        response = []
        for a in assignments:
            read = UserRoleAssignmentRead.model_validate(a)
            read.role_name = role_name_map.get(a.role_id)
            read.user_name = user_name_map.get(a.user_id)
            read.granted_by_name = (
                granted_by_name_map.get(a.granted_by) if a.granted_by else None
            )
            response.append(read)

        return response
    finally:
        set_unified_rbac_session(None)


@router.get(
    "/{assignment_id}",
    response_model=UserRoleAssignmentRead,
    dependencies=[Depends(RoleChecker(allowed_roles=["admin"]))],
    operation_id="get_role_assignment",
)
async def get_assignment(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> UserRoleAssignmentRead:
    """Get a single role assignment by ID."""
    result = await session.execute(
        select(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    read = UserRoleAssignmentRead.model_validate(assignment)

    # Enrich with role name
    role_result = await session.execute(
        select(RBACRole.name).where(RBACRole.id == assignment.role_id)
    )
    read.role_name = role_result.scalar_one_or_none()

    # Enrich with user name
    user_result = await session.execute(
        select(User.full_name).where(User.user_id == assignment.user_id)
    )
    read.user_name = user_result.scalar_one_or_none()

    # Enrich with granted_by name
    if assignment.granted_by is not None:
        granted_by_result = await session.execute(
            select(User.full_name).where(User.user_id == assignment.granted_by)
        )
        read.granted_by_name = granted_by_result.scalar_one_or_none()

    return read


@router.put(
    "/{assignment_id}",
    response_model=UserRoleAssignmentResponse,
    dependencies=[_admin_guard],
    operation_id="update_role_assignment",
)
async def update_assignment(
    assignment_id: UUID,
    assignment_in: UserRoleAssignmentUpdate,
    session: AsyncSession = Depends(get_db),
) -> UserRoleAssignmentResponse:
    """Update an existing role assignment."""
    set_unified_rbac_session(session)
    try:
        service = get_unified_rbac_service()
        assignment = await service.update_assignment(
            assignment_id=assignment_id,
            role_id=assignment_in.role_id,
            metadata=assignment_in.metadata_,
            expires_at=assignment_in.expires_at,
        )

        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role assignment not found",
            )

        await session.commit()
        await session.refresh(assignment)
        return UserRoleAssignmentResponse.model_validate(assignment)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.delete(
    "/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_guard],
    operation_id="delete_role_assignment",
)
async def delete_assignment(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a role assignment by ID."""
    set_unified_rbac_session(session)
    try:
        service = get_unified_rbac_service()

        # First get the assignment to find user_id, scope_type, scope_id
        result = await session.execute(
            select(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()

        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role assignment not found",
            )

        # Use service.revoke_role() to ensure cache invalidation
        deleted = await service.revoke_role(
            user_id=assignment.user_id,
            scope_type=assignment.scope_type,
            scope_id=assignment.scope_id,
            role_id=assignment.role_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role assignment not found",
            )

        await session.commit()
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise
    finally:
        set_unified_rbac_session(None)
