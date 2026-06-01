# How the Backcast AI Graph Works — A Complete Walkthrough

## Context

This document explains the full AI delegation graph using a concrete example.
It traces every prompt, every rule, and every decision point from user message to final response.

**Configuration:** Senior Project Manager persona, Expert Mode, project "DIY RC Car"
**Example prompt:** _"Analyze the EVM performance for the project and create a visualization of the results"_

This prompt triggers **two specialists**: `evm_analyst` then `visualization_specialist`.

---

## 1. The Actors

### Main Agent (Supervisor)

The "Senior Project Manager" is a **main agent** loaded from `ai_assistant_configs` in the DB. Its row defines:

| Field | Value |
|---|---|
| `name` | "Senior Project Manager" |
| `model_id` | UUID → deepseek-v4-flash |
| `temperature` | 0.30 |
| `max_tokens` | 160,401 |
| `recursion_limit` | 81 |
| `default_role` | "ai-manager" |
| `delegation_config.direct_tools` | 24 read-only tools the supervisor can use directly |
| `delegation_config.allowed_specialists` | 6 specialists it can hand off to |

The supervisor does NOT do domain work itself. It reads the briefing and delegates.

### Specialists (Subagents)

Each specialist is compiled from `backend/app/ai/subagents/__init__.py` with:
- A domain-specific **system prompt**
- A curated **allowed_tools** list
- An auto-appended **scope suffix**

---

## 2. Graph Architecture

```
START
  │
  ▼
initialize_briefing_node ─── Creates BriefingDocument, injects as SystemMessage
  │
  ▼
planner_node ─── Analyzes request, creates PlanDocument (or fast-path)
  │
  ▼
supervisor_node ─── Reads briefing + plan, calls handoff_to_X tool
  │
  ▼
specialist_wrapper_node ─── Resolves plan step, builds assignment, invokes specialist
  │                        Emits PLAN_UPDATE (status=in_progress)
  │                        Emits PLAN_UPDATE (status=completed)
  │
  ▼
[back to supervisor_node] ─── Checks next step, delegates again
  │
  ▼
END ─── When all steps complete or max iterations reached
```

**State:** Shared via `BackcastSupervisorState` (defined in `supervisor_state.py`):

```python
{
    "messages": list[BaseMessage],
    "active_agent": str,
    "briefing_data": dict,          # Serialized BriefingDocument
    "plan_data": dict,              # Serialized PlanDocument
    "completed_specialists": set,    # Names of finished specialists
    "completed_steps": set,         # Step indices that are done
    "current_step_index": int,
    "supervisor_iterations": int,
    "max_supervisor_iterations": 3,  # Extended to len(plan.steps)+2 when plan exists
}
```

---

## 3. Step-by-Step Walkthrough

### Step 0: User Sends Message

User types in the chat input and hits Enter. The frontend opens a WebSocket to `/api/v1/ai/chat/stream`.

`agent_service.py` receives the message and starts the graph execution.

### Step 1: `initialize_briefing_node`

**File:** `handoff_tools.py`

Extracts the user's text from the last HumanMessage, creates a `BriefingDocument`:

```python
doc = BriefingDocument(
    original_request="Analyze the EVM performance for the project and create a visualization of the results",
    sections=[],           # empty — no findings yet
    task_history=[],       # no tasks assigned yet
    plan=None,
)
```

Injects the briefing as a `SystemMessage` into the conversation:

```
SystemMessage("## Current Briefing\n\nNo findings yet.")
```

### Step 2: `planner_node`

**File:** `planner.py`

#### Rule: Fast-Path Check (no LLM call)

Before invoking the LLM, the planner checks if the request matches a simple keyword heuristic:

```python
_FAST_KEYWORD_MAP = {
    "budget": "project_manager", "cost": "project_manager",
    "project": "project_manager", "wbs": "project_manager",
    "evm": "evm_analyst", "cpi": "evm_analyst", "spi": "evm_analyst",
    "performance": "evm_analyst", "earned value": "evm_analyst",
    "diagram": "visualization_specialist", "chart": "visualization_specialist",
    "visualization": "visualization_specialist",
    # ... etc
}
```

