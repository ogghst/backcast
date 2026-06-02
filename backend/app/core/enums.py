"""Shared enumeration types for the application.

These enums provide type-safe status values with associated UI properties
(like Ant Design color names) that are used across backend and frontend.
"""

from enum import Enum


class ProjectStatus(str, Enum):
    """Project workflow statuses.

    Each status has an associated Ant Design color name for UI rendering.
    All status values are lowercase for consistency.
    """

    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

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
    All status values are lowercase with underscores for consistency.
    """

    DRAFT = "draft"
    SUBMITTED_FOR_APPROVAL = "submitted_for_approval"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    REJECTED = "rejected"

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
                "wbs-element-*",
                "control-account-*",
                "work-package-*",
                "cost-event-*",
                "progress-entry-*",
                "change-order-*",
                "forecast-*",
            ],
            ProjectRole.PROJECT_MANAGER: [
                "project-read",
                "project-update",
                "cost-element-*",
                "wbs-element-*",
                "control-account-*",
                "work-package-*",
                "cost-event-read",
                "cost-event-create",
                "cost-event-update",
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
                "wbs-element-read",
                "control-account-read",
                "work-package-read",
                "work-package-create",
                "cost-event-read",
                "cost-event-create",
                "progress-entry-create",
                "progress-entry-read",
                "change-order-read",
                "forecast-read",
                "forecast-create",
            ],
            ProjectRole.PROJECT_VIEWER: [
                "project-read",
                "cost-element-read",
                "wbs-element-read",
                "control-account-read",
                "work-package-read",
                "cost-event-read",
                "progress-entry-read",
                "change-order-read",
                "change-order-approve",
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


class WorkPackageStatus(str, Enum):
    """Work package lifecycle status.

    Open = costs can be posted. Closed = read-only.
    Two states only -- sufficient for current needs.
    Can be extended later via migration if TECO-style states are needed.
    """

    OPEN = "open"
    CLOSED = "closed"

    @property
    def color(self) -> str:
        """Ant Design color name for UI rendering."""
        colors = {
            WorkPackageStatus.OPEN: "success",
            WorkPackageStatus.CLOSED: "default",
        }
        return colors[self]


class COQCategory(str, Enum):
    """Cost of Quality categories per ASQ/ISO 9000 standard."""

    PREVENTION = "prevention"
    APPRAISAL = "appraisal"
    INTERNAL_FAILURE = "internal_failure"
    EXTERNAL_FAILURE = "external_failure"

    @property
    def label(self) -> str:
        labels = {
            COQCategory.PREVENTION: "Prevention",
            COQCategory.APPRAISAL: "Appraisal",
            COQCategory.INTERNAL_FAILURE: "Internal Failure",
            COQCategory.EXTERNAL_FAILURE: "External Failure",
        }
        return labels[self]

    @property
    def color(self) -> str:
        colors = {
            COQCategory.PREVENTION: "blue",
            COQCategory.APPRAISAL: "cyan",
            COQCategory.INTERNAL_FAILURE: "orange",
            COQCategory.EXTERNAL_FAILURE: "red",
        }
        return colors[self]
