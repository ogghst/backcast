# Phase 2 DO Execution Plan: Tool Standardization

**Created:** 2026-03-09
**Status:** Ready for Execution
**Approach:** Option B - Thorough (as approved in Phase 1 CHECK)
**Points:** 3

---

## Overview

This document provides the detailed execution plan for Phase 2 DO phase of the LangGraph Agent Enhancement. Phase 2 implements the tool standardization layer with `@ai_tool` decorator, tool registry, and migration of existing tools.

## Execution Strategy

### TDD Approach (RED → GREEN → REFACTOR)

For each task:
1. **RED:** Write failing tests first
2. **GREEN:** Implement minimum code to pass tests
3. **REFACTOR:** Improve code while keeping tests green

### Task Execution Order

Based on dependency graph from 01-plan.md:

```
Level 0: BE-P2-001 (Decorator) - START HERE
Level 1: BE-P2-002 (Types)
Level 2: BE-P2-003 (Registry)
Level 3: BE-P2-004 (Migrate list_projects)
Level 4: BE-P2-005 (Migrate get_project)
Level 5: BE-P2-006 (Test all tools)
```

---

## Task Details

### BE-P2-001: Implement @ai_tool Decorator

**File:** `backend/app/ai/tools/decorator.py`

**Implementation Requirements:**

```python
"""@ai_tool decorator for LangGraph tool standardization.

This decorator converts async functions into LangGraph-compatible tools with:
- Automatic schema generation from function signatures
- RBAC permission checking
- Context injection (db_session, user_id)
- Error handling and logging
- Tool metadata generation
"""

from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar
import logging

from langchain_core.tools import StructuredTool
from sqlalchemy.ext.asyncio import AsyncSession

# Import types (will be created in BE-P2-002)
from .types import ToolContext, ToolMetadata

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def ai_tool(
    name: str | None = None,
    description: str | None = None,
    permissions: list[str] | None = None,
    category: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to convert async function into LangGraph tool.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        permissions: Required permissions for RBAC
        category: Tool category for organization

    Returns:
        Decorated function with tool metadata

    Example:
        @ai_tool(
            name="list_projects",
            description="List all projects",
            permissions=["project-read"],
            category="projects"
        )
        async def list_projects(
            search: str | None = None,
            context: ToolContext = Depends(get_tool_context)
        ) -> dict[str, Any]:
            # Implementation
            pass
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Extract metadata from function
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or "No description"
        tool_permissions = permissions or []
        tool_category = category

        # Create ToolMetadata
        metadata = ToolMetadata(
            name=tool_name,
            description=tool_description,
            permissions=tool_permissions,
            category=tool_category,
            version="1.0.0"
        )

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Extract context from kwargs
            context: ToolContext | None = kwargs.pop("context", None)

            # Validate context
            if context is None:
                logger.error(f"Tool {tool_name} called without context")
                return {"error": "Tool context not provided"}  # type: ignore

            # Check permissions
            for permission in tool_permissions:
                if not await context.check_permission(permission):
                    logger.warning(
                        f"Permission denied: user={context.user_id} "
                        f"tool={tool_name} permission={permission}"
                    )
                    return {"error": f"Permission denied: {permission} required"}  # type: ignore

            # Execute original function with context
            try:
                result = await func(context=context, *args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Error in tool {tool_name}: {e}", exc_info=True)
                return {"error": str(e)}  # type: ignore

        # Attach metadata to wrapper
        wrapper._tool_metadata = metadata  # type: ignore
        wrapper._is_ai_tool = True  # type: ignore

        return wrapper  # type: ignore

    return decorator


def to_langchain_tool(
    func: Callable,
    context: ToolContext
) -> StructuredTool:
    """Convert @ai_tool decorated function to LangChain StructuredTool.

    Args:
        func: Decorated function
        context: Tool context for execution

    Returns:
        LangChain StructuredTool instance
    """
    metadata = getattr(func, "_tool_metadata", None)

    async def wrapped(**kwargs: Any) -> str:
        """Wrapped function that includes context."""
        import json
        result = await func(context=context, **kwargs)
        return json.dumps(result)

    return StructuredTool.from_function(
        coroutine=wrapped,
        name=metadata.name if metadata else func.__name__,
        description=metadata.description if metadata else func.__doc__ or "",
        args_schema=None,  # Will be auto-generated from signature
    )
```

