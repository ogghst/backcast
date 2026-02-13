"""Stub AuthService for authentication routes.

TODO: Replace with proper implementation using new TemporalService.
"""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.domain.user import User
from app.models.schemas.user import Token


class AuthService:
    """Temporary stub for authentication service."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate user by email and password."""
        from app.services.user import UserService

        user_service = UserService(self.session)
        user = await user_service.get_by_email(email)

        if not user or not verify_password(password, user.hashed_password):
            return None

        return user

    async def create_access_token_for_user(self, user: User) -> Token:
        """Create access token for authenticated user."""
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.email, expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")
