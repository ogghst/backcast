"""Tests for DatabaseRBACService.

Tests cover:
- Sync methods (has_role, has_permission, get_user_permissions) with cache
- Cache management (refresh_cache)
- Async project-level methods (has_project_access, get_user_projects, get_project_role)
- Fail-secure defaults when cache is empty
- Session fallback via contextvar
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.enums import ProjectRole as EnumProjectRole
from app.core.rbac import set_rbac_service, set_rbac_session
from app.core.rbac_database import DatabaseRBACService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service() -> DatabaseRBACService:
    """Create a DatabaseRBACService with no session for unit tests."""
    return DatabaseRBACService()


@pytest.fixture
def service_with_populated_cache() -> DatabaseRBACService:
    """Create a DatabaseRBACService with pre-populated permissions cache."""
    svc = DatabaseRBACService()
    now = datetime.now(UTC)
    svc._permissions_cache = {
        "admin": (
            [
                "project-read",
                "project-write",
                "project-delete",
                "user-read",
                "user-create",
            ],
            now,
        ),
        "manager": (
            ["project-read", "project-write", "forecast-read"],
            now,
        ),
        "viewer": (
            ["project-read", "forecast-read"],
            now,
        ),
    }
    return svc


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


class TestRefreshCache:
    """Tests for refresh_cache method."""

    @pytest.mark.asyncio
    async def test_refresh_cache_loads_role_permissions(self) -> None:
        """refresh_cache loads all role-permission mappings into cache.

        Given:
            A mock session returning role-permission rows.
        When:
            refresh_cache is called.
        Then:
            The permissions cache contains all roles and their permissions.
        """
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("admin", "project-read"),
            ("admin", "project-write"),
            ("viewer", "project-read"),
        ]
        mock_session.execute.return_value = mock_result

        set_rbac_session(mock_session)
        svc = DatabaseRBACService()
        await svc.refresh_cache()

        assert "admin" in svc._permissions_cache
        assert "viewer" in svc._permissions_cache
        perms, _ = svc._permissions_cache["admin"]
        assert "project-read" in perms
        assert "project-write" in perms

    @pytest.mark.asyncio
    async def test_refresh_cache_no_session_logs_warning(self) -> None:
        """refresh_cache does nothing when no session is available.

        Given:
            No session (self.session is None, contextvar is None).
        When:
            refresh_cache is called.
        Then:
            Cache remains empty.
        """
        set_rbac_session(None)
        svc = DatabaseRBACService(session=None)
        await svc.refresh_cache()

        assert svc._permissions_cache == {}

    @pytest.mark.asyncio
    async def test_refresh_cache_replaces_existing_entries(self) -> None:
        """refresh_cache replaces stale cache entries with fresh data.

        Given:
            An existing cache with old data.
        When:
            refresh_cache is called with new data.
        Then:
            Old entries are completely replaced.
        """
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("admin", "new-permission"),
        ]
        mock_session.execute.return_value = mock_result

        set_rbac_session(mock_session)
        svc = DatabaseRBACService()
        # Pre-populate with old data
        svc._permissions_cache = {
            "admin": (["old-permission"], datetime.now(UTC)),
            "removed_role": (["something"], datetime.now(UTC)),
        }

        await svc.refresh_cache()

        # Old roles not in the new result are gone
        assert "removed_role" not in svc._permissions_cache
        # Admin has the new permission
        perms, _ = svc._permissions_cache["admin"]
        assert "new-permission" in perms


# ---------------------------------------------------------------------------
# Sync methods (cache-only)
# ---------------------------------------------------------------------------


class TestHasRole:
    """Tests for has_role method."""

    def test_has_role_match(self, service: DatabaseRBACService) -> None:
        """has_role returns True when role is in required list."""
        assert service.has_role("admin", ["admin", "manager"]) is True

    def test_has_role_no_match(self, service: DatabaseRBACService) -> None:
        """has_role returns False when role is not in required list."""
        assert service.has_role("viewer", ["admin", "manager"]) is False

    def test_has_role_empty_required(self, service: DatabaseRBACService) -> None:
        """has_role returns False for empty required_roles."""
        assert service.has_role("admin", []) is False


class TestHasPermission:
    """Tests for has_permission method."""

    def test_has_permission_cache_hit(
        self, service_with_populated_cache: DatabaseRBACService
    ) -> None:
        """has_permission returns True when permission is in cache."""
        assert (
            service_with_populated_cache.has_permission("admin", "project-read") is True
        )

    def test_has_permission_cache_miss(self, service: DatabaseRBACService) -> None:
        """has_permission returns False when role is not in cache."""
        assert service.has_permission("unknown_role", "project-read") is False

    def test_has_permission_permission_missing(
        self, service_with_populated_cache: DatabaseRBACService
    ) -> None:
        """has_permission returns False when permission is not in cached list."""
        assert (
            service_with_populated_cache.has_permission("viewer", "project-write")
            is False
        )

    def test_has_permission_cache_hit_with_old_timestamp(
        self,
    ) -> None:
        """has_permission returns True even with old timestamp (no TTL expiry)."""
        svc = DatabaseRBACService(session=None)
        old_time = datetime.now(UTC) - timedelta(minutes=60)
        svc._permissions_cache = {
            "admin": (["project-read"], old_time),
        }

        assert svc.has_permission("admin", "project-read") is True

    def test_has_permission_empty_cache(self, service: DatabaseRBACService) -> None:
        """has_permission returns False (fail-secure) when cache is empty."""
        assert service.has_permission("admin", "project-read") is False


class TestGetUserPermissions:
    """Tests for get_user_permissions method."""

    def test_get_user_permissions_cache_hit(
        self, service_with_populated_cache: DatabaseRBACService
    ) -> None:
        """get_user_permissions returns cached permissions."""
        perms = service_with_populated_cache.get_user_permissions("admin")
        assert "project-read" in perms
        assert "project-write" in perms
        assert "project-delete" in perms

    def test_get_user_permissions_cache_miss(
        self, service: DatabaseRBACService
    ) -> None:
        """get_user_permissions returns empty list for unknown role."""
        assert service.get_user_permissions("unknown_role") == []

    def test_get_user_permissions_old_timestamp_still_valid(
        self,
    ) -> None:
        """get_user_permissions returns permissions even with old timestamp (no TTL)."""
        svc = DatabaseRBACService(session=None)
        old_time = datetime.now(UTC) - timedelta(minutes=60)
        svc._permissions_cache = {
            "admin": (["project-read"], old_time),
        }

        assert svc.get_user_permissions("admin") == ["project-read"]

    def test_get_user_permissions_returns_copy(
        self, service_with_populated_cache: DatabaseRBACService
    ) -> None:
        """get_user_permissions returns the actual cached list."""
        perms = service_with_populated_cache.get_user_permissions("viewer")
        assert perms == ["project-read", "forecast-read"]


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


class TestCacheHelpers:
    """Tests for _get_cached_permissions and _cache_permissions."""

    def test_get_cached_permissions_hit(self) -> None:
        """_get_cached_permissions returns permissions on fresh cache."""
        svc = DatabaseRBACService(session=None)
        svc._permissions_cache = {
            "admin": (["project-read"], datetime.now(UTC)),
        }
        assert svc._get_cached_permissions("admin") == ["project-read"]

    def test_get_cached_permissions_miss(self) -> None:
        """_get_cached_permissions returns None for unknown role."""
        svc = DatabaseRBACService(session=None)
        assert svc._get_cached_permissions("admin") is None

    def test_get_cached_permissions_old_timestamp_still_valid(self) -> None:
        """_get_cached_permissions returns permissions regardless of timestamp age."""
        svc = DatabaseRBACService(session=None)
        svc._permissions_cache = {
            "admin": (["project-read"], datetime.now(UTC) - timedelta(hours=1)),
        }
        assert svc._get_cached_permissions("admin") == ["project-read"]

    def test_cache_permissions_stores_entry(self) -> None:
        """_cache_permissions stores permissions with current timestamp."""
        svc = DatabaseRBACService(session=None)
        before = datetime.now(UTC)
        svc._cache_permissions("admin", ["project-read", "project-write"])
        after = datetime.now(UTC)

        assert "admin" in svc._permissions_cache
        perms, ts = svc._permissions_cache["admin"]
        assert perms == ["project-read", "project-write"]
        assert before <= ts <= after


# ---------------------------------------------------------------------------
# Async project-level methods
# ---------------------------------------------------------------------------


class TestHasProjectAccess:
    """Tests for has_project_access method."""

    @pytest.mark.asyncio
    async def test_admin_bypasses_project_checks(
        self, service: DatabaseRBACService
    ) -> None:
        """System admins always have project access."""
        user_id = uuid4()
        project_id = uuid4()

        has_access = await service.has_project_access(
            user_id=user_id,
            user_role="admin",
            project_id=project_id,
            required_permission="project-read",
        )
        assert has_access is True

    @pytest.mark.asyncio
    async def test_no_session_returns_false(self, service: DatabaseRBACService) -> None:
        """Missing database session denies access for non-admin users."""
        set_rbac_session(None)
        user_id = uuid4()
        project_id = uuid4()

        has_access = await service.has_project_access(
            user_id=user_id,
            user_role="viewer",
            project_id=project_id,
            required_permission="project-read",
        )
        assert has_access is False

    @pytest.mark.asyncio
    async def test_cache_hit_reduces_db_lookup(
        self, service: DatabaseRBACService
    ) -> None:
        """Cached project membership avoids database lookup."""
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)

        # project_manager has project-update permission
        service._project_cache[cache_key] = (
            EnumProjectRole.PROJECT_MANAGER.value,
            datetime.now(UTC),
        )

        has_access = await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-update",
        )
        assert has_access is True

    @pytest.mark.asyncio
    async def test_cache_hit_permission_denied(
        self, service: DatabaseRBACService
    ) -> None:
        """Cached project_viewer role denies update permission."""
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)

        service._project_cache[cache_key] = (
            EnumProjectRole.PROJECT_VIEWER.value,
            datetime.now(UTC),
        )

        has_access = await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-update",
        )
        assert has_access is False

    @pytest.mark.asyncio
    async def test_cache_expired_triggers_db_lookup(
        self, service: DatabaseRBACService
    ) -> None:
        """Expired cache entry falls through to database lookup."""
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)

        service._project_cache[cache_key] = (
            EnumProjectRole.PROJECT_EDITOR.value,
            datetime.now(UTC) - timedelta(minutes=6),
        )
        # No session, so DB lookup will fail
        set_rbac_session(None)

        has_access = await service.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-read",
        )
        assert has_access is False

    @pytest.mark.asyncio
    async def test_db_lookup_populates_cache(self) -> None:
        """Successful DB lookup populates the project cache."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_member = MagicMock()
        mock_member.role = EnumProjectRole.PROJECT_EDITOR.value
        mock_result.scalar_one_or_none.return_value = mock_member
        mock_session.execute.return_value = mock_result

        set_rbac_session(mock_session)
        svc = DatabaseRBACService()
        user_id = uuid4()
        project_id = uuid4()

        has_access = await svc.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-read",
        )
        assert has_access is True

        # Verify cache was populated
        cache_key = (user_id, project_id)
        assert cache_key in svc._project_cache
        cached_role, _ = svc._project_cache[cache_key]
        assert cached_role == EnumProjectRole.PROJECT_EDITOR.value

        # Cleanup
        set_rbac_session(None)

    @pytest.mark.asyncio
    async def test_no_membership_returns_false(self) -> None:
        """User not in project returns False."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        set_rbac_session(mock_session)
        svc = DatabaseRBACService()
        user_id = uuid4()
        project_id = uuid4()

        has_access = await svc.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-read",
        )
        assert has_access is False

        # Cleanup
        set_rbac_session(None)

    @pytest.mark.asyncio
    async def test_contextvar_session_fallback(self) -> None:
        """has_project_access uses contextvar session when self.session is None."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_member = MagicMock()
        mock_member.role = EnumProjectRole.PROJECT_VIEWER.value
        mock_result.scalar_one_or_none.return_value = mock_member
        mock_session.execute.return_value = mock_result

        set_rbac_session(mock_session)

        svc = DatabaseRBACService(session=None)
        user_id = uuid4()
        project_id = uuid4()

        has_access = await svc.has_project_access(
            user_id=user_id,
            user_role="user",
            project_id=project_id,
            required_permission="project-read",
        )
        assert has_access is True
        mock_session.execute.assert_called_once()

        # Cleanup
        set_rbac_session(None)


