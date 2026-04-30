# Issue Log: Briefing Room Orchestrator

**Source:** test-findings.md (2026-04-27) — items verified against codebase.
**Updated:** 2026-04-28 — post-fix E2E test results added.
**Updated:** 2026-04-28 — full E2E UI test with Playwright (message 1 + follow-up).
**Updated:** 2026-04-28 — second E2E test with Playwright, Expert Mode, multi-specialist follow-up.
**Updated:** 2026-04-28 — IL-16/IL-18/IL-19/IL-21 fixed, verified with E2E Playwright test.
**Updated:** 2026-04-29 — Full E2E Playwright test (Expert Mode, deepseek-v4-flash, 2 messages). Verified all resolved issues, confirmed IL-15 still present, found new IL-23.
**Updated:** 2026-04-29 — E2E test after briefing enhancement deployment (Supervisor Analysis, Task History, structured findings). Verified new fields working. Confirmed IL-15/IL-23/IL-20 still present. Found new IL-24 (execution stall).

---

## Resolved in 2026-04-28 session

| ID | Issue | Resolution |
|----|-------|-----------|
| IL-12 | `get_briefing` always returns "No briefing available yet." | Fixed: added `_BriefingSupervisorState(AgentState[Any])` with `briefing: str` field, passed as `state_schema` to `langgraph_create_agent`. LangGraph now shares `briefing` between parent `BriefingRoomState` and supervisor subgraph. |
| IL-01 | Pre-dispatch routing prevention | Mitigated by IL-12 fix. Single-cycle execution now achieved for simple tasks. Supervisor reads briefing correctly and stops. |
| IL-02 | Supervisor re-plans after early exit | Mitigated by IL-12 fix. Supervisor can now see specialist work in briefing and synthesizes directly. |
| IL-13 | Misleading `project_id: None` in briefing scope | Fixed: removed `project_id` from briefing metadata. `ToolContext.project_id` already injects it into every tool call. The briefing scope was confusing specialists into targeting wrong projects. |
| IL-14 | Specialist scope creep (doing other specialist's work) | Fixed: added `SCOPE BOUNDARY` section to specialist briefing prompt. Specialists are instructed to focus on their domain and write `## Delegation Notes` for out-of-scope work. |
| IL-06 | Redundant orchestrator messages (5-6 Assistant bubbles) | Fixed: single Assistant bubble per message confirmed in E2E test. All supervisor/specialist output merged into one chat bubble. |
| IL-17 | Supervisor skips briefing before follow-up handoff | Fixed: confirmed in second E2E test — supervisor correctly called `get_briefing` at 14:23:07 before handoff at 14:23:12 on follow-up message. |
| IL-19 | `detect_evm_anomalies` Tool Crashes with Unexpected Keyword Argument | Fixed: corrected `get_evm_timeseries()` call signature in `detect_evm_anomalies` and `analyze_forecast_trends` — `start_date`/`end_date` replaced with `control_date`/`granularity=EVMTimeSeriesGranularity.WEEK`. |
| IL-18 | Sequential EVM Tool Calls Per Cost Element | Fixed: added empty-data guards in `detect_evm_anomalies` and `analyze_forecast_trends` returning clear error messages when `timeseries.points` is empty. Prevents specialist retry loop on zero-data projects. |
| IL-21 | Parallel Specialist Failure Cascades | Fixed: wrapped `specialist_graph.ainvoke()` in try/except in specialist wrapper. On exception, error is compiled into briefing and specialist marked completed — supervisor can continue with other specialists. |
| IL-16 | EVM Analyst Specialist Internal Loop (Recursion Limit) | RESOLVED by IL-19 + IL-18 + IL-21 fixes. E2E test confirmed: no recursion crash, 201s execution, full EVM response rendered. |
| IL-15 | Specialist targets wrong project (creates in session project instead of new) | STILL PRESENT — specialist updated existing project `CACCIA-TACCHINO-001` instead of creating new. WBEs added to session project context. |
| IL-23 | `detect_evm_anomalies` timezone comparison error: offset-naive vs offset-aware | NEW — tool returns error internally but doesn't crash (caught by IL-21 isolation). |
| — | Simplify cycle verified: `SPECIALIST_AGENT_NAMES` dynamic, `defaultdict` module-level, `configs_by_name` dict, comments cleaned | All changes confirmed in place via grep. |

## Deployed 2026-04-29 — Briefing Enhancement

| Change | File | Description |
|--------|------|-------------|
| `TaskAssignment` model | `briefing.py` | New model for tracking task delegation history (specialist, description, rationale) |
| Enhanced `BriefingSection` | `briefing.py` | Added `supervisor_rationale`, `key_findings`, `open_questions`, `delegation_notes` |
| Enhanced `BriefingDocument` | `briefing.py` | Added `supervisor_analysis`, `task_history` list; updated `to_markdown()` |
| Structured findings parser | `briefing_compiler.py` | New `parse_structured_findings()` — deterministic regex parser for `## Key Findings`, `## Open Questions`, `## Delegation Notes` |
| Extended compile | `briefing_compiler.py` | `compile_specialist_output()` accepts 4 new optional params |
| Handoff rationale/analysis | `handoff_tools.py` | Handoff tools accept `rationale` and `analysis` params; populates `task_history` instead of overwriting `metadata["current_task"]` |
| Specialist wrapper enrichment | `supervisor_orchestrator.py` | Specialist receives "Your Assignment" block with supervisor rationale; output parsed for structured sections; `_SCOPE_BOUNDARY` updated with output format instructions |
| Tests | `tests/ai/test_briefing.py` | 29 tests (15 new) covering new models, parser, markdown rendering |

**E2E verification:** Message 2 confirmed all new fields working — Supervisor Analysis, Task History with rationale, Key Findings section parsed and rendered in briefing panel.

---

## P0 — Critical

### IL-01: Pre-Dispatch Routing Prevention — MITIGATED

**Source:** Finding 4 (Test 2) — Router Architecture Issue, Option 4
**Severity:** HIGH → MITIGATED
**Effort:** M
**Description:** The router checks `task_completed` and `completed_specialists` AFTER LangGraph has dispatched the specialist node. This means the specialist runs even when the task is already done.
**Mitigation:** IL-12 fix makes the supervisor's `get_briefing` tool return correct state. The supervisor now makes informed delegation decisions. The router + early exit + max iteration guard provide defense-in-depth.
**2026-04-28 test result:** Single specialist cycle achieved for project creation. No redundant dispatch.

### IL-02: Supervisor Re-Plans After Early Exit — MITIGATED

**Source:** Finding 1 (Test 3) — Supervisor Infinite Loop
**Severity:** HIGH → MITIGATED
**Effort:** M
**Description:** After a specialist early-exits with "already completed," the supervisor used to re-plan. Now the supervisor can read the briefing correctly and sees the specialist's completed work.
**Mitigation:** IL-12 fix + supervisor prompt completion rules. Max iteration guard (`max_supervisor_iterations=3`) provides safety net.
**2026-04-28 test result:** No re-planning observed. Supervisor synthesized directly after specialist completion.

---

### IL-16: EVM Analyst Specialist Internal Loop on Follow-up (Recursion Limit) — RESOLVED

**Source:** 2026-04-28 E2E test — follow-up message triggered graph recursion crash
**Severity:** CRITICAL → RESOLVED
**Effort:** L
**Description:** On follow-up messages that involve EVM analysis, the `evm_analyst` specialist enters an internal loop making 12+ sequential `calculate_evm_metrics` and `get_evm_performance_summary` calls, each requiring ~30s LLM round-trip. The specialist hits the LangGraph recursion limit of 50 and crashes the entire graph execution, including any parallel specialists.
**Root Cause (updated):** The original hypothesis (IL-17: supervisor skips briefing) is now fixed. The actual root cause is the `evm_analyst` specialist itself:
1. Specialist has no internal iteration limit — makes unlimited sequential tool calls.
2. For newly-created projects with no progress data, EVM metrics return zeros. Specialist keeps trying different tools/approaches to get meaningful data.
3. `detect_evm_anomalies` crashes with `start_date` kwarg error (IL-19), triggering retry with alternative tools.
4. When parallel specialist fails, the entire graph execution is killed — other specialists' work is lost (IL-21).
**Resolution:** Fixed via IL-19 (tool signature fix), IL-18 (empty-data guards), IL-21 (error isolation in specialist wrapper).
**2026-04-28 E2E test result (1st test):** `Error 500: Recursion limit of 50 reached`. Specialist completed 26 tool calls, supervisor looped. Execution crashed at 419s (7 min).
**2026-04-28 E2E test result (2nd test):** `Error 500: Recursion limit of 50 reached during evm_analyst task`. 28 tool calls total (12x `calculate_evm_metrics`, 5x `get_evm_performance_summary`, 3x `global_search`, 2x `get_project_kpis`, etc.). Execution: 605s (10 min). `project_manager` specialist's WBE update was lost. User saw red error banner.
**2026-04-28 E2E test result (post-fix):** SUCCESS. No recursion crash. `evm_analyst` ran 16 tool calls (including `detect_evm_anomalies` — no TypeError), supervisor dispatched to `general_purpose` for synthesis. 35 total tool calls across 2 specialists. Execution: 201s (~3.3 min). User received complete EVM metrics table with CPI/SPI analysis. No errors in backend logs.
**2026-04-29 E2E test result (Expert Mode, deepseek-v4-flash):** SUCCESS. No recursion crash. Message 2 dispatched `project_manager` (WBE rename) then `evm_analyst` (8 EVM tools). `detect_evm_anomalies` hit IL-23 timezone error but was caught. 17 tool calls total, 103s execution (~1.7 min). EVM metrics table rendered with CPI/SPI analysis.

### IL-17: Supervisor Skips Briefing Before Follow-up Handoff — RESOLVED

**Source:** 2026-04-28 E2E test — supervisor behavior differs between message 1 and message 2
**Severity:** HIGH → RESOLVED
**Effort:** S
**Description:** In the original E2E test, the supervisor skipped `get_briefing` before handoff in follow-up messages.
**Resolution:** Fixed. Confirmed in second E2E test: supervisor correctly called `get_briefing` at 14:23:07, then dispatched two specialists in parallel at 14:23:12.
**2026-04-28 E2E test result (2nd test):** `get_briefing` → `handoff_to_project_manager` + `handoff_to_evm_analyst` (parallel). Briefing correctly read before delegation.
**2026-04-29 E2E test result:** Both messages confirmed `get_briefing` called before handoff. Message 1: get_briefing at 00:14:55 → handoff at 00:14:59. Message 2: get_briefing at 00:14:55 → handoff to project_manager at 00:14:59, then handoff to evm_analyst at 00:15:12 (sequential, not parallel — supervisor waited for project_manager to finish first).

---

### IL-18: Sequential EVM Tool Calls Per Cost Element — RESOLVED

**Source:** 2026-04-28 E2E test — specialist called get_budget_status/get_latest_progress/get_cost_element_summary sequentially
**Severity:** MEDIUM → CRITICAL → RESOLVED
**Effort:** M
**Description:** When computing EVM metrics, the `evm_analyst` specialist calls `calculate_evm_metrics`, `get_evm_performance_summary`, `get_project_kpis`, and other EVM tools sequentially — each followed by a ~30s LLM round-trip to decide the next call. For projects with no actual progress data, the specialist loops trying different approaches without stopping, eventually hitting the recursion limit.
**Resolution:** Added empty-data guards in `detect_evm_anomalies` and `analyze_forecast_trends` returning clear error messages when no timeseries data exists. Prevents the specialist from interpreting empty data as "failed to get data" and retrying.
**Impact:** ~7 min of execution time wasted on sequential LLM round-trips. Root cause of IL-16 recursion limit crash.
**2026-04-28 E2E test result (1st test):** Specialist made 6x `get_budget_status` + 6x `get_latest_progress` + 4x `get_cost_element_summary` = 16 sequential EVM calls, each separated by ~5-10s of LLM thinking time.
**2026-04-28 E2E test result (2nd test):** `evm_analyst` made 12x `calculate_evm_metrics` + 5x `get_evm_performance_summary` + 2x `get_project_kpis` + 1x `detect_evm_anomalies` + 1x `assess_project_health` = 21 sequential EVM calls over ~7 minutes, each separated by ~30s LLM thinking time. This directly caused the recursion limit crash (IL-16).
**2026-04-28 E2E test result (post-fix):** `detect_evm_anomalies` ran successfully without crash. Specialist completed in reasonable time. No retry loop observed.

### IL-20: No Per-Specialist Iteration Limit — DEFERRED

**Source:** 2026-04-28 E2E test (2nd) — `evm_analyst` made 21+ sequential tool calls
**Severity:** CRITICAL → MEDIUM (mitigated by IL-19/IL-18/IL-21 fixes)
**Effort:** M
**Description:** Individual specialists have no internal guard on how many tool calls they can make. The `evm_analyst` made 21 sequential tool calls in a single run before hitting the graph-level recursion limit of 50. Each call requires a ~30s LLM round-trip, so a runaway specialist wastes 10+ minutes.
**Impact:** With IL-19/IL-18/IL-21 fixes in place, the specialist no longer crashes the graph. However, specialists can still make excessive tool calls (16+ observed in post-fix test) leading to slow execution (~200s).
**Fix:** Add a per-specialist max tool call limit (e.g., 15). When reached, the specialist should return its findings immediately.
**2026-04-28 E2E test result (post-fix):** `evm_analyst` still made 16 tool calls in a single run. No crash (error isolation caught it), but execution was slower than ideal. Per-specialist cap would reduce this to ~60-90s.
**2026-04-29 E2E test result (post-briefing enhancement):** `project_manager` made ~32 tool calls for message 1 (project creation). Specialist noticed `progress_percentage` returned null and entered a verification loop: 10x create_progress_entry → 10x get_latest_progress → 9x get_latest_progress (second pass) → 3x get_budget_status. The specialist should have stopped after creating the entities. Per-specialist cap of 15-20 would prevent this.

---

## P1 — High

### IL-19: `detect_evm_anomalies` Tool Crashes with Unexpected Keyword Argument — RESOLVED

**Source:** 2026-04-28 E2E test (2nd) — `evm_analyst` specialist called detect_evm_anomalies
**Severity:** HIGH → RESOLVED
**Effort:** S
**Description:** The `detect_evm_anomalies` tool calls `EVMService.get_evm_timeseries()` with a `start_date` keyword argument that the method does not accept, causing a TypeError crash. The error is caught internally but returns an error result to the specialist, which then retries with alternative tools — contributing to the recursion limit issue (IL-16/IL-18).
**Resolution:** Fixed call signature in both `detect_evm_anomalies` and `analyze_forecast_trends` in `advanced_analysis_template.py`. Replaced `start_date`/`end_date`/`granularity="weekly"` with `control_date=datetime.now()`/`granularity=EVMTimeSeriesGranularity.WEEK`. Updated response payload to use `timeseries.start_date`/`timeseries.end_date`.
**2026-04-28 E2E test result:** `ERROR - Error in detect_evm_anomalies: EVMService.get_evm_timeseries() got an unexpected keyword argument 'start_date'`
**2026-04-28 E2E test result (post-fix):** `detect_evm_anomalies` ran successfully. `get_evm_timeseries` called with correct signature (only a performance warning: 1.67s). No TypeError.

### IL-03: Cache `get_temporal_context` Within Execution

**Source:** Finding 3 (Test 1) — Redundant Tool Calls, Recommendation 1
**Severity:** MEDIUM
**Effort:** S
**Description:** `get_temporal_context` is called before every specialist dispatch even though the context hasn't changed within a single execution. Should be cached (called once, reused).
**Impact:** ~1-2 redundant tool calls per execution, ~15s wasted time.
**2026-04-28 E2E test result (1st test):** Confirmed. Supervisor called `get_temporal_context` at 10:05:12, specialist called it again at 10:07:29. Each call requires a full LLM round-trip (~20s total wasted).
**2026-04-28 E2E test result (2nd test):** Improved. Supervisor did NOT call `get_temporal_context` in message 2. Only the `project_manager` specialist called it once. Still called once per specialist per execution.

### IL-04: Handoff Tool Guard for Completed Specialists

**Source:** Finding 4 (Test 2) — Router Architecture Issue, Option 2
**Severity:** MEDIUM
**Effort:** S
**Description:** Handoff tools (`create_handoff_tool`) don't check `completed_specialists` before allowing handoff. The tool itself could return early: "Specialist X already completed, skipping."
**Impact:** Defense-in-depth against redundant specialist dispatch.
**2026-04-28 test result:** Not needed for current single-cycle behavior. Becomes relevant if supervisor re-introduces loops.

### IL-05: Pass Temporal Context Through Handoff

**Source:** Finding 3 (Test 3) — Redundant Tool Calls in Specialist
**Severity:** MEDIUM
**Effort:** S
**Description:** The supervisor calls `get_temporal_context`, then the specialist calls it again independently. The context should be passed through the handoff mechanism.
**Impact:** 1 redundant tool call per specialist cycle (~20s wasted).
**2026-04-28 E2E test result (1st test):** Confirmed. Same data as IL-03 — supervisor and specialist each call `get_temporal_context` independently within the same execution.
**2026-04-28 E2E test result (2nd test):** Partially improved. Supervisor didn't call `get_temporal_context` in message 2, but the specialist still called it independently. The context is not passed through handoff.

### IL-15: Specialist Targets Wrong Project in Follow-up Messages — IMPROVED, STILL RISKY

**Source:** 2026-04-28 E2E test — follow-up message targeted wrong project
**Severity:** HIGH → MEDIUM (improved)
**Effort:** M
**Description:** In multi-turn conversations, follow-up messages ask about "the project you created" or "the last WBE." The specialist has no persistent context about which project was created in the previous turn.
**Root Cause:** The briefing scope previously had `project_id: None`, and the specialist's briefing only contains the original user request — not the project_id from previous specialist iterations. The `ToolContext.project_id` is also `None` for general conversations.
**Fix Applied (partial):** Removed `project_id` from briefing scope to stop the confusing `project_id: None` display. The remaining gap is that specialists need to discover the project from the briefing's Specialist Findings section (which contains the project_id from previous iterations).
**2026-04-28 E2E test result (1st test, follow-up message):** CONFIRMED. Specialist called `list_wbes` without `project_id` filter, returning WBEs from ALL projects. It then updated WBE `0a4ed56d...` (code RO-001, "Roofing" from a different project) to "Ceiling Works & Finishes" instead of the intended WBE `087b3f45...` (code CS-001, "Ceiling Systems" from the current project). Cross-project entity contamination confirmed.
**2026-04-28 E2E test result (2nd test, follow-up message):** IMPROVED. Specialist used `global_search` to find the project rather than blindly listing all. No cross-project contamination observed. However, `ToolContext.project_id=None` still means no session-level scoping — the specialist relies on LLM inference from briefing content to identify the correct project.
**2026-04-29 E2E test result (Message 1, Expert Mode):** STILL PRESENT. Chat session was scoped to project `CACCIA-TACCHINO-001` (2bd1b380...). Specialist was asked to "create a new project" but instead updated the existing project's name to "Casa Renovação 2026" and added 8 WBEs + 8 cost elements to it. `create_project` was called but the specialist then operated within the session's project context. Root cause: `ToolContext.project_id` is set from the chat URL, so all tool calls are scoped to the session project. The specialist cannot escape this scope.
**2026-04-29 E2E test result (post-briefing enhancement):** CONFIRMED. Project "Casa Nova Renovation Project" (CNR-2026-001, id=49224c6a) was created, but all 9 WBEs were linked to project `13f5fcda-...` — a different (nonexistent) project ID. The `create_wbe` calls used a wrong `project_id`. The new project has zero WBEs. Root cause unchanged: `ToolContext.project_id` scoping from chat URL.
**Remaining Work:** The specialist must scope `list_wbes` and `list_cost_elements` to the project created in the previous turn. Consider: (1) adding a structured `last_created_entities` field to the briefing, (2) filtering list queries by project_id extracted from briefing Specialist Findings, or (3) maintaining a session-level `active_project_id` that persists across turns.

### IL-23: `detect_evm_anomalies` Timezone Comparison Error — NEW

**Source:** 2026-04-29 E2E test (Message 2) — `evm_analyst` specialist called `detect_evm_anomalies`
**Severity:** MEDIUM
**Effort:** S
**Description:** `detect_evm_anomalies` raises `TypeError: can't compare offset-naive and offset-aware datetimes` when processing timeseries data. The error is caught internally and returned as an error message to the specialist (IL-21 isolation working correctly). The tool reports `status=success` despite the error, meaning the specialist receives a string error message rather than structured anomaly data.
**Impact:** Non-critical — error is swallowed, specialist continues with other EVM tools. However, the `detect_evm_anomalies` tool returns no useful data, wasting one LLM round-trip (~30s).
**2026-04-29 E2E test result:** `ERROR - Error in detect_evm_anomalies: can't compare offset-naive and offset-aware datetimes` at 00:15:26. Tool exited with status=success at 00:15:26. `assess_project_health` and `analyze_cost_variance` completed normally alongside it.
**2026-04-29 E2E test result (post-briefing enhancement):** STILL PRESENT. `ERROR - Error in detect_evm_anomalies: can't compare offset-naive and offset-aware datetimes` at 07:21:56 during message 2. Tool exited with status=success. EVM analyst continued with other tools and produced complete report.
**Fix:** Ensure consistent timezone handling in `detect_evm_anomalies` — either use `datetime.now(timezone.utc)` or strip timezone from comparison values.

---

### IL-21: Parallel Specialist Failure Cascades — Other Specialists' Work Lost — RESOLVED

**Source:** 2026-04-28 E2E test (2nd) — `evm_analyst` crash killed `project_manager`'s work
**Severity:** HIGH → RESOLVED
**Effort:** M
**Description:** When the supervisor dispatches two specialists in parallel (e.g., `project_manager` + `evm_analyst`) and one specialist hits the recursion limit and crashes, the entire graph execution is killed. The other specialist's work (e.g., a successful WBE update) is discarded. The user sees only the error, not the partial results.
**Resolution:** Wrapped `specialist_graph.ainvoke()` in try/except in the specialist wrapper (`supervisor_orchestrator.py`). On exception, the error is logged, compiled into the briefing as a specialist finding, and the specialist is marked completed. The supervisor can then continue with other specialists or synthesize partial results.
**2026-04-28 E2E test result:** `project_manager` specialist was dispatched and started working (3x `global_search` calls), but `evm_analyst` hit recursion limit at iteration 50. WBE "Ceiling" was NOT updated to "Ceiling Works & Finishing" despite the project_manager having the correct task.
**2026-04-28 E2E test result (post-fix):** No specialist crashes occurred (IL-19 fix eliminated the TypeError). The error isolation safety net is in place — confirmed by unit test (`test_returns_error_state_on_specialist_exception`).

---

### IL-24: Execution Stalls After Long Specialist Run — NEW

**Source:** 2026-04-29 E2E test (message 1, post-briefing enhancement)
**Severity:** HIGH
**Effort:** M
**Description:** After the `project_manager` specialist completed a long-running task (~32 tool calls, ~5 min), the supervisor's final synthesis DeepSeek call returned HTTP 200 OK but the graph execution hung. No new log entries were produced for 4+ minutes. The UI showed "Stop generation" with a disabled textbox. The specialist's work was visible in the chat (full project summary rendered) but the supervisor's final response never arrived. The user had to reload the page to continue.
**Root Cause:** Unknown. The last log entry was a successful DeepSeek API call at 07:14:39. The specialist completed at ~07:18 (`briefing length=12390`), but no supervisor synthesis log entries appeared. Possible causes: (1) DeepSeek streaming timeout, (2) graph state inconsistency after long specialist run, (3) WebSocket disconnect during long execution.
**Impact:** User must reload page after long executions. All specialist work is rendered but the supervisor's final summary is lost.
**2026-04-29 E2E test result:** Message 1 stalled after ~5 min specialist run. Page reload required. Message 2 (shorter, ~2.5 min) completed normally with no stall.

---

## P2 — Medium

### IL-06: Suppress Redundant Orchestrator Messages — RESOLVED

**Source:** Finding 4 (Test 1) — Redundant Chat Messages
**Severity:** MEDIUM → RESOLVED
**Effort:** M
**Description:** Each orchestrator cycle used to emit its own message to the chat, producing 5-6 "Assistant" messages per user request.
**2026-04-28 E2E test result:** Single Assistant bubble per message confirmed. All supervisor/specialist output merged into one chat bubble. Briefing panel shows "1 specialist" with collapsible findings.

### IL-07: Cache `list_cost_element_types` in Briefing

**Source:** Finding 3 (Test 1) — Redundant Tool Calls, Recommendation 2
**Severity:** LOW
**Effort:** S
**Description:** `list_cost_element_types` is called by each specialist independently. The result is static within an execution and could be cached in the briefing or tool context.
**Impact:** 1 redundant tool call per specialist cycle.

### IL-08: Add Explicit `target_date` to `get_temporal_context`

**Source:** Finding 5 (Test 1) — Inconsistent Date Calculations
**Severity:** LOW
**Effort:** S
**Description:** `get_temporal_context` returns `current_date` but no relative date helpers. When users say "15 days from now," each specialist independently computes the date, leading to inconsistent results.
**Impact:** Inconsistent project dates across specialist cycles.

### IL-09: Add Cycle Count Telemetry

**Source:** Finding 4 (Test 3) — Recommendations, Item 5
**Severity:** LOW
**Effort:** S
**Description:** No telemetry for specialist cycle counts per message. The iteration count is used for control flow but not logged for monitoring.
**Impact:** No observability into orchestrator efficiency.

---

### IL-22: UI Textbox Stuck Disabled After Backend Restart Mid-Execution

**Source:** 2026-04-28 E2E test — backend hot-reload caused WebSocket disconnect
**Severity:** MEDIUM
**Effort:** S
**Description:** When the backend server restarts (e.g., due to hot-reload) during an active agent execution, the WebSocket disconnects and reconnects, but the frontend textbox remains permanently disabled ("generating" state). The user must reload the page to continue chatting.
**2026-04-28 E2E test result:** Backend restarted at 14:10:36 during execution. WebSocket reconnected at 14:10:58. Textbox stayed disabled for 5+ minutes until page was manually reloaded.
**Impact:** User cannot send follow-up messages after a backend restart. Requires manual page reload.
**Fix:** Add a watchdog timer or execution status check — if no WebSocket messages received for >60s after reconnection, reset the "generating" state and re-enable the textbox.

---

## P3 — Low / Future

### IL-10: Dead State Parameters in BriefingRoomOrchestrator

**Source:** Finding S3 (Code Review) — Dead State
**Severity:** LOW
**Effort:** XS
**Description:** `enable_subagents` and `interrupt_node` are stored in `BriefingRoomOrchestrator.__init__` but never used by graph creation methods.
**Impact:** Dead code, minor confusion.

### IL-11: Evaluate Alternative Architecture for Single-Specialist Tasks

**Source:** Finding 4 (Test 2) — Recommendations, Item 4
**Severity:** LOW
**Effort:** L
**Description:** The briefing room pattern adds overhead (briefing compilation, handoff tools) for tasks that only need a single specialist. For simple CRUD tasks, a direct specialist dispatch would be more efficient.
**Impact:** ~30s overhead per request for supervisor pre-dispatch.
