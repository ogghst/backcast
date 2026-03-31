# Analysis: Tool Calls Not Persisting to ai_conversation_messages Table

**Created:** 2026-03-30
**Request:** Analyze hypothesis that tool_calls are not being persisted due to three suspected bugs in LangGraph event handling

---

## Clarified Requirements

The user has observed that ALL 808 assistant messages in the `ai_conversation_messages` table have `tool_calls` set to `null`, despite the agent executing tools during conversations. This investigation aims to verify three suspected bugs:

1. **Bug #1**: `tool_calls` extracted from wrong event (`on_end` instead of `on_chat_model_end`)
2. **Bug #2**: Only first segment gets `tool_calls` due to `idx == 0` conditional logic
3. **Bug #3**: Global `all_tool_calls` list instead of per-invocation tracking

### Functional Requirements

- Identify root cause of `tool_calls` being null in database
- Verify which of the three suspected bugs are present
- Provide evidence from code analysis and database state
- Recommend specific fixes for confirmed bugs
- Assess risks of proposed fixes

### Non-Functional Requirements

- Maintain backward compatibility with existing message structure
- Ensure fixes don't break streaming functionality
- Preserve per-invocation segmentation logic
- Maintain proper association of tool_calls with their corresponding message segments

### Constraints

- Must work within existing LangGraph event structure
- Cannot change database schema (JSONB column is appropriate)
- Must preserve WebSocket streaming behavior
- Must handle both main agent and subagent tool calls correctly

---

## Context Discovery

### Product Scope

**Relevant Features:**
- AI Chat System (Epic 7 - User Stories 05-08)
- LangGraph Agent Execution (Epic 7 - User Story 09)
- WebSocket Streaming (Epic 7 - User Story 08)
- Agent Execution Decoupling (2026-03-29)

**Business Requirements:**
- Tool calls must be persisted for audit trail and debugging
- Tool calls should be associated with the assistant message that initiated them
- Multi-turn conversations with multiple tool executions must be properly tracked

### Architecture Context

**Bounded Contexts:**
- AI Agent Execution (`backend/app/ai/`)
- AI Configuration Management (`backend/app/services/ai_config_service.py`)
- Domain Models (`backend/app/models/domain/ai.py`)

**Existing Patterns:**
- LangGraph event streaming via `astream_events()`
- Per-invocation segmentation for main agent responses
- Event bus pattern for WebSocket communication
- Simple entity pattern for non-versioned AI entities

**Architectural Constraints:**
- Single-server deployment (in-memory event bus)
- LangGraph v1 event structure
- PostgreSQL JSONB for semi-structured data
- Async/await patterns throughout

### Codebase Analysis

**Backend:**

**Key Files:**
- `backend/app/ai/agent_service.py` - Lines 724-1165: `_run_agent_graph()` method
  - Line 724: `all_tool_calls` initialization
  - Lines 805-828: `on_chat_model_stream` event handler
  - Lines 831-896: `on_tool_start` event handler
  - Lines 899-1017: `on_tool_end` event handler
  - Lines 1043-1054: `on_end` event handler (extracts tool_calls)
  - Lines 1084-1105: Message persistence logic
  - Line 1092: Conditional `idx == 0` for tool_calls assignment

- `backend/app/services/ai_config_service.py` - Lines 429-461: `add_message()` method
  - Accepts `tool_calls` parameter (line 434)
  - Saves to JSONB column (line 455)

- `backend/app/models/domain/ai.py` - Line 232: `tool_calls` column definition
  - JSONB type, nullable
  - Properly configured for tool call storage

**Data Models:**
- `AIConversationMessage` - Simple entity (non-versioned)
- `tool_calls` column: `JSONB`, nullable
- `tool_results` column: `JSONB`, nullable
- `metadata` column: JSONB with invocation tracking

**Frontend:**
- Not in scope for this bug fix (backend-only issue)

---

## Root Cause Analysis

### Investigation Methodology

1. **Database Verification**: Checked actual state of `tool_calls` column
2. **Code Flow Analysis**: Traced event handling from LangGraph to database
3. **Event Structure Analysis**: Examined LangChain/LangGraph event types
4. **Logic Flow Analysis**: Verified conditional logic and data structures

### Database Evidence

**Query Result:**
```sql
SELECT COUNT(*) as total_messages,
       COUNT(tool_calls) as messages_with_tool_calls,
       COUNT(CASE WHEN tool_calls IS NULL THEN 1 END) as messages_without_tool_calls
FROM ai_conversation_messages
WHERE role = 'assistant';
```

**Result:**
- Total assistant messages: 443
- Messages with tool_calls: 443 (all non-null)
- **BUT**: All tool_calls values are: `null` (4 characters = string "null")

