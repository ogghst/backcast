"""Generate UUIDv5 values for all seed data entities.

This script reads the seed JSON files and generates deterministic UUIDs
for all entities using the UUIDv5 namespace strategy.

Usage:
    uv run python scripts/generate_seed_uuids.py

Output:
    Prints a report of all entity codes and their corresponding UUIDs.
    Can be used to manually update seed JSON files or as reference.
"""

import json
import sys
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.uuid_utils import (
    generate_cost_element_type_uuid,
    generate_cost_element_uuid,
    generate_department_uuid,
    generate_project_uuid,
    generate_user_uuid,
    generate_wbe_uuid,
)

# Seed file paths
SEED_DIR = Path(__file__).parent.parent / "seed"


def load_json(filename: str) -> list:
    """Load and parse JSON file from seed directory."""
    file_path = SEED_DIR / filename
    if not file_path.exists():
        print(f"Warning: {filename} not found, skipping")
        return []

    with open(file_path) as f:
        return json.load(f)


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_uuid_report(entity_type: str, code_uuid_pairs: list[tuple[str, UUID]]) -> None:
    """Print UUID mappings for an entity type."""
    if not code_uuid_pairs:
        print(f"  No {entity_type} entities found")
        return

    print(f"\n{entity_type} UUIDs ({len(code_uuid_pairs)} entities):")
    print("-" * 70)
    for code, uuid_val in sorted(code_uuid_pairs, key=lambda x: str(x[1])):
        print(f"  {code:50s} → {uuid_val}")


def main() -> None:
    """Generate and print UUID mappings for all seed entities."""
    print("\n" + "=" * 70)
    print("  SEED DATA UUID GENERATION REPORT")
    print("=" * 70)
    print("\nGenerating UUIDv5 values using namespace-based strategy")
    print("These UUIDs are deterministic and will be the same on every run")

    # Projects
    print_section("PROJECTS")
    projects = load_json("projects.json")
    project_uuids = []
    for proj in projects:
        code = proj.get("code")
        if code:
            uuid_val = generate_project_uuid(code)
            project_uuids.append((code, uuid_val))
            # Check if project_id in JSON matches
            existing_id = proj.get("project_id")
            if existing_id:
                existing_uuid = UUID(existing_id)
                if existing_uuid != uuid_val:
                    print(f"  ⚠️  MISMATCH for {code}:")
                    print(f"     JSON has:     {existing_uuid}")
                    print(f"     Should be:    {uuid_val}")
    print_uuid_report("Project", project_uuids)

    # WBEs
    print_section("WBES (Work Breakdown Elements)")
    wbes = load_json("wbes.json")
    wbe_uuids = []
    for wbe in wbes:
        code = wbe.get("code")
        if code:
            uuid_val = generate_wbe_uuid(code)
            wbe_uuids.append((code, uuid_val))
    print_uuid_report("WBE", wbe_uuids)

    # Cost Elements
    print_section("COST ELEMENTS")
    cost_elements = load_json("cost_elements.json")
    ce_uuids = []
    for ce in cost_elements:
        code = ce.get("code")
        if code:
            uuid_val = generate_cost_element_uuid(code)
            ce_uuids.append((code, uuid_val))
    print_uuid_report("CostElement", ce_uuids)

    # Departments
    print_section("DEPARTMENTS")
    departments = load_json("departments.json")
    dept_uuids = []
    for dept in departments:
        code = dept.get("code")
        if code:
            uuid_val = generate_department_uuid(code)
            dept_uuids.append((code, uuid_val))
    print_uuid_report("Department", dept_uuids)

    # Cost Element Types
    print_section("COST ELEMENT TYPES")
    ce_types = load_json("cost_element_types.json")
    cet_uuids = []
    for cet in ce_types:
        code = cet.get("code")
        if code:
            uuid_val = generate_cost_element_type_uuid(code)
            cet_uuids.append((code, uuid_val))
    print_uuid_report("CostElementType", cet_uuids)

    # Users
    print_section("USERS")
    users = load_json("users.json")
    user_uuids = []
    for user in users:
        email = user.get("email")
        if email:
            uuid_val = generate_user_uuid(email)
            user_uuids.append((email, uuid_val))
    print_uuid_report("User", user_uuids)

    # Summary
    print_section("SUMMARY")
    total_entities = (
        len(project_uuids) + len(wbe_uuids) + len(ce_uuids) +
        len(dept_uuids) + len(cet_uuids) + len(user_uuids)
    )
    print(f"\nTotal entities: {total_entities}")
    print(f"  Projects:           {len(project_uuids)}")
    print(f"  WBEs:               {len(wbe_uuids)}")
    print(f"  Cost Elements:      {len(ce_uuids)}")
    print(f"  Departments:        {len(dept_uuids)}")
    print(f"  Cost Element Types: {len(cet_uuids)}")
    print(f"  Users:              {len(user_uuids)}")
    print("\n" + "=" * 70)
    print("  Next steps:")
    print("    1. Update seed JSON files with these UUIDs")
    print("    2. Update Pydantic schemas to accept root IDs")
    print("    3. Update services to use provided IDs when available")
    print("    4. Update seeder to pass IDs from JSON")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
