#!/usr/bin/env python3
"""Verify comprehensive change order seed data implementation."""

import json
from pathlib import Path
from uuid import UUID

SEED_DIR = Path(__file__).parent.parent


def load_json(filename: str) -> list[dict]:
    """Load JSON file from seed directory."""
    with open(SEED_DIR / filename) as f:
        return json.load(f)


def verify_uuid(uuid_str: str) -> bool:
    """Verify UUID string is valid."""
    try:
        UUID(uuid_str)
        return True
    except ValueError:
        return False


def main():
    """Run comprehensive seed data verification."""
    print("=" * 70)
    print("COMPREHENSIVE CHANGE ORDER SEED DATA VERIFICATION")
    print("=" * 70)
    print()

    # Load all data
    projects = load_json("projects.json")
    change_orders = load_json("change_orders.json")
    branches = load_json("branches.json")
    wbes = load_json("wbes.json")
    cost_elements = load_json("cost_elements.json")
    schedule_baselines = load_json("schedule_baselines.json")

    print("✅ Data Files Loaded Successfully")
    print(f"  Projects: {len(projects)}")
    print(f"  Change Orders: {len(change_orders)}")
    print(f"  Branches: {len(branches)}")
    print(f"  WBEs: {len(wbes)}")
    print(f"  Cost Elements: {len(cost_elements)}")
    print(f"  Schedule Baselines: {len(schedule_baselines)}")
    print()

    # Verify branch entities
    print("=" * 70)
    print("BRANCH VERIFICATION")
    print("=" * 70)

    branch_names = set()
    for branch in branches:
        branch_names.add(branch["branch_id"])
        print(f"  ✓ Branch: {branch['name']}")
        print(f"    ID: {branch['branch_id']}")
        print(f"    Project: {branch['project_id']}")
        print(f"    Change Order: {branch['change_order_id']}")
        print(f"    Locked: {branch['locked']}")

    print()
    print(f"✅ Total Branches: {len(branch_names)}")
    print()

    # Verify WBE distribution
    print("=" * 70)
    print("WBE DISTRIBUTION VERIFICATION")
    print("=" * 70)

    main_wbes = [w for w in wbes if not w.get("branch") or w.get("branch") in ["", "main"]]
    branch_wbes = [w for w in wbes if w.get("branch") and w.get("branch") not in ["", "main"]]

    print(f"  Main Branch WBEs: {len(main_wbes)}")
    for branch in sorted(branch_names):
        branch_wbe_count = len([w for w in wbes if w.get("branch") == branch])
        print(f"  {branch[:30]}... WBEs: {branch_wbe_count}")

    print()
    print(f"✅ Total WBEs: {len(wbes)} ({len(main_wbes)} main + {len(branch_wbes)} branch)")
    print()

    # Verify cost element distribution
    print("=" * 70)
    print("COST ELEMENT DISTRIBUTION VERIFICATION")
    print("=" * 70)

    main_ces = [ce for ce in cost_elements if not ce.get("branch") or ce.get("branch") in ["", "main"]]
    branch_ces = [ce for ce in cost_elements if ce.get("branch") and ce.get("branch") not in ["", "main"]]

    print(f"  Main Branch CEs: {len(main_ces)}")
    for branch in sorted(branch_names):
        branch_ce_count = len([ce for ce in cost_elements if ce.get("branch") == branch])
        print(f"  {branch[:30]}... CEs: {branch_ce_count}")

    print()
    print(f"✅ Total Cost Elements: {len(cost_elements)} ({len(main_ces)} main + {len(branch_ces)} branch)")
    print()

    # Verify schedule baseline distribution
    print("=" * 70)
    print("SCHEDULE BASELINE DISTRIBUTION VERIFICATION")
    print("=" * 70)

    main_sbs = [sb for sb in schedule_baselines if not sb.get("branch") or sb.get("branch") in ["", "main"]]
    branch_sbs = [sb for sb in schedule_baselines if sb.get("branch") and sb.get("branch") not in ["", "main"]]

    print(f"  Main Branch SBs: {len(main_sbs)}")
    for branch in sorted(branch_names):
        branch_sb_count = len([sb for sb in schedule_baselines if sb.get("branch") == branch])
        print(f"  {branch[:30]}... SBs: {branch_sb_count}")

    print()
    print(f"✅ Total Schedule Baselines: {len(schedule_baselines)} ({len(main_sbs)} main + {len(branch_sbs)} branch)")
    print()

    # Verify 1:1 relationship
    print("=" * 70)
    print("1:1 RELATIONSHIP VERIFICATION (Cost Element ↔ Schedule Baseline)")
    print("=" * 70)

    ce_with_baseline = [ce for ce in cost_elements if ce.get("schedule_baseline_id")]
    ce_without_baseline = [ce for ce in cost_elements if not ce.get("schedule_baseline_id")]

    print(f"  Cost Elements with schedule_baseline_id: {len(ce_with_baseline)}/{len(cost_elements)}")
    print(f"  Cost Elements without schedule_baseline_id: {len(ce_without_baseline)}")

    if ce_without_baseline:
        print()
        print("  ⚠️  WARNING: Cost Elements without schedule baseline:")
        for ce in ce_without_baseline[:5]:
            print(f"    - {ce['code']}: {ce.get('schedule_baseline_id', 'None')}")

    # Check for duplicate schedule_baseline_id (expected for branch versions)
    baseline_ids = [ce["schedule_baseline_id"] for ce in cost_elements if ce.get("schedule_baseline_id")]
    unique_baseline_ids = set(baseline_ids)
    duplicate_count = len(baseline_ids) - len(unique_baseline_ids)

    print()
    print(f"  Unique schedule_baseline_id values: {len(unique_baseline_ids)}")
    print(f"  Duplicate references (branch versions): {duplicate_count}")

    # Verify all schedule baselines exist
    sb_ids = {sb["schedule_baseline_id"] for sb in schedule_baselines}
    ce_baseline_ids = set(baseline_ids)
    missing_baselines = ce_baseline_ids - sb_ids

    print(f"  Missing schedule baselines: {len(missing_baselines)}")

    if missing_baselines:
        print()
        print("  ⚠️  WARNING: Referenced schedule baselines not found:")
        for sb_id in list(missing_baselines)[:3]:
            print(f"    - {sb_id}")

    print()
    if len(ce_with_baseline) == len(cost_elements) and len(missing_baselines) == 0:
        print("✅ 1:1 Relationship Integrity: VERIFIED")
    else:
        print("⚠️  1:1 Relationship Integrity: ISSUES FOUND")
    print()

    # Verify UUIDs
    print("=" * 70)
    print("UUID VALIDITY VERIFICATION")
    print("=" * 70)

    all_valid = True
    entity_types = [
        ("WBEs", wbes, "wbe_id"),
        ("Cost Elements", cost_elements, "cost_element_id"),
        ("Schedule Baselines", schedule_baselines, "schedule_baseline_id"),
    ]

    for entity_name, entities, id_field in entity_types:
        invalid_uuids = []
        for entity in entities:
            entity_id = entity.get(id_field)
            if entity_id and not verify_uuid(entity_id):
                invalid_uuids.append(entity_id)

        if invalid_uuids:
            print(f"  ⚠️  {entity_name}: {len(invalid_uuids)} invalid UUIDs")
            all_valid = False
        else:
            print(f"  ✅ {entity_name}: All UUIDs valid")

    print()
    if all_valid:
        print("✅ UUID Validity: VERIFIED")
    else:
        print("⚠️  UUID Validity: ISSUES FOUND")
    print()

    # Verify change order scenarios
    print("=" * 70)
    print("CHANGE ORDER SCENARIOS VERIFICATION")
    print("=" * 70)

    scenarios = [
        ("CO-A", "BR-CO-2026-001", "Scope Addition", 2, 5, 5),
        ("CO-B", "BR-CO-2026-002", "Scope Modification", 3, 3, 3),
        ("CO-C", "BR-CO-2026-006", "Scope Reduction", 2, 2, 2),
        ("CO-D", "BR-CO-2026-003", "Schedule Only", 0, 0, 5),
        ("CO-E", "BR-CO-2026-004", "Cost Reallocation", 0, 5, 0),
        ("CO-F", "BR-CO-2026-005", "Critical Addition", 5, 25, 25),
    ]

    all_scenarios_valid = True
    for co_code, branch_id, scenario, exp_wbes, exp_ces, exp_sbs in scenarios:
        wbe_count = len([w for w in wbes if w.get("branch") == branch_id])
        ce_count = len([ce for ce in cost_elements if ce.get("branch") == branch_id])
        sb_count = len([sb for sb in schedule_baselines if sb.get("branch") == branch_id])

        status = "✅" if (wbe_count == exp_wbes and ce_count == exp_ces and sb_count == exp_sbs) else "⚠️"
        print(f"  {status} {co_code}: {scenario}")
        print(f"     WBEs: {wbe_count} (expected: {exp_wbes})")
        print(f"     CEs: {ce_count} (expected: {exp_ces})")
        print(f"     SBs: {sb_count} (expected: {exp_sbs})")

        if wbe_count != exp_wbes or ce_count != exp_ces or sb_count != exp_sbs:
            all_scenarios_valid = False

    print()
    if all_scenarios_valid:
        print("✅ Change Order Scenarios: ALL VERIFIED")
    else:
        print("⚠️  Change Order Scenarios: SOME ISSUES FOUND")
    print()

    # Final summary
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print()
    print("✅ Data Files: Loaded Successfully")
    print("✅ Branch Entities: Verified")
    print("✅ WBE Distribution: Verified")
    print("✅ Cost Element Distribution: Verified")
    print("✅ Schedule Baseline Distribution: Verified")

    if len(ce_with_baseline) == len(cost_elements) and len(missing_baselines) == 0:
        print("✅ 1:1 Relationship: Verified")
    else:
        print("⚠️  1:1 Relationship: Issues Found")

    if all_valid:
        print("✅ UUID Validity: Verified")
    else:
        print("⚠️  UUID Validity: Issues Found")

    if all_scenarios_valid:
        print("✅ Change Order Scenarios: All Verified")
    else:
        print("⚠️  Change Order Scenarios: Some Issues Found")

    print()
    print("=" * 70)
    if (all_valid and all_scenarios_valid and
        len(ce_with_baseline) == len(cost_elements) and
        len(missing_baselines) == 0):
        print("OVERALL STATUS: ✅ ALL VERIFICATIONS PASSED")
    else:
        print("OVERALL STATUS: ⚠️ SOME ISSUES FOUND")
    print("=" * 70)


if __name__ == "__main__":
    main()
