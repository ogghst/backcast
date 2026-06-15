# AI Prompt & Context Building — Developer Guide

Reference for backend developers working on the Backcast AI subsystem (`backend/app/ai/`). Covers how the three prompt families — Planner, Supervisor, Specialist — are assembled, what context each receives, and how the shared `BriefingDocument` flows between them.

## Table of Contents

1. [TL;DR](#tldr)
2. [Graph & Memory Map](#graph--memory-map)
3. [The Planner](#1-the-planner)
4. [The Supervisor](#2-the-supervisor)
5. [The Specialist](#3-the-specialist)
6. [Shared Memory & Context Flow](#4-shared-memory--context-flow)
7. [Known Issues & Enhancement Opportunities](#5-known-issues--enhancement-opportunities)
8. [How to Extend / Debug](#6-how-to-extend--debug)

---

## TL;DR

The AI graph is `START → initialize_briefing → planner → supervisor ↔ specialists → END` (`backend/app/ai/supervisor_orchestrator.py:537-544`). There are three distinct prompt assembly points, each with a different context budget:

| Role | Prompt assembled | Receives conversation history? | Where its context lives |
|---|---|---|---|
| **Planner** | Per-call, from `_PLANNER_PROMPT_TEMPLATE` + live specialist catalog + `PydanticOutputParser` format instructions (`backend/app/ai/planner.py:109-130, 560-567`) | **No** — exactly one SystemMessage + one HumanMessage (`backend/app/ai/planner.py:574-584`) | Only the latest user request + optional briefing markdown for follow-ups (`backend/app/ai/planner.py:137-155`) |
| **Supervisor** | Once at graph-build time from `_BASE_SUPERVISOR_PROMPT` + specialist roster + delegation section (`backend/app/ai/supervisor_orchestrator.py:397-429`); `{plan_section}` filled per-call by `PlanAwareToolMiddleware` (`backend/app/ai/middleware/plan_aware_tools.py:245`) | **No raw history replay** — sees a `## Current Briefing` SystemMessage (`backend/app/ai/supervisor_orchestrator.py:218`) plus its own message thread, which `ContextGuardMiddleware` trims deterministically | The `BriefingDocument` is the memory; persisted at `ai_conversation_sessions.briefing_data` (`backend/app/models/domain/ai.py:237`) |
| **Specialist** | Per-specialist from DB `system_prompt` (or `DEFAULT_SYSTEM_PROMPT`), bound at compile time (`backend/app/ai/subagent_compiler.py:177`); context is a single isolated `HumanMessage` "assignment block" built per-invocation (`backend/app/ai/supervisor_orchestrator.py:772-816`) | **Never** — invoked with `[HumanMessage(assignment_block)]` only (`backend/app/ai/supervisor_orchestrator.py:814-816`) | The assignment block embeds the full `BriefingDocument.to_markdown()` (`backend/app/ai/supervisor_orchestrator.py:793-797`) plus plan-step context |

The mental model: **the briefing document is the memory, not the message log.** Follow-ups never replay history; `initialize_briefing_node` appends to `follow_up_requests` (`backend/app/ai/supervisor_orchestrator.py:475-476`) and the planner reads only the latest `HumanMessage` (`backend/app/ai/planner.py:323-341`).

---

## Graph & Memory Map

```
                       START
                         |
                         v
              initialize_briefing_node          <-- seeds/reuses BriefingDocument
                         |                          (appends follow-up on turn 2+)
                         v
                    planner_node                 <-- STATELESS: 1 SystemMsg + 1 HumanMsg
                    /         \                      emits PlanDocument -> state.plan_data
       (replan) <--'           `--> (resume / fresh)
                    |
                    v
              +--> supervisor  <----------------------> specialists (isolated)
              |        |  ^                              |
              |        |  `-- Command(goto="supervisor") | each specialist gets ONE
              |        |       after compile_specialist_ | HumanMessage (assignment block)
              |        |       output() appends a        | built from plan step + briefing
              |        |       BriefingSection           |
              |        v                                  v
              |   PlanAwareToolMiddleware              set_briefing(ContextVar)
              |   fills {plan_section} per call        get_briefing tool reads it
              |   filters tools -> delegation only
              |
              `-- request_replan --> planner (capped at max_replan_count=2)
                         |
                         v
                        END

  state.plan_data     -> ai_conversation_sessions.plan_data   (JSONB)
  state.briefing_data -> ai_conversation_sessions.briefing_data (JSONB)
  messages            -> ai_conversation_messages             (raw, NOT replayed)
```

Key edge wiring: `initialize_briefing → planner → supervisor` is static (`backend/app/ai/supervisor_orchestrator.py:537-539`); the `supervisor` node uses a conditional router that can dispatch to any specialist, back to `planner` (replan), or to `END` (`backend/app/ai/supervisor_orchestrator.py:540-544`). Specialist nodes return an explicit `Command(goto="supervisor")` (`backend/app/ai/supervisor_orchestrator.py:1129`) — there is no static specialist→supervisor edge.

---

## 1. The Planner

The planner is a single, **deliberately stateless** LLM call that decomposes the latest user request into a `PlanDocument` — either a single-step plan (`requires_planning=false`) routed to one specialist, or an ordered multi-step plan with dependencies (`backend/app/ai/planner.py:8-9`). It sits between `initialize_briefing` and `supervisor`.

### Build steps

1. **Select the path** in strict order: REPLAN (`replan_context` present AND existing `plan_data`) > RESUME (existing `plan_data` with an incomplete step — **no LLM call**) > FRESH (`backend/app/ai/planner.py:437-438, 520, 532-538`).
2. **Extract the user request** by reverse-scanning messages for the most recent `HumanMessage` (`backend/app/ai/planner.py:323-341`). No history is replayed.
3. **Build the system prompt** via `build_planner_system_prompt()`: pick the catalog (defaults to `_DEFAULT_SPECIALIST_CATALOG` = only `general_purpose`, `backend/app/ai/planner.py:62-67`), render the `## Available Specialists` bullets via `_build_specialist_section` (`backend/app/ai/planner.py:100-106`), pick the template (custom override or `_PLANNER_PROMPT_TEMPLATE`), and substitute the literal `{specialist_section}` placeholder via `render_prompt` (`backend/app/ai/planner.py:128-129`).
4. **Append format instructions** from `PydanticOutputParser(PlannerOutput).get_format_instructions()` as a plain string (`backend/app/ai/planner.py:560-567`). This is a deliberate decision (see Callouts) — `with_structured_output` is avoided because it uses function-calling internally, which DeepSeek rejects in thinking mode and z.ai/GLM cannot parse reliably (`backend/app/ai/planner.py:556-559`).
5. **Build the HumanMessage** via `_build_planner_prompt`: always `User request: {user_request}`; for follow-ups only, append `Existing briefing context (this is a follow-up):` + `BriefingDocument.to_markdown()` (`backend/app/ai/planner.py:137-155, 540-548`).
6. **Make exactly one LLM call** with `[SystemMessage, HumanMessage]` — two messages, no history. The call is wrapped in `invoke_with_retry` (transport-only retries with backoff) under a **pausable timeout** of `settings.AI_PLANNER_STEP_TIMEOUT` seconds (`backend/app/ai/planner.py:574-584`; `AI_PLANNER_STEP_TIMEOUT` at `backend/app/core/config.py:60`). The replan path mirrors this (`backend/app/ai/planner.py:465-485`).
7. **Parse + convert**: `parser.parse(content)` → `PlannerOutput` → `_convert_planner_output` validates each specialist against the catalog (unknown names silently rewritten to `general_purpose`, `backend/app/ai/planner.py:178-184`), renumbers `step_index` positionally (`backend/app/ai/planner:177`), and produces a `PlanDocument`.
8. **Fallback on failure**: the bare `except Exception` is split into two observable branches — `parse_failed` (WARNING, keeps a content snippet, returns `_fallback_plan`) vs `llm_call_failed` (ERROR via `logger.exception`, returns `_fallback_plan`). Both produce a single `general_purpose` step with `requires_planning=false` (`backend/app/ai/planner.py:585-599`; `_fallback_plan` at `298-320`). The replan path keeps the existing plan on either failure branch (`backend/app/ai/planner.py:486-500`).

### Real example (Line Alpha WBE comparison)

The HumanMessage built by `_build_planner_prompt` (no follow-up here):

```
User request: Compare number of wbe against one hour ago
```

The system message is `build_planner_system_prompt(...)` with the live catalog substituted into `{specialist_section}`, then `"\n\n" + parser.get_format_instructions()`. The catalog block looks like:

```
## Available Specialists

- project_manager: Specialist for project structure: projects, WBS Elements, Control Accounts, Work Packages, and Cost Elements
- time_traveller: Specialist for temporal context: change viewing date, switch branches, set branch mode (isolated/merged)
- evm_analyst: Specialist for EVM metrics calculation and project performance analysis
...
```

After `_convert_planner_output` + `PlanDocument.to_prompt_text()`, the plan stored in `state.plan_data` renders as:

```
## Execution Plan
Request: Compare number of wbe against one hour ago
Complexity: moderate
Steps: 5
  0. [completed] project_manager: Retrieve the total count of WBS Elements for the current project state.
  1. [completed] time_traveller: Set the effective date and time to one hour ago. (depends on [0, ...])
  2. [completed] project_manager: Retrieve the total count of WBS Elements as of the currently set effective date (one hour ago). (depends on [1])
  3. [completed] time_traveller: Reset the effective date and time back to the present. (depends on [2])
  4. [completed] project_manager: Compare the current WBS Element count against the historical count from one hour ago and report the variance. (depends on [0, 2])
```

The `(depends on [...])` marker is emitted by `to_prompt_text` whenever a step's `dependencies` list is non-empty (`backend/app/ai/plan.py:196`).

### Callouts

- **Stateless by construction.** One `SystemMessage` + one `HumanMessage` per call (`backend/app/ai/planner.py:574-584`). The only extra context on follow-ups is the briefing markdown appended to the HumanMessage (`backend/app/ai/planner.py:150-155`). History-aware reasoning is the supervisor's job, not the planner's.
- **`{specialist_section}` is substituted via `render_prompt`, not an f-string or `.format()`** (`backend/app/ai/planner.py:128-129`). This lets the whole template body be stored verbatim in `AIAssistantConfig.planner_prompt` without escaping braces. `render_prompt` is a single-pass, never-raises allowlisted `{tag}` substitution (`backend/app/ai/prompt_template.py:46`); unknown tags and stray `{`/`}` are left verbatim and injected values are never re-scanned, so **no brace-doubling is needed** in any template (the old `.format()` brace-doubling caveat is obsolete). The replan path uses the same `render_prompt` substitution (`backend/app/ai/planner.py:453-459`). If you write a custom template, either include `{specialist_section}` once (replaced) or omit it (section appended).
- **Do not "modernize" to `with_structured_output`.** The inline rationale at `backend/app/ai/planner.py:556-559` is load-bearing: it uses function-calling/tool_choice internally, which DeepSeek rejects in thinking mode and z.ai/GLM cannot parse reliably. Re-test on both providers before changing.
- **Specialist names are validated after the LLM responds, not constrained at generation.** Any name not in the catalog is silently rewritten to `general_purpose` with a warning (`backend/app/ai/planner.py:178-184`). An LLM hallucinating a specialist name does not crash, but it silently degrades the step.
- **Three execution paths, checked in strict order:** REPLAN > RESUME > FRESH (`backend/app/ai/planner.py:437-438, 520, 532-538`). The RESUME path makes re-entering the planner mid-execution cheap and idempotent — it returns the existing plan unchanged.
- **Replan locks completed steps.** `_merge_replanned_steps` keeps all `status=="completed"` steps verbatim and re-indexes revised steps after the last completed index (`backend/app/ai/planner.py:234-235, 260, 281`). On any replan failure it keeps the entire existing plan (`backend/app/ai/planner.py:486-500`).
- **The 5-step cap is advisory, not enforced in code.** It appears only in the prompt Rules (`backend/app/ai/planner.py:59, 94`); neither `_convert_planner_output` nor `_merge_replanned_steps` truncates. See [Known Issues](#5-known-issues--enhancement-opportunities).

---

## 2. The Supervisor

The supervisor is the parent agent in the "briefing-room" pattern. Its system prompt is assembled **once at graph-build time** from a base template plus a specialist roster and an optional delegation-enforcement section, then handed to `PlanAwareToolMiddleware` which fills `{plan_section}` and enforces delegation **per LLM call**.

### Build steps

1. **Start from the base prompt** — `_BASE_SUPERVISOR_PROMPT` (custom `supervisor_prompt` from DB overrides it, `backend/app/ai/supervisor_orchestrator.py:397`). It contains the literal `{plan_section}` placeholder inside `## Execution Plan` (`backend/app/ai/supervisor_orchestrator.py:131`) AND a `{specialist_section}` placeholder. `{plan_section}` is intentionally left unresolved at build time.
2. **Resolve `{specialist_section}` at build time** via `_build_supervisor_specialist_section()` emitting `## Available Specialists` from the compiled `specialist_graphs` (`backend/app/ai/supervisor_orchestrator.py:172-189, 404-410`). This is resolved BEFORE any other section is appended because specialist descriptions may contain literal `{braces}` that would collide with `.format()`/`.replace()`. The substitution itself now goes through `render_prompt` (`backend/app/ai/supervisor_orchestrator.py:406-408`), leaving the literal `{plan_section}` tag verbatim for the middleware pass.
3. **Append the delegation-enforced section** when `AI_DELEGATION_ENFORCED` is true (default, `backend/app/ai/config.py:60`): `_DELEGATION_ENFORCED_SECTION` is appended to the base prompt (`backend/app/ai/supervisor_orchestrator.py:159-169, 413-414`).
4. **Append the tool-access tail** — if `delegation_config.direct_tools` exists, a `## Available direct tools` suffix is appended; otherwise the strict `_BRIEFING_HANDOFF_SUFFIX` ("You do NOT have direct access...") is appended (`backend/app/ai/supervisor_orchestrator.py:192-195, 419-429`).
5. **Compile the agent** with the assembled `supervisor_prompt`, supervisor tools (`get_briefing`, `request_replan`, `handoff_to_*`, optional direct tools), and the middleware stack (`backend/app/ai/supervisor_orchestrator.py:431-440`).
6. **At run time, the briefing is injected as a SystemMessage** — `_briefing_update()` pushes `SystemMessage(content="## Current Briefing\n\n" + briefing_md)` into `messages` (`backend/app/ai/supervisor_orchestrator.py:197, 218`), called from `initialize_briefing_node` on the first turn or when reusing an existing briefing (`backend/app/ai/supervisor_orchestrator.py:451-486`).
7. **Per model call, `PlanAwareToolMiddleware.awrap_model_call`** runs: when an active multi-step plan exists (`AI_DELEGATION_ENFORCED` and `_has_active_plan`, `backend/app/ai/middleware/plan_aware_tools.py:75-81, 212`), it fills `{plan_section}` from `plan.to_prompt_text()` (`backend/app/ai/middleware/plan_aware_tools.py:245-250`), pre-filters `request.tools` to delegation + direct tools (`backend/app/ai/middleware/plan_aware_tools.py:103-115, 213-234`), appends a delegation suffix (`backend/app/ai/middleware/plan_aware_tools.py:250-264`), and post-filters hallucinated tool calls (`backend/app/ai/middleware/plan_aware_tools.py:118-181, 275-285`).
8. **When no plan is active**, the middleware still replaces the literal `{plan_section}` tag with `"No execution plan — delegate directly."` so the model never sees the raw placeholder (`backend/app/ai/middleware/plan_aware_tools.py:286-296`).

### Real example (Line Alpha WBE comparison)

The `{plan_section}` filled per-call from `plan.to_prompt_text()` for this 5-step plan:

```
## Execution Plan
Request: Compare number of wbe against one hour ago
Complexity: moderate
Steps: 5
  0. [completed] project_manager: Retrieve the total count of WBS Elements for the current project state.
  1. [completed] time_traveller: Set the effective date and time to one hour ago.
  2. [completed] project_manager: Retrieve the total count of WBS Elements as of the currently set effective date (one hour ago). (depends on [1])
  3. [completed] time_traveller: Reset the effective date and time back to the present.
  4. [completed] project_manager: Compare the current WBS Element count against the historical count from one hour ago and report the variance. (depends on [0, 2])
```

The `## Current Briefing` SystemMessage (built from `briefing_data` via `to_markdown()`):

```
## Current Briefing

# Briefing Document

## Request
Compare number of wbe against one hour ago

## Supervisor Analysis
User wants to compare WBE count between current time and one hour ago. This requires temporal context switching.

## Task History
1. **time_traveller**: Set temporal context to one hour ago to enable comparison of WBS counts
   - Rationale: Need to establish a time point from one hour ago to compare against current state.
2. **project_manager**: Retrieve the total count of WBS Elements for the current project state
3. **project_manager**: Retrieve the total count of WBS Elements as of the currently set effective date (one hour ago)
...
## Specialist Findings
### project_manager (Step 0)
...5 WBS Elements (Assembly Station 1 [2 children], Assembly Station 2 [1 child]).
...
```

When `AI_DELEGATION_ENFORCED` is true (default), the middleware also appends `_PLAN_DELEGATION_SUFFIX`:

```
## CRITICAL: PLAN-DRIVEN EXECUTION MODE
An execution plan with multiple steps is active. You are in DELEGATION-ONLY mode.

Your ONLY job is to:
1. Call get_briefing to review specialist findings from completed steps
2. Call handoff_to_{specialist} to delegate the NEXT pending plan step
3. Call request_replan if findings make remaining steps redundant or conflicting

You MUST NOT:
- Answer the user's question directly
- Use any domain tools (get_project, global_search, find_users, etc.)
- Attempt to gather information yourself
- Skip delegation because you think you can answer
...
```

### Callouts

- **`{plan_section}` is filled PER MODEL CALL** by `PlanAwareToolMiddleware` (`backend/app/ai/middleware/plan_aware_tools.py:245`), NOT at build time. This is why the base prompt is stored with the literal tag intact. If you edit `_BASE_SUPERVISOR_PROMPT`, never resolve `{plan_section}` at build time or the per-turn status markers (`[pending]`/`[in progress]`/`[completed]`) will go stale.
- **`{specialist_section}` IS resolved at build time** (`backend/app/ai/supervisor_orchestrator.py:404-410`), before any specialist-description text is appended, because those descriptions may contain literal `{braces}`.
- **`get_briefing` intentionally duplicates the `## Current Briefing` SystemMessage.** Both render `BriefingDocument.to_markdown()` from the same `briefing_data`. The duplication is by design — the prompt tells the supervisor to call `get_briefing` between steps, and `get_briefing` is in `_ALLOWED_PREFIXES` so it survives tool filtering (`backend/app/ai/middleware/plan_aware_tools.py:41`; tool at `backend/app/ai/supervisor_orchestrator.py:245-265`). `_ALLOWED_PREFIXES` is the always-allowed delegation tool set: `get_briefing`, `handoff_to_*`, `ask_user`, `request_replan` (`backend/app/ai/middleware/plan_aware_tools.py:41`) — `ask_user` is included so the supervisor can ask clarifying questions mid-plan.
- **The briefing SystemMessage is NOT re-appended on every supervisor turn.** It is pushed at briefing initialization (`backend/app/ai/supervisor_orchestrator.py:218`, called from `initialize_briefing_node` at `481-486`) and persists in the message list. On specialist completion the wrapper injects a plan-status SystemMessage (`backend/app/ai/supervisor_orchestrator.py:1043`), not a fresh briefing. `ContextGuardMiddleware` keeps the briefing visible across turns by replacing trimmed old messages with the compiled briefing.
- **Iteration cap is dynamic.** When a multi-step plan is active, `max_supervisor_iterations` is raised to `len(plan.steps)+1`, bounded by `min(len(plan.steps)+1, _MAX_PLAN_STEPS+1)` (`backend/app/ai/supervisor_orchestrator.py:597-599`). For the staged 5-step example the cap is 6. The replan cap is separate and fixed at 2 (`max_replan_count`, set in `_briefing_update` at `backend/app/ai/supervisor_orchestrator.py:222`, enforced in the router at `620-631`).
- **`_strip_disallowed_tool_calls` injects a synthetic `get_briefing` call** if it strips ALL of the model's tool calls — otherwise LangGraph would route to END with pending steps (`backend/app/ai/middleware/plan_aware_tools.py:118-181`). It also annotates content with a `[System: All your tool calls were disallowed...]` note.
- **Re-dispatch to the same specialist is allowed only in plan mode** (the specialist_node early-exits when no matching pending step exists, `backend/app/ai/supervisor_orchestrator.py:727-739`). In non-plan mode the router forces END if the supervisor tries to re-handoff to a completed specialist (`backend/app/ai/supervisor_orchestrator.py:640-646`).

---

## 3. The Specialist

A specialist is a self-contained LangChain agent graph compiled once per specialist config row and invoked many times. Its system prompt comes from the DB (`ai_assistant_configs.system_prompt` for rows where `agent_type='specialist'`), falling back to a tiny generic `DEFAULT_SYSTEM_PROMPT`. The defining property is **isolation**: a specialist never sees the supervisor's message history. The wrapper builds a single `HumanMessage` "assignment block" and invokes the specialist graph with only that message.

### Build steps

1. **Load specialist configs from DB** via `load_specialists_from_db()` (active `agent_type='specialist'` rows, 5-min TTL cache, `backend/app/ai/subagents/db_loader.py:74-105`). Each row → a dict via `assistant_config_to_specialist_dict` (`backend/app/ai/subagents/db_loader.py:49-63`): `name`, `description`, `presentation_prompt`, `system_prompt`, `allowed_tools`, `structured_output_schema` (FQCN resolved by `importlib`), `model_id`, `temperature`, `max_tokens`.
2. **Resolve tools per-specialist** inside `compile_subagents` (`backend/app/ai/subagent_compiler.py:98-227`) via a three-way convention: `None` → no tools (skipped with warning at `:168` if filtered to empty); `["*"]` → all available_tools; named list → intersected with available_tools (`backend/app/ai/subagent_compiler.py:143-166`). `available_tools` is pre-filtered by `filter_tools_for_context` (execution_mode then RBAC, `backend/app/ai/subagent_compiler.py:41-70`).
3. **Build a fresh middleware stack** per specialist to avoid mutable state leakage: `[SequentialToolCallsMiddleware?] + TemporalContextMiddleware + BackcastSecurityMiddleware` (`backend/app/ai/subagent_compiler.py:73-95, 175`).
4. **Compile the agent** with `response_format=schema` (defaults to `SpecialistOutput`, `backend/app/ai/schemas.py:8-30`, unless the DB row set a domain-specific `structured_output_schema`) and per-name model resolution (`backend/app/ai/subagent_compiler.py:131, 177-184`).
5. **At invocation, the wrapper resolves the active plan step** matching this specialist (`backend/app/ai/supervisor_orchestrator.py:676-691`), then builds the **assignment block**.
6. **Plan-driven assignment block** (`backend/app/ai/supervisor_orchestrator.py:772-801`): `## Your Assignment (Plan Step N/M)` (N = `step_index + 1` 1-based), task description, `**Expected output:**`, optional `**Context from previous steps:**` + per-dependency `Step {idx} result:` lines, then `## Briefing Context (from prior specialists)` with the full `doc.to_markdown()`, then original + follow-up request context lines.
7. **Non-plan assignment block** (`backend/app/ai/supervisor_orchestrator.py:802-812`): `## Your Assignment` + task + optional rationale + briefing.
8. **Build the isolated message list** — `isolated_messages = [HumanMessage(content=assignment_block)]` — and expose the briefing via a ContextVar (`set_briefing(...)`, `backend/app/ai/supervisor_orchestrator.py:814-819`; `backend/app/ai/tools/briefing_tools.py:25-39`).
9. **Invoke the specialist graph** with only that message list, under a **pausable timeout** of `settings.AI_SPECIALIST_STEP_TIMEOUT` with `invoke_with_retry` transport retries (`backend/app/ai/supervisor_orchestrator.py:855-872`).
10. **Prefer structured output over text fallback** — if `result['structured_response']` has a `.summary` (`SpecialistOutput`), use it; else fall back to `extract_final_ai_response(messages)` + `parse_and_clean()` (`backend/app/ai/supervisor_orchestrator.py:959-977`).
11. **Compile the result back into the briefing** via `compile_specialist_output()` which appends a `BriefingSection` (`backend/app/ai/supervisor_orchestrator.py:979-986`; `backend/app/ai/briefing_compiler.py:108-129`).

### Real example (assignment block for project_manager, plan step index 2)

Reconstructed assignment block the supervisor hands to `project_manager` for plan step index 2 (deps `[1]`) in the staged session. Step index 2 displays as "Step 3/5" (`step_index + 1` / total). The dependency (step 1, `time_traveller`) is completed, so its `result_summary` is appended. The briefing-so-far carries sections from steps 0 and 1.

```
## Your Assignment (Plan Step 3/5)

Retrieve the total count of WBS Elements as of the currently set effective date (one hour ago).

**Expected output:** Historical count of WBS Elements from one hour ago

**Context from previous steps:** (none set on the step) - Step 1 result: Set as_of to 2026-06-12T03:32:00; branch main, merged mode.

## Briefing Context (from prior specialists)

# Briefing Document

## Request
Compare number of wbe against one hour ago

## Supervisor Analysis
User wants to compare WBE count between current time and one hour ago. This requires temporal context switching.

## Task History
1. **time_traveller**: Set temporal context to one hour ago to enable comparison of WBS counts
   - Rationale: Need to establish a time point from one hour ago to compare against current state.
2. **project_manager**: Retrieve the total count of WBS Elements for the current project state

## Execution Plan
Step 1: [project_manager] Retrieve the total count of WBS Elements for the current project state. — completed
Step 2: [time_traveller] Set the effective date and time to one hour ago. — completed
Step 3: [project_manager] Retrieve the total count of WBS Elements as of the currently set effective date (one hour ago) — in_progress
...
## Specialist Findings

### project_manager (Step 0)

Total WBS Elements: 5 (Assembly Station 1 [2 children], Assembly Station 2 [1 child]).

**Key Findings:**
- 5 WBS Elements existed one hour ago (03:32 AM on 2026-06-12)
- WBS count has not changed in the past hour — both current and historical states show 5 elements
- Project structure remained stable with two main branches

---

### time_traveller (Step 1)

Set as_of to 2026-06-12T03:32:00; branch main, merged mode.

---

**Original request: Compare number of wbe against one hour ago**
```

This is the ONLY message in the specialist's message list — there is no supervisor history, no prior tool calls, no other specialists' raw tool outputs. The specialist either reads this markdown directly or calls its `get_briefing` tool for the structured form.

### Callouts

- **Isolation is enforced by construction, not convention.** `isolated_messages = [HumanMessage(...)]` (`backend/app/ai/supervisor_orchestrator.py:814-815`) and the graph is invoked with ONLY that list (`:855-872`). A specialist literally cannot see supervisor or sibling messages — debug expectations accordingly.
- **The `handoff_tools.py` module docstring is misleading.** It claims "Handoff preserves full message history" (`backend/app/ai/handoff_tools.py:4-5`), but the receiving specialist node rebuilds a single isolated `HumanMessage`. See [Known Issues](#5-known-issues--enhancement-opportunities).
- **Plan step display is 1-based** (`step_index + 1`, `backend/app/ai/supervisor_orchestrator.py:775`) but dependency references in `Step {idx} result:` are 0-based raw `step_index` (`backend/app/ai/supervisor_orchestrator.py:791`). Do not confuse them when reading logs.
- **Tool filtering has three layers that compose:** (1) `filter_tools_for_context` prunes the whole pool by execution_mode + RBAC; (2) the specialist's `allowed_tools` (None/`[*]`/list) narrows it; (3) a specialist ending up with zero tools is **silently skipped** (`backend/app/ai/subagent_compiler.py:168`). A missing specialist in the graph is usually an empty-tool-list filter problem, not a DB load failure.
- **A specialist's `system_prompt` comes from the specialist config dict** (`backend/app/ai/subagents/db_loader.py:57`), NOT from `_build_system_prompt` (which wraps the SUPERVISOR's prompt). Specialists rely on the assignment block + `TemporalContextMiddleware` + their `get_briefing` tool for context. If a specialist seems unaware of the project, the `system_prompt` in its DB row is the place to fix it.
- **Per-specialist models.** Each specialist row can have its own `model_id` resolved to a different provider (`backend/app/ai/subagent_compiler.py:131` via `backend/app/ai/agent_service.py:782`). One specialist failing to resolve its model just logs a warning and falls back to the main model — it does not break the whole graph.
- **`SpecialistOutput` is preferred, not guaranteed.** If the model did not emit parseable structured output, the code falls back to `extract_final_ai_response` + `parse_and_clean` (`backend/app/ai/supervisor_orchestrator.py:974-977`), which regex-strips `## Key Findings` / `## Open Questions` / `## Delegation Notes` from free text (`backend/app/ai/briefing_compiler.py:41-105`). A specialist whose DB row sets a custom `structured_output_schema` overrides this entirely.
- **`reasoning_content` propagation** (`backend/app/ai/handoff_tools.py:89`) is required because DeepSeek thinking mode rejects an assistant message missing it when enabled; the synthesized empty `AIMessage` carries it across the PARENT boundary (`backend/app/ai/handoff_tools.py:96-107`).

---

## 4. Shared Memory & Context Flow

The AI subsystem replaces raw message-history replay with a single accumulating memory artifact: the `BriefingDocument`.

### BriefingDocument accumulation

`BriefingDocument` (`backend/app/ai/briefing.py:35`) is a pure-Pydantic model with: `original_request`, `follow_up_requests` (list[str]), `sections` (list[BriefingSection]), `supervisor_analysis`, `task_history` (list[TaskAssignment]), `plan` (list[dict]). Pure data — no LangChain dependency — so it round-trips cleanly through JSONB.

Each specialist's contribution is a `BriefingSection` (`backend/app/ai/briefing.py:22`): `specialist_name`, `findings`, `task_description`, `supervisor_rationale`, `key_findings`/`open_questions`/`delegation_notes`, `step_index`. The single write path that grows sections is `compile_specialist_output()` (`backend/app/ai/briefing_compiler.py:108-129`), called from the specialist wrapper after each run (`backend/app/ai/supervisor_orchestrator.py:979-986`).

### to_markdown()

`BriefingDocument.to_markdown()` (`backend/app/ai/briefing.py:59-126`) serializes into the canonical markdown injected into every prompt: `# Briefing Document`, `## Request`, `## Follow-up Questions`, `## Supervisor Analysis`, `## Task History`, `## Execution Plan`, then `## Specialist Findings` (one `###` per `BriefingSection` with `key_findings`/`open_questions`/`delegation_notes` bullets). This single string is the common currency shared by the supervisor system message and specialist assignment blocks.

`from_state()` (`backend/app/ai/briefing.py:48-54`) is the safe-deserialization boundary — it reconstructs the document from a raw state dict with `model_validate`, falling back to a stub (`original_request="(recovered)"`) on any validation error.

### Persistence to ai_conversation_sessions

`briefing_data` (JSONB, `backend/app/models/domain/ai.py:237`) and `plan_data` (JSONB, `backend/app/models/domain/ai.py:242`) live on `AIConversationSession` (`backend/app/models/domain/ai.py:201`). They are reloaded across turns, so accumulated findings and plan progress survive between graph invocations. `AIConversationMessage` still stores raw messages, but the orchestrator favors `briefing_data`/`plan_data` as the working memory rather than replaying the full message log.

### Follow-up compaction

Follow-ups never replay prior history. `initialize_briefing_node`, on seeing existing `briefing_data`, calls `BriefingDocument.from_state(...).follow_up_requests.append(user_request)` and reuses the document (`backend/app/ai/supervisor_orchestrator.py:475-476`). The planner mirrors this with `_extract_user_request` (`backend/app/ai/planner.py:323-341`), which scans messages in reverse for only the latest `HumanMessage`.

### Config-driven prompts (AIAssistantConfig columns)

Each `ai_assistant_configs` row (`backend/app/models/domain/ai.py:121`) drives prompt assembly:

| Column | Purpose |
|---|---|
| `system_prompt` (`:142`) | Supervisor base prompt (specialists use the dict `system_prompt` instead) |
| `planner_prompt` (`:143`) | Custom planner template; supports `{specialist_section}` |
| `supervisor_prompt` (`:148`) | Custom supervisor template; supports `{specialist_section}` and `{plan_section}` |
| `presentation_prompt` (`:131`) | Injected into planner/supervisor/handoff prompts to describe capabilities |
| `allowed_tools` (`:171`) | JSONB whitelist (None / `["*"]` / named list) |
| `delegation_config` (`:176`) | `{direct_tools: [...], allowed_specialists: [...]}` |
| `structured_output_schema` (`:181`) | Specialist Pydantic class (FQCN) |
| `max_supervisor_iterations` (`:158`) | Iteration cap override |

Specialists are loaded from these rows by `load_specialists_from_db()` (`backend/app/ai/subagents/db_loader.py:74`). The `_BASE_SUPERVISOR_PROMPT` is only the fallback when `supervisor_prompt` is null.

### Per-turn {plan_section} mutation by PlanAwareToolMiddleware

The supervisor base prompt is stored with the literal `{plan_section}` tag intact. On every model call, `PlanAwareToolMiddleware.awrap_model_call` (`backend/app/ai/middleware/plan_aware_tools.py:205`) inspects state for an active plan and:

- When a plan exists: replaces `{plan_section}` with `plan.to_prompt_text()` (`backend/app/ai/middleware/plan_aware_tools.py:245-250`), strips domain tools, appends a delegation suffix, post-filters hallucinated tool calls.
- When no plan exists: replaces `{plan_section}` with `"No execution plan — delegate directly."` so the model never sees the raw tag (`backend/app/ai/middleware/plan_aware_tools.py:286-296`).

### Context-rot mitigations (deterministic, no extra LLM call)

- **`token_estimator.py`** (`backend/app/ai/token_estimator.py:32`) applies a chars/4 heuristic; `log_context_usage_estimate()` logs estimated input tokens vs the model context window before invocation. This is the visibility layer that exposes growth, not a mitigation itself.
- **`ContextGuardMiddleware`** (`backend/app/ai/middleware/context_guard.py:161`) trims supervisor history when estimated tokens exceed `AI_CONTEXT_SUMMARY_THRESHOLD_PCT` of `AI_CONTEXT_TOKEN_LIMIT`. It keeps the first message (system prompt) and last `AI_CONTEXT_KEEP_RECENT` messages, replacing the middle with a single `HumanMessage` built from `briefing_data.to_markdown()` (`backend/app/ai/middleware/context_guard.py:147`), then `_repair_chain()` (`backend/app/ai/middleware/context_guard.py:43`) rebuilds tool-call/tool-message pairs. **No extra LLM call** — uses the already-compiled briefing as the summary. Specialists are exempt (they get isolated fresh message lists).
- **Tunables** (`backend/app/ai/config.py:48-56`): `AI_CONTEXT_TOKEN_LIMIT` (default 120000), `AI_CONTEXT_SUMMARY_THRESHOLD_PCT` (80), `AI_CONTEXT_KEEP_RECENT` (8). Env-var driven.

---

## 5. Known Issues & Enhancement Opportunities

> **Update 2026-06-14:** the three correctness issues below — planner parse fragility, unbounded plan steps, and ContextGuard trim drops — are **all RESOLVED** (commit `feat(ai): harden graph execution`, branch `llm_per_specialist`). Each is marked ✅ below with the fix. Issues #4 (handoff docstring) and #5 (delegation-rule duplication) remain open (low priority).

Only verified issues are listed. Each carries a severity badge and category.

### Quality / correctness

**✅ RESOLVED (2026-06-14) — planner parse resilience.** `_extract_json()` now tolerantly extracts a fenced ```` ```json ```` block or the first balanced `{...}` before parsing, on BOTH the fresh and replan paths; the bare `except` is split into `parse_failed` (WARNING, with a content snippet) vs `llm_call_failed` (ERROR). DeepSeek/GLM reasoning preamble no longer silently collapses multi-step plans to a single `general_purpose` step. Tests: `backend/tests/ai/test_planner_parse.py`. *(Original issue kept below for history.)*

**[LOW · correctness] PydanticOutputParser is fragile — stray content before the JSON fence silently degrades to a `general_purpose` fallback.**
`planner_node` parses the raw string response with `parser.parse(content)` (`backend/app/ai/planner.py:442`). DeepSeek in thinking mode and GLM frequently emit reasoning preamble before unfenced JSON. Any parse failure is caught by the bare `except Exception` (`backend/app/ai/planner.py:445-447`) and silently replaced with `_fallback_plan` — a single `general_purpose` step (`backend/app/ai/planner.py:243-265`) that discards the entire multi-step intent. The same fragility exists on the replan path (`backend/app/ai/planner.py:364`, except at `366-368`). There is no telemetry surfacing how often the fallback fires.
*Recommendation:* Before `_fallback_plan`, add a tolerant pre-extraction (regex the first fenced ` ```json...``` ` block or first balanced `{...}` object) mirroring the fence-strip already in `backend/app/ai/briefing_compiler.py:60`, then split the single `except` into two observable paths (`parse_failed` vs `llm_call_failed`) with structured logs/metrics.

**✅ RESOLVED (2026-06-14) — bounded plan steps (D2).** `_MAX_PLAN_STEPS = 5` is now enforced in code: `_convert_planner_output` and `_merge_replanned_steps` truncate (preserving locked completed steps on replan) with a WARNING; the router bounds `plan_max = min(len(plan.steps)+1, _MAX_PLAN_STEPS+1)`. An LLM ignoring the prompt can no longer inflate the budget. Tests: `backend/tests/ai/test_planner_step_cap.py`. *(Original issue kept below for history.)*

**[LOW · correctness] 5-step plan cap is advisory only — no programmatic truncation.**
The "Maximum 5 steps" rule appears only in the prompt templates (`backend/app/ai/planner.py:55, 85`). Neither `_convert_planner_output` (`backend/app/ai/planner.py:149-195`) nor `_merge_replanned_steps` (`backend/app/ai/planner.py:198-240`) applies any truncation. The dynamic iteration cap in the router scales to `len(plan.steps)+1` (`backend/app/ai/supervisor_orchestrator.py:531`), so an 8-step plan raises the budget to 9, compounding context growth and cost.
*Recommendation:* Add a defensive `_MAX_PLAN_STEPS` truncation in code in `_convert_planner_output` and `_merge_replanned_steps` (with a warning log), bound the router expansion with `min(len(plan.steps)+1, HARD_MAX)`, and optionally enforce at the schema level with `Field(max_length=5)` on `PlannerOutput.steps`.

**✅ RESOLVED (2026-06-14) — tool-call-aware context trim.** The trim boundary is now tool-call-aware via `_tool_aware_tail_start()` (backs the split up to the issuing assistant so a call/response group is never split), and `_repair_chain` now logs a WARNING on any residual drop. Live-validated via a fault-injection e2e (actual trim fired, zero chain errors). Tests: `backend/tests/ai/test_context_guard.py`. *(Original issue kept below for history.)*

**[LOW · correctness] ContextGuard trim boundary can silently drop in-progress tool-call pairs.**
`ContextGuardMiddleware` trims all messages between the first and the last `AI_CONTEXT_KEEP_RECENT`, then `_repair_chain` (`backend/app/ai/middleware/context_guard.py:43-129`) tries to reconstruct a valid pairing — but if a tool_call/tool_message pair straddles the boundary, BOTH halves are dropped. The supervisor's next decision may be made without a result it already obtained.
*Recommendation:* Make the trim boundary tool-call-aware: after computing `tail`, extend the slice forward past any message that is part of an in-progress pair. As a secondary guard, log at WARNING whenever `_repair_chain` drops a non-empty assistant `tool_call` or an orphaned tool message. Realistic impact is modest because specialist findings persist in `briefing_data` (re-injected by the summary), so prioritize the observability fix if effort is constrained.

### Maintainability

**[LOW · maintainability] `handoff_tools.py` docstring falsely claims history is preserved.**
The module docstring states "Handoff preserves full message history — the receiving agent sees everything discussed so far" (`backend/app/ai/handoff_tools.py:4-5`), and `create_handoff_tool`'s docstring repeats "preserving the full shared state including message history" (`backend/app/ai/handoff_tools.py:48`). This is false — the handoff tool only carries its two synthesized messages to the parent graph; the actual entry `_create_specialist_wrapper` builds `isolated_messages = [HumanMessage(assignment_block)]` and invokes the graph with ONLY that list (`backend/app/ai/supervisor_orchestrator.py:814-815, 855-872`). A maintainer could wrongly assume specialists share context.
*Recommendation:* Rewrite both docstrings to state that the handoff routes control to the specialist node in the parent graph, that the specialist does NOT inherit parent message history (it runs in an isolated subgraph with a single synthesized assignment message), and that shared context flows through the `BriefingDocument`. Add a cross-reference to `_create_specialist_wrapper`.

### Speed / context-rot

**[LOW · maintainability] Delegation-enforcement rules are duplicated across three prompt locations that can drift.**
The "you must delegate, never use domain tools directly" policy is stated in `_DELEGATION_ENFORCED_SECTION` (`backend/app/ai/supervisor_orchestrator.py:159-169`), the per-call `_PLAN_DELEGATION_SUFFIX` (`backend/app/ai/middleware/plan_aware_tools.py:43-57`), and the softer `_PLAN_WITH_DIRECT_TOOLS_SUFFIX` (`backend/app/ai/middleware/plan_aware_tools.py:59-72`). The forbidden-tool example lists ("get_project, global_search, find_users, etc.") are hardcoded duplicates; adding a new privileged tool requires editing both files. The duplicated coaxing adds ~400 tokens to every supervisor call under a plan.
*Recommendation:* Extract the forbidden-tool example list into a single shared constant referenced by both sections (do NOT merge the three sections wholesale — the two plan suffixes carry distinct workflow content). Optionally trim `_PLAN_DELEGATION_SUFFIX` to a one-line reminder since `_filter_tools_for_plan`/`_strip_disallowed_tool_calls` already enforce delegation in code, recovering ~150 tokens per call.

---

## 6. How to Extend / Debug

- **Change a specialist prompt:** edit the `system_prompt` column on its `ai_assistant_configs` row (`backend/app/models/domain/ai.py:142`). Loaded via `load_specialists_from_db()` with a 5-min TTL cache — call `invalidate_cache()` (`backend/app/ai/subagents/db_loader.py:66`) after CRUD, or restart the server.
- **Change the planner prompt template:** set `AIAssistantConfig.planner_prompt` (supports `{specialist_section}`, `backend/app/models/domain/ai.py:143`). Falls back to `_PLANNER_PROMPT_TEMPLATE` (`backend/app/ai/planner.py:30`) when null. All prompt assembly now goes through `render_prompt()` (`backend/app/ai/prompt_template.py`) — a single-pass, never-raises allowlisted `{tag}` substitution (NOT `str.format`/`str.replace`); unknown tags and stray `{`/`}` are left verbatim, and injected values are never re-scanned, so **no brace-doubling is needed** in templates (the old `.format()` brace-doubling caveat is obsolete).
- **Change the supervisor prompt template:** set `AIAssistantConfig.supervisor_prompt` (supports `{specialist_section}` and `{plan_section}`, `backend/app/models/domain/ai.py:148`). Never resolve `{plan_section}` at build time — the middleware fills it per call.
- **Tune iteration caps:** `AIAssistantConfig.max_supervisor_iterations` (`backend/app/models/domain/ai.py:158`) sets the base; when a plan is active the router raises it to `len(plan.steps)+1`, **bounded by `min(len(plan.steps)+1, _MAX_PLAN_STEPS+1)`** (`_MAX_PLAN_STEPS=5` in `backend/app/ai/planner.py`). The replan cap is fixed at 2 (`max_replan_count`, enforced in the router).
- **Tune context trimming:** set in `backend/.env` (now wired through the `Settings` singleton — previously dead config). `AI_CONTEXT_TOKEN_LIMIT` (code default 120000), `AI_CONTEXT_SUMMARY_THRESHOLD_PCT` (80), `AI_CONTEXT_KEEP_RECENT` (code default 8); module constants in `backend/app/ai/config.py` re-export from `settings.X`. Note: the trim rarely fires in practice — the supervisor's context stays small (~hundreds of tokens) by design (specialist isolation + compact briefing).
- **Toggle delegation enforcement:** `AI_DELEGATION_ENFORCED` (`backend/.env`, now a `Settings` field; code default `true`). Gates BOTH the build-time `_DELEGATION_ENFORCED_SECTION` append AND `PlanAwareToolMiddleware`'s active tool filtering. **This environment currently runs `AI_DELEGATION_ENFORCED=false`** (intentional) — the supervisor is NOT forced to delegate and may use domain tools directly under multi-step plans.
- **Read a stored briefing/plan from the DB:** query `ai_conversation_sessions.briefing_data` / `plan_data` (`backend/app/models/domain/ai.py:237, 242`) — they are serialized `BriefingDocument` / `PlanDocument`. Reconstruct with `BriefingDocument.from_state(...)` / `PlanDocument.from_state(...)` (`backend/app/ai/briefing.py:48`, `backend/app/ai/plan.py:83`) and render with `.to_markdown()` / `.to_prompt_text()`.
- **Debug "why doesn't the specialist remember X from two turns ago":** it never receives those turns — only the compiled briefing. Check `briefing_data.sections`, not `ai_conversation_messages`.
- **Debug "specialist missing from the graph":** usually an empty-tool-list filter result, not a DB load failure. Check the `[subagent] '%s' has no tools after filtering — skipping` warning (`backend/app/ai/subagent_compiler.py:168`) and the `allowed_tools` JSONB on the specialist's config row.
- **Debug premature graph termination with pending steps:** inspect `[PLAN_AWARE_TOOLS] All tool calls stripped` logs (`backend/app/ai/middleware/plan_aware_tools.py:155`) — the synthetic `get_briefing` injection is the last line of defense.
- **Debug "tool message without preceding tool_calls" errors in supervisor logs:** suspect `ContextGuardMiddleware`'s trim boundary landed inside a tool-call/tool-response pair (`backend/app/ai/middleware/context_guard.py:43`).

---

*Last updated: 2026-06-14* (line anchors refreshed against current source; planner `invoke_with_retry`/`parse_failed`/`llm_call_failed` split and `_ALLOWED_PREFIXES` including `ask_user` now reflected).