class TestGetUserProjects:
    """Tests for get_user_projects method."""

    @pytest.mark.asyncio
    async def test_admin_no_session_returns_empty(
        self, service: DatabaseRBACService
    ) -> None:
        """Admin without session returns empty list."""
        set_rbac_session(None)
        user_id = uuid4()

        projects = await service.get_user_projects(user_id=user_id, user_role="admin")
        assert projects == []

    @pytest.mark.asyncio
    async def test_non_admin_no_session_returns_empty(
        self, service: DatabaseRBACService
    ) -> None:
        """Non-admin without session returns empty list."""
        set_rbac_session(None)
        user_id = uuid4()

        projects = await service.get_user_projects(user_id=user_id, user_role="viewer")
        assert projects == []

    @pytest.mark.asyncio
    async def test_admin_gets_all_projects(self) -> None:
        """Admin user gets all project IDs from database."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        project_ids = [uuid4(), uuid4()]
        mock_result.all.return_value = [(pid,) for pid in project_ids]
        mock_session.execute.return_value = mock_result

        set_rbac_session(mock_session)
        svc = DatabaseRBACService()
        user_id = uuid4()

        projects = await svc.get_user_projects(user_id=user_id, user_role="admin")
        assert projects == project_ids

        # Cleanup
        set_rbac_session(None)

    @pytest.mark.asyncio
    async def test_non_admin_gets_member_projects(self) -> None:
        """Non-admin user gets only projects they are member of."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        project_id = uuid4()
        mock_result.all.return_value = [(project_id,)]
        mock_session.execute.return_value = mock_result

        set_rbac_session(mock_session)
        svc = DatabaseRBACService()
        user_id = uuid4()

        projects = await svc.get_user_projects(user_id=user_id, user_role="viewer")
        assert projects == [project_id]

        # Cleanup
        set_rbac_session(None)


