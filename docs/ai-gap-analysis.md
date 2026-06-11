# AI Agent System — Gap Analysis

**Date:** 2026-06-07 (updated)
**Scope:** `backend/seed/seed_system_config.json`, `backend/app/ai/`
**Status:** Implemented

---

## 1. Executive Summary

| Dimension | Previous State | Implemented State |
|---|---|---|
| Specialist model_id | All 7 set to a model UUID | `null` — specialists inherit main agent model |
| Specialist temperature/max_tokens/recursion_limit | All 7 set per specialist | `null` — inherited from main agent |
| Specialist count | 7 specialists | 9 specialists (+controller, +time_traveller) |
| `ask_user` availability | 1/7 specialists | 8/9 specialists (general_purpose uses `["*"]`) |
| System prompts | 80–300 words, verbose | ~50 words, context-review-first |
| Planner/Supervisor prompts | Near-identical across 3 main agents | Differentiated by role: read-only, full-ops, admin |
| Tool assignment accuracy | Specialists carried tools outside domain | Tight domain-aligned tool sets |
| `visualization_specialist` tools | 5 tools, no project structure access | 18 tools with full read access |

---

## 2. Model Configuration

### Finding

All specialists previously set `model_id`, `temperature`, `max_tokens`, and `recursion_limit`. These were **completely ignored** by the runtime — `subagent_compiler.py` compiles all specialists with the same LLM instance from the main agent.

### Action Taken

All specialist configs now set these fields to `null`. The DB schema already supported `NULL`.

---

## 3. Specialist Inventory

### 3.1 Project Manager (`project_manager`) — 41 tools

**Purpose:** Read and modify project structure — projects, WBS Elements, Control Accounts, Work Packages, Cost Elements, and progress entries.

| Domain | Tools |
|---|---|
| Projects | `create_project`, `update_project`, `delete_project`, `list_projects`, `get_project`, `batch_create_projects` |
| WBS Elements | `create_wbs_element`, `update_wbs_element`, `delete_wbs_element`, `find_wbs_elements`, `batch_create_wbs_elements`, `batch_update_wbs_elements` |
| Control Accounts | `create_control_account`, `update_control_account`, `delete_control_account`, `find_control_accounts`, `get_control_account_budget`, `batch_create_control_accounts` |
| Work Packages | `create_work_package`, `update_work_package`, `delete_work_package`, `find_work_packages`, `get_work_package_budget_status`, `batch_create_work_packages`, `batch_get_work_package_budget_status` |
| Cost Elements | `create_cost_element`, `update_cost_element`, `delete_cost_element`, `find_cost_elements`, `batch_create_cost_elements`, `batch_delete_cost_elements` |
| Progress Entries | `create_progress_entry`, `update_progress_entry`, `delete_progress_entry`, `batch_create_progress_entries` |
| Context | `get_project_context`, `get_project_structure`, `get_temporal_context`, `get_cost_element_details` |
| Interaction | `ask_user`, `get_briefing`, `global_search` |

**Removed from original:** cost registrations, cost events, forecasts, cost element types, cost event types, `set_temporal_context`, `search_documents`, `read_document`, `get_project_forecast`, `get_coq_data`, `list_cost_registrations`.

---

### 3.2 Accountant (`accountant`) — 35 tools

**Purpose:** Cost registrations, cost events, forecasts, COQ tracking, and document retrieval.

| Domain | Tools |
|---|---|
| Cost Registrations | `create_cost_registration`, `update_cost_registration`, `delete_cost_registration`, `list_cost_registrations`, `batch_create_cost_registrations` |
| Cost Events | `create_cost_event`, `update_cost_event`, `delete_cost_event`, `find_cost_events`, `batch_create_cost_events`, `get_coq_data` |
| Forecasts | `create_forecast`, `update_forecast`, `delete_forecast`, `batch_create_forecasts` |
| Read-only context | `get_project_context`, `get_project_structure`, `get_temporal_context`, `list_projects`, `get_project`, `find_wbs_elements`, `find_cost_elements`, `find_work_packages`, `find_control_accounts`, `get_cost_element_details`, `get_work_package_budget_status`, `get_control_account_budget`, `get_progress_data` |
| Type references | `find_cost_element_types`, `find_cost_event_types` |
| Documents | `search_documents`, `read_document` |
| Interaction | `ask_user`, `get_briefing`, `global_search` |

