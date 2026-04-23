#!/usr/bin/env python3
"""Generate OpenAPI specification file.

This script generates the OpenAPI specification from the FastAPI application
and saves it to backend/openapi.json for use in frontend client generation.

Usage:
    uv run python scripts/generate_openapi.py
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


def generate_openapi() -> None:
    """Generate and save OpenAPI spec."""
    print("Generating OpenAPI specification...")

    # Use the app's openapi method to get the dict
    openapi_schema = app.openapi()

    # Define output path
    output_path = Path(__file__).parent.parent / "openapi.json"

    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"✓ OpenAPI specification generated: {output_path}")
    print(f"  - {len(openapi_schema.get('paths', {}))} endpoints")
    print(f"  - {len(openapi_schema.get('components', {}).get('schemas', {}))} schemas")


if __name__ == "__main__":
    generate_openapi()
