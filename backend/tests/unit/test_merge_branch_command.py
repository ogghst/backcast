"""Unit tests for MergeBranchCommand with control_date parameter.

Tests follow TDD methodology: RED-GREEN-REFACTOR.

Test IDs from Option 2 Plan:
- T-001: test_merge_branch_with_explicit_control_date
- T-002: test_merge_branch_with_control_date_none
- T-003: test_merge_branch_control_date_in_past
- T-004: test_merge_branch_control_date_utc_aware
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.commands import MergeBranchCommand
from app.models.domain.project import Project
from app.models.domain.user import User
from app.models.schemas.project import ProjectCreate, ProjectUpdate


@pytest.fixture
def admin_user() -> User:
    """Create admin user fixture for testing."""
    return User(
        id=uuid4(),
        user_id=uuid4(),
        email="admin@example.com",
        is_active=True,
        role="admin",
        full_name="Admin User",
        hashed_password="hash",
        created_by=uuid4(),
    )


@pytest.mark.asyncio
async def test_merge_branch_with_explicit_control_date(
    session: AsyncSession,
    admin_user,
    sample_project,
):
    """T-001: Should use provided control_date for valid_time.lower.

    When control_date is explicitly provided, the merge operation should use
    that timestamp for the merged version's valid_time.lower bound.
    """
    # Arrange
    from app.services.project import ProjectService

    service = ProjectService(session)
    control_date = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

    # Create initial version on main
    project = await service.create_project(
        project_in=ProjectCreate(code="TEST-001", name="Original", budget=Decimal("100000")),
        actor_id=admin_user.user_id,
        control_date=datetime(2026, 1, 10, tzinfo=UTC),
    )

    # Create branch
    await service.create_branch(
        root_id=project.project_id,
        actor_id=admin_user.user_id,
        new_branch="BR-001",
        control_date=datetime(2026, 1, 11, tzinfo=UTC),
    )

    # Modify on branch
    await service.update_project(
        root_id=project.project_id,
        project_in=ProjectUpdate(name="Modified on Branch"),
        actor_id=admin_user.user_id,
        branch="BR-001",
        control_date=datetime(2026, 1, 12, tzinfo=UTC),
    )

    # Act: Merge with explicit control_date
    cmd = MergeBranchCommand(
        entity_class=Project,
        root_id=project.project_id,
        actor_id=admin_user.user_id,
        source_branch="BR-001",
        target_branch="main",
        control_date=control_date,
    )
    merged = await cmd.execute(session)

    # Assert: Verify merged version valid_time starts at control_date
    assert merged.valid_time.lower == control_date, (
        f"Merged version valid_time.lower should be {control_date}, "
        f"but got {merged.valid_time.lower}"
    )
    assert merged.name == "Modified on Branch"


@pytest.mark.asyncio
async def test_merge_branch_with_control_date_none(
    session: AsyncSession,
    admin_user,
    sample_project,
):
    """T-002: Should use datetime.now(UTC) when control_date is None.

    When control_date is None (default), the merge operation should use
    datetime.now(UTC) for the merged version's valid_time.lower bound.
    """
    # Arrange
    from app.services.project import ProjectService

    service = ProjectService(session)
    before_merge = datetime.now(UTC)

    # Create initial version on main
    project = await service.create_project(
        project_in=ProjectCreate(code="TEST-002", name="Original", budget=Decimal("100000")),
        actor_id=admin_user.user_id,
        control_date=datetime(2026, 1, 10, tzinfo=UTC),
    )

    # Create branch
    await service.create_branch(
        root_id=project.project_id,
        actor_id=admin_user.user_id,
        new_branch="BR-002",
        control_date=datetime(2026, 1, 11, tzinfo=UTC),
    )

    # Modify on branch
    await service.update_project(
        root_id=project.project_id,
        project_in=ProjectUpdate(name="Modified on Branch"),
        actor_id=admin_user.user_id,
        branch="BR-002",
        control_date=datetime(2026, 1, 12, tzinfo=UTC),
    )

    # Act: Merge without control_date (default behavior)
    cmd = MergeBranchCommand(
        entity_class=Project,
        root_id=project.project_id,
        actor_id=admin_user.user_id,
        source_branch="BR-002",
        target_branch="main",
        control_date=None,  # Explicitly None
    )
    merged = await cmd.execute(session)

    after_merge = datetime.now(UTC)

    # Assert: Verify merged version valid_time starts between before/after
    assert before_merge <= merged.valid_time.lower <= after_merge, (
        f"Merged version valid_time.lower should be between {before_merge} and {after_merge}, "
        f"but got {merged.valid_time.lower}"
    )
    assert merged.name == "Modified on Branch"


@pytest.mark.asyncio
async def test_merge_branch_control_date_in_past(
    session: AsyncSession,
    admin_user,
    sample_project,
):
    """T-003: Should successfully use past timestamp as control_date.

    Merge should work with control_date in the past, enabling time-travel
    scenarios and deterministic testing.
    """
    # Arrange
    from app.services.project import ProjectService

    service = ProjectService(session)
    past_date = datetime(2025, 12, 25, 10, 30, 0, tzinfo=UTC)  # Past date

    # Create initial version on main (before past_date)
    project = await service.create_project(
        project_in=ProjectCreate(code="TEST-003", name="Original", budget=Decimal("100000")),
        actor_id=admin_user.user_id,
        control_date=datetime(2025, 12, 20, tzinfo=UTC),
    )

    # Create branch (before past_date)
    await service.create_branch(
        root_id=project.project_id,
        actor_id=admin_user.user_id,
        new_branch="BR-003",
        control_date=datetime(2025, 12, 22, tzinfo=UTC),
    )

    # Modify on branch (before past_date)
    await service.update_project(
        root_id=project.project_id,
        project_in=ProjectUpdate(name="Modified on Branch"),
        actor_id=admin_user.user_id,
        branch="BR-003",
        control_date=datetime(2025, 12, 24, tzinfo=UTC),
    )

    # Act: Merge with past control_date
    cmd = MergeBranchCommand(
        entity_class=Project,
        root_id=project.project_id,
        actor_id=admin_user.user_id,
        source_branch="BR-003",
        target_branch="main",
        control_date=past_date,
    )
    merged = await cmd.execute(session)

    # Assert: Verify merged version valid_time starts at past_date
    assert merged.valid_time.lower == past_date, (
        f"Merged version valid_time.lower should be {past_date}, "
        f"but got {merged.valid_time.lower}"
    )
    assert merged.name == "Modified on Branch"


@pytest.mark.asyncio
async def test_merge_branch_control_date_utc_aware(
    session: AsyncSession,
    admin_user,
    sample_project,
):
    """T-004: Should require timezone-aware datetime.

    Merge should accept only timezone-aware datetime objects with tzinfo=UTC.
    Naive datetimes should be rejected or converted to UTC-aware.
    """
    # Arrange
    from app.services.project import ProjectService

    service = ProjectService(session)

    # Create initial version on main
    project = await service.create_project(
        project_in=ProjectCreate(code="TEST-004", name="Original", budget=Decimal("100000")),
        actor_id=admin_user.user_id,
        control_date=datetime(2026, 1, 10, tzinfo=UTC),
    )

    # Create branch
    await service.create_branch(
        root_id=project.project_id,
        actor_id=admin_user.user_id,
        new_branch="BR-004",
        control_date=datetime(2026, 1, 11, tzinfo=UTC),
    )

    # Modify on branch
    await service.update_project(
        root_id=project.project_id,
        project_in=ProjectUpdate(name="Modified on Branch"),
        actor_id=admin_user.user_id,
        branch="BR-004",
        control_date=datetime(2026, 1, 12, tzinfo=UTC),
    )

    # Act: Merge with UTC-aware control_date
    utc_aware_date = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    cmd = MergeBranchCommand(
        entity_class=Project,
        root_id=project.project_id,
        actor_id=admin_user.user_id,
        source_branch="BR-004",
        target_branch="main",
        control_date=utc_aware_date,
    )
    merged = await cmd.execute(session)

    # Assert: Verify merge accepts UTC-aware datetime
    assert merged.valid_time.lower == utc_aware_date, (
        f"Merged version valid_time.lower should be {utc_aware_date}, "
        f"but got {merged.valid_time.lower}"
    )
    assert merged.valid_time.lower.tzinfo == UTC, (
        f"Merged version valid_time.lower should be UTC-aware, "
        f"but got tzinfo={merged.valid_time.lower.tzinfo}"
    )
