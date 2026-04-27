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
