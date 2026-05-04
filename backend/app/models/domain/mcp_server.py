"""MCPServer domain model - non-versioned entity.

Stores configurations for MCP (Model Context Protocol) servers that
provide external tools to AI agents. Satisfies SimpleEntityProtocol
via SimpleEntityBase.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class MCPServer(SimpleEntityBase):
    """MCP Server configuration for external tool integration.

    Non-versioned entity storing connection details and configuration
    for MCP servers that expose tools to the AI agent system.

    Attributes:
        id: UUID primary key.
        name: Human-readable server name (unique).
        config: JSONB with server connection parameters (transport,
                URL, headers, etc.).
        is_active: Whether this server is currently enabled.
    """

    __tablename__ = "mcp_servers"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    def __repr__(self) -> str:
        return f"<MCPServer(id={self.id}, name={self.name!r}, is_active={self.is_active})>"