**Test File:** `backend/tests/unit/ai/tools/test_decorator.py`

```python
"""Tests for @ai_tool decorator."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ai.tools.decorator import ai_tool, to_langchain_tool
from app.ai.tools.types import ToolContext


class TestAiToolDecorator:
    """Test @ai_tool decorator functionality."""

    @pytest.mark.asyncio
    async def test_decorator_wraps_function(self):
        """Test decorator preserves function signature."""
        @ai_tool(name="test_tool")
        async def test_func(value: str) -> dict:
            return {"result": value}

        assert hasattr(test_func, "_is_ai_tool")
        assert hasattr(test_func, "_tool_metadata")
        assert test_func._tool_metadata.name == "test_tool"

    @pytest.mark.asyncio
    async def test_decorator_checks_permissions(self):
        """Test decorator enforces RBAC permissions."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.user_id = "user123"
        mock_context.check_permission = AsyncMock(return_value=False)

        @ai_tool(permissions=["admin-only"])
        async def admin_tool(context: ToolContext) -> dict:
            return {"success": True}

        result = await admin_tool(context=mock_context)
        assert "error" in result
        assert "Permission denied" in result["error"]

    @pytest.mark.asyncio
    async def test_decorator_injects_context(self):
        """Test decorator passes context to function."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.user_id = "user123"
        mock_context.check_permission = AsyncMock(return_value=True)

        @ai_tool()
        async def context_tool(context: ToolContext) -> dict:
            return {"user_id": context.user_id}

        result = await context_tool(context=mock_context)
        assert result["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_decorator_handles_errors(self):
        """Test decorator catches and returns errors."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.check_permission = AsyncMock(return_value=True)

        @ai_tool()
        async def failing_tool(context: ToolContext) -> dict:
            raise ValueError("Test error")

        result = await failing_tool(context=mock_context)
        assert "error" in result
        assert "Test error" in result["error"]

    def test_to_langchain_tool_conversion(self):
        """Test conversion to LangChain StructuredTool."""
        @ai_tool(name="test_tool", description="Test description")
        async def test_func(value: str) -> dict:
            return {"result": value}

        mock_context = MagicMock(spec=ToolContext)
        tool = to_langchain_tool(test_func, mock_context)

        assert tool.name == "test_tool"
        assert tool.description == "Test description"
```

**Success Criteria:**
- ✅ All tests pass
- ✅ MyPy strict mode (zero errors)
- ✅ Ruff clean (zero errors)
- ✅ 100% coverage for decorator module

---

### BE-P2-002: Define ToolContext and ToolMetadata Types

**File:** `backend/app/ai/tools/types.py`

**Implementation Requirements:**

```python
"""Type definitions for AI tool system."""

from dataclasses import dataclass
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.project import ProjectService
# Add other service imports as needed


@dataclass
class ToolContext:
    """Execution context for AI tools with dependency injection.

    Provides database session, user context, and service accessors
    for tool execution.

    Attributes:
        session: Async database session
        user_id: Authenticated user ID
        _permission_cache: Cache for permission checks
    """

    session: AsyncSession
    user_id: str
    _permission_cache: dict[str, bool] | None = None

    def __post_init__(self):
        """Initialize permission cache."""
        if self._permission_cache is None:
            self._permission_cache = {}

    @property
    def project_service(self) -> ProjectService:
        """Get project service instance."""
        return ProjectService(self.session)

    # Add other service accessors as needed
    # @property
    # def cost_element_service(self) -> CostElementService:
    #     return CostElementService(self.session)

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
        if permission in self._permission_cache:  # type: ignore
            return self._permission_cache[permission]  # type: ignore

        # TODO: Implement actual RBAC check
        # For now, allow all authenticated users
        granted = True

        # Cache result
        self._permission_cache[permission] = granted  # type: ignore
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
```

**Test File:** `backend/tests/unit/ai/tools/test_types.py`

