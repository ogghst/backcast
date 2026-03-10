"""Pydantic schemas for AI integration.

Provides schemas for:
- AIProvider: Provider definitions
- AIProviderConfig: Key-value config for- AIModel: Available models
- AIAssistantConfig: Assistant configuration
- AIConversationSession: Conversation sessions
- AIConversationMessage: Messages
- AIChatResponse: Chat response (for non-streaming operations)
- WebSocket messages: Streaming chat protocol
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Provider Types
PROVIDER_TYPE_OPENAI = "openai"
PROVIDER_TYPE_AZURE = "azure"
PROVIDER_TYPE_OLLAMA = "ollama"

# Message Roles
MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"
MESSAGE_ROLE_TOOL = "tool"


# === Provider Schemas ===


class AIProviderBase(BaseModel):
    """Base schema for AI provider."""

    provider_type: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    base_url: str | None = Field(None, max_length=500)
    is_active: bool = Field(True)


class AIProviderCreate(AIProviderBase):
    """Schema for creating an AI provider."""

    pass


class AIProviderUpdate(BaseModel):
    """Schema for updating an AI provider."""

    provider_type: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=255)
    base_url: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class AIProviderPublic(BaseModel):
    """Schema for reading AI provider (sensitive data masked)."""

    id: UUID
    provider_type: str
    name: str
    base_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === Provider Config Schemas ===


class AIProviderConfigBase(BaseModel):
    """Base schema for provider config."""

    key: str = Field(..., max_length=100)
    value: str | None = None
    is_encrypted: bool = Field(False)


class AIProviderConfigCreate(AIProviderConfigBase):
    """Schema for creating a provider config."""

    pass


class AIProviderConfigUpdate(BaseModel):
    """Schema for updating a provider config."""

    value: str | None = None
    is_encrypted: bool | None = None


class AIProviderConfigPublic(BaseModel):
    """Schema for reading provider config (values masked if encrypted)."""

    id: UUID
    provider_id: UUID
    key: str
    value: str | None = Field(None, description="***MASKED***")
    is_encrypted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='after')
    @classmethod
    def mask_encrypted_value(cls, model: Any) -> Any:
        """Mask encrypted values."""
        if model.is_encrypted and model.value:
            # Check if value looks like encrypted data (long base64 string)
            # Fernet encrypted values are base64 and typically 100+ chars
            if len(model.value) > 50:
                # Create a new model with masked value
                model.value = "***MASKED***"
        return model


# === Model Schemas ===


class AIModelBase(BaseModel):
    """Base schema for AI model."""

    model_id: str = Field(..., max_length=100)
    display_name: str = Field(..., max_length=255)
    is_active: bool = Field(True)


class AIModelCreate(AIModelBase):
    """Schema for creating an AI model.

    When creating via API endpoint, provider_id comes from the URL path
    parameter and is injected by the route handler.
    """

    provider_id: UUID | None = Field(None, description="Provider ID (injected from path)")


class AIModelUpdate(BaseModel):
    """Schema for updating an AI model."""

    model_id: str | None = Field(None, max_length=100)
    display_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class AIModelPublic(AIModelBase):
    """Schema for reading AI model."""

    id: UUID
    provider_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === Assistant Config Schemas ===


class AIAssistantConfigBase(BaseModel):
    """Base schema for assistant config."""

    name: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=2000)
    model_id: UUID
    system_prompt: str | None = Field(None, max_length=10000)
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=1, le=32000)
    allowed_tools: list[str] | None = Field(
        None, description="List of tool names this assistant can use"
    )
    is_active: bool = Field(True)


class AIAssistantConfigCreate(AIAssistantConfigBase):
    """Schema for creating an assistant config."""

    pass


class AIAssistantConfigUpdate(BaseModel):
    """Schema for updating an assistant config."""

    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)
    system_prompt: str | None = Field(None, max_length=10000)
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=1, le=32000)
    allowed_tools: list[str] | None = None
    model_id: UUID | None = None
    is_active: bool | None = None


class AIAssistantConfigPublic(AIAssistantConfigBase):
    """Schema for reading assistant config."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === Conversation Session Schemas ===


class AIConversationSessionPublic(BaseModel):
    """Schema for reading conversation session."""

    id: UUID
    user_id: UUID
    assistant_config_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIConversationSessionCreate(BaseModel):
    """Schema for creating a conversation session."""

    assistant_config_id: UUID
    title: str | None = Field(None, max_length=255)


# === Conversation Message Schemas ===


class AIConversationMessagePublic(BaseModel):
    """Schema for reading conversation message."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_results: list[dict[str, Any]] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === Chat Response Schema ===


class AIChatResponse(BaseModel):
    """Schema for chat response."""

    session_id: UUID
    message: AIConversationMessagePublic
    tool_calls: list[dict[str, Any]] | None = None


# === WebSocket Message Schemas ===


class WSChatRequest(BaseModel):
    """WebSocket chat message from client.

    Client -> Server message format for initiating chat sessions.
    """

    type: str = Field(default="chat", description="Message type discriminator")
    message: str = Field(..., min_length=1, max_length=10000, description="User message content")
    session_id: UUID | None = Field(None, description="Existing session ID or None for new session")
    assistant_config_id: UUID | None = Field(
        None, description="Assistant config to use (required for new sessions)"
    )


class WSTokenMessage(BaseModel):
    """WebSocket token streaming message from server.

    Server -> Client message for streaming response tokens.
    """

    type: str = Field(default="token", description="Message type discriminator")
    content: str = Field(..., description="Partial text token")
    session_id: UUID = Field(..., description="Session identifier")


class WSToolCallMessage(BaseModel):
    """WebSocket tool call notification from server.

    Server -> Client message indicating a tool is being called.
    """

    type: str = Field(default="tool_call", description="Message type discriminator")
    tool: str = Field(..., description="Tool function name being called")
    args: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class WSToolResultMessage(BaseModel):
    """WebSocket tool result message from server.

    Server -> Client message with tool execution results.
    """

    type: str = Field(default="tool_result", description="Message type discriminator")
    tool: str = Field(..., description="Tool function name")
    result: dict[str, Any] = Field(..., description="Tool execution result data")


class WSCompleteMessage(BaseModel):
    """WebSocket completion message from server.

    Server -> Client message indicating response generation is complete.
    """

    type: str = Field(default="complete", description="Message type discriminator")
    session_id: UUID = Field(..., description="Session identifier")
    message_id: UUID = Field(..., description="Complete message identifier")


class WSErrorMessage(BaseModel):
    """WebSocket error message from server.

    Server -> Client message for error reporting during streaming.
    """

    type: str = Field(default="error", description="Message type discriminator")
    message: str = Field(..., description="Error details")
    code: int | None = Field(None, description="Optional error code")


# Union type for all server->client WebSocket messages
WSMessage = (
    WSTokenMessage | WSToolCallMessage | WSToolResultMessage | WSCompleteMessage | WSErrorMessage
)
