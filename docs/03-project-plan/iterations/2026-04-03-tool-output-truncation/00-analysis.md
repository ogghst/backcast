# Analysis: Tool Output Truncation (Context Window Protection)

**Created:** 2026-04-03
**Request:** Tool Output Truncation -- cap verbose tool results at a configurable character/token budget to prevent context window blowout
**Status:** ANALYSIS COMPLETE - Awaiting User Approval

---

## 1. Clarified Requirements

### 1.1 User Intent

A single verbose AI tool result (e.g., `list_projects` returning 100+ records, or `analyze_change_order_impact` returning a full diff) can consume a disproportionate share of the LLM context window. The system currently detects this in `_make_json_serializable` (logs strings over 100KB) but takes no corrective action. There is no per-message output cap on tool results.

The goal is to introduce a post-execution truncation step that caps tool output before it enters the agent's message history, preserving context window headroom for reasoning.

### 1.2 Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| FR-1 | Default Output Cap | Tool outputs exceeding ~15,000 characters (~4,000 tokens) are truncated with a summary marker |
| FR-2 | Per-Tool Override | Individual tools can specify a custom `max_output_chars` via `@ai_tool` decorator metadata |
| FR-3 | Untruncated Tools | Tools marked as "read-type" (e.g., file readers) can opt out of truncation entirely |
| FR-4 | Truncation Marker | Truncated outputs include a machine-readable suffix indicating truncation occurred and original size |
| FR-5 | Truncation Logging | Every truncation event is logged at WARNING level with tool name, original size, and truncated size |
| FR-6 | Additive Only | No breaking changes to existing tool signatures, middleware chain, or message protocols |

### 1.3 Non-Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-1 | Performance | Truncation overhead must be < 1ms per tool call |
| NFR-2 | Type Safety | Full MyPy strict mode compliance |
| NFR-3 | Test Coverage | 90%+ coverage for truncation logic |
| NFR-4 | Zero Config | Works out of the box with sensible defaults; no mandatory configuration |

### 1.4 Constraints

| ID | Constraint | Description |
|----|------------|-------------|
| C-1 | Architecture | Must work within the existing middleware chain (TemporalContextMiddleware -> BackcastSecurityMiddleware) |
| C-2 | No New Middleware Class | Adding a third middleware class increases complexity; prefer extending existing interception points |
| C-3 | LangGraph Compatibility | ToolMessage content must remain a string (LangGraph state requirement) |
| C-4 | Backward Compatibility | All existing tools function identically if no `max_output_chars` is specified |

---

## 2. Context Discovery

### 2.1 Product Scope

**Relevant User Stories:**
- AI Chat Interface (US-AI-001): Natural language project queries
- AI Agent Tools (US-AI-002): Tool-based autonomous execution

**Business Requirements:**
- AI agent must remain responsive during long conversations
- Context window exhaustion leads to degraded response quality and increased API costs
- Agent should handle large datasets without losing reasoning capability

### 2.2 Architecture Context

**Bounded Contexts Involved:**
- AI Agent Bounded Context: LangGraph orchestration, tool execution, message history

**Existing Patterns to Follow:**
- `AgentMiddleware.awrap_tool_call()` pattern: Each middleware wraps the tool call, can inspect and modify the ToolMessage before returning it
- `ToolMetadata` dataclass pattern: Extensible metadata attached via `_tool_metadata` attribute on BaseTool instances
- `@ai_tool` decorator parameter pattern: Additional configuration parameters accepted as decorator arguments, forwarded to ToolMetadata

**Tool Output Flow (current):**
```
Tool function returns result
  -> @ai_tool wrapper (decorator.py:161) commits session, returns raw result
  -> LangGraph ToolNode wraps result as ToolMessage(content=str(result))
  -> BackcastSecurityMiddleware.awrap_tool_call() (backcast_security.py:178) returns ToolMessage
  -> TemporalContextMiddleware.awrap_tool_call() returns ToolMessage
  -> ToolMessage added to agent state messages list
  -> agent_service.py on_tool_end handler (line 901) extracts content via _make_json_serializable (line 999)
  -> Content broadcast to frontend via WebSocket
```

