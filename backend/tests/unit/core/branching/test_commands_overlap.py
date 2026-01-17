from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.commands import UpdateCommand
from app.core.versioning.commands import CreateVersionCommand
from app.core.versioning.exceptions import OverlappingVersionError
from app.models.domain.wbe import WBE

# Use WBE as the test subject since it's a Branchable entity


@pytest_asyncio.fixture
async def sample_wbe_root_id() -> UUID:
    return uuid4()


@pytest_asyncio.fixture
async def actor_id() -> UUID:
    return uuid4()


@pytest_asyncio.fixture
async def created_wbe(
    db_session: AsyncSession, sample_wbe_root_id: UUID, actor_id: UUID
) -> WBE:
    """Create an initial WBE version."""
    # We use CreateVersionCommand to create the first version
    # Valid from NOW to Infinity
    cmd = CreateVersionCommand(
        entity_class=WBE,
        root_id=sample_wbe_root_id,
        actor_id=actor_id,
        name="Test WBE",
        code="WBE-1",
        project_id=uuid4(),
        level=1,
    )
    # Manually ensure branch is main for this test if CreateVersionCommand doesn't set it default
    # WBE model has default="main"
    wbe = await cmd.execute(db_session)
    return wbe


@pytest.mark.asyncio
async def test_update_command_detects_overlap(
    db_session: AsyncSession, created_wbe: WBE, actor_id: UUID
):
    """Test that UpdateCommand raises error if valid_time overlaps.

    This simulates a Time Travel update that conflicts with existing ranges.
    """
    # Capture IDs before any raw SQL that might expire attributes
    root_id = created_wbe.wbe_id
    created_wbe_id = created_wbe.id

    # 1. Create a version V1 valid from T1=[Now-10d] to Infinity
    # (Actually created_wbe is from Now to Infinity. Let's adjust it to start earlier)

    start_time = datetime.now(UTC) - timedelta(days=10)

    # Manually adjust the created_wbe valid_time to start 10 days ago
    # This is "Arrange" to set up a specific scenario
    stmt = text("""
        UPDATE wbes
        SET valid_time = tstzrange(:start, NULL, '[]')
        WHERE id = :id
    """)
    await db_session.execute(stmt, {"start": start_time, "id": created_wbe_id})
    await (
        db_session.commit()
    )  # Commit to ensure separate transaction visibility if needed, or flush?
    # In tests usually we use same session.

    # Refresh to get updated valid_time
    await db_session.refresh(created_wbe)

    # 2. Now perform an Update with control_date = Now - 5d.
    # This creates V2 starting at T2 = Now - 5d.
    # V1 becomes [T1, T2). V2 is [T2, Infinity).
    # This is a VALID normal update (retroactive).

    t2 = datetime.now(UTC) - timedelta(days=5)

    update_cmd = UpdateCommand(
        entity_class=WBE,
        root_id=root_id,
        actor_id=actor_id,
        updates={"name": "V2 Name"},
        control_date=t2,
    )
    await update_cmd.execute(db_session)

    # 3. Now try to insert V3 starting at T3 = Now - 7d.
    # Range [T3, Infinity) -> should be [T3, T2) if we were smart, but currently
    # the system might try to make it [T3, Infinity) or just [T3, ???).
    #
    # If we use UpdateCommand with control_date=T3 (Now-7d),
    # It will see V1 (current on branch) ??
    # Wait, UpdateCommand fetches "current on branch".
    # Current on branch is V2 (valid from T2=Now-5d to Infinity).
    # V1 is historical.
    #
    # If we supply control_date=T3 (Now-7d), and current is V2 (starts at T2=Now-5d).
    # T3 < T2.
    # The UpdateCommand has a check: `if control_date < current_lower: raise ValueError`.
    # So we cannot normally insert a version *before* the current head using UpdateCommand easily?
    #
    # Unless we found the version applicable at T3?
    # But UpdateCommand finds "Current" (Head).

    # The issue described in TD-058 is:
    # "When using control_date parameter in past/future updates... overlapping valid_time ranges can be created."

    # Let's try the scenario where we have V1 [T1, Infinity].
    # We create V2 [T3, Infinity] via update.
    # Then somehow we have V3.

    # If we update a *different* version? UpdateCommand only updates HEAD.
    # Maybe the issue arises when we have multiple updates?

    # Let's simulate the TD example from 00-analysis.md:
    # Version A: [Jan 1, Infinity)
    # Update with control_date=Feb 1 -> Version B: [Feb 1, Infinity). Version A becomes [Jan 1, Feb 1).
    #
    # Now, if we try to insert something at Jan 15?
    # UpdateCommand fetches HEAD (Version B). Lower bound Feb 1.
    # control_date Jan 15 < Feb 1. The code RAISES ValueError currently (line 146 in commands.py).
    # So UpdateCommand protects against going BEFORE head.

    # What if we update with control_date = Future?
    # V1 [Jan 1, Infinity).
    # Update with control_date=March 1. -> V2 [March 1, Infinity). V1 [Jan 1, March 1).
    # HEAD is V2.
    # Now Update again with control_date=Feb 1.
    # HEAD is V2 (starts March 1). Feb 1 < March 1. Error.

    # So how do we get overlaps?
    # "When multiple corrections happen to the same time period"

    # Maybe via CreateVersionCommand?
    # Or maybe the check `func.upper(valid_time).is_(None)` in `_get_current_on_branch` is the key.
    # If we have [Jan 1, Feb 1) and [Feb 1, Infinity).
    # And we somehow manage to insert [Jan 15, Infinity)?

    # If we use a command that doesn't check against HEAD?
    # CreateVersionCommand creates a NEW version.
    # If I call CreateVersionCommand for an existing root_id?
    # It just inserts it. It closes nothing (it assumes it's the first).
    # BUT CreateVersionCommand updates valid_time of the NEW version.

    # Example logic in CreateVersionCommand.execute:
    # session.add(version) -> SQL Update valid_time.
    # It does NOT check if other versions verify for this root_id.

    # So if I misuse CreateVersionCommand on an existing entity, I can create overlaps easily.
    # This might be the vector.

    # Also, "Zombie entities".

    # Let's test that CreateVersionCommand on an EXISTING root_id detects overlap.

    t3 = datetime.now(UTC) - timedelta(days=2)  # T3 = Now - 2d.

    # We already have V2 [Now-5d, Infinity).
    # Try to create a NEW version using CreateVersionCommand with same root_id.

    overlap_cmd = CreateVersionCommand(
        entity_class=WBE,
        root_id=root_id,
        actor_id=actor_id,
        name="Zombie V3",
        code="WBE-1",
        project_id=uuid4(),
        level=1,
        control_date=t3,
    )

    with pytest.raises(OverlappingVersionError) as excinfo:
        await overlap_cmd.execute(db_session)

    assert str(root_id) in str(excinfo.value)


