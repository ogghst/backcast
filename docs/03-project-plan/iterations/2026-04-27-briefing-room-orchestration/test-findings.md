# Test Findings: Briefing Room Orchestrator Efficiency Audit

**Date:** 2026-04-27
**Test Type:** Live E2E UI test (Playwright MCP + backend log analysis + database verification)
**Assistant:** Senior Project Manager (ai-manager)
**Execution Mode:** Expert
**Request:** "create a new project for my family vacation, 15 days from now, duration 20 days. include expenses and planning for travel, accomodation, meals, leisure. create a detailed cost planning."
**Outcome:** Task completed functionally but with **critical efficiency issues** requiring manual stop after ~6 minutes

---

## Test Execution Summary

| Metric | Value |
|--------|-------|
| Wall-clock time | ~6+ minutes (manually stopped) |
| LLM API calls | 17 |
| Total tool calls | 33 |
| Specialist cycles | 2 completed + 1 in progress (stopped) |
| Chat messages generated | 5 (2 specialist + 3 orchestrator) |
| Projects created in DB | 3 (1 expected, 2 redundant) |
| WBEs created | 12 across 3 orphan project IDs (4 expected per project) |
| Cost elements created | 12 for the primary project |
| Backend errors | 0 |

---

## Finding 1: Orchestrator Loop (Severity: CRITICAL)

The briefing room orchestrator spawned **2 full specialist cycles** and started a **3rd** when manually stopped. After each specialist completed successfully and returned a briefing, the orchestrator spawned another assistant to "review" the briefing, which then called `handoff_to_project_manager` again.

### Observed Cycle Pattern

| Cycle | Specialist | Start | End | Duration | Briefing Size | Result |
|-------|-----------|-------|-----|----------|---------------|--------|
| 1 | project_manager | 17:53:52 | 17:55:26 | ~90s | 4,738 chars | Created full project (correct) |
| 2 | project_manager | 17:56:07 | 17:59:08 | ~130s | 8,249 chars | Found project exists, re-read it (redundant) |
| 3 | Assistant (stopped) | 17:59:11+ | - | - | - | Starting same intro text again |

### Root Cause Hypothesis

The orchestrator does not recognize task completion after a specialist successfully produces a briefing. The `Router` node after the briefing compiler does not have a termination condition that checks whether the task is done. Instead, it appears to always route back to the supervisor for "synthesis," which then decides to dispatch another specialist.

### Backend Log Evidence

```
17:55:26 - [BriefingRoom] Specialist project_manager completed, briefing length=4738
17:55:38 - get_briefing called again (post-specialist)
17:55:42 - get_temporal_context called again
17:55:59 - write_todos called again
17:56:07 - handoff_to_project_manager called AGAIN (2nd cycle)
...
17:59:08 - [BriefingRoom] Specialist project_manager completed, briefing length=8249
17:59:11 - HTTP Request: POST .../chat/completions (3rd cycle starting)
```

### Impact

- **Cost:** Each cycle burns 5-8 LLM API calls (~$0.10-0.20 per cycle with expert mode)
- **Time:** ~2 minutes of wasted wall-clock time per redundant cycle
- **User experience:** Chat shows duplicate messages, appears stuck in a loop
- **Data integrity:** Second specialist may create duplicate entities

### Recommended Fix

1. Add a **task completion signal** to the briefing state (e.g., `task_completed: bool`)
2. After each specialist completes, the router checks if the briefing contains a complete answer to the user's request
3. If `task_completed=True`, route directly to synthesis/END instead of back to the supervisor
4. Add a **hard iteration limit** (e.g., `max_specialist_cycles=3`) as a safety guard

---

## Finding 2: Duplicate Entity Creation (Severity: HIGH)

Three "Family Vacation" projects were created across the test runs:

| Project ID | Name | Code | WBEs |
|-----------|------|------|------|
| `5466a346` | Family Vacation | FAM-VAC-2026 | 0 |
| `7ea88928` | Family Vacation 2026 | FAMVAC-2026 | 0 |
| `420e8785` | Family Vacation 2026 | FAMVAC-2026 | 0 |

Plus 3 orphan project IDs with 4 WBEs each from previous runs. The second specialist in our test called `create_project` again (line 120-127 in logs), which succeeded silently, creating another duplicate.

### Backend Log Evidence

```
17:54:11 - create_project (1st specialist, expected)
...
17:56:35 - create_project (2nd specialist, DUPLICATE)
```

### Recommended Fix

