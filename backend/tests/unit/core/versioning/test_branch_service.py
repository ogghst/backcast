from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.core.versioning.branch_service import BranchableService
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.base import Base
from app.models.mixins import BranchableMixin, VersionableMixin


# Mock Entity
class MockBranchableEntity(Base, VersionableMixin, BranchableMixin):
    __tablename__ = "mock_branchable_entities"
    id = Column(PG_UUID, primary_key=True, default=uuid4)
    name = Column(String)
    mockbranchableentity_id = Column(PG_UUID) # root id field


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def service(mock_session):
    return BranchableService(MockBranchableEntity, mock_session)

class TestBranchableService:

    @pytest.mark.asyncio
    async def test_create_root_creates_main_branch(self, service, mock_session):
        # Arrange
        root_id = uuid4()
        data = {"name": "test"}

        # Mock Session execute for create_root since it delegates to CreateVersionCommand
        # which might not use execute directly but session.add?
        # CreateVersionCommand uses session.add.

        # Act
        result = await service.create_root(root_id, **data)

        # Assert
        assert result.branch == "main"
        assert result.mockbranchableentity_id == root_id
        assert result.name == "test"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_create_branch_clones_state(self, service, mock_session):
        # Arrange
        root_id = uuid4()
        parent_id = uuid4()

        # Mock existing version on main
        source_version = MockBranchableEntity(
            id=parent_id,
            mockbranchableentity_id=root_id,
            branch="main",
            name="existing"
        )

        # Mock functionality of _get_current_on_branch used by CreateBranchCommand
        # This requires mocking the execution of the select statement inside the command.
        # This is tricky with unit tests mocking the DB session.
        # Alternatively, we can rely on integration tests or mock the command execution?
        # The service delegates to commands. The tests here check if service correctly calls command logic.

        # Let's mock the session.execute to return the source version when querying
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = source_version
        mock_result.unique.return_value = mock_result # for scalars() calls if any
        mock_session.execute.return_value = mock_result

        # Act
        result = await service.create_branch(root_id, new_branch="dev", from_branch="main")

        # Assert
        assert result.branch == "dev"
        assert result.name == "existing"
        assert result.parent_id == parent_id
        mock_session.add.assert_called() # Should add the new branched version

    @pytest.mark.asyncio
    async def test_update_branch_isolates_changes(self, service, mock_session):
        # Arrange
        root_id = uuid4()
        parent_id = uuid4()

        # Current version on 'dev' branch
        current_dev = MockBranchableEntity(
            id=parent_id,
            mockbranchableentity_id=root_id,
            branch="dev",
            name="existing"
        )

        # Mock session to return this generic setup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = current_dev
        mock_session.execute.return_value = mock_result

        # Act
        result = await service.update(root_id, branch="dev", name="updated")

        # Assert
        assert result.branch == "dev"
        assert result.name == "updated"
        # Since parent was 'current_dev', new version parent should be 'current_dev.id'
        assert result.parent_id == parent_id

        # Verify call to flush (session.add and session.execute for closing old version)
        mock_session.add.assert_called()
        assert mock_session.execute.call_count >= 2 # One for select, one for update (close)

    @pytest.mark.asyncio
    async def test_merge_branch_applies_changes(self, service, mock_session):
        # Arrange
        root_id = uuid4()
        source_id = uuid4()
        target_id = uuid4()

        source = MockBranchableEntity(
            id=source_id, mockbranchableentity_id=root_id, branch="dev", name="feature_complete"
        )
        target = MockBranchableEntity(
            id=target_id, mockbranchableentity_id=root_id, branch="main", name="stable"
        )

        # Mock returns in sequence: Source lookup -> Target lookup
        # Side effect on execute to handle sequential calls?
        # Since _get_current_on_branch calls execute, we need side_effect.

        mock_res_source = MagicMock()
        mock_res_source.scalar_one_or_none.return_value = source

        mock_res_target = MagicMock()
        mock_res_target.scalar_one_or_none.return_value = target

        # We need a side effect that returns different results based on the query or just in sequence
        # The service calls: 1. get source, 2. get target, 3. update target (close)
        # mock_session.execute is awaited.
        mock_session.execute.side_effect = [mock_res_source, mock_res_target, MagicMock()]

        # Act
        result = await service.merge_branch(root_id, source_branch="dev", target_branch="main")

        # Assert
        assert result.branch == "main"
        assert result.name == "feature_complete" # Should take content from source
        assert result.parent_id == target_id # Parent should be previous HEAD of target
        assert result.merge_from_branch == "dev"

        mock_session.add.assert_called()

    @pytest.mark.asyncio
    async def test_get_by_id(self, service, mock_session):
        entity_id = uuid4()
        expected = MockBranchableEntity(id=entity_id)
        mock_session.get.return_value = expected

        result = await service.get_by_id(entity_id)
        assert result == expected
        mock_session.get.assert_called_with(MockBranchableEntity, entity_id)

    @pytest.mark.asyncio
    async def test_get_current(self, service, mock_session):
        root_id = uuid4()
        expected = MockBranchableEntity(id=uuid4(), mockbranchableentity_id=root_id)

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = expected
        mock_session.execute.return_value = mock_res

        result = await service.get_current(root_id, branch="main")
        assert result == expected
        mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_create_branch_raises_on_missing_source(self, service, mock_session):
        root_id = uuid4()

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None # No source
        mock_session.execute.return_value = mock_res

        with pytest.raises(ValueError, match="No active version"):
            await service.create_branch(root_id, new_branch="feat", from_branch="main")

    @pytest.mark.asyncio
    async def test_update_raises_on_missing_current(self, service, mock_session):
        root_id = uuid4()

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_res

        with pytest.raises(ValueError, match="No active version"):
            await service.update(root_id, branch="main", name="new")


    @pytest.mark.asyncio
    async def test_revert_restores_state(self, service, mock_session):
        # Arrange
        root_id = uuid4()
        current_id = uuid4()
        parent_id = uuid4()

        # Current HEAD
        current = MockBranchableEntity(
            id=current_id, mockbranchableentity_id=root_id, branch="main", name="oops", parent_id=parent_id
        )

        # Parent (Target for revert)
        parent = MockBranchableEntity(
            id=parent_id, mockbranchableentity_id=root_id, branch="main", name="good_state"
        )

        # Mock sequence:
        # 1. get current (calls execute)
        # 2. get target (calls session.get) - wait, RevertCommand uses session.get for specific ID

        mock_res_current = MagicMock()
        mock_res_current.scalar_one_or_none.return_value = current

        # side_effect for execute (for getting current) and close (update)
        # Note: Revert executes:
        # 1. _get_current_on_branch -> execute
        # 2. session.get(to_version_id or parent) -> get
        # 3. _close_version -> execute

        # So we need execute side effects for [get_current, close_version]
        mock_session.execute.side_effect = [mock_res_current, MagicMock()]

        mock_session.get.return_value = parent

        # Act
        # Revert to parent (implicitly via current.parent_id if not specified)
        result = await service.revert(root_id, branch="main")

        # Assert
        assert result.branch == "main"
        assert result.name == "good_state"
        assert result.parent_id == current_id # Revert is a new commit pointing to old HEAD

        mock_session.add.assert_called()
