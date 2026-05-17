# Analysis: Batch AI Tools for Bulk CRUD Operations

**Created:** 2026-05-17
**Request:** Add batch-aware AI tools that handle multiple entities in a single tool call, reducing N LLM-to-tool-to-DB round-trips to 1 call for bulk create/update/delete operations.

---

## Clarified Requirements

The current AI tool architecture maps 1:1 between tool calls and entity operations. When the LLM needs to create 5 cost elements, it must invoke `create_cost_element` 5 times -- each incurring token overhead for the tool-call round-trip and each triggering a separate DB commit cycle. Batch tools collapse these N calls into a single tool invocation while maintaining the same service-layer guarantees.

### Functional Requirements

1. **6 batch tools** covering the highest-frequency bulk operations:
   - `create_cost_elements` -- batch create cost elements under the same WBE
   - `create_wbes` -- batch create WBEs under the same project
   - `create_cost_registrations` -- batch register actual costs
   - `create_progress_entries` -- batch progress updates
   - `update_cost_elements` -- batch update cost elements by ID
   - `delete_cost_elements` -- batch soft-delete cost elements by ID
2. **Shared params at top level** -- e.g., `create_cost_elements` has `wbe_id` as a top-level param; items array contains only per-item fields
3. **All-or-nothing (atomic)** -- if any item in the batch fails validation or creation, the entire batch rolls back
4. **New tools alongside existing ones** -- no breaking changes to single-entity tools
5. **No new service methods initially** -- batch tools loop through existing service methods within the single transaction managed by the `@ai_tool` decorator

### Non-Functional Requirements

- **Token efficiency**: Reduce total tokens consumed per bulk operation by ~40-60% (fewer tool-call overhead frames)
- **Latency**: Reduce wall-clock time for N-entity operations from O(N) round-trips to O(1)
- **Observability**: Maintain existing logging patterns (temporal logging, metadata)
- **RBAC compliance**: Batch tools must respect the same permission model as their single-entity counterparts

### Constraints

- **LangChain schema limitation**: LangChain's `@tool(parse_docstring=True)` generates schemas from function signatures. Complex nested types (`list[dict[str, Any]]`) may produce unclear LLM-facing schemas. Need a pragmatic approach.
- **Sequential tool enforcement**: `SequentialToolCallsMiddleware` forces `parallel_tool_calls=False`. Batch tools work within this constraint -- they are a single tool call.
- **EVCS temporal versioning**: Each entity version gets a unique `clock_timestamp()`. Sequential flushes within one transaction will naturally get distinct timestamps, preserving temporal ordering.
- **Session lifecycle**: The `@ai_tool` decorator calls `ToolSessionManager.commit()` on success and `rollback()` on any exception. The batch tool's loop must NOT catch exceptions that should trigger full rollback.

---

## Context Discovery

### Product Scope

- No specific user story references batch AI operations. This is an optimization of the AI tool layer.
- Business value: Faster AI interactions when setting up project structures (e.g., "create 10 cost elements for the mechanical assembly WBE").

### Architecture Context

- **Bounded contexts**: EVCS Core (versioning), AI Agent (tool layer)
- **Existing patterns to follow**:
  - `@ai_tool` decorator wraps async functions into `BaseTool` instances with RBAC metadata, session management, and commit/rollback lifecycle
  - All tools call service methods, never duplicate business logic
  - Service methods use `CreateVersionCommand` which calls `session.flush()` (not commit)
  - `ToolSessionManager.commit()` is called once by the decorator after the tool function returns
  - Error handling: tools catch exceptions and return `{"error": "..."}` dicts
- **Architectural constraints**:
  - Services flush but do not commit -- the decorator manages the commit boundary
  - `SequentialToolCallsMiddleware` ensures one tool call at a time
  - `BackcastSecurityMiddleware` checks RBAC permissions and risk levels per tool invocation

### Codebase Analysis

**Backend:**

- Tool registration: `/home/nicola/dev/backcast/backend/app/ai/tools/__init__.py` -- `create_project_tools()` assembles the tool list and caches it as singletons. New tools must be imported and added here.
- Tool decorator: `/home/nicola/dev/backcast/backend/app/ai/tools/decorator.py` -- `@ai_tool` creates `BaseTool` instances. The `wrapped_with_context` function manages session commit/rollback. It catches all exceptions and returns `{"error": ...}`, which means individual item failures inside a batch would need re-raising to trigger full rollback.
- Session manager: `/home/nicola/dev/backcast/backend/app/ai/tools/session_manager.py` -- `ToolSessionManager.commit()` / `rollback()` operates on task-local scoped sessions.
- Existing templates:
  - `/home/nicola/dev/backcast/backend/app/ai/tools/templates/cost_element_template.py` -- single-entity CE create/update/delete tools
  - `/home/nicola/dev/backcast/backend/app/ai/tools/templates/forecast_cost_progress_template.py` -- single-entity cost registration and progress entry tools
  - `/home/nicola/dev/backcast/backend/app/ai/tools/templates/crud_template.py` -- single-entity project/WBE tools