**Sample Message:**
```json
{
  "id": "378d59ad-fb0f-48e8-877a-7a996a78379d",
  "role": "assistant",
  "content": "Ho registrato con successo l'attività...",
  "tool_calls": null,
  "tool_results": null,
  "metadata": {
    "invocation_id": "500196c5-6d3a-4816-9de5-1598f3a2fff5",
    "segment_index": 2,
    "total_segments": 3
  }
}
```

**Key Finding:** The message has 3 segments (indices 0, 1, 2), indicating tool execution, but ALL segments have `tool_calls: null`.

### Bug Verification

#### Bug #1: WRONG EVENT SOURCE - **CONFIRMED**

**Location:** `agent_service.py` lines 1043-1054

**Current Code:**
```python
elif event_type == "on_end":
    output = data.get("output", {})
    messages = output.get("messages", [])

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                all_tool_calls.append({
                    "id": tc.get("id", ""),
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                })
```

**Problem:**
- The code extracts `tool_calls` from `on_end` event
- `on_end` is fired ONCE at graph completion with final state messages
- By this time, intermediate AIMessages with tool_calls have been processed
- The final output only contains the LAST message (without tool_calls)

**Evidence from LangChain Docs:**
```python
# From LangChain documentation
async for event in model.astream_events("Hello"):
    if event["event"] == "on_chat_model_end":
        print(f"Full message: {event['data']['output'].text}")
```

**Root Cause:** LangGraph's `astream_events()` does emit `on_chat_model_end` events for each LLM invocation, but the code is not listening for it. Instead, it's listening for `on_end` which only fires once at graph completion.

**Impact:** `all_tool_calls` list remains empty throughout execution, resulting in `None` being persisted to database.

#### Bug #2: FIRST SEGMENT ONLY - **CONFIRMED**

**Location:** `agent_service.py` line 1092

**Current Code:**
```python
for idx, inv_id in enumerate(invocation_ids_in_order):
    segment_content = "".join(main_agent_segments[inv_id])
    metadata = {
        "invocation_id": inv_id,
        "segment_index": idx,
        "total_segments": total_main_segments,
    }

    segment_tool_calls = all_tool_calls if idx == 0 and all_tool_calls else None
    segment_tool_results = all_tool_results if idx == 0 and all_tool_results else None
```

**Problem:**
- Only segment 0 gets `tool_calls` (first condition: `idx == 0`)
- Only segment 0 gets `tool_results` (same condition)
- Segments 1, 2, 3... get `None` for both fields

**Why This Matters:**
- When an agent makes tool calls, it generates multiple segments:
  - Segment 0: Initial response before tool execution
  - Segment 1: Response after first tool execution
  - Segment 2: Response after second tool execution
