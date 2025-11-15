from collections.abc import Generator
from datetime import date
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, User, UserRole

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_time_machine_control_date(current_user: CurrentUser) -> date:
    """Resolve the effective control date for the current request."""

    return current_user.time_machine_date or date.today()


TimeMachineControlDate = Annotated[date, Depends(get_time_machine_control_date)]


def get_current_active_admin(current_user: CurrentUser) -> User:
    """Dependency to ensure current user has admin role."""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_current_user_with_role(required_role: UserRole):
    """Dependency factory to check for a specific role."""

    def role_checker(current_user: CurrentUser) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"The user doesn't have the required role: {required_role.value}",
            )
        return current_user

    return role_checker


# Keep old function name for backward compatibility during migration
# Will be removed after all routes are updated
get_current_active_superuser = get_current_active_admin