**Our example matches TWO specialists** (evm_analyst + visualization_specialist), so fast-path is **skipped** — the request is too ambiguous for single-domain routing.

#### Rule: LLM Planner Call

The planner calls DeepSeek with this system prompt:

```
You are a request planner for the Backcast project budget management system.
Analyze the user's request and decide whether it needs multi-step execution
or can be handled by a single specialist.

## Available Specialists
- project_manager: Project CRUD, WBS elements, cost elements, ...
- evm_analyst: Earned Value Management calculations, performance indices, ...
- visualization_specialist: Charts, diagrams, visual representations
- ... (all 8 listed)

## Your Task
Return a JSON object with this structure:
{
  "original_request": "<the user's request>",
  "requires_planning": true/false,
  "estimated_complexity": "simple" | "moderate" | "complex",
  "steps": [
    {
      "step_index": 0,
      "specialist": "<name>",
      "task_description": "<focused description>",
      "dependencies": [],
      "expected_output": "<what this step should produce>"
    }
  ]
}

## Rules
- Use ONLY specialist names from the list
- Keep task descriptions focused and actionable
- Only add dependencies when step N genuinely needs output from step M
- Maximum 5 steps
- Return ONLY valid JSON, no markdown fences
```

The LLM returns:

```json
{
  "original_request": "Analyze the EVM performance for the project and create a visualization...",
  "requires_planning": true,
  "estimated_complexity": "moderate",
  "steps": [
    {
      "step_index": 0,
      "specialist": "evm_analyst",
      "task_description": "Calculate EVM metrics (CPI, SPI, CV, SV, EAC, VAC, etc.) for the specified project...",
      "dependencies": [],
      "expected_output": "Structured EVM analysis report"
    },
    {
      "step_index": 1,
      "specialist": "visualization_specialist",
      "task_description": "Based on the EVM analysis output, create visual representations...",
      "dependencies": [0],
      "expected_output": "Charts and dashboard-style overview"
    }
  ]
}
```

A `PLAN_UPDATE` event is emitted to the frontend. The plan appears in the briefing rail: **"Plan 0/2 moderate"**.

### Step 3: `supervisor_node` (First Turn)

**File:** `supervisor_orchestrator.py`

#### The Supervisor's System Prompt

Since `AI_DELEGATION_ENFORCED=true` (env var), the supervisor gets the **full prompt** with delegation enforcement:

```
You are a supervisor for the Backcast project budget management system.

You coordinate specialist agents who report back through a compiled briefing document.
The user reads the briefing directly — do NOT summarize or repeat findings.

## How It Works
1. Read the briefing to see what has been analyzed
2. If not addressed, hand off to the most relevant specialist
3. After a specialist contributes, the briefing is updated automatically

## Execution Plan
- If a plan exists with multiple steps, delegate ONE step at a time in order
- Each step already specifies the specialist and focused task description
- For simple single-step plans, delegate normally

## Available Specialists
- project_manager -> Project CRUD, WBEs, cost elements, cost tracking, progress entries
- evm_analyst -> EVM calculations, performance analysis
- change_order_manager -> Change orders, impact analysis
- user_admin -> User and department management
- visualization_specialist -> Diagrams, visualizations
- forecast_manager -> Forecasts, schedule baselines
- mcp_specialist -> External tools via MCP servers
- general_purpose -> Unclear or cross-cutting requests

## Rules
- Do NOT write a response summarizing the briefing
- Only respond if you need to ask the user a clarification question
- Do NOT hand off to the same specialist more than once for the same task
- Always check the briefing before deciding to hand off

## CRITICAL: Plan-Driven Delegation
When a multi-step execution plan is active:
- You MUST delegate every step to the specialist specified in the plan
- You MUST NOT attempt to execute domain operations yourself
- Your ONLY tools are get_briefing and handoff_to_* -- use them to delegate
- NEVER use domain tools like get_project, global_search, find_users, etc.
- If you are unsure what to do, call get_briefing first, then delegate the next step
```