1. The specialist should check for existing projects with the same name/code before creating
2. The `create_project` tool should return a clear error or "already exists" response
3. The orchestrator should pass the first specialist's results (project ID) to subsequent specialists via the briefing

---

## Finding 3: Redundant Tool Calls (Severity: MEDIUM)

### Tool Call Breakdown

| Tool | Calls | Expected | Waste | Notes |
|------|-------|----------|-------|-------|
| `get_temporal_context` | 3 | 1 | 2x | Called before every specialist dispatch |
| `write_todos` | 3 | 1 | 2x | Identical todo lists written 3 times |
| `handoff_to_project_manager` | 2 | 1 | 1x | Second dispatch for same task |
| `create_project` | 2 | 1 | 1x | Created duplicate project |
| `list_cost_element_types` | 2 | 1 | 1x | Same data fetched twice |
| `get_briefing` | 1 | 1 | 0x | Correct usage |
| `create_wbe` | 4 | 4 | 0x | All 4 in parallel (efficient) |
| `create_cost_element` | 12 | 12 | 0x | All 12 in parallel (efficient) |
| `get_project_structure` | 1 | 0 | 1x | Only needed for re-read |
| `get_project` | 1 | 0 | 1x | Only needed for re-read |
| `list_wbes` | 1 | 0 | 1x | Only needed for re-read |
| `list_cost_elements` | 1 | 0 | 1x | Only needed for re-read |
| **Total** | **33** | **~17** | **~16** | **48% waste** |

### Orchestrator-Level Redundancy

The orchestrator-level tools (`get_temporal_context`, `write_todos`, `get_briefing`) are called before EACH specialist dispatch, even when the context has not changed. This is a pre-dispatch ritual that should be cached within a single execution.

### Specialist-Level Efficiency

Within each specialist cycle, the tool usage was efficient:
- 4 WBEs created in a single parallel batch
- 12 cost elements created in a single parallel batch
- Correct sequencing: context -> project -> types -> WBEs -> cost elements

### Recommended Fix

1. **Cache temporal context** within a single execution (call once, reuse)
2. **Cache `list_cost_element_types`** result in briefing or tool context
3. **Eliminate pre-dispatch `write_todos`** or make it a single call at execution start

---

## Finding 4: Redundant Chat Messages (Severity: MEDIUM)

The chat displayed **5 response messages** for a single user request:

| # | Agent | Status | Content |
|---|-------|--------|---------|
| 1 | project_manager | working | Full project creation with budget breakdown |
| 2 | project_manager | working | "Project already exists" - re-read with tables |
| 3 | Assistant | Done | "I'll help you create... reviewing current context" |
| 4 | Assistant | Done | "I'll help you create... reviewing system state" |
| 5 | Assistant | generating | "I'll help you create..." (stopped) |

All 3 Assistant messages had near-identical intro text. The user sees 5 responses for one question, with the first specialist providing the actual answer buried among redundant orchestrator messages.

### Recommended Fix

1. The orchestrator should emit a **single consolidated response** at the end
2. Specialist streaming output should be visible (current behavior is fine)
3. Orchestrator intermediate messages ("I'll help you create...") should be suppressed or replaced with a lightweight status indicator

---

## Finding 5: Inconsistent Date Calculations (Severity: LOW)

The two specialist runs computed different project dates:

| Specialist | Start Date | End Date | Duration |
|-----------|------------|----------|----------|
| PM #1 | May 12, 2026 | June 1, 2026 | 20 days |
| PM #2 | May 11, 2026 | May 31, 2026 | 21 days |
| Database | 2026-05-11 | 2026-05-31 | 21 days |

The phrase "15 days from now" (today being April 27) is ambiguous:
- May 12 = 15 calendar days from April 27 (exclusive counting)
- May 11 = 15 calendar days from April 27 (inclusive counting)

### Recommended Fix

The `get_temporal_context` tool should return an explicit `target_date` calculation field that specialists reference, avoiding independent date math.

---

## Finding 6: Specialist Parallelism (Severity: INFO, Positive)

The specialist-level tool execution was well-optimized:

**WBE Creation (all 4 in parallel):**
```
17:54:22.653 - create_wbe (Travel)
17:54:22.653 - create_wbe (Accommodation)
17:54:22.654 - create_wbe (Meals)
17:54:22.655 - create_wbe (Leisure)
17:54:23.053 - All completed (~400ms total)
```

