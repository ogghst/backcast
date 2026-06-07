# AI Agent System — Gap Analysis

**Date:** 2026-06-07
**Scope:** `backend/seed/seed_system_config.json`, `backend/app/ai/`
**Goal:** Align specialist agents with domain responsibilities, remove model duplication, consolidate prompts, add missing capabilities.

---

## 1. Executive Summary

| Dimension | Current State | Target State | Gap |
|---|---|---|---|
| Specialist model_id | All 7 specialists have `model_id` set | Remove — specialists inherit main agent model | **HIGH** — model_id is ignored by code, seed data is misleading |
| Time Traveller specialist | Does not exist | New specialist for temporal operations | **HIGH** — no dedicated agent for time-travel |
| `ask_user` availability | Only `project_manager` has it | All specialists must have it | **HIGH** — 5/7 specialists cannot ask clarification questions |
| System prompt verbosity | 80–300+ words per specialist | Concise, context-review-first prompts | **MEDIUM** — token waste on every invocation |
| Planner/Supervisor prompts | Duplicated across 3 main agents with minor wording diffs | Single consolidated template with role-specific additions | **MEDIUM** — 6 near-identical prompt strings to maintain |
| Tool assignment accuracy | Specialists carry tools outside their domain | Tight domain-aligned tool sets | **MEDIUM** — cross-domain tools increase error surface |
| `visualization_specialist` tools | Only 5 tools, no project structure access | Needs read tools to build diagrams | **LOW** — likely fails on complex visualizations |

---

## 2. Model Configuration

### Finding

All 7 specialists in `seed_system_config.json` set `"model_id": "11111111-1111-1111-1111-111111111112"`.

### Code Reality

`subagent_compiler.py` compiles **all specialists with the same LLM instance** created from the main agent's `model_id`. The specialist `model_id` column is **never read** — `db_loader.assistant_config_to_specialist_dict()` omits it entirely.

### Action