#### Rule: Tool Filtering (PlanAwareToolMiddleware)

When `AI_DELEGATION_ENFORCED=true` AND `plan_data` has >0 steps, the supervisor's tool list is **stripped** to only:
- `get_briefing`
- `handoff_to_evm_analyst`
- `handoff_to_visualization_specialist`

All 24 direct_tools (get_project, global_search, find_users, etc.) are removed.

#### What Happens

The supervisor reads the plan, sees step 0 needs `evm_analyst`, and calls:

```
handoff_to_evm_analyst(
    task_description="Calculate EVM metrics (CPI, SPI, CV, SV, EAC, VAC, etc.) for the specified project...",
    rationale="First step of the execution plan",
    analysis="User requested EVM analysis followed by visualization",
    step_index=0
)
```

This tool returns a `Command(goto="evm_analyst", graph=Command.PARENT)` which routes to the specialist wrapper.

### Step 4: `specialist_wrapper_node` (EVM Analyst)

**File:** `handoff_tools.py`

The wrapper resolves the plan step and builds the specialist's assignment:

#### Rule: Plan Step Assignment

A HumanMessage is constructed:

```
## Assignment
Task: Calculate EVM metrics (CPI, SPI, CV, SV, EAC, VAC, etc.) for the specified project
Delegated by: supervisor
Step 1 of 2

## Briefing Context
[Briefing document markdown — only sections relevant to this step]
```

#### Rule: Briefing Scoping

`to_scoped_markdown()` filters the briefing to only include sections relevant to the current step's dependencies. Since step 0 has no dependencies, the briefing is minimal.

#### EVM Analyst's System Prompt

```
You are an EVM analysis specialist.

You calculate and analyze earned value metrics including:
- CPI (Cost Performance Index) - cost efficiency
- SPI (Schedule Performance Index) - schedule efficiency
- CV (Cost Variance) - budget variance
- SV (Schedule Variance) - schedule variance
- EAC (Estimate at Completion) - projected final cost
- ETC (Estimate to Complete) - remaining work cost
- VAC (Variance at Completion) - final budget variance
- TCPI (To-Complete Performance Index) - required efficiency

You also provide:
- Performance trend analysis
- Project health assessments
- Anomaly detection in EVM metrics
- Optimization recommendations

Use get_project_analysis for EVM metrics, KPIs, health assessments, and anomaly detection.
Provide clear explanations of what the metrics mean and actionable insights.
Identify trends and potential risks early.

## SCOPE
Focus only on your specialist domain. Execute ONLY the task described in
your assignment — do not attempt other parts of the user's request or
plan, those will be handled by other specialists.

## OUTPUT FORMAT
After tool calls, write your findings with these sections:
- ## Key Findings: Most important discoveries
- ## Open Questions: Questions needing answers
- ## Delegation Notes: Context for follow-up work (IDs, partial results)
```

#### EVM Analyst's Tools (4 tools)

```
get_temporal_context, global_search, get_project_analysis, get_project_forecast
```

#### EVM Analyst Executes

The specialist calls `get_project_analysis` which returns all EVM metrics. It produces a structured output with Key Findings, Open Questions, and Delegation Notes.

#### PLAN_UPDATE Events

- **Before invocation:** `plan_data.steps[0].status = "in_progress"` → PLAN_UPDATE emitted
- **After completion:** `plan_data.steps[0].status = "completed"` → PLAN_UPDATE emitted
  - `completed_steps = {0}`
  - `result_summary` set to brief summary

The briefing is updated with a new `BriefingSection` containing the EVM analyst's findings.

Control returns to the supervisor via `Command(goto="supervisor")`.

### Step 5: `supervisor_node` (Second Turn)

The supervisor reads the updated briefing (now contains EVM analyst findings). It sees step 1 needs `visualization_specialist` and calls:

