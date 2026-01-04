"""Tests for /auth/me endpoint with permissions."""

from unittest.mock import MagicMock

import pytest

from app.core.rbac import RBACServiceABC


class TestAuthMeWithPermissions:
    """Test /auth/me endpoint returns user with permissions."""

    @pytest.mark.asyncio
    async def test_user_public_from_user_includes_permissions(self) -> None:
        """Test UserPublic.from_user() includes permissions from RBAC service."""
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

        # Mock RBAC service
        mock_rbac = MagicMock(spec=RBACServiceABC)
        mock_rbac.get_user_permissions.return_value = [
            "user-read",
            "user-create",
            "user-update",
            "user-delete",
            "department-read",
            "department-create",
            "department-update",
            "department-delete",
        ]

        # Act
        user_public = UserPublic.from_user(mock_user, mock_rbac)

        # Assert
        assert user_public.id == mock_user.id
        assert user_public.email == "admin@example.com"
        assert user_public.role == "admin"
        assert len(user_public.permissions) == 8
        assert "user-read" in user_public.permissions
        assert "user-delete" in user_public.permissions
        mock_rbac.get_user_permissions.assert_called_once_with("admin")

    @pytest.mark.asyncio
    async def test_user_public_from_user_viewer_permissions(self) -> None:
        """Test UserPublic.from_user() for viewer role."""
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

        # Mock RBAC service
        mock_rbac = MagicMock(spec=RBACServiceABC)
        mock_rbac.get_user_permissions.return_value = [
            "user-read",
            "department-read",
        ]

        # Act
        user_public = UserPublic.from_user(mock_user, mock_rbac)

        # Assert
        assert user_public.role == "viewer"
        assert len(user_public.permissions) == 2
        assert "user-read" in user_public.permissions
        assert "department-read" in user_public.permissions
        assert "user-delete" not in user_public.permissions
