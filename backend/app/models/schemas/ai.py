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
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Risk level literals
RISK_LEVEL_LOW = "low"
RISK_LEVEL_HIGH = "high"
RISK_LEVEL_CRITICAL = "critical"
RISK_LEVEL_VALUES = [RISK_LEVEL_LOW, RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL]

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
    def mask_encrypted_value(self) -> Self:
        """Mask encrypted values."""
        if self.is_encrypted and self.value:
            # Check if value looks like encrypted data (long base64 string)
            # Fernet encrypted values are base64 and typically 100+ chars
            if len(self.value) > 50:
                # Create a new model with masked value
                self.value = "***MASKED***"
        return self


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
    max_tokens: int | None = Field(None, ge=1, le=200000)
    recursion_limit: int | None = Field(None, ge=1, le=500, description="LangGraph recursion limit (maximum steps in agent execution loop)")
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
    max_tokens: int | None = Field(None, ge=1, le=200000)
    recursion_limit: int | None = Field(None, ge=1, le=500)
    allowed_tools: list[str] | None = None
    model_id: UUID | None = None
    is_active: bool | None = None


class AIAssistantConfigPublic(AIAssistantConfigBase):
    """Schema for reading assistant config."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIToolPublic(BaseModel):
    """Schema for returning AI tool metadata."""

    name: str
    description: str
    permissions: list[str]
    category: str | None = None
    version: str

    model_config = ConfigDict(from_attributes=True)


# === Conversation Session Schemas ===


class AIConversationSessionPublic(BaseModel):
    """Schema for reading conversation session."""

    id: UUID
    user_id: UUID
    assistant_config_id: UUID
    title: str | None
    project_id: UUID | None = Field(None, description="Optional project context")
    branch_id: UUID | None = Field(None, description="Optional branch or change order context")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIConversationSessionCreate(BaseModel):
    """Schema for creating a conversation session."""

    assistant_config_id: UUID
    title: str | None = Field(None, max_length=255)
    project_id: UUID | None = Field(None, description="Optional project context")
    branch_id: UUID | None = Field(None, description="Optional branch or change order context")


# === Conversation Message Schemas ===


class FileAttachment(BaseModel):
    """Schema for file attachments in chat messages."""

    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., max_length=255, description="Original filename")
    file_type: str = Field(..., max_length=100, description="MIME type or file extension")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    url: str = Field(..., max_length=500, description="URL to access the file")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


class AIConversationMessagePublic(BaseModel):
    """Schema for reading conversation message."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    content_format: Literal["text", "markdown", "mermaid", "code"] = Field(
        default="text", description="Format of the content"
    )
    tool_calls: list[dict[str, Any]] | None = None
    tool_results: list[dict[str, Any]] | None = None
    attachments: list[FileAttachment] = Field(
        default_factory=list, description="File attachments"
    )
    images: list[str] = Field(
        default_factory=list, description="Image URLs"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional message metadata"
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def ignore_sqlalchemy_metadata(cls, data: Any) -> Any:
        """Ignore SQLAlchemy's built-in metadata attribute during validation.

        SQLAlchemy models have a built-in `metadata` attribute (MetaData object)
        that conflicts with our schema's metadata field (dict). This validator
        handles the conflict by using the message_metadata field instead.
        """
        # Handle dict input (e.g., from API requests)
        if isinstance(data, dict):
            # Ensure metadata is a dict, not SQLAlchemy's MetaData
            if 'metadata' in data and not isinstance(data.get('metadata'), dict):
                data = dict(data)  # Make a copy
                data['metadata'] = {}
            return data

        # Handle SQLAlchemy model input (from_attributes=True)
        if hasattr(data, '__table__'):
            # Create a dict copy, using message_metadata if available
            result: dict[str, Any] = {}
            for key in cls.model_fields:
                if key == 'metadata':
                    # Use message_metadata from the database model
                    result[key] = getattr(data, 'message_metadata', None) or {}
                elif hasattr(data, key):
                    value = getattr(data, key)
                    result[key] = value
            return result

        return data


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
    title: str | None = Field(None, max_length=255, description="Optional session title (for new sessions)")
    project_id: UUID | None = Field(None, description="Optional project context for the session")
    branch_id: UUID | None = Field(None, description="Optional branch or change order context for the session")
    as_of: datetime | None = Field(None, description="Optional historical date for temporal queries")
    branch_name: str | None = Field("main", description="Branch name for temporal queries (default: 'main')")
    branch_mode: Literal["merged", "isolated"] | None = Field(
        "merged", description="Branch mode for temporal queries (default: 'merged')"
    )
    execution_mode: Literal["safe", "standard", "expert"] = Field(
        "standard", description="AI tool execution mode (default: 'standard')"
    )
    attachments: list[FileAttachment] = Field(
        default_factory=list, description="File attachments to the message"
    )
    images: list[str] = Field(
        default_factory=list, description="Image URLs included in the message"
    )


class WSTokenMessage(BaseModel):
    """WebSocket token streaming message from server.

    Server -> Client message for streaming response tokens.
    """

    type: str = Field(default="token", description="Message type discriminator")
    content: str = Field(..., description="Partial text token")
    session_id: UUID = Field(..., description="Session identifier")
    source: str = Field(default="main", description="'main' or 'subagent'")
    subagent_name: str | None = Field(
        default=None, description="Subagent name when source='subagent'"
    )
    invocation_id: str | None = Field(
        default=None, description="Unique invocation ID for subagent instance"
    )


class WSTokenBatchMessage(BaseModel):
    """WebSocket batched token streaming message from server.

    Server -> Client message for streaming multiple tokens in a single message.
    Reduces WebSocket message overhead while maintaining streaming UX.

    Tokens are pre-concatenated on the backend for optimal payload size.
    """

    type: str = Field(default="token_batch", description="Message type discriminator")
    tokens: str = Field(..., description="Concatenated token string")
    session_id: UUID = Field(..., description="Session identifier")
    source: str = Field(default="main", description="'main' or 'subagent'")
    subagent_name: str | None = Field(
        default=None, description="Subagent name when source='subagent'"
    )
    invocation_id: str | None = Field(
        default=None, description="Unique invocation ID for subagent instance"
    )


class WSSubagentResultMessage(BaseModel):
    """WebSocket subagent result message from server.

    Sent when a subagent (task tool) completes, containing the subagent's
    final response text for display in the Activity Panel.
    """

    type: str = Field(default="subagent_result", description="Message type discriminator")
    subagent_name: str = Field(..., description="Name of the subagent that completed")
    content: str = Field(..., description="Subagent's final response text")
    invocation_id: str = Field(..., description="Unique invocation ID for this subagent instance")


class WSContentResetMessage(BaseModel):
    """WebSocket content reset message.

    Sent when accumulated streaming content should be reset,
    typically after a subagent completes and the main agent
    begins its synthesis phase.
    """

    type: Literal["content_reset"] = "content_reset"
    reason: str = "subagent_completed"


class WSToolCallMessage(BaseModel):
    """WebSocket tool call notification from server.

    Server -> Client message indicating a tool is being called.
    """

    type: str = Field(default="tool_call", description="Message type discriminator")
    tool: str = Field(..., description="Tool function name being called")
    args: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    step_number: int | None = Field(None, description="Current step number (1-indexed)")
    total_steps: int | None = Field(None, description="Estimated total steps")


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


class WSApprovalRequestMessage(BaseModel):
    """WebSocket approval request message from server.

    Server -> Client message requesting user approval for critical tool execution.
    Sent when a critical tool is about to be executed in standard mode.

    The client should display an approval dialog and send back WSApprovalResponseMessage.
    """

    type: Literal["approval_request"] = Field(
        default="approval_request", description="Message type discriminator"
    )
    approval_id: str = Field(..., description="Unique UUID for this approval request")
    session_id: UUID = Field(..., description="Chat session ID")
    tool_name: str = Field(..., description="Name of the tool requiring approval")
    tool_args: dict[str, Any] = Field(
        default_factory=dict, description="Arguments that will be passed to the tool"
    )
    risk_level: Literal[RISK_LEVEL_LOW, RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL] = Field(
        ..., description="Risk level of the tool requiring approval ('low', 'high', or 'critical')"
    )
    expires_at: datetime = Field(
        ...,
        description="Expiration timestamp (5 minutes from request)",
    )


class WSApprovalResponseMessage(BaseModel):
    """WebSocket approval response message from client.

    Client -> Server message with user's decision on approval request.
    Sent when user clicks "Approve" or "Reject" in the approval dialog.
    """

    type: Literal["approval_response"] = Field(
        default="approval_response", description="Message type discriminator"
    )
    approval_id: str = Field(..., description="Approval ID being responded to")
    approved: bool = Field(..., description="True if user approved, False if rejected")
    user_id: UUID = Field(..., description="User ID making the decision")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Timestamp of the decision"
    )