```
handoff_to_visualization_specialist(
    task_description="Based on the EVM analysis output, create visual representations such as cost/schedule performance index charts...",
    rationale="Second step — depends on step 0 (completed)",
    analysis="EVM analysis complete, now need visualization",
    step_index=1
)
```

### Step 6: `specialist_wrapper_node` (Visualization Specialist)

#### Visualization Specialist's System Prompt

```
You are a visualization specialist.

You create diagrams to illustrate project structures, workflows, hierarchies, and relationships.

## How to Create Diagrams
Output Mermaid diagrams DIRECTLY in markdown code blocks. Do NOT call any diagram-generation tool.
The user's frontend renders ```mermaid code blocks automatically as SVG diagrams.

## Supported Diagram Types
- flowchart / graph: Process flows, decision trees, hierarchies
- sequencediagram: Interactions between actors over time

## Guidelines
- Use data from tools (global_search, get_temporal_context) to build accurate diagrams
- Keep diagrams focused and readable — max 15 nodes
- Always include a brief text explanation before each diagram

## SCOPE
Focus only on your specialist domain. Execute ONLY the task described in
your assignment.

## OUTPUT FORMAT
- ## Key Findings
- ## Open Questions
- ## Delegation Notes
```

#### Visualization Specialist's Tools (2 tools)

```
get_temporal_context, global_search
```

The specialist produces Mermaid diagrams and text explanations. Another PLAN_UPDATE is emitted (`steps[1].status = "completed"`).

### Step 7: `supervisor_node` (Final Turn)

The supervisor checks:
- Plan has 2 steps, both completed (`completed_steps = {0, 1}`)
- No more steps to delegate
- Routes to END

The final briefing contains sections from both specialists. The frontend renders the complete response to the user.

---

## 4. Context Manipulation Points

The system has exactly **3** context modification points:

### 4.1 Briefing Injection (every supervisor turn)

**Where:** `supervisor_orchestrator.py` → `_briefing_update()`
**What:** The briefing markdown is injected as a `SystemMessage` at the start of the supervisor's message list
**Why:** The supervisor needs to see all specialist findings without re-reading the full conversation

### 4.2 Context Guard (when tokens exceed threshold)

**Where:** `middleware/context_guard.py` → `ContextGuardMiddleware`
**What:** If estimated tokens > 80% of `AI_CONTEXT_TOKEN_LIMIT` (default 50K) AND there are ≥8 messages:
  - Keeps system prompt + last 4 messages
  - Replaces middle with a briefing document summary
  - Repairs broken tool_calls → tool response chains
**Why:** Prevents DeepSeek from silently truncating context and losing the plan
**Guard:** Won't trigger on early turns (< 8 messages) to avoid false positives from tool schemas

### 4.3 Specialist Scope Suffix (every specialist invocation)

**Where:** `subagent_compiler.py` → `_SPECIALIST_SCOPE_SUFFIX`
**What:** Appends boundary and output format instructions to every specialist's system prompt
```
## SCOPE
Focus only on your specialist domain. Execute ONLY the task described in
your assignment — do not attempt other parts of the user's request.

