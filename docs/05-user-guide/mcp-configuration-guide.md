# MCP Server Configuration — User Guide

**Last Updated:** 2026-05-04
**Audience:** System administrators, AI administrators

This guide explains how to configure MCP (Model Context Protocol) servers in Backcast to give AI agents access to external tools like web search, databases, and custom APIs.

---

## Table of Contents

1. [What Are MCP Servers?](#1-what-are-mcp-servers)
2. [Getting Started](#2-getting-started)
3. [Configuring MCP Servers](#3-configuring-mcp-servers)
4. [Transport Types](#4-transport-types)
5. [Example Server Configurations](#5-example-server-configurations)
6. [Testing and Monitoring](#6-testing-and-monitoring)
7. [Making Tools Available to Agents](#7-making-tools-available-to-agents)
8. [Troubleshooting](#8-troubleshooting)
9. [Security Considerations](#9-security-considerations)

---

## 1. What Are MCP Servers?

MCP (Model Context Protocol) is a standard protocol that allows AI agents to discover and use external tools. When you connect an MCP server to Backcast, the AI agents gain access to the tools that server provides.

**Examples of what MCP tools can do:**
- Search the web (DuckDuckGo, Brave Search)
- Query databases (PostgreSQL, SQLite)
- Read and write files
- Access custom APIs and internal services
- Fetch and process web pages

**How it works:**
1. You configure an MCP server in the Backcast admin UI
2. Backcast connects to the server and discovers its available tools
3. When you chat with the AI agent, it can use those tools to answer your questions

---

## 2. Getting Started

### Prerequisites

- Your user account must have the **MCP Server** management permissions (admin or AI-admin role)
- For stdio-based servers: the command must be available on the Backcast server (e.g., `npx`, `python`, `docker`)

### Accessing the MCP Server Page

1. Log in to Backcast
2. Click the **user icon** in the top-right corner
3. Select **MCP Servers** from the dropdown menu
4. You will see the MCP server management page with a list of configured servers

---

## 3. Configuring MCP Servers

### Adding a New Server

1. Click **+ Add Server** in the top-right corner
2. Fill in the form:
   - **Name**: A unique name for this server (e.g., `duckduckgo`, `postgres-internal`)
   - **Configuration (JSON)**: The connection config as a JSON object (see examples below)
3. Click **Create**

The server will be saved and Backcast will attempt to connect and discover tools. If the connection fails, the server is still saved — you can fix the config and test again later.

### Editing a Server

1. Click the **edit** (pencil) icon on the server row
2. Modify the name or configuration
3. Click **Save**

If you change the configuration, Backcast will reconnect to the server with the new settings.

### Deleting a Server

1. Click the **delete** (trash) icon on the server row
2. Confirm the deletion

All tools from that server are immediately removed from the agent's available tools.

### Deactivating a Server

To temporarily disable a server without deleting it:

1. Click **edit** on the server row
2. Toggle the **Active** switch to **off**
3. Click **Save**

Inactive servers are not connected at startup and their tools are not available to agents. You can reactivate them at any time.

---

## 4. Transport Types

MCP servers communicate with Backcast using different transport protocols. The `transport` field in the configuration determines which protocol to use.

### stdio

The server runs as a local subprocess on the Backcast machine. Backcast starts the process, communicates via standard input/output, and stops it when done.

```json
{
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "some-mcp-server-package"],
  "env": {}
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `command` | Yes | The command to run (e.g., `npx`, `python`, `docker`) |
| `args` | No | Arguments to pass to the command |
| `env` | No | Environment variables (key-value pairs) |

**Use when:** The MCP server is an npm package, Python script, or Docker container on the same machine.

### SSE (Server-Sent Events)

The server is accessed over HTTP using Server-Sent Events.

```json
{
  "transport": "sse",
  "url": "https://mcp.example.com/sse",
  "headers": {}
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | The SSE endpoint URL |
| `headers` | No | HTTP headers (for authentication, etc.) |

**Use when:** The MCP server is a remote service that exposes an SSE endpoint.

### streamable-http

The server is accessed over HTTP with streaming support.

```json
{
  "transport": "streamable_http",
  "url": "https://mcp.example.com/mcp",
  "headers": {}
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | The HTTP endpoint URL |
| `headers` | No | HTTP headers (for authentication, etc.) |

**Use when:** The MCP server uses the newer streamable HTTP transport (recommended over SSE for new deployments).

### websocket

The server is accessed via WebSocket.

```json
{
  "transport": "websocket",
  "url": "wss://mcp.example.com/ws"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | The WebSocket URL |

---

## 5. Example Server Configurations

### Web Search — DuckDuckGo (Free, No API Key)

Search the web using DuckDuckGo. No API key required — works out of the box.

```json
{
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@ericthered926/duckduckgo-mcp-server"],
  "env": {}
}
```

**Tools provided:** `duckduckgo_web_search`, `duckduckgo_news_search`

**Prerequisites:** Node.js and npm must be installed on the Backcast server.

### Web Search — Brave Search (API Key Required)

Search the web using Brave Search API.

```json
{
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@anthropic-ai/mcp-server-brave-search"],
  "env": {
    "BRAVE_API_KEY": "your-brave-api-key-here"
  }
}
```

**Prerequisites:** A Brave Search API key from [brave.com/search/api](https://brave.com/search/api/)

### Filesystem Access

Read and write files on the Backcast server within a specified directory.

```json
{
  "transport": "stdio",
  "command": "npx",
  "args": [
    "-y",
    "@anthropic-ai/mcp-server-filesystem",
    "/path/to/allowed/directory"
  ],
  "env": {}
}
```

**Caution:** This gives the AI agent access to files on the server. Restrict the directory path carefully.

### PostgreSQL Database

Query a PostgreSQL database directly.

```json
{
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@anthropic-ai/mcp-server-postgres"],
  "env": {
    "DATABASE_URL": "postgresql://user:password@host:5432/dbname"
  }
}
```

**Caution:** The agent can run arbitrary SQL queries. Use a read-only database user.

### GitHub

Access GitHub repositories, issues, and pull requests.

```json
{
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@anthropic-ai/mcp-server-github"],
  "env": {
    "GITHUB_TOKEN": "ghp_your-github-token-here"
  }
}
```

### Memory / Knowledge Graph

Persistent memory for the AI agent across conversations.

```json
{
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@anthropic-ai/mcp-server-memory"],
  "env": {}
}
```

### Puppeteer (Browser Automation)

Control a headless browser for web scraping and interaction.

```json
{
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@anthropic-ai/mcp-server-puppeteer"],
  "env": {}
}
```

### Custom Python MCP Server

If you have a custom MCP server written in Python:

```json
{
  "transport": "stdio",
  "command": "python",
  "args": ["/path/to/your/mcp_server.py"],
  "env": {
    "API_KEY": "your-api-key"
  }
}
```

### Remote MCP Server (HTTP)

Connect to an MCP server running on a different machine:

```json
{
  "transport": "streamable_http",
  "url": "https://mcp.internal.yourcompany.com/mcp",
  "headers": {
    "Authorization": "Bearer your-api-key"
  }
}
```

---

## 6. Testing and Monitoring

### Test Connection

After configuring a server, click the **test connection** (plug) icon to verify the connection works. This will:

1. Attempt to connect to the MCP server with the current configuration
2. Discover all available tools
3. Display the tool names and descriptions in a dialog

If the test fails, check:
- The command/path is correct
- Required environment variables are set
- The Backcast server can reach the MCP server (network connectivity)
- For stdio: the command is available on the system (`which npx`)

### View Discovered Tools

Click the **expand** arrow on the left side of a server row to see all tools that have been discovered and cached for that server. The tool list shows:

- **Tool name** (in monospace)
- **Description** of what the tool does

### Tools Count

The **Tools** column in the server table shows the number of cached tools. A `--` means no tools have been discovered (either the server hasn't connected yet or the connection failed).

---

## 7. Making Tools Available to Agents

### Agent Access Model

MCP tools are **not** available to all AI agents directly. They are routed through a dedicated **MCP specialist** agent:

```
You (chat) → Supervisor Agent → MCP Specialist (uses MCP tools)
```

When you ask a question that requires external tools (e.g., "Search the web for..."), the supervisor agent automatically delegates to the MCP specialist.

### Execution Mode

MCP tools require **STANDARD** or **EXPERT** execution mode:

| Mode | MCP Tools Available? |
|------|---------------------|
| SAFE | No — all MCP tools are blocked |
| STANDARD | Yes |
| EXPERT | Yes |

Set the execution mode in the AI chat interface before sending a message that requires external tools.

### User Permissions

Your user role must include the `mcp-tool-execute` permission to use MCP tools through the AI agent. This permission is included in the following roles by default:

| Role | Can Configure Servers | Can Use MCP Tools |
|------|-----------------------|-------------------|
| admin | Yes | Yes |
| ai-admin | Yes | Yes |
| ai-manager | No | Yes |
| viewer | No | No |

### When Tools Become Available

1. **At startup**: All active MCP servers are connected when Backcast starts
2. **On create**: When you add a new server, Backcast connects immediately
3. **On update**: When you change a server's config, Backcast reconnects with the new settings
4. **On delete**: Tools are removed immediately
5. **On deactivate**: Tools are removed; the server is skipped at next startup

**Note:** There may be a brief delay (a few seconds) between configuring a server and the tools becoming available to agents, as Backcast needs to start the server process and discover its tools.

---

## 8. Troubleshooting

### "Connection failed" when testing

| Cause | Solution |
|-------|----------|
| Command not found (stdio) | Install the required tool (`npm install -g npx`) |
| Package not found | Check the package name and try installing manually |
| Network error (HTTP/SSE) | Verify the URL is accessible from the Backcast server |
| Authentication error | Check API keys in the `env` or `headers` section |
| Timeout | The server may be slow to start — try again |

### Agent says it cannot access external tools

1. **Check execution mode**: Switch to STANDARD or EXPERT mode
2. **Check user role**: Your role needs `mcp-tool-execute` permission
3. **Check server status**: Verify the server is active and has discovered tools
4. **Restart**: If tools were just configured, the tool cache may need a server restart

### Tools were working but stopped

1. **Check server status**: Click "Test Connection" to verify the server is still reachable
2. **Check backend logs**: Ask your administrator to check `backend/logs/app.log` for MCP errors
3. **Restart the server**: MCP servers can crash — a Backcast restart will reconnect all servers

### Sensitive values in config

Environment variables and headers containing keys like `API_KEY`, `TOKEN`, `SECRET`, `PASSWORD`, or `AUTHORIZATION` are encrypted in the database. They appear as encrypted strings when viewed directly in the database but are decrypted automatically when Backcast connects to the server.

---

## 9. Security Considerations

### What You Should Know

- **MCP tools are external**: They run outside Backcast's sandbox. A misconfigured MCP server could access sensitive data or perform unwanted actions.
- **Agent isolation**: Only the dedicated MCP specialist agent can use MCP tools. Other agents cannot access them directly.
- **Encryption at rest**: API keys and tokens in the configuration are encrypted in the database using Fernet encryption.
- **RBAC**: Users need the `mcp-tool-execute` permission to trigger MCP tool usage through the AI agent.
- **Risk level**: All MCP tools are classified as HIGH risk, which means they are blocked in SAFE execution mode.

### Best Practices

1. **Use the minimum required permissions**: For database MCP servers, use a read-only user. For API servers, use scoped tokens.
2. **Restrict filesystem access**: When using filesystem MCP servers, limit the directory to only what the agent needs.
3. **Monitor usage**: Check the AI chat logs to see which MCP tools are being used and what data they access.
4. **Disable when not needed**: Deactivate servers that are not actively needed rather than keeping them running.
5. **Keep packages updated**: MCP server packages receive security updates — update them regularly.
6. **Network security**: For HTTP-based servers, use HTTPS and ensure the endpoint is not publicly accessible.
