from datetime import UTC, datetime
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

    def clone(self, **kwargs):
        return MockEntity(**kwargs)


@pytest.mark.asyncio
async def test_soft_delete_command_success():
    # Arrange
    root_id = uuid4()
    actor_id = uuid4()
    control_date = datetime(2026, 5, 5, 0, 0, 0, tzinfo=UTC)
    mock_entity = MockEntity(
        id=uuid4(), mock_id=root_id, valid_time=MagicMock(), deleted_at=None
    )

    session = AsyncMock()
    # Mock _get_current return value
    cmd = SoftDeleteCommand(MockEntity, root_id, actor_id, control_date=control_date)
    cmd._get_current = AsyncMock(return_value=mock_entity)

    # Act
    result = await cmd.execute(session)

    # Assert
    assert result.deleted_at == control_date
    assert result.deleted_by == actor_id
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
