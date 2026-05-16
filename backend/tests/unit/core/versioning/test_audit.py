from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.core.versioning.service import TemporalService
from app.models.mixins import VersionableMixin

# -----------------------------------------------------------------------------
# Mock Entity
# -----------------------------------------------------------------------------


class MockAuditEntity(EntityBase, VersionableMixin):
    __tablename__ = "mock_audit_entities"

    mock_audit_entity_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(nullable=False)


# -----------------------------------------------------------------------------
# Test Suite
# -----------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function", autouse=True)
async def create_mock_table(db_engine):
    async with db_engine.begin() as conn:
        await conn.run_sync(MockAuditEntity.__table__.create)
    yield
    async with db_engine.begin() as conn:
        await conn.run_sync(MockAuditEntity.__table__.drop)


@pytest.mark.asyncio
async def test_audit_create_persistence(db_session):
    """Verify actor_id is persisted to created_by on creation."""
    session = db_session

    # Create tables dynamically for this test if needed, or assume they exist?
    # Since we are adding new columns to Mixin, we need to ensure the DB reflects that.
    # For now, we will assume the migration will run before this test passes.
    # But for TDD, we write the test expecting the columns to exist on the model.
    # If columns don't exist on DB, it will fail (ProgrammingError).
    # If columns don't exist on Model, it will fail (AttributeError).

    # 1. Arrange
    actor_id = uuid4()
    root_id = uuid4()

    service = TemporalService(MockAuditEntity, session)

    # 2. Act
    # We expect TemporalService.create to accept actor_id
    entity = await service.create(
        root_id=root_id,
        description="Initial Version",
        actor_id=actor_id,  # This arg doesn't exist yet -> TypeError (RED)
    )

    # 3. Assert
    assert entity.created_by == actor_id
    assert entity.deleted_by is None


@pytest.mark.asyncio
async def test_audit_update_persistence(db_session):
    """Verify actor_id is persisted to created_by on update (new version)."""
    session = db_session
    actor_1 = uuid4()
    actor_2 = uuid4()
    root_id = uuid4()

    service = TemporalService(MockAuditEntity, session)

    # Create V1
    v1 = await service.create(root_id=root_id, description="V1", actor_id=actor_1)

    # Capture ID before update expires the instance
    v1_id = v1.id

    # Update to V2
    v2 = await service.update(
        entity_id=root_id,
        description="V2",
        actor_id=actor_2,  # New arg
    )

    assert v2.created_by == actor_2
    assert v2.id != v1_id  # New version


@pytest.mark.asyncio
async def test_audit_soft_delete_persistence(db_session):
    """Verify actor_id is persisted to deleted_by on soft delete."""
    session = db_session
    actor_1 = uuid4()
    deleter = uuid4()
    root_id = uuid4()

    service = TemporalService(MockAuditEntity, session)
    await service.create(root_id=root_id, description="To Delete", actor_id=actor_1)

    # Soft Delete
    await service.soft_delete(entity_id=root_id, actor_id=deleter)

    # Verify via direct query since soft_delete might return None or void
    # Use get_by_id on the *instance* we just deleted?
    # Command usually returns cached instance.

    # Let's fetch raw to check deleted_by
    stmt = (
        select(MockAuditEntity)
        .where(MockAuditEntity.mock_audit_entity_id == root_id)
        .order_by(MockAuditEntity.valid_time.desc())
    )
    result = await session.execute(stmt)
    deleted_entity = result.scalars().first()

    assert deleted_entity.is_deleted
    assert deleted_entity.deleted_by == deleter