```python
"""Tests for AI tool types."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ai.tools.types import ToolContext, ToolMetadata


class TestToolContext:
    """Test ToolContext functionality."""

    @pytest.mark.asyncio
    async def test_context_initialization(self):
        """Test ToolContext initializes with session and user_id."""
        mock_session = MagicMock()
        context = ToolContext(session=mock_session, user_id="user123")

        assert context.session == mock_session
        assert context.user_id == "user123"

    @pytest.mark.asyncio
    async def test_permission_checking(self):
        """Test permission checking with caching."""
        mock_session = MagicMock()
        context = ToolContext(session=mock_session, user_id="user123")

        # First check
        result1 = await context.check_permission("project-read")
        assert result1 is True

        # Second check should use cache
        result2 = await context.check_permission("project-read")
        assert result2 is True

    @pytest.mark.asyncio
    async def test_service_accessor(self):
        """Test project_service accessor."""
        mock_session = MagicMock()
        context = ToolContext(session=mock_session, user_id="user123")

        service = context.project_service
        assert service is not None
        assert service.session == mock_session


class TestToolMetadata:
    """Test ToolMetadata functionality."""

    def test_metadata_initialization(self):
        """Test ToolMetadata initialization."""
        metadata = ToolMetadata(
            name="test_tool",
            description="Test description",
            permissions=["project-read"],
            category="projects",
            version="1.0.0"
        )

        assert metadata.name == "test_tool"
        assert metadata.description == "Test description"
        assert metadata.permissions == ["project-read"]
        assert metadata.category == "projects"
        assert metadata.version == "1.0.0"

    def test_to_dict_serialization(self):
        """Test ToolMetadata serialization."""
        metadata = ToolMetadata(
            name="test_tool",
            description="Test description",
            permissions=["project-read"]
        )

        data = metadata.to_dict()
        assert data["name"] == "test_tool"
        assert data["description"] == "Test description"
        assert data["permissions"] == ["project-read"]
```

**Success Criteria:**
- ✅ All tests pass
- ✅ MyPy strict mode (zero errors)
- ✅ Ruff clean (zero errors)
- ✅ 100% coverage for types module

---

### BE-P2-003: Implement Tool Registry

**File:** `backend/app/ai/tools/registry.py`

**Implementation Requirements:**

```python
"""Tool registry for auto-discovery and management of AI tools."""

import importlib
import inspect
import logging
from pathlib import Path
from typing import Any

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext, ToolMetadata
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for AI tools with auto-discovery and filtering.

    Provides centralized tool management with:
    - Auto-discovery of @ai_tool decorated functions
    - Permission-based filtering
    - Category grouping
    - LangChain StructuredTool conversion
    """

    def __init__(self):
        """Initialize empty registry."""
        self._tools: dict[str, Any] = {}
        self._metadata: dict[str, ToolMetadata] = {}

    def register(self, func: Any, metadata: ToolMetadata) -> None:
        """Register a tool function with metadata.

        Args:
            func: Tool function (decorated with @ai_tool)
            metadata: Tool metadata
        """
        tool_name = metadata.name
        self._tools[tool_name] = func
        self._metadata[tool_name] = metadata
        logger.info(f"Registered tool: {tool_name}")

    def get_all_metadata(self) -> list[ToolMetadata]:
        """Get metadata for all registered tools.

        Returns:
            List of all tool metadata
        """
        return list(self._metadata.values())

    def get_by_permission(self, permission: str) -> list[ToolMetadata]:
        """Get tools that require a specific permission.

        Args:
            permission: Permission string

        Returns:
            List of tool metadata requiring the permission
        """
        return [
            metadata
            for metadata in self._metadata.values()
            if permission in metadata.permissions
        ]

    def get_by_category(self, category: str) -> list[ToolMetadata]:
        """Get tools in a specific category.

        Args:
            category: Category name

        Returns:
            List of tool metadata in the category
        """
        return [
            metadata
            for metadata in self._metadata.values()
            if metadata.category == category
        ]

    def as_langchain_tools(
        self,
        context: ToolContext,
        permissions: list[str] | None = None
    ) -> list[StructuredTool]:
        """Convert registered tools to LangChain StructuredTool instances.

        Args:
            context: Tool context for execution
            permissions: Optional permission filter (only include tools with these permissions)

        Returns:
            List of LangChain StructuredTool instances
        """
        from app.ai.tools.decorator import to_langchain_tool

        tools = []
        for name, func in self._tools.items():
            metadata = self._metadata[name]

            # Filter by permissions if specified
            if permissions:
                if not any(p in permissions for p in metadata.permissions):
                    continue

            # Convert to LangChain tool
            langchain_tool = to_langchain_tool(func, context)
            tools.append(langchain_tool)

        return tools

    def discover_and_register(self, module_path: str) -> None:
        """Discover and register @ai_tool decorated functions in a module.

        Args:
            module_path: Python module path (e.g., "app.ai.tools.project_tools")
        """
        try:
            module = importlib.import_module(module_path)

            for name, obj in inspect.getmembers(module):
                if hasattr(obj, "_is_ai_tool") and obj._is_ai_tool:
                    metadata = getattr(obj, "_tool_metadata", None)
                    if metadata:
                        self.register(obj, metadata)
                        logger.info(f"Auto-discovered tool: {metadata.name}")

        except ImportError as e:
            logger.error(f"Failed to import module {module_path}: {e}")


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance
    """
    return _registry


def register_tool(func: Any, metadata: ToolMetadata) -> None:
    """Register a tool with the global registry.

    Args:
        func: Tool function
        metadata: Tool metadata
    """
    _registry.register(func, metadata)


def get_all_tools() -> list[ToolMetadata]:
    """Get all registered tool metadata.

    Returns:
        List of all tool metadata
    """
    return _registry.get_all_metadata()


def get_tools_by_permission(permission: str) -> list[ToolMetadata]:
    """Get tools requiring a specific permission.

    Args:
        permission: Permission string

    Returns:
        List of tool metadata
    """
    return _registry.get_by_permission(permission)


def get_tools_by_category(category: str) -> list[ToolMetadata]:
    """Get tools in a specific category.

    Args:
        category: Category name

    Returns:
        List of tool metadata
    """
    return _registry.get_by_category(category)


def as_langchain_tools(
    context: ToolContext,
    permissions: list[str] | None = None
) -> list[StructuredTool]:
    """Get all tools as LangChain StructuredTool instances.

    Args:
        context: Tool context
        permissions: Optional permission filter

    Returns:
        List of LangChain StructuredTool instances
    """
    return _registry.as_langchain_tools(context, permissions)
```

