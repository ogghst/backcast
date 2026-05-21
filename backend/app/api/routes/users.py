from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    RoleChecker,
    UserIdentity,
    get_current_user,
    get_user_service,
)
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.preference import (
    UserPreferenceResponse,
    UserPreferenceUpdate,
)
from app.models.schemas.user import UserHistory, UserPublic, UserRegister, UserUpdate
from app.services.user import UserService

router = APIRouter()


async def _is_admin(user_id: UUID, session: AsyncSession) -> bool:
    """Check if a user has the admin role via unified RBAC."""
    from app.core.rbac_unified import (
        get_unified_rbac_service,
        set_unified_rbac_session,
    )

    try:
        set_unified_rbac_session(session)
        roles = await get_unified_rbac_service().get_user_roles(user_id, "global", None)
        return "admin" in roles
    finally:
        set_unified_rbac_session(None)


@router.get(
    "",
    response_model=list[UserPublic],
    operation_id="get_users",
    dependencies=[Depends(RoleChecker(["admin"]))],
)
async def read_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    service: UserService = Depends(get_user_service),
    session: AsyncSession = Depends(get_db),
) -> list[UserPublic]:
    """
    Retrieve users.
    Only Admins can list all users.
    """
    users = await service.get_users(skip=skip, limit=limit)
    return [await UserPublic.from_user_async(u, session) for u in users]


@router.post(
    "",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_user",
    dependencies=[Depends(RoleChecker(required_permission="user-create"))],
)
async def create_user(
    user_in: UserRegister,
    current_user: UserIdentity = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    """
    Create a new user.
    Admin only.
    """
    try:
        user = await service.create_user(user_in=user_in, actor_id=current_user.user_id)
        return await UserPublic.from_user_async(user, session)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/me/preferences",
    response_model=UserPreferenceResponse,
    operation_id="get_my_preferences",
    dependencies=[Depends(RoleChecker(required_permission="user-read"))],
)
async def get_my_preferences(
    current_user: UserIdentity = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> Any:
    """
    Get current user's preferences.
    Requires read permission.
    """
    try:
        prefs = await service.get_user_preferences(current_user.user_id)
        return UserPreferenceResponse(**prefs) if prefs else UserPreferenceResponse()
    except ValueError:
        # User not found, return default
        return UserPreferenceResponse()


@router.put(
    "/me/preferences",
    response_model=UserPreferenceResponse,
    operation_id="update_my_preferences",
    dependencies=[Depends(RoleChecker(required_permission="user-update"))],
)
async def update_my_preferences(
    pref_in: UserPreferenceUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> Any:
    """
    Update current user's preferences.
    Requires update permission.
    """
    try:
        # Use exclude_unset to only include fields that were actually provided
        updated_prefs = await service.update_user_preferences(
            current_user.user_id, pref_in.model_dump(exclude_unset=True)
        )
        return UserPreferenceResponse(**updated_prefs)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    operation_id="get_user",
    dependencies=[Depends(RoleChecker(required_permission="user-read"))],
)
async def read_user(
    user_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    """
    Get a specific user by id.
    Admin can get any user. Users can only get themselves.
    Requires read permission.
    """
    # Additional authorization: non-admins can only read themselves
    if (
        not await _is_admin(current_user.user_id, session)
        and current_user.user_id != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user",
        )

    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return await UserPublic.from_user_async(user, session)


@router.put(
    "/{user_id}",
    response_model=UserPublic,
    operation_id="update_user",
    dependencies=[Depends(RoleChecker(required_permission="user-update"))],
)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    """
    Update a user.
    Admin can update any user. Users can only update themselves.
    Requires update permission.
    """
    # Additional authorization: non-admins can only update themselves
    if (
        not await _is_admin(current_user.user_id, session)
        and current_user.user_id != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )

    try:
        updated_user = await service.update_user(
            user_id=user_id, user_in=user_in, actor_id=current_user.user_id
        )
        return await UserPublic.from_user_async(updated_user, session)
    except ValueError as e:  # Entity not found or version conflict
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_user",
    dependencies=[Depends(RoleChecker(required_permission="user-delete"))],
)
async def delete_user(
    user_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> None:
    """
    Soft delete a user.
    Admin only.
    """
    try:
        await service.delete_user(user_id=user_id, actor_id=current_user.user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{user_id}/history",
    response_model=list[UserHistory],
    operation_id="get_user_history",
    dependencies=[Depends(RoleChecker(required_permission="user-read"))],
)
async def get_user_history(
    user_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
    session: AsyncSession = Depends(get_db),
) -> Sequence[User]:
    """
    Get version history for a user.
    Admin can view any user's history. Users can only view their own.
    Requires read permission.
    """
    # Additional authorization: non-admins can only view their own history
    if (
        not await _is_admin(current_user.user_id, session)
        and current_user.user_id != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's history",
        )

    return await service.get_user_history(user_id)