**Cost Element Creation (all 12 in parallel):**
```
17:54:42.838 - 12x create_cost_element fired simultaneously
17:54:46.258 - All completed (~3.4s total)
```

This parallelism is efficient and should be preserved.

---

## Database Verification

### Projects Table

3 duplicate "Family Vacation" projects found. Only 1 should exist.

### WBEs Table

12 WBEs across 3 orphan project IDs (from previous test runs). The WBEs from our test run were correctly structured (Travel, Accommodation, Meals, Leisure) but linked to project IDs that don't appear in the current projects table (possible EVCS versioning artifact or previous run cleanup).

### Cost Elements Table

Cost elements matching the expected names exist with correct budget amounts:
- Travel: Flights ($2,400), Rental Car ($800), Local Transportation ($400)
- Accommodation: Hotel/Resort ($3,200), Fees & Taxes ($400)
- Meals: Restaurant Dining ($2,000), Groceries ($600), Special Dining ($800)
- Leisure: Attractions ($1,200), Tours ($800), Entertainment ($600), Shopping ($400)

**Total: $13,600** - matches the specialist's reported budget.

---

## Action Items

### Immediate (Before Next Release)

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| A1 | Add max iteration guard to briefing room router (max 2-3 specialist cycles) | P0 | S |
| A2 | Add task completion detection in router (stop after successful briefing) | P0 | M |
| A3 | Cache `get_temporal_context` result within a single execution | P1 | S |
| A4 | Suppress redundant orchestrator messages in chat UI | P1 | M |

### Short-Term (Next Iteration)

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| B1 | Add deduplication check in `create_project` tool (check name/code) | P1 | S |
| B2 | Pass completed work artifacts (project_id) via briefing to prevent re-creation | P1 | M |
| B3 | Cache `list_cost_element_types` in briefing or tool context | P2 | S |
| B4 | Add explicit target_date to `get_temporal_context` output | P2 | S |

### Monitoring

| # | Metric | Target | Current |
|---|--------|--------|---------|
| M1 | Specialist cycles per request | 1-2 | 2-3+ (unbounded) |
| M2 | LLM API calls per simple request | <8 | 17 |
| M3 | Tool call waste ratio | <15% | ~48% |
| M4 | Redundant entity creation rate | 0% | >100% (2x duplicates) |
| M5 | Wall-clock time for CRUD request | <60s | ~360s+ |

---

## Test Artifacts

- **Baseline timestamp:** 2026-04-27 17:52:18
- **Send timestamp:** 2026-04-27 17:53:25
- **Stop timestamp:** 2026-04-27 17:59:56
- **Backend log window:** `backend/logs/app.log` lines matching `17:53 - 17:59`
- **Console errors:** 12 (antd deprecation warnings, not functional)
- **Database queries:** Projects, WBEs, Cost Elements tables verified

---

---

# Test Findings: Briefing Room Orchestrator - Post-Fix Verification

**Date:** 2026-04-27 (Afternoon)
**Test Type:** Live E2E UI test (Playwright MCP + backend log analysis + database verification)
**Assistant:** Senior Project Manager (ai-manager)
**Execution Mode:** Expert
**Request:** "create a new project to renew a house, 15 days from now, duration 200 days. include expenses and proper planning with consistent relationships for hydraulic, electrical, floors, roof, ceiling, heating systems, doors, windows, garden, gate."
**Outcome:** Task completed functionally with **partial fix effectiveness** - 2 specialist cycles instead of 3+, no duplicate entities created

---

## Test Execution Summary (Post-Fix)

| Metric | Pre-Fix | Post-Fix | Target | Status |
|--------|---------|----------|--------|--------|
| Specialist cycles | 3+ | 2 | 1 | ⚠️ Improved but not optimal |
| Wall-clock time | ~360s+ | ~360s | <120s | ❌ |
| LLM API calls | 17 | ~12 | <8 | ⚠️ Improved |
| Tool calls | 33 | ~35 | ~25 | ⚠️ Similar |
| Duplicate entities | Yes | No | No | ✅ Fixed |
| Functional completion | Yes | Yes | Yes | ✅ |

---

## Finding 1: Router Fix - PARTIALLY EFFECTIVE (Severity: MEDIUM)

### Observed Behavior

The orchestrator executed **2 specialist cycles**:

| Cycle | Start | End | Duration | Briefing Size | Tool Calls | Result |
|-------|-------|-----|----------|---------------|------------|--------|
| 1 | 19:38:56 | 19:42:59 | ~4 min | 6,888 chars | 35 | Created full project |
| 2 | 19:44:26 | 19:46:49 | ~2.5 min | 9,311 chars | 0 (read only) | Review only |

