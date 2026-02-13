from uuid import uuid4

import pytest

from app.models.domain.branch import Branch
from app.models.domain.project import Project


@pytest.mark.asyncio
async def test_branch_has_temporal_fields(db_session):
    # Arrange
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-TEMPORAL",
        name="Test Project Temporal",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)
    await db_session.flush()

    # Act
    branch = Branch(
        name="temporal-branch",
        project_id=project.project_id,
        created_by=user_id,
    )
    db_session.add(branch)
    await db_session.flush()

    # Assert
    assert hasattr(branch, "branch_id")
    assert branch.branch_id is not None
    assert hasattr(branch, "valid_time")
    assert hasattr(branch, "transaction_time")
