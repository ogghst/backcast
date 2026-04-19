"""Stub AuthService for authentication routes.

TODO: Replace with proper implementation using new TemporalService.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.domain.user import User
from app.models.schemas.user import Token, TokenResponse


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

    async def create_refresh_token(
        self, user_root_id: UUID, user_version_id: UUID
    ) -> str:
        """Generate, hash, and store refresh token for user.

        Args:
            user_root_id: The user's root UUID (stable identifier)
            user_version_id: The user's version-specific UUID (for FK constraint)

        Returns:
            The raw refresh token (unhashed) to return to client
        """
        from app.models.domain.refresh_token import RefreshToken

        # Generate raw token
        raw_token = str(uuid4())

        # Hash it for storage
        token_hash = get_password_hash(raw_token)

        # Calculate expiration
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Store in database
        refresh_token = RefreshToken(
            user_id=user_version_id,  # FK to users.id (version-specific)
            user_root_id=user_root_id,  # For querying across versions
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(refresh_token)
        await self.session.flush()

        return raw_token

    async def verify_refresh_token(self, token: str) -> UUID | None:
        """Validate refresh token and return user_root_id if valid.

        Args:
            token: The raw refresh token from client

        Returns:
            user_root_id if token is valid and not revoked/expired, None otherwise
        """
        from sqlalchemy import select

        from app.models.domain.refresh_token import RefreshToken

        # We need to find the token by comparing the hash
        # Get all non-revoked, non-expired tokens
        stmt = select(RefreshToken).where(
            and_(
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()

        # Check each token's hash
        for refresh_token in tokens:
            if verify_password(token, refresh_token.token_hash):
                # Token is valid, return the root user ID
                return refresh_token.user_root_id

        # No valid token found
        return None

    async def revoke_refresh_token(self, token: str) -> bool:
        """Mark a refresh token as revoked (for logout).

        Args:
            token: The raw refresh token from client

        Returns:
            True if token was found and revoked, False otherwise
        """
        from sqlalchemy import select

        from app.models.domain.refresh_token import RefreshToken

        # Find the token by hash comparison
        stmt = select(RefreshToken).where(
            and_(
                RefreshToken.revoked_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()

        # Find and revoke the matching token
        for refresh_token in tokens:
            if verify_password(token, refresh_token.token_hash):
                refresh_token.revoked_at = datetime.now(UTC)
                await self.session.flush()
                return True

        return False

    async def authenticate(self, user: User) -> TokenResponse:
        """Create both access and refresh tokens for authenticated user.

        Args:
            user: The authenticated user entity

        Returns:
            TokenResponse with both access_token and refresh_token
        """
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.email, expires_delta=access_token_expires
        )

        # Create refresh token (pass both root_id and version_id)
        refresh_token = await self.create_refresh_token(
            user_root_id=user.user_id, user_version_id=user.id
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
