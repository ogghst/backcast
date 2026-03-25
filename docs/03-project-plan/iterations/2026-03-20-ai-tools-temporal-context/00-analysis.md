# Analysis: AI Tools Temporal Context Integration

**Created:** 2026-03-20
**Request:** "AI tools shall consider time machine control date, branch and branch mode on each request. Those parameters shall be configurable only from time machine component."

---

## Clarified Requirements

### Core Requirement

AI tools must respect the temporal context (time machine parameters) set by users through the Time Machine component. These parameters control how AI tools query and interpret data within the EVCS (Entity Versioning Control System).

### Functional Requirements

**FR-1: Temporal Context Propagation**
- AI tools MUST receive and use three temporal parameters on every request:
  - `as_of`: Timestamp for time-travel queries (null = "now")
  - `branch`: Branch name (e.g., "main", "feature-x")
  - `branch_mode`: Query mode ("merged" or "isolated")
- These parameters MUST be sourced from the Time Machine component store
- Parameters MUST be passed through the WebSocket chat request

**FR-2: ToolContext Enhancement**
- `ToolContext` dataclass MUST be extended to include:
  - `as_of: datetime | None`
  - `branch_name: str | None` (branch name, not UUID)
  - `branch_mode: Literal["merged", "isolated"] | None`
- Existing `branch_id` field should be renamed or clarified (see questions below)

**FR-3: AI Tool Behavior**
- All AI tools MUST respect temporal context when querying versioned entities
- Tools MUST pass temporal parameters to service layer methods
- Example: `project_service.get_projects(as_of, branch, branch_mode)`
- Tools MUST provide temporal context in responses to inform users

**FR-4: Single Source of Truth**
- Temporal parameters MUST ONLY be configurable from the Time Machine component
- Chat interface MUST NOT provide direct controls for temporal parameters
- Frontend MUST read from `useTimeMachineStore` and send with each WebSocket message

**FR-5: System Prompt Updates**
- AI system prompt MUST inform the model about active temporal context
- Prompt SHOULD include guidance on mentioning temporal state to users
- Example: "Note: You're viewing data as of Jan 15, 2025 in branch 'feature-x' (isolated mode)"

**FR-6: Validation and Defaults**
- System MUST validate temporal parameters before tool execution
- Defaults MUST be applied when parameters are missing:
  - `as_of`: None (current time)
  - `branch`: "main"
  - `branch_mode`: "merged"
- Invalid branches or future dates MUST return clear error messages

**FR-7: Backward Compatibility**
- Existing tools MUST be updated to use temporal parameters
- Changes MUST maintain backward compatibility for non-versioned entities
- AI chat sessions MUST preserve temporal context in `branch_id` field (current schema)

### Non-Functional Requirements

**NFR-1: Performance**
- Temporal parameter validation MUST NOT add significant latency
- Service layer already supports temporal queries (no performance regression expected)

**NFR-2: Maintainability**
- Changes MUST follow existing EVCS patterns (TemporalService interface)
- Tool updates MUST be consistent and repeatable

**NFR-3: User Experience**
- AI responses MUST be transparent about temporal context
- Users MUST understand when they're viewing historical or branch-isolated data

### Constraints

- **Constraint-1:** Frontend Time Machine component is the ONLY source for temporal parameters
- **Constraint-2:** Existing WebSocket protocol must be extended, not replaced
- **Constraint-3:** Must maintain compatibility with existing AI session schema (has `branch_id`)
- **Constraint-4:** Service layer already supports temporal parameters (no changes needed)

---

## Context Discovery

### Product Scope

Relevant documentation areas:
- **Temporal Query Reference:** `/docs/02-architecture/cross-cutting/temporal-query-reference.md`
  - Defines `as_of`, `branch`, and `branch_mode` semantics
  - Explains "merged" vs "isolated" query behavior
- **AI Chat System:** Currently implements project management features
  - Need to integrate with existing time travel architecture