**Added:** `ask_user`, `batch_create_cost_events`, forecast tools.
**Removed:** `set_temporal_context` (delegated to time_traveller).

---

### 3.3 Change Order Manager (`change_order_manager`) — 23 tools

**Purpose:** Full change order lifecycle — creation, approval workflows, impact analysis, branch management.

| Domain | Tools |
|---|---|
| Change Orders | `find_change_orders`, `create_change_order`, `generate_change_order_draft`, `submit_change_order_for_approval`, `approve_change_order`, `reject_change_order`, `analyze_change_order_impact`, `delete_change_order`, `batch_create_change_orders` |
| Temporal / Branch | `get_temporal_context`, `set_temporal_context` (kept — branch switching is integral to CO workflow) |
| Read-only structure | `get_project`, `get_project_context`, `get_project_structure`, `find_wbs_elements`, `find_work_packages`, `find_cost_elements`, `find_control_accounts`, `get_control_account_budget`, `get_cost_element_details` |
| Interaction | `ask_user`, `get_briefing`, `global_search` |

**Added:** `ask_user`, `batch_create_change_orders`, project structure read tools.

---

### 3.4 EVM Analyst (`evm_analyst`) — 18 tools

**Purpose:** EVM metrics calculation and project performance analysis. Read-only.

| Domain | Tools |
|---|---|
| EVM Analysis | `get_project_analysis`, `get_project_forecast`, `get_cost_element_details`, `get_progress_data` |
| Read-only structure | `get_project_context`, `get_project_structure`, `get_project`, `get_temporal_context`, `find_wbs_elements`, `find_cost_elements`, `find_work_packages`, `find_control_accounts`, `get_control_account_budget`, `get_work_package_budget_status`, `batch_get_work_package_budget_status` |
| Interaction | `ask_user`, `get_briefing`, `global_search` |

**Added:** `ask_user`, `get_project_context`, `get_project_structure`, `get_project`, `find_wbs_elements`, `batch_get_work_package_budget_status`.

---

### 3.5 Visualization Specialist (`visualization_specialist`) — 18 tools

**Purpose:** Generate Mermaid diagrams for project structures, hierarchies, and cost breakdowns.

| Domain | Tools |
|---|---|
| Visualization | `generate_mermaid_diagram` |
| Read-only structure | `get_project_context`, `get_project_structure`, `get_project`, `get_temporal_context`, `find_wbs_elements`, `find_cost_elements`, `find_work_packages`, `find_control_accounts`, `find_change_orders`, `get_cost_element_details`, `get_work_package_budget_status`, `get_control_account_budget`, `get_project_analysis`, `get_progress_data` |
| Interaction | `ask_user`, `get_briefing`, `global_search` |

**Added:** `ask_user` + 13 read tools. Previously had only 5 tools and could not generate meaningful diagrams.

---

### 3.6 User Admin (`user_admin`) — 9 tools

**Purpose:** User account management only.

| Domain | Tools |
|---|---|
| Users | `find_users`, `create_user`, `update_user`, `delete_user`, `batch_create_users` |
| Interaction | `ask_user`, `get_briefing`, `get_temporal_context`, `global_search` |

**Added:** `ask_user`, `batch_create_users`.
**Removed:** Organizational unit tools (moved to controller).

---

### 3.7 Controller (`controller`) — NEW — 18 tools

**Purpose:** Master data management — cost element types, cost event types, and organizational units. The structural configuration shared across projects.

