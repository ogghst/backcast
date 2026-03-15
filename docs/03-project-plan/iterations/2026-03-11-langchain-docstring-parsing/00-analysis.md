# Analysis: LangChain Docstring Parsing for AI Tool Parameter Descriptions

**Created:** 2026-03-11
**Revised:** 2026-03-11 (focused on Option A, validated against LangGraph 1.0 + coding standards)
**Priority:** Current sprint (E09-LANGGRAPH)

---

## Clarified Requirements

Refactor the `@ai_tool` decorator system to compose with LangChain's `@tool` decorator, gaining:
- Native `parse_docstring=True` for automatic parameter descriptions
- `InjectedToolArg` annotation for `ToolContext` (hidden from LLM schema)
- RBAC via `RBACToolNode` subclass (Option A)
- Reusable RBAC decorator shared between AI tools and API routes

### Functional Requirements

1. **Enable Docstring Parsing**: Use `@tool(parse_docstring=True)` to extract parameter descriptions from Google-style docstrings
2. **Context Injection via `InjectedToolArg`**: Hide `context: ToolContext` from LLM schema; `ToolNode` injects at runtime
3. **RBAC via `RBACToolNode`**: Permission checks at `ToolNode` level, not per-tool
4. **Reusable RBAC Decorator**: Extract permission checking into a decorator that works for both AI tools and API routes
5. **Backward Compatibility**: All existing tools continue to work

### Constraints

1. **Coding Standards**: Google-style docstrings with Context, Args, Returns, Raises sections
2. **MyPy strict mode** with `disallow_any_explicit = True` — no `Any` types
3. **Type Safety**: Use `Mapped[]`, `typing.Annotated` patterns
4. **LangChain/LangGraph**: `parse_docstring`, `InjectedToolArg`, `ToolNode` patterns

---

## Context Discovery

### Current Tool Architecture (Dual System)

The codebase has **two parallel implementations**:

| Component | Location | Pattern | Status |
|---|---|---|---|
| `__init__.py` tools | [\_\_init\_\_.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/__init__.py) | Pydantic schemas + `StructuredTool.from_function()` | **Active** |
| `@ai_tool` decorator | [decorator.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/decorator.py) | Custom decorator + `to_langchain_tool()` | **Built, unused** |
| `ToolRegistry` | [registry.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/registry.py) | Auto-discovery + filtering | **Built, unused** |

> [!IMPORTANT]
> `AgentService` uses `create_project_tools()` from `__init__.py`, NOT the `@ai_tool` decorator. This refactor converges both into one framework-aligned pattern.

### Current RBAC Stack

Three separate RBAC implementations exist today:

| Layer | Component | Pattern | Sync/Async |
|---|---|---|---|
| **Core** | [RBACServiceABC](file:///home/nicola/dev/backcast_evs/backend/app/core/rbac.py) | `has_permission(user_role, permission) → bool` | **Sync** |
| **API** | [RoleChecker](file:///home/nicola/dev/backcast_evs/backend/app/api/dependencies/auth.py#L67-L133) | FastAPI `Depends` callable class, uses `RBACServiceABC` | Async (wrapper) |
| **AI Tools** | [ToolContext.check_permission](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/types.py#L33-L56) | Stubbed (`return True`), doesn't use `RBACServiceABC` | Async (stubbed) |

> [!WARNING]
> `ToolContext.check_permission()` is **completely stubbed** — it always returns `True`. It does not call `RBACServiceABC` at all. The actual RBAC enforcement for AI tools only happens at the WebSocket route level (`ai-chat` permission check), not per-tool.

### Graph Pipeline (Production Path)

```
AgentService.chat() / chat_stream()
  → ToolContext(session, user_id)
  → create_project_tools(context)           # __init__.py
  → create_graph(llm, tools)                # graph.py
    → llm.bind_tools(tools)                 # schema → LLM
    → ToolNode(tools)                       # execution
  → graph.ainvoke() / astream_events()
```

### Domain Entities & Planned Tools (22 Functions)

| Template | Tools | Entities | Permissions |
|---|---|---|---|
| [crud_template.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/templates/crud_template.py) | 6 | Project, WBE | project-read/create/update, wbe-read/create |
| [change_order_template.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/templates/change_order_template.py) | 8 | ChangeOrder | change-order-read/create/update/approve |
| [analysis_template.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/templates/analysis_template.py) | 8 | Project (EVM/Forecast) | evm-read, forecast-read |

---

## LangGraph 1.0 Best Practices (Validated)

### 1. `@tool(parse_docstring=True)` — Schema from Docstrings

```python
from langchain_core.tools import tool

@tool(parse_docstring=True)
def search_database(query: str, limit: int = 10) -> str:
    """Search the customer database for records matching the query.

    Args:
        query: Search terms to look for
        limit: Maximum number of results to return
    """
    return f"Found {limit} results for '{query}'"
```

The LLM receives: `{"query": {"description": "Search terms to look for", ...}}`.

### 2. `InjectedToolArg` — Hide Runtime Context from LLM

```python
from typing import Annotated
from langchain_core.tools import tool, InjectedToolArg

@tool(parse_docstring=True)
async def get_project(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg],
) -> str:
    """Get detailed information about a project.

    Args:
        project_id: UUID of the project to retrieve
    """
    ...
```

- `InjectedToolArg` marks `context` as system-injected → excluded from tool schema
- `ToolNode` injects the value at runtime
- The LLM only sees `project_id`

### 3. `ToolNode` — Handles Injection + Error Handling

```python
tool_node = ToolNode(
    tools=[list_projects, get_project],
    handle_tool_errors=True,
    messages_key="messages",
)
```

### 4. Tool Best Practices Summary

| Practice | Guideline |
|---|---|
| Naming | Clear, `snake_case` names |
| Docstrings | One-line summary + Context + Args + Returns + Raises |
| Type hints | All arguments typed — they become the input schema |
| Single responsibility | One operation per tool |
| Errors | Return error dicts, don't raise exceptions |
| Context | `InjectedToolArg` for custom context, `InjectedState` for graph state |

---

## Solution Design: Option A — `RBACToolNode` with Reusable RBAC Decorator

### Architecture Overview

```
@ai_tool(permissions=["project-read"], category="projects")
   │
   ├─ Internally applies @tool(parse_docstring=True)
   ├─ Attaches ToolMetadata (permissions, category, version)
   └─ Uses InjectedToolArg for ToolContext

RBACToolNode(ToolNode)
   │
   ├─ Before each tool execution: check permissions via RBACServiceABC
   ├─ On permission denied: return ToolMessage with error
   └─ On success: delegate to parent ToolNode

@require_permission("project-read")  ← Reusable decorator
   │
   ├─ Used by RBACToolNode (AI tool path)
   └─ Used by API route dependencies (REST path)
```

### Reusable RBAC Decorator: `@require_permission`

The goal is a **single permission-checking decorator** that works across:
1. **AI tools** — via `RBACToolNode` pre-execution hook
2. **API routes** — as a standalone decorator or integrated with `RoleChecker`
3. **Service methods** — as a general-purpose permission guard

#### Current State (Fragmented)

```python
# API routes: FastAPI Depends callable class
class RoleChecker:
    def __init__(self, required_permission: str | None = None): ...
    async def __call__(self, current_user, rbac_service) -> User: ...

# AI tools: Stubbed, doesn't use RBACServiceABC at all
class ToolContext:
    async def check_permission(self, permission: str) -> bool:
        return True  # TODO: Implement actual RBAC check
```

#### Proposed: `@require_permission` Decorator

```python
# app/core/rbac.py — NEW addition

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def require_permission(
    permission: str,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that enforces RBAC permission before function execution.

    Context: Reusable across AI tools and API routes. Delegates to
    RBACServiceABC for actual permission resolution.

    Args:
        permission: Required permission string (e.g., "project-read")

    Returns:
        Decorated function that checks permission before execution

    Raises:
        PermissionError: If user lacks the required permission

    Note:
        The decorated function must have access to user_role either via:
        - A `context` parameter with `user_role` attribute (AI tools)
        - A `current_user` parameter with `role` attribute (API routes)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Attach permission metadata for introspection
        if not hasattr(func, "_required_permissions"):
            func._required_permissions = []  # type: ignore[attr-defined]
        func._required_permissions.append(permission)  # type: ignore[attr-defined]

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Check permission before executing the wrapped function.

            Context: Permission checking wrapper. Resolves user_role from
            context or current_user parameter.

            Args:
                *args: Positional arguments passed to wrapped function
                **kwargs: Keyword arguments passed to wrapped function

            Returns:
                Result of the wrapped function if permission granted

            Raises:
                PermissionError: If user lacks required permission
            """
            rbac_service = get_rbac_service()

            # Resolve user_role from context (AI tools) or current_user (API)
            user_role: str | None = None

            # AI tool path: context has user info
            context = kwargs.get("context")
            if context is not None and hasattr(context, "user_role"):
                user_role = context.user_role

            # API route path: current_user has role
            current_user = kwargs.get("current_user")
            if current_user is not None and hasattr(current_user, "role"):
                user_role = current_user.role

            if user_role is None:
                raise PermissionError(
                    f"Cannot resolve user_role for permission check: {permission}"
                )

            if not rbac_service.has_permission(user_role, permission):
                raise PermissionError(
                    f"Permission denied: {permission} required"
                )

            return await func(*args, **kwargs)  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator
```

#### How It Integrates

**AI Tools (via `RBACToolNode`):**
```python
class RBACToolNode(ToolNode):
    """ToolNode subclass with RBAC permission enforcement.

    Context: Wraps LangGraph's ToolNode to check tool-level permissions
    before execution using RBACServiceABC.

    Attributes:
        context: ToolContext providing user identity for permission checks
    """

    def __init__(
        self,
        tools: list[BaseTool],
        context: ToolContext,
        *,
        handle_tool_errors: bool = True,
        messages_key: str = "messages",
    ) -> None:
        """Initialize RBACToolNode with context for permission checks.

        Args:
            tools: List of BaseTool instances to execute
            context: ToolContext with user identity for RBAC
            handle_tool_errors: Return errors as ToolMessage instead of raising
            messages_key: Key in state for messages list
        """
        super().__init__(
            tools,
            handle_tool_errors=handle_tool_errors,
            messages_key=messages_key,
        )
        self.context = context

    async def _check_tool_permission(self, tool_name: str) -> str | None:
        """Check if current user has permission to execute a tool.

        Context: Resolves required permissions from tool metadata
        and checks against RBACServiceABC.

        Args:
            tool_name: Name of the tool to check permissions for

        Returns:
            None if permitted, error message string if denied
        """
        rbac_service = get_rbac_service()

        # Find the tool and check its metadata
        for tool_obj in self.tools_by_name.values():
            if tool_obj.name == tool_name:
                metadata = getattr(tool_obj, "_tool_metadata", None)
                if metadata and metadata.permissions:
                    for perm in metadata.permissions:
                        if not rbac_service.has_permission(
                            self.context.user_role, perm
                        ):
                            return f"Permission denied: {perm} required"
        return None
```

**API Routes (backward-compatible with `RoleChecker`):**

The `@require_permission` decorator can also be used directly on service methods or route handlers as a second layer of defense, but `RoleChecker` remains the primary FastAPI dependency for API routes (no change needed).

**Cross-concern benefit:** The same `_required_permissions` metadata attached by `@require_permission` can be introspected by both `RBACToolNode` and `RoleChecker`, enabling permission discovery without the permission list being duplicated in decorator args.

#### `ToolContext` Update

```python
@dataclass
class ToolContext:
    """Execution context for AI tools with dependency injection.

    Context: Provides database session, user context, and service
    accessors for tool execution within LangGraph graph.

    Attributes:
        session: Async database session for queries
        user_id: Authenticated user ID
        user_role: User's RBAC role for permission checks
    """

    session: AsyncSession
    user_id: str
    user_role: str  # NEW: needed by RBACToolNode for permission checks
```

### Refactored `@ai_tool` Decorator

```python
# app/ai/tools/decorator.py

import logging
from collections.abc import Callable
from typing import TypeVar

from langchain_core.tools import BaseTool
from langchain_core.tools import tool as langchain_tool

from .types import ToolMetadata

logger = logging.getLogger(__name__)

T = TypeVar("T")


def ai_tool(
    name: str | None = None,
    description: str | None = None,
    permissions: list[str] | None = None,
    category: str | None = None,
) -> Callable[[Callable[..., T]], BaseTool]:
    """Decorator composing LangChain @tool with domain metadata.

    Context: Bridges LangChain's tool system with Backcast EVS
    domain concerns (RBAC metadata, categories). RBAC enforcement
    is handled by RBACToolNode, not this decorator.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to docstring first line)
        permissions: Required RBAC permissions (stored as metadata)
        category: Tool category for registry grouping

    Returns:
        LangChain BaseTool with attached ToolMetadata

    Example:
        >>> @ai_tool(permissions=["project-read"], category="projects")
        ... async def list_projects(
        ...     search: str | None = None,
        ...     context: Annotated[ToolContext, InjectedToolArg] = None,
        ... ) -> str:
        ...     \"\"\"List all projects with optional search.
        ...
        ...     Args:
        ...         search: Search term for project code or name
        ...     \"\"\"
        ...     ...
    """

    def decorator(func: Callable[..., T]) -> BaseTool:
        """Apply LangChain @tool and attach domain metadata.

        Args:
            func: The tool function to decorate

        Returns:
            LangChain BaseTool with domain metadata attached
        """
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or "No description"

        metadata = ToolMetadata(
            name=tool_name,
            description=tool_description,
            permissions=permissions or [],
            category=category,
            version="1.0.0",
        )

        # Apply LangChain's @tool — handles schema gen + docstring parsing
        lc_tool: BaseTool = langchain_tool(
            parse_docstring=True,
        )(func)

        # Override name/description if explicitly provided
        if name:
            lc_tool.name = name
        if description:
            lc_tool.description = description

        # Attach domain metadata for registry and RBACToolNode
        lc_tool._tool_metadata = metadata  # type: ignore[attr-defined]
        lc_tool._is_ai_tool = True  # type: ignore[attr-defined]

        return lc_tool

    return decorator  # type: ignore[return-value]
```

### Tool Function Example (Compliant with Coding Standards)

```python
# app/ai/tools/project_tools.py

import json
import logging
from typing import Annotated

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)


@ai_tool(
    name="list_projects",
    permissions=["project-read"],
    category="projects",
)
async def list_projects(
    search: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
    sort_field: str | None = None,
    sort_order: str = "asc",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> str:
    """List all projects with optional search, filtering, and pagination.

    Context: LangGraph tool used by the AI agent to search and retrieve
    a paginated projects list. Wraps ProjectService.get_projects().

    Args:
        search: Search term for project code or name
        status: Filter by status code (e.g., 'ACT', 'PLN')
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return (1-100)
        sort_field: Field to sort by (e.g., 'name', 'code', 'budget')
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        JSON string with projects list, total count, skip, and limit.
        Returns error key if context missing or service error occurs.

    Raises:
        None (errors caught and returned as JSON dict)
    """
    assert context is not None

    try:
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

        return json.dumps({
            "projects": [
                {
                    "id": str(p.project_id),
                    "code": p.code,
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "budget": float(p.budget) if p.budget else None,
                    "start_date": p.start_date.isoformat()
                    if p.start_date
                    else None,
                    "end_date": p.end_date.isoformat()
                    if p.end_date
                    else None,
                }
                for p in projects
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        })
    except Exception as e:
        logger.error(f"Error in list_projects: {e}")
        return json.dumps({"error": str(e)})
```

### Graph Integration (Updated Pipeline)

```python
# In agent_service.py — updated tool creation

from app.ai.tools.project_tools import list_projects, get_project

# Tools are already BaseTool instances from @ai_tool
tool_context = ToolContext(
    session=db,
    user_id=str(user_id),
    user_role=user.role,  # NEW: needed by RBACToolNode
)
tools = [list_projects, get_project]

# In graph.py — use RBACToolNode instead of ToolNode
from app.ai.tools.rbac_tool_node import RBACToolNode

tool_node = RBACToolNode(
    tools=tools,
    context=tool_context,
    handle_tool_errors=True,
)
```

### Files Changed

| File | Change |
|---|---|
| `app/core/rbac.py` | Add `require_permission` decorator |
| `app/ai/tools/decorator.py` | Refactor to compose with `@tool(parse_docstring=True)` |
| `app/ai/tools/types.py` | Add `user_role` to `ToolContext` |
| `app/ai/tools/rbac_tool_node.py` | **NEW** — `RBACToolNode` subclass |
| `app/ai/tools/project_tools.py` | Add `InjectedToolArg`, update docstrings |
| `app/ai/tools/__init__.py` | Deprecate Pydantic schemas, update `create_project_tools()` |
| `app/ai/tools/registry.py` | Simplify `as_langchain_tools()` |
| `app/ai/graph.py` | Use `RBACToolNode` instead of `ToolNode` |
| `app/ai/agent_service.py` | Pass `user_role` to `ToolContext` |

### Trade-offs

| Aspect | Assessment |
|---|---|
| **Pros** | • Eliminates dual tool system<br>• `RBACToolNode` centralizes permission checks (DRY)<br>• `@require_permission` reusable across AI + API<br>• Aligns with LangGraph 1.0 `InjectedToolArg`<br>• Auto parameter descriptions from docstrings |
| **Cons** | • Requires `ToolNode` subclass (maintenance on LangGraph upgrades)<br>• `user_role` must be threaded through to `ToolContext`<br>• Migration touches 9 files |
| **Complexity** | **Medium** — refactor with new `RBACToolNode` class |
| **Risk** | **Low** — tools already have Google-style docstrings, RBAC is additive |

---

## Verification Plan

### Automated Tests

```bash
# Run existing tool tests
cd backend && python -m pytest tests/integration/ai/tools/ -v

# Run existing RBAC tests
cd backend && python -m pytest tests/security/ai/test_tool_rbac.py -v

# Type check
cd backend && python -m mypy app/ai/tools/ app/core/rbac.py --strict

# Lint
cd backend && ruff check app/ai/tools/ app/core/rbac.py --fix
```

### New Tests to Add

1. **`test_docstring_parsing`**: Assert tool schemas include parameter descriptions from docstrings
2. **`test_injected_tool_arg_exclusion`**: Assert `context` is NOT in tool schema
3. **`test_rbac_tool_node_permission_denied`**: Assert `RBACToolNode` returns error `ToolMessage` when permission denied
4. **`test_rbac_tool_node_permission_granted`**: Assert `RBACToolNode` allows execution when permission granted
5. **`test_require_permission_decorator`**: Assert `@require_permission` raises `PermissionError` for unauthorized roles

---

## User Confirmed Choices

- **RBAC Strategy**: Option A — `RBACToolNode` subclass with `@require_permission` decorator
- **Scope**: Audit + standardize existing tool docstrings
- **Test Coverage**: Unit tests for decorator, `RBACToolNode`, and `@require_permission`
- **Priority**: Current sprint (E09-LANGGRAPH)

---

## References

**LangGraph 1.0:**
- `@tool(parse_docstring=True)` — [LangChain Tools Guide](https://docs.langchain.com/oss/python/langchain/tools)
- `InjectedToolArg` / `InjectedState` — excluded from LLM schema, injected by `ToolNode`
- `ToolNode` — parallel execution, error handling, state injection
- Tool best practices: clear names, docstrings, type hints, single responsibility

**Coding Standards:**
- [Backend Coding Standards](file:///home/nicola/dev/backcast_evs/docs/02-architecture/backend/coding-standards.md) — docstring format, MyPy strict, Ruff

**Code:**
- [decorator.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/decorator.py) — current custom decorator
- [\_\_init\_\_.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/__init__.py) — active Pydantic schema tools
- [rbac.py](file:///home/nicola/dev/backcast_evs/backend/app/core/rbac.py) — `RBACServiceABC`, `JsonRBACService`
- [auth.py](file:///home/nicola/dev/backcast_evs/backend/app/api/dependencies/auth.py) — `RoleChecker` dependency
- [graph.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/graph.py) — `ToolNode` + `StateGraph`
- [agent_service.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/agent_service.py) — production pipeline
- [crud_template.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/templates/crud_template.py) — 6 tool examples
- [analysis_template.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/templates/analysis_template.py) — 8 tool examples
- [change_order_template.py](file:///home/nicola/dev/backcast_evs/backend/app/ai/tools/templates/change_order_template.py) — 8 tool examples