**Test File:** `backend/tests/unit/ai/tools/test_registry.py`

```python
"""Tests for tool registry."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ai.tools.registry import ToolRegistry, get_registry
from app.ai.tools.types import ToolContext, ToolMetadata


class TestToolRegistry:
    """Test ToolRegistry functionality."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()

        async def test_func() -> dict:
            return {"test": True}

        metadata = ToolMetadata(
            name="test_tool",
            description="Test",
            permissions=[]
        )

        registry.register(test_func, metadata)

        assert "test_tool" in registry._tools
        assert "test_tool" in registry._metadata

    def test_get_all_metadata(self):
        """Test getting all tool metadata."""
        registry = ToolRegistry()

        async def func1() -> dict:
            return {}

        async def func2() -> dict:
            return {}

        metadata1 = ToolMetadata(
            name="tool1",
            description="Tool 1",
            permissions=[]
        )
        metadata2 = ToolMetadata(
            name="tool2",
            description="Tool 2",
            permissions=["admin"]
        )

        registry.register(func1, metadata1)
        registry.register(func2, metadata2)

        all_metadata = registry.get_all_metadata()
        assert len(all_metadata) == 2

    def test_get_by_permission(self):
        """Test filtering tools by permission."""
        registry = ToolRegistry()

        async def func1() -> dict:
            return {}

        async def func2() -> dict:
            return {}

        metadata1 = ToolMetadata(
            name="tool1",
            description="Tool 1",
            permissions=["project-read"]
        )
        metadata2 = ToolMetadata(
            name="tool2",
            description="Tool 2",
            permissions=["admin"]
        )

        registry.register(func1, metadata1)
        registry.register(func2, metadata2)

        admin_tools = registry.get_by_permission("admin")
        assert len(admin_tools) == 1
        assert admin_tools[0].name == "tool2"

    def test_get_by_category(self):
        """Test filtering tools by category."""
        registry = ToolRegistry()

        async def func1() -> dict:
            return {}

        async def func2() -> dict:
            return {}

        metadata1 = ToolMetadata(
            name="tool1",
            description="Tool 1",
            permissions=[],
            category="projects"
        )
        metadata2 = ToolMetadata(
            name="tool2",
            description="Tool 2",
            permissions=[],
            category="analysis"
        )

        registry.register(func1, metadata1)
        registry.register(func2, metadata2)

        project_tools = registry.get_by_category("projects")
        assert len(project_tools) == 1
        assert project_tools[0].name == "tool1"

    @pytest.mark.asyncio
    async def test_as_langchain_tools(self):
        """Test converting to LangChain tools."""
        from app.ai.tools.decorator import ai_tool

        @ai_tool(name="test_tool", description="Test")
        async def test_func(value: str) -> dict:
            return {"result": value}

        registry = ToolRegistry()
        metadata = ToolMetadata(
            name="test_tool",
            description="Test",
            permissions=[]
        )
        registry.register(test_func, metadata)

        mock_context = MagicMock(spec=ToolContext)
        tools = registry.as_langchain_tools(mock_context)

        assert len(tools) == 1
        assert tools[0].name == "test_tool"
```