| Domain | Tools |
|---|---|
| Cost Element Types | `find_cost_element_types`, `create_cost_element_type`, `update_cost_element_type`, `delete_cost_element_type`, `batch_create_cost_element_types` |
| Cost Event Types | `find_cost_event_types`, `create_cost_event_type`, `update_cost_event_type`, `delete_cost_event_type` |
| Org Units | `find_organizational_units`, `create_organizational_unit`, `update_organizational_unit`, `delete_organizational_unit`, `batch_create_organizational_units` |
| Interaction | `ask_user`, `get_briefing`, `get_temporal_context`, `global_search` |

**Rationale:** Centralizes master data that was previously scattered across project_manager, accountant, and user_admin. The controller manages the "configuration layer" shared across all projects.

---

### 3.8 Time Traveller (`time_traveller`) — NEW — 9 tools

**Purpose:** Temporal context management — change viewing date, switch branches, set branch mode.

| Domain | Tools |
|---|---|
| Temporal | `get_temporal_context`, `set_temporal_context` |
| Read-only context | `get_project_context`, `get_project_structure`, `list_projects`, `get_project` |
| Interaction | `ask_user`, `get_briefing`, `global_search` |

**Rationale:** Centralizes temporal operations. `set_temporal_context` removed from project_manager and accountant. Kept on change_order_manager (branch switching is integral to CO workflow).

---

### 3.9 General Purpose (`general_purpose`) — wildcard

**Purpose:** Fallback for tasks that don't fit a specialist.

- `allowed_tools: ["*"]` — access to all tools
- `default_role: ai-manager`
- No changes needed

---

## 4. `ask_user` Availability — Final State

| Specialist | Has `ask_user` | Status |
|---|---|---|
| `project_manager` | ✅ | Unchanged |
| `evm_analyst` | ✅ | Added |
| `change_order_manager` | ✅ | Added |
| `user_admin` | ✅ | Added |
| `visualization_specialist` | ✅ | Added |
| `accountant` | ✅ | Added |
| `controller` | ✅ | Included in new design |
| `time_traveller` | ✅ | Included in new design |
| `general_purpose` | ✅ (via `["*"]`) | Unchanged |

---

## 5. System Prompt Design

### Pattern

All specialist prompts follow a consistent structure:

```
You are a {role} specialist.
Before calling tools, review your briefing context to avoid redundant queries.

Domain: {1-2 sentence description}

Key rules:
- {rule 1}
- {rule 2}
- {rule 3}
```

### Main Agent Prompts

Each main agent prompt follows:

```
You are a {role} for the Backcast system.
Delegate to specialists for domain work. Use direct tools for quick lookups.

{2-3 sentences on capabilities}

Rules:
- {rule}
- {rule}
- {rule}
```

### Token Savings

| Agent | Previous (words) | Current (words) | Savings |
|---|---|---|---|
| Friendly Project Analyzer | 86 | 47 | ~45% |
| Senior Project Manager | 113 | 50 | ~56% |
| System Manager | 72 | 40 | ~44% |
| project_manager | 178 | 49 | ~72% |
| evm_analyst | 88 | 42 | ~52% |
| change_order_manager | 180 | 50 | ~72% |
| user_admin | 45 | 34 | ~24% |
| visualization_specialist | 42 | 39 | ~7% |
| accountant | 85 | 44 | ~48% |
| **Total** | **~869** | **~395** | **~55%** |

---

## 6. Planner & Supervisor Prompts — Differentiated by Role

### Design Decision

Rather than consolidating into a single template, planner and supervisor prompts are differentiated by the main agent's role and use case.

### Friendly Project Analyzer (read-only)

**Planner:** Emphasizes read-only constraint, prefers single-step plans, max 3 steps.
**Supervisor:** Highlights no-modification constraint, conversational tone, clarification-only responses.

### Senior Project Manager (full operational access)

**Planner:** Includes multi-step pattern examples (create structure + budget, analyze + create CO, verify + register costs), max 5 steps.
**Supervisor:** Includes failure recovery (retry or skip), destructive operation confirmation, action-oriented tone.

### System Manager (admin)

**Planner:** Emphasizes single-step default, max 2 steps, rare multi-step patterns.
**Supervisor:** Highlights sensitive configuration, explicit delete confirmation requirement.

