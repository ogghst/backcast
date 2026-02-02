"""Change Order Workflow Service - flexible state machine.

This service encapsulates Change Order workflow state transitions and business rules.
It is designed as a simple state machine that can be replaced with a full business
process workflow engine (e.g., Camunda, Temporal) in a future iteration.

Workflow States (from FR-8.3):
Draft → Submitted for Approval → Under Review → Approved/Rejected → Implemented
"""


class ChangeOrderWorkflowService:
    """Encapsulates Change Order workflow state transitions and business rules.

    This service is designed as a simple state machine that can be replaced
    with a full business process workflow engine in future iterations.

    Workflow States (from FR-8.3):
    Draft → Submitted for Approval → Under Review → Approved/Rejected → Implemented

    Future Migration: Replace implementation with Camunda/Temporal while keeping
    the same interface methods.
    """

    # Define valid transitions
    _TRANSITIONS: dict[str, list[str]] = {
        "Draft": ["Submitted for Approval"],
        "Submitted for Approval": ["Under Review"],
        "Under Review": ["Approved", "Rejected"],
        "Rejected": ["Submitted for Approval"],
        "Approved": ["Implemented"],
        "Implemented": [],  # Terminal state
    }

    # Define which transitions trigger branch lock
    _LOCK_TRANSITIONS: set[tuple[str, str]] = {
        ("Draft", "Submitted for Approval"),
    }

    # Define which transitions trigger branch unlock
    _UNLOCK_TRANSITIONS: set[tuple[str, str]] = {
        ("Under Review", "Rejected"),
    }

    # Define which statuses allow editing
    _EDITABLE_STATUSES: set[str] = {"Draft", "Rejected"}

    async def get_next_status(self, current: str) -> str | None:
        """Get the single next status if the workflow is linear from current state.

        Returns None if multiple transitions are possible (e.g., from "Under Review").
        Use get_available_transitions() for non-linear branches.

        Args:
            current: Current workflow status

        Returns:
            Next status str if linear, None if multiple options
        """
        options = self._TRANSITIONS.get(current, [])
        return options[0] if len(options) == 1 else None

    async def get_available_transitions(self, current: str) -> list[str]:
        """Get all valid status transitions from the current state.

        Args:
            current: Current workflow status

        Returns:
            List of valid status strings that can be transitioned to
        """
        return self._TRANSITIONS.get(current, []).copy()

    async def should_lock_on_transition(self, from_status: str, to_status: str) -> bool:
        """Determine if a status transition should lock the branch.

        Args:
            from_status: Current workflow status
            to_status: Target workflow status

        Returns:
            True if branch should be locked after this transition
        """
        return (from_status, to_status) in self._LOCK_TRANSITIONS

    async def should_unlock_on_transition(
        self, from_status: str, to_status: str
    ) -> bool:
        """Determine if a status transition should unlock the branch.

        Args:
            from_status: Current workflow status
            to_status: Target workflow status

        Returns:
            True if branch should be unlocked after this transition
        """
        return (from_status, to_status) in self._UNLOCK_TRANSITIONS

    async def can_edit_on_status(self, status: str) -> bool:
        """Determine if Change Order details can be edited in this status.

        Args:
            status: Current workflow status

        Returns:
            True if CO fields can be modified, False if read-only
        """
        return status in self._EDITABLE_STATUSES

    async def is_valid_transition(self, from_status: str, to_status: str) -> bool:
        """Validate if a status transition is allowed.

        Args:
            from_status: Current workflow status
            to_status: Target workflow status

        Returns:
            True if transition is valid per workflow rules
        """
        valid_options = self._TRANSITIONS.get(from_status, [])
        return to_status in valid_options
