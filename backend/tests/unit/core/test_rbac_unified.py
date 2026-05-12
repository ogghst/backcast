"""Tests for UnifiedRBACService - permission checks, caching, and CRUD.

Tests cover:
- Permission checks across global/project/change_order scopes
- Cache hit/miss and TTL behavior
- Authority level checking
- CRUD operations (assign_role, revoke_role, get_user_roles)
- Thread safety (basic)
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.rbac_unified import (
    ScopeType,
    UnifiedRBACService,
    get_unified_rbac_service,
    set_unified_rbac_service,
)
from app.models.domain.user_role_assignment import UserRoleAssignment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_assignment(
    user_id: UUID,
    role_id: UUID,
    scope_type: str = ScopeType.GLOBAL,
    scope_id: UUID | None = None,
    metadata: dict | None = None,
) -> MagicMock:
    """Create a mock UserRoleAssignment instance for testing."""
    a = MagicMock(spec=UserRoleAssignment)
    a.id = uuid4()
    a.user_id = user_id
    a.role_id = role_id
    a.scope_type = scope_type
    a.scope_id = scope_id
    a.metadata_ = metadata
    a.granted_by = None
    a.granted_at = datetime.now(UTC)
    a.expires_at = None
    a.created_at = datetime.now(UTC)
    a.updated_at = datetime.now(UTC)
    return a


# ---------------------------------------------------------------------------
# Permission Cache Tests
# ---------------------------------------------------------------------------


class TestPermissionCache:
    """Tests for permission caching behavior."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()

    def test_cache_permissions_stores_entry(self) -> None:
        self.service._cache_permissions("admin", ["read", "write"])
        assert self.service._get_cached_permissions("admin") == ["read", "write"]

    def test_get_cached_permissions_returns_none_on_miss(self) -> None:
        assert self.service._get_cached_permissions("nonexistent") is None

    def test_get_cached_permissions_returns_none_on_expired(self) -> None:
        self.service._cache_permissions("admin", ["read"])
        # Manually expire the entry
        cached_at = datetime.now(UTC) - timedelta(hours=2)
        self.service._permissions_cache["admin"] = (["read"], cached_at)
        assert self.service._get_cached_permissions("admin") is None

    def test_get_cached_permissions_returns_value_within_ttl(self) -> None:
        self.service._cache_permissions("admin", ["read", "write"])
        result = self.service._get_cached_permissions("admin")
        assert result == ["read", "write"]

    def test_check_permission_from_roles_returns_true_on_match(self) -> None:
        self.service._cache_permissions("admin", ["read", "write"])
        assert self.service._check_permission_from_roles(["admin"], "read") is True

    def test_check_permission_from_roles_returns_false_on_no_match(self) -> None:
        self.service._cache_permissions("viewer", ["read"])
        assert self.service._check_permission_from_roles(["viewer"], "write") is False

    def test_check_permission_from_roles_returns_false_on_cache_miss(self) -> None:
        assert self.service._check_permission_from_roles(["unknown"], "read") is False


# ---------------------------------------------------------------------------
# Assignment Cache Tests
# ---------------------------------------------------------------------------