### Customization Points

| Main Agent | Role descriptor | Max steps | Key differentiation |
|---|---|---|---|
| Friendly Project Analyzer | "read-only project analysis assistant" | 3 | No-modification constraint |
| Senior Project Manager | "senior project management assistant with full operational access" | 5 | Multi-step patterns, failure recovery |
| System Manager | "system administration assistant" | 2 | Sensitive config, delete confirmation |

---

## 7. Main Agent Delegation Configuration

### Friendly Project Analyzer

- **Role:** `ai-viewer` (read-only)
- **Direct Tools:** 25 read-only tools + `set_temporal_context`
- **Specialists:** `evm_analyst`, `visualization_specialist`, `accountant`, `time_traveller`

### Senior Project Manager

- **Role:** `ai-manager` (read/write)
- **Direct Tools:** 26 read tools + `set_temporal_context` + `batch_get_work_package_budget_status`
- **Specialists:** `project_manager`, `change_order_manager`, `evm_analyst`, `visualization_specialist`, `accountant`, `time_traveller`

### System Manager

- **Role:** `ai-admin` (full admin)
- **Direct Tools:** 25 read-only tools + `set_temporal_context`
- **Specialists:** `user_admin`, `controller`, `time_traveller`

---

## 8. Code Changes

| File | Change |
|---|---|
| `backend/app/ai/subagent_compiler.py` | Updated `DEFAULT_SYSTEM_PROMPT` to include "review briefing context" instruction |

---

## 9. `set_temporal_context` Distribution

| Agent | Has `set_temporal_context` | Rationale |
|---|---|---|
| Main agents (direct_tools) | ✅ | Supervisor can time-travel before delegating |
| `change_order_manager` | ✅ | Branch switching integral to CO workflow |
| `time_traveller` | ✅ | Core responsibility |
| `project_manager` | ❌ | Removed — delegate to time_traveller |
| `accountant` | ❌ | Removed — delegate to time_traveller |
| `evm_analyst` | ❌ | Read-only, no temporal changes needed |
| `visualization_specialist` | ❌ | Read-only, no temporal changes needed |
| `user_admin` | ❌ | No temporal context needed |
| `controller` | ❌ | No temporal context needed |
| `general_purpose` | ✅ (via `["*"]`) | Fallback has all tools |

---

## 10. Appendix — Specialist Tool Assignment Matrix

| Tool Category | project_manager | accountant | change_order_mgr | evm_analyst | visualization | user_admin | controller | time_traveller |
|---|---|---|---|---|---|---|---|---|
| Projects CRUD | ✅ | — | — | — | — | — | — | — |
| Projects Read | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ |
| WBS CRUD | ✅ | — | — | — | — | — | — | — |
| WBS Read | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| Control Accounts CRUD | ✅ | — | — | — | — | — | — | — |
| Control Accounts Read | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| Work Packages CRUD | ✅ | — | — | — | — | — | — | — |
| Work Packages Read | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| Cost Elements CRUD | ✅ | — | — | — | — | — | — | — |
| Cost Elements Read | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| Cost Registrations | — | ✅ | — | — | — | — | — | — |
| Cost Events | — | ✅ | — | — | — | — | — | — |
| Forecasts | — | ✅ | — | — | — | — | — | — |
| Progress Entries | ✅ | — | — | — | — | — | — | — |
| Change Orders | — | — | ✅ | — | — | — | — | — |
| Cost Element Types | — | (find) | — | — | — | — | ✅ | — |
| Cost Event Types | — | (find) | — | — | — | — | ✅ | — |
| Org Units | — | — | — | — | — | — | ✅ | — |
| Users | — | — | — | — | — | ✅ | — | — |
| EVM Analysis | — | — | — | ✅ | — | — | — | — |
| Mermaid Diagrams | — | — | — | — | ✅ | — | — | — |
| Temporal Context | (get) | (get) | get+set | (get) | (get) | (get) | (get) | get+set |
| Documents | — | ✅ | — | — | — | — | — | — |
| `ask_user` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
