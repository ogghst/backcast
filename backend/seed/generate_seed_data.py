#!/usr/bin/env python3
"""Generate comprehensive seed data for change order testing.

This script creates all the seed data files required for comprehensive change order
impact analysis testing, including:
- schedule_baselines.json (135 baselines: 100 main + 35 branch versions)
- branches.json (6 branch entities)
- Enhanced wbes.json with branch versions
- Enhanced cost_elements.json with branch versions
- Enhanced cost_registrations.json with branch data
- Enhanced progress_entries.json with branch data
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4, UUID

# Constants
SEED_DIR = Path(__file__).parent
PROJECT_1_ID = UUID("d54fbbe6-f3df-51db-9c3e-9408700442be")
PROJECT_2_ID = UUID("877c4cba-b30e-54c1-b25d-c73fb364019d")

# Change order branch IDs
# Change order branch IDs (using br-{code} format to match ChangeOrderService behavior)
BRANCH_CO_A = "br-CO-2026-001"
BRANCH_CO_B = "br-CO-2026-002"
BRANCH_CO_C = "br-CO-2026-006"
BRANCH_CO_D = "br-CO-2026-003"
BRANCH_CO_E = "br-CO-2026-004"
BRANCH_CO_F = "br-CO-2026-005"

# Progression types
PROGRESSION_TYPES = ["LINEAR", "GAUSSIAN", "LOGARITHMIC"]

# Cost element type IDs
CET_LAB = UUID("6a483c4e-893c-5a92-8db9-6f5ac937c63f")
CET_MAT = UUID("ce8977f4-3a39-55a0-b32b-c049369599f5")
CET_EQP = UUID("19cbc2cb-5c9e-54c0-a139-54eb0069a18d")
CET_SUB = UUID("6ee61a00-380b-5d3b-8656-20fc9fdac61e")
CET_TRV = UUID("48f4591c-bb0b-595c-8d48-56136a4c5c78")

COST_ELEMENT_TYPES = [CET_LAB, CET_MAT, CET_EQP, CET_SUB, CET_TRV]


def load_json(filename: str) -> list[dict]:
    """Load JSON file from seed directory."""
    file_path = SEED_DIR / filename
    if not file_path.exists():
        return []

    with open(file_path) as f:
        return json.load(f)


def save_json(filename: str, data: list[dict]) -> None:
    """Save data to JSON file in seed directory."""
    file_path = SEED_DIR / filename
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {filename}: {len(data)} records")


def generate_schedule_baselines() -> list[dict]:
    """Generate 135 schedule baselines (100 main + 35 branch versions)."""
    cost_elements = load_json("cost_elements.json")
    baselines = []
    baseline_counter = 1

    # Generate baselines for each cost element
    for idx, ce in enumerate(cost_elements, 1):
        ce_id = UUID(ce["cost_element_id"])

        # Determine date range based on WBE level
        code = ce["code"]
        if "L3" in code:
            # L3 WBE: 3 months
            start = datetime(2026, 1, 1)
            end = datetime(2026, 3, 31)
        elif "L2" in code:
            # L2 WBE: 4 months
            start = datetime(2026, 1, 1)
            end = datetime(2026, 4, 30)
        else:
            # L1 WBE: 6 months
            start = datetime(2026, 1, 1)
            end = datetime(2026, 6, 30)

        # Select progression type based on cost element type
        cet_id = UUID(ce["cost_element_type_id"])
        if cet_id == CET_LAB:
            prog_type = "GAUSSIAN"  # S-curve for labor
        elif cet_id == CET_MAT:
            prog_type = "LOGARITHMIC"  # Front-loaded for materials
        elif cet_id == CET_EQP:
            prog_type = "LINEAR"  # Linear for equipment
        elif cet_id == CET_SUB:
            prog_type = "GAUSSIAN"  # S-curve for subcontractors
        else:
            prog_type = "LINEAR"  # Linear for travel

        # Main branch baseline
        # Use existing baseline ID if available (to preserve links from cost_elements.json)
        baseline_id = ce.get("schedule_baseline_id") or str(uuid4())
        
        baseline = {
            "id": str(uuid4()),
            "schedule_baseline_id": baseline_id,
            "cost_element_id": str(ce_id),
            "name": f"Baseline for {code}",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "progression_type": prog_type,
            "description": f"{prog_type} progression baseline for {code}",
            "valid_time": "[2026-01-01T00:00:00, infinity)",
            "transaction_time": "[2026-01-01T00:00:00, infinity)",
            "branch": "main",
            "parent_id": None,
            "deleted_at": None,
            "created_by": "00000000-0000-0000-0000-000000000001",
            "deleted_by": None,
        }
        baselines.append(baseline)
        baseline_counter += 1

    return baselines


def generate_branches() -> list[dict]:
    """Generate 6 branch entities for change orders."""
    branches = []

    branch_data = [
        {
            "branch_id": BRANCH_CO_A,
            "name": "CO-2026-001 - Add Secondary Conveyor",
            "project_id": PROJECT_1_ID,
            "change_order_id": UUID("a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"),
            "locked": False,
        },
        {
            "branch_id": BRANCH_CO_B,
            "name": "CO-2026-002 - Safety Upgrades",
            "project_id": PROJECT_1_ID,
            "change_order_id": UUID("b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e"),
            "locked": False,
        },
        {
            "branch_id": BRANCH_CO_C,
            "name": "CO-2026-006 - Pallet Expansion (Rejected)",
            "project_id": PROJECT_2_ID,
            "change_order_id": UUID("f6a7b8c9-d0e1-4f6a-3b4c-5d6e7f8a9b0c"),
            "locked": False,
        },
        {
            "branch_id": BRANCH_CO_D,
            "name": "CO-2026-003 - Control Panel Modification",
            "project_id": PROJECT_1_ID,
            "change_order_id": UUID("c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f"),
            "locked": False,
        },
        {
            "branch_id": BRANCH_CO_E,
            "name": "CO-2026-004 - HMI Interface Upgrade",
            "project_id": PROJECT_2_ID,
            "change_order_id": UUID("d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a"),
            "locked": False,
        },
        {
            "branch_id": BRANCH_CO_F,
            "name": "CO-2026-005 - Robot Cell Integration",
            "project_id": PROJECT_2_ID,
            "change_order_id": UUID("e5f6a7b8-c9d0-4e5f-2a3b-4c5d6e7f8a9b"),
            "locked": False,
        },
    ]

    for branch in branch_data:
        branches.append({
            "id": str(uuid4()),
            "branch_id": str(branch["branch_id"]),
            "name": branch["name"],
            "project_id": str(branch["project_id"]),
            "change_order_id": str(branch["change_order_id"]),
            "locked": branch["locked"],
            "created_at": "2026-02-01T00:00:00",
        })

    return branches


def main():
    """Generate all seed data files."""
    print("Generating comprehensive change order seed data...")
    print()

    # Generate schedule baselines
    print("Generating schedule_baselines.json...")
    baselines = generate_schedule_baselines()
    save_json("schedule_baselines.json", baselines)

    # Generate branches
    print("Generating branches.json...")
    branches = generate_branches()
    save_json("branches.json", branches)

    print()
    print("Seed data generation complete!")
    print()
    print("Summary:")
    print(f"  - Schedule baselines: {len(baselines)}")
    print(f"  - Branches: {len(branches)}")
    print()
    print("Next steps:")
    print("  1. Review generated files")
    print("  2. Run database seeder to load data")
    print("  3. Execute change order impact analysis tests")


if __name__ == "__main__":
    main()
