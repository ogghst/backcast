"""Exceptions for branching operations.

Defines exceptions raised during branch operations like merge conflicts
and branch lock violations.
"""

from typing import Any


class BranchLockedException(Exception):
    """Raised when attempting to modify an entity on a locked branch.

    This exception is raised when attempting to create, update, or delete
    a branchable entity on a branch that is currently locked. Branches are
    typically locked during Change Order review/approval to prevent
    modifications while the change is being evaluated.

    Attributes:
        branch: Name of the locked branch.
        entity_type: Type of entity being modified (e.g., "WBE", "CostElement").
        entity_id: ID of the entity being modified.
    """

    def __init__(
        self,
        branch: str,
        entity_type: str = "entity",
        entity_id: str | None = None,
    ) -> None:
        """Initialize branch locked exception.

        Args:
            branch: Name of the locked branch.
            entity_type: Type of entity being modified.
            entity_id: Optional ID of the entity being modified.
        """
        self.branch = branch
        self.entity_type = entity_type
        self.entity_id = entity_id

        if entity_id:
            message = (
                f"Cannot modify {entity_type} {entity_id}: "
                f"Branch '{branch}' is locked. "
                f"No modifications are allowed while a Change Order is under review."
            )
        else:
            message = (
                f"Cannot modify {entity_type}: "
                f"Branch '{branch}' is locked. "
                f"No modifications are allowed while a Change Order is under review."
            )

        super().__init__(message)


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
