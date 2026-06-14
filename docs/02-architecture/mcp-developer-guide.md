# MCP Tool Integration — Developer Guide

**Last Updated:** 2026-06-14
**Status:** Active
**Doc Version:** 1.1

This guide covers the architecture, internals, and extension points of the MCP (Model Context Protocol) tool integration in Backcast. It is intended for developers working on the AI agent system.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Tool Pipeline](#2-tool-pipeline)
3. [Core Components](#3-core-components)
4. [RBAC and Security Model](#4-rbac-and-security-model)
5. [MCP Tool Distribution](#5-mcp-tool-distribution)
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
| Database model | `app/models/domain/mcp_server.py` | `MCPServer(SimpleEntityBase)` — config stored as encrypted TEXT |
| Pydantic schemas | `app/models/schemas/mcp_server.py` | Create/Update/Public validation |
| CRUD service | `app/services/mcp_server_service.py` | Fernet encryption of the entire config blob |
| Client manager | `app/ai/mcp/client_manager.py` | Singleton — async lifecycle, sync cache |
| Tool wrapper | `app/ai/mcp/tool_metadata.py` | Attaches `ToolMetadata` to MCP tools |
| API routes | `app/api/routes/mcp_servers.py` | 6 REST endpoints |
| Pipeline hook | `app/ai/tools/__init__.py` | MCP tools appended to `base_tools` in `create_project_tools()` |

---

## 2. Tool Pipeline

MCP tools pass through the same multi-stage filtering pipeline as native tools:

```
1. Execution Mode    SAFE → LOW only, STANDARD → everything except CRITICAL (i.e. LOW+HIGH), EXPERT → all
2. Assistant Role    Ceiling from assistant config
3. User Role         Actual user permissions
4. Runtime RBAC      RBACToolNode checks mcp-tool-execute permission
5. Approval          InterruptNode for HIGH/CRITICAL risk operations
```

> **`RiskLevel`** is exactly `LOW` / `HIGH` / `CRITICAL` (there is **no** `MEDIUM` level) — see `app/ai/tools/types.py`.

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

CRUD service with Fernet encryption. The **entire** config blob is encrypted at rest as a single Fernet string:

- `encrypt_config(config: dict) -> str` serializes the full config dict to JSON and encrypts it into one Fernet blob, which is stored in the `config` TEXT column.
- `decrypt_config(config: str) -> dict` reverses this, raising `ValueError` if the blob cannot be decrypted (e.g. `SECRET_KEY` changed).
- There is **no** selective `SENSITIVE_KEYS` filtering and **no** `get_decrypted_config()` method — the whole config is one encrypted string.

The Fernet key is derived from `settings.SECRET_KEY` (first 32 bytes, padded), the same pattern as `AIConfigService`.

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

The `category` prefix `mcp:` is used by `_is_server_tool()` to identify which server a tool belongs to.

---

## 4. RBAC and Security Model

### Permissions

| Permission | Purpose | Assigned To |
|------------|---------|-------------|
| `mcp-server-read` | List/view MCP servers | admin, ai-admin |
| `mcp-server-create` | Add new MCP server | admin, ai-admin |
| `mcp-server-update` | Edit or test connection | admin, ai-admin |
| `mcp-server-delete` | Remove MCP server | admin, ai-admin |
| `mcp-tool-execute` | Use MCP tools via AI agent | admin, ai-admin, ai-manager, ai-viewer |

### Security Layers

| Layer | Mechanism |
|-------|-----------|
| **Admin gate** | Only `mcp-server-*` holders can configure servers |
| **Tool execution** | `RBACToolNode` checks `mcp-tool-execute` at runtime |
| **Execution mode** | HIGH risk — blocked in SAFE mode |
| **Encryption** | Entire config blob encrypted with Fernet |
| **Network** | stdio = local subprocess, HTTP = admin-configured endpoint |

### Permission Flow

```
User sends chat message
  → Agent (or any specialist) has MCP tools in the shared tool pool
    → RBACToolNode checks: does user's role include mcp-tool-execute?
      → YES: tool executes
      → NO: tool call blocked, error returned to agent
```

---

## 5. MCP Tool Distribution

There is **no** dedicated MCP subagent — the `mcp_specialist` specialist was removed in migration `7e61a160474b_remove_mcp_specialist` (2026-06-03) and is absent from the seed config. MCP tools are now distributed through the normal tool pool.

**Who receives MCP tools?**

All MCP tools are appended to `base_tools` inside `create_project_tools()` (`app/ai/tools/__init__.py`, ~lines 325-331):

```python
# Append MCP tools discovered from configured external servers
from app.ai.mcp.client_manager import MCPClientManager

mcp_manager = MCPClientManager()
base_tools.extend(mcp_manager.get_all_tools())
```

From there they are filtered only by:

- **Execution mode** — `filter_tools_by_execution_mode()` (HIGH-risk MCP tools are blocked in `SAFE` mode, allowed in `STANDARD`/`EXPERT`).
- **RBAC** — the `mcp-tool-execute` permission on the tool's `ToolMetadata` is checked by `RBACToolNode` at runtime.

There is **no** specialist-level isolation. Any agent or specialist whose tool whitelist resolves to those tool names can use MCP tools.

**Note on `allowed_tools: None` specialists:** A specialist configured with `allowed_tools: None` resolves to an **empty** tool list (`app/ai/subagent_compiler.py` ~lines 143-145) and is then **skipped** by `compile_subagents` (`if not subagent_tools: ... continue`, ~lines 168-172). So a `None`-whitelist specialist receives no tools at all, MCP or otherwise — use `allowed_tools: ["*"]` for a catch-all/fallback specialist.

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
| `app/services/mcp_server_service.py` | CRUD + full-blob Fernet encryption |
| `app/api/routes/mcp_servers.py` | REST endpoints |
| `app/ai/tools/__init__.py` | MCP tools appended to `base_tools` in `create_project_tools()` |
| `app/ai/subagent_compiler.py` | `compile_subagents` (skips tool-less specialists) |
| `app/main.py` | Lifespan hooks |
| `seed/rbac_roles.json` | RBAC permissions |
| `alembic/versions/44d11de23f6f_change_mcp_servers_config_to_text.py` | Migration: config column → TEXT |
| `alembic/versions/7e61a160474b_remove_mcp_specialist.py` | Migration: remove `mcp_specialist` |