**Success Criteria:**
- ✅ All tests pass
- ✅ MyPy strict mode (zero errors)
- ✅ Ruff clean (zero errors)
- ✅ 100% coverage for registry module

---

### BE-P2-004 & BE-P2-005: Migrate Existing Tools

**File:** `backend/app/ai/tools/project_tools.py`

**Implementation Requirements:**

```python
"""Project tools for AI agent.

Migrated from backend/app/ai/tools/__init__.py to use @ai_tool decorator.
"""

import logging
from typing import Any
from uuid import UUID

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext
from app.services.project import ProjectService

logger = logging.getLogger(__name__)


@ai_tool(
    name="list_projects",
    description="List all projects in the system with optional search, status filter, and pagination. "
                "Returns project code, name, status, budget, and dates.",
    permissions=["project-read"],
    category="projects"
)
async def list_projects(
    search: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
    sort_field: str | None = None,
    sort_order: str = "asc",
    context: ToolContext | None = None,
) -> dict[str, Any]:
    """List all projects in the system.

    Args:
        search: Search term for project code or name
        status: Filter by status code (e.g., 'ACT', 'PLN')
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        sort_field: Field to sort by (e.g., 'name', 'code')
        sort_order: Sort order (asc or desc)
        context: Injected tool execution context

    Returns:
        Dictionary with projects list, total count, skip, and limit
    """
    # Context is validated by decorator
    assert context is not None

    try:
        # Build filter string if status is provided
        filters = f"status:{status}" if status else None

        projects, total = await context.project_service.get_projects(
            skip=skip,
            limit=limit,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order,
            branch="main",
        )

        return {
            "projects": [
                {
                    "id": str(p.project_id),
                    "code": p.code,
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "budget": float(p.budget) if p.budget else None,
                    "start_date": p.start_date.isoformat() if p.start_date else None,
                    "end_date": p.end_date.isoformat() if p.end_date else None,
                }
                for p in projects
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error in list_projects: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_project",
    description="Get detailed information about a specific project by its ID. "
                "Requires the project ID as a UUID string.",
    permissions=["project-read"],
    category="projects"
)
async def get_project(
    project_id: str,
    context: ToolContext | None = None,
) -> dict[str, Any]:
    """Get detailed information about a specific project.

    Args:
        project_id: Project ID as UUID string
        context: Injected tool execution context

    Returns:
        Dictionary with detailed project information
    """
    # Context is validated by decorator
    assert context is not None

    try:
        project = await context.project_service.get_by_id(UUID(project_id))

        if not project:
            return {"error": f"Project {project_id} not found"}

        return {
            "id": str(project.project_id),
            "code": project.code,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "budget": float(project.budget) if project.budget else None,
            "start_date": project.start_date.isoformat()
            if project.start_date
            else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "branch": project.branch,
        }
    except ValueError:
        return {"error": f"Invalid project ID: {project_id}"}
    except Exception as e:
        logger.error(f"Error in get_project: {e}")
        return {"error": str(e)}
```

**Test File:** `backend/tests/integration/ai/tools/test_project_tools.py`

