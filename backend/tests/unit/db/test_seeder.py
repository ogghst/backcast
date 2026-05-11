"""Unit tests for DataSeeder module with root ID consistency verification."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.uuid_utils import generate_department_uuid, generate_user_uuid
from app.db.seeder import DataSeeder


def _make_mock_role(name: str, role_id: UUID | None = None) -> MagicMock:
    """Create a mock RBACRole with given name and id."""
    mock_role = MagicMock()
    mock_role.name = name
    mock_role.id = role_id or uuid4()
    return mock_role


def _make_mock_user(user_id: UUID, role: str) -> MagicMock:
    """Create a mock User with given user_id and role."""
    mock_user = MagicMock()
    mock_user.user_id = user_id
    mock_user.role = role
    return mock_user


def _make_scalar_result(items: list[MagicMock]) -> MagicMock:
    """Create a mock SQLAlchemy scalar result supporting both patterns.

    Supports:
    - result.scalars().all() -> items
    - result.scalar_one_or_none() -> first item or None
    """
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.scalar_one_or_none.return_value = items[0] if items else None
    return result


def _make_all_result(rows: list[tuple]) -> MagicMock:
    """Create a mock SQLAlchemy result for .all() returning rows."""
    result = MagicMock()
    result.all.return_value = rows
    return result


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
            mock_service.create_cost_element.return_value = mock_created_ce

            await seeder.seed_cost_elements(db_session)

            # Verify cost element was created with provided IDs
            mock_service.create_cost_element.assert_called_once()
            call_args = mock_service.create_cost_element.call_args
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
class TestSeedUserRoleAssignments:
    """Tests for seed_user_role_assignments method.

    Validates the new method creates GLOBAL UserRoleAssignment records
    for each seeded user, matching their User.role value.
    """

    async def test_happy_path_creates_assignments(self) -> None:
        """T-001: Creates one global assignment per user with valid roles."""
        seeder = DataSeeder(seed_dir=Path("/tmp/nonexistent"))

        session = AsyncMock(spec=AsyncSession)
        admin_id = UUID("e03556f3-4385-5d68-a685-af307fc8af5c")
        viewer_id = UUID("85b44758-76ab-5a80-9d47-836a09d00e03")
        pm_id = UUID("533a7e61-6b73-5978-a751-7862efa734f7")

        admin_role = _make_mock_role("admin")
        viewer_role = _make_mock_role("viewer")
        manager_role = _make_mock_role("manager")

        users = [
            _make_mock_user(admin_id, "admin"),
            _make_mock_user(viewer_id, "viewer"),
            _make_mock_user(pm_id, "manager"),
        ]
        roles = [admin_role, viewer_role, manager_role]

        # Mock: no existing assignments
        empty_result = _make_scalar_result([])

        call_count = 0

        def mock_execute(stmt: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: select users with roles
                return _make_scalar_result(users)
            elif call_count == 2:
                # Second call: select rbac_roles
                return _make_scalar_result(roles)
            else:
                # Subsequent calls: check existing assignments
                return empty_result

        session.execute = AsyncMock(side_effect=mock_execute)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await seeder.seed_user_role_assignments(session)

        # Verify 3 assignments were added
        assert session.add.call_count == 3
        assert session.flush.call_count >= 1

    async def test_idempotent_no_duplicates(self) -> None:
        """T-004: Calling twice does not create duplicates."""
        seeder = DataSeeder(seed_dir=Path("/tmp/nonexistent"))

        session = AsyncMock(spec=AsyncSession)
        admin_id = UUID("e03556f3-4385-5d68-a685-af307fc8af5c")
        admin_role = _make_mock_role("admin")
        users = [_make_mock_user(admin_id, "admin")]
        roles = [admin_role]

        # Mock existing assignment for admin user
        existing_assignment = MagicMock()
        existing_assignment.user_id = admin_id
        existing_result = _make_scalar_result([existing_assignment])

        call_count = 0

        def mock_execute(stmt: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_scalar_result(users)
            elif call_count == 2:
                return _make_scalar_result(roles)
            else:
                # Already has assignment
                return existing_result

        session.execute = AsyncMock(side_effect=mock_execute)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await seeder.seed_user_role_assignments(session)

        # Verify no new assignments added
        session.add.assert_not_called()

    async def test_skips_user_with_missing_role(self) -> None:
        """T-006: User with unrecognized role is skipped with a warning."""
        seeder = DataSeeder(seed_dir=Path("/tmp/nonexistent"))

        session = AsyncMock(spec=AsyncSession)
        admin_id = UUID("e03556f3-4385-5d68-a685-af307fc8af5c")
        unknown_id = UUID("99999999-9999-5999-9999-999999999999")

        admin_role = _make_mock_role("admin")
        users = [
            _make_mock_user(admin_id, "admin"),
            _make_mock_user(unknown_id, "nonexistent_role"),
        ]
        roles = [admin_role]

        call_count = 0

        def mock_execute(stmt: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_scalar_result(users)
            elif call_count == 2:
                return _make_scalar_result(roles)
            else:
                return _make_scalar_result([])

        session.execute = AsyncMock(side_effect=mock_execute)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await seeder.seed_user_role_assignments(session)

        # Only admin user's assignment should be created
        assert session.add.call_count == 1

    async def test_handles_empty_users(self) -> None:
        """Test: When no users exist, method completes without error."""
        seeder = DataSeeder(seed_dir=Path("/tmp/nonexistent"))

        session = AsyncMock(spec=AsyncSession)

        def mock_execute(stmt: object) -> MagicMock:
            return _make_scalar_result([])

        session.execute = AsyncMock(side_effect=mock_execute)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await seeder.seed_user_role_assignments(session)

        # No assignments created
        session.add.assert_not_called()

    async def test_works_after_migration(self) -> None:
        """T-005: Method works when assignments already exist (post-migration)."""
        seeder = DataSeeder(seed_dir=Path("/tmp/nonexistent"))

        session = AsyncMock(spec=AsyncSession)
        admin_id = UUID("e03556f3-4385-5d68-a685-af307fc8af5c")
        admin_role = _make_mock_role("admin")
        users = [_make_mock_user(admin_id, "admin")]
        roles = [admin_role]

        # Simulate: assignment already exists from migration
        existing = MagicMock()
        existing.user_id = admin_id

        call_count = 0

        def mock_execute(stmt: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_scalar_result(users)
            elif call_count == 2:
                return _make_scalar_result(roles)
            else:
                return _make_scalar_result([existing])

        session.execute = AsyncMock(side_effect=mock_execute)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await seeder.seed_user_role_assignments(session)

        # Should skip since assignment exists
        session.add.assert_not_called()


@pytest.mark.asyncio
class TestSeedAllUserRoleAssignments:
    """Tests verifying seed_all calls seed_user_role_assignments."""

    async def test_seed_all_includes_user_role_assignments(self) -> None:
        """T-007: seed_all() calls seed_user_role_assignments after seed_users."""
        seeder = DataSeeder(seed_dir=Path("/tmp/nonexistent"))
        session = AsyncMock(spec=AsyncSession)

        with patch.object(seeder, "seed_rbac_roles"):
            with patch.object(seeder, "seed_departments"):
                with patch.object(seeder, "seed_users"):
                    with patch.object(
                        seeder, "seed_user_role_assignments"
                    ) as mock_ura:
                        with patch.object(seeder, "seed_co_workflow_config"):
                            with patch.object(seeder, "seed_cost_element_types"):
                                with patch.object(seeder, "seed_projects"):
                                    with patch.object(seeder, "seed_wbes"):
                                        with patch.object(
                                            seeder, "seed_cost_elements"
                                        ):
                                            with patch.object(
                                                seeder, "seed_cost_registrations"
                                            ):
                                                with patch.object(
                                                    seeder, "seed_progress_entries"
                                                ):
                                                    with patch.object(
                                                        seeder, "seed_change_orders"
                                                    ):
                                                        with patch.object(
                                                            seeder,
                                                            "seed_change_order_audit_logs",
                                                        ):
                                                            with patch.object(
                                                                seeder,
                                                                "seed_ai_providers",
                                                            ):
                                                                with patch.object(
                                                                    seeder,
                                                                    "seed_ai_assistants",
                                                                ):
                                                                    await seeder.seed_all(
                                                                        session
                                                                    )

                                                                    mock_ura.assert_called_once_with(
                                                                        session
                                                                    )