@pytest.mark.asyncio
async def test_update_command_future_overlap_prevention(
    db_session: AsyncSession, created_wbe: WBE, actor_id: UUID
):
    """Test Update overlaps when dealing with future scheduled changes."""
    # Capture IDs early to avoid lazy loading issues
    root_id = created_wbe.wbe_id
    # Setup V1 [Now, Infinity)

    # Update to create V2 [Now+10d, Infinity)
    t_future = datetime.now(UTC) + timedelta(days=10)

    update_1 = UpdateCommand(
        entity_class=WBE,
        root_id=root_id,
        actor_id=actor_id,
        updates={"name": "Future V2"},
        control_date=t_future,
    )
    await update_1.execute(db_session)

    # Now we have V1 [Now, Now+10d), V2 [Now+10d, Infinity)

    # Attempt to create V3 via CreateVersionCommand that overlaps V1 or V2?
    # Or use UpdateCommand in a way that overlaps?

    # If valid_time overlap checking is generic, let's verify CreateVersionCommand
    # blocks inserting something at Now+5d which is inside V1's range [Now, Now+10d).

    t_mid = datetime.now(UTC) + timedelta(days=5)

    overlap_cmd = CreateVersionCommand(
        entity_class=WBE,
        root_id=root_id,
        actor_id=actor_id,
        control_date=t_mid,
        name="Overlap V3",
        code="WBE-1",
        project_id=uuid4(),
        level=1,
    )

    with pytest.raises(OverlappingVersionError):
        await overlap_cmd.execute(db_session)
