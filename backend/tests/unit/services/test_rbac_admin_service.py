"""Unit tests for RBACAdminService.

Tests cover:
- Role CRUD (create, read, update, delete)
- Permission management
- System-role deletion guard
- Cache refresh after writes
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rbac_admin_service import RBACAdminService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession for unit tests."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def service(mock_session: AsyncMock) -> RBACAdminService:
    """Create an RBACAdminService with a mocked session."""
    return RBACAdminService(mock_session)


def _make_role(
    name: str = "test-role",
    description: str | None = None,
    is_system: bool = False,
    permissions: list[str] | None = None,
) -> MagicMock:
    """Create a mock RBACRole with permissions loaded."""
    role = MagicMock()
    role.id = uuid4()
    role.name = name
    role.description = description
    role.is_system = is_system
    role.permissions = []
    if permissions:
        for perm in permissions:
            perm_obj = MagicMock()
            perm_obj.id = uuid4()
            perm_obj.permission = perm
            role.permissions.append(perm_obj)
    return role


# ---------------------------------------------------------------------------
# List roles
# ---------------------------------------------------------------------------


class TestListRoles:
    """Tests for list_roles method."""

    @pytest.mark.asyncio
    async def test_list_roles(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """list_roles returns all roles ordered by name with permissions loaded.

        Given:
            Two roles exist in the database.
        When:
            list_roles is called.
        Then:
            Both roles are returned ordered by name.
        """
        role_a = _make_role(name="alpha")
        role_b = _make_role(name="beta")

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [role_a, role_b]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        roles = await service.list_roles()

        assert len(roles) == 2
        # Verify permissions are force-loaded
        assert role_a.permissions == role_a.permissions
        assert role_b.permissions == role_b.permissions


# ---------------------------------------------------------------------------
# Create role
# ---------------------------------------------------------------------------


class TestCreateRole:
    """Tests for create_role method."""

    @pytest.mark.asyncio
    async def test_create_role(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """create_role returns a new role with correct attributes and permissions.

        Given:
            A valid role name, description, and permissions list.
        When:
            create_role is called.
        Then:
            A role is added to the session with is_system=False and the
            correct permission entries are created.
        """
        with patch.object(service, "_refresh_cache", new_callable=AsyncMock):
            role = await service.create_role(
                name="engineer",
                description="Engineering role",
                permissions=["project-read", "project-write"],
            )

        assert role.name == "engineer"
        assert role.description == "Engineering role"
        assert role.is_system is False
        # session.add called once for role + twice for permissions
        assert mock_session.add.call_count == 3
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_create_role_duplicate_name(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """create_role propagates IntegrityError for duplicate role names.

        Given:
            A role name that already exists (unique constraint violation).
        When:
            create_role is called and flush raises an IntegrityError.
        Then:
            The exception propagates to the caller.
        """
        from sqlalchemy.exc import IntegrityError

        mock_session.flush.side_effect = IntegrityError(
            "duplicate key", params=None, orig=Exception()
        )

        with pytest.raises(IntegrityError):
            await service.create_role(
                name="admin",
                description="Duplicate",
                permissions=["project-read"],
            )


# ---------------------------------------------------------------------------
# Update role
# ---------------------------------------------------------------------------


class TestUpdateRole:
    """Tests for update_role method."""

    @pytest.mark.asyncio
    async def test_update_role_name(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """update_role changes the name when name is provided.

        Given:
            An existing role.
        When:
            update_role is called with a new name.
        Then:
            The role's name attribute is updated.
        """
        role = _make_role(name="old-name")
        mock_session.get.return_value = role

        with patch.object(service, "_refresh_cache", new_callable=AsyncMock):
            updated = await service.update_role(
                role_id=role.id,
                name="new-name",
                description=None,
                permissions=None,
            )

        assert updated is not None
        assert updated.name == "new-name"

    @pytest.mark.asyncio
    async def test_update_role_permissions(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """update_role replaces all permissions when permissions list is given.

        Given:
            An existing role with permissions.
        When:
            update_role is called with a new permissions list.
        Then:
            Old permissions are deleted and new ones are added.
        """
        role = _make_role(name="editor")
        mock_session.get.return_value = role

        with patch.object(service, "_refresh_cache", new_callable=AsyncMock):
            updated = await service.update_role(
                role_id=role.id,
                name=None,
                description=None,
                permissions=["new-perm-a", "new-perm-b"],
            )

        assert updated is not None
        # session.execute called once for delete statement
        assert mock_session.execute.call_count == 1
        # session.add called twice for new permissions
        assert mock_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_update_role_partial(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """update_role changes only description when only description is given.

        Given:
            An existing role with name "editor".
        When:
            update_role is called with a new description only.
        Then:
            The name remains unchanged, description is updated.
        """
        role = _make_role(name="editor", description="old desc")
        mock_session.get.return_value = role

        with patch.object(service, "_refresh_cache", new_callable=AsyncMock):
            updated = await service.update_role(
                role_id=role.id,
                name=None,
                description="new desc",
                permissions=None,
            )

        assert updated is not None
        assert updated.name == "editor"
        assert updated.description == "new desc"
        # No delete or add calls since permissions is None
        assert mock_session.add.call_count == 0

    @pytest.mark.asyncio
    async def test_update_role_not_found(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """update_role returns None when role ID does not exist.

        Given:
            No role with the given ID.
        When:
            update_role is called.
        Then:
            None is returned.
        """
        mock_session.get.return_value = None

        result = await service.update_role(
            role_id=uuid4(),
            name="x",
            description=None,
            permissions=None,
        )

        assert result is None


# ---------------------------------------------------------------------------
# Delete role
# ---------------------------------------------------------------------------


class TestDeleteRole:
    """Tests for delete_role method."""

    @pytest.mark.asyncio
    async def test_delete_role(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """delete_role removes a non-system role and returns True.

        Given:
            A non-system role exists.
        When:
            delete_role is called.
        Then:
            The role is deleted and True is returned.
        """
        role = _make_role(name="custom", is_system=False)
        mock_session.get.return_value = role

        with patch.object(service, "_refresh_cache", new_callable=AsyncMock):
            deleted = await service.delete_role(role.id)

        assert deleted is True
        mock_session.delete.assert_called_once_with(role)

    @pytest.mark.asyncio
    async def test_delete_system_role_fails(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """delete_role raises ValueError when trying to delete a system role.

        Given:
            A system role (is_system=True).
        When:
            delete_role is called.
        Then:
            ValueError is raised with the appropriate message.
        """
        role = _make_role(name="admin", is_system=True)
        mock_session.get.return_value = role

        with pytest.raises(ValueError, match="Cannot delete system role"):
            await service.delete_role(role.id)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_role(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """delete_role returns False when role does not exist.

        Given:
            No role with the given ID.
        When:
            delete_role is called.
        Then:
            False is returned.
        """
        mock_session.get.return_value = None

        deleted = await service.delete_role(uuid4())

        assert deleted is False


# ---------------------------------------------------------------------------
# Get all permissions
# ---------------------------------------------------------------------------


class TestGetAllPermissions:
    """Tests for get_all_permissions method."""

    @pytest.mark.asyncio
    async def test_get_all_permissions(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """get_all_permissions returns distinct permission strings ordered alphabetically.

        Given:
            Multiple roles with overlapping permissions.
        When:
            get_all_permissions is called.
        Then:
            A deduplicated, sorted list of permission strings is returned.
        """
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("cost-element-read",),
            ("project-read",),
            ("project-write",),
        ]
        mock_session.execute.return_value = mock_result

        perms = await service.get_all_permissions()

        assert perms == ["cost-element-read", "project-read", "project-write"]


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------


class TestCacheRefresh:
    """Tests for _refresh_cache being called after write operations."""

    @pytest.mark.asyncio
    async def test_cache_refresh_on_create(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """_refresh_cache is called after create_role.

        Given:
            A valid role creation request.
        When:
            create_role is called.
        Then:
            _refresh_cache is invoked exactly once.
        """
        with patch.object(
            service, "_refresh_cache", new_callable=AsyncMock
        ) as mock_inv:
            await service.create_role(
                name="role-a",
                description=None,
                permissions=["perm-x"],
            )
            mock_inv.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_refresh_on_update(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """_refresh_cache is called after update_role.

        Given:
            An existing role.
        When:
            update_role is called.
        Then:
            _refresh_cache is invoked exactly once.
        """
        role = _make_role(name="editor")
        mock_session.get.return_value = role

        with patch.object(
            service, "_refresh_cache", new_callable=AsyncMock
        ) as mock_inv:
            await service.update_role(
                role_id=role.id,
                name="updated-editor",
                description=None,
                permissions=None,
            )
            mock_inv.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_refresh_on_delete(
        self, service: RBACAdminService, mock_session: AsyncMock
    ) -> None:
        """_refresh_cache is called after delete_role.

        Given:
            A non-system role to delete.
        When:
            delete_role is called.
        Then:
            _refresh_cache is invoked exactly once.
        """
        role = _make_role(name="custom", is_system=False)
        mock_session.get.return_value = role

        with patch.object(
            service, "_refresh_cache", new_callable=AsyncMock
        ) as mock_inv:
            await service.delete_role(role.id)
            mock_inv.assert_called_once()
