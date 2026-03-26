from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_user_service
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.user import (
    RefreshRequest,
    Token,
    TokenResponse,
    UserPublic,
    UserRegister,
)
from app.services.auth import AuthService
from app.services.user import UserService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="register",
)
async def register(
    user_in: UserRegister,
    service: UserService = Depends(get_user_service),
) -> Any:
    """
    Register a new user.
    """
    try:
        # Check existing
        existing = await service.get_by_email(user_in.email)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="The user with this user name already exists in the system.",
            )

        # Create
        # Note: UserService.create_user expects actor_id. For registration,
        # either we use a system actor or the user acts as themselves (bootstrap).
        # We'll use a nil UUID or handle in service.
        # But 'actor_id' is mandatory in our current signature.
        from uuid import UUID

        system_actor = UUID("00000000-0000-0000-0000-000000000000")

        # Pass Pydantic model directly
        user = await service.create_user(user_in=user_in, actor_id=system_actor)

        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/login", response_model=TokenResponse, operation_id="login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """
    OAuth2 compatible token login, get an access token and refresh token for future requests.
    """
    auth_service = AuthService(session)
    user = await auth_service.authenticate_user(
        email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Create both access and refresh tokens
    token_response = await auth_service.authenticate(user)
    return token_response


@router.get("/me", response_model=UserPublic, operation_id="get_current_user")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserPublic:
    """
    Get current user profile with RBAC permissions.

    Returns user data including their role-based permissions for use
    in frontend authorization checks.
    """
    from app.core.rbac import get_rbac_service

    rbac_service = get_rbac_service()
    return UserPublic.from_user(current_user, rbac_service)


@router.post("/refresh", response_model=Token, operation_id="refresh_token")
async def refresh_token(
    refresh_request: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """
    Refresh access token using a valid refresh token.

    Returns a new access token if the refresh token is valid, not expired,
    and not revoked.
    """
    auth_service = AuthService(session)

    # Verify refresh token and get user_root_id
    user_root_id = await auth_service.verify_refresh_token(refresh_request.refresh_token)

    if not user_root_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user by root_id
    from app.services.user import UserService
    user_service = UserService(session)
    user = await user_service.get_user(user_root_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new access token
    token = await auth_service.create_access_token_for_user(user)
    return token


@router.post("/logout", operation_id="logout")
async def logout(
    refresh_request: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """
    Logout user by revoking their refresh token.

    The access token will still be valid until it expires, but the
    refresh token cannot be used to get new access tokens.
    """
    auth_service = AuthService(session)

    # Revoke the refresh token
    revoked = await auth_service.revoke_refresh_token(refresh_request.refresh_token)

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token not found or already revoked",
        )

    return {"message": "Successfully logged out"}