### Backend Log Evidence

```
19:42:59 - [BriefingRoom] Specialist project_manager completed, briefing length=6888
19:44:26 - handoff_to_project_manager called
19:44:27 - [BRIEFING_ROOM] Task completed flag set, ending workflow
19:46:49 - [BriefingRoom] Specialist project_manager completed, briefing length=9311
```

### Analysis

**What Works:**
- ✅ `completed_specialists` set correctly tracks executed specialists
- ✅ `task_completed` flag gets set appropriately
- ✅ Router logs "task completed flag set, ending workflow"
- ✅ **Second specialist did NOT create duplicates** - only performed read operations
- ✅ Functional completion achieved with correct data

**What Doesn't Work:**
- ❌ Router cannot prevent already-dispatched specialist from executing
- ❌ The check happens **after** LangGraph has dispatched the specialist node
- ❌ The router's return value only determines where to go **next**, not whether to cancel current dispatch

### Root Cause

LangGraph's execution model:
1. Supervisor produces AIMessage with `handoff_to_project_manager` tool call
2. Router sees tool call and routes to specialist node (specialist is **dispatched**)
3. Specialist executes (can take minutes)
4. After specialist completes, router checks `task_completed` flag
5. Router returns END, but specialist already ran

The fix is in the wrong place - it needs to prevent the handoff tool from being called in the first place, not prevent routing after the fact.

---

## Finding 2: No Duplicate Entities Created (Severity: INFO, Positive)

### Database Verification

**Projects:**
- Only 1 "House Renovation" project with correct structure
- No duplicate projects created

**WBEs (10 created):**
1. Hydraulic Systems (HYD) - $25,000
2. Electrical Systems (ELEC) - $20,000
3. Flooring (FLR) - $37,000
4. Roofing (ROOF) - $50,000
5. Ceiling (CEL) - $14,000
6. Heating Systems (HEAT) - $32,000
7. Doors (DOR) - $15,000
8. Windows (WIN) - $26,000
9. Garden (GARD) - $20,000
10. Gate (GATE) - $8,000

**Cost Elements:** 20 total (2 per WBE: Materials + Labor)

**Total Budget:** $247,000

The second specialist cycle performed only read operations:
- `get_briefing`
- `get_temporal_context`
- `write_todos`

No create operations were attempted.

---

## Finding 3: Tool Call Efficiency (Severity: INFO)

**Cycle 1 (Creation):**
- `create_project`: 1
- `list_cost_element_types`: 1
- `create_wbe`: 10 (parallel batch)
- `create_cost_element`: 20 (parallel batches)
- `get_project_structure`: 1
- `update_project`: 2

**Cycle 2 (Review):**
- `get_briefing`: 1
- `get_temporal_context`: 2
- `write_todos`: 1

**Waste:** ~9 tool calls (26% of total) in second cycle for review only.

**Positive:** Parallel execution of WBE and cost element creation remains efficient.

---

## Finding 4: Router Architecture Issue (Severity: HIGH)

### Problem

The router-based prevention pattern doesn't work with LangGraph's execution model. Once a node is dispatched, it runs to completion regardless of state changes that occur during its execution.

### Current Implementation (Doesn't Work)

```python
def router(state: BriefingRoomState) -> str:
    # Check 1: Programmatic completion signal
    if state.get("task_completed", False):
        return END
    
    # Check for handoff tool calls
    # ...
    if tool_name == f"handoff_to_{spec_name}":
        return spec_name  # Specialist already dispatched!
```

### Recommended Fix Options

**Option 1: Supervisor Prompt-Based Prevention**
- Strengthen supervisor prompt to check briefing content before handoff
- Include explicit "do NOT handoff if briefing contains completion markers"
- Less reliable but aligns with LLM behavior patterns

**Option 2: Handoff Tool Modification**
- Modify handoff tool to check `completed_specialists` before returning
- Tool itself could return early: "Specialist X already completed, skipping"
- More programmatic but requires tool signature changes

**Option 3: Specialist Node Early Exit**
- Specialist node checks if it's already in `completed_specialists` at start
- Returns immediately with "already completed" message
- Doesn't prevent dispatch but minimizes wasted execution

**Option 4: Conditional Edge Function Enhancement**
- Add pre-dispatch check before routing decision
- Requires deeper LangGraph customization

---