```python
"""Integration tests for migrated project tools."""

import pytest
from uuid import uuid4

from app.ai.tools.project_tools import list_projects, get_project
from app.ai.tools.types import ToolContext
from app.services.project import ProjectService


@pytest.mark.asyncio
async def test_list_projects_migrated_equivalence(db_session, test_user):
    """Test migrated list_projects produces same results as original."""
    # Setup context
    context = ToolContext(session=db_session, user_id=test_user.id)

    # Call migrated tool
    result = await list_projects(context=context)

    # Validate structure
    assert "projects" in result
    assert "total" in result
    assert "skip" in result
    assert "limit" in result
    assert isinstance(result["projects"], list)

    # Validate can call with parameters
    result_with_params = await list_projects(
        search="test",
        skip=0,
        limit=10,
        context=context
    )
    assert "projects" in result_with_params


@pytest.mark.asyncio
async def test_get_project_migrated_equivalence(db_session, test_project, test_user):
    """Test migrated get_project produces same results as original."""
    # Setup context
    context = ToolContext(session=db_session, user_id=test_user.id)

    # Call migrated tool with valid project
    result = await get_project(
        project_id=str(test_project.project_id),
        context=context
    )

    # Validate structure
    assert "id" in result
    assert "code" in result
    assert "name" in result
    assert result["id"] == str(test_project.project_id)


@pytest.mark.asyncio
async def test_get_project_not_found(db_session, test_user):
    """Test get_project returns error for non-existent project."""
    context = ToolContext(session=db_session, user_id=test_user.id)

    result = await get_project(
        project_id=str(uuid4()),
        context=context
    )

    assert "error" in result
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_list_projects_permission_check(db_session, test_user):
    """Test list_projects enforces RBAC permissions."""
    context = ToolContext(session=db_session, user_id=test_user.id)

    # Mock permission check to deny
    async def deny_permission(permission: str) -> bool:
        return False

    context.check_permission = deny_permission

    result = await list_projects(context=context)

    assert "error" in result
    assert "Permission denied" in result["error"]
```

**Success Criteria:**
- ✅ Integration tests pass
- ✅ Migrated tools produce same results as original
- ✅ Permission checking works
- ✅ Error handling works
- ✅ MyPy strict mode (zero errors)
- ✅ Ruff clean (zero errors)

---

## Quality Gates (Run After Each Task)

### MyPy Strict Mode
```bash
cd backend && uv run mypy app/ai/tools/ --strict
```

### Ruff Linting
```bash
cd backend && uv run ruff check app/ai/tools/
```

### Test Coverage
```bash
cd backend && uv run pytest tests/unit/ai/tools/ tests/integration/ai/tools/ --cov=app/ai/tools --cov-report=term-missing
```

### Run All Tests
```bash
cd backend && uv run pytest tests/unit/ai/tools/ tests/integration/ai/tools/ -v
```

---

## Execution Checklist

### Task Completion Checklist (for each task)

- [ ] Write failing tests (RED)
- [ ] Implement minimum code (GREEN)
- [ ] Refactor while keeping tests green
- [ ] Run MyPy - must pass with zero errors
- [ ] Run Ruff - must pass with zero errors
- [ ] Run coverage - must achieve 80%+ for new code
- [ ] Document any deviations from plan
- [ ] Update task status in project tracking

### Phase 2 Completion Criteria

From 01-plan.md:

**Code Implementation:**
- [ ] `@ai_tool` decorator implemented in `backend/app/ai/tools/decorator.py`
- [ ] Tool registry implemented in `backend/app/ai/tools/registry.py`
- [ ] `ToolContext` and `ToolMetadata` types defined
- [ ] `list_projects` tool migrated (wraps `ProjectService.get_projects()`)
- [ ] `get_project` tool migrated (wraps `ProjectService.get_project()`)

**Testing:**
- [ ] Unit tests for decorator pass
- [ ] Unit tests for registry pass
- [ ] Integration tests for tool execution pass
- [ ] Regression tests show migrated tools produce same results
- [ ] 80%+ test coverage for tools module

**Code Quality:**
- [ ] Zero MyPy errors (strict mode)
- [ ] Zero Ruff errors
- [ ] All code follows project coding standards

---

## Next Steps

After completing Phase 2:

1. **Update 02-do.md** with Phase 2 completion status
2. **Proceed to Phase 3** - Migration & Expansion (tasks BE-P3-001 through BE-P3-006)
3. **CREATE 03-check.md** after Phase 4 completes

---

**Phase 2 DO Execution Plan Ready** ✅

**Based on:** /home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-03-09-langgraph-agent-enhancement/01-plan.md
**Approved:** Phase 1 CHECK report (Option B - Thorough Approach)
