"""MCP Server Configuration Service.

CRUD operations for MCP server configurations with Fernet encryption
for the entire config blob stored in the config TEXT column.
"""

import base64
import json
import logging
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.domain.mcp_server import MCPServer
from app.models.schemas.mcp_server import MCPServerCreate, MCPServerUpdate

logger = logging.getLogger(__name__)


class MCPServerService:
    """Service for managing MCP server configurations.

    Encrypts the entire config dict as a single Fernet-encrypted blob
    before persisting.  Returned MCPServer objects always contain the
    encrypted blob; use ``decrypt_config`` to retrieve the plaintext dict.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._fernet: Fernet | None = None

    # ── Encryption helpers ──────────────────────────────────────────

    def _get_fernet(self) -> Fernet:
        """Get Fernet instance for encryption."""
        if self._fernet is None:
            secret_key = settings.SECRET_KEY
            key = base64.urlsafe_b64encode(secret_key.encode()[:32].ljust(32, b"0"))
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt_config(self, config: dict[str, Any]) -> str:
        """Encrypt a full config dict into a Fernet blob."""
        plaintext = json.dumps(config)
        return self._get_fernet().encrypt(plaintext.encode()).decode()

    def decrypt_config(self, config: str) -> dict[str, Any]:
        """Decrypt a Fernet blob back into a config dict."""
        try:
            plaintext = self._get_fernet().decrypt(config.encode()).decode()
            return json.loads(plaintext)
        except InvalidToken as e:
            raise ValueError(
                "MCP server config cannot be decrypted -- it was encrypted "
                "with a different SECRET_KEY. Re-enter the configuration."
            ) from e

    # ── CRUD Operations ─────────────────────────────────────────────

    async def list_servers(self, *, active_only: bool = False) -> list[MCPServer]:
        """List MCP server configurations.

        Args:
            active_only: When True, return only servers where is_active is True.

        Returns:
            List of MCPServer objects (config contains encrypted blob).
        """
        stmt = select(MCPServer).order_by(MCPServer.name)
        if active_only:
            stmt = stmt.where(MCPServer.is_active)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_server(self, server_id: UUID) -> MCPServer:
        """Get a single MCP server by ID.

        Raises:
            ValueError: If the server is not found.
        """
        stmt = select(MCPServer).where(MCPServer.id == server_id)
        result = await self.session.execute(stmt)
        server = result.scalar_one_or_none()
        if not server:
            raise ValueError(f"MCP server {server_id} not found")
        return server

    async def create_server(self, data: MCPServerCreate) -> MCPServer:
        """Create a new MCP server configuration.

        The entire config dict is encrypted before persisting.
        """
        encrypted_config = self.encrypt_config(data.config)

        server = MCPServer(
            name=data.name,
            config=encrypted_config,
            is_active=data.is_active,
        )
        self.session.add(server)
        await self.session.flush()

        # Fetch fresh copy to get server-generated values (id, timestamps)
        stmt = select(MCPServer).where(MCPServer.id == server.id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_server(self, server_id: UUID, data: MCPServerUpdate) -> MCPServer:
        """Update an MCP server configuration.

        Only fields explicitly present in the request are modified.
        When ``config`` is provided, the entire dict is encrypted before
        persisting.
        """
        server = await self.session.get(MCPServer, server_id)
        if not server:
            raise ValueError(f"MCP server {server_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        # Encrypt config if it is being updated
        if "config" in update_data and update_data["config"] is not None:
            update_data["config"] = self.encrypt_config(update_data["config"])

        for key, value in update_data.items():
            setattr(server, key, value)

        await self.session.flush()

        # Fetch fresh copy to get server-generated values (updated_at)
        stmt = select(MCPServer).where(MCPServer.id == server_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_server(self, server_id: UUID) -> None:
        """Delete an MCP server configuration.

        Raises:
            ValueError: If the server is not found.
        """
        server = await self.get_server(server_id)
        await self.session.delete(server)
