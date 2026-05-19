"""Security tests for UnifiedRBACService - adversarial edge cases.

Tests cover:
- Metadata injection via arbitrary authority_level values in JSONB
- Expired role denial (documenting known gap: expires_at not filtered)
- Cache poisoning and invalidation integrity
- Scope isolation and privilege escalation prevention
- Admin bypass verification

TD-096: Security hardening tests for the unified RBAC system.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.rbac_unified import (
    ScopeType,
    UnifiedRBACService,
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
    expires_at: datetime | None = None,
) -> MagicMock:
    """Create a mock UserRoleAssignment instance for security testing."""
    a = MagicMock(spec=UserRoleAssignment)
    a.id = uuid4()
    a.user_id = user_id
    a.role_id = role_id
    a.scope_type = scope_type
    a.scope_id = scope_id
    a.metadata_ = metadata
    a.granted_by = None
    a.granted_at = datetime.now(UTC)
    a.expires_at = expires_at
    a.created_at = datetime.now(UTC)
    a.updated_at = datetime.now(UTC)
    return a


# ---------------------------------------------------------------------------
# 1. Metadata Injection Tests
# ---------------------------------------------------------------------------


class TestMetadataInjection:
    """Tests for adversarial authority_level values in metadata_ JSONB.

    The authority_level hierarchy is {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}.
    Any value not in this hierarchy maps to level 0, which is always denied.
    These tests verify that injecting arbitrary, malformed, or hostile values
    into the JSONB metadata_ field cannot elevate privileges.
    """

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()
        self.role_id = uuid4()

    @pytest.mark.asyncio
    async def test_arbitrary_authority_level_string_denied(self) -> None:
        """An invented authority string like 'SUPER_ADMIN' maps to 0 and is denied."""
        assignment = _make_assignment(
            self.user_id,
            self.role_id,
            ScopeType.CHANGE_ORDER,
            uuid4(),
            metadata={"authority_level": "SUPER_ADMIN"},
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment]
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Not admin globally
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "LOW", assignment.scope_id
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_empty_string_authority_denied(self) -> None:
        """Empty string authority_level maps to 0 and is denied."""
        assignment = _make_assignment(
            self.user_id,
            self.role_id,
            ScopeType.CHANGE_ORDER,
            uuid4(),
            metadata={"authority_level": ""},
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment]
        mock_session.execute = AsyncMock(return_value=mock_result)

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "LOW", assignment.scope_id
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_case_sensitive_authority_denied(self) -> None:
        """Lowercase 'high' is not in the hierarchy (keys are uppercase) and is denied."""
        assignment = _make_assignment(
            self.user_id,
            self.role_id,
            ScopeType.CHANGE_ORDER,
            uuid4(),
            metadata={"authority_level": "high"},
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment]
        mock_session.execute = AsyncMock(return_value=mock_result)

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "HIGH", assignment.scope_id
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_numeric_authority_denied(self) -> None:
        """An integer value (e.g., 3) for authority_level is not a valid hierarchy key."""
        assignment = _make_assignment(
            self.user_id,
            self.role_id,
            ScopeType.CHANGE_ORDER,
            uuid4(),
            metadata={"authority_level": 3},
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment]
        mock_session.execute = AsyncMock(return_value=mock_result)

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "LOW", assignment.scope_id
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_null_metadata_denied(self) -> None:
        """Null metadata_ has no authority_level key and is denied."""
        assignment = _make_assignment(
            self.user_id,
            self.role_id,
            ScopeType.CHANGE_ORDER,
            uuid4(),
            metadata=None,
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment]
        mock_session.execute = AsyncMock(return_value=mock_result)

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "LOW", assignment.scope_id
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_missing_authority_key_denied(self) -> None:
        """metadata_ with unrelated keys but no authority_level is denied."""
        assignment = _make_assignment(
            self.user_id,
            self.role_id,
            ScopeType.CHANGE_ORDER,
            uuid4(),
            metadata={"other_key": "value", "another": 42},
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment]
        mock_session.execute = AsyncMock(return_value=mock_result)

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "LOW", assignment.scope_id
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_sql_injection_in_authority_denied(self) -> None:
        """SQL injection strings in authority_level are not in hierarchy and are denied.

        The authority check is a dict lookup, not a SQL query, so injection
        is not exploitable — but this test confirms the defense in depth.
        """
        assignment = _make_assignment(
            self.user_id,
            self.role_id,
            ScopeType.CHANGE_ORDER,
            uuid4(),
            metadata={"authority_level": "'; DROP TABLE users;--"},
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment]
        mock_session.execute = AsyncMock(return_value=mock_result)

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "LOW", assignment.scope_id
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_very_long_authority_string_denied(self) -> None:
        """A 10000-character string for authority_level is not in hierarchy and is denied."""
        long_string = "A" * 10000
        assignment = _make_assignment(
            self.user_id,
            self.role_id,
            ScopeType.CHANGE_ORDER,
            uuid4(),
            metadata={"authority_level": long_string},
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment]
        mock_session.execute = AsyncMock(return_value=mock_result)

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "LOW", assignment.scope_id
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_valid_authority_with_extra_metadata_still_works(self) -> None:
        """Valid authority_level works correctly even with extra metadata keys present.

        The JSONB field may contain other application data alongside
        authority_level — only the authority_level key is read.
        """
        assignment = _make_assignment(
            self.user_id,
            self.role_id,
            ScopeType.CHANGE_ORDER,
            uuid4(),
            metadata={"authority_level": "HIGH", "extra": "data", "nested": {"x": 1}},
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment]
        mock_session.execute = AsyncMock(return_value=mock_result)

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "HIGH", assignment.scope_id
            )

        assert result is True


# ---------------------------------------------------------------------------
# 2. Expired Role Denial Tests
# ---------------------------------------------------------------------------


class TestExpiredRoleDenial:
    """Tests for expires_at behavior in role assignments.

    KNOWN GAP: The get_user_roles() method does NOT filter by expires_at.
    Expired assignments still return active role names, meaning expired
    roles continue to grant access. The xfail tests document this gap.
    """

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()
        self.role_id = uuid4()

    @pytest.mark.xfail(
        reason="expires_at not filtered in get_user_roles query — known security gap",
        strict=True,
    )
    @pytest.mark.asyncio
    async def test_expired_assignment_denied(self) -> None:
        """An assignment with expires_at in the past should be denied.

        The get_user_roles query has no WHERE expires_at > NOW() clause,
        so expired assignments currently still grant access. This test
        documents the expected correct behavior.
        """
        # Assignment expired 1 hour ago (not used in mock — documents intent)
        expired_at = datetime.now(UTC) - timedelta(hours=1)
        _make_assignment(
            self.user_id,
            self.role_id,
            ScopeType.GLOBAL,
            None,
            expires_at=expired_at,
        )

        # The DB query returns the role name despite expiration
        mock_result = MagicMock()
        mock_result.all.return_value = [("editor",)]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Seed the permission cache so editor has project-write
        self.service._cache_permissions("editor", ["project-write"])

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            # This SHOULD return False because the assignment is expired,
            # but currently returns True (hence xfail)
            result = await self.service.has_permission(
                self.user_id, "project-write", ScopeType.GLOBAL, None
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_future_expiration_still_grants(self) -> None:
        """An assignment with future expires_at continues to grant access.

        Since expires_at is never checked, future-dated expirations work
        the same as no expiration — access is granted.
        """
        # Future-dated expiration (not used in mock — documents intent)
        datetime.now(UTC) + timedelta(days=30)

        # The DB returns the role despite the future expiration
        mock_result = MagicMock()
        mock_result.all.return_value = [("editor",)]
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        self.service._cache_permissions("editor", ["project-write"])

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_permission(
                self.user_id, "project-write", ScopeType.GLOBAL, None
            )

        assert result is True


# ---------------------------------------------------------------------------
# 3. Cache Poisoning and Invalidation Tests
# ---------------------------------------------------------------------------


class TestCachePoisoningAndInvalidation:
    """Tests for cache integrity under adversarial conditions.

    The two-layer cache (permissions: 1h TTL, assignments: 5min TTL) must
    prevent stale data from being served after invalidation, and TTL must
    cause automatic expiration of outdated entries.
    """

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()

    @pytest.mark.asyncio
    async def test_stale_permissions_cache_denies_after_role_update(self) -> None:
        """After a role's permissions change, old cached permissions must not grant access.

        Simulates: editor role is cached with ['read'], then the role is
        updated to lose 'write'. After invalidation, 'write' must be denied.
        """
        # Seed: editor only has "read"
        self.service._cache_permissions("editor", ["read"])
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["editor"]
        )

        # Verify write is denied before any change
        assert (
            self.service._check_permission_from_roles(["editor"], "write") is False
        )

        # Simulate role update: clear permissions cache for editor
        # (refresh_permissions_cache does this in production)
        if "editor" in self.service._permissions_cache:
            del self.service._permissions_cache["editor"]

        # Cache miss for editor permissions → _check_permission_from_roles returns False
        assert (
            self.service._check_permission_from_roles(["editor"], "read") is False
        )
        assert (
            self.service._check_permission_from_roles(["editor"], "write") is False
        )

    @pytest.mark.asyncio
    async def test_invalidation_prevents_stale_access(self) -> None:
        """After invalidating assignment cache, stale roles are not served.

        Assigns 'editor' role, caches it, invalidates, then verifies
        the cache no longer returns the stale role list.
        """
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["editor"]
        )

        # Verify cached
        assert (
            self.service._get_cached_assignments(self.user_id, ScopeType.GLOBAL, None)
            == ["editor"]
        )

        # Invalidate all assignments for this user
        self.service._invalidate_assignment_cache(self.user_id)

        # Cache should be empty
        assert (
            self.service._get_cached_assignments(self.user_id, ScopeType.GLOBAL, None)
            is None
        )

    @pytest.mark.asyncio
    async def test_partial_invalidation_preserves_other_scopes(self) -> None:
        """Invalidating project scope does not clear global scope cache.

        Scope-specific invalidation must only affect the targeted scope,
        preserving caches for other scopes the user may have.
        """
        project_id = uuid4()

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, project_id, ["editor"]
        )

        # Invalidate only project scope
        self.service._invalidate_assignment_cache(
            self.user_id, ScopeType.PROJECT, project_id
        )

        # Global cache must survive
        assert (
            self.service._get_cached_assignments(self.user_id, ScopeType.GLOBAL, None)
            == ["admin"]
        )
        # Project cache must be gone
        assert (
            self.service._get_cached_assignments(
                self.user_id, ScopeType.PROJECT, project_id
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_concurrent_invalidation_no_stale_reads(self) -> None:
        """Rapid invalidation followed by read does not serve stale data.

        Simulates a race where invalidation happens between two reads.
        The second read must not return the pre-invalidation value.
        """
        # Seed cache
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["editor"]
        )

        # First read succeeds
        assert (
            self.service._get_cached_assignments(self.user_id, ScopeType.GLOBAL, None)
            == ["editor"]
        )

        # Invalidate
        self.service._invalidate_assignment_cache(self.user_id)

        # Second read must return None — no stale data
        assert (
            self.service._get_cached_assignments(self.user_id, ScopeType.GLOBAL, None)
            is None
        )

    def test_expired_assignment_cache_auto_expires(self) -> None:
        """Assignment cache entries older than TTL (5 min) auto-expire on read.

        Verifies that manually aging a cache entry past the TTL causes
        _get_cached_assignments to return None (cache miss).
        """
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["editor"]
        )

        # Manually age the entry past the 5-minute TTL
        cache_key = (self.user_id, ScopeType.GLOBAL, None)
        stale_time = datetime.now(UTC) - timedelta(minutes=6)
        self.service._assignment_cache[cache_key] = (["editor"], stale_time)

        result = self.service._get_cached_assignments(
            self.user_id, ScopeType.GLOBAL, None
        )
        assert result is None

    def test_permissions_cache_ttl_enforcement(self) -> None:
        """Permissions cache entries older than TTL (1 hour) auto-expire on read.

        Verifies that manually aging a cache entry past the TTL causes
        _get_cached_permissions to return None (cache miss).
        """
        self.service._cache_permissions("editor", ["read", "write"])

        # Manually age the entry past the 1-hour TTL
        stale_time = datetime.now(UTC) - timedelta(hours=2)
        self.service._permissions_cache["editor"] = (["read", "write"], stale_time)

        result = self.service._get_cached_permissions("editor")
        assert result is None


# ---------------------------------------------------------------------------
# 4. Scope Isolation Tests
# ---------------------------------------------------------------------------


class TestScopeIsolation:
    """Tests that scope boundaries are enforced and cannot be crossed.

    Roles assigned in one scope must not leak permissions into another scope.
    This prevents privilege escalation through scope manipulation.
    """

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()

    @pytest.mark.asyncio
    async def test_global_role_does_not_grant_project_scoped_permission(self) -> None:
        """A global 'viewer' role only grants permissions viewer has, not project-specific ones.

        The has_permission check tries global roles first, then scoped roles.
        A global viewer with only 'project-read' cannot get 'project-write'
        just because they have a global role.
        """
        self.service._cache_permissions("viewer", ["project-read"])
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        # No project-scoped assignment — DB returns empty on cache miss
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_permission(
                self.user_id, "project-write", ScopeType.PROJECT, uuid4()
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_project_scoped_role_does_not_leak_to_other_project(self) -> None:
        """Role assigned for project A does not grant access to project B.

        Scope IDs are part of the cache key and the DB query filter,
        so project-scoped roles are isolated by scope_id.
        """
        project_a = uuid4()
        project_b = uuid4()

        self.service._cache_permissions("editor", ["project-write"])
        # User has editor role on project A only
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, project_a, ["editor"]
        )
        # No assignment for project B — cache miss triggers DB query
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_permission(
                self.user_id, "project-write", ScopeType.PROJECT, project_b
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_change_order_scope_does_not_grant_project_permissions(self) -> None:
        """A change_order scoped role does not grant project-level permissions.

        The has_permission method checks the scope_type parameter.
        A role assigned in CHANGE_ORDER scope is only looked up when
        scope_type is CHANGE_ORDER, not PROJECT.
        """
        change_order_id = uuid4()

        self.service._cache_permissions("approver", ["co-approve"])
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.CHANGE_ORDER, change_order_id, ["approver"]
        )

        # No project assignment — cache miss triggers DB query returning empty
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_permission(
                self.user_id, "co-approve", ScopeType.PROJECT, uuid4()
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_scope_type_cannot_be_escalated_via_assignment(self) -> None:
        """An invalid scope_type in an assignment does not grant permissions.

        If an assignment somehow has a scope_type not in {global, project,
        change_order}, it should not match any valid scope check.
        """
        fake_scope = "super_admin"
        self.service._cache_assignments(self.user_id, fake_scope, None, ["editor"])
        self.service._cache_permissions("editor", ["project-write"])

        # The assignment is cached under a fake scope type.
        # has_permission checks GLOBAL and PROJECT scopes, which won't match.
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        self.service._cache_permissions("viewer", ["project-read"])

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=MagicMock(),
        ):
            result = await self.service.has_permission(
                self.user_id, "project-write", ScopeType.GLOBAL, None
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_scope_id_mismatch_denied(self) -> None:
        """Correct scope_type but wrong scope_id does not grant permission.

        The cache key includes (user_id, scope_type, scope_id).
        A different scope_id causes a cache miss, and the DB query
        filters by the correct scope_id, returning no roles.
        """
        correct_project = uuid4()
        wrong_project = uuid4()

        self.service._cache_permissions("editor", ["project-write"])
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, correct_project, ["editor"]
        )

        # Query for wrong project returns empty
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_permission(
                self.user_id, "project-write", ScopeType.PROJECT, wrong_project
            )

        assert result is False


# ---------------------------------------------------------------------------
# 5. Admin Bypass Verification Tests
# ---------------------------------------------------------------------------


class TestAdminBypassVerification:
    """Tests for admin bypass behavior — the 'admin' global role short-circuits.

    Admin bypass is a high-privilege path that must be precisely controlled:
    - Only the exact string "admin" in global roles triggers bypass
    - Admin has all authority levels
    - Admin accesses all projects
    - Case matters: "Admin" does not bypass
    - Admin must be a GLOBAL role, not a scoped role
    """

    def setup_method(self) -> None:
        self.service = UnifiedRBACService()
        self.user_id = uuid4()

    @pytest.mark.asyncio
    async def test_admin_bypasses_permission_check(self) -> None:
        """Admin role bypasses all specific permission checks without hitting the DB.

        The has_permission method checks 'admin' in global_roles before
        any permission lookup, returning True immediately.
        """
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )
        # No permissions cached for admin — bypasses the cache entirely

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=MagicMock(),
        ):
            result = await self.service.has_permission(
                self.user_id, "any-permission-that-does-not-exist", ScopeType.GLOBAL, None
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_admin_has_all_authority_levels(self) -> None:
        """Admin global role grants CRITICAL authority level without change_order assignment.

        The has_authority_level method checks global roles for 'admin'
        after checking change_order assignments. Admin always passes.
        """
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        # No change_order assignments needed — admin bypasses
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=mock_session,
        ):
            result = await self.service.has_authority_level(
                self.user_id, "CRITICAL", uuid4()
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_admin_has_project_access_to_all_projects(self) -> None:
        """Admin with global role can access any project, even without explicit assignment.

        has_project_access delegates to has_permission, which checks global
        roles first. Admin in global roles bypasses all checks.
        """
        random_project = uuid4()

        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["admin"]
        )

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=MagicMock(),
        ):
            result = await self.service.has_project_access(
                self.user_id, random_project, "any-permission"
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_admin_role_name_case_sensitive(self) -> None:
        """'Admin' (capital A) does NOT trigger bypass — role names are exact match.

        The check is `"admin" in global_roles`, which is case-sensitive.
        Any variation in casing must not bypass.
        """
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["Admin"]
        )
        # Admin with capital A has no permissions cached
        self.service._cache_permissions("Admin", [])

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=MagicMock(),
        ):
            result = await self.service.has_permission(
                self.user_id, "project-read", ScopeType.GLOBAL, None
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_admin_alone_in_scoped_assignment_does_not_bypass(self) -> None:
        """'admin' role in a scoped assignment (not global) does NOT bypass.

        The bypass check only inspects global_roles. An admin role
        assigned at project or change_order scope does not trigger
        the admin bypass.
        """
        project_id = uuid4()

        # User has 'viewer' globally and 'admin' only at project scope
        self.service._cache_assignments(
            self.user_id, ScopeType.GLOBAL, None, ["viewer"]
        )
        self.service._cache_assignments(
            self.user_id, ScopeType.PROJECT, project_id, ["admin"]
        )
        self.service._cache_permissions("viewer", ["project-read"])
        # admin has no specific permissions in cache (bypass would skip this)

        with patch(
            "app.core.rbac_unified.get_unified_rbac_session",
            return_value=MagicMock(),
        ):
            # Scoped 'admin' should not bypass — global 'viewer' lacks write
            result = await self.service.has_permission(
                self.user_id, "project-delete", ScopeType.PROJECT, project_id
            )

        assert result is False
