# AI Tool Development Guide

**Version:** 2.0.0
**Last Updated:** 2026-06-14
**Audience:** Backend Developers

> This guide supersedes the former `project-context-patterns.md` and
> `temporal-context-patterns.md`, whose verified content has been folded into the
> [Tool Context Patterns](#tool-context-patterns) section below. Those two docs
> have been removed.

---

## Overview

This guide explains how to create, test, and deploy AI tools for the Backcast
LangGraph agent. Tools are the primary way the AI agent interacts with the system:
they wrap existing service methods and provide a standardized, RBAC-enforced,
context-aware interface for LLM-powered conversations.

### What is an AI Tool?

An AI tool is an async function decorated with `@ai_tool` that:

- Wraps an existing service method (no business logic duplication)
- Declares RBAC permissions (enforced by `BackcastSecurityMiddleware`, not the decorator)
- Receives a `ToolContext` (database session, user, project/temporal scope) via
  dependency injection (`Annotated[ToolContext, InjectedToolArg]`)
- Returns structured data (dicts / Pydantic models) that the LLM can consume
- Is enumerated at runtime in `create_project_tools()` (and auto-discovered for
  the admin tool catalog via the `ToolRegistry`)

> [!NOTE]
> The `@ai_tool` decorator converts the function into a LangChain `BaseTool`
> instance. To execute the tool in Python code (like in tests), you must use
> `.ainvoke()` instead of calling it directly.

### Key Principles

1. **Wrap, Don't Duplicate**: Tools wrap existing service methods; they do not
   reimplement business logic.
2. **Security First**: Declare permissions on the decorator; the middleware
   enforces them. Never trust an `user_id` / `project_id` argument the LLM supplies.
3. **Context Injection**: Use `ToolContext` for database access, user identity,
   and project/temporal scope.
4. **Temporal Awareness**: For versioned entities, pass temporal parameters from
   `context` (`as_of`, `branch_name`, `branch_mode`) into the service layer's
   `get_as_of()` family of queries.
5. **Structured Returns**: Return dictionaries/Pydantic models the LLM can
   understand. Prefer selective fields over full ORM dumps.
6. **Error Handling**: Let the decorator's wrapper commit/rollback the task-local
   session and convert exceptions to `{"error": ...}`. Tools return error dicts
   for business-level misses (e.g. "not found").
7. **Observability**: Log temporal and project context for ALL tools that query
   data, and attach `_temporal_context` / `_project_context` metadata to results.

---

## Quick Start (5 Minutes)

### Step 1: Create Your Tool

Create a new file in `app/ai/tools/` or add to an existing file:

```python
# app/ai/tools/project_tools.py

from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import RiskLevel, ToolContext

@ai_tool(
    name="get_project",
    description="Get project details by ID.",
    permissions=["project-read"],
    category="projects",
    risk_level=RiskLevel.LOW,
)
async def get_project(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get detailed information about a specific project.

    Args:
        project_id: Project ID as UUID string
        context: Injected tool execution context

    Returns:
        Dictionary containing detailed project information, or an error.
    """
    log_temporal_context("get_project", context)

    try:
        from uuid import UUID

        from app.core.versioning.enums import BranchMode

        branch = context.branch_name or "main"
        branch_mode = (
            BranchMode.MERGED
            if context.branch_mode == "merged"
            else BranchMode.ISOLATED
        )

        # ProjectService is accessed via context (task-local session),
        # and uses get_as_of() for temporal queries.
        project = await context.project_service.get_as_of(
            entity_id=UUID(project_id),
            as_of=context.as_of,
            branch=branch,
            branch_mode=branch_mode,
        )

        if not project:
            return add_temporal_metadata(
                {"error": f"Project {project_id} not found"}, context
            )

        result = {
            "id": str(project.project_id),
            "name": project.name,
            "code": project.code,
            "status": project.status,
            "budget": float(project.budget) if project.budget else None,
        }
        return add_temporal_metadata(result, context)
    except ValueError:
        return add_temporal_metadata(
            {"error": f"Invalid project ID: {project_id}"}, context
        )
```

### Step 2: Register the Tool for Runtime Use

The LangGraph agent executes the tools listed in `create_project_tools()`
(`backend/app/ai/tools/__init__.py`). Add your tool to the appropriate
category block there:

```python
# backend/app/ai/tools/__init__.py
from app.ai.tools import project_tools

def create_project_tools(context: ToolContext) -> list[BaseTool]:
    ...
    tools: list[BaseTool] = [
        project_tools.list_projects,
        project_tools.get_project,
        # your tool here
    ]
    ...
```

### Step 3: Test Your Tool

```python
# tests/unit/ai/tools/test_project_tools.py

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ai.tools.project_tools import get_project
from app.ai.tools.types import ToolContext

@pytest.mark.asyncio
async def test_get_project_success():
    # Arrange — note: context.session (property), not context.db_session
    context = MagicMock(spec=ToolContext)
    context.session = MagicMock()
    context.user_id = "test-user"
    context.as_of = None
    context.branch_name = "main"
    context.branch_mode = "merged"

    # Act
    result = await get_project.ainvoke({
        "project_id": "123e4567-e89b-12d3-a456-426614174000",
        "context": context,
    })

    # Assert — middleware enforces RBAC, not the tool itself
    assert "error" in result  # or your success assertions
```

```bash
uv run pytest tests/unit/ai/tools/test_project_tools.py -v
```

---

## Tool Anatomy

### The @ai_tool Decorator

The `@ai_tool` decorator (`backend/app/ai/tools/decorator.py`):

1. **Wraps with context + session lifecycle**: injects the `ToolContext`,
   commits on success, rolls back on error, and converts raised exceptions to
   `{"error": str(e)}`.
2. **Attaches metadata**: stores a `ToolMetadata` on `tool._tool_metadata`
   (name, description, permissions, category, version, risk_level) and sets
   `tool._is_ai_tool = True` for registry discovery.
3. **Builds the LangChain tool**: calls `tool(parse_docstring=False, ...)`
   (see [Decorator Parameters](#decorator-parameters) below) and returns a
   `BaseTool`.
4. Does **NOT** enforce RBAC itself. It only attaches permission metadata,
   which `BackcastSecurityMiddleware` reads at execution time (see
   [Security: RBAC enforcement](#1-rbac-enforcement-lives-in-the-middleware)).

### Decorator Parameters

```python
from app.ai.tools.types import RiskLevel

@ai_tool(
    name="tool_name",                       # Optional: defaults to function name
    description="LLM-facing description",   # Optional: defaults to docstring
    permissions=["perm1", "perm2"],         # Optional: RBAC perms (default [])
    category="category_name",               # Optional: for the admin catalog
    risk_level=RiskLevel.LOW,               # Optional: LOW/HIGH/CRITICAL (default HIGH)
)
```

`risk_level` controls which execution modes may call the tool
(`safe` = LOW only; `standard` = LOW+HIGH; `expert` = all). Every real tool in
this codebase specifies `risk_level` explicitly. **There is no `MEDIUM` value**;
the `RiskLevel` enum is exactly `LOW`, `HIGH`, `CRITICAL`
(`backend/app/ai/tools/types.py`). The default when omitted is `HIGH`
(`decorator.py`).

> [!IMPORTANT]
> **Docstring parsing is OFF.** The decorator calls LangChain's
> `tool(parse_docstring=False, ...)` (`decorator.py`). The LLM-facing
> description comes **only** from the `description=` argument (or the function
> docstring if `description` is omitted). The Google-style `Args:` sections are
> developer documentation only — they are **not** sent to the LLM. This keeps
> token usage down.

### Function Signature

```python
async def tool_function(
    param1: type1,         # Tool parameters (what the LLM provides)
    param2: type2,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:       # Return structured data
    """Developer-facing docstring. Args sections are NOT sent to the LLM."""
    ...
```

- `context` must be annotated with `Annotated[ToolContext, InjectedToolArg]` so
  LangChain hides it from the tool schema (the LLM cannot see or set it).
- Access the DB via `context.session` (a task-local `AsyncSession`), not any
  `db_session` attribute. See [Tool Context Patterns](#tool-context-patterns).

---

## Tool Discovery and Registration (Two Paths)

Tools reach the system through **two distinct paths**. Do not conflate them:

### (a) Runtime construction — `create_project_tools()`

The list of tools the LangGraph agent actually executes at runtime is
**manually enumerated** in `create_project_tools()` in
`backend/app/ai/tools/__init__.py`. This function imports each tool module and
assembles a `list[BaseTool]` grouped by category (`projects`, `cost-management`,
`work-tracking`, `change-orders`, `analysis`, `users`, ...). Tools are cached as
singletons after the first call. The `ToolContext` argument is accepted for
backward compatibility; tools retrieve their context at runtime via context
variables.

**To make a tool available to the agent, you must add it here.** Merely
decorating a function with `@ai_tool` does not expose it to the agent.

### (b) Auto-discovery catalog — `ToolRegistry` / admin UI

The `ToolRegistry` (`backend/app/ai/tools/registry.py`) provides auto-discovery
of `@ai_tool`-decorated functions via `discover_and_register(module_path)`,
which imports a module and registers every attribute with `_is_ai_tool == True`.

This path is **not dead code** — it powers the admin tool catalog. The
`GET /api/v1/ai/config/tools` endpoint
(`backend/app/api/routes/ai_config.py`, permission `ai-config-read`) calls
`registry.discover_and_register()` for ~19 modules and then
`get_all_tools()` to enumerate the catalog shown in the configuration UI.

Key registry functions (`registry.py`):

- `get_registry()` — global singleton `ToolRegistry`.
- `registry.discover_and_register(module_path)` — import + register a module's tools.
- `get_all_tools()` — returns `list[ToolMetadata]` (**not** `list[BaseTool]`).
- `registry.get_by_permission(...)` / `get_by_category(...)` — filtering helpers.
- `registry.as_langchain_tools(context, permissions=None)` — convert to `BaseTool`.

> [!NOTE]
> `get_all_tools()` returns **`list[ToolMetadata]`**, not `list[BaseTool]`.
> The decorator produces `BaseTool` instances directly; the registry stores
> function + metadata pairs.

---

## Common Patterns

### Pattern 1: List/Search with Pagination

`list_projects` (`backend/app/ai/tools/project_tools.py`) is the canonical
paginated read tool. Note the shape:

```python
@ai_tool(
    name="list_projects",
    description=(
        "List projects with search, filter, and pagination. "
        "IMPORTANT: results are paginated — ... check 'total' and 'has_more' ..."
    ),
    permissions=["project-read"],
    category="projects",
    risk_level=RiskLevel.LOW,
)
async def list_projects(
    search: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int | None = None,
    sort_field: str | None = None,
    sort_order: str = "asc",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    ...
```

It returns a **dict** (not a `list[dict]`):

```python
{
    "projects": [ ... ],     # one page of project dicts
    "total": <int>,          # count after filtering
    "page": <int>,
    "limit": <int>,
    "page_count": <int>,
    "has_more": <bool>,
    "_project_context": { "project_id": ... },
    "_temporal_context": { "as_of": ..., "branch_name": ..., "branch_mode": ... },
}
```

It auto-scopes to `context.project_id` after verifying RBAC access
(`project_tools.py`).

### Pattern 2: Get Single Versioned Entity (temporal)

For a single versioned entity, use the service's `get_as_of()` with temporal
params from context — there is no `ProjectService.get_project()`:

```python
from uuid import UUID
from app.core.versioning.enums import BranchMode

branch = context.branch_name or "main"
branch_mode = (
    BranchMode.MERGED if context.branch_mode == "merged" else BranchMode.ISOLATED
)

project = await context.project_service.get_as_of(
    entity_id=UUID(project_id),
    as_of=context.as_of,
    branch=branch,
    branch_mode=branch_mode,
)
```

`ProjectService.get_as_of(entity_id, as_of, branch, branch_mode)` lives in
`backend/app/services/project.py` and returns `Project | None`.

### Pattern 3: Create Item (CRUD)

Wrap a create schema + service method. Temporal params (branch, etc.) come from
context, not from the LLM:

```python
@ai_tool(
    name="create_project",
    description="Create a new project.",
    permissions=["project-create"],
    category="projects",
    risk_level=RiskLevel.HIGH,
)
async def create_project(
    name: str,
    code: str,
    status: str = "PLN",
    budget: float | None = None,
    description: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    ...
```

See `backend/app/ai/tools/templates/project_template.py` for the full
implementation.

### Pattern 4: Analysis / EVM

EVM metrics come from `EVMService.calculate_evm_metrics(...)` in
`app.services.evm_service` (note: `evm_service`, **not** `app.services.evm`).
The method is **not** `calculate_metrics(project_id)`; it is per work package
and time-aware:

```python
from app.services.evm_service import EVMService
from app.core.versioning.enums import BranchMode

service = EVMService(context.session)
metrics = await service.calculate_evm_metrics(
    work_package_id=UUID(work_package_id),
    control_date=as_of,            # time-travel anchor
    branch=branch,
    branch_mode=BranchMode.MERGED,  # or ISOLATED
)
# metrics is an EVMMetricsRead Pydantic model (BAC, PV, AC, EV, CV, SV, CPI, SPI, ...)
```

The `analysis_template` / `advanced_analysis_template` modules wrap these calls
for the agent (see [Templates](#templates)).

---

## Best Practices

### 1. RBAC enforcement lives in the middleware

The `@ai_tool` decorator **attaches** `permissions` to `tool._tool_metadata`; it
does **not** check them. `BackcastSecurityMiddleware`
(`backend/app/ai/middleware/backcast_security.py`) reads
`tool._tool_metadata.permissions` and enforces every permission before the tool
runs (per-permission project-aware checks). The middleware also gates tools by
`risk_level` vs. the session's `execution_mode`.

✅ **DO:** Declare exact permissions on the decorator.

```python
@ai_tool(permissions=["project-read", "evm-read"], risk_level=RiskLevel.LOW)
```

❌ **DON'T:** Re-implement permission checks inside the tool body, or use
overly-broad permissions like `["admin"]`.

### 2. Service Wrapping

✅ **DO:** Wrap existing service methods via `context.session` / service accessors.

```python
project = await context.project_service.get_as_of(
    entity_id=UUID(project_id), as_of=context.as_of, ...
)
```

❌ **DON'T:** Duplicate business logic, or hit the DB directly bypassing services.

### 3. Context Access

✅ **DO:** Use `context.session` (task-local), `context.user_id`, and temporal
fields from context.

❌ **DON'T:** Reference `context.db_session` — it does not exist. Don't accept
`user_id` / `project_id` as LLM-provided parameters.

### 4. Error Handling

✅ **DO:** Return business-level error dicts (e.g. "not found", "invalid UUID"),
and let the decorator's wrapper convert raised exceptions to `{"error": ...}`
and manage the session.

❌ **DON'T:** Wrap tool bodies in `try/except` that swallows exceptions into
`{"error": str(e)}` — the decorator already does this and also handles rollback.

### 5. Type Hints

✅ **DO:** Use precise type hints; annotate `context` with `InjectedToolArg`.

❌ **DON'T:** Use `Any` / untyped params.

---

## Tool Context Patterns

This section consolidates the verified content from the former
`project-context-patterns.md` and `temporal-context-patterns.md`.

### ToolContext is a mutable, project-scoped, injection-hidden dataclass

`ToolContext` (`backend/app/ai/tools/types.py`) is a **plain `@dataclass`
without `frozen=True`** — it is mutable. It carries:

- `session` — a property returning a **task-local** `AsyncSession`
  (`async_scoped_session` keyed on the current asyncio task). The original
  WebSocket-level session is stored separately as `_root_session`.
- `user_id`, `user_role`, `execution_mode`
- **Project scope**: `project_id` (set from the URL by default, switchable
  mid-session via the RBAC-gated `set_project_context` tool — see below), `branch_id`
- **Temporal scope** (LLM-mutable): `as_of`, `branch_name`, `branch_mode`
- `project_service` — a `ProjectService(self.session)` accessor property
- `_permission_cache` (LRU), `_event_bus`, `_stop_event`

It is injected via `Annotated[ToolContext, InjectedToolArg]`, which excludes it
from the tool schema so the LLM cannot see or manipulate scope directly.

> [!IMPORTANT]
> **Mutable scope, but RBAC-gated.** **Project scope** is set from the URL by
> default, but it **can be switched mid-session** by the LLM via the
> RBAC-gated `set_project_context` tool (`backend/app/ai/tools/context_tools.py`),
> which mutates `context.project_id` in place and **persists** the new scope to
> the `AIConversationSession.project_id` row so it survives across turns. The
> switch is rejected unless the user already has access to the target project
> (verified via `get_accessible_projects`), so it grants no access the user did
> not already have. **Temporal scope is LLM-mutable** via
> `set_temporal_context`, which mutates `context.as_of`, `context.branch_name`,
> and `context.branch_mode` in place and publishes a `temporal_context_change`
> event. The old "ToolContext is immutable / temporal context is read-only"
> thesis is **false** — `ToolContext` is a plain mutable dataclass, and the LLM
> *can* shift both the project scope and the temporal view through tools.

### Project context

- **Frontend → backend**: the frontend derives `project_id` from the URL
  (`/projects/:projectId/chat`) and sends it in the `WSChatRequest` (see
  [WebSocket schema](#websocket-schema)).
- **`list_projects` auto-scopes**: after resolving the user's accessible projects
  via the unified RBAC service, if `context.project_id` is set, the tool filters
  to that project only — or to an empty list if the user lacks access
  (`project_tools.py`).
- **`get_project_context`** (`backend/app/ai/tools/context_tools.py`) is the
  read-only tool the LLM uses to inspect project scope (name, code, user roles).
  It never mutates `project_id`.
- **`set_project_context`** (`backend/app/ai/tools/context_tools.py`,
  ~lines 190-270) is the **mutable** project-scope tool. Given a `project_id`
  (e.g. from `list_projects`), it (1) RBAC-checks the target via
  `unified_service.get_accessible_projects(user_id)` — rejected if the user
  cannot already access it, (2) confirms the project exists, then (3) mutates
  the shared `ToolContext` in place (resetting `branch_name`/`branch_mode` to
  `main`/`merged`) and **persists** the new `project_id` to the
  `AIConversationSession` row (via `_apply_session_project_switch`, ~lines
  273-335) so the scope survives to the next turn, and publishes a
  `project_context_change` event. All subsequent tool calls in the session see
  the new project scope. It grants no access the user did not already have via
  `list_projects` / `get_project`.
- **Security argument**: `project_id` rides on the injected `ToolContext`, and
  every project-scoped tool auto-scopes after an RBAC access check
  (`get_accessible_projects`). The only tool that moves `context.project_id`,
  `set_project_context`, re-runs that same access check before switching, so a
  prompt-injection attempt cannot land the LLM in a project the user cannot
  already see — it can only switch between projects the user already has access
  to. The LLM may ask; the tool layer enforces.

### Temporal context

- **`get_temporal_context`** (`backend/app/ai/tools/temporal_tools.py`) is
  read-only: it reports `as_of`, `current_date`, `branch_name`, `branch_mode`.
- **`set_temporal_context`** (`temporal_tools.py`) is the **mutable** tool: given
  `as_of` / `branch_name` / `branch_mode`, it validates them (ISO datetime,
  valid branch against `BranchService.list_branches_as_of`, mode ∈
  {merged, isolated}), then **mutates the shared `ToolContext` in place** and
  publishes an `AgentEvent` of type `temporal_context_change` on the event bus.
  All subsequent tool calls in the session see the new temporal view.
- **`list_branches`** (`temporal_tools.py`) enumerates branches for the current
  project (used before switching).
- **Service-layer `get_as_of()` query patterns**: for versioned entities, always
  call `Service.get_as_of(entity_id=..., as_of=..., branch=..., branch_mode=...)`
  (e.g. `ProjectService.get_as_of`). Never use non-temporal `get_list()` /
  `get_by_id()` for versioned entities. Non-versioned entities (`SimpleEntityBase`
  — Users, AI Configs) ignore temporal params.

### System prompt DOES inject temporal context (refuted stale thesis)

`AgentService._build_system_prompt(base_prompt, project_id, as_of, branch_name,
branch_mode, context)` (`backend/app/ai/agent_service.py`) takes a
`context: dict | None` (a `SessionContext`) that drives `general` / `project` /
`wbe` / `cost_element` / `work_package` scoping, and **appends a
`[TEMPORAL CONTEXT]` section** to the prompt when `branch_name != "main"` or
when `as_of` is set. The old "system prompt excludes temporal context" thesis is
**false**. The prompt also tells the LLM it can change the temporal view via
`set_temporal_context`. Enforcement still happens at the tool layer; the prompt
section is for LLM awareness.

### WebSocket schema

The frontend `WSChatRequest` (`frontend/src/features/ai/chat/types.ts`) is:

```typescript
export interface WSChatRequest {
  type: "chat";
  message: string;
  session_id: string | null;        // required (null for new session)
  assistant_config_id: string;      // required
  title?: string;
  execution_mode: ExecutionMode;    // required: safe | standard | expert
  as_of?: string | null;            // ISO timestamp or null
  branch_name?: string;             // e.g. "main", "BR-001"
  branch_mode?: "merged" | "isolated";
  project_id?: string;              // from URL, optional
  context?: SessionContext;         // { type, id, project_id, name }
  attachments?: FileAttachment[];
  images?: string[];
}
```

> [!NOTE]
> There is **no `branch_id` field** on `WSChatRequest`. Branch context is
> conveyed via `branch_name` (+ `branch_mode`), not a UUID.

### RBAC helpers (unified)

The real RBAC API is the **unified** service in
`backend/app/core/rbac_unified.py`, not the older `get_rbac_service()`:

```python
from app.core.rbac_unified import (
    get_unified_rbac_service,
    set_unified_rbac_session,
)

set_unified_rbac_session(context.session)          # inject the task-local session
unified_service = get_unified_rbac_service()

accessible = await unified_service.get_accessible_projects(user_id=user_uuid)
roles       = await unified_service.get_project_roles(
    user_id=user_uuid, project_id=project_uuid
)  # returns a LIST (possibly empty)
```

`get_project_roles(...)` returns a **list** (`user_roles`), not a single string.
`context_tools.py` and `project_tools.py` both use this API.

### Logging and metadata helpers

`backend/app/ai/tools/temporal_logging.py` provides four helpers used across
the tool suite:

- `log_temporal_context(tool_name, context)` — logs `[TEMPORAL_CONTEXT] ...`.
- `add_temporal_metadata(result, context)` — adds a `_temporal_context` key.
- `log_project_context(tool_name, context)` — logs `[PROJECT_CONTEXT] ...`.
- `add_project_metadata(result, context)` — adds a `_project_context` key.

Rule of thumb: if a tool queries the database, call both `log_*` helpers at
entry and wrap the result (and any error dict) with the corresponding
`add_*_metadata` helpers.

### Migration checklist (per tool)

When adding or migrating a tool:

- [ ] Import `RiskLevel` and set `risk_level=` explicitly.
- [ ] Annotate `context` with `Annotated[ToolContext, InjectedToolArg]`.
- [ ] Access the DB via `context.session` / `context.project_service` — never
      `context.db_session`.
- [ ] Call `log_temporal_context` / `log_project_context` at entry.
- [ ] Wrap results **and** error dicts with `add_temporal_metadata` /
      `add_project_metadata`.
- [ ] For versioned entities, use `Service.get_as_of(...)` with temporal params
      from context.
- [ ] Do **not** put `user_id` / `project_id` in the tool signature.
- [ ] Declare exact `permissions=`; rely on the middleware to enforce.
- [ ] Add the tool to `create_project_tools()` in `backend/app/ai/tools/__init__.py`.
- [ ] If the tool mutates `context.project_id` (like `set_project_context`):
      re-run an RBAC access check (`get_accessible_projects`) on the target
      before switching, and persist the new scope to the `AIConversationSession`
      row (see `_apply_session_project_switch` in `context_tools.py`) so it
      survives across turns.

---

## Testing Strategies

### Unit Tests

Mock `ToolContext` (spec it) and the service accessors. The middleware enforces
RBAC, so unit tests generally assert on returned shape, not on permission checks:

```python
@pytest.mark.asyncio
async def test_list_projects_returns_paginated_dict():
    context = MagicMock(spec=ToolContext)
    context.session = MagicMock()
    context.user_id = str(uuid4())
    context.as_of = None
    context.branch_name = "main"
    context.branch_mode = "merged"
    context.project_id = None

    result = await list_projects.ainvoke({"context": context})

    assert isinstance(result, dict)
    for key in ("projects", "total", "page", "limit", "page_count", "has_more"):
        assert key in result
```

### Integration Tests

Use a real DB session and exercise temporal parameters (create versions, then
query with different `as_of` / branch values).

### Async Fixture Pattern (pytest-asyncio)

In pytest-asyncio **strict** mode, async fixtures must use `@pytest_asyncio.fixture`
(not `@pytest.fixture`):

```python
import pytest_asyncio

@pytest_asyncio.fixture
async def test_forecast(test_db):
    forecast = await ForecastService(test_db).create_forecast(...)
    return forecast
```

> [!IMPORTANT]
> Using `@pytest.fixture` (non-async) for a fixture that async tests depend on
> fails strict mode with "requested an async fixture". Always use
> `@pytest_asyncio.fixture` for async fixtures.

### Permission metadata in tests

Permissions live on `_tool_metadata`, not as a top-level attribute:

```python
# ✅ correct
assert "forecast-read" in get_forecast._tool_metadata.permissions

# ❌ wrong — attribute does not exist at top level
# assert "forecast-read" in get_forecast.permissions
```

---

## Templates

Ready-to-use tool template modules live in `backend/app/ai/tools/templates/`.
Each module groups related CRUD operations. The current templates are:

| Template module | Tools |
| --- | --- |
| `project_template` | Project + WBS Element CRUD (`create_project`, `update_project`, `delete_project`, `batch_create_projects`, `find_wbs_elements`, `create_wbs_element`, ...) |
| `work_package_template` | Work Package CRUD + budget status |
| `cost_element_template` | Cost Element + Cost Element Type CRUD |
| `cost_event_template` | Cost Event CRUD + COQ |
| `cost_event_type_template` | Cost Event Type CRUD |
| `control_account_template` | Control Account CRUD + budget |
| `forecast_cost_progress_template` | Forecast + Cost Registration + Progress Entry |
| `change_order_template` | Change order workflow (create, submit, approve, reject, analyze, delete, batch) |
| `analysis_template` | Project analysis (`get_project_analysis`) |
| `advanced_analysis_template` | Project forecast (`get_project_forecast`) |
| `user_management_template` | User + Organizational Unit management |
| `diagram_template` | Diagram generation |

> [!NOTE]
> There is **no** `crud_template.py`. Copy the closest existing template module
> and modify it for your use case.

---

## Performance Considerations

### Pagination

Use `page`/`limit` pagination and return a dict envelope with `total`,
`page_count`, and `has_more` (see Pattern 1). Tell the LLM in the `description`
that results are paginated and that it must page forward.

### Selective Fields

Return only the fields the LLM needs:

```python
# ✅ selective
return {
    "id": str(project.project_id),
    "name": project.name,
    "status": project.status,
}

# ❌ bloated
return project.to_dict()  # all fields
```

### Task-local sessions

`context.session` returns a per-task `AsyncSession` via
`async_scoped_session`, so concurrent tool executions do not collide on a shared
session. Do not bypass it by stashing a session reference in module state.

---

## Security Considerations

### 1. RBAC enforcement lives in the middleware

`BackcastSecurityMiddleware` reads `tool._tool_metadata.permissions` and enforces
all of them before each tool call (`backend/app/ai/middleware/backcast_security.py`).
It also gates tools by `risk_level` vs `execution_mode`.

### 2. Project scope is RBAC-gated, temporal scope is tool-mutable

Project scope (`context.project_id`) is set from the URL by default, but it
**can be switched mid-session** by the RBAC-gated `set_project_context` tool
(`backend/app/ai/tools/context_tools.py`). The switch re-runs
`get_accessible_projects` and is rejected unless the user already has access to
the target project, so it grants no new access — prompt-injection cannot move
the LLM into a project the user could not already see. The new scope is
persisted to the `AIConversationSession` row and survives across turns.
Temporal scope is independently LLM-mutable via `set_temporal_context`
(validated, and it only changes the *viewing* context).

### 3. Never trust LLM-supplied identity

Do not put `user_id` or `project_id` in tool signatures. Always source them from
`context`. Validate UUIDs before use.

---

## Troubleshooting

### Tool not available to the agent

**Cause:** the tool is decorated but not listed in `create_project_tools()`.
**Fix:** add it to the appropriate category block in
`backend/app/ai/tools/__init__.py`.

### Tool not in the admin config catalog

**Cause:** its module is not passed to `registry.discover_and_register()` in the
`GET /api/v1/ai/config/tools` endpoint
(`backend/app/api/routes/ai_config.py`).
**Fix:** add a `registry.discover_and_register("app.ai.tools.your_module")` call
there.

### "Tool context not provided"

**Cause:** `context` is missing the `Annotated[ToolContext, InjectedToolArg]`
annotation, or it is not the last parameter.
**Fix:**

```python
# ✅ correct
async def tool(param1: str, context: Annotated[ToolContext, InjectedToolArg] = None): ...

# ❌ wrong
async def tool(context: ToolContext, param1: str): ...          # wrong position / no InjectedToolArg
async def tool(param1: str, context: ToolContext): ...
```

### Async fixture errors (pytest-asyncio)

**Cause:** non-async `@pytest.fixture` used for an async fixture.
**Fix:** use `@pytest_asyncio.fixture` (see [Testing Strategies](#testing-strategies)).

### Permission assertions fail

**Cause:** test reads `tool.permissions` instead of `tool._tool_metadata.permissions`.
**Fix:** assert against `tool._tool_metadata.permissions`.

---

## References

- [Agent Common Concepts](./agent-common-concepts.md)
- [Supervisor Orchestrator](./supervisor-orchestrator.md)
- [Tool Development Guide (this document)](./tool-development-guide.md)
- `backend/app/ai/tools/decorator.py` — `@ai_tool`
- `backend/app/ai/tools/types.py` — `ToolContext`, `ToolMetadata`, `RiskLevel`
- `backend/app/ai/tools/registry.py` — `ToolRegistry`, `get_all_tools`
- `backend/app/ai/tools/__init__.py` — `create_project_tools` (runtime enumeration)
- `backend/app/api/routes/ai_config.py` — admin tool catalog endpoint
- `backend/app/ai/middleware/backcast_security.py` — RBAC + risk enforcement
- `backend/app/services/project.py` — `ProjectService.get_as_of`
- `backend/app/services/evm_service.py` — `EVMService.calculate_evm_metrics`
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

---

**Questions?** Ask in #backend-dev channel or create an issue.