- **Change Management:** Branch isolation is critical for change order workflows

Business Requirements:
- Users need to ask AI questions about historical project states
- Users need to explore "what-if" scenarios in isolated branches
- AI must be aware of context to provide accurate, non-confusing answers

### Architecture Context

**Bounded Contexts Involved:**
1. **AI Chat Bounded Context**
   - AgentService, ToolContext, AI tools
   - WebSocket protocol for streaming chat

2. **Versioning Bounded Context (EVCS)**
   - TemporalService with `as_of`, `branch`, `branch_mode` support
   - All versioned entities already support temporal queries

3. **Frontend Time Machine Context**
   - Zustand store with `selectedTime`, `selectedBranch`, `viewMode`
   - Context provider for component integration

**Existing Patterns:**
- Service layer methods accept `as_of`, `branch`, `branch_mode` parameters
- Frontend uses `useAsOfParam()`, `useBranchParam()`, `useModeParam()` hooks
- Temporal queries use TSTZRANGE with PostgreSQL

**Architectural Constraints:**
- Must respect single-source-of-truth pattern (Time Machine component only)
- WebSocket message schema must remain backward compatible
- AI tools use LangChain's `InjectedToolArg` pattern for context injection

### Codebase Analysis

**Backend:**

**Existing Related APIs:**
- `/backend/app/api/routes/ai_chat.py` (lines 102-280)
  - WebSocket endpoint at `/api/v1/ai/chat/stream`
  - Already accepts `project_id` and `branch_id` in `WSChatRequest`
  - Need to extend with temporal parameters

**Data Models:**
- `/backend/app/models/schemas/ai.py` (lines 332-353)
  - `WSChatRequest` has `project_id` and `branch_id`
  - `AIConversationSession` stores `branch_id` for context persistence

**Service Layer:**
- `/backend/app/core/versioning/service.py` (lines 1-100+)
  - `TemporalService.get_projects(as_of, branch, branch_mode)`
  - All services already support temporal parameters

**AI Tool System:**
- `/backend/app/ai/tools/types.py` (lines 11-63)
  - `ToolContext` dataclass currently has:
    - `project_id: str | None`
    - `branch_id: str | None` (UUID, not branch name)
    - Missing: `as_of`, `branch_name`, `branch_mode`

- `/backend/app/ai/tools/project_tools.py` (lines 18-92)
  - Example tool: `list_projects` hardcodes `branch="main"` (line 68)
  - Does NOT use `context.branch_id` (exists but ignored)
  - Pattern: All tools need similar updates

- `/backend/app/ai/agent_service.py` (lines 342-630)
  - `chat_stream()` method creates `ToolContext` (lines 434-440)
  - Already passes `project_id` and `branch_id` to ToolContext
  - Does NOT pass temporal parameters

**Frontend:**

**Time Machine Store:**
- `/frontend/src/stores/useTimeMachineStore.ts` (lines 1-308)
  - Stores: `selectedTime`, `selectedBranch`, `viewMode`
  - Hooks: `useAsOfParam()`, `useBranchParam()`, `useModeParam()`
  - Defaults: `null`, `"main"`, `"merged"`

**WebSocket Client:**
- Need to extend chat WebSocket messages with temporal parameters
- Must read from Time Machine store before sending messages

---

## Critical Questions Before Solution Design

Before proceeding with solution options, I need clarification on several critical aspects:

### Question 1: AI Tool Behavior with Temporal Context

When a user sets `branch="feature-x"` and `as_of="2025-01-15"`, should AI tools:

**Option A:** Strictly enforce temporal isolation
- ONLY see data as of that date/branch
- If user asks "show me all projects", return only projects visible as of 2025-01-15 in branch "feature-x"
- AI cannot "break out" of the temporal context

**Option B:** Informative transparency
- Be informed of temporal context
- Can reference it in responses ("In branch feature-x as of Jan 15...")
- May query across contexts if explicitly requested
- Defaults to temporal context for general queries

