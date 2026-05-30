"""Comprehensive tests for the EVCS Simple Core.

Covers:
- app.core.simple.commands: SimpleCreateCommand, SimpleUpdateCommand, SimpleDeleteCommand
- app.core.simple.service: SimpleService (get, list_all, create, update, delete)

Uses RBACRole as the test entity (SimpleEntityBase subclass with simple fields).
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.simple.commands import (
    SimpleCreateCommand,
    SimpleDeleteCommand,
    SimpleUpdateCommand,
)
from app.core.simple.service import SimpleService
from app.models.domain.rbac import RBACRole

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_unique_counter = 0


def _unique_name() -> str:
    """Generate a unique role name to avoid collisions between tests."""
    global _unique_counter
    _unique_counter += 1
    return f"test-role-{uuid4().hex[:8]}-{_unique_counter}"


async def _create_role(session: AsyncSession, **overrides: object) -> RBACRole:
    """Factory: create and persist a RBACRole via direct command."""
    defaults: dict[str, object] = {
        "name": _unique_name(),
        "description": "Test role",
        "is_system": False,
    }
    defaults.update(overrides)
    cmd = SimpleCreateCommand(RBACRole, **defaults)
    return await cmd.execute(session)


# ===================================================================
# SimpleCreateCommand
# ===================================================================


class TestSimpleCreateCommand:
    """Tests for SimpleCreateCommand."""

    @pytest.mark.asyncio
    async def test_execute_creates_entity(self, db: AsyncSession) -> None:
        """SimpleCreateCommand persists a new entity and returns it."""
        name = _unique_name()
        cmd = SimpleCreateCommand(
            RBACRole,
            name=name,
            description="Created via command",
            is_system=False,
        )
        result = await cmd.execute(db)

        assert isinstance(result, RBACRole)
        assert result.name == name
        assert result.description == "Created via command"
        assert result.is_system is False
        assert result.id is not None
        assert result.created_at is not None
        assert result.updated_at is not None

    @pytest.mark.asyncio
    async def test_execute_persists_to_db(self, db: AsyncSession) -> None:
        """Entity is retrievable from session after create command."""
        name = _unique_name()
        cmd = SimpleCreateCommand(
            RBACRole, name=name, description="Persist test", is_system=False
        )
        created = await cmd.execute(db)
        await db.commit()

        fetched = await db.get(RBACRole, created.id)
        assert fetched is not None
        assert fetched.name == name

    @pytest.mark.asyncio
    async def test_init_stores_fields(self) -> None:
        """Constructor stores entity_class and fields."""
        cmd = SimpleCreateCommand(RBACRole, name="x", description="y")
        assert cmd.entity_class is RBACRole
        assert cmd.fields == {"name": "x", "description": "y"}

    @pytest.mark.asyncio
    async def test_execute_with_minimal_fields(self, db: AsyncSession) -> None:
        """Create with only required fields (server defaults for others)."""
        name = _unique_name()
        cmd = SimpleCreateCommand(RBACRole, name=name)
        result = await cmd.execute(db)

        assert result.name == name
        assert result.description is None
        assert result.is_system is False  # server_default


# ===================================================================
# SimpleUpdateCommand
# ===================================================================


class TestSimpleUpdateCommand:
    """Tests for SimpleUpdateCommand."""

    @pytest.mark.asyncio
    async def test_execute_updates_entity(self, db: AsyncSession) -> None:
        """SimpleUpdateCommand modifies existing entity fields."""
        role = await _create_role(db, description="Original")
        await db.commit()

        cmd = SimpleUpdateCommand(
            RBACRole, role.id, description="Updated", is_system=True
        )
        result = await cmd.execute(db)

        assert result.id == role.id
        assert result.description == "Updated"
        assert result.is_system is True

    @pytest.mark.asyncio
    async def test_execute_raises_on_missing_entity(self, db: AsyncSession) -> None:
        """SimpleUpdateCommand raises ValueError when entity not found."""
        fake_id = uuid4()
        cmd = SimpleUpdateCommand(RBACRole, fake_id, description="Nope")

        with pytest.raises(ValueError, match="not found"):
            await cmd.execute(db)

    @pytest.mark.asyncio
    async def test_init_stores_fields(self) -> None:
        """Constructor stores entity_class, entity_id, and updates."""
        entity_id = uuid4()
        cmd = SimpleUpdateCommand(
            RBACRole, entity_id, description="new", is_system=True
        )
        assert cmd.entity_class is RBACRole
        assert cmd.entity_id == entity_id
        assert cmd.updates == {"description": "new", "is_system": True}

    @pytest.mark.asyncio
    async def test_execute_update_name(self, db: AsyncSession) -> None:
        """Update the name field specifically."""
        role = await _create_role(db)
        await db.commit()

        new_name = _unique_name()
        cmd = SimpleUpdateCommand(RBACRole, role.id, name=new_name)
        result = await cmd.execute(db)

        assert result.name == new_name


# ===================================================================
# SimpleDeleteCommand
# ===================================================================


class TestSimpleDeleteCommand:
    """Tests for SimpleDeleteCommand."""

    @pytest.mark.asyncio
    async def test_execute_deletes_existing_entity(self, db: AsyncSession) -> None:
        """SimpleDeleteCommand removes entity and returns True."""
        role = await _create_role(db)
        await db.commit()

        cmd = SimpleDeleteCommand(RBACRole, role.id)
        result = await cmd.execute(db)

        assert result is True

        # Verify entity is gone
        await db.commit()
        fetched = await db.get(RBACRole, role.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_execute_returns_false_for_missing(self, db: AsyncSession) -> None:
        """SimpleDeleteCommand returns False when entity does not exist."""
        fake_id = uuid4()
        cmd = SimpleDeleteCommand(RBACRole, fake_id)
        result = await cmd.execute(db)

        assert result is False

    @pytest.mark.asyncio
    async def test_init_stores_fields(self) -> None:
        """Constructor stores entity_class and entity_id."""
        entity_id = uuid4()
        cmd = SimpleDeleteCommand(RBACRole, entity_id)
        assert cmd.entity_class is RBACRole
        assert cmd.entity_id == entity_id


# ===================================================================
# SimpleService
# ===================================================================


class TestSimpleService:
    """Tests for SimpleService CRUD operations."""

    def _service(self, session: AsyncSession) -> SimpleService[RBACRole]:
        return SimpleService(session, RBACRole)

    # -- get --

    @pytest.mark.asyncio
    async def test_get_returns_entity(self, db: AsyncSession) -> None:
        """get() returns the entity when it exists."""
        role = await _create_role(db)
        await db.commit()

        svc = self._service(db)
        result = await svc.get(role.id)

        assert result is not None
        assert result.id == role.id
        assert result.name == role.name

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self, db: AsyncSession) -> None:
        """get() returns None when entity does not exist."""
        svc = self._service(db)
        result = await svc.get(uuid4())

        assert result is None

    # -- list_all --

    @pytest.mark.asyncio
    async def test_list_all_returns_entities(self, db: AsyncSession) -> None:
        """list_all() returns all entities in the table."""
        await _create_role(db, name=_unique_name())
        await _create_role(db, name=_unique_name())
        await db.commit()

        svc = self._service(db)
        results = await svc.list_all()

        assert len(results) >= 2
        assert all(isinstance(r, RBACRole) for r in results)

    @pytest.mark.asyncio
    async def test_list_all_with_pagination(self, db: AsyncSession) -> None:
        """list_all() respects skip and limit parameters."""
        # Create at least 3 roles
        for _ in range(3):
            await _create_role(db, name=_unique_name())
        await db.commit()

        svc = self._service(db)

        # Get first page of 1
        page1 = await svc.list_all(skip=0, limit=1)
        assert len(page1) == 1

        # Get second page of 1
        page2 = await svc.list_all(skip=1, limit=1)
        assert len(page2) == 1

        # Pages should differ
        assert page1[0].id != page2[0].id

    @pytest.mark.asyncio
    async def test_list_all_default_params(self, db: AsyncSession) -> None:
        """list_all() defaults to skip=0, limit=100000."""
        svc = self._service(db)
        results = await svc.list_all()

        assert isinstance(results, list)

    # -- create --

    @pytest.mark.asyncio
    async def test_create_persists_entity(self, db: AsyncSession) -> None:
        """create() delegates to SimpleCreateCommand and returns entity."""
        name = _unique_name()
        svc = self._service(db)
        result = await svc.create(name=name, description="Via service", is_system=False)

        assert isinstance(result, RBACRole)
        assert result.name == name
        assert result.description == "Via service"
        assert result.id is not None

    # -- update --

    @pytest.mark.asyncio
    async def test_update_modifies_entity(self, db: AsyncSession) -> None:
        """update() delegates to SimpleUpdateCommand and returns entity."""
        role = await _create_role(db, description="Before")
        await db.commit()

        svc = self._service(db)
        result = await svc.update(role.id, description="After")

        assert result.description == "After"

    @pytest.mark.asyncio
    async def test_update_returns_entity_on_success(self, db: AsyncSession) -> None:
        """update() returns the updated entity, not a boolean."""
        role = await _create_role(db)
        await db.commit()

        svc = self._service(db)
        result = await svc.update(role.id, description="Changed")

        assert isinstance(result, RBACRole)

    # -- delete --

    @pytest.mark.asyncio
    async def test_delete_removes_entity(self, db: AsyncSession) -> None:
        """delete() returns True when entity is deleted."""
        role = await _create_role(db)
        await db.commit()

        svc = self._service(db)
        result = await svc.delete(role.id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_missing(self, db: AsyncSession) -> None:
        """delete() returns False when entity does not exist."""
        svc = self._service(db)
        result = await svc.delete(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_returns_false_on_value_error(self, db: AsyncSession) -> None:
        """delete() catches ValueError from command and returns False."""
        from unittest.mock import AsyncMock, patch

        svc = self._service(db)
        with patch(
            "app.core.simple.service.SimpleDeleteCommand.execute",
            new_callable=AsyncMock,
            side_effect=ValueError("not found"),
        ):
            result = await svc.delete(uuid4())

        assert result is False

    # -- init --

    def test_init_stores_session_and_class(self, db: AsyncSession) -> None:
        """Constructor stores session and entity_class."""
        svc = self._service(db)
        assert svc.session is db
        assert svc.entity_class is RBACRole
