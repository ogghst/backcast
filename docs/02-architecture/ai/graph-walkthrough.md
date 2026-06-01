# How the Backcast AI Graph Works — A Complete Walkthrough

## Context

This document explains the full AI delegation graph using concrete examples.
It traces every prompt, every rule, and every decision point from user message to final response.

### Example 1: Multi-Specialist EVM Analysis

**Configuration:** Senior Project Manager persona, Expert Mode, project "DIY RC Car"
**Example prompt:** _"Analyze the EVM performance for the project and create a visualization of the results"_

This prompt triggers **two specialists**: `evm_analyst` then `visualization_specialist`.

### Example 2: External Web Search via MCP Specialist

**Example prompt:** _"Search the web for recent EU construction cost regulations and summarize how they might affect our active projects"_

This prompt triggers **two specialists**: `mcp_specialist` (web search) then `project_manager` (list active projects and correlate).

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
| `system_prompt` | Custom supervisor instructions (or uses the built-in default) |
| `delegation_config.direct_tools` | 24 read-only tools the supervisor can use directly |
| `delegation_config.allowed_specialists` | 6 specialists it can hand off to |

The supervisor does NOT do domain work itself. It reads the briefing and delegates.

**Configurable prompt:** The supervisor's system prompt comes from `AIAssistantConfig.system_prompt` when set via the AI Assistant management page. If no custom prompt is configured, the built-in `_BASE_SUPERVISOR_PROMPT` is used. Regardless of whether the prompt is custom or default, the system **always appends**:
1. The delegation enforcement section (when `AI_DELEGATION_ENFORCED=true`)
2. A dynamic "## Available Specialists" section built from the compiled specialist catalog
3. A direct-tools or handoff suffix

### Specialists (Subagents)

Each specialist is compiled from the database (via `db_loader.py`) or from hardcoded fallbacks (`subagents/__init__.py`) with:
- A domain-specific **system prompt**
- A curated **allowed_tools** list
- A **structured output schema** (defaults to `SpecialistOutput` from `schemas.py`)

The specialist list in both the planner and supervisor prompts is **dynamic** — it reflects the actual specialists loaded from the database, not a hardcoded list.

---

## 2. Graph Architecture

```
START
  │
  ▼
initialize_briefing_node ─── Creates BriefingDocument, injects as SystemMessage
  │
  ▼
planner_node ─── Analyzes request via LLM, creates PlanDocument
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

## 3. Step-by-Step Walkthrough (Example 1: EVM + Visualization)

### Step 0: User Sends Message

User types in the chat input and hits Enter. The frontend opens a WebSocket to `/api/v1/ai/chat/stream`.

`agent_service.py` receives the message and starts the graph execution.

### Step 1: `initialize_briefing_node`

**File:** `supervisor_orchestrator.py`

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

The planner **always** uses an LLM call to analyze the request. The system prompt is built dynamically via `build_planner_system_prompt(specialist_catalog)`, which includes a "## Available Specialists" section generated from the compiled specialist catalog.

```
You are a request planner for the Backcast project budget management system.
Analyze the user's request and decide whether it needs multi-step execution
or can be handled by a single specialist.

## Available Specialists
- project_manager: Project CRUD, WBS elements, cost elements, ...
- evm_analyst: Earned Value Management calculations, performance indices, ...
- visualization_specialist: Charts, diagrams, visual representations
- ... (dynamically listed from compiled specialists)

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

The supervisor prompt is assembled dynamically in `create_supervisor_graph()`:

1. **Base prompt** — custom from `AIAssistantConfig.system_prompt` or the built-in default
2. **Delegation enforcement section** — appended when `AI_DELEGATION_ENFORCED=true`
3. **Dynamic specialist section** — built from the compiled specialist catalog
4. **Direct-tools or handoff suffix** — based on the delegation config