class WSThinkingMessage(BaseModel):
    """WebSocket thinking message from server.

    Server -> Client message indicating the agent is processing/thinking.
    Useful for showing initial loading state before any tool calls.
    """

    type: Literal["thinking"] = Field(
        default="thinking", description="Message type discriminator"
    )


class WSPlanningMessage(BaseModel):
    """WebSocket planning message from server.

    Server -> Client message indicating the Deep Agent is creating a plan.
    Sent when the agent uses the write_todos tool for task planning.
    """

    type: Literal["planning"] = Field(
        default="planning", description="Message type discriminator"
    )
    plan: str | None = Field(None, description="Plan description")
    steps: list[dict[str, Any]] | None = Field(
        None,
        description="Planning steps with text and done status",
    )
    step_number: int | None = Field(None, description="Current step number (1-indexed)")
    total_steps: int | None = Field(None, description="Total steps in plan")


class WSSubagentMessage(BaseModel):
    """WebSocket subagent delegation message from server.

    Server -> Client message indicating the Deep Agent is delegating to a subagent.
    """

    type: Literal["subagent"] = Field(
        default="subagent", description="Message type discriminator"
    )
    subagent: str = Field(..., description="Subagent name (e.g., 'evm_analyst')")
    message: str | None = Field(
        None, description="Optional description of what the subagent is doing"
    )
    step_number: int | None = Field(None, description="Current step number (1-indexed)")
    total_steps: int | None = Field(None, description="Estimated total steps")
    invocation_id: str = Field(..., description="Unique invocation ID for this subagent instance")


