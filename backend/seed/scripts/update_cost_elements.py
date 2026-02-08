#!/usr/bin/env python3
"""Update cost_elements.json to add schedule_baseline_id FK.

This script reads the existing cost_elements.json and schedule_baselines.json,
then updates each cost element to include the schedule_baseline_id foreign key.
"""

import json
from pathlib import Path
from uuid import UUID

SEED_DIR = Path(__file__).parent


def main():
    """Update cost_elements.json with schedule_baseline_id FK."""
    print("Reading cost_elements.json...")
    with open(SEED_DIR / "cost_elements.json") as f:
        cost_elements = json.load(f)

    print("Reading schedule_baselines.json...")
    with open(SEED_DIR / "schedule_baselines.json") as f:
        baselines = json.load(f)

    # Create mapping from cost_element_id to schedule_baseline_id
    baseline_map = {
        UUID(baseline["cost_element_id"]): baseline["schedule_baseline_id"]
        for baseline in baselines
    }

    print(f"Found {len(cost_elements)} cost elements")
    print(f"Found {len(baselines)} schedule baselines")

    # Update each cost element with schedule_baseline_id
    updated_count = 0
    for ce in cost_elements:
        ce_id = UUID(ce["cost_element_id"])
        if ce_id in baseline_map:
            ce["schedule_baseline_id"] = str(baseline_map[ce_id])
            updated_count += 1
        else:
            print(f"WARNING: No baseline found for cost element {ce['code']}")
            ce["schedule_baseline_id"] = None

    print(f"Updated {updated_count} cost elements with schedule_baseline_id")

    # Save updated cost elements
    output_file = SEED_DIR / "cost_elements_updated.json"
    with open(output_file, "w") as f:
        json.dump(cost_elements, f, indent=2)

    print(f"Saved updated cost elements to {output_file}")
    print()
    print("To apply changes:")
    print(f"  mv {output_file} cost_elements.json")


if __name__ == "__main__":
    main()
