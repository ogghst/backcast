"""Integration tests for RoleChecker dependency.

Tests the RoleChecker FastAPI dependency using real database users and the
unified RBAC system (UnifiedRBACService). Each test creates User records
and UserRoleAssignment records linked to the seeded RBAC roles.
"""

from typing import Annotated, Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_user
from app.core.rbac_unified import (
    UnifiedRBACService,
    set_unified_rbac_service,
    set_unified_rbac_session,
)
from app.db.session import get_db
from app.models.domain.rbac import RBACRole
from app.models.domain.user import User
from app.models.domain.user_role_assignment import ScopeType, UserRoleAssignment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Seeded role IDs from the database (looked up per test to avoid stale refs).
# The test DB has these roles: admin, manager, viewer (is_system=True).

async def _get_role_id(session: AsyncSession, role_name: str) -> Any:
    """Look up a seeded RBAC role ID by name."""
    result = await session.execute(
        select(RBACRole.id).where(RBACRole.name == role_name)
    )
    return result.scalar_one()

async def _create_db_user(
    session: AsyncSession,
    email: str,
    role: str = "viewer",
) -> User:
    """Insert a User row and return it."""
    user = User(
        id=uuid4(),
        user_id=uuid4(),
        email=email,
        full_name=f"{role.title()} User",
        is_active=True,
        hashed_password="hash",
        created_by=uuid4(),
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user

async def _assign_role(
    session: AsyncSession,
    user_id: Any,
    role_name: str,
    scope_type: str = ScopeType.GLOBAL,
    scope_id: Any | None = None,
) -> None:
    """Create a UserRoleAssignment row linking a user to a seeded role."""
    role_id = await _get_role_id(session, role_name)
    assignment = UserRoleAssignment(
        id=uuid4(),
        user_id=user_id,
        role_id=role_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )
    session.add(assignment)
    await session.flush()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create a real admin user in the database with admin role assignment."""
    user = await _create_db_user(
        db_session, "test-role-checker-admin@example.com", "admin"
    )
    await _assign_role(db_session, user.user_id, "admin")
    return user

@pytest_asyncio.fixture
async def manager_user(db_session: AsyncSession) -> User:
    """Create a real manager user in the database with manager role assignment."""
    user = await _create_db_user(
        db_session, "test-role-checker-manager@example.com", "manager"
    )
    await _assign_role(db_session, user.user_id, "manager")
    return user

@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Create a real viewer user in the database with viewer role assignment."""
    user = await _create_db_user(
        db_session, "test-role-checker-viewer@example.com", "viewer"
    )
    await _assign_role(db_session, user.user_id, "viewer")
    return user

@pytest_asyncio.fixture
def rbac_service() -> UnifiedRBACService:
    """Create a fresh UnifiedRBACService for each test (no stale cache)."""
    return UnifiedRBACService()

@pytest_asyncio.fixture
def test_app(
    db_session: AsyncSession,
    rbac_service: UnifiedRBACService,
) -> FastAPI:
    """Create a test FastAPI app with protected routes and real RBAC wiring."""
    app = FastAPI()

    # Wire up DB and auth overrides
    app.dependency_overrides[get_db] = lambda: db_session

    # -- Protected routes --

    @app.get("/admin-only")
    async def admin_only_route(
        user: Annotated[User, Depends(RoleChecker(["admin"]))],
    ) -> dict[str, Any]:
        return {"message": "Admin access granted"}

    @app.get("/admin-or-manager")
    async def admin_or_manager_route(
        user: Annotated[User, Depends(RoleChecker(["admin", "manager"]))],
    ) -> dict[str, Any]:
        return {"message": "Admin or manager access granted"}

    @app.get("/delete-permission")
    async def delete_permission_route(
        user: Annotated[User, Depends(RoleChecker(required_permission="user-delete"))],
    ) -> dict[str, Any]:
        return {"message": "Delete permission granted"}

    @app.get("/admin-or-delete")
    async def admin_or_delete_route(
        user: Annotated[User, Depends(RoleChecker(["admin"], "user-delete"))],
    ) -> dict[str, Any]:
        return {"message": "Admin or delete permission granted"}

    return app

def _make_client(
    test_app: FastAPI,
    db_session: AsyncSession,
    rbac_service: UnifiedRBACService,
    user: User,
) -> AsyncClient:
    """Build an AsyncClient that authenticates as the given user."""
    test_app.dependency_overrides[get_current_user] = lambda: user
    # Install the unified RBAC service globally and seed its permission cache
    set_unified_rbac_service(rbac_service)
    set_unified_rbac_session(db_session)
    return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRoleChecker:
    """Integration tests for RoleChecker dependency."""

    @pytest.mark.asyncio
    async def test_admin_accesses_admin_only_route(
        self,
        test_app: FastAPI,
        db_session: AsyncSession,
        rbac_service: UnifiedRBACService,
        admin_user: User,
    ) -> None:
        """Test that admin user can access admin-only route."""
        await rbac_service.refresh_permissions_cache()

        async with _make_client(
            test_app, db_session, rbac_service, admin_user
        ) as client:
            response = await client.get("/admin-only")

        assert response.status_code == 200
        assert response.json() == {"message": "Admin access granted"}

    @pytest.mark.asyncio
    async def test_viewer_denied_admin_only_route(
        self,
        test_app: FastAPI,
        db_session: AsyncSession,
        rbac_service: UnifiedRBACService,
        viewer_user: User,
    ) -> None:
        """Test that viewer user is denied access to admin-only route."""
        await rbac_service.refresh_permissions_cache()

        async with _make_client(
            test_app, db_session, rbac_service, viewer_user
        ) as client:
            response = await client.get("/admin-only")

        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_manager_accesses_admin_or_manager_route(
        self,
        test_app: FastAPI,
        db_session: AsyncSession,
        rbac_service: UnifiedRBACService,
        manager_user: User,
    ) -> None:
        """Test that manager user can access admin-or-manager route."""
        await rbac_service.refresh_permissions_cache()

        async with _make_client(
            test_app, db_session, rbac_service, manager_user
        ) as client:
            response = await client.get("/admin-or-manager")

        assert response.status_code == 200
        assert response.json() == {"message": "Admin or manager access granted"}

    @pytest.mark.asyncio
    async def test_admin_has_delete_permission(
        self,
        test_app: FastAPI,
        db_session: AsyncSession,
        rbac_service: UnifiedRBACService,
        admin_user: User,
    ) -> None:
        """Test that admin user with delete permission can access route."""
        await rbac_service.refresh_permissions_cache()

        async with _make_client(
            test_app, db_session, rbac_service, admin_user
        ) as client:
            response = await client.get("/delete-permission")

        assert response.status_code == 200
        assert response.json() == {"message": "Delete permission granted"}

    @pytest.mark.asyncio
    async def test_viewer_lacks_delete_permission(
        self,
        test_app: FastAPI,
        db_session: AsyncSession,
        rbac_service: UnifiedRBACService,
        viewer_user: User,
    ) -> None:
        """Test that viewer user without delete permission is denied."""
        await rbac_service.refresh_permissions_cache()

        async with _make_client(
            test_app, db_session, rbac_service, viewer_user
        ) as client:
            response = await client.get("/delete-permission")

        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_combined_check_admin_role(
        self,
        test_app: FastAPI,
        db_session: AsyncSession,
        rbac_service: UnifiedRBACService,
        admin_user: User,
    ) -> None:
        """Test combined check: admin role grants access."""
        await rbac_service.refresh_permissions_cache()

        async with _make_client(
            test_app, db_session, rbac_service, admin_user
        ) as client:
            response = await client.get("/admin-or-delete")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_combined_check_denied(
        self,
        test_app: FastAPI,
        db_session: AsyncSession,
        rbac_service: UnifiedRBACService,
        viewer_user: User,
    ) -> None:
        """Test combined check: neither role nor permission denies access."""
        await rbac_service.refresh_permissions_cache()

        async with _make_client(
            test_app, db_session, rbac_service, viewer_user
        ) as client:
            response = await client.get("/admin-or-delete")

        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]
