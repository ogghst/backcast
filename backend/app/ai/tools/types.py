"""Type definitions for AI tool system."""

import collections
import collections.abc
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import inject_rbac_session
from app.services.project import ProjectService


class _LRUCache(dict[str, bool]):
    """Simple LRU cache with maximum size limit.

    Inherits from dict for compatibility with existing code that treats
    _permission_cache as a dictionary. Automatically evicts least recently
    used entries when capacity is exceeded.
    """

    def __init__(self, max_size: int = 1000) -> None:
        """Initialize LRU cache with maximum size.

        Args:
            max_size: Maximum number of entries to cache (default: 1000)
        """
        self._max_size = max_size
        self._usage_order: collections.OrderedDict[str, None] = (
            collections.OrderedDict()
        )
        super().__init__()

    def __setitem__(self, key: str, value: bool) -> None:
        """Set item and update usage order.

        If key already exists, updates its value and moves to most recent.
        If at capacity, evicts least recently used entry before adding new one.
        """
        if key in self:
            # Move to end (most recently used)
            self._usage_order.move_to_end(key)
        else:
            # Add new entry
            self._usage_order[key] = None
            # Evict LRU if at capacity
            if len(self._usage_order) > self._max_size:
                lru_key, _ = self._usage_order.popitem(last=False)
                super().__delitem__(lru_key)

        super().__setitem__(key, value)

    def __getitem__(self, key: str) -> bool:
        """Get item and mark as recently used."""
        if key in self._usage_order:
            self._usage_order.move_to_end(key)
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        """Check if key exists in cache."""
        return key in self._usage_order

    def clear(self) -> None:
        """Clear all entries from cache."""
        self._usage_order.clear()
        super().clear()


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
    - standard: Low and high-risk tools (critical blocked)
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
        session: Property that returns task-local session for concurrent tool execution
        _root_session: Root WebSocket-level session (for fallback/non-tool operations)
        user_id: Authenticated user ID
        user_role: User's role for RBAC authorization (e.g., "admin", "viewer")
        execution_mode: AI tool execution mode (default: STANDARD)
        project_id: Optional project context UUID for scoped operations
        branch_id: Optional branch or change order context UUID for scoped operations
        as_of: Optional historical date for temporal queries (None for current state)
        branch_name: Optional branch name for temporal queries (e.g., "main", "BR-001")
        branch_mode: Optional branch mode for temporal queries ("merged" or "isolated")
        _permission_cache: LRU cache for permission checks (max 1000 entries)

    Note:
        The `session` property returns a task-local session using SQLAlchemy's
        async_scoped_session, which ensures each concurrent tool execution gets
        its own isolated session to prevent "Session is already flushing" errors.
        The original session passed during construction is stored as `_root_session`
        for potential fallback or WebSocket-level operations.
        The permission cache uses LRU eviction to prevent unbounded memory growth.
    """

    _root_session: AsyncSession = field(init=False, repr=False)
    user_id: str
    user_role: str = "guest"
    execution_mode: ExecutionMode = ExecutionMode.STANDARD
    project_id: str | None = None
    branch_id: str | None = None
    as_of: datetime | None = None
    branch_name: str | None = None
    branch_mode: Literal["merged", "isolated"] | None = None
    _permission_cache: collections.abc.MutableMapping[str, bool] = field(
        default_factory=lambda: _LRUCache(max_size=1000)
    )

    def __init__(
        self,
        session: AsyncSession,
        user_id: str,
        user_role: str = "guest",
        execution_mode: ExecutionMode = ExecutionMode.STANDARD,
        project_id: str | None = None,
        branch_id: str | None = None,
        as_of: datetime | None = None,
        branch_name: str | None = None,
        branch_mode: Literal["merged", "isolated"] | None = None,
        _permission_cache: collections.abc.MutableMapping[str, bool] | None = None,
    ) -> None:
        """Initialize ToolContext with session and user context.

        Args:
            session: The database session (will be stored as _root_session)
            user_id: Authenticated user ID
            user_role: User's role for RBAC
            execution_mode: AI tool execution mode
            project_id: Optional project context UUID
            branch_id: Optional branch context UUID
            as_of: Optional historical date for temporal queries
            branch_name: Optional branch name for temporal queries
            branch_mode: Optional branch mode for temporal queries
            _permission_cache: Optional permission cache (uses LRU with 1000-entry limit if not provided)
        """
        self._root_session = session
        self.user_id = user_id
        self.user_role = user_role
        self.execution_mode = execution_mode
        self.project_id = project_id
        self.branch_id = branch_id
        self.as_of = as_of
        self.branch_name = branch_name
        self.branch_mode = branch_mode
        # Use provided cache or create new LRU cache
        if _permission_cache is not None:
            self._permission_cache = _permission_cache
        else:
            self._permission_cache = _LRUCache(max_size=1000)

    @property
    def session(self) -> AsyncSession:
        """Get task-local session for concurrent tool execution.

        Returns a session scoped to the current asyncio task using
        SQLAlchemy's async_scoped_session with asyncio.current_task as scopefunc.

        Returns:
            AsyncSession: Task-local session for the current tool execution
        """
        from app.db.session import get_tool_session

        return get_tool_session()

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
                    inject_rbac_session(rbac_service, self.session)

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
