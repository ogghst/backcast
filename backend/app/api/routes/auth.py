from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_user_service
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.user import Token, UserPublic, UserRegister
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


@router.post("/login", response_model=Token, operation_id="login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
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

    # Access Token
    token = await auth_service.create_access_token_for_user(user)
    return token


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