## Comparison: Pre-Fix vs Post-Fix

| Aspect | Pre-Fix | Post-Fix |
|--------|---------|----------|
| Specialist cycles | 3+ unbounded | 2 (consistent) |
| Duplicate entities | Yes | No |
| Task completion | Functional | Functional |
| Router logging | None | Clear logging |
| Cycle 2 behavior | Created duplicates | Read-only review |
| User experience | Confusing duplicates | Cleaner but still 2 cycles |

---

## Recommendations

### Immediate (High Priority)

1. **Implement Option 3 (Specialist Early Exit)** - Lowest effort, highest impact
   - Specialist checks `completed_specialists` at start
   - Returns immediately with summary if already completed
   - Reduces second cycle from ~2.5 min to <5 seconds

2. **Strengthen Supervisor Prompt** - Add explicit completion check instructions
   ```
   CRITICAL: Before calling handoff_to_X, check if the briefing already contains
   findings from specialist X. If so, respond directly with synthesis instead.
   ```

### Medium Priority

3. **Add Handoff Tool Guard** - Prevent redundant handoffs at tool level
4. **Consider Alternative Architecture** - Evaluate if briefing room pattern is optimal for single-specialist tasks

### Low Priority

5. **Add Metrics** - Track specialist cycle counts per request
6. **User UI Enhancement** - Show cycle count to users for transparency

---

## Conclusion

The fix is **partially effective**:
- ✅ Eliminated duplicate entity creation
- ✅ Added proper tracking and logging
- ✅ Reduced cycles from 3+ to 2
- ❌ Did not achieve single-cycle execution
- ❌ Router check happens too late in LangGraph flow

**Recommended Path Forward:** Implement Option 3 (Specialist Early Exit) combined with strengthened supervisor prompts for a defense-in-depth approach.

---

## Test Artifacts

- **Execution window:** 2026-04-27 19:38 - 19:50
- **Backend logs:** `backend/logs/app.log`
- **Database verification:** Projects, WBEs, Cost Elements tables verified
- **Chat session:** Cleared after completion

---

# Code Review: Supervisor Orchestrator Simplification

**Date:** 2026-04-27
**Review Type:** /simplify — Code Reuse, Quality, and Efficiency audit
**Files:** `supervisor_orchestrator.py`, `handoff_tools.py`, `subagent_compiler.py`, `deep_agent_orchestrator.py`
**Reference:** Context7 fetched `langgraph-supervisor-py` docs to validate patterns against official implementation
**Outcome:** 7 fixes applied across 4 files. One critical runtime bug caught before deployment.

---

## Finding S1: Handoff Tools Reference Non-Existent Graph Nodes (Severity: CRITICAL)

### Problem

`create_all_handoff_tools(subagent_configs)` created handoff tools for ALL configured specialists, but `compile_subagents()` could skip specialists with zero tools after RBAC filtering. If the LLM called `handoff_to_<filtered_specialist>`, LangGraph would crash — no graph node exists for that name.

### Impact

Runtime crash when RBAC or tool filtering removes a specialist but the supervisor still sees its handoff tool.

### Fix

Changed `create_all_handoff_tools` to receive the compiled `specialist_graphs` list instead of raw `subagent_configs`. Only successfully compiled specialists get handoff tools.

```python
# Before (bug):
handoff_tools = create_all_handoff_tools(subagent_configs)

# After (fixed):
handoff_tools = create_all_handoff_tools(specialist_graphs)
```

**Status:** Fixed

---

## Finding S2: Shared Middleware Instances Across Subagents (Severity: HIGH)

### Problem

`subagent_compiler.py` created a single middleware list and passed the same instances to all compiled subagents. `BackcastSecurityMiddleware` holds mutable state (`_approval_semaphore`, `_consecutive_approval_timeouts`). Shared instances could cause state leakage between agents.

### Fix

Middleware now created fresh per subagent inside the compilation loop. Also passes `subagent_tools` (not the full `available_tools`) to `BackcastSecurityMiddleware`.

**Status:** Fixed

---

## Finding S3: Dead State — `enable_subagents` and `interrupt_node` (Severity: MEDIUM)

### Problem

- `enable_subagents` was stored in `__init__` but never checked by `create_supervisor_graph()`. Setting it to `False` had no effect.
- `interrupt_node` was stored but hardcoded to `None` in both `BackcastSecurityMiddleware` calls. The middleware resolves the interrupt node via context vars at runtime — the parameter was always dead.

### Fix

