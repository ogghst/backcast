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


class ProjectRole(str, Enum):
    """Project-level roles for RBAC.

    Each role has specific permissions for project operations.
    """

    PROJECT_ADMIN = "project_admin"
    PROJECT_MANAGER = "project_manager"
    PROJECT_EDITOR = "project_editor"
    PROJECT_VIEWER = "project_viewer"

    @property
    def permissions(self) -> list[str]:
        """Get the list of global permissions for this role.

        Returns:
            List of permission strings for this role.
        """
        permission_map = {
            ProjectRole.PROJECT_ADMIN: [
                "project-*",
                "cost-element-*",
                "wbe-*",
                "progress-entry-*",
                "change-order-*",
                "forecast-*",
            ],
            ProjectRole.PROJECT_MANAGER: [
                "project-read",
                "project-update",
                "cost-element-*",
                "wbe-*",
                "progress-entry-*",
                "change-order-read",
                "change-order-create",
                "forecast-*",
            ],
            ProjectRole.PROJECT_EDITOR: [
                "project-read",
                "project-update",
                "cost-element-create",
                "cost-element-read",
                "cost-element-update",
                "wbe-read",
                "progress-entry-create",
                "progress-entry-read",
                "progress-entry-update",
                "change-order-read",
                "forecast-read",
                "forecast-create",
            ],
            ProjectRole.PROJECT_VIEWER: [
                "project-read",
                "cost-element-read",
                "wbe-read",
                "progress-entry-read",
                "change-order-read",
                "forecast-read",
            ],
        }
        return permission_map[self]

    @property
    def color(self) -> str:
        """Get Ant Design color name for this role.

        Returns:
            Ant Design color name suitable for Tag/Badge components.
        """
        color_map = {
            ProjectRole.PROJECT_ADMIN: "error",
            ProjectRole.PROJECT_MANAGER: "warning",
            ProjectRole.PROJECT_EDITOR: "processing",
            ProjectRole.PROJECT_VIEWER: "default",
        }
        return color_map[self]