Since `AI_DELEGATION_ENFORCED=true`, the supervisor gets the **full prompt**:

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
- project_manager -> Specialist for project, WBE, cost element management
- evm_analyst -> Specialist for earned value management calculations
- visualization_specialist -> Specialist for generating visualizations
- ... (dynamically listed)

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

**File:** `supervisor_orchestrator.py` → `_create_specialist_wrapper()`

The wrapper resolves the plan step and builds the specialist's assignment:

#### Rule: Plan Step Assignment

A HumanMessage is constructed:

```
## Your Assignment (Plan Step 1/2)

Calculate EVM metrics (CPI, SPI, CV, SV, EAC, VAC, etc.) for the specified project

**Expected output:** Structured EVM analysis report

Use the get_briefing tool to review prior specialist findings if needed for context.

## Briefing

[Briefing document markdown — full briefing is always passed]
```

#### Rule: Full Briefing (no scoping)

The full briefing is always passed to every specialist. The specialist can use the `get_briefing` tool to review prior findings as needed. This ensures specialists have complete context without artificial filtering.

#### EVM Analyst's System Prompt

The specialist's system prompt comes from the specialist config (DB or hardcoded). No scope suffix or output format instructions are appended — structured output is handled by the `SpecialistOutput` schema:

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

Use get_project_analysis for EVM metrics, KPIs, health assessments, and anomaly detection.
Provide clear explanations of what the metrics mean and actionable insights.
Identify trends and potential risks early.
```

#### Structured Output: SpecialistOutput

By default, all specialists produce structured JSON output via the `SpecialistOutput` Pydantic model:

```python
class SpecialistOutput(BaseModel):
    summary: str           # Brief summary of what was accomplished
    key_findings: list[str]  # Most important discoveries
    open_questions: list[str]  # Questions needing answers
    delegation_notes: str    # Context for follow-up (IDs, partial results)
```

Specialists with domain-specific schemas (e.g., `EVMMetricsRead`, `ImpactAnalysisResponse`, `ForecastRead`) use their own schemas instead. The `briefing_compiler.parse_and_clean()` function handles both JSON and plain text formats — it tries JSON parsing first and falls back to regex-based section extraction.

#### EVM Analyst's Tools (4 tools)

```
get_temporal_context, global_search, get_project_analysis, get_project_forecast
```

#### EVM Analyst Executes

The specialist calls `get_project_analysis` which returns all EVM metrics. It produces a structured `SpecialistOutput` (or `EVMMetricsRead`) with its findings.

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

## Guidelines
- Use data from tools (global_search, get_temporal_context) to build accurate diagrams
- Keep diagrams focused and readable — max 15 nodes
- Always include a brief text explanation before each diagram
```

#### Visualization Specialist's Tools (2 tools)

```
get_temporal_context, global_search
```

The specialist produces Mermaid diagrams and text explanations as a structured `SpecialistOutput` (diagrams go in the `summary` field). Another PLAN_UPDATE is emitted (`steps[1].status = "completed"`).

### Step 7: `supervisor_node` (Final Turn)

The supervisor checks:
- Plan has 2 steps, both completed (`completed_steps = {0, 1}`)
- No more steps to delegate
- Routes to END

The final briefing contains sections from both specialists. The frontend renders the complete response to the user.

---

## 3b. Step-by-Step Walkthrough (Example 2: Tavily Web Search via MCP)

This example traces a request that uses the `mcp_specialist` to perform an external web search via Tavily, then correlates results with project data.

**Example prompt:** _"Search the web for recent EU construction cost regulations and summarize how they might affect our active projects"_

### Step 1: `initialize_briefing_node`

Creates a `BriefingDocument` with the request. No findings yet.

### Step 2: `planner_node`

The planner LLM produces a 2-step plan:

```json
{
  "requires_planning": true,
  "estimated_complexity": "moderate",
  "steps": [
    {
      "step_index": 0,
      "specialist": "mcp_specialist",
      "task_description": "Search the web for recent EU construction cost regulations using Tavily search",
      "dependencies": [],
      "expected_output": "Summary of recent EU regulations affecting construction costs"
    },
    {
      "step_index": 1,
      "specialist": "project_manager",
      "task_description": "List active projects and assess which ones might be affected by the EU regulations found",
      "dependencies": [0],
      "expected_output": "Project impact assessment"
    }
  ]
}
```

### Step 3: `supervisor_node` (First Turn)

Delegates step 0 to `mcp_specialist`:

```
handoff_to_mcp_specialist(
    task_description="Search the web for recent EU construction cost regulations...",
    step_index=0
)
```

### Step 4: `specialist_wrapper_node` (MCP Specialist)

The MCP specialist is unique: it has **no regular tools** (`allowed_tools=None`). Instead, it receives MCP tools dynamically injected by category prefix (`AI_MCP_TOOL_CATEGORY_PREFIX="mcp:"`).

#### MCP Tool Injection

When the graph is compiled, any tools whose name starts with `mcp:` are added to the MCP specialist's tool pool. For example, if a Tavily MCP server is configured, the specialist receives tools like:

```
mcp:tavily_search    — Search the web for information
mcp:tavily_extract   — Extract content from URLs
```

These MCP tools are:
- Discovered dynamically from configured MCP servers (`mcp/client_manager.py`)
- Wrapped with Backcast RBAC (`mcp/tool_metadata.py`)
- Injected into the MCP specialist's tool pool by category prefix

#### MCP Specialist Executes

The specialist calls `mcp:tavily_search` with an appropriate query:

```python
mcp:tavily_search(query="EU construction cost regulations 2026 changes")
```

The tool returns search results. The specialist summarizes the findings and produces a `SpecialistOutput`:

```json
{
  "summary": "Found 3 relevant EU regulation updates affecting construction costs...",
  "key_findings": [
    "EU Regulation 2026/XXX increases mandatory safety budget allocation by 5%",
    "New carbon accounting requirements effective Q3 2026",
    "Updated labor cost benchmarks for EU member states"
  ],
  "open_questions": ["Exact implementation timeline for carbon accounting"],
  "delegation_notes": "Regulation details stored for project correlation"
}
```

PLAN_UPDATE emitted: step 0 → completed.

### Step 5: `supervisor_node` (Second Turn)

Reads the updated briefing (now contains MCP specialist findings about EU regulations). Delegates step 1 to `project_manager`:

```
handoff_to_project_manager(
    task_description="List active projects and assess which might be affected by EU regulations...",
    step_index=1
)
```

### Step 6: `specialist_wrapper_node` (Project Manager)

The project manager specialist:
1. Calls `list_projects` to get all active projects
2. Correlates project locations and budgets with the EU regulation findings
3. Produces a structured impact assessment

PLAN_UPDATE emitted: step 1 → completed.

### Step 7: `supervisor_node` (Final Turn)

Both steps complete. Routes to END. The final briefing contains the web search findings and the project impact assessment.

---

## 4. Context Manipulation Points

The system has exactly **2** context modification points:

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

### 4.3 Structured Output (every specialist invocation)

**Where:** `schemas.py` → `SpecialistOutput`, `subagent_compiler.py`
**What:** All specialists default to producing structured JSON via the `SpecialistOutput` Pydantic model. The output includes `summary`, `key_findings`, `open_questions`, and `delegation_notes`. Domain-specific specialists can override with their own schema (e.g., `EVMMetricsRead`).
**Why:** Ensures consistent, parseable output from all specialists. The briefing compiler (`parse_and_clean()`) handles both JSON and plain text formats.

---

## 5. Rules Summary

### Planner Rules
| Rule | Source | Effect |
|---|---|---|
| Dynamic specialist list | `planner.py` `build_planner_system_prompt()` | Specialist catalog built from compiled graphs, not hardcoded |
| Max 5 plan steps | Planner system prompt | Hard limit in prompt instructions |
| LLM always called | `planner.py` `planner_node()` | Every request goes through LLM planning (no fast-path shortcut) |

