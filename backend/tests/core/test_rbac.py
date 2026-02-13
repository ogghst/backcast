"""Unit tests for RBAC service.

Tests the JsonRBACService implementation following TDD approach.
"""

import json
import tempfile
from pathlib import Path

import pytest

from app.core.rbac import JsonRBACService


class TestJsonRBACService:
    """Test suite for JsonRBACService."""

    @pytest.fixture
    def rbac_config(self) -> dict:
        """Sample RBAC configuration for testing."""
        return {
            "roles": {
                "admin": {
                    "permissions": [
                        "user-read",
                        "user-create",
                        "user-update",
                        "user-delete",
                        "department-read",
                        "department-create",
                        "department-update",
                        "department-delete",
                    ]
                },
                "manager": {
                    "permissions": [
                        "user-read",
                        "user-update",
                        "department-read",
                        "department-create",
                        "department-update",
                    ]
                },
                "viewer": {"permissions": ["user-read", "department-read"]},
            }
        }

    @pytest.fixture
    def rbac_service(self, rbac_config: dict) -> JsonRBACService:
        """Create a JsonRBACService instance with test configuration."""
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(rbac_config, f)
            config_path = f.name

        service = JsonRBACService(config_path=Path(config_path))
        yield service

        # Cleanup
        Path(config_path).unlink()

    # 🔴 RED: Test 1 - has_role with direct match
    def test_has_role_direct_match(self, rbac_service: JsonRBACService) -> None:
        """Test that user role in allowed roles returns True."""
        # Arrange
        user_role = "admin"
        required_roles = ["admin", "manager"]

        # Act
        result = rbac_service.has_role(user_role, required_roles)

        # Assert
        assert result is True

    # 🔴 RED: Test 2 - has_role with no match
    def test_has_role_no_match(self, rbac_service: JsonRBACService) -> None:
        """Test that user role not in allowed roles returns False."""
        # Arrange
        user_role = "viewer"
        required_roles = ["admin"]

        # Act
        result = rbac_service.has_role(user_role, required_roles)

        # Assert
        assert result is False

    # 🔴 RED: Test 3 - has_role with empty required roles
    def test_has_role_empty_required_roles(self, rbac_service: JsonRBACService) -> None:
        """Test that empty required roles returns False."""
        # Arrange
        user_role = "admin"
        required_roles: list[str] = []

        # Act
        result = rbac_service.has_role(user_role, required_roles)

        # Assert
        assert result is False

    # 🔴 RED: Test 4 - has_permission direct match
    def test_has_permission_direct_match(self, rbac_service: JsonRBACService) -> None:
        """Test that role with permission returns True."""
        # Arrange
        user_role = "admin"
        required_permission = "user-delete"

        # Act
        result = rbac_service.has_permission(user_role, required_permission)

        # Assert
        assert result is True

    # 🔴 RED: Test 5 - has_permission no match
    def test_has_permission_no_match(self, rbac_service: JsonRBACService) -> None:
        """Test that role without permission returns False."""
        # Arrange
        user_role = "viewer"
        required_permission = "user-delete"

        # Act
        result = rbac_service.has_permission(user_role, required_permission)

        # Assert
        assert result is False

    # 🔴 RED: Test 6 - has_permission unknown role
    def test_has_permission_unknown_role(self, rbac_service: JsonRBACService) -> None:
        """Test that unknown role returns False."""
        # Arrange
        user_role = "unknown_role"
        required_permission = "read"

        # Act
        result = rbac_service.has_permission(user_role, required_permission)

        # Assert
        assert result is False

    # 🔴 RED: Test 7 - get_user_permissions
    def test_get_user_permissions(self, rbac_service: JsonRBACService) -> None:
        """Test that get_user_permissions returns all role permissions."""
        # Arrange
        user_role = "admin"
        expected_permissions = [
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
        result = rbac_service.get_user_permissions(user_role)

        # Assert
        assert result == expected_permissions

    # 🔴 RED: Test 8 - get_user_permissions unknown role
    def test_get_user_permissions_unknown_role(
        self, rbac_service: JsonRBACService
    ) -> None:
        """Test that unknown role returns empty permissions list."""
        # Arrange
        user_role = "unknown_role"

        # Act
        result = rbac_service.get_user_permissions(user_role)

        # Assert
        assert result == []

    # 🔴 RED: Test 9 - JSON file loading
    def test_json_file_loading(self, rbac_config: dict) -> None:
        """Test that JSON configuration loads correctly."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(rbac_config, f)
            config_path = Path(f.name)

        # Act
        service = JsonRBACService(config_path=config_path)

        # Assert
        assert service.has_role("admin", ["admin"]) is True
        assert service.has_permission("manager", "department-update") is True

        # Cleanup
        config_path.unlink()

    # 🔴 RED: Test 10 - Invalid JSON file
    def test_invalid_json_file(self) -> None:
        """Test that invalid JSON raises appropriate error."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            config_path = Path(f.name)

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            JsonRBACService(config_path=config_path)

        # Cleanup
        config_path.unlink()

    # 🔴 RED: Test 11 - Missing JSON file
    def test_missing_json_file(self) -> None:
        """Test that missing JSON file raises FileNotFoundError."""
        # Arrange
        config_path = Path("/nonexistent/path/rbac.json")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            JsonRBACService(config_path=config_path)
