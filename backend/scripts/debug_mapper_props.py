
import sys
from pathlib import Path

from sqlalchemy import inspect

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from app.models.domain.branch import Branch  # noqa: E402


def inspect_mapper_properties():
    mapper = inspect(Branch)
    print(f"Mapper: {mapper}")

    for col in mapper.columns:
        prop = mapper.get_property_by_column(col)
        print(f"Column: {col.name}, Key in Mapper: {col.key}, Property Key: {prop.key}")

if __name__ == "__main__":
    inspect_mapper_properties()
