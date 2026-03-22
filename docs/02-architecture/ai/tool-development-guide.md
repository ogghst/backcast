# AI Tool Development Guide

**Version:** 1.1.0
**Last Updated:** 2026-03-22
**Audience:** Backend Developers

---

## Overview

This guide explains how to create, test, and deploy AI tools for the Backcast EVS LangGraph agent. Tools are the primary way the AI agent interacts with the system - they wrap existing service methods and provide a standardized interface for LLM-powered conversations.

### What is an AI Tool?

An AI tool is an async function decorated with `@ai_tool` that:

- Wraps an existing service method (no business logic duplication)
- Enforces RBAC permissions at the tool level
- Receives context (database session, user ID) via dependency injection
- Returns structured data that the LLM can use in responses
- Is auto-discovered by the tool registry

> [!NOTE]
> The `@ai_tool` decorator converts the function into a LangChain `BaseTool` instance. To execute the tool in Python code (like in tests), you must use `.ainvoke()` instead of calling it directly.

### Key Principles

1. **Wrap, Don't Duplicate**: Tools should wrap existing service methods, not reimplement business logic
2. **Security First**: Always enforce permissions via the `@ai_tool` decorator
3. **Context Injection**: Use `ToolContext` for database access and user identification
4. **Temporal Awareness**: For versioned entities, use temporal params from `context` to respect Time Machine state
5. **Structured Returns**: Return dictionaries/Pydantic models that LLMs can understand
6. **Error Handling**: Let the decorator handle exceptions, focus on business logic
7. **Observability**: Log temporal context for ALL tools (both branchable and non-branchable entities)

> [!IMPORTANT]
> **Temporal Context**: When creating tools that query versioned entities (Projects, Change Orders, WBEs, etc.), you MUST use temporal parameters from `ToolContext` to respect the user's Time Machine state. See [Temporal Context Patterns](./temporal-context-patterns.md) for detailed guidance.

> [!NOTE]
> **Temporal Logging for All Tools**: Log temporal context using `log_temporal_context()` for ALL tools, including those that query non-branchable entities (e.g., Forecasts, Cost Registrations, Progress Entries). This provides consistent observability across the entire tool suite and helps debug temporal state issues.

---

## Quick Start (5 Minutes)

### Step 1: Create Your Tool

Create a new file in `app/ai/tools/` or add to an existing file:

```python
# app/ai/tools/project_tools.py

from typing import Annotated
from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext
from app.services.project import ProjectService

@ai_tool(
    name="get_project_details",
    description="Get detailed information about a specific project",
    permissions=["project-read"],
    category="projects"
)
async def get_project_details(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,
) -> dict[str, object]:
    """Get detailed information for a project.

    Args:
        project_id: UUID of the project to retrieve

    Returns:
        Dictionary with project details including name, code, status, budget
    """
    service = ProjectService(context.db_session)
    project = await service.get_project(project_id)

    if not project:
        return {"error": "Project not found"}

    return {
        "id": str(project.id),
        "name": project.name,
        "code": project.code,
        "status": project.status,
        "budget": float(project.budget) if project.budget else None,
        "start_date": project.start_date.isoformat() if project.start_date else None,
    }
```

### Step 2: Test Your Tool

Create a test file:

```python
# tests/unit/ai/tools/test_project_tools.py

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ai.tools.project_tools import get_project_details
from app.ai.tools.types import ToolContext

@pytest.mark.asyncio
async def test_get_project_details_success():
    # Arrange
    mock_session = MagicMock()
    context = MagicMock(spec=ToolContext)
    context.db_session = mock_session
    context.user_id = "test-user"
    context.check_permission = AsyncMock(return_value=True)

    # Act
    result = await get_project_details.ainvoke({
        "project_id": "123e4567-e89b-12d3-a456-426614174000",
        "context": context
    })

    # Assert
    assert "error" not in result
    assert context.check_permission.called
```

### Step 3: Run Tests

```bash
uv run pytest tests/unit/ai/tools/test_project_tools.py -v
```

That's it! Your tool is now ready to be used by the AI agent.

---

## Tool Anatomy

### The @ai_tool Decorator

The `@ai_tool` decorator provides:

1. **Automatic Schema Generation**: Converts function signature to LangChain tool schema
2. **RBAC Enforcement**: Checks permissions before execution
3. **Context Injection**: Provides database session and user ID
4. **Error Handling**: Catches exceptions and returns error responses
5. **Metadata Attachment**: Stores tool metadata for registry

