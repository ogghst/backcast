import sys
from pathlib import Path

from sqlalchemy import inspect

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from app.models.domain.branch import Branch  # noqa: E402


def inspect_mapper():
    mapper = inspect(Branch)
    print(f"Mapper: {mapper}")
    print("Columns:")
    for col in mapper.columns:
        print(f"  Key: {col.key}, Name: {col.name}, Type: {type(col)}")

    print("\nAttributes:")
    for attr in mapper.attrs:
        print(f"  Key: {attr.key}")

    # specific check
    print("\nChecking metadata attr:")
    b = Branch(name="test", project_id="123")
    if hasattr(b, "metadata"):
        print(f"  b.metadata type: {type(b.metadata)}")

    if hasattr(b, "branch_metadata"):
        print(f"  b.branch_metadata type: {type(b.branch_metadata)}")


if __name__ == "__main__":
    inspect_mapper()
