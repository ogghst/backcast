"""UnifiedRBACService singleton reset for test isolation (TD-115).

``reset_unified_rbac_service()`` drops the process-wide singleton so its
in-memory permission/assignment caches cannot leak between tests.
"""

from datetime import UTC, datetime

from app.core.rbac_unified import (
    get_unified_rbac_service,
    reset_unified_rbac_service,
)


def test_get_returns_singleton_within_a_run() -> None:
    """Repeated gets return the same instance (it really is a singleton)."""
    first = get_unified_rbac_service()
    second = get_unified_rbac_service()
    assert first is second


def test_reset_yields_a_fresh_instance() -> None:
    """After reset, get constructs a brand-new instance."""
    first = get_unified_rbac_service()
    reset_unified_rbac_service()
    second = get_unified_rbac_service()
    assert first is not second


def test_reset_clears_poisoned_caches() -> None:
    """Cache state written before a reset does not survive the reset."""
    service = get_unified_rbac_service()
    # Simulate a prior test polluting the in-memory permission cache.
    service._permissions_cache["stale_role"] = (["leaked_perm"], datetime.now(UTC))  # noqa: SLF001

    reset_unified_rbac_service()
    fresh = get_unified_rbac_service()

    assert fresh._permissions_cache == {}  # noqa: SLF001
    assert fresh._assignment_cache == {}  # noqa: SLF001
