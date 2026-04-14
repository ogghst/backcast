# Analysis: AI Chat Session Context System

**Created:** 2026-04-13
**Request:** Implement context-aware AI chat sessions with flexible context types (general, project, wbe, cost_element)

---

## Clarified Requirements

Based on the feature request and existing codebase analysis, the requirements are:

### Functional Requirements

1. **Session Context Field**: AI chat sessions must have a `context` field to track their scope/type
2. **Context-Aware Filtering**: Session list component must filter sessions by context
3. **Navigation Context Assignment**:
   - Main navigation AI chat → `"general"` context
   - Project AI chat → `project_id` as context
   - Future: WBE chat → `wbe_id` as context
   - Future: Cost element chat → `cost_element_id` as context
4. **Flexible Architecture**: System must support multiple context types extensible in the future
5. **Agent Integration**: Context should be passed to the main agent system prompt for contextual awareness

### Non-Functional Requirements

- **Type Safety**: Strong typing for context values (TypeScript frontend, Python backend)
- **Performance**: Efficient filtering/querying of sessions by context
- **Maintainability**: Easy to add new context types without major refactoring
- **Backward Compatibility**: Existing sessions without context should default to "general"

### Constraints

- **SimpleEntityBase Pattern**: AI chat entities use `SimpleEntityBase` (non-versioned, no EVCS)
- **Existing Schema**: `project_id` and `branch_id` already exist in `AIConversationSession`
- **Single-Server Deployment**: In-memory event bus, no Redis
- **Database**: PostgreSQL 15+ with UUID support

---

## Context Discovery

### Product Scope

From `docs/01-product-scope/` and memory:
- AI chat system supports general assistance and project-specific queries
- Users navigate AI chat from main nav (`/chat`) and project detail (`/projects/:projectId/chat`)
- Deep Agent orchestrator uses subagents with tool-based context injection
- Project members have role-based permissions (PROJECT_ADMIN, PROJECT_MANAGER, etc.)

### Architecture Context

**Bounded Contexts:**
- AI Integration (`app/ai/`): LangGraph agents, tools, WebSocket streaming
- Chat Session Management (`app/api/routes/ai_chat.py`): Session CRUD, message handling
- Project Management (`app/models/domain/project.py`): Project context for sessions

**Existing Patterns:**
- `SimpleEntityBase` for AI entities (non-versioned)
- `TemporalBase` for versioned entities (not used for AI chat)
- RBAC via `RoleChecker` middleware
- TanStack Query for frontend state management
- Zustand for client-side state

**Architectural Constraints:**
- AI chat uses WebSocket for streaming (`/api/v1/ai/chat/stream`)
- Sessions support `project_id` and `branch_id` (already migrated in `20260320_phase3e_session_context.py`)
- Agent system prompt is in `DEFAULT_SYSTEM_PROMPT` constant

### Codebase Analysis

**Backend:**

- **Existing APIs:**
  - `GET /api/v1/ai/chat/sessions` - List all sessions (no filtering)
  - `GET /api/v1/ai/chat/sessions/paginated` - Paginated sessions (no context filter)
  - `POST /api/v1/ai/chat/sessions` - Create session (has `project_id`, `branch_id`)
  - `WebSocket /api/v1/ai/chat/stream` - Chat with session context

- **Data Models** (`app/models/domain/ai.py`):
  ```python
  class AIConversationSession(SimpleEntityBase):
      user_id: Mapped[str]
      assistant_config_id: Mapped[str]
      title: Mapped[str | None]
      project_id: Mapped[str | None]  # Already exists
      branch_id: Mapped[str | None]   # Already exists
      # MISSING: context field to distinguish session types
  ```

- **Schemas** (`app/models/schemas/ai.py`):
  - `AIConversationSessionPublic` - Response model (no context field)
  - `AIConversationSessionCreate` - Create model (no context field)
  - `WSChatRequest` - WebSocket request (has `project_id`, `branch_id`)

- **Agent Service** (`app/ai/agent_service.py`):
  - `DEFAULT_SYSTEM_PROMPT` - Static system prompt
  - `start_execution()` - Accepts `project_id`, `branch_id` parameters
  - Tool creation uses `create_project_tools(project_id)` for project-scoped tools

