#!/usr/bin/env python3
"""Test script to verify SQLAlchemy cartesian product warning is fixed.

This script performs a simple WBE query and checks for SQLAlchemy warnings.
"""

import asyncio
import sys
import warnings

from sqlalchemy import exc as sqlalchemy_exc

# Add backend to path
sys.path.insert(0, "/home/nicola/dev/backcast_evs/backend")

from app.db.session import async_session_maker
from app.services.wbe import WBEService


async def test_wbe_query():
    """Test WBE query and check for cartesian product warnings."""

    # Capture SQLAlchemy warnings
    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always")

        async with async_session_maker() as session:
            service = WBEService(session)

            # Test 1: Get WBE by root_id (uses _get_base_stmt)
            print("Testing get_by_root_id...")
            wbe = await service.get_by_root_id(
                root_id="00000000-0000-0000-0000-000000000001",
                branch="main"
            )
            if wbe:
                print(f"  ✓ Found WBE: {wbe.code} - {wbe.name}")
                if hasattr(wbe, "parent_name"):
                    print(f"  ✓ Parent name resolved: {wbe.parent_name}")
            else:
                print("  ⚠ WBE not found (might not exist in seeded data)")

            # Test 2: List WBEs (uses _get_base_stmt with pagination)
            print("\nTesting get_wbes...")
            wbes, total = await service.get_wbes(branch="main", limit=10)
            print(f"  ✓ Found {total} WBE(s)")
            for wbe in wbes[:3]:  # Show first 3
                print(f"    - {wbe.code}: {wbe.name} (parent: {wbe.parent_name})")

            # Test 3: Get WBE history (uses get_wbe_history with scalar subqueries)
            print("\nTesting get_wbe_history...")
            history = await service.get_wbe_history(
                wbe_id="00000000-0000-0000-0000-000000000001"
            )
            print(f"  ✓ Found {len(history)} version(s)")

            # Check for SQLAlchemy SAWarning about cartesian products
            print("\n" + "=" * 60)
            print("SQLAlchemy Warning Check:")
            print("=" * 60)

            sawarnings = [
                w for w in warning_list
                if issubclass(w.category, sqlalchemy_exc.SAWarning)
            ]

            if sawarnings:
                print(f"❌ FAILED: Found {len(sawarnings)} SQLAlchemy warning(s):")
                for w in sawarnings:
                    print(f"  - {w.message}")
                return False
            else:
                print("✅ SUCCESS: No SQLAlchemy warnings detected!")
                print("   The cartesian product warning has been fixed.")
                return True


if __name__ == "__main__":
    result = asyncio.run(test_wbe_query())
    sys.exit(0 if result else 1)
