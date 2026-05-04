"""MCP Server Configuration Service.

CRUD operations for MCP server configurations with Fernet encryption
for sensitive values stored within the config JSONB column.
"""

import base64
import copy
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

    Encrypts sensitive values (API keys, tokens, passwords) inside the
    config JSONB column before persisting.  Returned MCPServer objects
    always contain encrypted config; use ``get_decrypted_config`` to
    retrieve the plaintext version.
    """

    SENSITIVE_KEYS = {"api_key", "authorization", "token", "secret", "password"}

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

    def _encrypt_value(self, value: str) -> str:
        """Encrypt a sensitive value."""
        return self._get_fernet().encrypt(value.encode()).decode()

    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a sensitive value."""
        try:
            return self._get_fernet().decrypt(encrypted_value.encode()).decode()
        except InvalidToken as e:
            raise ValueError(
                "MCP server config value cannot be decrypted -- it was encrypted "
                "with a different SECRET_KEY. Re-enter the configuration."
            ) from e

    def _is_sensitive_key(self, key: str) -> bool:
        """Check whether a dict key refers to a sensitive value."""
        return any(s in key.lower() for s in self.SENSITIVE_KEYS)

    def _encrypt_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Encrypt sensitive values within a config dict (deep copy).

        Scans ``env`` and ``headers`` sub-dicts for keys matching
        :attr:`SENSITIVE_KEYS` and encrypts their values in-place.
        """
        encrypted = copy.deepcopy(config)

        for section in ("env", "headers"):
            section_dict = encrypted.get(section)
            if not section_dict or not isinstance(section_dict, dict):
                continue
            for key, value in section_dict.items():
                if self._is_sensitive_key(key) and isinstance(value, str):
                    section_dict[key] = self._encrypt_value(value)

        return encrypted

    def _decrypt_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Decrypt sensitive values within a config dict (deep copy)."""
        decrypted = copy.deepcopy(config)

        for section in ("env", "headers"):
            section_dict = decrypted.get(section)
            if not section_dict or not isinstance(section_dict, dict):
                continue
            for key, value in section_dict.items():
                if self._is_sensitive_key(key) and isinstance(value, str):
                    section_dict[key] = self._decrypt_value(value)

        return decrypted

    # ── CRUD Operations ─────────────────────────────────────────────

    async def list_servers(self, *, active_only: bool = False) -> list[MCPServer]:
        """List MCP server configurations.

        Args:
            active_only: When True, return only servers where is_active is True.

        Returns:
            List of MCPServer objects (config contains encrypted values).
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

        Sensitive values inside ``config.env`` and ``config.headers`` are
        encrypted before persisting.
        """
        encrypted_config = self._encrypt_config(data.config)

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
        When ``config`` is provided, sensitive values are encrypted before
        persisting.
        """
        server = await self.session.get(MCPServer, server_id)
        if not server:
            raise ValueError(f"MCP server {server_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        # Encrypt config if it is being updated
        if "config" in update_data and update_data["config"] is not None:
            update_data["config"] = self._encrypt_config(update_data["config"])

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

    async def get_decrypted_config(self, server_id: UUID) -> dict[str, Any]:
        """Return the fully decrypted config dict for a server.

        This is the method callers should use when they need the actual
        connection parameters (e.g. to initialise an MCP client).
        """
        server = await self.get_server(server_id)
        return self._decrypt_config(server.config)
