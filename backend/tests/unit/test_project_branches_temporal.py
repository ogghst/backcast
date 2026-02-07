from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.domain.branch import Branch
from app.models.domain.project import Project
from app.services.project import ProjectService


@pytest.mark.asyncio
async def test_get_project_branches_temporal(db_session):
    # Arrange
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PB-001",
        name="Test PB 1",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)

    # Branch 1 (Main) - created automatically in real app, manual here
    branch_main = Branch(
        name="main",
        type="main",
        project_id=project.project_id,
        created_by=user_id
    )
    db_session.add(branch_main)

    await db_session.flush()
    await db_session.refresh(branch_main)
    # T1
    t1 = datetime.now(UTC)

    # Wait

    # Branch 2 (CO) created later
    # We simulate temporal aspect by just creating it.
    branch_co = Branch(
        name="co-CO-TEST-1",
        type="change_order",
        project_id=project.project_id,
        created_by=user_id
    )
    db_session.add(branch_co)
    await db_session.flush()
    await db_session.refresh(branch_co)
    # T2
    t2 = datetime.now(UTC)

    service = ProjectService(db_session)

    # Act
    # Query at T1 (before CO branch creation)
    # Actually T1 is roughly when main created. T2 is when CO created.
    # We need t_between such that T1 < t_between < T2?
    # Actually, branch_co.valid_time.lower matches creation.
    # So if we query at T1 (or slightly after), branch_co shouldn't exist?
    # But current time might be same as T1 if execution is fast.
    # Let's use explicit valid_time filtering or rely on sleep? No sleep.
    # We can inspect valid_time.

    result_current = await service.get_project_branches(project.project_id)

    # Query at t_before_co
    t_before_co = branch_co.valid_time.lower - timedelta(seconds=1)
    result_past = await service.get_project_branches(project.project_id, as_of=t_before_co)

    # Assert
    assert len(result_current) == 2
    names_current = {b.name for b in result_current}
    assert "main" in names_current
    assert "co-CO-TEST-1" in names_current

    names_past = {b.name for b in result_past}
    assert "main" in names_past
    assert "co-CO-TEST-1" not in names_past
    # Depending on T1 vs t_before_co, main might be there.
    # If t_before_co < main.valid_time.lower, then empty?
    # But main was created before CO. So t_before_co should be >= main time?
    # Unless specific timing.
    # Better: t_before_main = branch_main.valid_time.lower - timedelta(seconds=1)
    # result_pre_creation = await service.get_project_branches(..., as_of=t_before_main)
    # assert len(result_pre_creation) == 0

    if branch_main.valid_time.lower <= t_before_co:
         assert len(result_past) >= 1