**Which behavior do you prefer?**

### Question 2: System Prompt Awareness

Should the AI explicitly tell users about temporal context in every response?

**Example with awareness:**
> "Here are the 3 active projects as of January 15, 2025 in branch 'feature-x' (isolated mode)..."

**Example without awareness:**
> "Here are the 3 active projects..."

**Should we include temporal context in system prompt for all responses, or only when relevant?**

### Question 3: branch_id vs branch_name Semantics

Current schema has `branch_id` (UUID) in both `ToolContext` and `AIConversationSession`.

**Confusion:**
- `branch_id` typically means "change order UUID" in EVCS
- But Time Machine uses `branch` (name like "main", "feature-x")
- These are different concepts!

**Clarification needed:**
- Should `ToolContext` have BOTH:
  - `branch_id: UUID | None` (for change order context in session)
  - `branch_name: str | None` (for temporal queries from Time Machine)?
- Or should we repurpose `branch_id` to store branch name instead?
- Or use `as_of`, `branch`, `branch_mode` as flat fields in `ToolContext`?

### Question 4: Default Behavior

When temporal parameters are NOT set (first-time user, or missing from WebSocket), what should happen?

**Proposed defaults:**
- `as_of`: `None` (current time, "now")
- `branch`: `"main"`
- `branch_mode`: `"merged"`

**Are these defaults acceptable?**

### Question 5: Validation Strategy

What happens if Time Machine params are set to invalid values?

**Example scenarios:**
- `branch="non-existent-branch"`
- `as_of="2099-01-01"` (future date)
- `branch_mode="invalid"`

**Should we:**
- Validate BEFORE tool execution and return errors?
- Let service layer handle it (already returns empty results)?
- Add specific validation in ToolContext initialization?

### Question 6: Non-Versioned Entities

Should ALL AI tools respect temporal context, even for non-versioned entities?

**Examples of non-versioned entities:**
- User settings
- AI conversation sessions
- AI assistant configs

**Options:**
- A: All tools use temporal context (consistent, even if ignored by service)
- B: Only versioned entity tools use temporal context (selective optimization)

### Question 7: WebSocket Message Frequency

Should temporal parameters be sent:

**Option A:** On EVERY WebSocket message
- Pros: Always current, handles mid-conversation Time Machine changes
- Cons: More bandwidth, redundant data

**Option B:** Once per connection/session
- Pros: Less bandwidth
- Cons: Stale if Time Machine changes during chat

**Which approach?** (I recommend Option A for consistency with current `project_id`/`branch_id` pattern)

---

## Preliminary Observations

Based on codebase analysis, here are initial findings:

### Strengths of Current Architecture

1. **Service Layer Ready:** All TemporalService methods already support `as_of`, `branch`, `branch_mode`
2. **Frontend Infrastructure Exists:** Time Machine store and hooks are ready
3. **WebSocket Protocol Extensible:** `WSChatRequest` can be enhanced
4. **Tool Context Pattern:** `InjectedToolArg` makes context injection clean

### Gaps Identified

1. **ToolContext Missing Fields:** No `as_of`, `branch_name`, `branch_mode`
2. **Tools Hardcode Values:** `list_projects` uses `branch="main"` directly
3. **No System Prompt Integration:** Temporal context not mentioned to AI
4. **branch_id Semantics Confusion:** UUID vs name ambiguity
5. **Frontend-Backend Disconnect:** Store exists but not wired to WebSocket

### Implementation Complexity Estimate

**Low Complexity:**
- Extending `WSChatRequest` schema (1 field)
- Adding fields to `ToolContext` (3 fields)
- Frontend: Sending params from store to WebSocket

**Medium Complexity:**
- Updating all AI tools to use temporal params (10+ tools)
- System prompt template generation with temporal context
- Validation logic for invalid params