class TestGetProjectRole:
    """Tests for get_project_role method."""

    @pytest.mark.asyncio
    async def test_no_session_returns_none(self, service: DatabaseRBACService) -> None:
        """Missing session returns None."""
        set_rbac_session(None)
        user_id = uuid4()
        project_id = uuid4()

        role = await service.get_project_role(user_id=user_id, project_id=project_id)
        assert role is None

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_role(
        self, service: DatabaseRBACService
    ) -> None:
        """Cached role is returned without database lookup."""
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)
        cached_role = EnumProjectRole.PROJECT_VIEWER.value

        service._project_cache[cache_key] = (cached_role, datetime.now(UTC))

        role = await service.get_project_role(user_id=user_id, project_id=project_id)
        assert role == cached_role

    @pytest.mark.asyncio
    async def test_cache_expired_returns_none_without_session(
        self, service: DatabaseRBACService
    ) -> None:
        """Expired cache without session returns None."""
        user_id = uuid4()
        project_id = uuid4()
        cache_key = (user_id, project_id)

        service._project_cache[cache_key] = (
            EnumProjectRole.PROJECT_ADMIN.value,
            datetime.now(UTC) - timedelta(minutes=6),
        )
        set_rbac_session(None)

        role = await service.get_project_role(user_id=user_id, project_id=project_id)
        assert role is None

    @pytest.mark.asyncio
    async def test_db_lookup_populates_cache(self) -> None:
        """Successful DB lookup populates cache and returns role."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = (
            EnumProjectRole.PROJECT_EDITOR.value
        )
        mock_session.execute.return_value = mock_result

        set_rbac_session(mock_session)
        svc = DatabaseRBACService()
        user_id = uuid4()
        project_id = uuid4()

        role = await svc.get_project_role(user_id=user_id, project_id=project_id)
        assert role == EnumProjectRole.PROJECT_EDITOR.value

        # Verify cache was populated
        cache_key = (user_id, project_id)
        assert cache_key in svc._project_cache

        # Cleanup
        set_rbac_session(None)

    @pytest.mark.asyncio
    async def test_no_membership_returns_none(self) -> None:
        """User not in project returns None and nothing cached."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        set_rbac_session(mock_session)
        svc = DatabaseRBACService()
        user_id = uuid4()
        project_id = uuid4()

        role = await svc.get_project_role(user_id=user_id, project_id=project_id)
        assert role is None

        # Nothing cached for non-membership
        cache_key = (user_id, project_id)
        assert cache_key not in svc._project_cache

        # Cleanup
        set_rbac_session(None)