**Critical Observation:** The middleware `awrap_tool_call()` methods receive the ToolMessage **after** the handler executes. Both `BackcastSecurityMiddleware.awrap_tool_call()` (line 178) and `TemporalContextMiddleware.awrap_tool_call()` (line 102) return the ToolMessage directly from `await handler(request)`. This is the correct interception point -- the middleware can modify the ToolMessage content before returning it upstream.

### 2.3 Codebase Analysis

#### Backend

**Existing Related Code:**

| File | Purpose | Relevance |
|------|---------|-----------|
| `backend/app/ai/middleware/backcast_security.py` | Security middleware, `awrap_tool_call()` interception | Primary interception point for post-execution truncation |
| `backend/app/ai/tools/types.py` | `ToolMetadata` dataclass with `RiskLevel`, permissions | Needs `max_output_chars` field |
| `backend/app/ai/tools/decorator.py` | `@ai_tool` decorator that attaches metadata | Needs `max_output_chars` parameter |
| `backend/app/ai/agent_service.py:1409` | `_make_json_serializable` already detects large strings (100KB) | Logging precedent; does not truncate |
| `backend/app/ai/tools/subagent_task.py:313` | Already truncates for display: `json_str[:500] + "... (truncated)"` | Precedent for truncation pattern in the codebase |
| `backend/app/ai/middleware/temporal_context.py` | Middleware that modifies tool args before execution | Reference for middleware structure |

**Existing Truncation Precedent:**
In `subagent_task.py:313`, there is already a simple truncation pattern:
```python
json_str = json_str[:500] + "\n... (truncated)"
```
This confirms truncation is an accepted pattern in the codebase.

**Key Architecture Detail -- Middleware Ordering:**
From `deep_agent_orchestrator.py:139-146`, the middleware stack is:
```python
backcast_middleware = [
    TemporalContextMiddleware(self.context),
    BackcastSecurityMiddleware(self.context, tools=all_tools, interrupt_node=None),
]
```
Middleware is executed in list order for `awrap_tool_call` (outermost first). So `TemporalContextMiddleware` wraps `BackcastSecurityMiddleware`. The truncation should happen in `BackcastSecurityMiddleware` (innermost) so it operates on the final result before it propagates outward.

**No existing `backend/app/ai/context/` directory:** The proposed file `backend/app/ai/context/tool_output_budget.py` would be a new directory and file.

#### Frontend

No frontend changes are required for this feature. Truncation is a backend-only concern that affects what the LLM sees in its message history. The frontend already receives tool results via WebSocket; truncated results will appear naturally with the truncation marker.

---

## 3. Solution Options

### Option 1: Truncation in BackcastSecurityMiddleware (Minimal Extension)

**Architecture & Design:**

Extend the existing `BackcastSecurityMiddleware.awrap_tool_call()` to truncate the ToolMessage content after the handler executes. The truncation logic is a private method on the middleware class. No new files or classes are created.

**Components:**
1. **ToolMetadata extension**: Add `max_output_chars: int | None = None` field
2. **@ai_tool decorator extension**: Add `max_output_chars` parameter
3. **BackcastSecurityMiddleware._truncate_output()**: Private method that checks tool metadata and truncates if needed
4. **DEFAULT_MAX_OUTPUT_CHARS**: Module-level constant (15,000)

**Data Flow:**
```
Tool executes -> handler(request) returns ToolMessage
  -> BackcastSecurityMiddleware checks _tool_metadata.max_output_chars
  -> If content length exceeds budget:
       content = content[:budget] + truncation_marker
       log WARNING with tool_name, original_size, truncated_size
  -> Return modified ToolMessage
```

**Implementation:**

| File | Changes | Est. Lines |
|------|---------|------------|
| `backend/app/ai/tools/types.py` | Add `max_output_chars: int \| None = None` to ToolMetadata | +3 |
| `backend/app/ai/tools/decorator.py` | Add `max_output_chars` parameter, forward to ToolMetadata | +8 |
| `backend/app/ai/middleware/backcast_security.py` | Add `_truncate_output()` method, call in `awrap_tool_call()` after handler | +35 |
| `backend/tests/unit/ai/test_tool_output_truncation.py` | New test file | +80 |

