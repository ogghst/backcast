from typing import Any


class OverlappingVersionError(Exception):
    """Raised when a version's valid_time overlaps with an existing version.

    This ensures that for any given entity (root_id) on a specific branch,
    there is at most one active version for any point in valid_time.

    Attributes:
        root_id: The UUID of the versioned entity.
        branch: The branch name (optional for non-branchable).
        new_range: The valid_time range being inserted/updated.
        existing_range: The valid_time range that conflicts.
    """

    def __init__(
        self,
        root_id: str,
        new_range: Any,
        existing_range: Any,
        branch: str | None = None,
    ) -> None:
        self.root_id = root_id
        self.branch = branch
        self.new_range = new_range
        self.existing_range = existing_range

        msg_parts = [f"Overlapping version detected for entity {root_id}"]
        if branch:
            msg_parts.append(f"on branch '{branch}'")
        msg_parts.append(
            f". New range {new_range} overlaps with existing range {existing_range}."
        )

        super().__init__(" ".join(msg_parts))
