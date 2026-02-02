import json
import os
import sys

# Ensure we are in backend root
sys.path.append(os.getcwd())

from app.main import app


def main():
    print("Generating OpenAPI schema...")
    openapi_data = app.openapi()

    output_path = "openapi.json"
    with open(output_path, "w") as f:
        json.dump(openapi_data, f, indent=2)

    print(f"Schema written to {output_path}")

if __name__ == "__main__":
    main()
