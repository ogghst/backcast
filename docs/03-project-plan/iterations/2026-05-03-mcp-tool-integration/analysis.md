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
4. **Subagent Whitelist**: Domain specialization per subagent (MCP tools only available to `mcp_specialist`)
5. **Runtime**: `RBACToolNode` checks permissions at execution time (MCP tools require `mcp-tool-execute`)
6. **Approval**: `InterruptNode` for HIGH/CRITICAL risk operations

### Key Constraint

`create_project_tools()` is **synchronous** and uses global caching (`_cached_tools`). All callers (`subagent_compiler.py`, `graph.py`) expect a `list[BaseTool]` return. Any MCP integration must work within this constraint.

### Agent Orchestration

The supervisor orchestrator (`backend/app/ai/supervisor_orchestrator.py`) compiles subagents with filtered tools. The briefing-room pattern dispatches tasks to specialists. MCP tools must be available at the same compilation stage as native tools.

---

## Proposed Architecture: MCP Tool Integration

### Dedicated MCP Specialist

MCP tools are **not** available to all agents. A dedicated `mcp_specialist` subagent is the only agent with MCP tools in its whitelist. This follows the existing domain-specialization pattern (evm_analyst for EVM tools, change_order_manager for change orders, etc.).

**Rationale:**
- MCP tools are external and potentially risky — isolating them to one specialist limits blast radius
- Clear audit trail — all MCP tool usage routes through a single, well-defined agent
- Consistent with existing subagent architecture — no special-case tool routing logic
- The supervisor delegates to `mcp_specialist` when external tool access is needed

```
Supervisor → mcp_specialist (has MCP tools + selected native tools)
           → evm_analyst (EVM tools only)
           → project_manager (project CRUD tools only)
           → ...
```

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
    permissions=["mcp-tool-execute"],  # Dedicated RBAC permission
    category=f"mcp:{server_name}",
    risk_level=RiskLevel.HIGH,         # Conservative — blocked in SAFE mode
)
```

This ensures MCP tools:
- Require the `mcp-tool-execute` permission — only roles with this permission can use MCP tools
- Are blocked in SAFE execution mode (HIGH risk level)
- Are identifiable by category prefix `mcp:` for specialist filtering
- Are routed to a dedicated specialist (`mcp_specialist`) for execution

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
- **JSON-based configuration** — a single JSON editor field where the admin writes the full MCP server config (transport, command, args, url, headers, env) following the standard MCP server configuration format
- JSON editor provides schema validation and syntax highlighting
- "Test Connection" button validates configuration and discovers available tools
- Tool discovery view shows available tools per server
- Example config shown as placeholder:
  ```json
  {
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@ericthered926/duckduckgo-mcp-server"],
    "env": {}
  }
  ```

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
    config: dict           # JSONB — full MCP server config (transport, command, args, url, headers, env)
                           # Sensitive values (headers.auth, env.API_KEY) encrypted via Fernet
    is_active: bool        # Enable/disable without deleting
```

The `config` JSONB stores the entire MCP server configuration as a single JSON document — matching the JSON editor in the admin UI. Example configs:

**stdio transport:**
```json
{
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@ericthered926/duckduckgo-mcp-server"],
  "env": {}
}
```

**HTTP transport:**
```json
{
  "transport": "streamable-http",
  "url": "https://mcp.example.com/sse",
  "headers": {"Authorization": "Bearer secret"}
}
```

Follows `AIProvider` model pattern (`backend/app/models/domain/ai.py:28`). Encryption uses existing Fernet pattern from `AIConfigService`.

### New Files

