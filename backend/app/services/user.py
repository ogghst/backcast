"""UserService extending TemporalService.

Provides User-specific operations on top of generic temporal service.
"""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.service import TemporalService
from app.models.domain.user import User
from app.models.schemas.user import UserRegister, UserUpdate


class UserService(TemporalService[User]):  # type: ignore[type-var,unused-ignore]
    """Service for User entity operations.

    Extends TemporalService with user-specific methods like get_by_email.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_user(self, user_id: UUID) -> User | None:
        """Get user by ID (current version)."""
        return await self.get_by_id(user_id)

    async def get_users(self, skip: int = 0, limit: int = 100000) -> list[User]:
        """Get all users with pagination."""
        return await self.get_all(skip, limit)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address (current active version)."""
        # Use upper(valid_time) IS NULL for open-ended ranges (consistent with get_all)
        from typing import Any, cast

        from sqlalchemy import func

        stmt = (
            select(User)
            .where(
                User.email == email,
                func.upper(cast(Any, User).valid_time).is_(None),
                cast(Any, User).deleted_at.is_(None),
            )
            .order_by(cast(Any, User).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, user_in: UserRegister, actor_id: UUID) -> User:
        """Create new user using CreateVersionCommand with Pydantic validation."""
        user_data = user_in.model_dump()

        # Handle password hashing
        password = user_data.pop("password")
        user_data["hashed_password"] = get_password_hash(password)

        # Ensure root user_id exists (though normally not in register input,
        # but could be generated here if needed for CreateVersionCommand)
        root_id = uuid4()
        user_data["user_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=User,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            **user_data,
        )
        return await cmd.execute(self.session)

    async def update_user(
        self, user_id: UUID, user_in: UserUpdate, actor_id: UUID
    ) -> User:
        """Update user using UpdateVersionCommand with Pydantic validation."""
        # Filter None values from update data
        update_data = user_in.model_dump(exclude_unset=True)

        if "password" in update_data:
            password = update_data.pop("password")
            update_data["hashed_password"] = get_password_hash(password)

        # If no changes remaining (e.g. empty update), we might still want to
        # create a new version if that's the semantic, or just return current.
        # But UpdateVersionCommand usually expects something.
        # However, purely strictly speaking, if nothing to update, we pass it down
        # and let the command decide or just do it.

        cmd = UpdateVersionCommand(
            entity_class=User,  # type: ignore[type-var,unused-ignore]
            root_id=user_id,
            actor_id=actor_id,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def delete_user(self, user_id: UUID, actor_id: UUID) -> User:
        """Soft delete user using SoftDeleteCommand."""
        cmd = SoftDeleteCommand(
            entity_class=User,  # type: ignore[type-var,unused-ignore]
            root_id=user_id,
            actor_id=actor_id,
        )
        return await cmd.execute(self.session)

    async def get_user_history(self, user_id: UUID) -> list[User]:
        """Get all versions of a user by root user_id (with creator name)."""
        return await self.get_history(user_id)

    async def get_user_preferences(self, user_id: UUID) -> dict[str, Any]:
        """Get user preferences from JSON column."""
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return user.preferences or {}

    async def update_user_preferences(
        self, user_id: UUID, preferences_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update user preferences in JSON column."""
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Merge with existing preferences
        current_prefs = user.preferences or {}
        updated_prefs = {**current_prefs, **preferences_data}

        # Update the user entity directly (no versioning for preferences)
        user.preferences = updated_prefs
        await self.session.commit()  # Commit immediately to persist changes

        return updated_prefs