- Service methods:
  - `CostElementService.create_cost_element()` validates parent WBE, validates CE type, creates via `CreateVersionCommand`, auto-creates schedule baseline + forecast + initial progress entry, then `flush()`. Total: 4+ flushes per CE.
  - `WBEService.create_wbe()` validates parent project, creates via `CreateVersionCommand`, then flushes.
  - `CostRegistrationService.create_cost_registration()` creates via version command, flushes.
  - `ProgressEntryService.create()` creates via version command, flushes.
- Key observation: Service methods already use `flush()` not `commit()`. Multiple service calls within the same session will accumulate in the same transaction. The decorator commits once at the end. This means looping service calls within one `@ai_tool` function will naturally be atomic -- if any service call raises, the decorator catches the exception and rolls back the entire transaction.

**Frontend:**

- No frontend changes required. These are backend-only AI tool additions.

---

## Solution Options

### Option 1: Simple Loop with Early Exit (Recommended)

**Architecture & Design:**

Each batch tool is an `@ai_tool`-decorated async function that:
1. Accepts a top-level shared param (e.g., `wbe_id`) and a `list[dict]` of items
2. Validates all inputs up front (UUID parsing, required fields)
3. Loops through items, calling the existing service method for each
4. Collects results into a summary dict
5. On any exception from a service call, lets it propagate to the decorator (triggering rollback)

**Implementation:**

- New file: `backend/app/ai/tools/templates/batch_tools_template.py`
- Modify: `backend/app/ai/tools/__init__.py` (import and register 6 new tools)
- Modify: `backend/app/ai/tools/templates/__init__.py` (add `batch_tools_template` to imports/exports)

Each batch tool function signature uses `list[dict[str, str | float | None]]` for the items parameter. LangChain will generate a JSON schema with `items` as `type: array, items: type: object`. The LLM will construct the array of dicts from its natural language understanding.

Example schema for `create_cost_elements`:
- `wbe_id: str` (shared parent)
- `cost_element_type_id: str` (shared type, since CEs under same WBE often share type)
- `start_date: str | None` (shared schedule start)
- `end_date: str | None` (shared schedule end)
- `progression_type: str | None` (shared progression)
- `items: list[dict[str, str | float | None]]` (per-item: code, name, budget_amount, description)

Pre-flight validation checks all UUIDs and required fields before any service call, providing clear error messages about which item failed.

**Trade-offs:**

| Aspect          | Assessment                                              |
| --------------- | ------------------------------------------------------- |
| Pros            | Minimal code changes; reuses existing services; atomic by default via decorator rollback; easy to understand and maintain |
| Cons            | No per-item partial success (but this is a stated requirement); LangChain schema for `list[dict]` is less descriptive than typed objects |
| Complexity      | Low -- each tool is ~80-120 lines following the existing template pattern |
| Maintainability | Good -- follows established patterns; no new service layer code |
| Performance     | N service calls in one transaction, one commit. Each call does a flush (DB round-trip), but no commit overhead between items |

---

### Option 2: Pre-Validation with Detailed Per-Item Error Reporting

**Architecture & Design:**

Same as Option 1, but instead of letting exceptions propagate to the decorator, the batch tool catches per-item exceptions and collects them into a structured response. The tool performs a two-phase approach:

1. **Phase 1 -- Dry-run validation**: Loop through all items, calling service-level validation logic (without actually creating). Collect any validation errors.
2. **Phase 2 -- Execute**: Only if all items pass validation, loop through and create.
3. **Error response**: If any item fails during execution (not validation), roll back and return detailed errors showing which items succeeded conceptually before the failure.

**Implementation:**

- Same files as Option 1
- Additional helper functions for validation-only checks
- More complex error collection logic

**Trade-offs:**

| Aspect          | Assessment                                              |
| --------------- | ------------------------------------------------------- |
| Pros            | Richer error messages showing exactly which items failed and why; LLM can self-correct more effectively |
| Cons            | More complex code; dry-run validation duplicates some service logic; validation and execution are separate phases that could diverge |
| Complexity      | Medium -- two-phase validation adds significant logic per tool |
| Maintainability | Fair -- validation logic must be kept in sync with service methods |
| Performance     | Slightly worse due to double validation pass |

