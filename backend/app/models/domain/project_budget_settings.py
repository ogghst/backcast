"""Project Budget Settings domain model - budget validation configuration.

Project Budget Settings define how budget validation works for a project,
including warning thresholds and admin override permissions.
"""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

if TYPE_CHECKING:
    pass


class ProjectBudgetSettings(EntityBase, VersionableMixin):
    """Project Budget Settings - budget validation configuration.

    Project Budget Settings control cost registration validation behavior,
    including warning thresholds and admin override permissions.

    Versionable but NOT branchable - budget settings apply across all branches
    as they represent project-wide configuration, not branch-specific changes.
    This ensures consistent budget validation regardless of which change order
    branch is being viewed.

    Attributes:
        project_budget_settings_id: Root ID for the settings aggregation.
        project_id: Reference to the project these settings apply to.
        warning_threshold_percent: Percentage threshold for warnings (default 80.0).
        allow_project_admin_override: Whether project admins can override warnings.

    Examples:
        - Threshold: 80.0 means warn at 80% of budget used
        - Override: True allows project admins to bypass warnings

    Satisfies: VersionableProtocol
    """

    __tablename__ = "project_budget_settings"

    # Root ID (stable identity across versions)
    project_budget_settings_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, index=True
    )

    # Foreign key to project
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No database-level ForeignKey constraint on root ID.
    )

    # Warning threshold percentage (0.00 to 999.99)
    warning_threshold_percent: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2), nullable=False, default=Decimal("80.0")
    )

    # Whether project admins can override budget warnings
    allow_project_admin_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Whether to block cost registrations that exceed budget
    enforce_budget: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Temporal fields inherited from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None
    # - created_by: UUID
    # - deleted_by: UUID | None

    # NOTE: Does NOT inherit BranchableMixin (no branch, parent_id, merge_from_branch)

    def __repr__(self) -> str:
        return (
            f"<ProjectBudgetSettings(id={self.id}, "
            f"project_budget_settings_id={self.project_budget_settings_id}, "
            f"project_id={self.project_id}, "
            f"warning_threshold_percent={self.warning_threshold_percent}, "
            f"allow_project_admin_override={self.allow_project_admin_override}, "
            f"enforce_budget={self.enforce_budget})>"
        )
