"""Enums for versioning system."""

from enum import Enum


class BranchMode(str, Enum):
    """Branch resolution mode for time-travel queries.
    
    Controls how entity lookups handle branch isolation:
    - STRICT: Only return entities from the specified branch
    - MERGE: Fall back to main branch if entity not found on specified branch
    """

    STRICT = "strict"  # Only look at specified branch
    MERGE = "merge"    # Fall back to main if not found on branch