---

### Option 3: Typed Pydantic Models for Batch Items

**Architecture & Design:**

Instead of `list[dict]`, define Pydantic models for each batch item type (e.g., `CostElementBatchItem`, `WBEBatchItem`). The tool function accepts `list[CostElementBatchItem]` which gives LangChain a precise schema to generate.

**Implementation:**

- New file: `backend/app/models/schemas/batch.py` with Pydantic models for each batch item type
- New file: `backend/app/ai/tools/templates/batch_tools_template.py`
- LangChain `@tool(parse_docstring=True)` will generate schemas from the typed list parameter

**Trade-offs:**

| Aspect          | Assessment                                              |
| --------------- | ------------------------------------------------------- |
| Pros            | Strongest type safety; best schema for LLM; Pydantic validation on items |
| Cons            | More files and models to maintain; risk of schema duplication (batch item models vs existing Create models); LangChain may not serialize nested Pydantic models cleanly in tool schemas |
| Complexity      | Medium-High -- new schema models + potential LangChain schema generation issues |
| Maintainability | Fair -- batch item models must stay in sync with Create schemas |
| Performance     | Same as Option 1 (no runtime difference) |

---

## Comparison Summary

| Criteria           | Option 1: Simple Loop | Option 2: Pre-Validation | Option 3: Typed Models |
| ------------------ | --------------------- | ------------------------ | ---------------------- |
| Development Effort | Low (1 new file + reg) | Medium (2x logic per tool) | Medium-High (schemas + tools) |
| Schema Clarity     | Adequate (dict-based) | Adequate (dict-based)   | Best (typed Pydantic)  |
| Error Reporting    | Basic (first failure) | Best (per-item detail)  | Basic (first failure)  |
| Maintainability    | Best (minimal code)   | Fair (duplication risk) | Fair (sync burden)     |
| LLM Correctness    | Good                  | Good                     | Best                   |
| Best For           | First iteration, YAGNI | When per-item errors matter most | When schema precision is critical |

---

## Recommendation

**I recommend Option 1 (Simple Loop with Early Exit) because:**

1. **YAGNI alignment** -- The user's stated design decisions already confirm all-or-nothing semantics. Option 1 delivers exactly that with the least code.
2. **Decorator handles atomicity for free** -- The `@ai_tool` decorator already does commit-on-success / rollback-on-error. A loop of service calls inside one tool function is naturally atomic because services use `flush()` not `commit()`.
3. **Pre-flight validation covers the 80% case** -- Checking all UUIDs and required fields before the loop catches most errors (wrong parent, invalid type) with clear messages. Service-level errors (e.g., duplicate codes) will fail on the specific item and roll back the whole batch, which is the desired behavior.
4. **Same pattern as existing tools** -- Each batch tool follows the exact same structure as single-entity tools (import service, build schema, call method, convert result), just in a loop.

**Alternative consideration:** If LLM schema quality proves insufficient with `list[dict]` (LLM frequently malforms the items array), upgrade to Option 3 in a follow-up iteration by adding Pydantic batch item models.

**Risk level assignment for batch tools:**
- `create_*` batch tools: `RiskLevel.HIGH` (data modification, same as single-entity creates)
- `update_cost_elements`: `RiskLevel.HIGH` (data modification)
- `delete_cost_elements`: `RiskLevel.CRITICAL` (destructive, same as single-entity delete)

**Permission mapping:**
- `create_cost_elements` -> `["cost-element-create"]`
- `create_wbes` -> `["wbe-create"]`
- `create_cost_registrations` -> `["cost-registration-create"]`
- `create_progress_entries` -> `["progress-entry-create"]`
- `update_cost_elements` -> `["cost-element-update"]`
- `delete_cost_elements` -> `["cost-element-delete"]`

**Batch size limit:** Add a `max_items` cap (e.g., 50) to prevent excessively large batches that could timeout or exhaust resources. Validate `len(items) <= max_items` in pre-flight.

---

## E2E Test Data Analysis (2026-05-17)

Tool invocation data from 6 e2e test sessions confirms and expands batching opportunities:

### Tool Call Frequency (per session)

| Tool | Calls/Session | Batching Impact |
|------|---------------|-----------------|
| `create_wbe` | 27-35 | Eliminates 63% of all tool calls |
| `create_cost_element` | 8-31 | Second highest frequency |
| `create_cost_registration` | ~20 | Causes pool exhaustion (1-10s each) |
| `update_wbe` | ~6 | Additional batch candidate |
| `get_budget_status` | ~8 | Batch read candidate |
| `get_temporal_context` | 2 | Pre-injectable (not a tool) |
| `list_cost_element_types` | 1 | Cacheable (not a batch target) |