# ---------------------------------------------------------------------------
# Integration: get_rbac_service factory
# ---------------------------------------------------------------------------


class TestGetRbacServiceFactory:
    """Tests for get_rbac_service factory supporting database provider."""

    def test_database_provider_creates_database_service(self) -> None:
        """get_rbac_service creates DatabaseRBACService when RBAC_PROVIDER=database."""
        from app.core.rbac import get_rbac_service
        from app.core.rbac_database import DatabaseRBACService

        # Reset singleton
        set_rbac_service(None)  # type: ignore[arg-type]

        original = None
        try:
            from app.core.config import settings

            original = settings.RBAC_PROVIDER
            settings.RBAC_PROVIDER = "database"

            svc = get_rbac_service()
            assert isinstance(svc, DatabaseRBACService)
        finally:
            # Restore
            if original is not None:
                settings.RBAC_PROVIDER = original
            set_rbac_service(None)  # type: ignore[arg-type]

    def test_json_provider_creates_json_service(self) -> None:
        """get_rbac_service creates JsonRBACService when RBAC_PROVIDER=json."""
        from app.core.rbac import JsonRBACService, get_rbac_service

        # Reset singleton
        set_rbac_service(None)  # type: ignore[arg-type]

        try:
            from app.core.config import settings

            original = settings.RBAC_PROVIDER
            settings.RBAC_PROVIDER = "json"

            svc = get_rbac_service()
            assert isinstance(svc, JsonRBACService)
        finally:
            from app.core.config import settings

            settings.RBAC_PROVIDER = original
            set_rbac_service(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TTL constant
# ---------------------------------------------------------------------------


class TestCacheTTL:
    """Tests for project cache TTL configuration."""

    def test_project_cache_ttl_is_5_minutes(self) -> None:
        """Project membership cache TTL is set to 5 minutes."""
        assert DatabaseRBACService._PROJECT_CACHE_TTL == timedelta(minutes=5)


# ---------------------------------------------------------------------------
# Abstract method compliance
# ---------------------------------------------------------------------------


class TestAbstractMethodCompliance:
    """Test that DatabaseRBACService implements all abstract methods."""

    def test_implements_all_abstract_methods(self) -> None:
        """DatabaseRBACService has all required methods."""
        svc = DatabaseRBACService(session=None)

        assert hasattr(svc, "has_role") and callable(svc.has_role)
        assert hasattr(svc, "has_permission") and callable(svc.has_permission)
        assert hasattr(svc, "get_user_permissions") and callable(
            svc.get_user_permissions
        )
        assert hasattr(svc, "has_project_access") and callable(svc.has_project_access)
        assert hasattr(svc, "get_user_projects") and callable(svc.get_user_projects)
        assert hasattr(svc, "get_project_role") and callable(svc.get_project_role)
        assert hasattr(svc, "refresh_cache") and callable(svc.refresh_cache)