### Decorator Parameters

```python
@ai_tool(
    name="tool_name",              # Required: Tool name (unique)
    description="Tool description", # Required: What the tool does
    permissions=["perm1", "perm2"], # Required: Permissions for RBAC
    category="category_name"        # Optional: Tool category
)
```

### Function Signature

```python
async def tool_function(
    param1: type1,         # Tool parameters (what LLM provides)
    param2: type2,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # Always last parameter (injected automatically)
) -> dict[str, Any]:      # Return structured data
    """Docstring becomes tool description if not provided to decorator."""
    # Implementation
    pass
```

---

## Common Patterns

### Pattern 1: List/Search (CRUD - Read)

```python
@ai_tool(
    name="list_projects",
    description="List all projects with optional filtering",
    permissions=["project-read"],
    category="projects"
)
async def list_projects(
    search: str | None = None,
    status: str | None = None,
    limit: int = 100,
    context: Annotated[ToolContext, InjectedToolArg] = None,
) -> list[dict[str, object]]:
    """List projects with optional search and status filter.

    Args:
        search: Search term for project name or code
        status: Filter by status (e.g., 'ACT', 'PLN')
        limit: Maximum number of results (default: 100)

    Returns:
        List of project dictionaries
    """
    service = ProjectService(context.db_session)
    projects = await service.get_projects(search=search, status=status, limit=limit)

    return [
        {
            "id": str(p.id),
            "name": p.name,
            "code": p.code,
            "status": p.status,
        }
        for p in projects
    ]
```

### Pattern 2: Get Single Item (CRUD - Read)

```python
@ai_tool(
    name="get_project",
    description="Get detailed information about a specific project",
    permissions=["project-read"],
    category="projects"
)
async def get_project(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,
) -> dict[str, object]:
    """Get detailed project information.

    Args:
        project_id: UUID of the project

    Returns:
        Project details or error if not found
    """
    service = ProjectService(context.db_session)
    project = await service.get_project(project_id)

    if not project:
        return {"error": "Project not found"}

    return {
        "id": str(project.id),
        "name": project.name,
        "code": project.code,
        "status": project.status,
        "budget": float(project.budget) if project.budget else 0.0,
        "description": project.description,
    }
```

### Pattern 3: Create Item (CRUD - Create)

```python
@ai_tool(
    name="create_project",
    description="Create a new project",
    permissions=["project-create"],
    category="projects"
)
async def create_project(
    name: str,
    code: str,
    status: str = "PLN",
    budget: float | None = None,
    description: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,
) -> dict[str, object]:
    """Create a new project.

    Args:
        name: Project name
        code: Three-letter project code
        status: Project status (default: 'PLN')
        budget: Optional project budget
        description: Optional project description

    Returns:
        Created project details
    """
    from app.models.schemas.project import ProjectCreate

    service = ProjectService(context.db_session)

    project_data = ProjectCreate(
        name=name,
        code=code,
        status=status,
        budget=budget,
        description=description,
    )

    project = await service.create_project(project_data)

    return {
        "id": str(project.id),
        "name": project.name,
        "code": project.code,
        "status": project.status,
    }
```

### Pattern 4: Analysis/EVM

```python
@ai_tool(
    name="calculate_evm_metrics",
    description="Calculate Earned Value Management metrics for a project",
    permissions=["evm-read"],
    category="analysis"
)
async def calculate_evm_metrics(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,
) -> dict[str, float]:
    """Calculate EVM metrics for a project.

    Args:
        project_id: UUID of the project

    Returns:
        Dictionary with EVM metrics (PV, EV, AC, CV, SV, CPI, SPI)
    """
    from app.services.evm import EVMService

    service = EVMService(context.db_session)
    metrics = await service.calculate_metrics(project_id)

    return {
        "planned_value": float(metrics.planned_value),
        "earned_value": float(metrics.earned_value),
        "actual_cost": float(metrics.actual_cost),
        "cost_variance": float(metrics.cost_variance),
        "schedule_variance": float(metrics.schedule_variance),
        "cost_performance_index": float(metrics.cost_performance_index),
        "schedule_performance_index": float(metrics.schedule_performance_index),
    }
```

---

## Best Practices

### 1. Service Wrapping

✅ **DO:** Wrap existing service methods

```python
service = ProjectService(context.db_session)
projects = await service.get_projects(search=search)
```

❌ **DON'T:** Duplicate business logic

```python
# Bad: Direct database access
from app.models.domain.project import Project
result = await context.db_session.execute(select(Project).where(...))
```

