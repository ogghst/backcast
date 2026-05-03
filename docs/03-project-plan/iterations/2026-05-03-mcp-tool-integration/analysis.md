# Analysis: MCP Tool Integration for AI Agent System

**Date:** 2026-05-03
**Scope:** AI agent tool extensibility via MCP (Model Context Protocol)
**Related Epic:** E09 — AI Integration
**Status:** Research & Analysis

---

## Executive Summary

The Backcast AI agents currently have access only to domain-specific tools (project CRUD, EVM analysis, change orders, etc.) defined with the `@ai_tool` decorator. MCP (Model Context Protocol) provides a standard for exposing external tools (filesystem, databases, web APIs, custom services) that agents can discover and use dynamically. This analysis evaluates integrating MCP tools into the existing Backcast tool pipeline using `langchain-mcp-adapters`.

**Recommendation:** Add MCP tool support via database-configured MCP servers with admin UI. Use `langchain-mcp-adapters` to convert MCP tools into LangChain `BaseTool` instances that merge into the existing tool pipeline alongside native Backcast tools. A singleton `MCPClientManager` handles connection lifecycle, tool caching, and graceful degradation — requiring only a 3-line addition to `create_project_tools()`.

---

## Current Architecture: Native Tool Pipeline

### Tool Definition & Registration

```
@ai_tool decorator → ToolMetadata → ToolRegistry → create_project_tools() → bind_tools()
```

| Component | File | Role |
|-----------|------|------|
| `@ai_tool` decorator | `backend/app/ai/tools/decorator.py` | Converts async functions to LangChain `BaseTool` with RBAC metadata |
| `ToolRegistry` | `backend/app/ai/tools/registry.py` | Auto-discovers and manages registered tools |
| `create_project_tools()` | `backend/app/ai/tools/__init__.py` | Creates cached tool list, filters by mode + role |
| `filter_tools_for_context()` | `backend/app/ai/subagent_compiler.py` | Applies execution-mode + RBAC filtering per subagent |
| `RBACToolNode` | `backend/app/ai/tools/rbac_tool_node.py` | Runtime permission check on tool execution |
| `InterruptNode` | `backend/app/ai/tools/interrupt_node.py` | Human-in-the-loop approval for HIGH/CRITICAL tools |

### Tool Filtering Pipeline

Tools are filtered in a layered pipeline:

1. **Execution Mode**: SAFE → LOW only, STANDARD → LOW+HIGH, EXPERT → all
2. **Assistant Role**: Ceiling from assistant config
3. **User Role**: Actual user permissions
4. **Subagent Whitelist**: Domain specialization per subagent
5. **Runtime**: `RBACToolNode` checks permissions at execution time
6. **Approval**: `InterruptNode` for HIGH/CRITICAL risk operations

### Key Constraint

`create_project_tools()` is **synchronous** and uses global caching (`_cached_tools`). All callers (`subagent_compiler.py`, `graph.py`) expect a `list[BaseTool]` return. Any MCP integration must work within this constraint.

### Agent Orchestration

The supervisor orchestrator (`backend/app/ai/supervisor_orchestrator.py`) compiles subagents with filtered tools. The briefing-room pattern dispatches tasks to specialists. MCP tools must be available at the same compilation stage as native tools.

---

## Proposed Architecture: MCP Tool Integration

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Admin UI                                 │
│  Configure MCP Servers (stdio / SSE / streamable-http)      │
└────────────────────────┬────────────────────────────────────┘
                         │ CRUD + test connection
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  MCPServer (DB)  ←→  MCPServerService (CRUD + encryption)   │
└────────────────────────┬────────────────────────────────────┘
                         │ initialize / refresh
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  MCPClientManager (singleton)                                │
│  - Connects to MCP servers via langchain-mcp-adapters        │
│  - Caches discovered tools as list[BaseTool]                 │
│  - get_all_tools() → sync access from create_project_tools() │
│  - Graceful degradation on server failure                    │
└────────────────────────┬────────────────────────────────────┘
                         │ append MCP tools
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  create_project_tools()                                      │
│  native_tools (cached) + mcp_tools (from client manager)     │
└────────────────────────┬────────────────────────────────────┘
                         │ filter_tools_for_context()
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent / Subagent (LangGraph)                                │
│  Same RBAC, risk-level, and approval pipeline as today       │
└─────────────────────────────────────────────────────────────┘
```

### Core Design Decision: Sync Cache Pattern

**Problem:** `create_project_tools()` is synchronous. MCP tool loading requires async I/O (network/subprocess connections).

**Solution:** `MCPClientManager` loads tools **asynchronously during startup** (in `main.py` lifespan) and stores them in a sync-accessible `list[BaseTool]` cache. When `create_project_tools()` runs, it calls `get_all_tools()` (sync dict lookup) and appends MCP tools to the native tool list.

**Why not make `create_project_tools` async?** It would cascade changes to `subagent_compiler.py`, both orchestrators, `graph.py`, and all their callers. The sync cache approach requires zero signature changes to existing code.

### MCP Tool Metadata

Each MCP tool gets `_tool_metadata` attached for pipeline compatibility:

```python
ToolMetadata(
    name=tool.name,
    description=tool.description,
    permissions=[],          # No Backcast RBAC — always allowed
    category=f"mcp:{server_name}",
    risk_level=RiskLevel.HIGH,  # Conservative — blocked in SAFE mode
)
```

This ensures MCP tools:
- Pass through `filter_tools_by_role()` (empty permissions = always allowed)
- Are blocked in SAFE execution mode (HIGH risk level)
- Are identifiable by category prefix `mcp:` for specialist filtering

### MCP Client Manager

```python
class MCPClientManager:
    """Singleton managing MCP server connections and tool discovery."""

    _tools: list[BaseTool]  # Sync-accessible cache

    # Async lifecycle (called from FastAPI lifespan)
    async def initialize(session: AsyncSession) -> None
    async def refresh_server(server_name: str, session: AsyncSession) -> None
    async def remove_server(server_name: str) -> None
    async def shutdown() -> None
    async def test_connection(server_config: dict) -> list[Tool]

    # Sync access (called from create_project_tools)
    def get_all_tools() -> list[BaseTool]