| File | Purpose |
|------|---------|
| `backend/app/models/domain/mcp_server.py` | Database model (MCPServer) |
| `backend/app/models/schemas/mcp_server.py` | Pydantic schemas (Create/Update/Public) |
| `backend/app/services/mcp_server_service.py` | CRUD service with encryption |
| `backend/app/ai/mcp/__init__.py` | Package init |
| `backend/app/ai/mcp/client_manager.py` | MCP connection lifecycle + tool cache |
| `backend/app/ai/mcp/tool_metadata.py` | MCP tool metadata wrapper |
| `backend/app/api/routes/mcp_servers.py` | CRUD + test-connection endpoints |
| `backend/alembic/versions/xxxx_create_mcp_servers.py` | Migration |

### Modified Files

| File | Change |
|------|--------|
| `backend/pyproject.toml` | Add `langchain-mcp-adapters` dependency |
| `backend/app/models/domain/__init__.py` | Register `mcp_server` module |
| `backend/app/db/seed/rbac_roles.json` | Add `mcp-server-*` and `mcp-tool-execute` permissions |
| `backend/app/ai/tools/__init__.py` | Append MCP tools in `create_project_tools()` |
| `backend/app/ai/subagents/__init__.py` | Add `mcp_specialist` subagent definition |
| `backend/app/main.py` | Register MCP routes + lifespan hooks |
| `frontend/src/features/ai/api/queryKeys.ts` | Add `mcpServers` query key factory |
| `frontend/src/features/ai/types.ts` | Add MCP server types |
| `frontend/src/pages/admin/AIProviderManagement.tsx` | Add MCP Servers tab with JSON editor |

### RBAC Permissions

Add to `rbac_roles.json`:
- `mcp-server-read` — List and view MCP servers
- `mcp-server-create` — Add new MCP server
- `mcp-server-update` — Edit or test MCP server connection
- `mcp-server-delete` — Remove MCP server
- `mcp-tool-execute` — Use MCP tools via the AI agent (assigned to roles that should have external tool access)

### Security Model

| Aspect | Design |
|--------|--------|
| Admin gate | Only `mcp-server-*` permission holders can configure |
| Tool execution | Requires `mcp-tool-execute` permission — checked by RBACToolNode at runtime |
| Specialist isolation | Only `mcp_specialist` has MCP tools in its whitelist — other agents cannot access them |
| Execution mode | HIGH risk level — blocked in SAFE mode, allowed in STANDARD/EXPERT |
| Context isolation | MCP tools don't receive Backcast `ToolContext` |
| Network | stdio = local subprocess, HTTP/SSE = admin-configured endpoint |
| Encryption | Sensitive values within `config` JSONB encrypted with Fernet |

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
3. Pydantic schemas (JSON config validation)
4. `MCPServerService` (CRUD + encryption)
5. `MCPClientManager` (lifecycle, caching, metadata wrapping)
6. `mcp_specialist` subagent definition
7. Tool pipeline integration (`create_project_tools()` — 3 lines)
8. API routes + `main.py` registration
9. Frontend types + API hooks
10. Frontend admin components (list, JSON editor modal, tools view)

### Validation Phase

The final validation step proves the full pipeline works end-to-end using a real MCP server:

**MCP Server:** `@ericthered926/duckduckgo-mcp-server` — free DuckDuckGo web search via stdio, no API key required.

**Config:**
```json
{
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@ericthered926/duckduckgo-mcp-server"],
  "env": {}
}
```

**Test Steps:**
1. Add the DuckDuckGo MCP server via admin UI (paste JSON config)
2. Click "Test Connection" — verify tools are discovered (e.g., `search`, `fetch`)
3. Start an AI chat session in STANDARD or EXPERT mode
4. Ask: "Search the web for information about Area 51"
5. Verify the supervisor delegates to `mcp_specialist`
6. Verify `mcp_specialist` uses the DuckDuckGo search tool
7. Verify the response contains real web search results about Area 51

**Success Criteria:**
- MCP server connects and tools are discovered at startup
- `mcp_specialist` receives MCP tools in its whitelist
- `RBACToolNode` checks `mcp-tool-execute` permission before allowing tool execution
- Agent returns actual web search results, not a fallback message

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
