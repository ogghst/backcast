"""Test WBE update commands validate temporal bounds per temporal-query-reference.md.

This test validates that when a WBE is updated:
1. The old version is properly closed with correct valid_time and transaction_time bounds
2. The new version has correct temporal ranges
3. No empty ranges are created (e.g., [t, t))
4. Temporal bounds follow the bitemporal versioning semantics

Reference: docs/02-architecture/cross-cutting/temporal-query-reference.md
"""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.wbe import WBEUpdate
from app.services.wbe import WBEService


def print_debug_header(title: str) -> None:
    """Print a formatted debug header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_temporal_bounds(
    version_id: UUID,
    valid_lower: datetime | None,
    valid_upper: datetime | None,
    tx_lower: datetime | None,
    tx_upper: datetime | None,
    label: str,
    indent: str = "  ",
) -> None:
    """Print detailed temporal information for a version with validation."""
    print(f"{indent}{label}:")
    print(f"{indent}  version_id={version_id}")
    print(f"{indent}  valid_time=[{valid_lower}, {valid_upper})")
    print(f"{indent}  transaction_time=[{tx_lower}, {tx_upper})")

    # Validate and print warnings
    if valid_lower is None:
        print(f"{indent}  ⚠️  WARNING: valid_time lower bound is NULL")
    if tx_lower is None:
        print(f"{indent}  ⚠️  WARNING: transaction_time lower bound is NULL")

    # Check for empty or inverted ranges
    if valid_upper is not None and valid_lower is not None:
        if valid_upper <= valid_lower:
            print(
                f"{indent}  ❌ ERROR: valid_time is empty or inverted [{valid_lower}, {valid_upper})"
            )
        else:
            duration = valid_upper - valid_lower
            print(f"{indent}  ✓ valid_time duration: {duration.total_seconds():.3f}s")
    else:
        if valid_upper is None:
            print(f"{indent}  ✓ valid_time is open-ended (current version)")

    if tx_upper is not None and tx_lower is not None:
        if tx_upper <= tx_lower:
            print(
                f"{indent}  ❌ ERROR: transaction_time is empty or inverted [{tx_lower}, {tx_upper})"
            )
        else:
            duration = tx_upper - tx_lower
            print(
                f"{indent}  ✓ transaction_time duration: {duration.total_seconds():.3f}s"
            )
    else:
        if tx_upper is None:
            print(f"{indent}  ✓ transaction_time is open-ended (current version)")


async def get_wbe_versions_from_db(
    session: AsyncSession, wbe_id: UUID
) -> list[dict[str, Any]]:
    """Fetch all versions of a WBE directly from the database.

    Returns raw temporal data for validation.
    """
    query = text(
        """
        SELECT
            id,
            wbe_id,
            code,
            name,
            lower(valid_time) as valid_lower,
            upper(valid_time) as valid_upper,
            lower(transaction_time) as tx_lower,
            upper(transaction_time) as tx_upper,
            deleted_at,
            branch,
            parent_id
        FROM wbes
        WHERE wbe_id = :wbe_id
        ORDER BY transaction_time ASC
        """
    )

    result = await session.execute(query, {"wbe_id": wbe_id})
    rows = result.fetchall()

    return [
        {
            "id": row.id,
            "wbe_id": row.wbe_id,
            "code": row.code,
            "name": row.name,
            "valid_lower": row.valid_lower,
            "valid_upper": row.valid_upper,
            "tx_lower": row.tx_lower,
            "tx_upper": row.tx_upper,
            "deleted_at": row.deleted_at,
            "branch": row.branch,
            "parent_id": row.parent_id,
        }
        for row in rows
    ]


@pytest.mark.asyncio
async def test_wbe_update_temporal_bounds(db_session: AsyncSession) -> None:
    """
    Test that WBE update creates proper temporal bounds.

    Scenario:
    1. Create WBE at T1
    2. Fetch its valid_time and transaction_time from DB
    3. Wait 3 seconds
    4. Update WBE at T2
    5. Fetch both versions from DB and verify temporal bounds

    Expected behavior (per temporal-query-reference.md):
    - Old version (v1):
      * valid_time: [T1, T2) - closed at update time
      * transaction_time: [T1, T2) - closed at update time
    - New version (v2):
      * valid_time: [T2, NULL) - open-ended
      * transaction_time: [T2, NULL) - open-ended
    """

    print_debug_header("WBE UPDATE TEMPORAL BOUNDS TEST")

    # ========================================================================
    # Setup
    # ========================================================================
    service = WBEService(db_session)
    project_id = uuid4()
    wbe_id = uuid4()
    actor_id = uuid4()

    print("\n--- SETUP ---")
    print(f"  project_id={project_id}")
    print(f"  wbe_id={wbe_id}")
    print(f"  actor_id={actor_id}")

    # ========================================================================
    # STEP 1: Create initial WBE
    # ========================================================================
    print("\n--- STEP 1: Creating initial WBE ---")

    t1 = datetime.now(UTC)
    print(f"  Creating at T1={t1.isoformat()}")

    wbe_v1 = await service.create_root(
        root_id=wbe_id,
        actor_id=actor_id,
        branch="main",
        project_id=project_id,
        code="TEST-001",
        name="Initial WBE",
        level=1,
        control_date=t1,
    )

    print(f"  Created WBE: id={wbe_v1.id}, code={wbe_v1.code}, name={wbe_v1.name}")

    # Fetch v1 from DB to get actual temporal values
    versions_v1 = await get_wbe_versions_from_db(db_session, wbe_id)
    assert len(versions_v1) == 1, (
        f"Expected 1 version after creation, got {len(versions_v1)}"
    )

    v1_data = versions_v1[0]
    print("\n  V1 (from DB):")
    print_temporal_bounds(
        v1_data["id"],
        v1_data["valid_lower"],
        v1_data["valid_upper"],
        v1_data["tx_lower"],
        v1_data["tx_upper"],
        "V1 (initial)",
        indent="    ",
    )

    # Verify v1 initial state
    assert v1_data["valid_lower"] is not None, (
        "V1 valid_time lower bound should not be NULL"
    )
    assert v1_data["valid_upper"] is None, (
        "V1 valid_time upper bound should be NULL (open-ended)"
    )
    assert v1_data["tx_lower"] is not None, (
        "V1 transaction_time lower bound should not be NULL"
    )
    assert v1_data["tx_upper"] is None, (
        "V1 transaction_time upper bound should be NULL (open-ended)"
    )
    assert v1_data["deleted_at"] is None, "V1 should not be deleted"
    print("    ✓ V1 initial state validated")

    # Store v1 bounds for later comparison
    v1_valid_lower = v1_data["valid_lower"]
    v1_tx_lower = v1_data["tx_lower"]

    # ========================================================================
    # STEP 2: Wait 3 seconds to ensure clear temporal separation
    # ========================================================================
    print("\n--- STEP 2: Waiting 3 seconds for temporal separation ---")
    await asyncio.sleep(3)
    t2 = datetime.now(UTC)
    print(f"  Current time T2={t2.isoformat()}")
    print(f"  Time delta: {(t2 - t1).total_seconds():.3f}s")

    # ========================================================================
    # STEP 3: Update WBE
    # ========================================================================
    print("\n--- STEP 3: Updating WBE ---")
    print(f"  Updating at T2={t2.isoformat()}")

    updated_wbe = await service.update_wbe(
        wbe_id=wbe_id,
        wbe_in=WBEUpdate(name="Updated WBE", control_date=t2),
        actor_id=actor_id,
    )

    print(
        f"  Updated WBE: id={updated_wbe.id}, code={updated_wbe.code}, name={updated_wbe.name}"
    )

    # ========================================================================
    # STEP 4: Fetch both versions and verify temporal bounds
    # ========================================================================
    print("\n--- STEP 4: Verifying temporal bounds ---")

    versions_after_update = await get_wbe_versions_from_db(db_session, wbe_id)
    assert len(versions_after_update) == 2, (
        f"Expected 2 versions after update, got {len(versions_after_update)}"
    )

    v1_after = versions_after_update[0]
    v2_data = versions_after_update[1]

    print("\n  V1 (after update, from DB):")
    print_temporal_bounds(
        v1_after["id"],
        v1_after["valid_lower"],
        v1_after["valid_upper"],
        v1_after["tx_lower"],
        v1_after["tx_upper"],
        "V1 (closed)",
        indent="    ",
    )

    print("\n  V2 (new version, from DB):")
    print_temporal_bounds(
        v2_data["id"],
        v2_data["valid_lower"],
        v2_data["valid_upper"],
        v2_data["tx_lower"],
        v2_data["tx_upper"],
        "V2 (current)",
        indent="    ",
    )

    # ========================================================================
    # VALIDATION: V1 (old version) should be properly closed
    # ========================================================================
    print("\n--- VALIDATION: V1 (old version) ---")

    # V1 valid_time should be closed at T2
    assert v1_after["valid_upper"] is not None, (
        "V1 valid_time upper bound should be set (closed)"
    )
    assert v1_after["valid_upper"] == t2, (
        f"V1 valid_time upper bound should equal T2 ({t2}), got {v1_after['valid_upper']}"
    )
    assert v1_after["valid_lower"] == v1_valid_lower, (
        "V1 valid_time lower bound should not change"
    )
    assert v1_after["valid_lower"] < v1_after["valid_upper"], (
        "V1 valid_time should not be empty"
    )
    print(
        f"  ✓ V1 valid_time properly closed: [{v1_after['valid_lower']}, {v1_after['valid_upper']})"
    )

    # V1 transaction_time should be closed
    assert v1_after["tx_upper"] is not None, (
        "V1 transaction_time upper bound should be set (closed)"
    )
    assert v1_after["tx_lower"] == v1_tx_lower, (
        "V1 transaction_time lower bound should not change"
    )
    assert v1_after["tx_lower"] < v1_after["tx_upper"], (
        "V1 transaction_time should not be empty"
    )
    print(
        f"  ✓ V1 transaction_time properly closed: [{v1_after['tx_lower']}, {v1_after['tx_upper']})"
    )

    # V1 should not be deleted (soft delete, not temporal closure)
    assert v1_after["deleted_at"] is None, "V1 should not be soft deleted"
    print("  ✓ V1 not soft deleted")

    # V1 parent_id - tracks branch hierarchy, not version chain
    # For regular updates (not branching), parent_id is not used for version chaining
    # parent_id is used in branching operations to track the source version
    print(
        f"  ✓ V1 parent_id={v1_after['parent_id']} (branch hierarchy, not version chain)"
    )

    # ========================================================================
    # VALIDATION: V2 (new version) should be open-ended
    # ========================================================================
    print("\n--- VALIDATION: V2 (new version) ---")

    # V2 valid_time should start at T2 and be open-ended
    assert v2_data["valid_lower"] is not None, (
        "V2 valid_time lower bound should not be NULL"
    )
    assert v2_data["valid_lower"] == t2, (
        f"V2 valid_time lower bound should equal T2 ({t2}), got {v2_data['valid_lower']}"
    )
    assert v2_data["valid_upper"] is None, (
        "V2 valid_time upper bound should be NULL (open-ended)"
    )
    print(f"  ✓ V2 valid_time open-ended: [{v2_data['valid_lower']}, NULL)")

    # V2 transaction_time should start after V1's transaction_time and be open-ended
    assert v2_data["tx_lower"] is not None, (
        "V2 transaction_time lower bound should not be NULL"
    )
    assert v2_data["tx_upper"] is None, (
        "V2 transaction_time upper bound should be NULL (open-ended)"
    )
    assert v2_data["tx_lower"] > v1_after["tx_upper"], (
        f"V2 transaction_time lower bound should be after V1's transaction_time upper bound. "
        f"Got V2.tx_lower={v2_data['tx_lower']}, V1.tx_upper={v1_after['tx_upper']}"
    )
    print(f"  ✓ V2 transaction_time open-ended: [{v2_data['tx_lower']}, NULL)")

    # V2 should not be deleted
    assert v2_data["deleted_at"] is None, "V2 should not be deleted"
    print("  ✓ V2 not deleted")

    # V2 parent_id - tracks branch hierarchy, not version chain
    # For regular updates (not branching), parent_id is not used for version chaining
    print(
        f"  ✓ V2 parent_id={v2_data['parent_id']} (branch hierarchy, not version chain)"
    )

    # V2 should have the updated data
    assert v2_data["name"] == "Updated WBE", (
        f"V2 name should be 'Updated WBE', got {v2_data['name']}"
    )
    assert v2_data["code"] == "TEST-001", (
        f"V2 code should remain 'TEST-001', got {v2_data['code']}"
    )
    print(f"  ✓ V2 has updated data: name={v2_data['name']}")

    # ========================================================================
    # VALIDATION: Temporal continuity
    # ========================================================================
    print("\n--- VALIDATION: Temporal continuity ---")

    # valid_time should be continuous (v1.upper == v2.lower)
    assert v1_after["valid_upper"] == v2_data["valid_lower"], (
        f"valid_time should be continuous: V1.upper ({v1_after['valid_upper']}) "
        f"should equal V2.lower ({v2_data['valid_lower']})"
    )
    print(
        f"  ✓ valid_time is continuous: V1.upper == V2.lower == {v1_after['valid_upper']}"
    )

    # transaction_time should not overlap (v1.upper < v2.lower)
    assert v1_after["tx_upper"] < v2_data["tx_lower"], (
        f"transaction_time should not overlap: V1.upper ({v1_after['tx_upper']}) "
        f"should be < V2.lower ({v2_data['tx_lower']})"
    )
    print("  ✓ transaction_time does not overlap: V1.upper < V2.lower")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("  ✓ ALL VALIDATIONS PASSED")
    print("=" * 80)
    print("\nSummary:")
    print("  • V1 (old version) properly closed:")
    print(f"    - valid_time: [{v1_after['valid_lower']}, {v1_after['valid_upper']})")
    print(f"    - transaction_time: [{v1_after['tx_lower']}, {v1_after['tx_upper']})")
    print("  • V2 (new version) open-ended:")
    print(f"    - valid_time: [{v2_data['valid_lower']}, NULL)")
    print(f"    - transaction_time: [{v2_data['tx_lower']}, NULL)")
    print("  • Temporal continuity maintained")
    print("  • No empty or inverted ranges")
    print("=" * 80 + "\n")


@pytest.mark.asyncio
async def test_wbe_update_without_control_date_uses_current_time(
    db_session: AsyncSession,
) -> None:
    """
    Test that WBE update without control_date uses current time.

    This validates the default behavior when control_date is not provided.
    """
    print_debug_header("WBE UPDATE WITHOUT control_date TEST")

    service = WBEService(db_session)
    project_id = uuid4()
    wbe_id = uuid4()
    actor_id = uuid4()

    # Create initial WBE
    _ = await service.create_root(
        root_id=wbe_id,
        actor_id=actor_id,
        branch="main",
        project_id=project_id,
        code="TEST-002",
        name="WBE for control_date test",
        level=1,
    )

    await asyncio.sleep(1)

    # Update without specifying control_date
    update_time = datetime.now(UTC)
    _ = await service.update_wbe(
        wbe_id=wbe_id,
        wbe_in=WBEUpdate(name="Updated without control_date"),
        actor_id=actor_id,
        # control_date NOT provided - should use current time
    )

    # Fetch both versions from DB
    versions = await get_wbe_versions_from_db(db_session, wbe_id)
    assert len(versions) == 2

    v1 = versions[0]
    v2 = versions[1]

    print("\n  V1 (closed):")
    print_temporal_bounds(
        v1["id"],
        v1["valid_lower"],
        v1["valid_upper"],
        v1["tx_lower"],
        v1["tx_upper"],
        "V1",
        indent="    ",
    )

    print("\n  V2 (current):")
    print_temporal_bounds(
        v2["id"],
        v2["valid_lower"],
        v2["valid_upper"],
        v2["tx_lower"],
        v2["tx_upper"],
        "V2",
        indent="    ",
    )

    # V1 should be closed
    assert v1["valid_upper"] is not None, "V1 should be closed"
    assert v1["tx_upper"] is not None, "V1 transaction_time should be closed"

    # V2 should be open-ended
    assert v2["valid_upper"] is None, "V2 should be open-ended"
    assert v2["tx_upper"] is None, "V2 transaction_time should be open-ended"

    # V2's valid_time lower should be close to update_time (within 1 second)
    time_diff = abs((v2["valid_lower"] - update_time).total_seconds())
    assert time_diff < 1.0, (
        f"V2 valid_time lower should be close to update_time, diff={time_diff}s"
    )

    print(f"\n  ✓ control_date defaults to current time (diff={time_diff:.3f}s)")
    print("  ✓ ALL VALIDATIONS PASSED")