```

**Graceful degradation:** Unreachable servers are logged and skipped. The agent gets whatever tools are available from connected servers. No exceptions propagate to the tool pipeline.

**Connection refresh:** After admin creates/updates/deletes an MCP server via API, the route notifies `MCPClientManager.refresh_server()` to reconnect.

---

## Option Comparison

### Option 1: Database + Admin UI (Recommended)

**Architecture:**
- `MCPServer` table stores server configurations (transport, command, url, headers, env)
- Admin CRUD API at `/api/v1/mcp/servers`
- Admin UI tab in existing AI Settings page
- `MCPClientManager` loads from DB at startup

**UX Design:**
- New "MCP Servers" tab alongside Providers/Models/Assistants in admin
- Modal form with conditional fields (command/args for stdio, url/headers for HTTP/SSE)
- "Test Connection" button validates configuration
- Tool discovery view shows available tools per server

**Trade-offs:**

| Aspect          | Assessment                                               |
| --------------- | -------------------------------------------------------- |
| Pros            | Consistent with AI provider pattern, encrypted storage, audit trail, dynamic config |
| Cons            | Database migration needed, more implementation effort    |
| Complexity      | Medium                                                   |
| Maintainability | Good — follows established patterns                      |
| Performance     | One-time async load at startup, sync cache for runtime   |

### Option 2: JSON Config File

**Architecture:**
- `backend/mcp_servers.json` stores server configurations
- `MCPClientManager` reads file at startup
- No admin API or UI — file edits + server restart

**Trade-offs:**

| Aspect          | Assessment                                               |
| --------------- | -------------------------------------------------------- |
| Pros            | Fastest to implement, no DB changes, version-controlled  |
| Cons            | No runtime reconfiguration, no encryption, no audit trail, requires restart |
| Complexity      | Low                                                      |
| Maintainability | Fair — config drift, no validation                       |
| Performance     | Same as Option 1                                         |

### Option 3: Environment Variables

**Architecture:**
- MCP servers defined via environment variables (JSON-encoded)
- Limited to simple configurations

**Trade-offs:**

| Aspect          | Assessment                                               |
| --------------- | -------------------------------------------------------- |
| Pros            | Simplest, standard 12-factor pattern                     |
| Cons            | No multi-server support, no structured config, no UI     |
| Complexity      | Low                                                      |
| Maintainability | Poor — hard to manage complex configs                    |
| Performance     | Same as Option 1                                         |

---

## Comparison Summary

| Criteria           | Option 1 (DB + Admin) | Option 2 (Config File) | Option 3 (Env Vars) |
| ------------------ | --------------------- | ---------------------- | ------------------- |
| Development Effort | Medium (8-10 files)   | Low (3-4 files)        | Lowest (2-3 files)  |
| UX Quality         | Full admin UI         | File editing only      | Manual env setup    |
| Flexibility        | Runtime reconfig      | Restart required       | Restart required    |
| Security           | Encrypted storage     | Plain text             | Plain text          |
| Best For           | Production use        | Quick prototyping      | Simple single-server|

---

## Recommendation

**Option 1: Database + Admin UI** — consistent with the existing AI provider management pattern (E09-U01/U02). Users already manage providers and assistants through the admin UI. MCP server management should follow the same UX.

---

## Implementation Details

### Database Model

**New file:** `backend/app/models/domain/mcp_server.py`

```
MCPServer(SimpleEntityBase):
    __tablename__ = "mcp_servers"

    name: str              # Unique human-readable name
    transport: str         # "stdio" | "sse" | "streamable-http"
    command: str | None    # stdio: executable command
    args: list | None      # stdio: JSONB array of arguments
    url: str | None        # sse/http: server URL
    headers: dict | None   # sse/http: JSONB (sensitive values encrypted)
    env: dict | None       # stdio: JSONB env vars (sensitive values encrypted)
    is_active: bool        # Enable/disable without deleting
    tool_name_prefix: bool # Prefix tool names with server name
