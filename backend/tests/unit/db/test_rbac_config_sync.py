"""CI-sync test for RBAC config file parity.

Validates that seed/rbac_roles.json and config/rbac.json contain
identical role and permission definitions. The seed file is authoritative.
"""

import json
from pathlib import Path

import pytest

# Resolve paths relative to the backend directory
BACKEND_DIR = Path(__file__).parent.parent.parent.parent
SEED_RBAC_FILE = BACKEND_DIR / "seed" / "rbac_roles.json"
CONFIG_RBAC_FILE = BACKEND_DIR / "config" / "rbac.json"


class TestRBACConfigSync:
    """Ensure seed/rbac_roles.json and config/rbac.json stay synchronized."""

    @pytest.fixture()
    def seed_roles(self) -> dict[str, list[str]]:
        """Load role permission sets from seed file."""
        with SEED_RBAC_FILE.open() as f:
            data = json.load(f)
        roles: dict[str, list[str]] = {}
        for role_name, role_def in data.get("roles", {}).items():
            roles[role_name] = sorted(role_def.get("permissions", []))
        return roles

    @pytest.fixture()
    def config_roles(self) -> dict[str, list[str]]:
        """Load role permission sets from config file."""
        with CONFIG_RBAC_FILE.open() as f:
            data = json.load(f)
        roles: dict[str, list[str]] = {}
        for role_name, role_def in data.get("roles", {}).items():
            roles[role_name] = sorted(role_def.get("permissions", []))
        return roles

    def test_same_role_names(
        self, seed_roles: dict[str, list[str]], config_roles: dict[str, list[str]]
    ) -> None:
        """T-003a: Both files define the exact same set of role names."""
        seed_names = set(seed_roles.keys())
        config_names = set(config_roles.keys())

        missing_in_config = seed_names - config_names
        extra_in_config = config_names - seed_names

        assert not missing_in_config, (
            f"Roles missing from config/rbac.json: {missing_in_config}"
        )
        assert not extra_in_config, (
            f"Extra roles in config/rbac.json: {extra_in_config}"
        )

    def test_same_permissions_per_role(
        self, seed_roles: dict[str, list[str]], config_roles: dict[str, list[str]]
    ) -> None:
        """T-003b: Each role has the exact same permission set in both files."""
        differences: list[str] = []
        for role_name in seed_roles:
            if role_name not in config_roles:
                continue  # Caught by test_same_role_names
            if seed_roles[role_name] != config_roles[role_name]:
                seed_only = set(seed_roles[role_name]) - set(config_roles[role_name])
                config_only = set(config_roles[role_name]) - set(seed_roles[role_name])
                details: list[str] = []
                if seed_only:
                    details.append(f"in seed only: {sorted(seed_only)}")
                if config_only:
                    details.append(f"in config only: {sorted(config_only)}")
                differences.append(f"  {role_name}: {', '.join(details)}")

        assert not differences, (
            "Permission mismatches between seed and config:\n" + "\n".join(differences)
        )

    def test_change_order_approver_exists_in_seed(self) -> None:
        """T-002: seed/rbac_roles.json contains change_order_approver with 7 permissions."""
        with SEED_RBAC_FILE.open() as f:
            data = json.load(f)

        roles = data.get("roles", {})
        assert "change_order_approver" in roles, (
            "change_order_approver role missing from seed/rbac_roles.json"
        )

        permissions = roles["change_order_approver"].get("permissions", [])
        assert len(permissions) == 8, (
            f"change_order_approver should have 8 permissions, got {len(permissions)}: "
            f"{sorted(permissions)}"
        )

    def test_change_order_approver_exists_in_config(self) -> None:
        """T-002b: config/rbac.json contains change_order_approver with 8 permissions."""
        with CONFIG_RBAC_FILE.open() as f:
            data = json.load(f)

        roles = data.get("roles", {})
        assert "change_order_approver" in roles, (
            "change_order_approver role missing from config/rbac.json"
        )

        permissions = roles["change_order_approver"].get("permissions", [])
        assert len(permissions) == 8, (
            f"change_order_approver should have 8 permissions, got {len(permissions)}: "
            f"{sorted(permissions)}"
        )

    def test_no_contributor_role_in_users_json(self) -> None:
        """Verify no user in seed/users.json has role 'contributor'."""
        users_file = BACKEND_DIR / "seed" / "users.json"
        with users_file.open() as f:
            users = json.load(f)

        contributor_users = [
            u["email"] for u in users if u.get("role") == "contributor"
        ]
        assert not contributor_users, (
            f"Users with 'contributor' role found: {contributor_users}. "
            "All should be 'manager'."
        )
