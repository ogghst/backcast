from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.project import Project

UTC = UTC


@pytest.mark.asyncio
async def test_create_version_command_with_control_date(db_session):
    """CreateVersionCommand should set valid_time to control_date."""
    # Use a date in the future (30 days from now) to ensure transaction_time < control_date
    control_date = datetime.now(UTC) + timedelta(days=30)
    actor_id = uuid4()

    # Passing control_date to init - currently this will likely be treated as a field
    # or fail if not handled. But if it goes into **fields, it might crash the model init
    # unless we strip it. We want to test that we CAN pass it and it WORKS.
    root_id = uuid4()

    # Passing control_date to init - currently this will likely be treated as a field
    # or fail if not handled. But if it goes into **fields, it might crash the model init
    # unless we strip it. We want to test that we CAN pass it and it WORKS.
    cmd = CreateVersionCommand(
        Project,
        root_id,
        actor_id,
        control_date=control_date,
        project_id=root_id,
        name="Test Project",
        budget=1000.0,
        code="TEST-001",
        description="Test Desc",
        # Required fields for Project might vary, guessing minimal set
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=30),
    )

    # This execution should set the valid_time to control_date
    try:
        project = await cmd.execute(db_session)
    except TypeError:
        # If __init__ doesn't accept control_date specifically and it goes to **fields,
        # and Project model rejects it, that's also a failure we want to fix.
        pytest.fail("CreateVersionCommand rejected control_date argument")

    # Refresh to ensure we have DB values
    await db_session.refresh(project)

    # valid_time should start at control_date
    # Note: Using almost equal/check implementation details if exact match issues arise
    assert project.valid_time.lower == control_date

    # transaction_time should be approximately NOW (2026-01-10)
    # control_date is 2026-03-03 (future)
    # so transaction_time (now) < valid_time (future)
    assert project.transaction_time.lower < control_date


@pytest.mark.asyncio
async def test_update_version_command_with_control_date(db_session):
    """UpdateVersionCommand should close old version at control_date and start new at control_date."""
    from app.core.versioning.commands import UpdateVersionCommand

    # 1. Create a project using existing command (valid_time defaults to NOW, which is 2026-01-10)
    actor_id = uuid4()
    root_id = uuid4()
    cmd = CreateVersionCommand(
        Project,
        root_id,
        actor_id,
        project_id=root_id,
        name="Original Name",
        budget=100.0,
        code="TEST-UPD-001",
        description="Desc",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=5),
    )
    await cmd.execute(db_session)

    # 2. Update with control_date (e.g., 5 days later)
    # Using specific future date to distinguish from now()
    control_date = datetime.now(UTC) + timedelta(days=5)

    update_cmd = UpdateVersionCommand(
        Project, root_id, actor_id, control_date=control_date, name="Updated Name"
    )

    try:
        new_version = await update_cmd.execute(db_session)
    except TypeError:
        pytest.fail("UpdateVersionCommand rejected control_date argument")

    # 3. Assertions
    # Check new version starts at control_date
    delta = timedelta(seconds=1)
    assert control_date - delta <= new_version.valid_time.lower <= control_date + delta

    # Check old version closed at control_date
    stmt = select(Project).where(
        Project.project_id == root_id, Project.id != new_version.id
    )
    result = await db_session.execute(stmt)
    old_version = result.scalar_one()

    assert old_version.valid_time.upper is not None
    assert control_date - delta <= old_version.valid_time.upper <= control_date + delta


@pytest.mark.asyncio
async def test_soft_delete_command_with_control_date(db_session):
    """SoftDeleteCommand should set deleted_at to control_date."""
    from app.core.versioning.commands import SoftDeleteCommand

    actor_id = uuid4()
    root_id = uuid4()

    # Create project
    cmd = CreateVersionCommand(
        Project,
        root_id,
        actor_id,
        project_id=root_id,
        name="To Delete",
        budget=100.0,
        code="TEST-DEL-001",
        description="Desc",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=5),
    )
    await cmd.execute(db_session)

    # Delete with control_date (future/past)
    control_date = datetime(2027, 1, 1, tzinfo=UTC)

    del_cmd = SoftDeleteCommand(Project, root_id, actor_id, control_date=control_date)

    try:
        deleted_project = await del_cmd.execute(db_session)
    except TypeError:
        pytest.fail("SoftDeleteCommand rejected control_date argument")

    assert deleted_project.deleted_at == control_date
    assert deleted_project.deleted_by == actor_id