Removed both parameters from `SupervisorOrchestrator.__init__` and the caller in `deep_agent_orchestrator.py`.

**Status:** Fixed

---

## Finding S4: Duplicate Router Logic (Severity: MEDIUM)

### Problem

`_make_supervisor_router()` and `_make_specialist_router()` contained near-identical logic — both scanned the last `AIMessage` for `handoff_to_{name}` tool calls. They differed only in the fallback return value (`END` vs `"supervisor"`).

### Fix

Unified into a single `_make_router(specialist_names, *, default=str)` with the fallback as a parameter.

**Status:** Fixed

---

## Finding S5: Duplicate Middleware Setup (Severity: MEDIUM)

### Problem

The middleware list `[TodoListMiddleware(), TemporalContextMiddleware(...), BackcastSecurityMiddleware(...)]` was duplicated between `create_supervisor_graph()` and `_build_fallback_graph()`.

### Fix

Extracted `_build_middleware(self, tools)` method used by both code paths.

**Status:** Fixed

---

## Finding S6: `METADATA_KEY_HANDOFF_DESTINATION` Never Set (Severity: MEDIUM)

### Problem

The constant was defined and exported but never attached to any tool's metadata. The official `langgraph-supervisor-py` sets `handoff_to_agent.metadata = {METADATA_KEY_HANDOFF_DESTINATION: agent_name}` to enable metadata-based routing detection without parsing tool names.

### Fix

Added `handoff_tool.metadata = {METADATA_KEY_HANDOFF_DESTINATION: agent_name}` inside `create_handoff_tool()`.

**Status:** Fixed

---

## Finding S7: Minor Cleanups (Severity: LOW)

- Replaced `specialist_names` append loop with list comprehension
- Replaced f-string logging args with `%s` format (avoids formatting when log level disabled)
- Verified `langgraph` is already a project dependency — custom handoff tools justified by Backcast-specific needs (RBAC integration, temporal context)

**Status:** Fixed

---

## Context7 Validation

Fetched documentation from `langgraph-supervisor-py` (library ID: `/langchain-ai/langgraph-supervisor-py`) and `langgraph` Python docs (library ID: `/websites/langchain_oss_python_langgraph`) to validate:

1. **`Command(goto=..., graph=Command.PARENT)`** pattern — confirmed correct for parent-graph subgraph routing
2. **`InjectedState` / `InjectedToolCallId`** — confirmed correct dependency injection for handoff tools
3. **`StateGraph.add_node(compiled_subgraph)`** — confirmed subgraphs with shared state keys work as implemented
4. **`create_handoff_tool` metadata** — confirmed the official library sets `METADATA_KEY_HANDOFF_DESTINATION` on tool metadata (our fix aligns)

---

## Files Changed

| File | Changes |
|------|---------|
| `ai/supervisor_orchestrator.py` | Removed dead params, unified router, extracted middleware factory, fixed handoff tools source |
| `ai/handoff_tools.py` | Added metadata to handoff tools |
| `ai/subagent_compiler.py` | Fresh middleware per subagent |
| `ai/deep_agent_orchestrator.py` | Removed dead params from SupervisorOrchestrator call |

All changes pass `mypy`, `ruff check`, and `ruff format`.

---

# Test Findings: Supervisor Infinite Loop + Session State Bug

**Date:** 2026-04-27 (Evening, ~22:23)
**Test Type:** Live E2E UI test (Playwright MCP + backend log analysis + database verification)
**Assistant:** Senior Project Manager (ai-manager)
**Execution Mode:** Expert
**Request 1:** "create a new project to renew a house, 15 days from now, duration 200 days. include expenses and proper planning with consistent relationships for hydraulic electrical, floors, roof, ceiling, heating systems, doors, windows, garden, gate"
**Request 2 (follow-up):** 'update the name of the last WBE you created to "Main Gate Entrance"'
**Outcome:** Message 1 completed functionally but supervisor entered infinite loop. Message 2 **failed entirely** due to stale session state.

---

## Test Execution Summary

| Metric | Message 1 | Message 2 |
|--------|-----------|-----------|
| Wall-clock time | ~7 min (manually stopped at ~3 min into loop) | ~2 min (manually stopped) |
| LLM API calls | ~16 (work) + ~10 (loop) | ~10 (all wasted) |
| Specialist cycles | 1 (work) + 3+ (loop) | 0 (blocked) |
| Functional result | Project created successfully | WBE not updated |
| Duplicate entities | No | N/A |

---