### Supervisor Rules
| Rule | Source | Effect |
|---|---|---|
| Delegation enforced | `config.py` `AI_DELEGATION_ENFORCED` | Strip all domain tools when plan exists |
| Max 3 iterations (default) | `supervisor_state.py` | Prevent infinite loops; auto-extends for multi-step plans |
| Don't repeat specialists | Supervisor prompt | Won't hand off to same specialist twice |
| Don't summarize briefing | Supervisor prompt | Briefing shown to user directly |
| Check briefing before delegating | Supervisor prompt | Read first, delegate second |
| Configurable prompt | `AIAssistantConfig.system_prompt` | Custom supervisor prompt via AI Assistant page |
| Dynamic specialist section | `_build_supervisor_specialist_section()` | Always appended to any prompt (custom or default) |

### Specialist Rules
| Rule | Source | Effect |
|---|---|---|
| Structured output | `schemas.py` `SpecialistOutput` | All specialists produce structured JSON by default |
| Tool filtering | `subagent_compiler.py` | Only get their allowed_tools |
| RBAC filtering | `backcast_security.py` | Tools filtered by user role |
| Sequential tool calls | `sequential_tool_calls.py` | One tool at a time (configurable via `AI_SEQUENTIAL_TOOL_CALLS`) |

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
- `allowed_tools = None` → **no tools** (mcp_specialist — receives MCP tools dynamically)
- `allowed_tools = ["*"]` → **all tools** (general_purpose)
- `allowed_tools = ["t1", "t2", ...]` → **only those tools**

---

## 7. Environment Controls

| Env Var | Default | What It Controls |
|---|---|---|
| `AI_CONTEXT_TOKEN_LIMIT` | 50000 | Max tokens before context guard trims |
| `AI_CONTEXT_SUMMARY_THRESHOLD_PCT` | 80 | % threshold to trigger trimming |
| `AI_CONTEXT_KEEP_RECENT` | 4 | Messages to keep unsummarized |
| `AI_DELEGATION_ENFORCED` | true | Strip supervisor tools when plan exists |
| `AI_SEQUENTIAL_TOOL_CALLS` | true | Enforce one tool call at a time (set false for parallel) |
| `AI_MCP_TOOL_CATEGORY_PREFIX` | "mcp:" | Category prefix for MCP tool identification |
| `AI_TOOLS_{SPECIALIST}` | (hardcoded) | Override specialist tool lists per deployment |

---

## 8. Key Files Reference

| File | Purpose |
|---|---|
| `backend/app/ai/supervisor_orchestrator.py` | Graph construction, supervisor node, routing, specialist wrappers |
| `backend/app/ai/planner.py` | Request planning, dynamic specialist catalog, PlanDocument creation |
| `backend/app/ai/handoff_tools.py` | Handoff tool creation, specialist routing |
| `backend/app/ai/subagents/__init__.py` | Hardcoded specialist configs (prompts, tool lists) |
| `backend/app/ai/subagents/db_loader.py` | Load specialist configs from DB with TTL caching |
| `backend/app/ai/subagent_compiler.py` | Specialist compilation, tool filtering, middleware setup |
| `backend/app/ai/schemas.py` | `SpecialistOutput` structured output model |
| `backend/app/ai/config.py` | All AI_* env constants |
| `backend/app/ai/briefing.py` | BriefingDocument model, to_markdown |
| `backend/app/ai/briefing_compiler.py` | parse_and_clean (JSON + regex), compile_specialist_output |
| `backend/app/ai/plan.py` | PlanDocument, PlanStep models, VALID_SPECIALISTS |
| `backend/app/ai/middleware/context_guard.py` | Context trimming with chain repair |
| `backend/app/ai/middleware/backcast_security.py` | RBAC + risk-based tool filtering |
| `backend/app/ai/agent_service.py` | Graph execution entry point, event emission |
