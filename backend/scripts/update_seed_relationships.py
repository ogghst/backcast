"""Update seed JSON files to use root IDs instead of codes for relationships.

This script transforms seed files from code-based relationships to ID-based relationships
for consistency and efficiency.
"""

import json

# Add parent directory to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.uuid_utils import (
    generate_project_uuid,
)

# Seed directory
SEED_DIR = Path(__file__).parent.parent / "seed"


def load_json(filename: str) -> list:
    """Load JSON file."""
    with open(SEED_DIR / filename) as f:
        return json.load(f)


def save_json(filename: str, data: list) -> None:
    """Save JSON file with proper formatting."""
    with open(SEED_DIR / filename, "w") as f:
        json.dump(data, f, indent=2)


def update_wbes():
    """Update WBEs to use project_id and parent_wbe_id."""
    print("Updating wbes.json...")

    # Load WBEs
    wbes = load_json("wbes.json")

    # Create a mapping of WBE codes to their UUIDs
    wbe_id_map = {wbe["code"]: wbe["wbe_id"] for wbe in wbes}

    # Update each WBE
    for wbe in wbes:
        # Replace project_code with project_id
        project_code = wbe.pop("project_code")
        wbe["project_id"] = str(generate_project_uuid(project_code))

        # Replace parent_wbe_code with parent_wbe_id
        parent_code = wbe.pop("parent_wbe_code", None)
        if parent_code:
            wbe["parent_wbe_id"] = wbe_id_map[parent_code]
        else:
            wbe["parent_wbe_id"] = None

    save_json("wbes.json", wbes)
    print(f"  Updated {len(wbes)} WBEs")


def update_cost_elements():
    """Update cost elements to use wbe_id and cost_element_type_id."""
    print("Updating cost_elements.json...")

    # Load cost elements
    cost_elements = load_json("cost_elements.json")

    # Load WBEs and cost element types to create mappings
    wbes = load_json("wbes.json")
    cost_element_types = load_json("cost_element_types.json")

    # Create mappings
    wbe_id_map = {wbe["code"]: wbe["wbe_id"] for wbe in wbes}
    cet_id_map = {
        cet["code"]: cet["cost_element_type_id"] for cet in cost_element_types
    }

    # Update each cost element
    for ce in cost_elements:
        # Replace wbe_code with wbe_id
        wbe_code = ce.pop("wbe_code")
        ce["wbe_id"] = wbe_id_map[wbe_code]

        # Replace cost_element_type_code with cost_element_type_id
        cet_code = ce.pop("cost_element_type_code")
        ce["cost_element_type_id"] = cet_id_map[cet_code]

    save_json("cost_elements.json", cost_elements)
    print(f"  Updated {len(cost_elements)} cost elements")


def update_cost_element_types():
    """Update cost element types to use department_id."""
    print("Updating cost_element_types.json...")

    # Load cost element types
    cost_element_types = load_json("cost_element_types.json")

    # Load departments to create mapping
    departments = load_json("departments.json")

    # Create mapping
    dept_id_map = {dept["code"]: dept["department_id"] for dept in departments}

    # Update each cost element type
    for cet in cost_element_types:
        # Replace department_code with department_id
        dept_code = cet.pop("department_code")
        cet["department_id"] = dept_id_map[dept_code]

    save_json("cost_element_types.json", cost_element_types)
    print(f"  Updated {len(cost_element_types)} cost element types")


def main():
    """Run all updates."""
    print("\n" + "=" * 60)
    print("Updating seed files to use ID-based relationships")
    print("=" * 60 + "\n")

    # Update in the correct order (dependencies first)
    update_cost_element_types()  # Depends on departments (already has department_id)
    update_wbes()  # Depends on projects (already has project_id)
    update_cost_elements()  # Depends on WBEs and cost element types

    print("\n" + "=" * 60)
    print("All seed files updated successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
