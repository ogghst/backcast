"""Type definitions for AI tool system."""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.project import ProjectService


@dataclass
class ToolContext:
    """Execution context for AI tools with dependency injection.

    Provides database session, user context, and service accessors
    for tool execution.

    Attributes:
        session: Async database session
        user_id: Authenticated user ID
        user_role: User's role for RBAC authorization (e.g., "admin", "viewer")
        _permission_cache: Cache for permission checks
    """

    session: AsyncSession
    user_id: str
    user_role: str = "guest"
    _permission_cache: dict[str, bool] = field(default_factory=dict)

    @property
    def project_service(self) -> ProjectService:
        """Get project service instance."""
        return ProjectService(self.session)

    async def check_permission(self, permission: str) -> bool:
        """Check if user has the specified permission.

        Args:
            permission: Permission string to check

        Returns:
            True if user has permission, False otherwise

        Note:
            Implements simple caching for performance.
            In production, this would check against user's roles.
        """
        # Check cache first
        if permission in self._permission_cache:
            return self._permission_cache[permission]

        # TODO: Implement actual RBAC check
        # For now, allow all authenticated users
        granted = True

        # Cache result
        self._permission_cache[permission] = granted
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
    """

    name: str
    description: str
    permissions: list[str]
    category: str | None = None
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions,
            "category": self.category,
            "version": self.version,
        }