## Finding 1: Supervisor Infinite Loop After Specialist Completion (Severity: CRITICAL)

### Observed Behavior

After the `project_manager` specialist completed at 22:26:44, the supervisor entered an **infinite loop** that continued for 3+ minutes until manually stopped. Each loop iteration was identical:

```
22:27:15 → get_temporal_context + get_briefing (parallel)
22:27:23 → LLM call → write_todos + handoff_to_project_manager
22:28:08 → "Task completed flag set, ending workflow"
22:28:08 → "Specialist project_manager already completed, early exiting"
22:28:12 → LLM call (supervisor synthesizes... but then loops again)
22:28:34 → get_temporal_context + get_briefing AGAIN
22:29:04 → write_todos + handoff_to_project_manager AGAIN
22:29:06 → "Task completed flag set, ending workflow" AGAIN
22:29:06 → "Specialist project_manager already completed, early exiting" AGAIN
→ repeats...
```

### Timeline

| Time | Phase | Event |
|------|-------|-------|
| 22:23:26 | Start | WebSocket connect, graph compiled |
| 22:23:36 | Supervisor | `get_briefing` + `get_temporal_context` (parallel) |
| 22:23:46 | Supervisor | `write_todos` + `handoff_to_project_manager` |
| 22:23:51 | Specialist | `get_temporal_context` |
| 22:23:57 | Specialist | `create_project` |
| 22:24:00 | Specialist | `list_cost_element_types` |
| 22:24:08 | Specialist | `create_wbe` x10 (parallel) |
| 22:24:37 | Specialist | `create_cost_element` x20 (parallel) |
| 22:24:52 | Specialist | `get_project_structure` (verification) |
| 22:26:44 | Specialist | Completed (briefing=5882) |
| 22:26:47 | Supervisor | **Loop begins** — re-calls LLM |
| 22:27:15 | Supervisor | `get_temporal_context` + `get_briefing` again |
| 22:28:06 | Supervisor | `write_todos` + `handoff_to_project_manager` again |
| 22:28:08 | System | "Task completed flag set, ending workflow" |
| 22:28:34 | Supervisor | `get_temporal_context` + `get_briefing` AGAIN (3rd cycle) |
| 22:29:04 | Supervisor | `handoff_to_project_manager` AGAIN |
| 22:30:09 | Supervisor | Still looping (4th cycle detected) |
| 22:30:24 | User | Manually stopped generation |

### Root Cause

The supervisor receives the specialist's briefing, but instead of recognizing the task is done and synthesizing a final response, it decides to plan and delegate again. The `task_completed` flag prevents the specialist from re-executing, but does not prevent the supervisor from entering the plan-delegate cycle.

The supervisor is behaving as if it never "sees" the completion signal. After the specialist early-exits, the supervisor gets an empty/synthesized briefing back, interprets this as "the task is still pending," and loops.

### Impact

- **Cost:** ~10 wasted LLM API calls (~$0.30-0.50)
- **Time:** 3+ minutes of wasted time, requires manual intervention
- **UX:** 3-4 duplicate "Assistant" messages in chat, confusing for user
- **No max iteration guard:** The loop would continue indefinitely

---

## Finding 2: task_completed Flag Not Reset Between Messages (Severity: CRITICAL)

### Observed Behavior

After manually stopping the loop on message 1, the user sent a follow-up message: "update the name of the last WBE you created to 'Main Gate Entrance'". The supervisor attempted to delegate to `project_manager` specialist, but the `task_completed` flag was **still set from message 1**.

```
22:32:34 → handoff_to_project_manager
22:32:34 → "Task completed flag set, ending workflow"
22:32:35 → "Specialist project_manager already completed, early exiting"
→ Loops again with same pattern as message 1
```

The specialist **never executed** for message 2. The WBE "Gate" was never renamed.

### Database Verification

```sql
SELECT name FROM wbes WHERE code = 'WBE-GTE';
-- Result: "Gate" (unchanged)
```

### Root Cause

The `task_completed` flag in the briefing room state is session-scoped, not message-scoped. Once set during message 1, it persists for all subsequent messages in the same chat session. This means:

1. **Every follow-up message is broken** — specialist can never execute
2. **The only workaround** is starting a new chat session
3. **This is a regression** from the session-based architecture design

### Impact

- **Functional failure:** Follow-up messages cannot execute any specialist work
- **User experience:** Completely broken multi-turn conversation
- **Workaround:** Start a new chat for every message (defeats purpose of conversation)

---