**Trade-offs:**

| Aspect          | Assessment                                                         |
| --------------- | ------------------------------------------------------------------ |
| Pros            | - Minimal surface area (3 files touched, 1 new test file)          |
|                 | - Follows established middleware pattern exactly                    |
|                 | - No new classes, modules, or abstractions                         |
|                 | - Leverages existing `_tools_by_name` lookup for metadata access   |
| Cons            | - Adds truncation responsibility to security middleware             |
|                 | - Concern mixing (security + output shaping)                       |
| Complexity      | Low                                                                |
| Maintainability | Good (all output shaping in one method)                            |
| Performance     | Excellent (single string slice, < 1ms)                             |

---

### Option 2: Dedicated Truncation Utility + Middleware Method

**Architecture & Design:**

Extract the truncation logic into a standalone utility function in a new module `backend/app/ai/tools/output_budget.py`. The middleware calls this utility. The utility is a pure function with no dependencies on the middleware class.

**Components:**
1. **ToolMetadata extension**: Add `max_output_chars: int | None = None` field (same as Option 1)
2. **@ai_tool decorator extension**: Add `max_output_chars` parameter (same as Option 1)
3. **New `backend/app/ai/tools/output_budget.py`**: Pure function `truncate_tool_output(content, max_chars, tool_name) -> str`
4. **BackcastSecurityMiddleware**: Calls utility in `awrap_tool_call()` after handler

**Data Flow:**
```
Tool executes -> handler(request) returns ToolMessage
  -> BackcastSecurityMiddleware checks metadata
  -> Calls truncate_tool_output(content, budget, tool_name)
  -> Utility returns truncated content + logs event
  -> Return modified ToolMessage
```

**Implementation:**

| File | Changes | Est. Lines |
|------|---------|------------|
| `backend/app/ai/tools/types.py` | Add `max_output_chars` to ToolMetadata | +3 |
| `backend/app/ai/tools/decorator.py` | Add `max_output_chars` parameter | +8 |
| `backend/app/ai/tools/output_budget.py` | New file: `truncate_tool_output()` function | +40 |
| `backend/app/ai/middleware/backcast_security.py` | Import and call utility | +10 |
| `backend/tests/unit/ai/test_output_budget.py` | New test file for utility | +60 |
| `backend/tests/unit/ai/test_tool_output_truncation.py` | Integration test | +30 |

**Trade-offs:**

| Aspect          | Assessment                                                         |
| --------------- | ------------------------------------------------------------------ |
| Pros            | - Separation of concerns (utility is pure, testable independently) |
|                 | - Utility can be reused outside middleware (e.g., subagent results)|
|                 | - Follows single-responsibility principle                          |
| Cons            | - New file for a single function                                   |
|                 | - Slightly more indirection                                        |
|                 | - Over-engineering risk for what is essentially a string slice     |
| Complexity      | Low-Medium                                                         |
| Maintainability | Good (utility is self-contained and independently testable)        |
| Performance     | Excellent (< 1ms)                                                  |

---

### Option 3: Third Middleware in the Chain (TruncationMiddleware)

**Architecture & Design:**

Create a new `OutputTruncationMiddleware(AgentMiddleware)` class that sits in the middleware chain between `TemporalContextMiddleware` and `BackcastSecurityMiddleware`. It intercepts the ToolMessage after execution and truncates based on tool metadata.

**Components:**
1. **ToolMetadata extension**: Add `max_output_chars: int | None = None` field
2. **@ai_tool decorator extension**: Add `max_output_chars` parameter
3. **New `backend/app/ai/middleware/output_truncation.py`**: `OutputTruncationMiddleware` class
4. **`deep_agent_orchestrator.py`**: Add third middleware to stack (both main agent and subagent)