## OUTPUT FORMAT
After tool calls, write your findings with these sections:
- ## Key Findings
- ## Open Questions
- ## Delegation Notes
```
**Why:** Prevents specialists from trying to do work outside their domain

---

## 5. Rules Summary

### Planner Rules
| Rule | Source | Effect |
|---|---|---|
| Fast-path keywords | `planner.py` `_FAST_KEYWORD_MAP` | Skip LLM call for obvious single-domain requests |
| Multi-domain = no fast-path | `planner.py` `_try_fast_path()` | If ≥2 specialists matched, fall through to LLM |
| Max 5 plan steps | Planner system prompt | Hard limit in prompt instructions |
| `AI_PLANNER_FAST_PATH` env var | `config.py` | Can disable fast-path entirely |

### Supervisor Rules
| Rule | Source | Effect |
|---|---|---|
| Delegation enforced | `config.py` `AI_DELEGATION_ENFORCED` | Strip all domain tools when plan exists |
| Max 3 iterations (default) | `supervisor_state.py` | Prevent infinite loops; auto-extends for multi-step plans |
| Don't repeat specialists | Supervisor prompt | Won't hand off to same specialist twice |
| Don't summarize briefing | Supervisor prompt | Briefing shown to user directly |
| Check briefing before delegating | Supervisor prompt | Read first, delegate second |

### Specialist Rules
| Rule | Source | Effect |
|---|---|---|
| Scoped to assigned task | `_SPECIALIST_SCOPE_SUFFIX` | Don't attempt other parts of the request |
| Structured output format | `_SPECIALIST_SCOPE_SUFFIX` | Key Findings / Open Questions / Delegation Notes |
| Tool filtering | `subagent_compiler.py` | Only get their allowed_tools |
| RBAC filtering | `backcast_security.py` | Tools filtered by user role |
| Sequential tool calls | `sequential_tool_calls.py` | One tool at a time |

### Context Guard Rules
| Rule | Source | Effect |
|---|---|---|
| Min 8 messages to trim | `context_guard.py` `_MIN_MESSAGES_TO_TRIM` | Avoid false positives from tool schemas |
| Skip system prompt in estimate | `context_guard.py` `_estimate_tokens()` | System prompt doesn't grow across turns |
| Keep last 4 messages | `config.py` `AI_CONTEXT_KEEP_RECENT` | Preserve recent context |
| Chain repair after trim | `context_guard.py` `_repair_chain()` | Fix orphaned tool messages |

---

## 6. Tool Filtering Pipeline

When the graph is compiled, tools go through 4 layers:

```
88 total tools created
  ↓ execution mode filter (expert = all pass)
  ↓ RBAC role filter (ai-manager → ~74 pass)
  ↓ per-specialist allowed_tools
  ↓ supervisor plan-aware filter (when plan exists)
```

Per-specialist convention (defined in `subagent_compiler.py`):
- `allowed_tools = None` → **no tools** (mcp_specialist)
- `allowed_tools = ["*"]` → **all tools** (general_purpose)
- `allowed_tools = ["t1", "t2", ...]` → **only those tools**

---

## 7. Environment Controls

| Env Var | Default | What It Controls |
|---|---|---|
| `AI_CONTEXT_TOKEN_LIMIT` | 50000 | Max tokens before context guard trims |
| `AI_CONTEXT_SUMMARY_THRESHOLD_PCT` | 80 | % threshold to trigger trimming |
| `AI_CONTEXT_KEEP_RECENT` | 4 | Messages to keep unsummarized |
| `AI_PLANNER_FAST_PATH` | true | Enable/disable keyword-based planner shortcut |
| `AI_DELEGATION_ENFORCED` | true | Strip supervisor tools when plan exists |
| `AI_MCP_TOOL_CATEGORY_PREFIX` | "mcp:" | Category prefix for MCP tool identification |
| `AI_TOOLS_{SPECIALIST}` | (hardcoded) | Override specialist tool lists per deployment |

---

## 8. Key Files Reference

| File | Purpose |
|---|---|
| `backend/app/ai/supervisor_orchestrator.py` | Graph construction, supervisor node, routing |
| `backend/app/ai/planner.py` | Request planning, fast-path, PlanDocument creation |
| `backend/app/ai/handoff_tools.py` | Handoff tool creation, specialist wrapper, PLAN_UPDATE events |
| `backend/app/ai/subagents/__init__.py` | Specialist configs (prompts, tool lists) |
| `backend/app/ai/subagent_compiler.py` | Specialist compilation, tool filtering, scope suffix |
| `backend/app/ai/config.py` | All AI_* env constants |
| `backend/app/ai/briefing.py` | BriefingDocument model, to_markdown, to_scoped_markdown |
| `backend/app/ai/middleware/context_guard.py` | Context trimming with chain repair |
| `backend/app/ai/middleware/backcast_security.py` | RBAC + risk-based tool filtering |
| `backend/app/ai/agent_service.py` | Graph execution entry point, event emission |
