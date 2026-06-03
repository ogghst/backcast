"""API routes for MCP server management.

Provides endpoints for CRUD operations on MCP server configurations,
connection testing, and tool discovery.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.mcp.client_manager import MCPClientManager
from app.api.dependencies.auth import RoleChecker
from app.db.session import get_db
from app.models.domain.mcp_server import MCPServer
from app.models.schemas.mcp_server import (
    MCPServerCreate,
    MCPServerPublic,
    MCPServerUpdate,
    MCPToolInfo,
)
from app.services.mcp_server_service import MCPServerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp/servers", tags=["MCP Servers"])


def get_mcp_server_service(
    session: AsyncSession = Depends(get_db),
) -> MCPServerService:
    """Get MCP server configuration service."""
    return MCPServerService(session)


def _decrypt_and_public(service: MCPServerService, server: MCPServer) -> MCPServerPublic:
    """Build a MCPServerPublic with decrypted config."""
    decrypted = service.decrypt_config(server.config)
    return MCPServerPublic(
        id=server.id,
        name=server.name,
        config=decrypted,
        is_active=server.is_active,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )


@router.get(
    "",
    response_model=list[MCPServerPublic],
    operation_id="list_mcp_servers",
    dependencies=[Depends(RoleChecker(required_permission="mcp-server-read"))],
)
async def list_servers(
    include_inactive: bool = False,
    service: MCPServerService = Depends(get_mcp_server_service),
) -> list[MCPServerPublic]:
    """List all MCP server configurations."""
    servers = await service.list_servers(active_only=not include_inactive)
    return [_decrypt_and_public(service, s) for s in servers]


@router.post(
    "",
    response_model=MCPServerPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_mcp_server",
    dependencies=[Depends(RoleChecker(required_permission="mcp-server-create"))],
)
async def create_server(
    server_in: MCPServerCreate,
    service: MCPServerService = Depends(get_mcp_server_service),
) -> MCPServerPublic:
    """Create a new MCP server configuration."""
    server = await service.create_server(server_in)

    # Notify MCP client manager to connect and discover tools (non-blocking)
    mcp_manager = MCPClientManager()
    decrypted = service.decrypt_config(server.config)
    try:
        await mcp_manager.refresh_server(server.name, decrypted)
    except Exception:
        logger.warning(
            "MCP server '%s' connection failed after create", server.name, exc_info=True
        )

    return _decrypt_and_public(service, server)


@router.put(
    "/{server_id}",
    response_model=MCPServerPublic,
    operation_id="update_mcp_server",
    dependencies=[Depends(RoleChecker(required_permission="mcp-server-update"))],
)
async def update_server(
    server_id: UUID,
    server_in: MCPServerUpdate,
    service: MCPServerService = Depends(get_mcp_server_service),
) -> MCPServerPublic:
    """Update an MCP server configuration."""
    try:
        server = await service.update_server(server_id, server_in)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Refresh MCP client manager if config or is_active was part of the update
    update_data = server_in.model_dump(exclude_unset=True)
    needs_remove = "is_active" in update_data and not server.is_active
    needs_refresh = "config" in update_data or (
        "is_active" in update_data and server.is_active
    )
    if needs_remove or needs_refresh:
        mcp_manager = MCPClientManager()
        if needs_remove:
            await mcp_manager.remove_server(server.name)
        if needs_refresh:
            decrypted = service.decrypt_config(server.config)
            try:
                await mcp_manager.refresh_server(server.name, decrypted)
            except Exception:
                logger.warning(
                    "MCP server '%s' connection failed after update",
                    server.name,
                    exc_info=True,
                )

    return _decrypt_and_public(service, server)


@router.delete(
    "/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_mcp_server",
    dependencies=[Depends(RoleChecker(required_permission="mcp-server-delete"))],
)
async def delete_server(
    server_id: UUID,
    service: MCPServerService = Depends(get_mcp_server_service),
) -> None:
    """Delete an MCP server configuration."""
    try:
        server = await service.get_server(server_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Notify MCP client manager before deleting
    mcp_manager = MCPClientManager()
    await mcp_manager.remove_server(server.name)

    await service.delete_server(server_id)


@router.post(
    "/{server_id}/test",
    response_model=list[MCPToolInfo],
    operation_id="test_mcp_server_connection",
    dependencies=[Depends(RoleChecker(required_permission="mcp-server-update"))],
)
async def test_server_connection(
    server_id: UUID,
    service: MCPServerService = Depends(get_mcp_server_service),
) -> list[MCPToolInfo]:
    """Test connection to an MCP server and return discovered tools."""
    try:
        server = await service.get_server(server_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    decrypted = service.decrypt_config(server.config)
    mcp_manager = MCPClientManager()
    tools = await mcp_manager.test_connection(decrypted)
    return [MCPToolInfo.model_validate(t) for t in tools]


@router.get(
    "/{server_id}/tools",
    response_model=list[MCPToolInfo],
    operation_id="get_mcp_server_tools",
    dependencies=[Depends(RoleChecker(required_permission="mcp-server-read"))],
)
async def get_server_tools(
    server_id: UUID,
    service: MCPServerService = Depends(get_mcp_server_service),
) -> list[MCPToolInfo]:
    """Get cached tools for an MCP server."""
    try:
        server = await service.get_server(server_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    mcp_manager = MCPClientManager()
    server_tools = [
        t
        for t in mcp_manager.get_all_tools()
        if mcp_manager._is_server_tool(t, server.name)
    ]
    return [
        MCPToolInfo(name=t.name, description=t.description or "") for t in server_tools
    ]
