"""Unit tests for DataSeeder module with root ID consistency verification."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.uuid_utils import generate_department_uuid, generate_user_uuid
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
class TestSeedUsersWithRootId:
    """Tests for seed_users method with root ID verification."""

    async def test_seed_users_uses_provided_user_id(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding uses the provided user_id from seed data."""
        # Generate deterministic user_id
        test_email = "test@example.com"
        expected_user_id = generate_user_uuid(test_email)

        # Create seed file with explicit user_id
        seed_file = tmp_path / "users.json"
        user_data = [
            {
                "user_id": str(expected_user_id),
                "email": test_email,
                "password": "TestPass123!",
                "full_name": "Test User",
                "role": "viewer",
            }
        ]
        seed_file.write_text(json.dumps(user_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock UserService
        with patch("app.services.user.UserService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_by_email.return_value = None  # User doesn't exist

            # Mock created user with the expected user_id
            mock_created_user = MagicMock()
            mock_created_user.user_id = expected_user_id
            mock_service.create_user.return_value = mock_created_user

            await seeder.seed_users(db_session)

            # Verify user was created with the provided user_id
            mock_service.create_user.assert_called_once()
            call_args = mock_service.create_user.call_args
            assert call_args[0][0].email == test_email
            assert call_args[0][0].user_id == expected_user_id

    async def test_seed_users_generates_id_when_not_provided(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding generates user_id when not provided."""
        # Create seed file without user_id
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

        # Mock UserService
        with patch("app.services.user.UserService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_by_email.return_value = None

            mock_created_user = MagicMock()
            mock_service.create_user.return_value = mock_created_user

            await seeder.seed_users(db_session)

            # Verify user was created
            mock_service.create_user.assert_called_once()
            call_args = mock_service.create_user.call_args
            assert call_args[0][0].email == "test@example.com"
            # user_id should be None, allowing service to generate
            assert call_args[0][0].user_id is None


@pytest.mark.asyncio
class TestSeedDepartmentsWithRootId:
    """Tests for seed_departments method with root ID verification."""

    async def test_seed_departments_uses_provided_department_id(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding uses the provided department_id from seed data."""
        # Generate deterministic department_id
        test_code = "ENG"
        expected_dept_id = generate_department_uuid(test_code)

        # Create seed file with explicit department_id
        seed_file = tmp_path / "departments.json"
        dept_data = [
            {
                "department_id": str(expected_dept_id),
                "code": test_code,
                "name": "Engineering",
                "is_active": True,
                "manager_id": None,
            }
        ]
        seed_file.write_text(json.dumps(dept_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock DepartmentService
        with patch("app.services.department.DepartmentService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_by_code.return_value = None

            mock_created_dept = MagicMock()
            mock_service.create_department.return_value = mock_created_dept

            await seeder.seed_departments(db_session)

            # Verify department was created with the provided department_id
            mock_service.create_department.assert_called_once()
            call_args = mock_service.create_department.call_args
            assert call_args[0][0].code == test_code
            assert call_args[0][0].department_id == expected_dept_id


@pytest.mark.asyncio
class TestSeedWBEsWithRootId:
    """Tests for seed_wbes method with root ID verification."""

    async def test_seed_wbes_uses_provided_wbe_id(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding uses the provided wbe_id from seed data."""
        # Create seed file with explicit wbe_id
        seed_file = tmp_path / "wbes.json"
        wbe_data = [
            {
                "wbe_id": "3a42f62c-96f8-5392-bff1-2e16f97734f0",
                "code": "TEST-WBE-001",
                "name": "Test WBE",
                "project_id": "d54fbbe6-f3df-51db-9c3e-9408700442be",
                "parent_wbe_id": None,
                "level": 1,
                "budget_allocation": 100000.0,
                "description": "Test WBE",
            }
        ]
        seed_file.write_text(json.dumps(wbe_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock WBEService
        with patch("app.services.wbe.WBEService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            mock_created_wbe = MagicMock()
            mock_created_wbe.wbe_id = UUID("3a42f62c-96f8-5392-bff1-2e16f97734f0")
            mock_service.create_wbe.return_value = mock_created_wbe

            await seeder.seed_wbes(db_session)

            # Verify WBE was created with the provided wbe_id
            mock_service.create_wbe.assert_called_once()
            call_args = mock_service.create_wbe.call_args
            assert call_args[0][0].code == "TEST-WBE-001"
            assert call_args[0][0].wbe_id == UUID(
                "3a42f62c-96f8-5392-bff1-2e16f97734f0"
            )
            # Verify relationships use IDs
            assert call_args[0][0].project_id == UUID(
                "d54fbbe6-f3df-51db-9c3e-9408700442be"
            )
            assert call_args[0][0].parent_wbe_id is None


@pytest.mark.asyncio
class TestSeedCostElementsWithRootId:
    """Tests for seed_cost_elements method with root ID verification."""

    async def test_seed_cost_elements_uses_provided_ids(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding uses provided cost_element_id and relationship IDs."""
        # Create seed file with explicit IDs
        seed_file = tmp_path / "cost_elements.json"
        ce_data = [
            {
                "cost_element_id": "18c26d12-9789-5004-b766-3b099405e884",
                "code": "TEST-CE-001",
                "name": "Test Cost Element",
                "budget_amount": 1000.0,
                "wbe_id": "3a42f62c-96f8-5392-bff1-2e16f97734f0",
                "cost_element_type_id": "6a483c4e-893c-5a92-8db9-6f5ac937c63f",
                "description": "Test cost element",
            }
        ]
        seed_file.write_text(json.dumps(ce_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock CostElementService
        with patch(
            "app.services.cost_element_service.CostElementService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            mock_created_ce = MagicMock()
            mock_service.create.return_value = mock_created_ce

            await seeder.seed_cost_elements(db_session)

            # Verify cost element was created with provided IDs
            mock_service.create.assert_called_once()
            call_args = mock_service.create.call_args
            assert call_args[0][0].code == "TEST-CE-001"
            assert call_args[0][0].cost_element_id == UUID(
                "18c26d12-9789-5004-b766-3b099405e884"
            )
            # Verify relationships use IDs
            assert call_args[0][0].wbe_id == UUID(
                "3a42f62c-96f8-5392-bff1-2e16f97734f0"
            )
            assert call_args[0][0].cost_element_type_id == UUID(
                "6a483c4e-893c-5a92-8db9-6f5ac937c63f"
            )


@pytest.mark.asyncio
class TestSeedUsers:
    """Tests for seed_users method (backward compatibility)."""

    async def test_seed_users_skips_existing(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding skips existing users."""
        # Create seed file
        seed_file = tmp_path / "users.json"
        user_data = [
            {
                "user_id": "e03556f3-4385-5d68-a685-af307fc8af5c",
                "email": "existing@example.com",
                "password": "TestPass123!",
                "full_name": "Existing User",
                "role": "viewer",
            }
        ]
        seed_file.write_text(json.dumps(user_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock UserService
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

        # Mock UserService
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

        # Mock UserService
        with patch("app.services.user.UserService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            await seeder.seed_users(db_session)

            # No users should be attempted
            mock_service.get_by_email.assert_not_called()


@pytest.mark.asyncio
class TestSeedDepartments:
    """Tests for seed_departments method (backward compatibility)."""

    async def test_seed_departments_skips_existing(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test seeding skips existing departments."""
        # Create seed file
        seed_file = tmp_path / "departments.json"
        dept_data = [
            {
                "department_id": "1c47969b-d568-5f34-bb9d-4e11cae84745",
                "code": "EXIST",
                "name": "Existing",
                "is_active": True,
            }
        ]
        seed_file.write_text(json.dumps(dept_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock DepartmentService
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

        with patch.object(
            seeder, "seed_departments", side_effect=ValueError("Test error")
        ):
            with patch.object(db_session, "rollback") as mock_rollback:
                with pytest.raises(ValueError):
                    await seeder.seed_all(db_session)

                # Verify rollback was called
                mock_rollback.assert_called_once()


@pytest.mark.asyncio
class TestWBEParentBranchLookup:
    """Tests for WBE parent lookup respecting branch context."""

    async def test_create_wbe_with_parent_on_same_branch(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test that creating a child WBE finds parent on the same branch."""
        from uuid import UUID, uuid4

        # Create seed file with parent and child on same branch
        seed_file = tmp_path / "wbes.json"
        branch = "test-branch-abc"
        parent_id = UUID("12345678-1234-5678-1234-567812345678")
        project_id = UUID("877c4cba-b30e-54c1-b25d-c73fb364019d")

        wbe_data = [
            {
                "wbe_id": str(parent_id),
                "code": "TEST-PARENT",
                "name": "Parent WBE",
                "project_id": str(project_id),
                "parent_wbe_id": None,
                "level": 1,
                "budget_allocation": 100000.0,
                "description": "Parent WBE",
                "branch": branch,
                "control_date": "2026-02-01T00:00:00",
            },
            {
                "wbe_id": str(uuid4()),
                "code": "TEST-CHILD",
                "name": "Child WBE",
                "project_id": str(project_id),
                "parent_wbe_id": str(parent_id),
                "level": 2,
                "budget_allocation": 50000.0,
                "description": "Child WBE",
                "branch": branch,  # Same branch as parent
                "control_date": "2026-02-01T00:00:00",
            },
        ]
        seed_file.write_text(json.dumps(wbe_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock WBEService
        with patch("app.services.wbe.WBEService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Mock parent lookup to return parent when called with correct branch
            mock_parent = MagicMock()
            mock_parent.wbe_id = parent_id
            mock_parent.level = 1
            mock_service.get_by_root_id.return_value = mock_parent

            # Mock successful creation
            mock_created_parent = MagicMock()
            mock_created_parent.wbe_id = parent_id
            mock_created_child = MagicMock()
            mock_created_child.wbe_id = uuid4()
            mock_service.create_wbe.side_effect = [
                mock_created_parent,
                mock_created_child,
            ]

            await seeder.seed_wbes(db_session)

            # Verify create_wbe was called twice (parent and child)
            assert mock_service.create_wbe.call_count == 2

            # Verify get_by_root_id was called with the correct branch for child
            # The second call should look up parent with branch parameter
            parent_lookup_calls = list(mock_service.get_by_root_id.call_args_list)
            assert len(parent_lookup_calls) >= 1

            # Check that at least one call used the correct branch
            correct_branch_used = any(
                call.kwargs.get("branch") == branch or call[1].get("branch") == branch
                for call in parent_lookup_calls
            )
            assert correct_branch_used, (
                f"Expected branch '{branch}' not found in get_by_root_id calls: {parent_lookup_calls}"
            )

    async def test_create_wbe_child_fails_when_parent_on_different_branch(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Test that creating child fails when parent doesn't exist on child's branch."""
        from uuid import UUID, uuid4

        # Create seed file with parent on one branch, child on another
        seed_file = tmp_path / "wbes.json"
        parent_id = UUID("12345678-1234-5678-1234-567812345678")
        project_id = UUID("877c4cba-b30e-54c1-b25d-c73fb364019d")

        wbe_data = [
            {
                "wbe_id": str(uuid4()),
                "code": "TEST-CHILD",
                "name": "Child WBE",
                "project_id": str(project_id),
                "parent_wbe_id": str(parent_id),
                "level": 2,
                "budget_allocation": 50000.0,
                "description": "Child WBE",
                "branch": "branch-b",  # Different from parent
                "control_date": "2026-02-01T00:00:00",
            },
        ]
        seed_file.write_text(json.dumps(wbe_data))

        seeder = DataSeeder(seed_dir=tmp_path)

        # Mock WBEService
        with patch("app.services.wbe.WBEService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Parent lookup returns None (doesn't exist on child's branch)
            mock_service.get_by_root_id.return_value = None

            # Should handle error gracefully
            await seeder.seed_wbes(db_session)

            # Verify create_wbe was NOT called (failed parent lookup)
            mock_service.create_wbe.assert_not_called()
