"""MCP client manager singleton for Backcast AI agent system.

Manages connections to MCP (Model Context Protocol) servers, discovers
their tools at startup, and caches them for synchronous access from
``create_project_tools()``.

Design:
    - Async lifecycle: ``initialize()`` called from FastAPI lifespan.
    - Sync access: ``get_all_tools()`` returns cached tools.
    - Graceful degradation: unreachable servers are logged and skipped.
    - ``langchain-mcp-adapters`` handles transport lifecycle internally
      when given a connection config via ``load_mcp_tools(connection=...)``.
"""

import logging
from typing import Any

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.config import AI_MCP_TOOL_CATEGORY_PREFIX
from app.ai.mcp.tool_metadata import wrap_mcp_tool

logger = logging.getLogger(__name__)


class MCPClientManager:
    """Singleton managing MCP server connections and tool discovery."""

    _instance: "MCPClientManager | None" = None
    _tools: list[BaseTool]

    def __new__(cls) -> "MCPClientManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = []
        return cls._instance

    # -- Async lifecycle (called from FastAPI lifespan) ---------------------

    async def initialize(self, session: AsyncSession) -> None:
        """Load all active MCP servers from DB and connect.

        Args:
            session: Database session for querying MCP server configs.
        """
        from app.services.mcp_server_service import (
            MCPServerService,
        )

        service = MCPServerService(session)
        servers = await service.list_servers(active_only=True)

        for server in servers:
            try:
                decrypted_config = service.decrypt_config(server.config)
                tools = await self._connect_server(server.name, decrypted_config)
                self._tools.extend(tools)
                logger.info("MCP server '%s': %d tools loaded", server.name, len(tools))
            except Exception:
                logger.warning(
                    "MCP server '%s' failed during initialize",
                    server.name,
                    exc_info=True,
                )

        logger.info(
            "MCP: %d total tools loaded from %d servers",
            len(self._tools),
            len(servers),
        )

    async def refresh_server(self, server_name: str, config: dict[str, Any]) -> None:
        """Reconnect a specific server after create/update.

        Args:
            server_name: Server identifier.
            config: Connection config dict (transport, command/url, etc.).
        """
        self._tools = [
            t for t in self._tools if not self._is_server_tool(t, server_name)
        ]
        tools = await self._connect_server(server_name, config)
        self._tools.extend(tools)

        from app.ai.tools import invalidate_tool_cache

        invalidate_tool_cache()

    async def remove_server(self, server_name: str) -> None:
        """Remove tools belonging to a deleted server.

        Args:
            server_name: Server identifier.
        """
        before = len(self._tools)
        self._tools = [
            t for t in self._tools if not self._is_server_tool(t, server_name)
        ]
        logger.info(
            "MCP server '%s' removed: %d tools dropped",
            server_name,
            before - len(self._tools),
        )

        from app.ai.tools import invalidate_tool_cache

        invalidate_tool_cache()

    async def shutdown(self) -> None:
        """Clean up all cached tools."""
        self._tools = []

        from app.ai.tools import invalidate_tool_cache

        invalidate_tool_cache()

        logger.info("MCP client manager shut down")

    async def test_connection(self, config: dict[str, Any]) -> list[dict[str, str]]:
        """Test a server config and return discovered tool names/descriptions.

        Args:
            config: Connection config dict (transport, command/url, etc.).

        Returns:
            List of dicts with ``name`` and ``description`` keys.
        """
        tools = await self._connect_server("__test__", config)
        return [{"name": t.name, "description": t.description or ""} for t in tools]

    # -- Sync access (called from create_project_tools) --------------------

    def get_all_tools(self) -> list[BaseTool]:
        """Return cached MCP tools for synchronous access.

        Called from ``create_project_tools()`` which is synchronous.
        """
        return list(self._tools)

    # -- Internal helpers --------------------------------------------------

    def _is_server_tool(self, tool: BaseTool, server_name: str) -> bool:
        """Check if a tool belongs to a specific MCP server.

        Args:
            tool: Tool to check.
            server_name: Server identifier.

        Returns:
            True if the tool's metadata category matches ``mcp:<server_name>``.
        """
        meta = getattr(tool, "_tool_metadata", None)
        if meta is not None:
            return meta.category == f"{AI_MCP_TOOL_CATEGORY_PREFIX}{server_name}"
        return False

    def _build_connection(self, config: dict[str, Any]) -> Any:
        """Build a langchain-mcp-adapters connection TypedDict from raw config.

        Args:
            config: Raw config dict stored in the database.

        Returns:
            A connection TypedDict suitable for ``load_mcp_tools``.

        Raises:
            ValueError: If the transport type is unsupported.
        """
        transport = config.get("transport", "stdio")

        if transport == "stdio":
            from langchain_mcp_adapters.sessions import StdioConnection

            return StdioConnection(
                transport="stdio",
                command=config["command"],
                args=config.get("args", []),
                env=config.get("env"),
            )
        elif transport == "sse":
            from langchain_mcp_adapters.sessions import SSEConnection

            return SSEConnection(
                transport="sse",
                url=config["url"],
                headers=config.get("headers"),
            )
        elif transport == "streamable_http":
            from langchain_mcp_adapters.sessions import StreamableHttpConnection

            return StreamableHttpConnection(
                transport="streamable_http",
                url=config["url"],
                headers=config.get("headers"),
            )
        elif transport == "websocket":
            from langchain_mcp_adapters.sessions import WebsocketConnection

            return WebsocketConnection(
                transport="websocket",
                url=config["url"],
            )
        else:
            raise ValueError(f"Unsupported MCP transport: {transport}")

    async def _connect_server(
        self, server_name: str, config: dict[str, Any]
    ) -> list[BaseTool]:
        """Connect to an MCP server and return wrapped tools.

        Uses ``langchain-mcp-adapters`` which manages transport lifecycle
        internally via the connection config.

        Args:
            server_name: Server identifier for metadata tagging.
            config: Connection config dict.

        Returns:
            List of BaseTool instances wrapped with Backcast metadata.
        """
        from langchain_mcp_adapters.tools import load_mcp_tools

        connection = self._build_connection(config)
        raw_tools = await load_mcp_tools(
            session=None,
            connection=connection,
            server_name=server_name,
        )
        return [wrap_mcp_tool(t, server_name) for t in raw_tools]
