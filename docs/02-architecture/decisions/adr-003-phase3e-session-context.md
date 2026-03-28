# ADR 003: Phase 3E - Session Context Enhancement

**Status:** Implemented
**Date:** 2026-03-20
**Phase:** 3E - Session Context Enhancement

## Context

AI conversations need project and branch context to provide context-aware assistance. Tools need to know which project and branch the user is working with to provide relevant information and perform scoped operations.

## Decision

Added `project_id` and `branch_id` fields to the `AIConversationSession` model and throughout the AI conversation stack to enable context-aware conversations.

### Changes Made

#### 1. Model Layer (`backend/app/models/domain/ai.py`)

**Added to `AIConversationSession`:**
```python
project_id: Mapped[str | None] = mapped_column(
    PG_UUID, nullable=True, index=True, comment="Optional project context"
)
branch_id: Mapped[str | None] = mapped_column(
    PG_UUID, nullable=True, index=True, comment="Optional branch or change order context"
)
```

**Updated `__repr__`:**
- Now includes project_id and branch_id when present
- Example: `<AIConversationSession(id=..., user_id=..., project_id=..., branch_id=...)>`

#### 2. Database Migration (`backend/alembic/versions/20260320_phase3e_session_context.py`)

**Migration actions:**
- Added `project_id` column (UUID, nullable) with index
- Added `branch_id` column (UUID, nullable) with index
- Both fields are optional for backward compatibility

#### 3. Schema Layer (`backend/app/models/schemas/ai.py`)

**Updated schemas:**
- `AIConversationSessionPublic`: Added `project_id` and `branch_id` fields
- `AIConversationSessionCreate`: Added `project_id` and `branch_id` fields
- `WSChatRequest`: Added `project_id` and `branch_id` fields

#### 4. Service Layer (`backend/app/services/ai_config_service.py`)

**Updated `create_session` method:**
```python
async def create_session(
    self,
    user_id: UUID,
    assistant_config_id: UUID,
    title: str | None = None,
    project_id: UUID | None = None,  # New
    branch_id: UUID | None = None,   # New
) -> AIConversationSession:
```

#### 5. API Layer (`backend/app/api/routes/ai_chat.py`)

**Updated WebSocket endpoint:**
- Now accepts `project_id` and `branch_id` from `WSChatRequest`
- Passes context to `agent_service.chat_stream()`

#### 6. Tool Context (`backend/app/ai/tools/types.py`)

**Updated `ToolContext` dataclass:**
```python
@dataclass
class ToolContext:
    session: AsyncSession
    user_id: str
    user_role: str = "guest"
    project_id: str | None = None  # New
    branch_id: str | None = None   # New
    _permission_cache: dict[str, bool] = field(default_factory=dict)
```

#### 7. Agent Service (`backend/app/ai/agent_service.py`)

**Updated `chat_stream` method:**
- Accepts `project_id` and `branch_id` parameters
- Stores context in session when creating new sessions
- Passes context to `ToolContext` for tool execution

## API Usage

### Starting a Chat with Context

**Client sends:**
```json
{
  "type": "chat",
  "message": "Show me the budget for this project",
  "assistant_config_id": "uuid-of-assistant",
  "project_id": "uuid-of-project",
  "branch_id": "uuid-of-branch-or-change-order"
}
```

**Server creates session with context:**
```python
session = AIConversationSession(
    user_id=user_id,
    assistant_config_id=assistant_config_id,
    project_id=project_id,
    branch_id=branch_id,
)
```

**Tools receive context:**
```python
@ai_tool()
async def get_project_budget(context: ToolContext) -> str:
    """Get budget for the current project context."""
    if not context.project_id:
        return "No project context available"

    # Use context.project_id to query scoped data
    project = await context.project_service.get_by_id(context.project_id)
    return f"Budget: {project.budget}"
```

### Backward Compatibility

**Without context (existing behavior):**
```json
{
  "type": "chat",
  "message": "List all projects",
  "assistant_config_id": "uuid-of-assistant"
}
```

## Benefits

1. **Context-Aware Conversations**: AI can provide project-specific and branch-specific information
2. **Scoped Operations**: Tools can perform operations scoped to the current project/branch
3. **Improved User Experience**: Users don't need to repeatedly specify project/branch context
4. **Backward Compatible**: Existing conversations without context continue to work
5. **Flexible**: Context is optional, supporting both scoped and global conversations

## Implementation Notes

- **Foreign Keys**: No FK constraints added to `projects` or `branches` tables to avoid coupling
- **String Storage**: UUIDs stored as strings for consistency with other fields
- **Indexing**: Both fields have indexes for efficient filtering queries
- **Nullable**: Both fields are optional to support both scoped and unscoped conversations
- **Tool Access**: Tools can access context via `ToolContext.project_id` and `ToolContext.branch_id`

## Testing

All changes verified:
- ✅ Model instantiation with context
- ✅ Schema validation (WSChatRequest, AIConversationSessionPublic)
- ✅ ToolContext with project_id and branch_id
- ✅ Backward compatibility (None values)
- ✅ Database migration applied successfully
- ✅ Ruff linting passes
- ✅ MyPy strict mode passes

## Future Enhancements

1. **Context Validation**: Validate project_id and branch_id exist when provided
2. **Context Switching**: Allow changing context mid-conversation
3. **Context Permissions**: Check user has access to specified project/branch
4. **Context History**: Track context changes in conversation history
5. **Multi-Context**: Support multiple project contexts in one conversation

## References

- `backend/app/models/domain/ai.py` - Model definition
- `backend/app/models/schemas/ai.py` - Schema definitions
- `backend/app/services/ai_config_service.py` - Service layer
- `backend/app/api/routes/ai_chat.py` - API endpoints
- `backend/app/ai/tools/types.py` - Tool context
- `backend/app/ai/agent_service.py` - Agent orchestration
- `backend/alembic/versions/20260320_phase3e_session_context.py` - Migration
