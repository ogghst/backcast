from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.versioning.commands import SoftDeleteCommand
from app.models.protocols import VersionableProtocol


class MockEntity(VersionableProtocol):
    __tablename__ = "mock_entities"

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def soft_delete(self):
        self.deleted_at = "deleted"

    def clone(self, **kwargs):
        return MockEntity(**kwargs)


@pytest.mark.asyncio
async def test_soft_delete_command_success():
    # Arrange
    root_id = uuid4()
    actor_id = uuid4()
    mock_entity = MockEntity(
        id=uuid4(), mock_id=root_id, valid_time=MagicMock(), deleted_at=None
    )

    session = AsyncMock()
    # Mock _get_current return value
    # We need to patch the internal _get_current or let it run
    # Let's patch it for the unit test

    cmd = SoftDeleteCommand(MockEntity, root_id, actor_id)
    cmd._get_current = AsyncMock(return_value=mock_entity)

    # Act
    result = await cmd.execute(session)

    # Assert
    assert result.deleted_at == "deleted"
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_soft_delete_command_no_active_version():
    # Arrange
    root_id = uuid4()
    actor_id = uuid4()
    session = AsyncMock()

    cmd = SoftDeleteCommand(MockEntity, root_id, actor_id)
    cmd._get_current = AsyncMock(return_value=None)

    # Act & Assert
    with pytest.raises(ValueError, match=f"No active version found for {root_id}"):
        await cmd.execute(session)
