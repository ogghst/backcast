
import json
from pathlib import Path

from app.main import app


def generate_openapi():
    # Use the app's openapi method to get the dict
    openapi_schema = app.openapi()

    # Define output path
    output_path = Path(__file__).parent.parent / "openapi.json"

    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"OpenAPI spec generated at {output_path}")

if __name__ == "__main__":
    generate_openapi()
