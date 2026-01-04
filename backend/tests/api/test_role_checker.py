"""Integration tests for RoleChecker dependency.

Tests the RoleChecker FastAPI dependency with mock routes and users.
"""

from typing import Annotated
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.auth import RoleChecker
from app.core.rbac import RBACServiceABC, set_rbac_service
from app.models.domain.user import User


class TestRoleChecker:
    """Integration tests for RoleChecker dependency."""

    @pytest.fixture
    def mock_rbac_service(self) -> RBACServiceABC:
        """Create a mock RBAC service for testing."""
        mock_service = MagicMock(spec=RBACServiceABC)

        # Configure mock behavior
        def has_role_side_effect(user_role: str, required_roles: list[str]) -> bool:
            return user_role in required_roles

        def has_permission_side_effect(user_role: str, required_permission: str) -> bool:
            role_permissions = {
                "admin": [
                    "user-read",
                    "user-create",
                    "user-update",
                    "user-delete",
                    "department-read",
                    "department-create",
                    "department-update",
                    "department-delete",
                ],
                "manager": [
                    "user-read",
                    "user-update",
                    "department-read",
                    "department-create",
                    "department-update",
                ],
                "viewer": ["user-read", "department-read"],
            }
            return required_permission in role_permissions.get(user_role, [])

        mock_service.has_role.side_effect = has_role_side_effect
        mock_service.has_permission.side_effect = has_permission_side_effect

        return mock_service

    @pytest.fixture
    def test_app(self, mock_rbac_service: RBACServiceABC) -> FastAPI:
        """Create a test FastAPI app with protected routes."""
        # Set the mock RBAC service globally
        set_rbac_service(mock_rbac_service)

        app = FastAPI()

        # Mock current user dependency
        def get_mock_user(role: str = "viewer") -> User:
            user = MagicMock(spec=User)
            user.role = role
            user.email = "test@example.com"
            user.is_active = True
            return user

        # Route 1: Role-only protection (admin only)
        @app.get("/admin-only")
        async def admin_only_route(
            user: Annotated[User, Depends(RoleChecker(["admin"]))]
        ) -> dict:
            return {"message": "Admin access granted"}

        # Route 2: Role-only protection (admin or manager)
        @app.get("/admin-or-manager")
        async def admin_or_manager_route(
            user: Annotated[User, Depends(RoleChecker(["admin", "manager"]))]
        ) -> dict:
            return {"message": "Admin or manager access granted"}

        # Route 3: Permission-only protection (user-delete permission)
        @app.get("/delete-permission")
        async def delete_permission_route(
            user: Annotated[User, Depends(RoleChecker(required_permission="user-delete"))]
        ) -> dict:
            return {"message": "Delete permission granted"}

        # Route 4: Combined protection (admin role OR user-delete permission)
        @app.get("/admin-or-delete")
        async def admin_or_delete_route(
            user: Annotated[User, Depends(RoleChecker(["admin"], "user-delete"))]
        ) -> dict:
            return {"message": "Admin or delete permission granted"}

        # Helper endpoint to set current user role
        current_user_role = {"role": "viewer"}

        @app.get("/set-role/{role}")
        async def set_role(role: str) -> dict:
            current_user_role["role"] = role
            return {"role": role}

        # Override the get_current_user dependency
        async def override_get_current_user() -> User:
            return get_mock_user(current_user_role["role"])

        # Import and override after the routes are defined
        from app.api.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user

        return app

    # 🔴 RED: Integration Test 1 - Admin accesses admin-only route
    @pytest.mark.asyncio
    async def test_admin_accesses_admin_only_route(self, test_app: FastAPI) -> None:
        """Test that admin user can access admin-only route."""
        # Arrange
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            # Set user role to admin
            await client.get("/set-role/admin")

            # Act
            response = await client.get("/admin-only")

            # Assert
            assert response.status_code == 200
            assert response.json() == {"message": "Admin access granted"}

    # 🔴 RED: Integration Test 2 - Viewer tries admin route → 403
    @pytest.mark.asyncio
    async def test_viewer_denied_admin_only_route(self, test_app: FastAPI) -> None:
        """Test that viewer user is denied access to admin-only route."""
        # Arrange
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            # Set user role to viewer
            await client.get("/set-role/viewer")

            # Act
            response = await client.get("/admin-only")

            # Assert
            assert response.status_code == 403
            assert "Insufficient permissions" in response.json()["detail"]

    # 🔴 RED: Integration Test 3 - Manager accesses admin-or-manager route
    @pytest.mark.asyncio
    async def test_manager_accesses_admin_or_manager_route(self, test_app: FastAPI) -> None:
        """Test that manager user can access admin-or-manager route."""
        # Arrange
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            # Set user role to manager
            await client.get("/set-role/manager")

            # Act
            response = await client.get("/admin-or-manager")

            # Assert
            assert response.status_code == 200
            assert response.json() == {"message": "Admin or manager access granted"}

    # 🔴 RED: Integration Test 4 - Permission-only check (admin has delete)
    @pytest.mark.asyncio
    async def test_admin_has_delete_permission(self, test_app: FastAPI) -> None:
        """Test that admin user with delete permission can access route."""
        # Arrange
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            # Set user role to admin
            await client.get("/set-role/admin")

            # Act
            response = await client.get("/delete-permission")

            # Assert
            assert response.status_code == 200
            assert response.json() == {"message": "Delete permission granted"}

    # 🔴 RED: Integration Test 5 - Permission-only check (viewer lacks delete)
    @pytest.mark.asyncio
    async def test_viewer_lacks_delete_permission(self, test_app: FastAPI) -> None:
        """Test that viewer user without delete permission is denied."""
        # Arrange
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            # Set user role to viewer
            await client.get("/set-role/viewer")

            # Act
            response = await client.get("/delete-permission")

            # Assert
            assert response.status_code == 403
            assert "Insufficient permissions" in response.json()["detail"]

    # 🔴 RED: Integration Test 6 - Combined check (admin role granted)
    @pytest.mark.asyncio
    async def test_combined_check_admin_role(self, test_app: FastAPI) -> None:
        """Test combined check: admin role grants access."""
        # Arrange
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            # Set user role to admin
            await client.get("/set-role/admin")

            # Act
            response = await client.get("/admin-or-delete")

            # Assert
            assert response.status_code == 200

    # 🔴 RED: Integration Test 7 - Combined check (neither role nor permission)
    @pytest.mark.asyncio
    async def test_combined_check_denied(self, test_app: FastAPI) -> None:
        """Test combined check: neither role nor permission denies access."""
        # Arrange
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            # Set user role to viewer (no admin role, no delete permission)
            await client.get("/set-role/viewer")

            # Act
            response = await client.get("/admin-or-delete")

            # Assert
            assert response.status_code == 403
            assert "Insufficient permissions" in response.json()["detail"]
