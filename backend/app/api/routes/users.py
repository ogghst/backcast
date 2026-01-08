from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.auth import (
    RoleChecker,
    get_current_active_user,
    get_user_service,
)
from app.models.domain.user import User
from app.models.schemas.preference import (
    UserPreferenceResponse,
    UserPreferenceUpdate,
)
from app.models.schemas.user import UserHistory, UserPublic, UserRegister, UserUpdate
from app.services.user import UserService

router = APIRouter()


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
) -> Sequence[User]:
    """
    Retrieve users.
    Only Admins can list all users.
    """
    return await service.get_users(skip=skip, limit=limit)


@router.post(
    "",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_user",
    dependencies=[Depends(RoleChecker(required_permission="user-create"))],
)
async def create_user(
    user_in: UserRegister,
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
) -> User:
    """
    Create a new user.
    Admin only.
    """
    try:
        # Pass Pydantic model directly to service
        # Service handles hashing and dictionary conversion
        user = await service.create_user(user_in=user_in, actor_id=current_user.user_id)
        return user
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
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
) -> Any:
    """
    Get current user's preferences.
    Requires read permission.
    """
    try:
        prefs = await service.get_user_preferences(current_user.id)
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
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
) -> Any:
    """
    Update current user's preferences.
    Requires update permission.
    """
    try:
        # Use exclude_unset to only include fields that were actually provided
        updated_prefs = await service.update_user_preferences(
            current_user.id, pref_in.model_dump(exclude_unset=True)
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
    user_id: UUID,  # This fetches by version ID (PK)
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
) -> User:
    """
    Get a specific user by id.
    Admin can get any user. Users can only get themselves.
    Requires read permission.
    """
    # Additional authorization: non-admins can only read themselves
    if current_user.role != "admin" and current_user.id != user_id:
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
    return user


@router.put(
    "/{user_id}",
    response_model=UserPublic,
    operation_id="update_user",
    dependencies=[Depends(RoleChecker(required_permission="user-update"))],
)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
) -> User:
    """
    Update a user.
    Admin can update any user. Users can only update themselves.
    Requires update permission.
    """
    # Additional authorization: non-admins can only update themselves
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )

    try:
        updated_user = await service.update_user(
            user_id=user_id, user_in=user_in, actor_id=current_user.user_id
        )
        return updated_user
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
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
) -> Sequence[User]:
    """
    Get version history for a user.
    Admin can view any user's history. Users can only view their own.
    Requires read permission.
    """
    # Additional authorization: non-admins can only view their own history
    if current_user.role != "admin" and current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's history",
        )

    return await service.get_user_history(user_id)
