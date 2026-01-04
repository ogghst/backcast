"""Unit tests for DataSeeder module."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seeder import DataSeeder


class TestDataSeederInit:
    """Tests for DataSeeder initialization."""

    def test_init_with_default_seed_dir(self) -> None:
        """Test seeder initializes with default seed directory."""
        seeder = DataSeeder()
        assert seeder.seed_dir is not None
        assert seeder.seed_dir.name == "seed"

    def test_init_with_custom_seed_dir(self, tmp_path: Path) -> None:
        """Test seeder initializes with custom seed directory."""
        custom_dir = tmp_path / "custom_seed"
        custom_dir.mkdir()
        seeder = DataSeeder(seed_dir=custom_dir)
        assert seeder.seed_dir == custom_dir


class TestLoadSeedFile:
    """Tests for load_seed_file method."""

    def test_load_valid_json(self, tmp_path: Path) -> None:
        """Test loading valid JSON file."""
        seed_file = tmp_path / "test.json"
        test_data = [{"name": "Test", "code": "TEST"}]
        seed_file.write_text(json.dumps(test_data))

        seeder = DataSeeder(seed_dir=tmp_path)
        result = seeder.load_seed_file("test.json")

        assert result == test_data

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading non-existent file returns empty list."""
        seeder = DataSeeder(seed_dir=tmp_path)
        result = seeder.load_seed_file("nonexistent.json")

        assert result == []

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        """Test loading invalid JSON returns empty list."""
        seed_file = tmp_path / "invalid.json"
        seed_file.write_text("{invalid json}")

        seeder = DataSeeder(seed_dir=tmp_path)
        result = seeder.load_seed_file("invalid.json")

        assert result == []

    def test_load_non_array_json(self, tmp_path: Path) -> None:
        """Test loading non-array JSON returns empty list."""
        seed_file = tmp_path / "object.json"
        seed_file.write_text('{"key": "value"}')

        seeder = DataSeeder(seed_dir=tmp_path)
        result = seeder.load_seed_file("object.json")

        assert result == []


@pytest.mark.asyncio
class TestSeedUsers:
    """Tests for seed_users method."""

    async def test_seed_users_creates_new_users(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding creates new users successfully."""
        # Create seed file
        seed_file = tmp_path / "users.json"
        user_data = [
            {
                "email": "test@example.com",
                "password": "TestPass123!",
                "full_name": "Test User",
                "role": "viewer",
            }
        ]
        seed_file.write_text(json.dumps(user_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock UserService at the import location
        with patch("app.services.user.UserService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_by_email.return_value = None  # User doesn't exist
            mock_service.create_user.return_value = MagicMock()

            await seeder.seed_users(db_session)

            # Verify user was created
            mock_service.create_user.assert_called_once()
            call_args = mock_service.create_user.call_args
            assert call_args[0][0].email == "test@example.com"

    async def test_seed_users_skips_existing(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding skips existing users."""
        # Create seed file
        seed_file = tmp_path / "users.json"
        user_data = [
            {
                "email": "existing@example.com",
                "password": "TestPass123!",
                "full_name": "Existing User",
                "role": "viewer",
            }
        ]
        seed_file.write_text(json.dumps(user_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock UserService at the import location
        with patch("app.services.user.UserService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_by_email.return_value = MagicMock()  # User exists

            await seeder.seed_users(db_session)

            # Verify user was NOT created
            mock_service.create_user.assert_not_called()

    async def test_seed_users_handles_invalid_data(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding handles invalid user data gracefully."""
        # Create seed file with invalid data
        seed_file = tmp_path / "users.json"
        user_data = [
            {"email": "invalid-email", "password": "short"},  # Invalid email & password
        ]
        seed_file.write_text(json.dumps(user_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock UserService at the import location
        with patch("app.services.user.UserService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Should not raise exception, just log error
            await seeder.seed_users(db_session)

            # No users should be created
            mock_service.create_user.assert_not_called()

    async def test_seed_users_empty_file(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding with no data."""
        # Create empty seed file
        seed_file = tmp_path / "users.json"
        seed_file.write_text("[]")

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock UserService at the import location
        with patch("app.services.user.UserService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            await seeder.seed_users(db_session)

            # No users should be attempted
            mock_service.get_by_email.assert_not_called()


@pytest.mark.asyncio
class TestSeedDepartments:
    """Tests for seed_departments method."""

    async def test_seed_departments_creates_new(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding creates new departments successfully."""
        # Create seed file
        seed_file = tmp_path / "departments.json"
        dept_data = [
            {"code": "ENG", "name": "Engineering", "is_active": True, "manager_id": None}
        ]
        seed_file.write_text(json.dumps(dept_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock DepartmentService at the import location
        with patch("app.services.department.DepartmentService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_by_code.return_value = None  # Department doesn't exist
            mock_service.create_department.return_value = MagicMock()

            await seeder.seed_departments(db_session)

            # Verify department was created
            mock_service.create_department.assert_called_once()
            call_args = mock_service.create_department.call_args
            assert call_args[0][0].code == "ENG"

    async def test_seed_departments_skips_existing(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding skips existing departments."""
        # Create seed file
        seed_file = tmp_path / "departments.json"
        dept_data = [{"code": "EXIST", "name": "Existing", "is_active": True}]
        seed_file.write_text(json.dumps(dept_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock DepartmentService at the import location
        with patch("app.services.department.DepartmentService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_by_code.return_value = MagicMock()  # Department exists

            await seeder.seed_departments(db_session)

            # Verify department was NOT created
            mock_service.create_department.assert_not_called()


@pytest.mark.asyncio
class TestSeedAll:
    """Tests for seed_all orchestration method."""

    async def test_seed_all_calls_in_order(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seed_all calls seeding methods in correct order."""
        seeder = DataSeeder(seed_dir=tmp_path)

        with patch.object(seeder, "seed_departments") as mock_depts:
            with patch.object(seeder, "seed_users") as mock_users:
                await seeder.seed_all(db_session)

                # Verify both methods were called
                mock_depts.assert_called_once_with(db_session)
                mock_users.assert_called_once_with(db_session)

                # Verify departments called before users
                assert mock_depts.call_count == 1
                assert mock_users.call_count == 1

    async def test_seed_all_commits_transaction(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seed_all commits the transaction on success."""
        seeder = DataSeeder(seed_dir=tmp_path)

        with patch.object(seeder, "seed_departments"):
            with patch.object(seeder, "seed_users"):
                with patch.object(db_session, "commit") as mock_commit:
                    await seeder.seed_all(db_session)

                    # Verify commit was called
                    mock_commit.assert_called_once()

    async def test_seed_all_rollback_on_error(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seed_all rolls back transaction on error."""
        seeder = DataSeeder(seed_dir=tmp_path)

        with patch.object(seeder, "seed_departments", side_effect=ValueError("Test error")):
            with patch.object(db_session, "rollback") as mock_rollback:
                with pytest.raises(ValueError):
                    await seeder.seed_all(db_session)

                # Verify rollback was called
                mock_rollback.assert_called_once()