class TestAssignmentCache:
    """Tests for role assignment caching behavior."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()

    def test_cache_assignments_stores_entry(self) -> None:
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )
        result = self.service._get_cached_assignments(
            self.user_id, ScopeType.GLOBAL, None
        )
        assert result == ["admin"]

    def test_get_cached_assignments_returns_none_on_miss(self) -> None:
        result = self.service._get_cached_assignments(
            uuid4(), ScopeType.GLOBAL, None
        )
        assert result is None

    def test_get_cached_assignments_returns_none_on_expired(self) -> None:
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )
        # Expire
        cache_key = (self.user_id, ScopeType.GLOBAL, None)
        cached_at = datetime.now(UTC) - timedelta(minutes=10)
        self.service._assignment_cache[cache_key] = (["admin"], cached_at)

        result = self.service._get_cached_assignments(
            self.user_id, ScopeType.GLOBAL, None
        )
        assert result is None

    def test_invalidate_assignment_cache_by_user(self) -> None:
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, uuid4(), ["editor"]
        )

        self.service._invalidate_assignment_cache(self.user_id)

        assert self.service._get_cached_assignments(
            self.user_id, ScopeType.GLOBAL, None
        ) is None
        assert self.service._assignment_cache == {}

    def test_invalidate_assignment_cache_by_scope(self) -> None:
        project_id = uuid4()
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, project_id, ["editor"]
        )

        self.service._invalidate_assignment_cache(
            self.user_id, ScopeType.PROJECT, project_id
        )

        # Global should still be cached
        assert self.service._get_cached_assignments(
            self.user_id, ScopeType.GLOBAL, None
        ) == ["admin"]
        # Project should be invalidated
        assert self.service._get_cached_assignments(
            self.user_id, ScopeType.PROJECT, project_id
        ) is None


# ---------------------------------------------------------------------------
# Permission Check Tests
# ---------------------------------------------------------------------------


class TestPermissionChecks:
    """Tests for has_permission with scope resolution."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()
        self.admin_role_id = uuid4()
        self.editor_role_id = uuid4()

    @pytest.mark.asyncio
    async def test_admin_bypasses_all_checks(self) -> None:
        """Admin role should bypass all permission checks."""
        # Seed cache: admin has all permissions
        self.service._cache_permissions("admin", ["everything"])
        # Seed assignment cache
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session", return_value=MagicMock()
        ):
            result = await self.service.has_permission(
                self.user_id, "any-permission", ScopeType.GLOBAL, None
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_global_permission_check(self) -> None:
        """Global role grants permission."""
        self.service._cache_permissions("manager", ["project-read", "project-write"])
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["manager"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session", return_value=MagicMock()
        ):
            result = await self.service.has_permission(
                self.user_id, "project-read", ScopeType.GLOBAL, None
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_global_permission_denied(self) -> None:
        """User without matching permission is denied."""
        self.service._cache_permissions("viewer", ["project-read"])
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session", return_value=MagicMock()
        ):
            result = await self.service.has_permission(
                self.user_id, "project-delete", ScopeType.GLOBAL, None
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_project_scoped_permission_check(self) -> None:
        """Project-scoped role grants permission."""
        project_id = uuid4()
        self.service._cache_permissions("editor", ["project-read", "project-write"])
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, project_id, ["editor"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session", return_value=MagicMock()
        ):
            result = await self.service.has_permission(
                self.user_id, "project-write", ScopeType.PROJECT, project_id
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_fail_secure_on_no_session(self) -> None:
        """Permission check returns False when no session available."""
        with patch(
            "app.core.rbac_unified.get_unified_rbac_session", return_value=None
        ):
            result = await self.service.has_permission(
                self.user_id, "any-permission", ScopeType.GLOBAL, None
            )
        assert result is False


# ---------------------------------------------------------------------------
# Authority Level Tests
# ---------------------------------------------------------------------------


class TestAuthorityLevel:
    """Tests for has_authority_level method."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()

    @pytest.mark.asyncio
    async def test_admin_has_all_authority(self) -> None:
        """Admin users always have authority."""
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock())

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "CRITICAL", None
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_insufficient_authority_denied(self) -> None:
        """User with LOW authority cannot approve HIGH requirement."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "HIGH", None
            )
        assert result is False


# ---------------------------------------------------------------------------
# CRUD Tests
# ---------------------------------------------------------------------------


class TestCRUDOperations:
    """Tests for assign_role, revoke_role, get_user_roles."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()
        self.role_id = uuid4()

    @pytest.mark.asyncio
    async def test_assign_role_creates_assignment(self) -> None:
        """assign_role creates a UserRoleAssignment."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            assignment = await self.service.assign_role(
                user_id=self.user_id,
                role_id=self.role_id,
                scope_type=ScopeType.GLOBAL,
                scope_id=None,
            )

        assert assignment.user_id == self.user_id
        assert assignment.role_id == self.role_id
        assert assignment.scope_type == ScopeType.GLOBAL
        assert assignment.scope_id is None

    @pytest.mark.asyncio
    async def test_assign_role_rejects_duplicate(self) -> None:
        """assign_role raises ValueError for duplicate assignment."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_assignment(
            self.user_id, self.role_id
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            with pytest.raises(ValueError, match="already has a role assignment"):
                await self.service.assign_role(
                    user_id=self.user_id,
                    role_id=self.role_id,
                    scope_type=ScopeType.GLOBAL,
                    scope_id=None,
                )

    @pytest.mark.asyncio
    async def test_assign_role_with_metadata(self) -> None:
        """assign_role stores metadata (e.g., authority_level)."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        metadata = {"authority_level": "HIGH"}

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            assignment = await self.service.assign_role(
                user_id=self.user_id,
                role_id=self.role_id,
                scope_type=ScopeType.CHANGE_ORDER,
                scope_id=uuid4(),
                metadata=metadata,
            )

        assert assignment.metadata_ == metadata

    @pytest.mark.asyncio
    async def test_revoke_role_deletes_assignment(self) -> None:
        """revoke_role deletes the assignment and returns True."""
        existing = _make_assignment(self.user_id, self.role_id)

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.get = AsyncMock(return_value=existing)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.revoke_role(
                self.user_id, ScopeType.GLOBAL, None
            )

        assert result is True
        mock_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_role_returns_false_when_not_found(self) -> None:
        """revoke_role returns False when no assignment exists."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.revoke_role(
                self.user_id, ScopeType.GLOBAL, None
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_assign_role_no_session_raises(self) -> None:
        """assign_role raises RuntimeError when no session available."""
        with patch(
            "app.core.rbac_unified.get_unified_rbac_session", return_value=None
        ):
            with pytest.raises(RuntimeError, match="No database session"):
                await self.service.assign_role(
                    self.user_id, self.role_id, ScopeType.GLOBAL
                )


# ---------------------------------------------------------------------------
# Singleton Tests
# ---------------------------------------------------------------------------


class TestSingleton:
    """Tests for service singleton management."""

    def test_get_unified_rbac_service_creates_singleton(self) -> None:
        service = get_unified_rbac_service()
        assert isinstance(service, UnifiedRBACService)

    def test_set_unified_rbac_service_overrides(self) -> None:
        custom = UnifiedRBACService()
        set_unified_rbac_service(custom)
        assert get_unified_rbac_service() is custom

        # Reset
        set_unified_rbac_service(UnifiedRBACService())


# ---------------------------------------------------------------------------
# Refresh Permissions Cache Tests
# ---------------------------------------------------------------------------


class TestRefreshPermissionsCache:
    """Tests for refresh_permissions_cache method."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()

    @pytest.mark.asyncio
    async def test_refresh_permissions_cache_loads_roles(self) -> None:
        """refresh_permissions_cache loads role-permission mappings from DB."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("admin", "read"),
            ("admin", "write"),
            ("viewer", "read"),
        ]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            await self.service.refresh_permissions_cache()

        # Verify cache was populated
        perms = self.service._get_cached_permissions("admin")
        assert perms is not None
        assert "read" in perms
        assert "write" in perms
        assert self.service._get_cached_permissions("viewer") == ["read"]

    @pytest.mark.asyncio
    async def test_refresh_permissions_cache_clears_old_entries(self) -> None:
        """refresh_permissions_cache clears existing cache before loading."""
        # Seed old cache
        self.service._cache_permissions("old_role", ["old_perm"])

        mock_result = MagicMock()
        mock_result.all.return_value = [("admin", "read")]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            await self.service.refresh_permissions_cache()

        # Old entry should be gone
        assert self.service._get_cached_permissions("old_role") is None

    @pytest.mark.asyncio
    async def test_refresh_permissions_cache_returns_on_no_session(self) -> None:
        """refresh_permissions_cache returns early when no session available."""
        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=None,
        ):
            await self.service.refresh_permissions_cache()

        # Cache should remain empty
        assert self.service._permissions_cache == {}


# ---------------------------------------------------------------------------
# get_user_roles DB Path Tests
# ---------------------------------------------------------------------------


class TestGetUserRolesDBPath:
    """Tests for get_user_roles database query path (cache miss)."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()

    @pytest.mark.asyncio
    async def test_get_user_roles_queries_db_on_cache_miss(self) -> None:
        """get_user_roles queries DB when cache misses and caches result."""
        mock_result = MagicMock()
        mock_result.all.return_value = [("admin",), ("editor",)]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            roles = await self.service.get_user_roles(
                self.user_id, ScopeType.GLOBAL, None
            )

        assert roles == ["admin", "editor"]
        # Result should be cached
        cached = self.service._get_cached_assignments(
            self.user_id, ScopeType.GLOBAL, None
        )
        assert cached == ["admin", "editor"]

    @pytest.mark.asyncio
    async def test_get_user_roles_returns_empty_on_no_session(self) -> None:
        """get_user_roles returns [] when no session available (cache miss)."""
        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=None,
        ):
            roles = await self.service.get_user_roles(
                self.user_id, ScopeType.GLOBAL, None
            )

        assert roles == []

    @pytest.mark.asyncio
    async def test_get_user_roles_with_scope_id(self) -> None:
        """get_user_roles handles scoped queries with scope_id."""
        project_id = uuid4()
        mock_result = MagicMock()
        mock_result.all.return_value = [("project-editor",)]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            roles = await self.service.get_user_roles(
                self.user_id, ScopeType.PROJECT, project_id
            )

        assert roles == ["project-editor"]


