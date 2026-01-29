import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from app.models.domain.branch import Branch
from app.models.domain.project import Project
from app.services.branch_service import BranchService
from sqlalchemy import select

@pytest.mark.asyncio
async def test_get_as_of(db_session):
    # Arrange
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-BS-001",
        name="Test BS 1",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)
    await db_session.flush()

    service = BranchService(db_session)
    
    # Create branch at T1
    branch_name = "temporal-branch-svc"
    branch = Branch(
        name=branch_name,
        project_id=project.project_id,
        created_by=user_id
    )
    db_session.add(branch)
    await db_session.flush()
    await db_session.refresh(branch) 
    # T1 = created time
    
    t1 = datetime.now(UTC) 
    
    # Act
    # Query at T0 (before creation) uses valid_time logic
    # But valid_time defaults to NOW(). So T0 < Valid Time
    t0 = t1 - timedelta(hours=1)
    
    result_t0 = await service.get_as_of(branch_name, project.project_id, t0)
    result_t1 = await service.get_as_of(branch_name, project.project_id, t1 + timedelta(seconds=1))

    # Assert
    assert result_t0 is None
    assert result_t1 is not None
    assert result_t1.name == branch_name

@pytest.mark.asyncio
async def test_lock_update_in_place(db_session):
    # Arrange
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-BS-002",
        name="Test BS 2",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)
    await db_session.flush()
    
    branch = Branch(
        name="lock-test-branch",
        project_id=project.project_id,
        created_by=user_id,
        locked=False
    )
    db_session.add(branch)
    await db_session.flush()
    await db_session.refresh(branch)
    original_id = branch.branch_id
    
    service = BranchService(db_session)
    
    # Act: Lock
    await service.lock("lock-test-branch", project.project_id)
    
    # Assert: Count versions. Should be 1.
    result = await db_session.execute(select(Branch).where(Branch.name == "lock-test-branch"))
    versions = result.scalars().all()
    assert len(versions) == 1
    assert versions[0].locked is True
    assert versions[0].branch_id == original_id