- **Service Layer** (`app/services/ai_config_service.py`):
  - `list_sessions()` - No filtering by context
  - `create_session()` - No context parameter
  - `list_sessions_paginated()` - No context filtering

**Frontend:**

- **Components:**
  - `ChatInterfacePage` (`/pages/chat/ChatInterface`) - Main AI chat UI
  - `ProjectChat` (`/pages/projects/ProjectChat`) - Project-specific chat
  - `useChatSessions` hook - Fetches all sessions (no filtering)

- **Types** (`features/ai/chat/types.ts`):
  - `WSChatRequest` - Has `project_id` but no context field
  - No session context type definitions

- **Routing** (`src/routes/index.tsx`):
  ```typescript
  { path: "/chat", element: <ChatInterfacePage /> }  // General chat
  { path: "/projects/:projectId", children: [
    { path: "chat", element: <ProjectChat /> }  // Project chat
  ]}
  ```

**Key Findings:**

1. ✅ `project_id` and `branch_id` already exist in database (migration `20260320_phase3e_session_context.py`)
2. ❌ No `context` field to distinguish session types (general vs project vs wbe vs cost_element)
3. ❌ No session filtering by context in API or frontend
4. ❌ Agent system prompt doesn't adapt based on session context
5. ❌ Frontend routes don't pass context hints to chat interface

---

## Solution Options

### Option 1: String-Based Context Field (Simple & Flexible)

**Architecture & Design:**

Add a nullable `context` string column to `AIConversationSession` table:
- `context` values: `"general"`, `"project"`, `"wbe"`, `"cost_element"`
- Use existing `project_id`, `branch_id` columns for context-specific IDs
- Add composite index on `(user_id, context)` for efficient filtering

**UX Design:**

- **General Chat** (`/chat`): Auto-set `context="general"` on new sessions
- **Project Chat** (`/projects/:projectId/chat`): Auto-set `context="project"` + `project_id`
- **Session List**: Filter by context via dropdown/tabs (All | General | Projects | WBEs | Cost Elements)
- **Context Indicators**: Show icon/badge in session list indicating context type

**Implementation:**

- **Backend:**
  - Migration: Add `context` column (VARCHAR(50), nullable, default `"general"`)
  - Update `AIConversationSession` model with `context` field
  - Update schemas (`AIConversationSessionPublic`, `AIConversationSessionCreate`)
  - Add `context` parameter to `create_session()` and `list_sessions()`
  - Update `WSChatRequest` to include `context` field
  - Modify agent system prompt to include context info (e.g., "You are in a project-specific chat")

- **Frontend:**
  - Add `context` field to TypeScript types
  - Update `useChatSessions` to accept optional `context` filter parameter
  - Add context filter UI to session list (tabs or dropdown)
  - Auto-set context based on route (`/chat` → `"general"`, `/projects/:id/chat` → `"project"`)
  - Pass context in WebSocket `WSChatRequest`

**Trade-offs:**

| Aspect          | Assessment                        |
| --------------- | --------------------------------- |
| Pros            | Simple, flexible, easy to extend  |
| Cons            | No referential integrity, manual validation required |
| Complexity      | Low                               |
| Maintainability | Good                              |
| Performance     | Good (composite index on user+context) |

---

### Option 2: Context Table with Foreign Keys (Structured & Validated)

**Architecture & Design:**

Create a new `ai_session_contexts` table:
```python
class AISessionContext(SimpleEntityBase):
    context_type: Mapped[str]  # "general", "project", "wbe", "cost_element"
    entity_id: Mapped[str | None]  # UUID for project/wbe/cost_element
    display_name: Mapped[str]  # Human-readable name
```

Add `context_id` foreign key to `AIConversationSession`.

**UX Design:**

Same as Option 1, but context is managed via dedicated table with UI for context administration.

**Implementation:**

- **Backend:**
  - Create `AISessionContext` model and table
  - Add `context_id` FK to `AIConversationSession`
  - Create CRUD API for context management
  - Update session creation to reference context
  - Default context row for "general" (no entity_id)

- **Frontend:**
  - Similar to Option 1, but fetch context from dedicated endpoint
  - Admin UI for managing contexts (future enhancement)

**Trade-offs:**