**High Complexity:**
- Resolving `branch_id` vs `branch_name` semantics (architectural decision)
- Handling edge cases (future dates, invalid branches)
- Testing temporal isolation across all tools

---

## References

**Architecture Documentation:**
- [Temporal Query Reference](/docs/02-architecture/cross-cutting/temporal-query-reference.md)
- [EVCS Architecture](/docs/02-architecture/bounded-contexts/versioning/README.md)

**Code References:**
- Backend: `/backend/app/ai/tools/types.py` (ToolContext)
- Backend: `/backend/app/ai/tools/project_tools.py` (example tool)
- Backend: `/backend/app/api/routes/ai_chat.py` (WebSocket endpoint)
- Backend: `/backend/app/core/versioning/service.py` (TemporalService)
- Frontend: `/frontend/src/stores/useTimeMachineStore.ts` (Time Machine store)

**Related Features:**
- AI Chat System (implemented)
- Time Machine Component (implemented)
- EVCS Temporal Queries (implemented)
- Change Order Management (uses branch isolation)

---

## User Answers to Critical Questions

The following answers were provided to guide solution design:

**Q1: AI Tool Behavior** → **Strict enforcement** - AI ONLY sees data as of that date/branch. Cannot query outside the temporal context even if explicitly requested.

**Q2: System Prompt** → **When relevant** - Only mention temporal context when it materially affects the answer or to prevent confusion (not every response).

**Q3: Branch Semantics** → **Both fields** - ToolContext has branch_id (UUID for session/change order) AND branch_name (string for temporal queries like 'main', 'feature-x').

**Q4: WebSocket Frequency** → **Every message** - Send temporal parameters on every WebSocket message to always have current state and handle mid-conversation Time Machine changes.

**Q5: Defaults** → **Accept defaults** - as_of=None (current time), branch='main', branch_mode='merged' are acceptable.

**Q6: Validation** → **Service layer** - Let the service layer handle validation (already returns empty results for invalid branches/dates).

**Q7: Tool Scope** → **Versioned only** - Only versioned entity tools (projects, WBEs, cost elements) use temporal context, not non-versioned entities (user settings, AI configs).

---

## Approved Solution: Minimal Extension

Based on the clarified requirements and user answers, the following solution has been approved:

### Solution Overview

**Approach:** Extend existing infrastructure with minimal changes, maintaining backward compatibility.

#### Architecture Changes

**Backend Changes:**

1. **ToolContext Enhancement** (`/backend/app/ai/tools/types.py`):
   ```python
   @dataclass
   class ToolContext:
       project_id: str | None = None
       branch_id: str | None = None  # Existing: UUID for session/change order
       branch_name: str | None = None  # NEW: Branch name for temporal queries
       branch_mode: Literal["merged", "isolated"] | None = None  # NEW
       as_of: datetime | None = None  # NEW: Time travel timestamp
   ```

2. **WSChatRequest Extension** (`/backend/app/models/schemas/ai.py`):
   ```python
   class WSChatRequest(BaseModel):
       message: str
       project_id: str | None = None
       branch_id: str | None = None  # Existing
       as_of: datetime | None = None  # NEW
       branch_name: str | None = None  # NEW
       branch_mode: Literal["merged", "isolated"] | None = None  # NEW
   ```

3. **AgentService Update** (`/backend/app/ai/agent_service.py`):
   - Extract temporal params from WebSocket request
   - Pass to ToolContext initialization
   - Add temporal context to system prompt when relevant

4. **Tool Updates** (Apply pattern to all versioned entity tools):
   ```python
   def list_projects(
       context: Annotated[ToolContext, InjectedToolArg()],
       # ... other params
   ) -> str:
       # OLD: branch="main"
       # NEW:
       projects = project_service.get_projects(
           as_of=context.as_of,
           branch=context.branch_name or "main",
           branch_mode=context.branch_mode or "merged"
       )
   ```

