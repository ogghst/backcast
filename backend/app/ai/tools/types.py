"""Type definitions for AI tool system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.project import ProjectService

# Module-level ordering dict for RiskLevel (outside the enum to avoid it becoming a member)
_RISK_LEVEL_ORDERING = {
    "low": 1,
    "high": 2,
    "critical": 3,
}


class RiskLevel(str, Enum):
    """Risk level for AI tools.

    Used to determine which execution modes can use the tool:
    - low: Read-only tools, no side effects (safe mode compatible)
    - high: Tools that modify data but with validation (standard mode)
    - critical: Tools that delete data, bulk operations, or sensitive actions (expert mode only)

    Used in Phase 1: Tool categorization
    Used in Phase 2: Risk checking and execution mode filtering

    Note: Supports comparison operators for risk level ordering (LOW < HIGH < CRITICAL)
    """

    LOW = "low"
    HIGH = "high"
    CRITICAL = "critical"

    def _get_order_value(self) -> int:
        """Get the integer ordering value for this risk level."""
        return _RISK_LEVEL_ORDERING[self.value]

    def __ge__(self, other: Any) -> bool:
        """Support >= comparison for risk level checking."""
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self._get_order_value() >= other._get_order_value()

    def __gt__(self, other: Any) -> bool:
        """Support > comparison for risk level checking."""
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self._get_order_value() > other._get_order_value()

    def __le__(self, other: Any) -> bool:
        """Support <= comparison for risk level checking."""
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self._get_order_value() <= other._get_order_value()

    def __lt__(self, other: Any) -> bool:
        """Support < comparison for risk level checking."""
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self._get_order_value() < other._get_order_value()


class ExecutionMode(str, Enum):
    """AI tool execution mode.

    Controls which tools are available for execution based on risk levels:
    - safe: Only low-risk tools (read-only operations)
    - standard: Low and high-risk tools (requires approval for critical)
    - expert: All tools including critical (no approval required)

    Used in Phase 2: Risk checking and approval workflow
    """

    SAFE = "safe"
    STANDARD = "standard"
    EXPERT = "expert"


@dataclass
class ToolContext:
    """Execution context for AI tools with dependency injection.

    Provides database session, user context, project/branch context, and service accessors
    for tool execution.

    Attributes:
        session: Async database session
        user_id: Authenticated user ID
        user_role: User's role for RBAC authorization (e.g., "admin", "viewer")
        execution_mode: AI tool execution mode (default: STANDARD)
        project_id: Optional project context UUID for scoped operations
        branch_id: Optional branch or change order context UUID for scoped operations
        as_of: Optional historical date for temporal queries (None for current state)
        branch_name: Optional branch name for temporal queries (e.g., "main", "BR-001")
        branch_mode: Optional branch mode for temporal queries ("merged" or "isolated")
        _permission_cache: Cache for permission checks
    """

    session: AsyncSession
    user_id: str
    user_role: str = "guest"
    execution_mode: ExecutionMode = ExecutionMode.STANDARD
    project_id: str | None = None
    branch_id: str | None = None
    as_of: datetime | None = None
    branch_name: str | None = None
    branch_mode: Literal["merged", "isolated"] | None = None
    _permission_cache: dict[str, bool] = field(default_factory=dict)

    @property
    def project_service(self) -> ProjectService:
        """Get project service instance."""
        return ProjectService(self.session)

    async def check_permission(
        self,
        permission: str,
        project_id: str | None = None,
    ) -> bool:
        """Check if user has the specified permission.

        Args:
            permission: Permission string to check
            project_id: Optional project ID for project-level access checks

        Returns:
            True if user has permission, False otherwise

        Note:
            Implements simple caching for performance.
            Uses project-level access checks when project_id is provided.
        """
        from uuid import UUID

        from app.core.rbac import get_rbac_service

        # Build cache key
        cache_key = f"{permission}:{project_id or 'global'}"

        # Check cache first
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]

        # Get RBAC service
        rbac_service = get_rbac_service()

        # Inject session if available for project-level checks
        if project_id is not None:
            try:
                project_uuid = UUID(project_id)
                user_uuid = UUID(self.user_id)

                # Check if rbac_service supports project-level access
                if hasattr(rbac_service, "has_project_access"):
                    # Inject session if service supports it
                    if hasattr(rbac_service, "session") and rbac_service.session is None:
                        rbac_service.session = self.session

                    granted = await rbac_service.has_project_access(
                        user_id=user_uuid,
                        user_role=self.user_role,
                        project_id=project_uuid,
                        required_permission=permission,
                    )
                else:
                    # Fallback to role-based check
                    granted = rbac_service.has_permission(self.user_role, permission)
            except (ValueError, TypeError):
                # Invalid UUID format, deny permission
                granted = False
        else:
            # Global permission check
            granted = rbac_service.has_permission(self.user_role, permission)

        # Cache result
        self._permission_cache[cache_key] = granted
        return granted


@dataclass
class ToolMetadata:
    """Metadata for AI tools.

    Attributes:
        name: Tool name
        description: Tool description
        permissions: Required permissions list
        category: Tool category for grouping
        version: Tool version
        risk_level: Tool risk level (default: HIGH for backward compatibility)
    """

    name: str
    description: str
    permissions: list[str]
    category: str | None = None
    version: str = "1.0.0"
    risk_level: RiskLevel = RiskLevel.HIGH

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions,
            "category": self.category,
            "version": self.version,
            "risk_level": self.risk_level.value,
        }