- **Remove `model_id`** from all specialist configs in seed data (set to `null`).
- **Remove `temperature`, `max_tokens`, `recursion_limit`** from specialist configs — these are also ignored (specialists use the main agent's LLM instance with its parameters).
- The DB schema already supports `NULL` for these fields on specialist records.

### Fields Affected per Specialist

| Field | Current | Target |
|---|---|---|
| `model_id` | `"11111111-1111-1111-1111-111111111112"` | `null` |
| `temperature` | `0.0` – `0.3` | `null` |
| `max_tokens` | `3000` – `4096` | `null` |
| `recursion_limit` | `10` – `25` | `null` |

---

## 3. Specialist-by-Specialist Analysis

### 3.1 Project Manager (`project_manager`)

**Purpose:** Read and modify project structure — WBS Elements, Control Accounts, Work Packages.

#### Current Tools (48)

```
ask_user, batch_create_cost_elements, batch_create_cost_registrations,
batch_create_progress_entries, batch_create_wbs_elements, batch_delete_cost_elements,
batch_update_wbs_elements, create_control_account, create_cost_element,
create_cost_element_type, create_cost_event, create_cost_registration,
create_forecast, create_progress_entry, create_project, create_wbs_element,
create_work_package, delete_control_account, delete_cost_element,
delete_cost_element_type, delete_cost_event, delete_cost_registration,
delete_forecast, delete_progress_entry, delete_project, delete_wbs_element,
delete_work_package, find_control_accounts, find_cost_element_types,
find_cost_elements, find_cost_events, find_wbs_elements, find_work_packages,
get_briefing, get_control_account_budget, get_coq_data, get_cost_element_details,
get_progress_data, get_project, get_project_context, get_project_forecast,
get_project_structure, get_temporal_context, get_work_package_budget_status,
global_search, list_cost_registrations, list_projects, read_document,
search_documents, set_temporal_context, update_control_account,
update_cost_element, update_cost_element_type, update_cost_event,
update_cost_registration, update_forecast, update_progress_entry,
update_project, update_wbs_element, update_work_package
```

#### Gap — Scope Overreach

The project manager currently owns cost registrations, cost events, forecasts, progress entries, and cost element types — these belong to the **accountant** or should be read-only. The specialist should focus strictly on project structure.

#### Recommended Tools

| Domain | Tools |
|---|---|
| Projects | `create_project`, `update_project`, `delete_project`, `list_projects`, `get_project`, `batch_create_projects` |
| WBS Elements | `create_wbs_element`, `update_wbs_element`, `delete_wbs_element`, `find_wbs_elements`, `batch_create_wbs_elements`, `batch_update_wbs_elements` |
| Control Accounts | `create_control_account`, `update_control_account`, `delete_control_account`, `find_control_accounts`, `get_control_account_budget`, `batch_create_control_accounts` |
| Work Packages | `create_work_package`, `update_work_package`, `delete_work_package`, `find_work_packages`, `get_work_package_budget_status`, `batch_create_work_packages`, `batch_get_work_package_budget_status` |
| Cost Elements | `create_cost_element`, `update_cost_element`, `delete_cost_element`, `find_cost_elements`, `batch_create_cost_elements`, `batch_delete_cost_elements` |
| Read-only context | `get_project_context`, `get_project_structure`, `get_temporal_context`, `get_cost_element_details` |
| Interaction | `ask_user`, `get_briefing`, `global_search` |

**Removed:** cost registrations, cost events, forecasts, progress entries, cost element types, `set_temporal_context`, `search_documents`, `read_document`, `get_project_forecast`, `get_coq_data`, `get_progress_data`, `list_cost_registrations`.

**Rationale:** Project manager creates the structure. Accountant registers costs. Time Traveller handles temporal context. Removes ~20 tools that were outside domain.

---

### 3.2 Accountant (`accountant`)

**Purpose:** Set up and manage cost registrations, cost events, and documentation.

#### Current Tools (32)

```
get_briefing, get_temporal_context, set_temporal_context, global_search,
get_project_context, get_project_structure, list_projects, get_project,
find_wbs_elements, find_cost_elements, find_cost_element_types,
find_cost_event_types, find_work_packages, find_control_accounts,
get_cost_element_details, get_work_package_budget_status,
get_control_account_budget, get_progress_data, create_cost_registration,
update_cost_registration, delete_cost_registration,
batch_create_cost_registrations, list_cost_registrations, find_cost_events,
create_cost_event, update_cost_event, delete_cost_event, get_coq_data,
search_documents, read_document
```

#### Gap

- ✅ Domain well-aligned
- ❌ Missing `ask_user`
- ❌ Has `set_temporal_context` — should delegate to time_traveller instead
- ❌ Missing `create_cost_event_type` — if managing cost events, should also manage types

#### Recommended Tools

| Domain | Tools |
|---|---|
| Cost Registrations | `create_cost_registration`, `update_cost_registration`, `delete_cost_registration`, `list_cost_registrations`, `batch_create_cost_registrations` |
| Cost Events | `find_cost_events`, `create_cost_event`, `update_cost_event`, `delete_cost_event`, `batch_create_cost_events`, `get_coq_data` |
| Cost Element Types | `find_cost_element_types`, `find_cost_event_types` |
| Read-only context | `get_project_context`, `get_project_structure`, `get_temporal_context`, `list_projects`, `get_project`, `find_wbs_elements`, `find_cost_elements`, `find_work_packages`, `find_control_accounts`, `get_cost_element_details`, `get_work_package_budget_status`, `get_control_account_budget`, `get_progress_data` |
| Documents | `search_documents`, `read_document` |
| Interaction | `ask_user`, `get_briefing`, `global_search` |

**Added:** `ask_user`, `batch_create_cost_events`.
**Removed:** `set_temporal_context`.

---

### 3.3 Change Order Manager (`change_order_manager`)

**Purpose:** Perform all change order configuration — creation, approval workflow, impact analysis, branch management.

#### Current Tools (14)

```
get_briefing, get_temporal_context, set_temporal_context, global_search,
find_change_orders, create_change_order, generate_change_order_draft,
submit_change_order_for_approval, approve_change_order, reject_change_order,
analyze_change_order_impact, delete_change_order, find_control_accounts,
get_control_account_budget
```

#### Gap

- ❌ Missing `ask_user`
- ❌ Missing `batch_create_change_orders` — exists as a tool but not assigned
- ⚠️ Has `set_temporal_context` — essential for branch switching (isolated/merged mode). **Keep this** — change order specialist must switch branches to analyze impact.
- ❌ Missing read tools to understand project structure before creating COs: `get_project`, `get_project_structure`, `find_wbs_elements`, `find_work_packages`, `find_cost_elements`

#### Recommended Tools

| Domain | Tools |
|---|---|
| Change Orders | `find_change_orders`, `create_change_order`, `generate_change_order_draft`, `submit_change_order_for_approval`, `approve_change_order`, `reject_change_order`, `analyze_change_order_impact`, `delete_change_order`, `batch_create_change_orders` |
| Temporal / Branch | `get_temporal_context`, `set_temporal_context` |
| Read-only structure | `get_project`, `get_project_context`, `get_project_structure`, `find_wbs_elements`, `find_work_packages`, `find_cost_elements`, `find_control_accounts`, `get_control_account_budget`, `get_cost_element_details` |
| Interaction | `ask_user`, `get_briefing`, `global_search` |

**Added:** `ask_user`, `batch_create_change_orders`, `get_project`, `get_project_context`, `get_project_structure`, `find_wbs_elements`, `find_work_packages`, `find_cost_elements`, `get_cost_element_details`.
**Kept:** `set_temporal_context` — essential for branch switching.

---

### 3.4 EVM Analyst (`evm_analyst`)

**Purpose:** Read project data and perform EVM analysis. Read-only.

#### Current Tools (13)

```
get_briefing, get_temporal_context, global_search, get_project_analysis,
get_project_forecast, find_control_accounts, get_control_account_budget,
find_work_packages, find_cost_elements, get_cost_element_details,
get_progress_data, get_work_package_budget_status
```

#### Gap

- ❌ Missing `ask_user`
- ❌ Missing `get_project_context`, `get_project_structure`, `get_project`, `find_wbs_elements` — needed for complete analysis context
- ⚠️ `default_role` is `ai-viewer` (read-only) — correct for analysis-only specialist

#### Recommended Tools

| Domain | Tools |
|---|---|
| EVM Analysis | `get_project_analysis`, `get_project_forecast`, `get_cost_element_details`, `get_progress_data` |
| Read-only structure | `get_project_context`, `get_project_structure`, `get_project`, `get_temporal_context`, `find_wbs_elements`, `find_cost_elements`, `find_work_packages`, `find_control_accounts`, `get_control_account_budget`, `get_work_package_budget_status`, `batch_get_work_package_budget_status` |
| Interaction | `ask_user`, `get_briefing`, `global_search` |

**Added:** `ask_user`, `get_project_context`, `get_project_structure`, `get_project`, `find_wbs_elements`, `batch_get_work_package_budget_status`.

---

### 3.5 Visualization Specialist (`visualization_specialist`)

**Purpose:** Generate diagrams and visual representations.

#### Current Tools (5)

```
get_briefing, get_temporal_context, global_search, find_control_accounts,
generate_mermaid_diagram
```

#### Gap

- ❌ Missing `ask_user` — may need to clarify diagram requirements
- ❌ Severely under-tooled — cannot read project structure, WBS hierarchy, cost data, or change order data to build meaningful diagrams
- Needs read access to all entities it might visualize

#### Recommended Tools

| Domain | Tools |
|---|---|
| Visualization | `generate_mermaid_diagram` |
| Read-only structure | `get_project_context`, `get_project_structure`, `get_project`, `get_temporal_context`, `find_wbs_elements`, `find_cost_elements`, `find_work_packages`, `find_control_accounts`, `find_change_orders`, `get_cost_element_details`, `get_work_package_budget_status`, `get_control_account_budget`, `get_project_analysis`, `get_progress_data` |
| Interaction | `ask_user`, `get_briefing`, `global_search` |

**Added:** `ask_user` + 13 read tools. Without these, the specialist cannot generate any meaningful diagram.

---

### 3.6 User Admin (`user_admin`)

**Purpose:** User and organizational unit management. System configuration.

#### Current Tools (11)

```
get_briefing, get_temporal_context, global_search, find_users, create_user,
update_user, delete_user, find_organizational_units,
create_organizational_unit, update_organizational_unit,
delete_organizational_unit
```

#### Gap

- ❌ Missing `ask_user` — critical for confirming destructive user operations
- ❌ Missing batch tools: `batch_create_users`, `batch_create_organizational_units`

#### Recommended Tools

| Domain | Tools |
|---|---|
| Users | `find_users`, `create_user`, `update_user`, `delete_user`, `batch_create_users` |
| Org Units | `find_organizational_units`, `create_organizational_unit`, `update_organizational_unit`, `delete_organizational_unit`, `batch_create_organizational_units` |
| Interaction | `ask_user`, `get_briefing`, `get_temporal_context`, `global_search` |

**Added:** `ask_user`, `batch_create_users`, `batch_create_organizational_units`.

---

### 3.7 General Purpose (`general_purpose`)

**Purpose:** Fallback agent for tasks that don't fit a specialist.

#### Current Config

- `allowed_tools: ["*"]` — access to all tools
- `default_role: ai-manager`

#### Gap

- ❌ Missing `ask_user` in explicit list, but `["*"]` includes everything
- ⚠️ `default_role: ai-manager` is correct for write access
- ✅ No changes needed — wildcard tool access is appropriate for fallback

---

### 3.8 NEW: Time Traveller Specialist (`time_traveller`)

**Purpose:** Change temporal context — viewing date, branch, branch mode. Verify temporal state.

#### Why Needed

Currently `set_temporal_context` is scattered across project_manager, change_order_manager, accountant, and all main agents' direct_tools. A dedicated specialist:
- Centralizes temporal operations
- Can explain temporal implications to the user
- Prevents accidental time-travel by non-specialist agents
- Aligns with the user's requirement for a "time traveller specialist"

#### Recommended Config

```json
{
  "name": "time_traveller",
  "description": "Specialist for temporal context management — time-travel, branch switching, and temporal state verification",
  "presentation_prompt": "Specialist for changing temporal context: viewing date (as_of), branch selection, and branch mode (isolated/merged)",
  "system_prompt": "You are a temporal context specialist.\n\nBefore calling any tool, review your briefing context to avoid redundant queries.\n\nYou manage the temporal viewing context:\n- **as_of date**: Change the point-in-time for historical queries\n- **branch**: Switch to a change order branch (e.g. BR-CO-2026-001)\n- **branch_mode**: \"isolated\" (only branch changes) or \"merged\" (baseline + changes)\n\nExplain the implications of each temporal change to the user.\nAlways confirm the resulting context after switching.",
  "model_id": null,
  "default_role": "ai-viewer",
  "agent_type": "specialist",
  "is_active": true,
  "temperature": null,
  "max_tokens": null,
  "recursion_limit": null,
  "allowed_tools": [
    "ask_user", "get_briefing", "get_temporal_context", "set_temporal_context",
    "get_project_context", "get_project_structure", "list_projects", "get_project",
    "global_search"
  ],
  "structured_output_schema": null
}
```

#### Impact on Other Agents

- **Remove `set_temporal_context`** from: `project_manager`, `accountant` (they no longer need it)
- **Keep `set_temporal_context`** on: `change_order_manager` (branch switching is integral to CO workflow)
- **Keep `set_temporal_context`** in all main agent `direct_tools` (supervisor needs it for direct time-travel requests)
- **Add `time_traveller`** to `allowed_specialists` on all 3 main agents

---

## 4. `ask_user` Availability Gap

| Specialist | Has `ask_user` | Required Action |
|---|---|---|
| `project_manager` | ✅ | None |
| `evm_analyst` | ❌ | Add |
| `change_order_manager` | ❌ | Add |
| `user_admin` | ❌ | Add |
| `visualization_specialist` | ❌ | Add |
| `accountant` | ❌ | Add |
| `general_purpose` | ✅ (via `["*"]`) | None |
| `time_traveller` (new) | ✅ (in design) | — |

**5 specialists need `ask_user` added.**

---

## 5. System Prompt Consolidation

### Problem

Current system prompts are verbose (80–300+ words), repeat information already available in tool descriptions, and lack a consistent structure.

### Principles for Concise Prompts

1. **Context-review-first**: Always instruct the specialist to review briefing context before calling tools
2. **Domain-only**: Describe only what the specialist does — not how tools work (tool descriptions handle that)
3. **No filler**: Remove "You are a friendly and accessible...", "When responding: Be conversational...", etc.
4. **Structure**: Role → Domain → Key rules (max 3–5 bullet points)

### Proposed Prompt Templates

#### Specialist Prompt Template (~50 words)

```
You are a {role} specialist.
Before calling tools, review your briefing context to avoid redundant queries.

Domain: {1-2 sentence domain description}

Key rules:
- {rule 1}
- {rule 2}
- {rule 3}
```

#### Main Agent System Prompt Template (~60 words)

```
You are a {role} for the Backcast project management system.
Delegate to specialists for domain work. Use direct tools for quick lookups.

Capabilities: {1-2 sentences}
Temporal: set_temporal_context changes the viewing date or branch.

Rules:
- Confirm before destructive operations
- Be concise and action-oriented
```

### Current vs Proposed — Token Savings Estimate

| Agent | Current (words) | Proposed (words) | Savings |
|---|---|---|---|
| Friendly Project Analyzer | 86 | 50 | ~42% |
| Senior Project Manager | 113 | 55 | ~51% |
| System Manager | 72 | 45 | ~38% |
| project_manager | 178 | 55 | ~69% |
| evm_analyst | 88 | 40 | ~55% |
| change_order_manager | 180 | 65 | ~64% |
| user_admin | 45 | 30 | ~33% |
| visualization_specialist | 42 | 30 | ~29% |
| accountant | 85 | 45 | ~47% |
| **Total** | **~869** | **~415** | **~52%** |

---

## 6. Planner & Supervisor Prompt Consolidation

### Problem

Each of the 3 main agents carries its own `planner_prompt` and `supervisor_prompt`. These are near-identical with minor wording variations (e.g. "read-only project analysis assistant" vs "senior project management assistant" vs "system administration assistant").

### Current Duplication

| Prompt | Word Count | Variations |
|---|---|---|
| Planner prompts | 3 × ~65 words | Role name + step limit + specialist list |
| Supervisor prompts | 3 × ~80 words | Role name + failure handling wording |

### Proposed Consolidation

**Option A: Single template with placeholders** (recommended)

Define the planner/supervisor prompts once in code (or a single DB row), using `{role_name}` and `{max_steps}` placeholders. The specialist section is already injected via `{specialist_section}`.

**Option B: Remove from seed data, use code defaults**

The code in `planner.py` and `supervisor_orchestrator.py` already has hardcoded defaults. Remove planner/supervisor prompts from seed data entirely and let the code defaults handle it.

### Recommended Planner Prompt (consolidated)

```
You are a request planner for the Backcast {role_name}.

{specialist_section}

## Rules
- Default to single-step plans. Multi-step only when genuinely needed.
- Maximum {max_steps} steps.
- Use ONLY specialist names from the list above.
- Keep task descriptions focused and actionable.
- Only add dependencies when step N genuinely needs output from step M.
```

### Recommended Supervisor Prompt (consolidated)

```
You are the supervisor for the Backcast {role_name}.

{specialist_section}

## Role
Execute the plan by delegating to specialists, one step at a time.

## Rules
- Follow the plan. Do NOT reassign steps to different specialists.
- Do NOT summarize the briefing — the user reads it directly.
- Only respond to the user for clarification or to confirm destructive operations.
- Check the briefing before each delegation to avoid duplicate work.
```

### Per-Main-Agent Customization

| Main Agent | `role_name` | `max_steps` |
|---|---|---|
| Friendly Project Analyzer | "project analysis assistant (read-only)" | 3 |
| Senior Project Manager | "project management assistant" | 5 |
| System Manager | "system administration assistant" | 2 |

---

## 7. Main Agent Direct Tools Review

### Current State

| Main Agent | Direct Tools | Count |
|---|---|---|
| Friendly Project Analyzer | Read-only tools + `set_temporal_context` | 23 |
| Senior Project Manager | Read-only tools + `set_temporal_context` + `batch_get_work_package_budget_status` | 24 |
| System Manager | Read-only tools + `set_temporal_context` | 23 |

### Gap

- All 3 main agents have nearly identical `direct_tools` — the only difference is the Senior PM has one extra batch tool
- `set_temporal_context` is appropriate as a direct tool — the supervisor should be able to time-travel before delegating

### Recommended Direct Tools

Keep the current pattern but normalize across all agents:

**Common direct tools for all main agents:**
```
# Context
get_temporal_context, set_temporal_context, get_project_context,
get_project_structure, global_search
# Read: Projects
list_projects, get_project
# Read: Structure
find_wbs_elements, find_cost_elements, find_cost_element_types,
find_cost_event_types, find_work_packages, find_control_accounts,
find_cost_events, find_users, find_organizational_units
# Read: Details & Analysis
get_cost_element_details, get_progress_data,
get_work_package_budget_status, get_control_account_budget,
batch_get_work_package_budget_status,
get_project_analysis, get_project_forecast, get_coq_data
# Documents
search_documents, read_document
```

**No changes needed** — current direct tools are reasonable. The main agents should have broad read access to answer quick questions without delegation.

---

## 8. Summary of Required Changes

### Seed Data Changes (`seed_system_config.json`)

| Change | Details |
|---|---|
| **Remove model_id** from 7 specialists | Set to `null` |
| **Remove temperature/max_tokens/recursion_limit** from 7 specialists | Set to `null` |
| **Add `time_traveller` specialist** | New entry with temporal tools |
| **Add `ask_user`** to 5 specialists | evm_analyst, change_order_manager, user_admin, visualization_specialist, accountant |
| **Trim `project_manager` tools** | Remove cost registrations, cost events, forecasts, progress entries, cost element types |
| **Expand `visualization_specialist` tools** | Add 13 read tools |
| **Expand `change_order_manager` tools** | Add ask_user, batch_create_change_orders, read tools |
| **Expand `evm_analyst` tools** | Add ask_user, project structure reads |
| **Expand `user_admin` tools** | Add ask_user, batch tools |
| **Add `time_traveller`** to all 3 main agents' `allowed_specialists` | |
| **Consolidate system prompts** | Rewrite all 10 prompts to be concise, context-review-first |
| **Consolidate planner/supervisor prompts** | Single template with `{role_name}` and `{max_steps}` placeholders |

### Code Changes

| Change | File | Details |
|---|---|---|
| Default specialist prompt | `subagent_compiler.py` | Update `DEFAULT_SYSTEM_PROMPT` to include "review context before tools" instruction |
| Planner template | `planner.py` | Consolidate `_PLANNER_PROMPT_TEMPLATE` with role placeholder |
| Supervisor template | `supervisor_orchestrator.py` | Consolidate `_BASE_SUPERVISOR_PROMPT` with role placeholder |

---

## 9. Risk Assessment

| Risk | Impact | Mitigation |
|---|---|---|
| Removing `set_temporal_context` from project_manager | Specialists lose direct time-travel | Delegate to time_traveller specialist when needed |
| Trimming project_manager tool set | Some multi-step workflows need two specialists | Planner handles decomposition — cost operations route to accountant |
| Keeping `set_temporal_context` on change_order_manager | CO specialist can still switch branches independently | This is intentional — branch switching is integral to CO workflow |
| Token savings from prompt consolidation | May reduce specialist "personality" | Acceptable trade-off — specialists should be functional, not chatty |

---

## 10. Appendix — Complete Tool Catalog (78 tools)

<details>
<summary>Expand for full tool list by category</summary>

### Projects (11)
`list_projects`, `get_project`, `create_project`, `update_project`, `delete_project`, `batch_create_projects`, `find_wbs_elements`, `create_wbs_element`, `update_wbs_element`, `delete_wbs_element`, `batch_create_wbs_elements`, `batch_update_wbs_elements`

### Cost Management (32)
`find_cost_elements`, `create_cost_element`, `update_cost_element`, `delete_cost_element`, `batch_create_cost_elements`, `batch_delete_cost_elements`, `find_cost_element_types`, `create_cost_element_type`, `update_cost_element_type`, `delete_cost_element_type`, `batch_create_cost_element_types`, `find_cost_events`, `create_cost_event`, `update_cost_event`, `delete_cost_event`, `batch_create_cost_events`, `get_coq_data`, `find_cost_event_types`, `create_cost_event_type`, `update_cost_event_type`, `delete_cost_event_type`, `create_forecast`, `update_forecast`, `delete_forecast`, `batch_create_forecasts`, `get_cost_element_details`, `create_cost_registration`, `update_cost_registration`, `delete_cost_registration`, `list_cost_registrations`, `batch_create_cost_registrations`

### Work Tracking (11)
`find_control_accounts`, `create_control_account`, `update_control_account`, `delete_control_account`, `get_control_account_budget`, `batch_create_control_accounts`, `find_work_packages`, `create_work_package`, `update_work_package`, `delete_work_package`, `get_work_package_budget_status`, `batch_create_work_packages`, `batch_get_work_package_budget_status`, `create_progress_entry`, `update_progress_entry`, `delete_progress_entry`, `get_progress_data`, `batch_create_progress_entries`

### Change Orders (9)
`find_change_orders`, `create_change_order`, `generate_change_order_draft`, `submit_change_order_for_approval`, `approve_change_order`, `reject_change_order`, `analyze_change_order_impact`, `delete_change_order`, `batch_create_change_orders`

### Analysis (3)
`get_project_analysis`, `get_project_forecast`, `global_search`

### Users (12)
`find_users`, `create_user`, `update_user`, `delete_user`, `batch_create_users`, `find_organizational_units`, `create_organizational_unit`, `update_organizational_unit`, `delete_organizational_unit`, `batch_create_organizational_units`

### Context (8)
`get_project_context`, `get_project_structure`, `get_temporal_context`, `set_temporal_context`, `search_documents`, `read_document`, `get_briefing`, `ask_user`

### Interaction (2)
`generate_mermaid_diagram`

</details>