**Frontend Changes:**

1. **WebSocket Message Enhancement**:
   ```typescript
   const timeMachine = useTimeMachineStore();
   const sendMessage = (message: string) => {
     websocket.send({
       message,
       project_id: projectId,
       branch_id: branchId,
       // NEW: Read from Time Machine store
       as_of: timeMachine.selectedTime,
       branch_name: timeMachine.selectedBranch,
       branch_mode: timeMachine.viewMode,
     });
   };
   ```

2. **System Prompt Template** (Backend):
   ```python
   def build_system_prompt(context: ToolContext) -> str:
     base_prompt = "You are a project management assistant..."
     if context.branch_name != "main" or context.as_of:
       temporal_note = f"""
       Note: You're viewing data{' as of ' + context.as_of.strftime('%Y-%m-%d') if context.as_of else ''} in branch '{context.branch_name}' ({context.branch_mode} mode).
       Mention this temporal context only when it materially affects your answer.
       """
       base_prompt += temporal_note
     return base_prompt
   ```

#### Trade-off Analysis

**Advantages:**
- Minimal architectural changes (extends existing patterns)
- Backward compatible (old clients work with defaults)
- Clear separation: branch_id (UUID) vs branch_name (string)
- Service layer validation (no new validation code)
- Only versioned entity tools affected (reduced scope)

**Disadvantages:**
- ToolContext has 6 fields (slightly complex)
- Need to update 10+ tools manually
- Frontend must send params on every message (bandwidth)

**Development Effort:** 2-3 days
- Backend: 1 day (ToolContext, schema, AgentService, tools)
- Frontend: 0.5 day (WebSocket integration)
- Testing: 0.5-1 day (temporal isolation tests)

**UX Quality:** High
- AI transparent about temporal context when relevant
- No confusion from time-travel queries
- Consistent with Time Machine component expectations

**Flexibility:** Medium
- Strict enforcement prevents cross-context queries
- Can be relaxed later if needed

---

## Rationale for Approved Solution

**Rationale for Approval:**

1. **Principle of Least Surprise**: Extends existing patterns without introducing new concepts
2. **Risk Minimization**: Lowest risk of bugs, maintains backward compatibility
3. **Fastest Delivery**: 2-3 days development effort
4. **Sufficient Flexibility**: Meets all requirements while allowing future enhancements
5. **Clear Debugging**: Explicit temporal parameters in tools make issues obvious

**User Alignment:**
- Strict enforcement of temporal context (matches user requirement)
- Temporal context mentioned only when relevant (matches UX preference)
- Both branch_id (UUID) and branch_name (string) fields (clear semantics)
- Parameters sent on every WebSocket message (always current)
- Service layer handles validation (no new validation code needed)
- Only versioned entity tools affected (selective optimization)

---

## References

**Architecture Documentation:**
- [Temporal Query Reference](/docs/02-architecture/cross-cutting/temporal-query-reference.md)
- [EVCS Architecture](/docs/02-architecture/bounded-contexts/versioning/README.md)

**Code References:**
- Backend: `/backend/app/ai/tools/types.py` (ToolContext)
- Backend: `/backend/app/ai/tools/project_tools.py` (example tool)
- Backend: `/backend/app/api/routes/ai_chat.py` (WebSocket endpoint)
- Backend: `/backend/app/core/versioning/service.py` (TemporalService)
- Frontend: `/frontend/src/stores/useTimeMachineStore.ts` (Time Machine store)

**Related Features:**
- AI Chat System (implemented)
- Time Machine Component (implemented)
- EVCS Temporal Queries (implemented)
- Change Order Management (uses branch isolation)

---

**ANALYSIS PHASE COMPLETE** - Solution approved, proceeding to PLAN phase.
**See:** `/home/nicola/dev/backcast/docs/03-project-plan/iterations/2026-03-20-ai-tools-temporal-context/01-plan.md`
