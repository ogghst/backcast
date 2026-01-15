"""Exceptions for branching operations.

Defines exceptions raised during branch operations like merge conflicts.
"""

from typing import Any


class MergeConflictError(Exception):
    """Raised when merge cannot proceed due to conflicting changes.

    This exception is raised when attempting to merge a source branch into
    a target branch where both branches have diverged with conflicting changes
    to the same entity.

    Attributes:
        conflicts: List of conflict dictionaries containing details about
                   each conflicting change.

    Example conflict:
        {
            "entity_type": "Project",
            "entity_id": "123e4567-e89b-12d3-a456-426614174000",
            "field": "name",
            "source_branch": "co-123",
            "target_branch": "main",
            "source_value": "Updated Name",
            "target_value": "Original Name",
        }
    """

    def __init__(self, conflicts: list[dict[str, Any]]) -> None:
        """Initialize merge conflict error.

        Args:
            conflicts: List of conflict details.
        """
        self.conflicts = conflicts
        conflict_count = len(conflicts)

        if conflict_count == 0:
            message = "No conflicts detected"
        elif conflict_count == 1:
            c = conflicts[0]
            message = (
                f"1 conflict detected: {c['entity_type']} {c['entity_id']} "
                f"has conflicting changes on '{c['source_branch']}' vs '{c['target_branch']}' "
                f"for field '{c['field']}'"
            )
        else:
            message = (
                f"{conflict_count} conflicts detected between "
                f"'{conflicts[0]['source_branch']}' and '{conflicts[0]['target_branch']}'"
            )

        super().__init__(message)