**Data Flow:**
```
TemporalContextMiddleware (inject temporal params)
  -> OutputTruncationMiddleware (intercept ToolMessage on return path)
    -> BackcastSecurityMiddleware (security checks)
      -> Tool executes
      <- ToolMessage returned
    <- ToolMessage returned (security-checked)
  <- ToolMessage returned (truncated if needed)
<- ToolMessage returned (temporal-injected)
```

**Implementation:**

| File | Changes | Est. Lines |
|------|---------|------------|
| `backend/app/ai/tools/types.py` | Add `max_output_chars` to ToolMetadata | +3 |
| `backend/app/ai/tools/decorator.py` | Add `max_output_chars` parameter | +8 |
| `backend/app/ai/middleware/output_truncation.py` | New middleware class | +60 |
| `backend/app/ai/middleware/__init__.py` | Export new middleware | +3 |
| `backend/app/ai/deep_agent_orchestrator.py` | Add middleware to stack (2 locations: main + subagent) | +10 |
| `backend/tests/unit/ai/test_output_truncation_middleware.py` | New test file | +80 |

**Trade-offs:**

| Aspect          | Assessment                                                         |
| --------------- | ------------------------------------------------------------------ |
| Pros            | - Cleanest separation of concerns                                  |
|                 | - Follows middleware pattern perfectly                              |
|                 | - Can be added/removed independently                               |
| Cons            | - Third middleware class for a simple string slice                  |
|                 | - Must be added to both main agent AND subagent middleware stacks  |
|                 | - Requires `tools` list for metadata lookup (duplicated from security) |
|                 | - Adds latency of one more middleware hop per tool call             |
| Complexity      | Medium                                                             |
| Maintainability | Good (isolated concern)                                            |
| Performance     | Good (< 2ms, extra middleware overhead)                            |

---

## 4. Comparison Summary

| Criteria           | Option 1: Inline in Security MW | Option 2: Utility Function    | Option 3: New Middleware      |
| ------------------ | ------------------------------- | ----------------------------- | ----------------------------- |
| Development Effort | ~126 lines (3 files + tests)    | ~151 lines (4 files + tests)  | ~164 lines (5 files + tests)  |
| Implementation Time| 0.5-1 day                       | 1 day                         | 1-1.5 days                    |
| New Files          | 1 (test file)                   | 2 (utility + test)            | 2 (middleware + test)         |
| Complexity         | Low                             | Low-Medium                    | Medium                        |
| Maintainability    | Good                            | Good                          | Good                          |
| Performance        | Excellent (< 1ms)               | Excellent (< 1ms)             | Good (< 2ms)                  |
| Best For           | Pragmatic, minimal change       | Reusable utility              | Strict SoC                    |
| Concern Mixing     | Security + output shaping       | Clean separation              | Cleanest separation           |

---

## 5. Recommendation

### I Recommend Option 1: Truncation Inline in BackcastSecurityMiddleware

**Rationale:**

1. **Minimal surface area**: The change touches 3 existing files and adds 1 test file. No new modules, no new classes, no new abstractions. This is a string-length check followed by a slice operation -- it does not warrant its own module or middleware class.

2. **BackcastSecurityMiddleware already owns tool-result post-processing**: The middleware already intercepts every tool call and inspects the result (for approval flow, error handling, logging). Adding a truncation step is a natural extension of its existing responsibility.

3. **Follows the existing pattern exactly**: `TemporalContextMiddleware` modifies tool args before execution. `BackcastSecurityMiddleware` checks permissions and risk before execution and handles results after. This is consistent.

4. **No orchestration changes**: Options 3 requires modifying `deep_agent_orchestrator.py` in two places (main agent + subagent stacks). Option 1 requires zero changes outside the middleware and tool types.

5. **Practical benefit over theoretical purity**: The truncation logic is ~15 lines of code (a length check, a string slice, a log statement, and a marker suffix). Creating a dedicated module or middleware class for this is over-engineering that violates the project's "Simplicity First" guideline.

### Alternative Consideration:

**Choose Option 2 if:** You anticipate needing truncation logic in multiple places beyond the middleware chain (e.g., truncating subagent results, truncating messages during context compaction). In that case, a reusable utility function makes sense. However, the current request is scoped to tool output only, so Option 1 is sufficient.

**Do NOT choose Option 3 unless:** You have a strong architectural principle that each middleware must have exactly one responsibility. The cost (new class, new file, orchestration changes in 2 places) outweighs the benefit for a string-slice operation.

---

## 6. Decision Questions

1. **Default Budget**: The proposed default is 15,000 characters (~4,000 tokens). Is this appropriate, or do you prefer a different limit? Note: the existing 100KB threshold in `_make_json_serializable` is far too high for context window protection.

2. **Truncation Marker Format**: Should the truncation suffix include structured metadata (original size, tool name) for the LLM to reason about, or just a simple `[truncated at X chars, originally Y chars]` marker?

3. **Read-Tool Exemption**: Should certain tools (e.g., file readers, data export tools) be exempt from truncation by default? If so, should this be expressed as `max_output_chars=0` meaning "no limit", or `max_output_chars=None` meaning "use default"?

---

## 7. Implementation Preview (Option 1)

### Step 1: Extend ToolMetadata (~5 min)
Add `max_output_chars: int | None = None` to `ToolMetadata` dataclass in `types.py`.

### Step 2: Extend @ai_tool Decorator (~10 min)
Add `max_output_chars: int | None = None` parameter to decorator, forward to `ToolMetadata`.

### Step 3: Add Truncation to Middleware (~30 min)
Add `_truncate_output()` private method to `BackcastSecurityMiddleware`. Call it after `await handler(request)` in `awrap_tool_call()`.

### Step 4: Tests (~30 min)
Test file covering: default truncation, custom per-tool budget, exemption, marker format, logging.

### Step 5: Annotate High-Output Tools (~15 min)
Add `max_output_chars` overrides to tools known to produce large output (e.g., list tools, analysis tools).

---

## 8. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Truncation loses critical data** | High | Per-tool override via `max_output_chars`; tools that need full content opt out |
| **Truncation marker confuses LLM** | Medium | Include structured metadata in marker (original size, tool name) so LLM can ask for more detail |
| **Budget too aggressive** | Medium | Default 15K chars is conservative (~4K tokens); can be tuned per-tool |
| **Breaking existing tool behavior** | Low | Default applies only when output exceeds threshold; no change for outputs under budget |
| **Tool returns non-string content** | Low | ToolMessage.content is always a string in LangGraph; truncation operates on strings only |

---

## 9. References

### Code References
- [BackcastSecurityMiddleware](/home/nicola/dev/backcast/backend/app/ai/middleware/backcast_security.py) -- Primary interception point
- [ToolMetadata dataclass](/home/nicola/dev/backcast/backend/app/ai/tools/types.py) -- Metadata structure to extend
- [@ai_tool decorator](/home/nicola/dev/backcast/backend/app/ai/tools/decorator.py) -- Decorator to extend
- [agent_service.py _make_json_serializable](/home/nicola/dev/backcast/backend/app/ai/agent_service.py#L1409) -- Existing large-string detection precedent
- [subagent_task.py truncation](/home/nicola/dev/backcast/backend/app/ai/tools/subagent_task.py#L313) -- Existing truncation pattern
- [TemporalContextMiddleware](/home/nicola/dev/backcast/backend/app/ai/middleware/temporal_context.py) -- Reference middleware pattern
- [deep_agent_orchestrator.py middleware stack](/home/nicola/dev/backcast/backend/app/ai/deep_agent_orchestrator.py#L139) -- Middleware ordering

### Research References
- [Claude Code Context Management Research](/home/nicola/dev/backcast/docs/03-project-plan/iterations/2026-04-02-claude-code-like-context-management/) -- Background research on tool result clearing strategies

### External Resources
- [Anthropic Context Editing Docs](https://platform.claude.com/docs/en/build-with-claude/context-editing) -- Tool result clearing as context management strategy

---

**Awaiting User Decision**: Please review the three options and decision questions, then indicate which approach you would like to proceed with.