# ---------------------------------------------------------------------------
# get_assignments_by_scope Tests
# ---------------------------------------------------------------------------


class TestGetAssignmentsByScope:
    """Tests for get_assignments_by_scope method."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()

    @pytest.mark.asyncio
    async def test_get_assignments_by_scope_returns_assignments(self) -> None:
        """get_assignments_by_scope returns matching assignments."""
        assignment = _make_assignment(uuid4(), uuid4(), ScopeType.PROJECT, uuid4())
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.get_assignments_by_scope(
                ScopeType.PROJECT, assignment.scope_id
            )

        assert len(result) == 1
        assert result[0] is assignment

    @pytest.mark.asyncio
    async def test_get_assignments_by_scope_global_no_scope_id(self) -> None:
        """get_assignments_by_scope handles global scope (scope_id=None)."""
        assignment = _make_assignment(uuid4(), uuid4(), ScopeType.GLOBAL, None)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.get_assignments_by_scope(
                ScopeType.GLOBAL, None
            )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_assignments_by_scope_returns_empty_on_no_session(
        self,
    ) -> None:
        """get_assignments_by_scope returns [] when no session available."""
        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=None,
        ):
            result = await self.service.get_assignments_by_scope(
                ScopeType.PROJECT, uuid4()
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_assignments_by_scope_type_only(self) -> None:
        """get_assignments_by_scope with scope_type only returns all assignments of that type."""
        project_id_1 = uuid4()
        project_id_2 = uuid4()
        a1 = _make_assignment(uuid4(), uuid4(), ScopeType.PROJECT, project_id_1)
        a2 = _make_assignment(uuid4(), uuid4(), ScopeType.PROJECT, project_id_2)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [a1, a2]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.get_assignments_by_scope(
                ScopeType.PROJECT, None
            )

        assert len(result) == 2
        assert result[0] is a1
        assert result[1] is a2


# ---------------------------------------------------------------------------
# get_all_user_assignments Tests
# ---------------------------------------------------------------------------


class TestGetAllUserAssignments:
    """Tests for get_all_user_assignments method."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()

    @pytest.mark.asyncio
    async def test_get_all_user_assignments_returns_all(self) -> None:
        """get_all_user_assignments returns all assignments for a user."""
        a1 = _make_assignment(self.user_id, uuid4(), ScopeType.GLOBAL, None)
        a2 = _make_assignment(self.user_id, uuid4(), ScopeType.PROJECT, uuid4())
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [a1, a2]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.get_all_user_assignments(self.user_id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_all_user_assignments_returns_empty_on_no_session(
        self,
    ) -> None:
        """get_all_user_assignments returns [] when no session available."""
        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=None,
        ):
            result = await self.service.get_all_user_assignments(self.user_id)

        assert result == []