### 2. Error Handling

✅ **DO:** Let the decorator handle exceptions

```python
project = await service.get_project(project_id)
if not project:
    return {"error": "Project not found"}
return project.to_dict()
```

❌ **DON'T:** Swallow exceptions

```python
try:
    project = await service.get_project(project_id)
except Exception as e:
    return {"error": str(e)}  # Decorator does this automatically
```

### 3. Type Hints

✅ **DO:** Use precise type hints

```python
async def get_project(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,
) -> dict[str, object]:
```

❌ **DON'T:** Use vague types

```python
async def get_project(
    project_id: any,
    context: any
) -> any:
```

### 4. Permission Specification

✅ **DO:** Specify exact permissions needed

```python
@ai_tool(
    permissions=["project-read", "evm-read"]  # Specific permissions
)
```

❌ **DON'T:** Use overly broad permissions

```python
@ai_tool(
    permissions=["admin"]  # Too broad
)
```

### 5. Context Usage

✅ **DO:** Use context for database and user

```python
service = ProjectService(context.db_session)
user_id = context.user_id
```

❌ **DON'T:** Accept user_id as parameter (security risk)

```python
async def bad_tool(user_id: str, context: ToolContext):
    # User could spoof user_id!
```

---

## Testing Strategies

### Unit Tests

Test tool logic in isolation with mocked services:

```python
@pytest.mark.asyncio
async def test_list_projects_filters_by_status():
    # Arrange
    mock_session = MagicMock()
    context = MagicMock(spec=ToolContext)
    context.db_session = mock_session
    context.check_permission = AsyncMock(return_value=True)

    mock_service = MagicMock()
    mock_service.get_projects = AsyncMock(return_value=[])

    # Act
    result = await list_projects.ainvoke({
        "status": "ACT",
        "context": context
    })

    # Assert
    assert isinstance(result, list)
    assert context.check_permission.called
```

### Integration Tests

Test tool with real database:

```python
@pytest.mark.asyncio
async def test_list_projects_integration(test_db, authenticated_user):
    # Arrange
    context = ToolContext(
        db_session=test_db,
        user_id=str(authenticated_user.id)
    )

    # Act
    result = await list_projects.ainvoke({"context": context})

    # Assert
    assert isinstance(result, list)
```

### Security Tests

Test permission enforcement:

```python
@pytest.mark.asyncio
async def test_tool_denied_without_permission():
    # Arrange
    context = MagicMock(spec=ToolContext)
    context.check_permission = AsyncMock(return_value=False)

    # Act
    result = await secure_tool.ainvoke({"context": context})

    # Assert
    assert "error" in result
    assert "permission" in result["error"].lower()
```

### Async Fixture Pattern (pytest-asyncio)

When writing tests for async tools in pytest-asyncio strict mode, use `@pytest_asyncio.fixture` for fixtures that async tests depend on:

```python
import pytest_asyncio

@pytest_asyncio.fixture
async def test_forecast(test_db):
    """Create a test forecast for async tests."""
    # Setup async fixture data
    forecast = await ForecastService(test_db).create_forecast(...)
    return forecast, forecast.cost_element_id

@pytest.mark.asyncio
async def test_get_forecast_with_fixture(test_forecast):
    """Test using async fixture."""
    forecast, cost_element_id = test_forecast

    result = await get_forecast.ainvoke({
        "cost_element_id": str(cost_element_id),
        "context": mock_context
    })

    assert result["id"] == str(forecast.forecast_id)
```

> [!IMPORTANT]
> **Common Mistake**: Using `@pytest.fixture` (non-async) for fixtures that async tests depend on causes pytest-asyncio strict mode to fail with "requested an async fixture" errors. Always use `@pytest_asyncio.fixture` for async test fixtures.

### Edge Case Testing

Test error paths and edge cases to improve coverage:

```python
@pytest.mark.asyncio
async def test_get_forecast_invalid_uuid_format():
    """Test with invalid UUID format."""
    result = await get_forecast.ainvoke({
        "cost_element_id": "not-a-uuid",
        "context": mock_context
    })
    assert "error" in result

@pytest.mark.asyncio
async def test_get_forecast_empty_uuid():
    """Test with empty UUID string."""
    result = await get_forecast.ainvoke({
        "cost_element_id": "",
        "context": mock_context
    })
    assert "error" in result

@pytest.mark.asyncio
async def test_get_forecast_not_found():
    """Test with non-existent forecast."""
    result = await get_forecast.ainvoke({
        "cost_element_id": str(uuid4()),
        "context": mock_context
    })
    assert "error" in result
```