class WSPollingHeartbeatMessage(BaseModel):
    """WebSocket polling heartbeat message from server.

    Server -> Client message sent during approval polling to keep the WebSocket
    connection alive. Prevents connection timeout due to inactivity during the
    30-second polling period.

    Sent every 5 seconds while waiting for user approval response.
    """

    type: Literal["polling_heartbeat"] = Field(
        default="polling_heartbeat", description="Message type discriminator"
    )
    approval_id: str = Field(..., description="Approval ID being polled")
    elapsed_seconds: float = Field(..., description="Time elapsed since approval request (seconds)")
    remaining_seconds: float = Field(..., description="Time remaining until timeout (seconds)")


# Union type for all server->client WebSocket messages
WSMessage = (
    WSTokenMessage
    | WSToolCallMessage
    | WSToolResultMessage
    | WSCompleteMessage
    | WSErrorMessage
    | WSApprovalRequestMessage
    | WSThinkingMessage
    | WSPlanningMessage
    | WSSubagentMessage
)


# === Image Upload Schemas ===


class ImageUploadResponse(BaseModel):
    """Schema for image upload response."""

    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    url: str = Field(..., description="URL to access the uploaded image")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the image")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


# === File Upload Schemas ===


class FileUploadResponse(BaseModel):
    """Schema for file upload response."""

    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    url: str = Field(..., description="URL to access the uploaded file")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the file")
    file_type: str = Field(..., description="Category of file (document, spreadsheet, etc.)")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


# === Mermaid Diagram Schemas ===


class MermaidDiagramRequest(BaseModel):
    """Schema for requesting Mermaid diagram generation."""

    diagram_type: Literal["flowchart", "sequence", "class", "state", "er", "gantt"] = Field(
        ..., description="Type of diagram to generate"
    )
    description: str = Field(
        ..., min_length=1, max_length=5000, description="Natural language description of the diagram"
    )
    title: str | None = Field(None, max_length=255, description="Optional diagram title")
    context: str | None = Field(
        None, max_length=2000, description="Additional context for diagram generation"
    )


class MermaidDiagramResponse(BaseModel):
    """Schema for Mermaid diagram generation response."""

    mermaid_code: str = Field(..., description="Mermaid diagram code")
    diagram_type: str = Field(..., description="Type of diagram generated")
    title: str | None = Field(None, description="Diagram title")
    description: str = Field(..., description="Original description")
    rendered_url: str | None = Field(None, description="URL to render the diagram (if applicable)")