```

Follows `AIProvider` model pattern (`backend/app/models/domain/ai.py:28`). Encryption uses existing Fernet pattern from `AIConfigService`.

### New Files

| File | Purpose |
|------|---------|
| `backend/app/models/domain/mcp_server.py` | Database model |
| `backend/app/models/schemas/mcp_server.py` | Pydantic schemas (Create/Update/Public) |
| `backend/app/services/mcp_server_service.py` | CRUD service with encryption |
| `backend/app/ai/mcp/__init__.py` | Package init |
| `backend/app/ai/mcp/client_manager.py` | MCP connection lifecycle + tool cache |
| `backend/app/api/routes/mcp_servers.py` | CRUD + test-connection endpoints |
| `backend/alembic/versions/xxxx_create_mcp_servers.py` | Migration |
| `frontend/src/features/ai/api/useMCPServers.ts` | TanStack Query hooks |
| `frontend/src/features/ai/components/MCPServerList.tsx` | Server table |
| `frontend/src/features/ai/components/MCPServerModal.tsx` | Create/Edit modal |
| `frontend/src/features/ai/components/MCPServerToolsModal.tsx` | Tool discovery view |

### Modified Files

| File | Change |
|------|--------|
| `backend/pyproject.toml` | Add `langchain-mcp-adapters` dependency |
| `backend/app/models/domain/__init__.py` | Register `mcp_server` module |
| `backend/app/db/seed/rbac_roles.json` | Add `mcp-server-*` permissions |
| `backend/app/ai/tools/__init__.py` | Append MCP tools in `create_project_tools()` |
| `backend/app/main.py` | Register MCP routes + lifespan hooks |
| `frontend/src/features/ai/api/queryKeys.ts` | Add `mcpServers` query key factory |
| `frontend/src/features/ai/types.ts` | Add MCP server types |
| `frontend/src/pages/admin/AIProviderManagement.tsx` | Add MCP Servers tab |

### RBAC Permissions

Add to admin role in `rbac_roles.json`:
- `mcp-server-read` — List and view MCP servers
- `mcp-server-create` — Add new MCP server
- `mcp-server-update` — Edit or test MCP server connection
- `mcp-server-delete` — Remove MCP server

### Security Model

| Aspect | Design |
|--------|--------|
| Admin gate | Only `mcp-server-*` permission holders can configure |
| Tool visibility | MCP tools visible to all agents once configured (no per-tool RBAC) |
| Execution mode | HIGH risk level — blocked in SAFE mode, allowed in STANDARD/EXPERT |
| Context isolation | MCP tools don't receive Backcast `ToolContext` |
| Network | stdio = local subprocess, HTTP/SSE = admin-configured endpoint |
| Encryption | Sensitive headers/env values encrypted with Fernet |

### API Endpoints

```
GET    /api/v1/mcp/servers              — List servers
POST   /api/v1/mcp/servers              — Create server
PUT    /api/v1/mcp/servers/{id}         — Update server
DELETE /api/v1/mcp/servers/{id}         — Delete server
POST   /api/v1/mcp/servers/{id}/test    — Test connection + discover tools
GET    /api/v1/mcp/servers/{id}/tools   — List cached tools for server
```

### Implementation Order

1. `pyproject.toml` + `uv sync`
2. Database model + migration + RBAC seed
3. Pydantic schemas
4. `MCPServerService` (CRUD + encryption)
5. `MCPClientManager` (lifecycle, caching, metadata)
6. Tool pipeline integration (`create_project_tools()` — 3 lines)
7. API routes + `main.py` registration
8. Frontend types + API hooks
9. Frontend admin components (list, modal, tools view)

---

## References

- Epic E09: AI Integration (`docs/03-project-plan/epics.md`)
- AI Provider model: `backend/app/models/domain/ai.py`
- AI Config Service: `backend/app/services/ai_config_service.py`
- AI Config Routes: `backend/app/api/routes/ai_config.py`
- Tool pipeline: `backend/app/ai/tools/__init__.py`
- Subagent compiler: `backend/app/ai/subagent_compiler.py`
- Supervisor orchestrator: `backend/app/ai/supervisor_orchestrator.py`
- `langchain-mcp-adapters`: https://github.com/langchain-ai/langchain-mcp-adapters
- MCP specification: https://modelcontextprotocol.io/
