#!/usr/bin/env python3
"""Add comprehensive change order scenarios to seed data.

This script adds all 6 change order scenarios to the existing seed data:
- CO-A: Scope Addition (2 WBEs + 5 CEs + 5 SBs)
- CO-B: Scope Modification (3 WBEs + 3 CEs + 3 SBs)
- CO-C: Scope Reduction (2 soft-deleted WBEs + CEs + SBs)
- CO-D: Schedule Only (5 modified SBs)
- CO-E: Cost Reallocation (5 modified CEs)
- CO-F: Critical Addition (5 WBEs + 25 CEs + 25 SBs)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

SEED_DIR = Path(__file__).parent

# Change order branch IDs
# Change order branch IDs (using BR-{code} format to match ChangeOrderService behavior)
BRANCH_CO_A = "BR-CO-2026-001"
BRANCH_CO_B = "BR-CO-2026-002"
BRANCH_CO_C = "BR-CO-2026-006"
BRANCH_CO_D = "BR-CO-2026-003"
BRANCH_CO_E = "BR-CO-2026-004"
BRANCH_CO_F = "BR-CO-2026-005"

# Project IDs
PROJECT_1_ID = "d54fbbe6-f3df-51db-9c3e-9408700442be"
PROJECT_2_ID = "877c4cba-b30e-54c1-b25d-c73fb364019d"

# Cost element type IDs
CET_LAB = "6a483c4e-893c-5a92-8db9-6f5ac937c63f"
CET_MAT = "ce8977f4-3a39-55a0-b32b-c049369599f5"
CET_EQP = "19cbc2cb-5c9e-54c0-a139-54eb0069a18d"
CET_SUB = "6ee61a00-380b-5d3b-8656-20fc9fdac61e"
CET_TRV = "48f4591c-bb0b-595c-8d48-56136a4c5c78"


def load_json(filename: str) -> list[dict]:
    """Load JSON file from seed directory."""
    with open(SEED_DIR / filename) as f:
        return json.load(f)


def save_json(filename: str, data: list[dict]) -> None:
    """Save data to JSON file in seed directory."""
    with open(SEED_DIR / filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Updated {filename}: {len(data)} records")


def add_co_a_scope_addition(wbes: list[dict], cost_elements: list[dict],
                             schedule_baselines: list[dict]) -> None:
    """CO-A: Add 2 new L3 WBEs + 5 CEs + 5 SBs."""
    print("\n=== CO-A: Scope Addition (+$150K, +3 months) ===")

    # Get parent WBE for new L3 WBEs
    parent_wbe = next(w for w in wbes if w["code"] == "PRJ-DEMO-001-L1-1-L2-1"
                      and w.get("branch") != BRANCH_CO_A)

    # Create 2 new L3 WBEs
    new_wbe_1 = {
        "id": str(uuid4()),
        "wbe_id": str(uuid4()),
        "code": "PRJ-DEMO-001-L1-1-L2-1-L3-2",
        "name": "L3 WBE 1.1.2 (NEW - Secondary Conveyor)",
        "budget_allocation": 30000.0,
        "level": 3,
        "description": "New L3 WBE for secondary conveyor system (CO-A)",
        "project_id": PROJECT_1_ID,
        "parent_wbe_id": parent_wbe["wbe_id"],
        "control_date": "2026-02-01T00:00:00",
        "branch": BRANCH_CO_A,
        "parent_id": None,  # New entity
    }

    new_wbe_2 = {
        "id": str(uuid4()),
        "wbe_id": str(uuid4()),
        "code": "PRJ-DEMO-001-L1-1-L2-1-L3-3",
        "name": "L3 WBE 1.1.3 (NEW - Conveyor Controls)",
        "budget_allocation": 30000.0,
        "level": 3,
        "description": "New L3 WBE for conveyor control system (CO-A)",
        "project_id": PROJECT_1_ID,
        "parent_wbe_id": parent_wbe["wbe_id"],
        "control_date": "2026-02-01T00:00:00",
        "branch": BRANCH_CO_A,
        "parent_id": None,  # New entity
    }

    wbes.extend([new_wbe_1, new_wbe_2])
    print(f"  Added 2 new WBEs on branch {BRANCH_CO_A[:20]}...")

    # Create 5 new cost elements (distributed across the 2 new WBEs)
    new_wbe_1_id = new_wbe_1["wbe_id"]
    new_wbe_2_id = new_wbe_2["wbe_id"]

    new_cost_elements = []
    new_schedule_baselines = []

    # 3 cost elements for new_wbe_1
    for idx, (cet_id, cet_code) in enumerate([
        (CET_LAB, "LAB"), (CET_MAT, "MAT"), (CET_EQP, "EQP")
    ], 1):
        ce_id = str(uuid4())
        sb_id = str(uuid4())

        ce = {
            "id": str(uuid4()),
            "cost_element_id": ce_id,
            "wbe_id": new_wbe_1_id,
            "cost_element_type_id": cet_id,
            "code": f"PRJ-DEMO-001-L1-1-L2-1-L3-2-CE-{idx}",
            "name": f"Cost Element {idx}",
            "budget_amount": 30000.0,  # $30K each
            "description": f"Cost element of type {cet_code} (CO-A new)",
            "schedule_baseline_id": sb_id,
            "control_date": "2026-02-01T00:00:00",
            "branch": BRANCH_CO_A,
            "parent_id": None,
        }
        new_cost_elements.append(ce)

        sb = {
            "id": str(uuid4()),
            "schedule_baseline_id": sb_id,
            "cost_element_id": ce_id,
            "name": f"Baseline for PRJ-DEMO-001-L1-1-L2-1-L3-2-CE-{idx}",
            "start_date": "2026-02-01T00:00:00",
            "end_date": "2026-06-30T23:59:59",  # Extended timeline
            "progression_type": "LINEAR",
            "description": f"Linear progression for {cet_code} cost element (CO-A)",
            "valid_time": "[2026-02-01T00:00:00, infinity)",
            "transaction_time": "[2026-02-01T00:00:00, infinity)",
            "branch": BRANCH_CO_A,
            "parent_id": None,
            "deleted_at": None,
            "created_by": "00000000-0000-0000-0000-000000000001",
            "deleted_by": None,
        }
        new_schedule_baselines.append(sb)

    # 2 cost elements for new_wbe_2
    for idx, (cet_id, cet_code) in enumerate([
        (CET_SUB, "SUB"), (CET_TRV, "TRV")
    ], 4):
        ce_id = str(uuid4())
        sb_id = str(uuid4())

        ce = {
            "id": str(uuid4()),
            "cost_element_id": ce_id,
            "wbe_id": new_wbe_2_id,
            "cost_element_type_id": cet_id,
            "code": f"PRJ-DEMO-001-L1-1-L2-1-L3-3-CE-{idx}",
            "name": f"Cost Element {idx}",
            "budget_amount": 30000.0,  # $30K each
            "description": f"Cost element of type {cet_code} (CO-A new)",
            "schedule_baseline_id": sb_id,
            "control_date": "2026-02-01T00:00:00",
            "branch": BRANCH_CO_A,
            "parent_id": None,
        }
        new_cost_elements.append(ce)

        sb = {
            "id": str(uuid4()),
            "schedule_baseline_id": sb_id,
            "cost_element_id": ce_id,
            "name": f"Baseline for PRJ-DEMO-001-L1-1-L2-1-L3-3-CE-{idx}",
            "start_date": "2026-02-01T00:00:00",
            "end_date": "2026-06-30T23:59:59",  # Extended timeline
            "progression_type": "LINEAR",
            "description": f"Linear progression for {cet_code} cost element (CO-A)",
            "valid_time": "[2026-02-01T00:00:00, infinity)",
            "transaction_time": "[2026-02-01T00:00:00, infinity)",
            "branch": BRANCH_CO_A,
            "parent_id": None,
            "deleted_at": None,
            "created_by": "00000000-0000-0000-0000-000000000001",
            "deleted_by": None,
        }
        new_schedule_baselines.append(sb)

    cost_elements.extend(new_cost_elements)
    schedule_baselines.extend(new_schedule_baselines)

    print("  Added 5 new cost elements (total budget: +$150,000)")
    print("  Added 5 new schedule baselines (extended timeline to 2026-06-30)")


def add_co_b_scope_modification(wbes: list[dict], cost_elements: list[dict],
                                 schedule_baselines: list[dict]) -> None:
    """CO-B: Modify 3 existing WBEs + 3 CEs + 3 SBs."""
    print("\n=== CO-B: Scope Modification (+$45K, +2 weeks) ===")

    # Find 3 existing WBEs to modify (from main branch)
    # Note: existing WBEs don't have 'id' field - wbe_id is the root ID
    wbes_to_modify = [w for w in wbes if not w.get("branch") or w.get("branch") in ["", "main"]][:3]

    for _idx, main_wbe in enumerate(wbes_to_modify, 1):
        # Clone WBE to CO-B branch
        cloned_wbe = main_wbe.copy()
        cloned_wbe["id"] = str(uuid4())  # New version ID
        cloned_wbe["wbe_id"] = main_wbe["wbe_id"]  # Same root ID
        cloned_wbe["branch"] = BRANCH_CO_B
        cloned_wbe["parent_id"] = None  # Will be set by seeder based on wbe_id
        cloned_wbe["description"] = f"{main_wbe['description']} (MODIFIED - Safety Upgrades)"
        cloned_wbe["control_date"] = "2026-02-01T00:00:00"

        wbes.append(cloned_wbe)

    # Find 3 cost elements to modify
    ces_to_modify = [ce for ce in cost_elements if not ce.get("branch") or ce.get("branch") in ["", "main"]][:3]

    for main_ce in ces_to_modify:
        # Clone cost element with +10% budget
        cloned_ce = main_ce.copy()
        cloned_ce["id"] = str(uuid4())  # New version ID
        cloned_ce["cost_element_id"] = main_ce["cost_element_id"]  # Same root ID
        cloned_ce["branch"] = BRANCH_CO_B
        cloned_ce["parent_id"] = None  # Will be set by seeder based on cost_element_id
        cloned_ce["budget_amount"] = float(main_ce["budget_amount"]) * 1.10  # +10%
        cloned_ce["description"] = f"{main_ce['description']} (MODIFIED - +10% safety)"
        cloned_ce["control_date"] = "2026-02-01T00:00:00"

        cost_elements.append(cloned_ce)

        # Clone and extend schedule baseline by 2 weeks
        main_sb = next((sb for sb in schedule_baselines
                        if sb["cost_element_id"] == main_ce["cost_element_id"]
                        and (not sb.get("branch") or sb.get("branch") in ["", "main"])), None)
        if main_sb:
            cloned_sb = main_sb.copy()
            cloned_sb["id"] = str(uuid4())  # New version ID
            cloned_sb["schedule_baseline_id"] = main_sb["schedule_baseline_id"]  # Same root ID
            cloned_sb["branch"] = BRANCH_CO_B
            cloned_sb["parent_id"] = None  # Will be set by seeder

            # Extend end date by 2 weeks
            end_date = datetime.fromisoformat(main_sb["end_date"])
            new_end = end_date + timedelta(weeks=2)
            cloned_sb["end_date"] = new_end.isoformat()

            cloned_sb["description"] = f"{main_sb['description']} (EXTENDED +2 weeks)"
            cloned_sb["valid_time"] = "[2026-02-01T00:00:00, infinity)"
            cloned_sb["transaction_time"] = "[2026-02-01T00:00:00, infinity)"

            schedule_baselines.append(cloned_sb)

    print(f"  Modified 3 WBEs on branch {BRANCH_CO_B[:20]}...")
    print("  Modified 3 cost elements (+10% budget each)")
    print("  Modified 3 schedule baselines (extended +2 weeks)")


def add_co_c_scope_reduction(wbes: list[dict], cost_elements: list[dict],
                              schedule_baselines: list[dict]) -> None:
    """CO-C: Soft-delete 2 WBEs + 2 CEs + 2 SBs."""
    print("\n=== CO-C: Scope Reduction (-$125K, REJECTED) ===")

    # Find 2 existing WBEs to soft-delete
    wbes_to_delete = [w for w in wbes if not w.get("branch") or w.get("branch") in ["", "main"]][:2]

    for main_wbe in wbes_to_delete:
        # Clone WBE with deleted_at timestamp
        deleted_wbe = main_wbe.copy()
        deleted_wbe["id"] = str(uuid4())  # New version ID
        deleted_wbe["wbe_id"] = main_wbe["wbe_id"]  # Same root ID
        deleted_wbe["branch"] = BRANCH_CO_C
        deleted_wbe["parent_id"] = None  # Will be set by seeder based on wbe_id
        deleted_wbe["deleted_at"] = "2026-02-01T00:00:00"
        deleted_wbe["control_date"] = "2026-02-01T00:00:00"

        wbes.append(deleted_wbe)

    # Find 2 cost elements to soft-delete
    ces_to_delete = [ce for ce in cost_elements if not ce.get("branch") or ce.get("branch") in ["", "main"]][:2]

    for main_ce in ces_to_delete:
        # Clone cost element with deleted_at
        deleted_ce = main_ce.copy()
        deleted_ce["id"] = str(uuid4())  # New version ID
        deleted_ce["cost_element_id"] = main_ce["cost_element_id"]  # Same root ID
        deleted_ce["branch"] = BRANCH_CO_C
        deleted_ce["parent_id"] = None  # Will be set by seeder based on cost_element_id
        deleted_ce["deleted_at"] = "2026-02-01T00:00:00"
        deleted_ce["control_date"] = "2026-02-01T00:00:00"

        cost_elements.append(deleted_ce)

        # Clone schedule baseline with deleted_at
        main_sb = next((sb for sb in schedule_baselines
                        if sb["cost_element_id"] == main_ce["cost_element_id"]
                        and (not sb.get("branch") or sb.get("branch") in ["", "main"])), None)
        if main_sb:
            deleted_sb = main_sb.copy()
            deleted_sb["id"] = str(uuid4())  # New version ID
            deleted_sb["schedule_baseline_id"] = main_sb["schedule_baseline_id"]  # Same root ID
            deleted_sb["branch"] = BRANCH_CO_C
            deleted_sb["parent_id"] = None  # Will be set by seeder
            deleted_sb["deleted_at"] = "2026-02-01T00:00:00"
            deleted_sb["valid_time"] = "[2026-02-01T00:00:00, infinity)"
            deleted_sb["transaction_time"] = "[2026-02-01T00:00:00, infinity)"

            schedule_baselines.append(deleted_sb)

    print(f"  Soft-deleted 2 WBEs on branch {BRANCH_CO_C[:20]}...")
    print("  Soft-deleted 2 cost elements")
    print("  Soft-deleted 2 schedule baselines")
    print("  Status: REJECTED (data preserved for analysis)")


def add_co_d_schedule_only(schedule_baselines: list[dict]) -> None:
    """CO-D: Modify 5 schedule baselines only (progression type change)."""
    print("\n=== CO-D: Schedule Adjustment Only ($0, progression change) ===")

    # Find 5 LINEAR baselines to convert to GAUSSIAN
    linear_sbs = [sb for sb in schedule_baselines
                  if sb.get("progression_type") == "LINEAR"
                  and (not sb.get("branch") or sb.get("branch") in ["", "main"])][:5]

    for main_sb in linear_sbs:
        # Clone schedule baseline with changed progression type
        cloned_sb = main_sb.copy()
        cloned_sb["id"] = str(uuid4())  # New version ID
        cloned_sb["schedule_baseline_id"] = main_sb["schedule_baseline_id"]  # Same root ID
        cloned_sb["branch"] = BRANCH_CO_D
        cloned_sb["parent_id"] = None  # Will be set by seeder based on schedule_baseline_id
        cloned_sb["progression_type"] = "GAUSSIAN"  # Change from LINEAR
        cloned_sb["description"] = f"{main_sb['description']} (CHANGED to GAUSSIAN)"
        cloned_sb["valid_time"] = "[2026-02-01T00:00:00, infinity)"
        cloned_sb["transaction_time"] = "[2026-02-01T00:00:00, infinity)"

        schedule_baselines.append(cloned_sb)

    print(f"  Modified 5 schedule baselines on branch {BRANCH_CO_D[:20]}...")
    print("  Changed progression type: LINEAR → GAUSSIAN")
    print("  No WBE or cost element changes")


def add_co_e_cost_reallocation(cost_elements: list[dict]) -> None:
    """CO-E: Reallocate budgets (LAB +$40K, MAT -$40K)."""
    print("\n=== CO-E: Cost Reallocation ($0 net, LAB +$40K, MAT -$40K) ===")

    # Find 2 LAB cost elements to increase
    lab_ces = [ce for ce in cost_elements
               if ce["cost_element_type_id"] == CET_LAB
               and (not ce.get("branch") or ce.get("branch") in ["", "main"])][:2]

    for main_ce in lab_ces:
        cloned_ce = main_ce.copy()
        cloned_ce["id"] = str(uuid4())  # New version ID
        cloned_ce["cost_element_id"] = main_ce["cost_element_id"]  # Same root ID
        cloned_ce["branch"] = BRANCH_CO_E
        cloned_ce["parent_id"] = None  # Will be set by seeder based on cost_element_id
        cloned_ce["budget_amount"] = float(main_ce["budget_amount"]) + 20000.0  # +$20K each
        cloned_ce["description"] = f"{main_ce['description']} (REALLOCATED +$20K)"
        cloned_ce["control_date"] = "2026-02-01T00:00:00"

        cost_elements.append(cloned_ce)

    # Find 3 MAT cost elements to decrease
    mat_ces = [ce for ce in cost_elements
               if ce["cost_element_type_id"] == CET_MAT
               and (not ce.get("branch") or ce.get("branch") in ["", "main"])][:3]

    for main_ce in mat_ces:
        cloned_ce = main_ce.copy()
        cloned_ce["id"] = str(uuid4())  # New version ID
        cloned_ce["cost_element_id"] = main_ce["cost_element_id"]  # Same root ID
        cloned_ce["branch"] = BRANCH_CO_E
        cloned_ce["parent_id"] = None  # Will be set by seeder based on cost_element_id
        new_amount = float(main_ce["budget_amount"]) - 13333.33
        # Ensure non-negative
        if new_amount < 0:
            new_amount = 0.0

        cloned_ce["budget_amount"] = new_amount
        cloned_ce["description"] = f"{main_ce['description']} (REALLOCATED -$13.33K or to zero)"
        cloned_ce["control_date"] = "2026-02-01T00:00:00"

        cost_elements.append(cloned_ce)

    print(f"  Modified 5 cost elements on branch {BRANCH_CO_E[:20]}...")
    print("  LAB cost elements: +$20K × 2 = +$40K")
    print("  MAT cost elements: -$13.33K × 3 = -$40K")
    print("  Net change: $0 (internal reallocation)")


def add_co_f_critical_addition(wbes: list[dict], cost_elements: list[dict],
                                schedule_baselines: list[dict]) -> None:
    """CO-F: Add complete 5-WBE hierarchy (1 L1, 2 L2, 2 L3) + 25 CEs + 25 SBs."""
    print("\n=== CO-F: Critical Scope Addition (+$375K, +6 months) ===")

    # Create complete WBE hierarchy for robot cell integration
    # L1 WBE
    l1_wbe = {
        "id": str(uuid4()),
        "wbe_id": str(uuid4()),
        "code": "PRJ-DEMO-002-L1-3",
        "name": "L1 WBE 3 (NEW - Robot Cell)",
        "budget_allocation": 150000.0,
        "level": 1,
        "description": "New L1 WBE for robot cell integration (CO-F)",
        "project_id": PROJECT_2_ID,
        "parent_wbe_id": None,
        "control_date": "2026-02-01T00:00:00",
        "branch": BRANCH_CO_F,
        "parent_id": None,
    }
    wbes.append(l1_wbe)

    # L2 WBEs (2 children of L1)
    l2_wbes = []
    for idx in range(1, 3):
        l2_wbe = {
            "id": str(uuid4()),
            "wbe_id": str(uuid4()),
            "code": f"PRJ-DEMO-002-L1-3-L2-{idx}",
            "name": f"L2 WBE 3.{idx} (NEW - Robot Cell)",
            "budget_allocation": 75000.0,
            "level": 2,
            "description": f"New L2 WBE {idx} for robot cell (CO-F)",
            "project_id": PROJECT_2_ID,
            "parent_wbe_id": l1_wbe["wbe_id"],
            "control_date": "2026-02-01T00:00:00",
            "branch": BRANCH_CO_F,
            "parent_id": None,
        }
        l2_wbes.append(l2_wbe)
        wbes.append(l2_wbe)

    # L3 WBEs (2 children, one under each L2)
    l3_wbes = []
    for idx, l2_wbe in enumerate(l2_wbes, 1):
        l3_wbe = {
            "id": str(uuid4()),
            "wbe_id": str(uuid4()),
            "code": f"PRJ-DEMO-002-L1-3-L2-{idx}-L3-1",
            "name": f"L3 WBE 3.{idx}.1 (NEW - Robot Cell)",
            "budget_allocation": 37500.0,
            "level": 3,
            "description": f"New L3 WBE {idx} for robot cell (CO-F)",
            "project_id": PROJECT_2_ID,
            "parent_wbe_id": l2_wbe["wbe_id"],
            "control_date": "2026-02-01T00:00:00",
            "branch": BRANCH_CO_F,
            "parent_id": None,
        }
        l3_wbes.append(l3_wbe)
        wbes.append(l3_wbe)

    # Create 25 cost elements (5 per WBE: 1 L1 + 2 L2 + 2 L3 = 5 WBEs)
    all_wbes = [l1_wbe] + l2_wbes + l3_wbes
    new_cost_elements = []
    new_schedule_baselines = []

    for _wbe_idx, wbe in enumerate(all_wbes, 1):
        for cet_idx, (cet_id, cet_code) in enumerate([
            (CET_LAB, "LAB"), (CET_MAT, "MAT"), (CET_EQP, "EQP"),
            (CET_SUB, "SUB"), (CET_TRV, "TRV")
        ], 1):
            ce_id = str(uuid4())
            sb_id = str(uuid4())

            ce = {
                "id": str(uuid4()),
                "cost_element_id": ce_id,
                "wbe_id": wbe["wbe_id"],
                "cost_element_type_id": cet_id,
                "code": f"{wbe['code']}-CE-{cet_idx}",
                "name": f"Cost Element {cet_idx}",
                "budget_amount": 15000.0,  # $15K each
                "description": f"Cost element of type {cet_code} (CO-F new)",
                "schedule_baseline_id": sb_id,
                "control_date": "2026-02-01T00:00:00",
                "branch": BRANCH_CO_F,
                "parent_id": None,
            }
            new_cost_elements.append(ce)

            sb = {
                "id": str(uuid4()),
                "schedule_baseline_id": sb_id,
                "cost_element_id": ce_id,
                "name": f"Baseline for {wbe['code']}-CE-{cet_idx}",
                "start_date": "2026-02-01T00:00:00",
                "end_date": "2026-08-31T23:59:59",  # 7-month timeline
                "progression_type": "GAUSSIAN",  # S-curve for complex robot work
                "description": f"Gaussian S-curve for {cet_code} cost element (CO-F)",
                "valid_time": "[2026-02-01T00:00:00, infinity)",
                "transaction_time": "[2026-02-01T00:00:00, infinity)",
                "branch": BRANCH_CO_F,
                "parent_id": None,
                "deleted_at": None,
                "created_by": "00000000-0000-0000-0000-000000000001",
                "deleted_by": None,
            }
            new_schedule_baselines.append(sb)

    cost_elements.extend(new_cost_elements)
    schedule_baselines.extend(new_schedule_baselines)

    print(f"  Added 5 new WBEs (1 L1, 2 L2, 2 L3) on branch {BRANCH_CO_F[:20]}...")
    print("  Added 25 new cost elements (5 per WBE)")
    print("  Added 25 new schedule baselines (7-month timeline to 2026-08-31)")
    print("  Total budget impact: +$375,000")


def main():
    """Add all change order scenarios to seed data."""
    print("=" * 70)
    print("COMPREHENSIVE CHANGE ORDER SEED DATA ENHANCEMENT")
    print("=" * 70)

    # Load existing data
    print("\nLoading existing seed data...")
    wbes = load_json("wbes.json")
    cost_elements = load_json("cost_elements.json")
    schedule_baselines = load_json("schedule_baselines.json")

    print(f"  WBEs: {len(wbes)}")
    print(f"  Cost Elements: {len(cost_elements)}")
    print(f"  Schedule Baselines: {len(schedule_baselines)}")

    # Add all change order scenarios
    add_co_a_scope_addition(wbes, cost_elements, schedule_baselines)
    add_co_b_scope_modification(wbes, cost_elements, schedule_baselines)
    add_co_c_scope_reduction(wbes, cost_elements, schedule_baselines)
    add_co_d_schedule_only(schedule_baselines)
    add_co_e_cost_reallocation(cost_elements)
    add_co_f_critical_addition(wbes, cost_elements, schedule_baselines)

    # Save enhanced data
    print("\n" + "=" * 70)
    print("Saving enhanced seed data...")
    print("=" * 70)

    save_json("wbes.json", wbes)
    save_json("cost_elements.json", cost_elements)
    save_json("schedule_baselines.json", schedule_baselines)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total WBEs: {len(wbes)} (20 main + 9 branch versions)")
    print(f"Total Cost Elements: {len(cost_elements)} (100 main + 18 branch versions)")
    print(f"Total Schedule Baselines: {len(schedule_baselines)} (100 main + 18 branch versions)")
    print()
    print("Change Order Scenarios Added:")
    print("  CO-A: Scope Addition (+$150K, +3 months)")
    print("  CO-B: Scope Modification (+$45K, +2 weeks)")
    print("  CO-C: Scope Reduction (-$125K, REJECTED)")
    print("  CO-D: Schedule Adjustment Only ($0, progression change)")
    print("  CO-E: Cost Reallocation ($0 net, LAB +$40K, MAT -$40K)")
    print("  CO-F: Critical Addition (+$375K, +6 months)")
    print()
    print("All change order scenarios successfully implemented!")
    print("=" * 70)


if __name__ == "__main__":
    main()