## Finding 3: Redundant Tool Calls in Specialist (Severity: LOW)

The specialist called `get_temporal_context` at 22:23:51, but the supervisor had already called it at 22:23:36. The context could have been passed through the handoff mechanism.

| Tool | Supervisor Calls | Specialist Calls | Redundant |
|------|-----------------|-----------------|-----------|
| `get_temporal_context` | 1 | 1 | 1x |
| `get_briefing` | 1 | 0 | 0x |
| `write_todos` | 2 | 0 | 1x (2nd call) |

---

## Finding 4: Efficient Parallel Execution Within Specialist (Severity: INFO, Positive)

The specialist-level execution was well-optimized:

- **10 WBEs created in parallel** at 22:24:08 (all completed in ~2.5s)
- **20 cost elements created in parallel** at 22:24:37 (all completed in ~7s)
- **Correct sequencing:** context → project → types → WBEs → cost elements → verification
- **Proper verification step** with `get_project_structure`

---

## Database Verification (Message 1)

### Project

| Field | Value |
|-------|-------|
| ID | `a5918ae1-fb9a-4ff8-be8c-d17e194f269b` |
| Name | House Renovation Project |
| Code | HOUSE-RENO-2026 |
| Status | Draft |
| Start Date | May 12, 2026 |
| End Date | November 28, 2026 |

### WBEs (10 created)

| # | Name | Code | Budget |
|---|------|------|--------|
| 1 | Hydraulic Systems | WBE-HYD | $15,000 |
| 2 | Electrical Systems | WBE-ELE | $12,000 |
| 3 | Flooring | WBE-FLR | $18,000 |
| 4 | Roof | WBE-ROF | $25,000 |
| 5 | Ceiling | WBE-CEL | $8,000 |
| 6 | Heating Systems | WBE-HTG | $15,000 |
| 7 | Doors | WBE-DRS | $10,000 |
| 8 | Windows | WBE-WIN | $12,000 |
| 9 | Garden | WBE-GRD | $8,000 |
| 10 | Gate | WBE-GTE | $5,000 |

### Cost Elements (20 created, 2 per WBE)

Materials + Labor/Subcontractor split per WBE. Total: $128,000.

---

## Comparison: All Three Test Runs

| Metric | Test 1 (17:53) | Test 2 (19:38) | Test 3 (22:23) |
|--------|----------------|----------------|-----------------|
| Specialist cycles | 3+ unbounded | 2 | 1 + infinite loop |
| Duplicate entities | Yes | No | No |
| Follow-up worked | N/A | N/A | **No** |
| Task completion | Functional | Functional | Functional (msg 1) |
| Max iteration guard | None | None | **Still none** |
| Manual stop required | Yes | No | Yes |

---

## Action Items

### P0 — Critical

| # | Action | Details |
|---|--------|---------|
| C1 | **Reset task_completed per message** | The flag must be cleared at the start of each new user message. The briefing room state initialization must include `task_completed=False`. |
| C2 | **Add max iteration guard** | Hard limit of 2-3 specialist dispatch cycles per message. After that, force route to END with whatever briefing exists. |
| C3 | **Fix supervisor loop exit condition** | After specialist early-exits with "already completed," the supervisor should synthesize and stop — not re-plan. The supervisor prompt or routing logic must detect the early-exit signal. |

### P1 — High

| # | Action | Details |
|---|--------|---------|
| C4 | **Clear completed_specialists per message** | The `completed_specialists` set must be reset when a new message arrives in the same session. |
| C5 | **Pass context through handoff** | Avoid re-fetching `get_temporal_context` in the specialist if the supervisor already has it. |

### P2 — Medium

| # | Action | Details |
|---|--------|---------|
| C6 | **Suppress duplicate Assistant messages** | Only emit one final supervisor message, not one per cycle. |
| C7 | **Add cycle count telemetry** | Log specialist cycle count per message for monitoring. |

---

## Test Artifacts

- **Baseline timestamp:** 2026-04-27 22:21:57
- **Message 1 sent:** 2026-04-27 22:23:01
- **Message 1 stopped:** 2026-04-27 22:30:24
- **Message 2 sent:** 2026-04-27 22:32:42
- **Message 2 stopped:** 2026-04-27 22:34:17
- **Backend logs:** `backend/logs/app.log` + `backend/logs/app.log.1`
- **Console errors:** 8 (antd deprecation warnings, not functional)
- **Database verification:** Projects, WBEs, Cost Elements tables verified
