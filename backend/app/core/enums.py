"""Shared enumeration types for the application.

These enums provide type-safe status values with associated UI properties
(like Ant Design color names) that are used across backend and frontend.
"""

from enum import Enum


class ProjectStatus(str, Enum):
    """Project workflow statuses.

    Each status has an associated Ant Design color name for UI rendering.
    """

    DRAFT = "Draft"
    ACTIVE = "Active"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

    @property
    def color(self) -> str:
        """Get Ant Design color name for this status.

        Returns:
            Ant Design color name suitable for Tag/Badge components.
        """
        color_map = {
            ProjectStatus.DRAFT: "default",
            ProjectStatus.ACTIVE: "success",
            ProjectStatus.ON_HOLD: "warning",
            ProjectStatus.COMPLETED: "default",
            ProjectStatus.CANCELLED: "error",
        }
        return color_map[self]


class ChangeOrderStatus(str, Enum):
    """Change Order workflow statuses.

    Each status has an associated Ant Design color name for UI rendering.
    """

    DRAFT = "Draft"
    SUBMITTED_FOR_APPROVAL = "Submitted for Approval"
    UNDER_REVIEW = "Under Review"
    APPROVED = "Approved"
    IMPLEMENTED = "Implemented"
    REJECTED = "Rejected"

    @property
    def color(self) -> str:
        """Get Ant Design color name for this status.

        Returns:
            Ant Design color name suitable for Tag/Badge components.
        """
        color_map = {
            ChangeOrderStatus.DRAFT: "default",
            ChangeOrderStatus.SUBMITTED_FOR_APPROVAL: "processing",
            ChangeOrderStatus.UNDER_REVIEW: "blue",
            ChangeOrderStatus.APPROVED: "success",
            ChangeOrderStatus.IMPLEMENTED: "green",
            ChangeOrderStatus.REJECTED: "error",
        }
        return color_map[self]
