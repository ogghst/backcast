"""Pydantic schemas for MCP server configuration.

Provides schemas for:
- MCPServerConfigBase: Transport-agnostic config base
- StdioConfig / HttpConfig: Transport-specific config validation
- MCPServerCreate: Create MCP server entries
- MCPServerUpdate: Update MCP server entries
- MCPServerPublic: Read MCP server entries
- MCPToolInfo: Discovered tool metadata
"""

from datetime import datetime
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# --- JSON Config Validation ---


class MCPServerConfigBase(BaseModel):
    """Base config for MCP server connection."""

    transport: Literal["stdio", "sse", "streamable-http", "websocket"]
    env: dict[str, str] | None = None
    headers: dict[str, str] | None = None


class StdioConfig(MCPServerConfigBase):
    """Config for stdio-based MCP servers."""

    transport: Literal["stdio"] = "stdio"
    command: str
    args: list[str] = []


class HttpConfig(MCPServerConfigBase):
    """Config for HTTP/SSE/WS-based MCP servers."""

    transport: Literal["sse", "streamable-http", "websocket"]
    url: str


MCPConfig = StdioConfig | HttpConfig


# --- CRUD Schemas ---


class MCPServerCreate(BaseModel):
    """Schema for creating an MCP server."""

    name: str = Field(..., min_length=1, max_length=255)
    config: dict[str, Any]
    is_active: bool = True

    @model_validator(mode="after")
    def validate_config(self) -> Self:
        """Validate config matches transport type."""
        transport = self.config.get("transport", "stdio")
        if transport == "stdio":
            if "command" not in self.config:
                raise ValueError("stdio transport requires 'command' field")
        elif transport in ("sse", "streamable-http", "websocket"):
            if "url" not in self.config:
                raise ValueError(f"{transport} transport requires 'url' field")
        return self


class MCPServerUpdate(BaseModel):
    """Schema for updating an MCP server."""

    name: str | None = Field(None, min_length=1, max_length=255)
    config: dict[str, Any] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_config(self) -> Self:
        """Validate config matches transport type when provided."""
        if self.config is not None:
            transport = self.config.get("transport", "stdio")
            if transport == "stdio":
                if "command" not in self.config:
                    raise ValueError("stdio transport requires 'command' field")
            elif transport in ("sse", "streamable-http", "websocket"):
                if "url" not in self.config:
                    raise ValueError(f"{transport} transport requires 'url' field")
        return self


class MCPServerPublic(BaseModel):
    """Schema for reading MCP server (config shown as-is, no masking needed)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    config: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MCPToolInfo(BaseModel):
    """Schema for a discovered MCP tool."""

    name: str
    description: str