---

## Tool Registry

### Auto-Discovery

Tools are auto-discovered by the `@ai_tool` decorator. No manual registration needed!

```python
# app/ai/tools/__init__.py

from langchain_core.tools import BaseTool

def get_all_tools() -> list[BaseTool]:
    """Get all registered tools."""
    # Auto-discovery happens via decorator
    # Tools with @_is_ai_tool attribute are collected
    pass
```

### Tool Metadata

Each tool has metadata attached:

```python
tool._tool_metadata.name        # Tool name
tool._tool_metadata.description # Tool description
tool._tool_metadata.permissions # Required permissions (list of strings)
tool._tool_metadata.category    # Tool category
tool._tool_metadata.version     # Tool version
```

> [!IMPORTANT]
> **Permission Access**: When verifying tool permissions in tests, always check `tool._tool_metadata.permissions`, not `tool.permissions`. The decorator stores metadata in the `_tool_metadata` attribute.

Example: Checking tool permissions in tests

```python
def test_tool_has_correct_permissions():
    """Verify tool has required permissions."""
    # Correct: Check _tool_metadata.permissions
    assert "forecast-read" in get_forecast._tool_metadata.permissions

    # Incorrect: This will fail
    # assert hasattr(get_forecast, "permissions")  # False
```

---

## Performance Considerations

### 1. Fast Execution

Keep tools fast - the LLM waits for tool results:

```python
# ✅ Good: Fast query
projects = await service.get_projects(limit=10)

# ❌ Bad: Slow query processing all projects
projects = await service.get_projects()  # No limit
```

### 2. Pagination

Use pagination for large result sets:

```python
async def list_projects(
    limit: int = 100,
    offset: int = 0,
    context: Annotated[ToolContext, InjectedToolArg] = None,
) -> dict[str, Any]:
    projects = await service.get_projects(limit=limit, offset=offset)
    return {
        "projects": [p.to_dict() for p in projects],
        "total": len(projects),
        "limit": limit,
        "offset": offset,
    }
```

### 3. Selective Fields

Return only necessary fields:

```python
# ✅ Good: Selective fields
return {
    "id": str(project.id),
    "name": project.name,
    "status": project.status,
}

# ❌ Bad: All fields (large payload)
return project.to_dict()  # Includes all fields
```

---

## Temporal Logging Best Practices

### Log Temporal Context for All Tools

All tools should log temporal context for observability, even when querying non-branchable entities:

```python
from app.ai.tools.temporal_logging import log_temporal_context, add_temporal_metadata

@ai_tool(
    name="get_forecast",
    description="Get the forecast for a specific cost element",
    permissions=["forecast-read"],
    category="forecast"
)
async def get_forecast(
    cost_element_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,
) -> dict[str, Any]:
    """Get forecast for a cost element.

    Args:
        cost_element_id: UUID of the cost element

    Returns:
        Forecast details with temporal metadata
    """
    # Log temporal context for observability
    log_temporal_context("get_forecast", context)

    try:
        service = ForecastService(context.session)
        forecast = await service.get_for_cost_element(
            cost_element_id=UUID(cost_element_id),
            branch=context.branch_name or "main",
        )

        result = {
            "id": str(forecast.forecast_id),
            "eac_amount": float(forecast.eac_amount),
            "as_of_date": forecast.as_of_date.isoformat(),
        }

        # Add temporal metadata to result
        return add_temporal_metadata(result, context)
    except Exception as e:
        return add_temporal_metadata({"error": str(e)}, context)
```

### Benefits of Temporal Logging

1. **Observability**: Track which temporal context (branch, as_of) tools are using
2. **Debugging**: Quickly identify temporal state issues in logs
3. **Audit Trail**: Maintain complete record of temporal context for all tool invocations
4. **Consistency**: Uniform logging pattern across all tools (branchable and non-branchable)

### When to Use Temporal Logging

| Entity Type | Branchable | Log Temporal Context | Use Temporal Metadata |
| ----------- | ---------- | -------------------- | --------------------- |
| Projects | Yes | Always | Always |
| Change Orders | Yes | Always | Always |
| WBEs | Yes | Always | Always |
| Forecasts | No | Always | Always |
| Cost Registrations | No | Always | Always |
| Progress Entries | No | Always | Always |
| Analysis/EVM | N/A | Always | Always |

