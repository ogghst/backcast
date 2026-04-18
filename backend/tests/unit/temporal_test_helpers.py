"""Temporal test helper functions for EVCS temporal entity testing.

This module provides reusable helper functions to reduce repeated "zombie check"
and temporal query patterns across temporal entity tests.

Common Patterns Covered:
    1. Zombie Check: Entity should not exist before creation, and should exist after
    2. Temporal Consistency: Verify entity state across multiple timestamps
    3. Branch Isolation: Verify STRICT vs MERGE branch modes
    4. Deletion Detection: Verify soft-deleted entities respect temporal boundaries

Example Usage:
    from tests.unit.temporal_test_helpers import (
        assert_created_at_time,
        assert_not_exists_before_time,
        assert_branch_isolation,
    )

    # After creating an entity
    await assert_created_at_time(
        entity_id=project_id,
        as_of_time=T1_after,
        service=service,
        branch="main",
    )

    # Verify zombie check
    await assert_not_exists_before_time(
        entity_id=project_id,
        before_time=T1_before,
        service=service,
        branch="main",
    )
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.versioning.enums import BranchMode
from app.core.versioning.service import TemporalService
from app.models.protocols import VersionableProtocol


async def assert_created_at_time[TVersionable: VersionableProtocol](
    entity_id: UUID,
    as_of_time: datetime,
    service: TemporalService[TVersionable],
    branch: str = "main",
    branch_mode: BranchMode = BranchMode.STRICT,
    custom_assertion: Any | None = None,
) -> TVersionable:
    """Assert that an entity exists at a specific point in time.

    This is the core "after creation" check in the zombie check pattern.
    Verifies that querying at as_of_time returns the expected entity.

    Args:
        entity_id: The root entity ID (e.g., project_id, wbe_id)
        as_of_time: The timestamp to query at (should be after creation)
        service: The temporal service instance (e.g., ProjectService, WBEService)
        branch: Branch name (default: "main")
        branch_mode: Branch resolution mode (default: STRICT)
        custom_assertion: Optional callable to perform additional assertions
                         on the returned entity. Receives the entity as parameter.

    Returns:
        The entity found at the specified time

    Raises:
        AssertionError: If entity is None at the specified time

    Example:
        T1 = datetime(2026, 1, 8, 12, 0, 0, tzinfo=timezone.utc)
        co = await co_service.create_change_order(...)

        # Verify CO exists after creation
        await assert_created_at_time(
            entity_id=co_id,
            as_of_time=T1 + timedelta(hours=1),
            service=co_service,
            branch="main",
            custom_assertion=lambda e: e.code == "CO-2026-001",
        )
    """
    entity = await service.get_as_of(
        entity_id=entity_id,
        as_of=as_of_time,
        branch=branch,
        branch_mode=branch_mode,
    )

    assert entity is not None, (
        f"Entity {entity_id} should exist at {as_of_time} on branch '{branch}' "
        f"with mode {branch_mode.value}"
    )

    if custom_assertion is not None:
        custom_assertion(entity)

    return entity


async def assert_not_exists_before_time[TVersionable: VersionableProtocol](
    entity_id: UUID,
    before_time: datetime,
    service: TemporalService[TVersionable],
    branch: str = "main",
    branch_mode: BranchMode = BranchMode.STRICT,
) -> None:
    """Assert that an entity does NOT exist at a specific point in time.

    This is the core "before creation" check in the zombie check pattern.
    Verifies that querying at before_time returns None.

    Args:
        entity_id: The root entity ID (e.g., project_id, wbe_id)
        before_time: The timestamp to query at (should be before creation)
        service: The temporal service instance
        branch: Branch name (default: "main")
        branch_mode: Branch resolution mode (default: STRICT)

    Raises:
        AssertionError: If entity is found at the specified time

    Example:
        T1 = datetime(2026, 1, 8, 12, 0, 0, tzinfo=timezone.utc)
        T1_before = datetime(2026, 1, 7, 12, 0, 0, tzinfo=timezone.utc)
        co = await co_service.create_change_order(...)

        # Zombie check: CO should NOT exist before T1
        await assert_not_exists_before_time(
            entity_id=co_id,
            before_time=T1_before,
            service=co_service,
            branch="main",
        )
    """
    entity = await service.get_as_of(
        entity_id=entity_id,
        as_of=before_time,
        branch=branch,
        branch_mode=branch_mode,
    )

    assert entity is None, (
        f"Entity {entity_id} should NOT exist at {before_time} on branch '{branch}' "
        f"with mode {branch_mode.value}, but found: {entity}"
    )


async def assert_temporal_consistency[TVersionable: VersionableProtocol](
    entity_id: UUID,
    service: TemporalService[TVersionable],
    time_expectations: dict[datetime, Any],
    branch: str = "main",
    branch_mode: BranchMode = BranchMode.STRICT,
) -> None:
    """Assert entity state consistency across multiple timestamps.

    Verifies that an entity has the expected state at each timestamp.
    Useful for testing time travel across control dates.

    Args:
        entity_id: The root entity ID
        service: The temporal service instance
        time_expectations: Dictionary mapping timestamps to expected values.
                          Values can be:
                          - None: Entity should not exist at this time
                          - callable(entity): Function that asserts on entity
                          - dict: Dictionary of field -> expected value pairs
        branch: Branch name (default: "main")
        branch_mode: Branch resolution mode (default: STRICT)

    Raises:
        AssertionError: If any time point does not match expectations

    Example:
        T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        T1 = datetime(2026, 1, 8, tzinfo=timezone.utc)
        T2 = datetime(2026, 1, 15, tzinfo=timezone.utc)

        # Create at T0, update at T1
        await assert_temporal_consistency(
            entity_id=wbe_id,
            service=wbe_service,
            time_expectations={
                T0: {"name": "Original WBE"},
                T1: {"name": "Updated WBE"},
                T2: lambda e: e.name == "Updated WBE",
            },
            branch="main",
        )
    """
    for as_of_time, expectation in time_expectations.items():
        entity = await service.get_as_of(
            entity_id=entity_id,
            as_of=as_of_time,
            branch=branch,
            branch_mode=branch_mode,
        )

        if expectation is None:
            assert entity is None, (
                f"Entity {entity_id} should NOT exist at {as_of_time}, "
                f"but found: {entity}"
            )
        elif callable(expectation):
            # Expectation is a callable that performs assertions
            assert entity is not None, (
                f"Entity {entity_id} should exist at {as_of_time} for assertion check"
            )
            expectation(entity)
        elif isinstance(expectation, dict):
            # Expectation is a dict of field -> value pairs
            assert entity is not None, (
                f"Entity {entity_id} should exist at {as_of_time} "
                f"for field value checks"
            )
            for field, expected_value in expectation.items():
                actual_value = getattr(entity, field, None)
                assert actual_value == expected_value, (
                    f"Entity {entity_id} field '{field}' at {as_of_time}: "
                    f"expected {expected_value}, got {actual_value}"
                )


async def assert_branch_isolation[TVersionable: VersionableProtocol](
    entity_id: UUID,
    service: TemporalService[TVersionable],
    branch_a: str,
    branch_b: str,
    as_of_time: datetime,
    expect_exists_on_a: bool = True,
    expect_exists_on_b: bool = False,
    branch_mode: BranchMode = BranchMode.STRICT,
) -> None:
    """Assert that an entity has different visibility on different branches.

    Tests the core branch isolation pattern:
    - Entity exists on branch_a but not on branch_b (before branch creation/modification)
    - STRICT mode returns None on branch_b if entity not modified there
    - MERGE mode falls back to main if entity not on branch_b

    Args:
        entity_id: The root entity ID
        service: The temporal service instance
        branch_a: First branch name (e.g., "main")
        branch_b: Second branch name (e.g., "BR-CO-001")
        as_of_time: Timestamp to query at
        expect_exists_on_a: Whether entity should exist on branch_a (default: True)
        expect_exists_on_b: Whether entity should exist on branch_b (default: False)
        branch_mode: Branch mode to use for both queries (default: STRICT)

    Raises:
        AssertionError: If branch isolation does not match expectations

    Example:
        # Create WBE on main, verify not on CO branch
        await assert_branch_isolation(
            entity_id=wbe_id,
            service=wbe_service,
            branch_a="main",
            branch_b="BR-CO-001",
            as_of_time=T1,
            expect_exists_on_a=True,
            expect_exists_on_b=False,
        )
    """
    entity_a = await service.get_as_of(
        entity_id=entity_id,
        as_of=as_of_time,
        branch=branch_a,
        branch_mode=branch_mode,
    )

    entity_b = await service.get_as_of(
        entity_id=entity_id,
        as_of=as_of_time,
        branch=branch_b,
        branch_mode=branch_mode,
    )

    if expect_exists_on_a:
        assert entity_a is not None, (
            f"Entity {entity_id} should exist on branch '{branch_a}' at {as_of_time}"
        )
    else:
        assert entity_a is None, (
            f"Entity {entity_id} should NOT exist on branch '{branch_a}' "
            f"at {as_of_time}"
        )

    if expect_exists_on_b:
        assert entity_b is not None, (
            f"Entity {entity_id} should exist on branch '{branch_b}' at {as_of_time}"
        )
    else:
        assert entity_b is None, (
            f"Entity {entity_id} should NOT exist on branch '{branch_b}' "
            f"at {as_of_time}"
        )


async def assert_merge_mode_fallback[TVersionable: VersionableProtocol](
    entity_id: UUID,
    service: TemporalService[TVersionable],
    source_branch: str,
    as_of_time: datetime,
    main_branch_state: Any | None = None,
) -> TVersionable:
    """Assert that MERGE mode falls back to main branch when entity not on source branch.

    Tests the MERGE mode behavior:
    - STRICT mode returns None if entity not on source branch
    - MERGE mode falls back to main branch

    Args:
        entity_id: The root entity ID
        service: The temporal service instance
        source_branch: The branch to query (e.g., change order branch)
        as_of_time: Timestamp to query at
        main_branch_state: Optional expected state from main branch.
                          Can be a dict of field -> value, or a callable.

    Returns:
        The entity returned from MERGE mode query

    Raises:
        AssertionError: If MERGE mode does not fall back correctly

    Example:
        # MERGE mode should fall back to main
        wbe = await assert_merge_mode_fallback(
            entity_id=wbe_id,
            service=wbe_service,
            source_branch="BR-CO-001",
            as_of_time=T1,
            main_branch_state={"name": "Original WBE"},
        )
    """
    # STRICT mode should return None (entity not on source branch)
    entity_strict = await service.get_as_of(
        entity_id=entity_id,
        as_of=as_of_time,
        branch=source_branch,
        branch_mode=BranchMode.STRICT,
    )

    assert entity_strict is None, (
        f"Entity {entity_id} should NOT exist on branch '{source_branch}' "
        f"with STRICT mode at {as_of_time}"
    )

    # MERGE mode should fall back to main
    entity_merge = await service.get_as_of(
        entity_id=entity_id,
        as_of=as_of_time,
        branch=source_branch,
        branch_mode=BranchMode.MERGE,
    )

    assert entity_merge is not None, (
        f"Entity {entity_id} should be returned from main branch via "
        f"MERGE mode fallback at {as_of_time}"
    )

    if main_branch_state is not None:
        if callable(main_branch_state):
            main_branch_state(entity_merge)
        elif isinstance(main_branch_state, dict):
            for field, expected_value in main_branch_state.items():
                actual_value = getattr(entity_merge, field, None)
                assert actual_value == expected_value, (
                    f"MERGE mode fallback for field '{field}': "
                    f"expected {expected_value}, got {actual_value}"
                )

    return entity_merge


async def assert_zombie_check[TVersionable: VersionableProtocol](
    entity_id: UUID,
    service: TemporalService[TVersionable],
    creation_time: datetime,
    branch: str = "main",
    time_delta_seconds: int = 1,
) -> TVersionable:
    """Perform complete zombie check: entity does not exist before, exists after.

    This is the most common temporal test pattern, checking that:
    - Entity returns None when queried before creation_time
    - Entity returns result when queried after creation_time

    Args:
        entity_id: The root entity ID
        service: The temporal service instance
        creation_time: The time when entity was created
        branch: Branch name (default: "main")
        time_delta_seconds: Time offset before/after creation (default: 1 second)

    Returns:
        The entity found at the time after creation

    Example:
        T1 = datetime(2026, 1, 8, 12, 0, 0, tzinfo=timezone.utc)
        co = await co_service.create_change_order(...)

        # Complete zombie check
        await assert_zombie_check(
            entity_id=co_id,
            service=co_service,
            creation_time=T1,
            branch="main",
        )
    """
    from datetime import timedelta

    before_time = creation_time - timedelta(seconds=time_delta_seconds)
    after_time = creation_time + timedelta(seconds=time_delta_seconds)

    # Should NOT exist before
    await assert_not_exists_before_time(
        entity_id=entity_id,
        before_time=before_time,
        service=service,
        branch=branch,
    )

    # Should exist after
    return await assert_created_at_time(
        entity_id=entity_id,
        as_of_time=after_time,
        service=service,
        branch=branch,
    )


async def assert_deleted_not_visible[TVersionable: VersionableProtocol](
    entity_id: UUID,
    service: TemporalService[TVersionable],
    deletion_time: datetime,
    branch: str = "main",
    time_delta_seconds: int = 1,
) -> None:
    """Assert that a soft-deleted entity is NOT visible after deletion.

    Verifies the zombie check for soft deletes:
    - Entity is visible when querying before deletion_time
    - Entity returns None when querying after deletion_time

    Args:
        entity_id: The root entity ID
        service: The temporal service instance
        deletion_time: The time when entity was soft-deleted
        branch: Branch name (default: "main")
        time_delta_seconds: Time offset after deletion (default: 1 second)

    Raises:
        AssertionError: If deletion visibility is incorrect

    Example:
        await service.soft_delete(entity_id=wbe_id, actor_id=actor_id)
        await db_session.commit()

        # Verify zombie check for deletion
        await assert_deleted_not_visible(
            entity_id=wbe_id,
            service=wbe_service,
            deletion_time=datetime.now(timezone.utc),
        )
    """
    from datetime import timedelta

    before_deletion = deletion_time - timedelta(seconds=time_delta_seconds)
    after_deletion = deletion_time + timedelta(seconds=time_delta_seconds)

    # Should be visible before deletion
    entity_before = await service.get_as_of(
        entity_id=entity_id,
        as_of=before_deletion,
        branch=branch,
    )
    assert entity_before is not None, (
        f"Entity {entity_id} should be visible before deletion at {before_deletion}"
    )

    # Should NOT be visible after deletion
    entity_after = await service.get_as_of(
        entity_id=entity_id,
        as_of=after_deletion,
        branch=branch,
    )
    assert entity_after is None, (
        f"Entity {entity_id} should NOT be visible after deletion at {after_deletion} "
        f"(zombie check failed)"
    )


async def assert_branch_merge_preserves_source[TVersionable: VersionableProtocol](
    entity_id: UUID,
    service: TemporalService[TVersionable],
    source_branch: str,
    target_branch: str,
    as_of_time: datetime,
    expected_state: dict[str, Any],
) -> None:
    """Assert that source branch is preserved after merge operation.

    After a merge, both branches should have the merged state:
    - target_branch (e.g., "main") has the merged changes
    - source_branch (e.g., "BR-CO-001") is preserved with original state

    Args:
        entity_id: The root entity ID
        service: The temporal service instance
        source_branch: The branch that was merged from
        target_branch: The branch that was merged to (usually "main")
        as_of_time: Timestamp to query at (after merge)
        expected_state: Expected state dict (field -> value) on both branches

    Raises:
        AssertionError: If either branch does not have expected state

    Example:
        await co_service.merge_change_order(...)

        # Verify both branches have merged state
        await assert_branch_merge_preserves_source(
            entity_id=wbe_id,
            service=wbe_service,
            source_branch="BR-CO-001",
            target_branch="main",
            as_of_time=T3,
            expected_state={"name": "Assembly Station 1 - EXPANDED"},
        )
    """
    target_entity = await service.get_as_of(
        entity_id=entity_id,
        as_of=as_of_time,
        branch=target_branch,
        branch_mode=BranchMode.STRICT,
    )

    source_entity = await service.get_as_of(
        entity_id=entity_id,
        as_of=as_of_time,
        branch=source_branch,
        branch_mode=BranchMode.STRICT,
    )

    assert target_entity is not None, (
        f"Entity {entity_id} should exist on target branch '{target_branch}' "
        f"after merge at {as_of_time}"
    )

    assert source_entity is not None, (
        f"Entity {entity_id} should still exist on source branch '{source_branch}' "
        f"after merge at {as_of_time}"
    )

    for field, expected_value in expected_state.items():
        target_value = getattr(target_entity, field, None)
        source_value = getattr(source_entity, field, None)

        assert target_value == expected_value, (
            f"Target branch field '{field}' after merge: "
            f"expected {expected_value}, got {target_value}"
        )

        assert source_value == expected_value, (
            f"Source branch field '{field}' after merge: "
            f"expected {expected_value}, got {source_value}"
        )


async def assert_temporal_range_validity[TVersionable: VersionableProtocol](
    entity_id: UUID,
    service: TemporalService[TVersionable],
) -> None:
    """Assert that all temporal versions have valid time ranges (no empty ranges).

    Checks the version history to ensure no version has an empty valid_time range,
    which would indicate a temporal integrity issue.

    Args:
        entity_id: The root entity ID
        service: The temporal service instance (must implement get_history)

    Raises:
        AssertionError: If any version has an empty temporal range
        AttributeError: If service does not implement get_history

    Example:
        # After performing temporal operations
        await assert_temporal_range_validity(
            entity_id=wbe_id,
            service=wbe_service,
        )
    """
    if not hasattr(service, "get_history"):
        raise AttributeError(
            f"Service {service.__class__.__name__} does not implement get_history()"
        )

    history = await service.get_history(root_id=entity_id)

    for version in history:
        if hasattr(version, "valid_time"):
            valid_time = version.valid_time
            if valid_time.upper is not None:
                assert valid_time.lower < valid_time.upper, (
                    f"Version {version.id} of entity {entity_id} has empty "
                    f"valid_time range: [{valid_time.lower}, {valid_time.upper}]"
                )


async def assert_entity_unchanged_on_branch[TVersionable: VersionableProtocol](
    entity_id: UUID,
    service: TemporalService[TVersionable],
    branch: str,
    as_of_time: datetime,
    expected_state: dict[str, Any],
) -> TVersionable:
    """Assert that an entity has not changed on a specific branch at a given time.

    Useful for verifying that changes on one branch do not affect other branches
    (branch isolation verification).

    Args:
        entity_id: The root entity ID
        service: The temporal service instance
        branch: The branch to check
        as_of_time: Timestamp to query at
        expected_state: Expected state dict (field -> value)

    Returns:
        The entity found (for additional assertions if needed)

    Raises:
        AssertionError: If entity state does not match expected

    Example:
        # Verify main branch unchanged after CO branch modification
        await assert_entity_unchanged_on_branch(
            entity_id=wbe_id,
            service=wbe_service,
            branch="main",
            as_of_time=T2,
            expected_state={"name": "Original WBE", "code": "1.1"},
        )
    """
    entity = await service.get_as_of(
        entity_id=entity_id,
        as_of=as_of_time,
        branch=branch,
        branch_mode=BranchMode.STRICT,
    )

    assert entity is not None, (
        f"Entity {entity_id} should exist on branch '{branch}' at {as_of_time}"
    )

    for field, expected_value in expected_state.items():
        actual_value = getattr(entity, field, None)
        assert actual_value == expected_value, (
            f"Entity {entity_id} on branch '{branch}' field '{field}' at {as_of_time}: "
            f"expected {expected_value}, got {actual_value} "
            f"(branch may have been unexpectedly modified)"
        )

    return entity
