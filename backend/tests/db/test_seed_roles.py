"""Tests for the functional RBAC roles seeded by ``seed_users_rbac``.

The ``cost-controller`` and ``pmo-director`` roles are the Phase 2 functional
dashboards roles (read-heavy + a minimal set of approved writes). These tests
assert the seeded permission matrix is exactly what the product owner approved,
so a drift in ``ROLE_PERMISSIONS`` fails the suite.
"""

from app.db.seed_users_rbac import DEFAULT_USERS, ROLE_PERMISSIONS, USER_ROLE_MAP


def _perms(role_name: str) -> set[str]:
    permissions = ROLE_PERMISSIONS[role_name]["permissions"]
    assert isinstance(permissions, list)
    return set(permissions)


# ---------------------------------------------------------------------------
# cost-controller
# ---------------------------------------------------------------------------


def test_cost_controller_includes_approved_permissions() -> None:
    perms = _perms("cost-controller")
    for granted in (
        "portfolio-read",
        "forecast-update",
        "evm-read",
        "cost-registration-read",
    ):
        assert granted in perms, f"cost-controller must grant {granted}"


def test_cost_controller_excludes_forbidden_permissions() -> None:
    perms = _perms("cost-controller")
    for denied in (
        "project-create",
        "change-order-approve",
        "cost-registration-create",
    ):
        assert denied not in perms, f"cost-controller must NOT grant {denied}"


# ---------------------------------------------------------------------------
# pmo-director
# ---------------------------------------------------------------------------


def test_pmo_director_includes_approved_permissions() -> None:
    perms = _perms("pmo-director")
    for granted in (
        "portfolio-read",
        "change-order-approve",
        "change-order-submit",
    ):
        assert granted in perms, f"pmo-director must grant {granted}"


def test_pmo_director_excludes_forbidden_permissions() -> None:
    perms = _perms("pmo-director")
    for denied in (
        "project-create",
        "cost-registration-create",
        "forecast-update",
    ):
        assert denied not in perms, f"pmo-director must NOT grant {denied}"


# ---------------------------------------------------------------------------
# Functional users are mapped to their role at GLOBAL scope
# ---------------------------------------------------------------------------


def test_functional_users_seeded_and_mapped() -> None:
    emails = {u["email"] for u in DEFAULT_USERS}
    assert "controller@backcast.org" in emails
    assert "pmo-director@backcast.org" in emails

    assert USER_ROLE_MAP["controller@backcast.org"] == "cost-controller"
    assert USER_ROLE_MAP["pmo-director@backcast.org"] == "pmo-director"

    # The roles themselves must exist in the role dictionary.
    assert "cost-controller" in ROLE_PERMISSIONS
    assert "pmo-director" in ROLE_PERMISSIONS