| Aspect          | Assessment                        |
| --------------- | --------------------------------- |
| Pros            | Referential integrity, audit trail, extensible metadata |
| Cons            | More complex, additional table/join, over-engineering for current needs |
| Complexity      | Medium-High                       |
| Maintainability | Good                              |
| Performance     | Good (foreign key index)          |

---

### Option 3: Hybrid: Enum-Style Context with Nullable Entity Columns

**Architecture & Design:**

Add `context_type` enum column to `AIConversationSession`:
- `context_type`: ENUM("general", "project", "wbe", "cost_element")
- Reuse existing `project_id`, `branch_id` columns
- Add `wbe_id` and `cost_element_id` columns (nullable, indexed)

**UX Design:**

Same as Option 1, but with explicit columns for each context type (better query performance).

**Implementation:**

- **Backend:**
  - Migration: Add `context_type` ENUM column + `wbe_id`, `cost_element_id` columns
  - Update model with all context ID fields
  - Business logic validation: If `context_type="project"`, require `project_id`
  - Agent uses `context_type` to determine which entity to fetch

- **Frontend:**
  - Similar to Option 1, but with explicit columns
  - Route-based context auto-detection

**Trade-offs:**

| Aspect          | Assessment                        |
| --------------- | --------------------------------- |
| Pros            | Strong typing, clear semantics, optimized queries |
| Cons            | Schema changes for each new context type, nullable columns sprawl |
| Complexity      | Medium                            |
| Maintainability | Fair (needs migration per context) |
| Performance     | Excellent (direct column access)  |

---

## Comparison Summary

| Criteria           | Option 1 (String) | Option 2 (Context Table) | Option 3 (Hybrid Enum) |
| ------------------ | ----------------- | ------------------------ | ---------------------- |
| Development Effort | 2-3 days          | 4-5 days                 | 3-4 days               |
| UX Quality         | Good              | Good                     | Good                   |
| Flexibility        | Excellent         | Excellent                | Fair (migration needed) |
| Type Safety        | Runtime           | Compile-time + Runtime   | Compile-time + Runtime |
| Query Performance  | Good              | Good (join)              | Excellent              |
| Best For           | Rapid iteration, evolving requirements | Enterprise with audit requirements | Stable context types |

---

## Recommendation

**I recommend Option 1 (String-Based Context Field)** because:

1. **Immediate Value**: Fastest to implement, solves the core problem
2. **Flexibility**: Easy to add new context types without migration
3. **Simplicity**: Aligns with existing `SimpleEntityBase` pattern
4. **Future-Proof**: Can migrate to Option 2 or 3 if context management becomes complex
5. **Adequate Validation**: Application-level validation is sufficient for 4-5 context types

**Alternative consideration**: Choose Option 3 (Hybrid Enum) if context types are expected to be stable (no frequent additions) and query performance is critical (e.g., 1000+ sessions per user).

---

## Decision Questions

1. **Context Type Stability**: Do you expect context types to change frequently (e.g., adding "department", "user" contexts)? If yes, Option 1 is better.
2. **Query Performance**: Do you anticipate users having 1000+ sessions? If yes, Option 3's direct column access may be beneficial.
3. **Admin Requirements**: Do admins need to manage/edit contexts via UI? If yes, Option 2 provides a natural administration interface.
4. **Migration Tolerance**: Are you comfortable requiring a database migration for each new context type? If no, Option 1 avoids this.

---

## References

- **Architecture Docs:**
  - `docs/02-architecture/backend/coding-standards.md` - Type safety, validation patterns
  - `docs/02-architecture/01-bounded-contexts.md` - AI Integration bounded context

- **Existing Code:**
  - `backend/app/models/domain/ai.py` - AIConversationSession model
  - `backend/app/models/schemas/ai.py` - Session schemas
  - `backend/app/api/routes/ai_chat.py` - Session endpoints
  - `backend/alembic/versions/20260320_phase3e_session_context.py` - Existing context migration
  - `frontend/src/features/ai/chat/types.ts` - WebSocket types
  - `frontend/src/routes/index.tsx` - Routing structure

- **Related Memory:**
  - `01-ai-chat-implementation.md` - Event bus, WebSocket protocol
  - `08-multimodal-ai-io.md` - Attachments, multimodal support
