"""Enums for versioning system."""

from enum import Enum


class BranchMode(str, Enum):
    """Branch resolution mode for time-travel queries.

    Controls how entity lookups handle branch isolation:
    - ISOLATED: Only return entities from the specified branch
    - MERGED: Fall back to main branch if entity not found on specified branch
    """

    ISOLATED = "isolated"  # Only look at specified branch
    MERGED = "merged"  # Fall back to main if not found on branch
