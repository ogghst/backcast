"""Integration tests for BranchableService using Project entity."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.models.domain.project import Project


@pytest.mark.asyncio
async def test_branch_service_lifecycle(db_session: AsyncSession):
    """Verify full lifecycle of branched entity via service."""
    service = BranchableService(Project, db_session)
    root_id = uuid4()
    actor_id = uuid4()

    # 1. Create Root (Main)
    # ------------------------------------------------------------------
    v1 = await service.create_root(
        root_id=root_id,
        actor_id=actor_id,
        branch="main",
        name="Project Alpha",
        code="PROJ-001",
        description="Initial Plan",
        budget=1000.0,
    )
    assert v1.project_id == root_id
    assert v1.branch == "main"
    assert v1.name == "Project Alpha"
    v1_id = v1.id

    # 2. Create Feature Branch
    # ------------------------------------------------------------------
    v2 = await service.create_branch(
        root_id=root_id,
        actor_id=actor_id,
        new_branch="feature/scope-increase",
        from_branch="main",
    )
    assert v2.branch == "feature/scope-increase"
    assert v2.parent_id == v1_id
    assert v2.name == "Project Alpha"  # Cloned content
    v2_id = v2.id

    # 3. Update Feature Branch
    # ------------------------------------------------------------------
    v3 = await service.update(
        root_id=root_id,
        actor_id=actor_id,
        branch="feature/scope-increase",
        name="Project Alpha Plus",
        budget=5000.0,
    )
    assert v3.branch == "feature/scope-increase"
    assert v3.name == "Project Alpha Plus"
    assert v3.budget == 5000.0
    assert v3.id != v2_id
    v3_id = v3.id

    # 4. Merge Feature -> Main
    # ------------------------------------------------------------------
    merged = await service.merge_branch(
        root_id=root_id,
        actor_id=actor_id,
        source_branch="feature/scope-increase",
        target_branch="main",
    )
    assert merged.branch == "main"
    assert merged.name == "Project Alpha Plus"
    assert merged.budget == 5000.0
    assert merged.parent_id == v1_id  # Linked to previous main tip
    assert merged.merge_from_branch == "feature/scope-increase"
    merged_id = merged.id

    # 5. Revert Main to V1 state
    reverted = await service.revert(
        root_id=root_id, actor_id=actor_id, branch="main", to_version_id=v1_id
    )
    assert reverted.branch == "main"
    assert reverted.name == "Project Alpha"  # Restored content
    assert reverted.budget == 1000.0
    assert reverted.parent_id == merged_id  # History verified

    # 6. Verify Current State
    current_main = await service.get_as_of(root_id, branch="main")
    assert current_main is not None
    assert current_main.id == reverted.id

    current_feature = await service.get_as_of(root_id, branch="feature/scope-increase")
    assert current_feature is not None
    assert current_feature.id == v3_id
