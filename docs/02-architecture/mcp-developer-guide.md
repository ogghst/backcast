# MCP Tool Integration — Developer Guide

**Last Updated:** 2026-05-04
**Status:** Active

This guide covers the architecture, internals, and extension points of the MCP (Model Context Protocol) tool integration in Backcast. It is intended for developers working on the AI agent system.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Tool Pipeline](#2-tool-pipeline)
3. [Core Components](#3-core-components)
4. [RBAC and Security Model](#4-rbac-and-security-model)
5. [MCP Specialist Subagent](#5-mcp-specialist-subagent)
6. [Adding a New MCP Transport](#6-adding-a-new-mcp-transport)
7. [Extending the Tool Metadata](#7-extending-the-tool-metadata)
8. [Testing Patterns](#8-testing-patterns)
9. [Troubleshooting](#9-troubleshooting)
10. [File Reference](#10-file-reference)

---

## 1. Architecture Overview

MCP tools integrate into the existing Backcast tool pipeline alongside native `@ai_tool` tools. The key architectural constraint is that `create_project_tools()` is **synchronous** with a global cache, while MCP tool discovery requires async I/O. This is resolved via a **sync cache pattern**: tools are loaded asynchronously at startup and stored for synchronous access at runtime.

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
│  - Connects via langchain-mcp-adapters                       │
│  - Caches tools as list[BaseTool]                            │
│  - get_all_tools() → sync dict lookup                        │
└────────────────────────┬────────────────────────────────────┘
                         │ extend
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  create_project_tools()                                      │
│  native_tools (cached) + mcp_tools (from client manager)     │
└────────────────────────┬────────────────────────────────────┘
                         │ filter_tools_for_context()
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent / Subagent (LangGraph)                                │
│  Same RBAC, risk-level, and approval pipeline as native      │
└─────────────────────────────────────────────────────────────┘
```

### Key Files

| Component | File | Role |
|-----------|------|------|
| Database model | `app/models/domain/mcp_server.py` | `MCPServer(SimpleEntityBase)` — JSONB config storage |
| Pydantic schemas | `app/models/schemas/mcp_server.py` | Create/Update/Public validation |
| CRUD service | `app/services/mcp_server_service.py` | Fernet encryption for sensitive values |
| Client manager | `app/ai/mcp/client_manager.py` | Singleton — async lifecycle, sync cache |
| Tool wrapper | `app/ai/mcp/tool_metadata.py` | Attaches `ToolMetadata` to MCP tools |
| API routes | `app/api/routes/mcp_servers.py` | 6 REST endpoints |
| Pipeline hook | `app/ai/tools/__init__.py` | 3-line integration in `create_project_tools()` |
| Subagent | `app/ai/subagents/__init__.py` | `mcp_specialist` definition |

---

## 2. Tool Pipeline

MCP tools pass through the same multi-stage filtering pipeline as native tools:

```
1. Execution Mode    SAFE → LOW only, STANDARD → LOW+HIGH, EXPERT → all
2. Assistant Role    Ceiling from assistant config
3. User Role         Actual user permissions
4. Subagent Filter   MCP tools only available to mcp_specialist
5. Runtime RBAC      RBACToolNode checks mcp-tool-execute permission
6. Approval          InterruptNode for HIGH/CRITICAL risk operations
```

MCP tools have `risk_level=RiskLevel.HIGH`, meaning:
- **SAFE mode**: blocked
- **STANDARD mode**: allowed (HIGH is included)
- **EXPERT mode**: allowed (all levels included)

The integration point in `create_project_tools()` (`app/ai/tools/__init__.py`):

```python
# After native tools are collected and filtered to BaseTool instances:
from app.ai.mcp.client_manager import MCPClientManager

mcp_manager = MCPClientManager()
base_tools.extend(mcp_manager.get_all_tools())
```

This is a **pure append** — no modifications to the native tool logic. MCP tools are cached alongside native tools in `_cached_tools`.

---

## 3. Core Components

### MCPClientManager

**File:** `app/ai/mcp/client_manager.py`

Singleton that manages MCP server connections. Key methods:

| Method | Type | Called From | Purpose |
|--------|------|-------------|---------|
| `initialize(session)` | async | `main.py` lifespan | Load all active servers from DB |
| `refresh_server(name, config)` | async | API routes (create/update) | Reconnect a specific server |
| `remove_server(name)` | async | API routes (delete) | Drop tools for a deleted server |
| `test_connection(config)` | async | API routes (test) | Probe config without caching |
| `get_all_tools()` | sync | `create_project_tools()` | Return cached tools |
| `shutdown()` | async | `main.py` lifespan | Clear cache |

**Connection lifecycle:**

The `_connect_server()` method builds a `langchain-mcp-adapters` connection TypedDict from the raw config and calls `load_mcp_tools(connection=...)`. The library handles transport lifecycle internally — no manual context manager management needed.

**Supported transports:**

| Transport | Connection Type | Config Fields |
|-----------|----------------|---------------|
| `stdio` | `StdioConnection` | `command`, `args`, `env` |
| `sse` | `SSEConnection` | `url`, `headers` |
| `streamable_http` | `StreamableHttpConnection` | `url`, `headers` |
| `websocket` | `WebsocketConnection` | `url` |

**Graceful degradation:** Each server connection is wrapped in try/except during `initialize()`. Failed servers are logged and skipped — the agent gets whatever tools are available from connected servers.

### MCPServerService

**File:** `app/services/mcp_server_service.py`

CRUD service with Fernet encryption. Sensitive values within the `config` JSONB are encrypted at rest:

- Keys matching `SENSITIVE_KEYS` (`api_key`, `authorization`, `token`, `secret`, `password`) in `config.env` and `config.headers` sub-dicts are encrypted.
- The `get_decrypted_config()` method returns plaintext config for `MCPClientManager` to use when connecting.

Encryption follows the same pattern as `AIConfigService` — key derived from `settings.SECRET_KEY`.

### Tool Metadata Wrapper

**File:** `app/ai/mcp/tool_metadata.py`

Each MCP tool gets a `ToolMetadata` attached:

```python
ToolMetadata(
    name=tool.name,
    description=tool.description or "",
    permissions=["mcp-tool-execute"],
    category=f"mcp:{server_name}",
    risk_level=RiskLevel.HIGH,
)
```

The `category` prefix `mcp:` is used by `_is_server_tool()` to identify which server a tool belongs to, and by the subagent compiler to route tools to `mcp_specialist`.

---

## 4. RBAC and Security Model

### Permissions

| Permission | Purpose | Assigned To |
|------------|---------|-------------|
| `mcp-server-read` | List/view MCP servers | admin, ai-admin |
| `mcp-server-create` | Add new MCP server | admin, ai-admin |
| `mcp-server-update` | Edit or test connection | admin, ai-admin |
| `mcp-server-delete` | Remove MCP server | admin, ai-admin |
| `mcp-tool-execute` | Use MCP tools via AI agent | admin, ai-admin, ai-manager |

### Security Layers

| Layer | Mechanism |
|-------|-----------|
| **Admin gate** | Only `mcp-server-*` holders can configure servers |
| **Tool execution** | `RBACToolNode` checks `mcp-tool-execute` at runtime |
| **Specialist isolation** | Only `mcp_specialist` receives MCP tools |
| **Execution mode** | HIGH risk — blocked in SAFE mode |
| **Encryption** | Sensitive config values encrypted with Fernet |
| **Network** | stdio = local subprocess, HTTP = admin-configured endpoint |

### Permission Flow

```
User sends chat message
  → Supervisor decides to delegate to mcp_specialist
    → mcp_specialist has MCP tools in its whitelist
      → RBACToolNode checks: does user's role include mcp-tool-execute?
        → YES: tool executes
        → NO: tool call blocked, error returned to agent
```

---

## 5. MCP Specialist Subagent

**File:** `app/ai/subagents/__init__.py`

The `mcp_specialist` is a dedicated subagent that is the **only** agent with access to MCP tools. This follows the existing domain-specialization pattern.

**Definition:**

```python
MCP_SPECIALIST_SUBAGENT = {
    "name": "mcp_specialist",
    "description": "Handles tasks requiring external tools via MCP servers...",
    "system_prompt": "You are an MCP specialist...",
    "allowed_tools": None,  # Receives all tools; RBAC filters MCP-specific
    ...
}
```

**Why `allowed_tools: None`?** MCP tool names are dynamic — they depend on which servers are configured. Setting `allowed_tools: None` means the specialist receives all available tools, and the RBAC pipeline filters by the `mcp-tool-execute` permission on MCP tool metadata.

**Supervisor delegation:** The supervisor orchestrator lists `mcp_specialist` in its briefing room prompt, so it knows to delegate when external tool access is needed (web search, database queries, etc.).

---

## 6. Adding a New MCP Transport

If `langchain-mcp-adapters` adds a new transport type (e.g., `grpc`), you need to update two places:

### 1. Pydantic Schema

**File:** `app/models/schemas/mcp_server.py`

Add the new transport to the `Literal` type and create a config class:

```python
class GrpcConfig(MCPServerConfigBase):
    """Config for gRPC-based MCP servers."""
    transport: Literal["grpc"] = "grpc"
    url: str
    # Add gRPC-specific fields
```

Update the union type:

```python
MCPConfig = StdioConfig | HttpConfig | GrpcConfig
```

### 2. Client Manager

**File:** `app/ai/mcp/client_manager.py`

Add a new branch in `_build_connection()`:

```python
elif transport == "grpc":
    from langchain_mcp_adapters.sessions import GrpcConnection

    return GrpcConnection(
        transport="grpc",
        url=config["url"],
    )
```

### 3. Frontend

No changes needed — the transport type is extracted from `config.transport` dynamically. It will appear as a tag in the server list automatically.

---

## 7. Extending the Tool Metadata

To change the default risk level or permissions for MCP tools, edit `app/ai/mcp/tool_metadata.py`:

```python
metadata = ToolMetadata(
    name=tool.name,
    description=tool.description or "",
    permissions=["mcp-tool-execute"],
    category=f"mcp:{server_name}",
    risk_level=RiskLevel.HIGH,  # Change to LOW if you trust all MCP tools
)
```

**Per-server risk levels** are not currently supported — all MCP tools get `HIGH`. To add per-server configuration, extend the `MCPServer` model with a `default_risk_level` column and pass it through `wrap_mcp_tool()`.

---

## 8. Testing Patterns

### Unit Testing MCP Components

Mock `MCPClientManager` to avoid needing real MCP servers:

```python
from unittest.mock import MagicMock
from app.ai.mcp.client_manager import MCPClientManager


def test_mcp_tools_included_in_pipeline():
    manager = MCPClientManager()
    manager._tools = [MagicMock(spec=BaseTool, name="mock_mcp_tool")]

    tools = manager.get_all_tools()
    assert len(tools) == 1
    assert tools[0].name == "mock_mcp_tool"
```

### Testing API Routes

Use `httpx.AsyncClient` with the FastAPI test client:

```python
async def test_create_mcp_server(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/v1/mcp/servers",
        json={
            "name": "test-server",
            "config": {"transport": "stdio", "command": "echo"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
```

### Integration Testing with Real MCP Server

Use the DuckDuckGo MCP server (free, no API key):

```python
config = {
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@ericthered926/duckduckgo-mcp-server"],
    "env": {},
}
manager = MCPClientManager()
tools = await manager.test_connection(config)
assert len(tools) > 0
assert any("search" in t["name"] for t in tools)
```

---

## 9. Troubleshooting

### Server created but no tools discovered

**Symptom:** MCP server appears in list with `--` tools count.

**Cause:** The MCP server process failed to start or the connection was rejected.

**Debug:**
1. Click "Test Connection" in the admin UI — this attempts a fresh connection and shows the error
2. Check backend logs: `grep "MCP" backend/logs/app.log`
3. Verify the command works manually: `npx -y @ericthered926/duckduckgo-mcp-server`

### Tools discovered but agent cannot use them

**Symptom:** Tools show in admin UI but agent says it cannot access external tools.

**Cause (most likely):** User's role lacks `mcp-tool-execute` permission.

**Debug:**
1. Check the user's role permissions in the database
2. Verify the chat is in STANDARD or EXPERT mode (SAFE mode blocks HIGH-risk tools)

### Config changes not taking effect

**Symptom:** Updated config but old tools still appear.

**Cause:** The tool cache in `create_project_tools()` is stale.

**Fix:** Restart the backend server. The global `_cached_tools` is invalidated on restart, and `MCPClientManager` reinitializes from the database.

---

## 10. File Reference

| File | Purpose |
|------|---------|
| `app/ai/mcp/__init__.py` | Package init |
| `app/ai/mcp/client_manager.py` | MCP connection lifecycle + tool cache |
| `app/ai/mcp/tool_metadata.py` | ToolMetadata wrapper for MCP tools |
| `app/models/domain/mcp_server.py` | Database model |
| `app/models/schemas/mcp_server.py` | Pydantic schemas |
| `app/services/mcp_server_service.py` | CRUD + encryption |
| `app/api/routes/mcp_servers.py` | REST endpoints |
| `app/ai/tools/__init__.py` | Pipeline integration (3 lines) |
| `app/ai/subagents/__init__.py` | mcp_specialist definition |
| `app/main.py` | Lifespan hooks |
| `seed/rbac_roles.json` | RBAC permissions |
| `alembic/versions/02a4e8ce7dbb_*` | Migration |
