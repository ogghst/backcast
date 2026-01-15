"""Core branching module for EVCS.

Provides branchable entity services and commands for Git-style branching.
"""

from app.core.branching.exceptions import MergeConflictError
from app.core.branching.service import BranchableService

__all__ = ["BranchableService", "MergeConflictError"]
