"""Project Default Configurations.

Provides default configurations applied when creating a new project.
Designed to be extensible for future project creation configurations.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from app.models.schemas.project_budget_settings import ProjectBudgetSettingsBase

if TYPE_CHECKING:
    pass


class BudgetSettingsService(Protocol):
    """Protocol for ProjectBudgetSettingsService.

    Used for type hints without circular imports.
    """

    async def upsert_settings(
        self,
        project_id: UUID,
        actor_id: UUID,
        warning_threshold_percent: Decimal | None = None,
        allow_project_admin_override: bool | None = None,
        enforce_budget: bool | None = None,
    ) -> object: ...  # Returns ProjectBudgetSettings, but we use object to avoid import

# Default budget warning threshold percentage
DEFAULT_BUDGET_WARNING_THRESHOLD = Decimal("80.0")


@dataclass(frozen=True)
class ProjectCreationDefaults:
    """Encapsulates all default configurations for project creation.

    This dataclass aggregates all default configurations that should be
    applied when creating a new project. Add new configuration categories
    as additional dataclass fields.

    Attributes:
        budget: Budget warning configuration defaults.

    Examples:
        >>> defaults = ProjectCreationDefaults()
        >>> defaults.budget.warning_threshold_percent
        Decimal('80.0')
    """

    budget: ProjectBudgetSettingsBase = field(
        default_factory=lambda: ProjectBudgetSettingsBase()
    )


def get_project_creation_defaults(
    **overrides: Decimal | bool | None,
) -> ProjectCreationDefaults:
    """Get project creation defaults with optional overrides.

    Provides a frozen ProjectCreationDefaults instance with all default
    configurations for project creation. Individual configurations can be
    overridden via kwargs.

    Args:
        **overrides: Optional field overrides. Supported keys:
            - warning_threshold_percent: Decimal
            - allow_project_admin_override: bool

    Returns:
        Frozen ProjectCreationDefaults with applied overrides.

    Examples:
        >>> # Get all defaults
        >>> defaults = get_project_creation_defaults()
        >>>
        >>> # Override warning threshold
        >>> from decimal import Decimal
        >>> defaults = get_project_creation_defaults(
        ...     warning_threshold_percent=Decimal("90.0")
        ... )
    """
    budget_config = ProjectBudgetSettingsBase(**overrides)
    return ProjectCreationDefaults(budget=budget_config)


async def apply_project_creation_defaults(
    project_id: UUID,
    actor_id: UUID,
    budget_settings_service: BudgetSettingsService,
    defaults: ProjectCreationDefaults | None = None,
) -> None:
    """Apply default configurations to a newly created project.

    Args:
        project_id: The ID of the newly created project.
        actor_id: The user who created the project (for audit trail).
        budget_settings_service: ProjectBudgetSettingsService instance.
        defaults: Optional custom defaults. Uses system defaults if not provided.
    """
    if defaults is None:
        defaults = get_project_creation_defaults()

    await budget_settings_service.upsert_settings(
        project_id=project_id,
        actor_id=actor_id,
        warning_threshold_percent=defaults.budget.warning_threshold_percent,
        allow_project_admin_override=defaults.budget.allow_project_admin_override,
        enforce_budget=defaults.budget.enforce_budget,
    )

    # Future: Add additional default configurations here
