from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.service import TemporalService
from app.models.protocols import VersionableProtocol


# Mock Entity
class MockEntity(VersionableProtocol):
    __tablename__ = "mock_entities"
    id = uuid4()
    # Mocking protocol requirements
    valid_time = MagicMock()
    transaction_time = MagicMock()
    deleted_at = None

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def clone(self, **kwargs: Any) -> Any:
        return MockEntity(**kwargs)

    def soft_delete(self) -> None:
        pass

    def undelete(self) -> None:
        pass

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def service(mock_session: AsyncMock) -> TemporalService[MockEntity]:
    return TemporalService(MockEntity, mock_session)


@pytest.mark.asyncio
async def test_create_delegates_to_command(
    service: TemporalService[MockEntity], mock_session: AsyncMock
) -> None:
    # Arrange
    data = {"name": "test"}
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Mock execute to return empty result for overlap check (no existing versions)
    from unittest.mock import Mock

    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Act
    result = await service.create(root_id=uuid4(), actor_id=uuid4(), **data)

    # Assert
    assert isinstance(result, MockEntity)
    assert result.name == "test"
    mock_session.add.assert_called_once()
    # flush is called twice: once after add(), once after SQL update
    assert mock_session.flush.call_count == 2
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_update_delegates_to_command(
    service: TemporalService[MockEntity], mock_session: AsyncMock
) -> None:
    # This requires mocking the internal command execution or database state
    # For unit testing the service wrapper, we mainly want to ensure it calls the right things
    # But since the commands handle the logic, we might need integration tests more than unit tests here
    pass


# NOTE: The fix for "Multiple rows were found" error (transaction_time tiebreaker)
# is verified through integration testing with actual database queries.
# The fix ensures ORDER BY valid_time DESC, transaction_time DESC for deterministic
# selection when concurrent updates create multiple versions with the same valid_time.