### Additional Batching Opportunities (Tier 2)

Based on e2e data, two additional batch tools beyond the original 6:

1. **`update_wbes`** — 6 calls/session for bulk WBE property changes. Items: `[{wbe_id, name?, code?, description?}]`
2. **`get_budget_status_batch`** — 8 calls/session for bulk budget status reads. Params: `cost_element_ids: list[str]`

### Performance Baseline

| Metric | Current | Target |
|--------|---------|--------|
| Tool calls per session | 33-59 | 3-5 (for bulk scenarios) |
| LLM round-trips per session | 13-15 | 3-5 |
| DB transactions per session | 33-59 | 1 per batch tool call |
| `create_cost_registration` latency | 1-10s per call | 1 call total |
| Pool exhaustion risk | HIGH (4+ parallel registrations) | ELIMINATED (1 atomic call) |

---

## Seed Permission Updates

### Affected Specialist: `project_manager`

Only the **project_manager** specialist needs batch tool permissions. It currently has 50 allowed_tools covering single-entity CRUD operations. The 8 new batch tool names must be added to its `allowed_tools` array.

**File:** `backend/seed/ai_specialist_configs.json` (project_manager entry, line 13-50)

**Tools to add:**
```json
"create_cost_elements",
"update_cost_elements",
"delete_cost_elements",
"create_wbes",
"update_wbes",
"create_cost_registrations",
"create_progress_entries",
"get_budget_status_batch"
```

**System prompt update:** Add guidance to `project_manager.system_prompt` about preferring batch tools for 2+ items:
```
BATCH TOOLS:
- When creating/updating/deleting 2+ entities of the same type, use the batch tool variant (e.g., create_cost_elements instead of create_cost_element).
- For single items, use the standard single-entity tool.
```

### Other Specialists

- **evm_analyst** — read-only, no batch tools needed
- **change_order_manager** — workflow tools, no batch pattern applicable
- **user_admin** — could benefit from batch user/dept creation in future iteration
- **forecast_manager** — read-heavy, no immediate batch need
- **visualization_specialist** — single diagram generation, no batch need
- **general_purpose** — `allowed_tools: null` means all tools available, batch tools included automatically
- **mcp_specialist** — `allowed_tools: null`, same as above

---

## Decision Questions

1. Should `create_cost_elements` also share `cost_element_type_id` at the top level, or should each item specify its own type? (Sharing is simpler but less flexible -- the LLM could always use the single-entity tool for mixed-type scenarios.)
2. Should batch tools include a `dry_run: bool = False` parameter that validates all items without executing, letting the LLM preview the batch? (This adds Option 2-like capability without the two-phase complexity.)
3. What batch size limit is appropriate? Default suggestion is 50 items per call. Is this sufficient for your use cases?

---

## References

- Tool decorator: `/home/nicola/dev/backcast/backend/app/ai/tools/decorator.py`
- Tool registration: `/home/nicola/dev/backcast/backend/app/ai/tools/__init__.py`
- Session manager: `/home/nicola/dev/backcast/backend/app/ai/tools/session_manager.py`
- Cost element template: `/home/nicola/dev/backcast/backend/app/ai/tools/templates/cost_element_template.py`
- Forecast/cost/progress template: `/home/nicola/dev/backcast/backend/app/ai/tools/templates/forecast_cost_progress_template.py`
- CRUD template (WBE/Project): `/home/nicola/dev/backcast/backend/app/ai/tools/templates/crud_template.py`
- Security middleware: `/home/nicola/dev/backcast/backend/app/ai/middleware/backcast_security.py`
- Sequential tool middleware: `/home/nicola/dev/backcast/backend/app/ai/middleware/sequential_tool_calls.py`
- Cost element service: `/home/nicola/dev/backcast/backend/app/services/cost_element_service.py` (create_cost_element at line 146)
- WBE service: `/home/nicola/dev/backcast/backend/app/services/wbe.py` (create_wbe at line 551)
- Cost registration service: `/home/nicola/dev/backcast/backend/app/services/cost_registration_service.py`
- Progress entry service: `/home/nicola/dev/backcast/backend/app/services/progress_entry_service.py`
- AI specialist configs (seed): `/home/nicola/dev/backcast/backend/seed/ai_specialist_configs.json`
- AI assistant configs (seed): `/home/nicola/dev/backcast/backend/seed/ai_assistant_configs.json`
