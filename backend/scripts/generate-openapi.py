#!/usr/bin/env python3
"""Generate OpenAPI specification file."""

import json
from pathlib import Path

from app.main import app


def main() -> None:
    """Generate and save OpenAPI spec."""
    openapi_schema = app.openapi()
    output_path = Path(__file__).parent.parent / "openapi.json"

    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"OpenAPI specification generated: {output_path}")


if __name__ == "__main__":
    main()