# ---------------------------------------------------------------------------
# update_assignment Tests
# ---------------------------------------------------------------------------


class TestUpdateAssignment:
    """Tests for update_assignment method."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.assignment_id = uuid4()
        self.user_id = uuid4()
        self.role_id = uuid4()

    @pytest.mark.asyncio
    async def test_update_assignment_updates_role(self) -> None:
        """update_assignment updates role_id and returns the assignment."""
        existing = _make_assignment(self.user_id, self.role_id)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.get = AsyncMock(return_value=existing)
        mock_session.flush = AsyncMock()

        new_role_id = uuid4()

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.update_assignment(
                assignment_id=self.assignment_id,
                role_id=new_role_id,
            )

        assert result is existing
        assert existing.role_id == new_role_id

    @pytest.mark.asyncio
    async def test_update_assignment_updates_metadata(self) -> None:
        """update_assignment updates metadata and returns the assignment."""
        existing = _make_assignment(self.user_id, self.role_id)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.get = AsyncMock(return_value=existing)
        mock_session.flush = AsyncMock()

        new_metadata = {"authority_level": "HIGH"}

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.update_assignment(
                assignment_id=self.assignment_id,
                metadata=new_metadata,
            )

        assert result is existing
        assert existing.metadata_ == new_metadata

    @pytest.mark.asyncio
    async def test_update_assignment_updates_expires_at(self) -> None:
        """update_assignment updates expires_at timestamp."""
        existing = _make_assignment(self.user_id, self.role_id)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.get = AsyncMock(return_value=existing)
        mock_session.flush = AsyncMock()

        new_expires = datetime.now(UTC) + timedelta(days=30)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.update_assignment(
                assignment_id=self.assignment_id,
                expires_at=new_expires,
            )

        assert result is existing
        assert existing.expires_at == new_expires

    @pytest.mark.asyncio
    async def test_update_assignment_returns_none_when_not_found(self) -> None:
        """update_assignment returns None when assignment not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.update_assignment(
                assignment_id=self.assignment_id,
                role_id=uuid4(),
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_assignment_no_session_raises(self) -> None:
        """update_assignment raises RuntimeError when no session available."""
        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="No database session"):
                await self.service.update_assignment(
                    assignment_id=self.assignment_id,
                    role_id=uuid4(),
                )

    @pytest.mark.asyncio
    async def test_update_assignment_invalidates_cache(self) -> None:
        """update_assignment invalidates assignment cache for the user/scope."""
        project_id = uuid4()
        existing = _make_assignment(self.user_id, self.role_id, ScopeType.PROJECT, project_id)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.get = AsyncMock(return_value=existing)
        mock_session.flush = AsyncMock()

        # Seed cache
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, project_id, ["editor"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            await self.service.update_assignment(
                assignment_id=self.assignment_id,
                role_id=uuid4(),
            )

        # Cache should be invalidated
        assert (
            self.service._get_cached_assignments(
                self.user_id, ScopeType.PROJECT, project_id
            )
            is None
        )


# ---------------------------------------------------------------------------
# get_accessible_projects Tests
# ---------------------------------------------------------------------------


class TestGetAccessibleProjects:
    """Tests for get_accessible_projects method."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()

    @pytest.mark.asyncio
    async def test_admin_gets_all_projects(self) -> None:
        """Admin users receive all project IDs from the Project table."""
        project_ids = [uuid4(), uuid4(), uuid4()]

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )

        mock_result = MagicMock()
        mock_result.all.return_value = [(pid,) for pid in project_ids]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.get_accessible_projects(self.user_id)

        assert result == project_ids

    @pytest.mark.asyncio
    async def test_non_admin_gets_project_scoped_ids(self) -> None:
        """Non-admin users get distinct scope_ids from project-scoped assignments."""
        project_id_1 = uuid4()
        project_id_2 = uuid4()

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        mock_result = MagicMock()
        mock_result.all.return_value = [(project_id_1,), (project_id_2,)]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.get_accessible_projects(self.user_id)

        assert result == [project_id_1, project_id_2]

    @pytest.mark.asyncio
    async def test_non_admin_filters_none_scope_ids(self) -> None:
        """Non-admin path filters out None scope_ids from results."""
        project_id = uuid4()

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        mock_result = MagicMock()
        mock_result.all.return_value = [(project_id,), (None,)]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.get_accessible_projects(self.user_id)

        assert result == [project_id]

    @pytest.mark.asyncio
    async def test_no_session_returns_empty_list(self) -> None:
        """Returns empty list when no database session is available."""
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=None,
        ):
            result = await self.service.get_accessible_projects(self.user_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_no_session_non_admin_returns_empty_list(self) -> None:
        """Non-admin path also returns empty list without a session."""
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=None,
        ):
            result = await self.service.get_accessible_projects(self.user_id)

        assert result == []


# ---------------------------------------------------------------------------
# has_project_access Tests
# ---------------------------------------------------------------------------


class TestHasProjectAccess:
    """Tests for has_project_access convenience wrapper."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()

    @pytest.mark.asyncio
    async def test_delegates_to_has_permission(self) -> None:
        """has_project_access delegates to has_permission with PROJECT scope."""
        project_id = uuid4()
        self.service._cache_permissions("editor", ["project-write"])
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["editor"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, project_id, ["editor"]
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock())

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_project_access(
                self.user_id, project_id, "project-write"
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_denied_when_permission_missing(self) -> None:
        """has_project_access returns False when user lacks the permission."""
        project_id = uuid4()
        self.service._cache_permissions("viewer", ["project-read"])
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, project_id, ["viewer"]
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock())

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_project_access(
                self.user_id, project_id, "project-delete"
            )

        assert result is False


# ---------------------------------------------------------------------------
# get_project_role Tests
# ---------------------------------------------------------------------------


class TestGetProjectRole:
    """Tests for get_project_role method."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()

    @pytest.mark.asyncio
    async def test_admin_returns_project_admin(self) -> None:
        """Admin users always get 'project_admin' as their project role."""
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )

        result = await self.service.get_project_role(self.user_id, uuid4())
        assert result == "project_admin"

    @pytest.mark.asyncio
    async def test_non_admin_with_assignment_returns_role_name(self) -> None:
        """Non-admin user with a project assignment gets the role name."""
        project_id = uuid4()
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        mock_result = MagicMock()
        mock_result.first.return_value = ("project_admin",)
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.get_project_role(self.user_id, project_id)

        assert result == "project_admin"

    @pytest.mark.asyncio
    async def test_no_assignment_returns_none(self) -> None:
        """Returns None when user has no assignment for the project."""
        project_id = uuid4()
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.get_project_role(self.user_id, project_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_no_session_returns_none(self) -> None:
        """Returns None when no database session is available."""
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=None,
        ):
            result = await self.service.get_project_role(self.user_id, uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# get_user_permissions Tests
# ---------------------------------------------------------------------------


class TestGetUserPermissions:
    """Tests for get_user_permissions method."""

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()

    @pytest.mark.asyncio
    async def test_admin_returns_wildcard(self) -> None:
        """Admin role returns ['*'] wildcard permissions."""
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )

        result = await self.service.get_user_permissions(
            self.user_id, ScopeType.GLOBAL, None
        )

        assert result == ["*"]

    @pytest.mark.asyncio
    async def test_regular_role_returns_sorted_deduplicated_permissions(self) -> None:
        """Regular roles return sorted, deduplicated permissions from cache."""
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["editor"]
        )
        self.service._cache_permissions("editor", ["project-write", "project-read"])

        result = await self.service.get_user_permissions(
            self.user_id, ScopeType.GLOBAL, None
        )

        assert result == ["project-read", "project-write"]

    @pytest.mark.asyncio
    async def test_no_cached_permissions_returns_empty(self) -> None:
        """Returns empty list when role has no cached permissions."""
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        # Do not seed the permissions cache for "viewer"

        result = await self.service.get_user_permissions(
            self.user_id, ScopeType.GLOBAL, None
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_combines_global_and_scoped_permissions(self) -> None:
        """Combines permissions from global role and scoped role."""
        project_id = uuid4()
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, project_id, ["editor"]
        )
        self.service._cache_permissions("viewer", ["project-read"])
        self.service._cache_permissions("editor", ["project-write"])

        result = await self.service.get_user_permissions(
            self.user_id, ScopeType.PROJECT, project_id
        )

        assert result == ["project-read", "project-write"]

    @pytest.mark.asyncio
    async def test_deduplicates_across_roles(self) -> None:
        """Deduplicates permissions that appear in multiple roles."""
        project_id = uuid4()
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, project_id, ["editor"]
        )
        self.service._cache_permissions("viewer", ["project-read", "project-write"])
        self.service._cache_permissions("editor", ["project-write"])

        result = await self.service.get_user_permissions(
            self.user_id, ScopeType.PROJECT, project_id
        )

        # "project-write" appears in both roles but only once in output
        assert result == ["project-read", "project-write"]

    @pytest.mark.asyncio
    async def test_global_scope_skips_scoped_lookup(self) -> None:
        """When scope_type is GLOBAL, does not look up scoped roles."""
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["editor"]
        )
        self.service._cache_permissions("editor", ["project-read"])

        # Should not query for scoped roles since scope_type is GLOBAL
        result = await self.service.get_user_permissions(
            self.user_id, ScopeType.GLOBAL, None
        )

        assert result == ["project-read"]

    @pytest.mark.asyncio
    async def test_scoped_admin_returns_wildcard(self) -> None:
        """Admin in a scoped role still returns wildcard."""
        project_id = uuid4()
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, project_id, ["admin"]
        )

        result = await self.service.get_user_permissions(
            self.user_id, ScopeType.PROJECT, project_id
        )

        assert result == ["*"]