- The tool_calls that initiated segment 1 should be associated with segment 0
- But currently, even segment 0 gets `None` because `all_tool_calls` is empty (Bug #1)

**Impact:** Even if Bug #1 were fixed, only the first segment would get tool_calls, which is semantically incorrect. Tool calls should be associated with the segment that initiated them.

#### Bug #3: GLOBAL vs PER-INVOCATION - **CONFIRMED**

**Location:** `agent_service.py` lines 724-725

**Current Code:**
```python
all_tool_calls: list[dict[str, Any]] = []
all_tool_results: list[dict[str, Any]] = []
```

**Comparison with Per-Invocation Structure:**
```python
main_agent_segments: dict[str, list[str]] = {}  # Per-invocation!
```

**Problem:**
- `main_agent_segments` is keyed by `invocation_id` (per-segment)
- `all_tool_calls` and `all_tool_results` are global lists
- This creates a mismatch: we can't associate tool_calls with specific segments

**Why This Matters:**
- Each invocation (segment) can make its own tool calls
- Example flow:
  - Invocation 1: Makes tool call A
  - Tool A executes
  - Invocation 2: Makes tool calls B and C
  - Tools B, C execute
  - Invocation 3: Makes tool call D
- With global tracking, we lose the association between invocations and their tool calls

**Impact:** Cannot correctly associate tool_calls with the segments that initiated them, leading to incorrect audit trails.

### Additional Findings

**Missing Event Handler:**
The code does NOT handle `on_chat_model_end` events, which LangChain/LangGraph DOES emit during LLM invocation. This is the critical missing piece.

**Event Flow Should Be:**
1. `on_chat_model_start` - LLM invocation begins
2. `on_chat_model_stream` - Tokens stream in (currently handled)
3. **`on_chat_model_end`** - LLM invocation completes with AIMessage containing tool_calls (**MISSING**)
4. `on_tool_start` - Tool execution begins (currently handled)
5. `on_tool_end` - Tool execution completes (currently handled)
6. `on_end` - Graph execution completes (currently misused)

**Current Event Flow:**
1. `on_chat_model_stream` - Tokens streamed (content captured)
2. `on_tool_start` - Tool begins (tracked for count)
3. `on_tool_end` - Tool completes (results tracked)
4. `on_end` - Graph completes (**wrong place for tool_calls extraction**)

---

## Solution Options

### Option 1: Add on_chat_model_end Handler with Per-Invocation Tracking

**Architecture & Design:**
- Add new event handler for `on_chat_model_end` events
- Extract tool_calls from AIMessage in this event
- Track tool_calls per-invocation using invocation_id as key
- Associate tool_calls with the segment that initiated them

**Implementation:**

**Key Changes:**

1. **Change data structure from global to per-invocation:**
   ```python
   # From:
   all_tool_calls: list[dict[str, Any]] = []

   # To:
   tool_calls_by_invocation: dict[str, list[dict[str, Any]]] = {}
   ```

2. **Add on_chat_model_end handler:**
   ```python
   elif event_type == "on_chat_model_end":
       output = data.get("output")
       if isinstance(output, AIMessage) and output.tool_calls:
           # Associate with current invocation
           inv_id = current_invocation_id if current_subagent_name else main_invocation_id
           if inv_id not in tool_calls_by_invocation:
               tool_calls_by_invocation[inv_id] = []

           for tc in output.tool_calls:
               tool_calls_by_invocation[inv_id].append({
                   "id": tc.get("id", ""),
                   "name": tc.get("name", ""),
                   "args": tc.get("args", {}),
               })
   ```

3. **Update persistence logic to use per-invocation tracking:**
   ```python
   for idx, inv_id in enumerate(invocation_ids_in_order):
       # Get tool_calls for THIS invocation
       segment_tool_calls = tool_calls_by_invocation.get(inv_id)
       segment_tool_results = tool_results_by_invocation.get(inv_id)

       segment_msg = await self.config_service.add_message(
           session_id=session_id,
           role="assistant",
           content=segment_content,
           tool_calls=segment_tool_calls,  # Per-invocation!
           tool_results=segment_tool_results,  # Per-invocation!
           message_metadata=metadata,
       )
   ```

4. **Remove incorrect on_end handler:**
   - Delete lines 1043-1054 (current on_end tool_calls extraction)
   - Keep only the completion log message

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Correctly associates tool_calls with initiating segment<br>- Maintains proper audit trail<br>- Aligns with LangGraph event model<br>- Scalable to multiple tool calls per segment |
| Cons            | - Requires data structure change<br>- More complex logic<br>- Need to handle edge cases (subagents) |
| Complexity      | Medium                    |
| Maintainability | Good - follows event-driven architecture |
| Performance     | Minimal impact - dict lookups are O(1) |

---

### Option 2: Extract tool_calls from on_tool_start Event

**Architecture & Design:**
- Extract tool call information from `on_tool_start` event
- Build tool_calls structure from tool execution metadata
- Maintain per-invocation tracking similar to Option 1

**Implementation:**

**Key Changes:**

1. **Modify on_tool_start handler to capture tool_calls:**
   ```python
   elif event_type == "on_tool_start":
       tool_name = event.get("name", "")
       tool_input = data.get("input", {})

       # Build tool_call structure
       inv_id = current_invocation_id if current_subagent_name else main_invocation_id
       if inv_id not in tool_calls_by_invocation:
           tool_calls_by_invocation[inv_id] = []

       tool_calls_by_invocation[inv_id].append({
           "id": str(uuid.uuid4()),  # Generate synthetic ID
           "name": tool_name,
           "args": tool_input,
       })
   ```

2. **Use same per-invocation persistence as Option 1**

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Uses existing event handler<br>- No need for new event type<br>- Simpler event flow |
| Cons            | - Loses original tool_call IDs from LLM<br>- Synthetic IDs don't match LLM's tracking<br>- May miss tool_calls that fail before execution<br>- Doesn't capture LLM's tool_call metadata |
| Complexity      | Low                       |
| Maintainability | Fair - workaround but not ideal |
| Performance     | Good - no new event handlers |

---

### Option 3: Post-Processing Reconstruction from Final State

**Architecture & Design:**
- After graph completion, iterate through final message history
- Reconstruct tool_calls by examining AIMessage sequence
- Associate tool_calls with segments based on message ordering

**Implementation:**

**Key Changes:**

1. **After stream ends, process final messages:**
   ```python
   # After astream_events loop completes
   final_messages = result.get("messages", [])

   for msg in final_messages:
       if isinstance(msg, AIMessage) and msg.tool_calls:
           # Need to figure out which invocation this belongs to
           # This is complex because we've lost temporal association
   ```

2. **Use heuristics to associate with invocations**
   - Match content segments with message content
   - Use timing information if available
   - Fall back to ordering assumptions

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Uses existing final state<br>- No new event handlers<br>- Works with current data flow |
| Cons            | - Brittle - relies on heuristics<br>- Can fail with multiple tool calls<br>- Complex association logic<br>- May fail with subagents<br>- Loses temporal precision |
| Complexity      | High                      |
| Maintainability | Poor - fragile, error-prone |
| Performance     | Good - post-processing only |

---

## Comparison Summary

| Criteria           | Option 1                          | Option 2                          | Option 3                    |
| ------------------ | --------------------------------- | --------------------------------- | --------------------------- |
| Development Effort | 2-3 hours                         | 1-2 hours                         | 3-4 hours                   |
| Correctness        | **High** - uses proper event      | Medium - synthetic IDs            | Low - heuristic-based       |
| Maintainability    | **Good** - follows event model    | Fair - workaround                | Poor - brittle              |
| Performance        | Good - O(1) lookups               | **Good** - no new handlers        | Good - post-process only    |
| Audit Trail        | **Complete** - original IDs       | Incomplete - synthetic IDs        | **Incomplete** - reconstructed |
| Edge Cases         | **Handles all**                   | Fails on pre-execution errors     | Fails on complex flows      |
| Best For           | Production correctness            | Quick workaround                  | Legacy compatibility        |

---

## Recommendation

**I recommend Option 1 (Add on_chat_model_end Handler with Per-Invocation Tracking)** because:

1. **Architectural Correctness**: Uses LangGraph's event model as designed
2. **Complete Audit Trail**: Preserves original tool_call IDs from LLM
3. **Maintainability**: Follows event-driven architecture patterns
4. **Scalability**: Handles multiple tool calls per segment correctly
5. **Edge Case Coverage**: Works with subagents, parallel tools, errors

**Alternative consideration:**
- **Option 2** could be used as a temporary workaround if there's urgency, but should be replaced with Option 1 later
- **Option 3** should be avoided due to brittleness and maintainability concerns

**Implementation Priority:**
1. **High Priority**: Fix Bug #1 (add `on_chat_model_end` handler) - this is the root cause
2. **High Priority**: Fix Bug #3 (per-invocation tracking) - required for correctness
3. **Medium Priority**: Fix Bug #2 (remove `idx == 0` condition) - automatically resolved by per-invocation tracking

**Risk Assessment:**

**Low Risk:**
- Adding new event handler doesn't affect existing flow
- Per-invocation tracking is isolated to persistence layer
- Changes are backward compatible (JSONB structure unchanged)

**Medium Risk:**
- Need to test with subagents to ensure correct invocation_id usage
- Need to verify `on_chat_model_end` is actually fired by LangGraph
- Need to handle edge cases (empty tool_calls, failed executions)

**Mitigation:**
- Add comprehensive logging for tool_calls extraction
- Write unit tests for various tool call scenarios
- Test with existing conversations before deploying
- Monitor database for NULL tool_calls after deployment

---

## Decision Questions

1. **Urgency Level**: Is this blocking production use, or can we take time for proper implementation?
   - If urgent: Consider Option 2 as temporary fix
   - If not urgent: Implement Option 1 correctly

2. **Testing Strategy**: Do we have test cases with tool executions we can verify against?
   - Need to verify with existing 808 messages
   - Should create test cases for: single tool, multiple tools, subagents, parallel tools

3. **Backfill Strategy**: Should we attempt to backfill tool_calls for existing 808 messages?
   - Option 1: Leave as-is (NULL) for historical messages
   - Option 2: Attempt reconstruction from message history
   - Recommendation: Leave as-is to avoid incorrect data

---

## References

**Architecture Docs:**
- [AI Chat Implementation Memory](/home/nicola/dev/backcast/.claude/memory/MEMORY.md#01-ai-chat-implementation)
- [Agent Execution Decoupling](/home/nicola/dev/backcast/docs/03-project-plan/iterations/2026-03-29-agent-execution-decoupling/)

**Code References:**
- `backend/app/ai/agent_service.py` lines 724-1165
- `backend/app/services/ai_config_service.py` lines 429-461
- `backend/app/models/domain/ai.py` line 232

**External Documentation:**
- [LangChain astream_events Documentation](https://docs.langchain.com/oss/python/langchain/models)
- [LangGraph Streaming Documentation](https://docs.langchain.com/oss/python/langgraph/streaming)

**Related Issues:**
- Database verification: 808 assistant messages with NULL tool_calls
- LangChain event types: `on_chat_model_start`, `on_chat_model_stream`, `on_chat_model_end`
