"""Tests for /auth/me endpoint with permissions."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestAuthMeWithPermissions:
    """Test /auth/me endpoint returns user with permissions."""

    @pytest.mark.asyncio
    async def test_user_public_from_user_async_loads_permissions_from_db(self) -> None:
        """Test UserPublic.from_user_async() loads permissions from database."""
        from uuid import uuid4

        from app.models.domain.user import User
        from app.models.schemas.user import UserPublic

        # Mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.user_id = uuid4()
        mock_user.email = "admin@example.com"
        mock_user.full_name = "Admin User"
        mock_user.role = "admin"
        mock_user.is_active = True

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock database result for permissions
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("user-read",),
            ("user-create",),
            ("user-update",),
            ("user-delete",),
            ("department-read",),
            ("department-create",),
            ("department-update",),
            ("department-delete",),
        ]

        # Mock execute to return our mock result
        mock_session.execute.return_value = mock_result

        # Act
        user_public = await UserPublic.from_user_async(mock_user, mock_session)

        # Assert
        assert user_public.id == mock_user.id
        assert user_public.email == "admin@example.com"
        assert user_public.role == "admin"
        assert len(user_public.permissions) == 8
        assert "user-read" in user_public.permissions
        assert "user-delete" in user_public.permissions

    @pytest.mark.asyncio
    async def test_user_public_from_user_async_viewer_permissions(self) -> None:
        """Test UserPublic.from_user_async() for viewer role."""
        from uuid import uuid4

        from app.models.domain.user import User
        from app.models.schemas.user import UserPublic

        # Mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.user_id = uuid4()
        mock_user.email = "viewer@example.com"
        mock_user.full_name = "Viewer User"
        mock_user.role = "viewer"
        mock_user.is_active = True

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock database result for permissions
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("user-read",),
            ("department-read",),
        ]

        # Mock execute to return our mock result
        mock_session.execute.return_value = mock_result

        # Act
        user_public = await UserPublic.from_user_async(mock_user, mock_session)

        # Assert
        assert user_public.role == "viewer"
        assert len(user_public.permissions) == 2
        assert "user-read" in user_public.permissions
        assert "department-read" in user_public.permissions
        assert "user-delete" not in user_public.permissions

    @pytest.mark.asyncio
    async def test_user_public_from_user_async_uses_cache_when_available(self) -> None:
        """Test UserPublic.from_user_async() uses cache when available."""
        from uuid import uuid4

        from app.core.rbac_unified import get_unified_rbac_service
        from app.models.domain.user import User
        from app.models.schemas.user import UserPublic

        # Mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.user_id = uuid4()
        mock_user.email = "admin@example.com"
        mock_user.full_name = "Admin User"
        mock_user.role = "admin"
        mock_user.is_active = True

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)

        # Pre-populate cache
        unified_service = get_unified_rbac_service()
        unified_service._cache_permissions(
            "admin",
            [
                "user-read",
                "user-create",
                "user-update",
                "user-delete",
            ],
        )

        # Act
        user_public = await UserPublic.from_user_async(mock_user, mock_session)

        # Assert - should use cache, not query database
        assert len(user_public.permissions) == 4
        assert "user-read" in user_public.permissions
        # Session execute should not be called when cache is hit
        mock_session.execute.assert_not_called()