> [!NOTE]
> **Rule of Thumb**: If a tool queries data from the database, log temporal context and add temporal metadata to results. This includes ALL tools, regardless of whether the underlying entity supports branching.

---

## Security Considerations

### 1. Permission Checking

Always specify permissions:

```python
@ai_tool(
    permissions=["project-read"],  # Required!
)
```

### 2. User Context

Use `context.user_id` for filtering:

```python
# Good: Filter by current user
projects = await service.get_projects(user_id=context.user_id)

# Bad: Accept user_id as parameter
async def list_projects(user_id: str, context: Annotated[ToolContext, InjectedToolArg] = None):
    # User could impersonate others!
```

### 3. Input Validation

Validate inputs:

```python
async def get_project(project_id: str, context: Annotated[ToolContext, InjectedToolArg] = None):
    # Validate UUID format
    try:
        UUID(project_id)
    except ValueError:
        return {"error": "Invalid project ID format"}

    # Proceed with lookup
    project = await service.get_project(project_id)
    # ...
```

---

## Troubleshooting

### Tool Not Discovered

**Problem:** Tool doesn't appear in registry

**Solution:** Ensure file is imported in `app/ai/tools/__init__.py`:

```python
from app.ai.tools.project_tools import list_projects, get_project
```

### Permission Denied

**Problem:** Tool always returns permission denied

**Solution:** Check that `context.check_permission()` is working:

```python
# Test with mock
context.check_permission = AsyncMock(return_value=True)
```

### Context Not Provided

**Problem:** "Tool context not provided" error

**Solution:** Ensure `context` is the last parameter:

```python
# ✅ Correct
async def tool(param1: str, context: Annotated[ToolContext, InjectedToolArg] = None):

# ❌ Wrong
async def tool(context: ToolContext, param1: str):

# ❌ Wrong (missing InjectedToolArg)
async def tool(param1: str, context: ToolContext):
```

### Async Fixture Errors (pytest-asyncio)

**Problem:** Tests fail with "requested an async fixture 'X', with no plugin or hook that handled it"

**Root Cause:** Using `@pytest.fixture` (non-async) for fixtures that async tests depend on, violating pytest-asyncio strict mode requirements

**Solution:** Convert fixtures to `@pytest_asyncio.fixture`:

```python
# ❌ Wrong: Non-async fixture
@pytest.fixture
def test_forecast(test_db):
    forecast = await ForecastService(test_db).create_forecast(...)
    return forecast

# ✅ Correct: Async fixture
import pytest_asyncio

@pytest_asyncio.fixture
async def test_forecast(test_db):
    forecast = await ForecastService(test_db).create_forecast(...)
    return forecast
```

**Prevention:**
- Always use `@pytest_asyncio.fixture` for fixtures that async tests depend on
- Run test suite incrementally during implementation to catch fixture issues early
- Verify fixture execution during RED phase of TDD, not just test collection

### Permission Test Failures

**Problem:** Test fails with `AssertionError: tool should have permissions`

**Root Cause:** Test checks `hasattr(tool, "permissions")` but decorator stores permissions in `tool._tool_metadata.permissions`

**Solution:** Check the correct attribute path:

```python
# ❌ Wrong: Direct attribute access
assert hasattr(get_forecast, "permissions")  # False
assert "forecast-read" in get_forecast.permissions  # AttributeError

# ✅ Correct: Check _tool_metadata
assert hasattr(get_forecast, "_tool_metadata")  # True
assert "forecast-read" in get_forecast._tool_metadata.permissions  # True
```

**Prevention:**
- Review decorator implementation (`decorator.py`) before writing tests
- Use test discovery phase to verify tool attributes
- Check for `_tool_metadata` attribute in tests, not just `permissions`

---

## Templates

Ready-to-use templates are available:

- **CRUD Template**: `app/ai/tools/templates/crud_template.py`
- **Change Order Template**: `app/ai/tools/templates/change_order_template.py`
- **Analysis Template**: `app/ai/tools/templates/analysis_template.py`

Copy a template and modify for your use case.

---

## References

- [API Reference](/home/nicola/dev/backcast_evs/docs/02-architecture/ai/api-reference.md)
- [Troubleshooting Guide](/home/nicola/dev/backcast_evs/docs/02-architecture/ai/troubleshooting.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [ADR 009: LangGraph Rewrite](/home/nicola/dev/backcast_evs/docs/02-architecture/decisions/009-langgraph-rewrite.md)

---

**Questions?** Ask in #backend-dev channel or create an issue.
