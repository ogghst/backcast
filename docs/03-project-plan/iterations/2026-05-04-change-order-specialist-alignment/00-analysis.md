# Analysis: Align Change Order Specialist Agent with Documented Workflow

**Created:** 2026-05-04
**Request:** The change order specialist AI agent needs to be aligned with the documented change order workflow. The specialist's prompt and tools do not match the intended process flow. Three workflow tools have critical bugs (bypassing service validation), and 7 service operations are missing AI tool wrappers entirely.

---

## Clarified Requirements

The change order specialist agent must accurately reflect and enforce the documented change order lifecycle. Currently, three tools bypass the proper workflow service methods, and seven service operations have no AI tool wrappers. The specialist prompt lacks phase-by-phase guidance needed to steer the agent through the full workflow correctly.

### Functional Requirements

**FR-1: Fix 3 buggy workflow tools** to call the correct service methods:
- `submit_change_order_for_approval` must call `service.submit_for_approval()` instead of `service.update_change_order(status="Pending Approval")`
- `approve_change_order` must call `service.approve_change_order()` instead of `service.update_change_order(status="Approved")`
- `reject_change_order` must call `service.reject_change_order()` instead of `service.update_change_order(status="Rejected")`

Each of these fixes restores the following bypassed validations:
- Workflow state transition validation (is the current status valid for this action?)
- Control date sequence validation
- Impact analysis completion check (submit requires completed analysis)
- Approver authority validation (approve/reject requires sufficient role)
- Assigned approver match check (only the assigned approver can approve)
- Branch locking on submission
- Branch unlocking on rejection
- SLA deadline calculation
- Audit trail entries via proper command objects

**FR-2: Add 7 new AI tool wrappers** for uncovered service operations:
1. `implement_change_order` wrapping `service.merge_change_order()` -- merges branch to main, status becomes "Implemented"
2. `get_change_order_impact` wrapping `ImpactAnalysisService.analyze_impact()` -- full KPI scorecard, waterfall, entity changes
3. `get_pending_approvals` wrapping `service.get_pending_approvals()` -- COs awaiting user's approval
4. `get_change_order_approval_info` -- composite info: CO + impact level + approver + SLA + authority
5. `delete_change_order` wrapping `service.delete_change_order()` -- soft delete for draft COs
6. `archive_change_order_branch` wrapping `service.archive_change_order_branch()` -- archive implemented/rejected branches
7. `recover_change_order` wrapping `service.recover_change_order()` -- admin recovery for stuck workflows

**FR-3: Rewrite the specialist system prompt** to include:
- Phase-by-phase workflow guidance (Creation, Scoping, Impact Analysis, Submission, Review, Implementation, Rejection Handling)
- Pre-submission checklist (impact analysis completed, approver assigned, branch has modifications)
- Post-approval implementation guidance (merge to main, branch archival)
- Rejection handling (re-edit and resubmit)
- SLA awareness (deadlines per impact level)
- Authority matrix awareness (who can approve what)
- Tool selection guidance per workflow phase

**FR-4: Register all 7 new tools** in `create_project_tools()` in `app/ai/tools/__init__.py` and update the specialist's `allowed_tools` list in `app/ai/subagents/__init__.py`.

### Non-Functional Requirements

- **NFR-1:** All tools follow the existing `@ai_tool` decorator pattern (permissions, risk_level, category)
- **NFR-2:** Proper RBAC permissions for new tools (admin tools use `change-order-admin`, workflow tools use existing permissions)
- **NFR-3:** Temporal context logging on all new tools (log_temporal_context + add_temporal_metadata)
- **NFR-4:** Risk level classification: LOW for read tools, HIGH for state-changing tools, CRITICAL for merge and recovery
- **NFR-5:** No changes to service layer -- this is purely an AI tool/prompt alignment task

### Constraints

- **C-1:** Service method signatures are the source of truth -- tools must wrap them exactly
- **C-2:** No frontend changes required
- **C-3:** No database migrations required
- **C-4:** Must not break existing AI tool registration/caching mechanism
- **C-5:** The `analyze_change_order_impact` tool already exists but uses a simplified inline calculation -- it should be refactored to call `ImpactAnalysisService.analyze_impact()` instead

---

## Context Discovery

### Product Scope

- Change Order workflow is a core EVM feature (FR-8.3)
- Approval authority matrix is a business requirement with SLA compliance
- The specialist agent is the primary AI interface for change order operations
- Users expect the AI to enforce workflow rules, not bypass them

### Architecture Context

- **Bounded contexts involved:** Change Order Workflow, Branching, Impact Analysis, Approval Matrix
- **Existing patterns to follow:** `@ai_tool` decorator pattern in `change_order_template.py` and other template files
- **Service layer organization:** `ChangeOrderService` (lifecycle), `ChangeOrderWorkflowService` (state machine), `ImpactAnalysisService` (analysis), `ChangeOrderReportingService` (dashboard)
- **Key architectural decisions:** Tools are thin wrappers over services; no business logic in tools; `ToolContext` provides session/user/branch via injection

**Critical architectural observation:** The codebase has TWO paths for workflow transitions:
1. `ChangeOrderWorkflowService.submit_for_approval()` -- the older, standalone workflow service method that takes `db_session` directly
2. `ChangeOrderService.submit_for_approval()` -- the newer, integrated method that validates control date sequence, checks impact analysis status, uses versioned commands, and commits

The AI tools must call the `ChangeOrderService` methods (path 2) because they provide the complete validation chain including control date sequence, impact analysis prerequisite checks, and proper audit logging.

### Codebase Analysis

**Backend:**

- `backend/app/ai/tools/templates/change_order_template.py` -- 755 lines, 8 tools. Three buggy tools (lines 422-619) use `service.update_change_order()` with manual status strings. The `analyze_change_order_impact` tool (lines 627-711) performs a simplified inline calculation rather than calling `ImpactAnalysisService`.
- `backend/app/ai/subagents/__init__.py` -- CHANGE_ORDER_MANAGER_SUBAGENT (lines 137-195) with basic prompt and 10 allowed tools.
- `backend/app/ai/tools/__init__.py` -- `create_project_tools()` (lines 199-209) registers 8 change order tools.
- `backend/app/services/change_order_service.py` -- 2060+ lines. Key methods:
  - `submit_for_approval(change_order_id, actor_id, branch, comment, control_date)` -- validates Draft/Rejected status, checks impact analysis completed, calculates SLA, locks branch
  - `approve_change_order(change_order_id, approver_id, actor_id, branch, comments, control_date)` -- validates Submitted/Under Review, validates approver authority and assignment match
  - `reject_change_order(change_order_id, rejecter_id, actor_id, branch, comments, control_date)` -- validates authority, unlocks branch
  - `merge_change_order(change_order_id, actor_id, target_branch, control_date)` -- discovers all entities, merges WBEs and CostElements, updates project budget
  - `delete_change_order(change_order_id, actor_id, control_date)` -- soft delete
  - `archive_change_order_branch(change_order_id, actor_id, control_date)` -- archive branches in terminal states
  - `recover_change_order(...)` -- admin recovery with manual override
  - `get_pending_approvals(user_id, skip, limit, branch, branch_mode)` -- pending COs for a user
  - `generate_draft(...)` -- AI-powered draft generation
- `backend/app/services/impact_analysis_service.py` -- `analyze_impact(change_order_id, branch_name, branch_mode, timeout_seconds, include_evm_metrics, as_of)` returns `ImpactAnalysisResponse`
- `backend/app/services/change_order_workflow_service.py` -- standalone workflow service (older pattern, still used internally)

**Permission model (from existing tools):**
- `change-order-read` -- list, get, analyze
- `change-order-create` -- create, generate draft
- `change-order-update` -- submit for approval
- `change-order-approve` -- approve, reject
- New tools need: `change-order-delete`, `change-order-admin`

---

## Solution Options

### Option 1: Minimal Bug Fix + High-Priority Missing Tools

**Architecture & Design:**
Fix the 3 buggy tools to call correct service methods. Add only the 4 most critical missing tools: `implement_change_order`, `get_change_order_impact`, `get_pending_approvals`, and `delete_change_order`. Skip admin/recovery tools and composite info tools for a follow-up iteration. Enhance the prompt to cover the primary workflow phases.

**Implementation:**
- Fix 3 tools in `change_order_template.py` (replace `update_change_order` calls with proper service methods)
- Refactor `analyze_change_order_impact` to call `ImpactAnalysisService.analyze_impact()`
- Add 4 new tool functions following the existing pattern
- Update specialist prompt with primary workflow phases
- Register 4 new tools in `__init__.py` and update `allowed_tools`
- Estimated files: 3 files modified

**Trade-offs:**

| Aspect          | Assessment                                                                      |
| --------------- | ------------------------------------------------------------------------------- |
| Pros            | Fastest path to fixing critical bugs; minimal risk of regression                 |
| Cons            | Leaves 3 tools missing (recovery, archive, approval info); prompt still partial  |
| Complexity      | Low                                                                              |
| Maintainability | Fair -- partial coverage creates inconsistent specialist capabilities             |
| Performance     | No impact (same service calls, just routed correctly)                            |

---

### Option 2: Complete Alignment -- Fix All Bugs + All 7 New Tools + Full Prompt Rewrite

**Architecture & Design:**
Complete alignment between documented workflow and specialist agent. Fix all 3 buggy tools, add all 7 missing tools, and rewrite the specialist prompt to be phase-aware with a pre-submission checklist, implementation guidance, rejection handling, SLA awareness, and authority matrix. This makes the specialist fully autonomous for the complete change order lifecycle.

**Implementation:**
- Fix 3 buggy tools (same as Option 1)
- Refactor `analyze_change_order_impact` to call `ImpactAnalysisService.analyze_impact()`
- Add all 7 new tool functions:
  1. `implement_change_order` (HIGH risk, `change-order-update` permission)
  2. `get_change_order_impact` (LOW risk, `change-order-read` permission) -- replaces/refactors the existing `analyze_change_order_impact`
  3. `get_pending_approvals` (LOW risk, `change-order-read` permission)
  4. `get_change_order_approval_info` (LOW risk, `change-order-read` permission) -- composite read
  5. `delete_change_order` (HIGH risk, `change-order-delete` permission)
  6. `archive_change_order_branch` (HIGH risk, `change-order-update` permission)
  7. `recover_change_order` (CRITICAL risk, `change-order-admin` permission)
- Rewrite specialist prompt with 7 workflow phases
- Update `allowed_tools` with all 15 tools (8 existing + 7 new)
- Register all 7 in `create_project_tools()`
- Estimated files: 3 files modified

**Trade-offs:**

| Aspect          | Assessment                                                                         |
| --------------- | ---------------------------------------------------------------------------------- |
| Pros            | Full workflow coverage; specialist can handle any CO lifecycle scenario autonomously |
| Cons            | Larger scope increases regression risk; more tools to test                          |
| Complexity      | Medium                                                                              |
| Maintainability | Good -- complete alignment means no gaps to document or workaround                  |
| Performance     | No impact (tools are thin wrappers)                                                 |

---

### Option 3: Complete Alignment + Split Template by Workflow Phase

**Architecture & Design:**
Same coverage as Option 2, but reorganizes the change order template file into separate modules by workflow phase:
- `change_order_crud_template.py` -- list, get, create, delete, generate_draft
- `change_order_workflow_template.py` -- submit, approve, reject, recover
- `change_order_analysis_template.py` -- analyze_impact, get_pending_approvals, get_approval_info
- `change_order_implementation_template.py` -- implement, archive

Each phase module has its own imports and documentation. The specialist prompt references phase-specific tool sets.

**Implementation:**
- All changes from Option 2
- Split `change_order_template.py` (755 lines) into 4 focused modules
- Update all import paths in `__init__.py`
- Update `allowed_tools` references

**Trade-offs:**

| Aspect          | Assessment                                                                            |
| --------------- | ------------------------------------------------------------------------------------- |
| Pros            | Better file organization; easier to find and modify phase-specific tools               |
| Cons            | Large refactoring scope; high regression risk; breaks existing import paths everywhere |
| Complexity      | High                                                                                   |
| Maintainability | Good long-term, but introduces migration burden for all future changes                  |
| Performance     | No impact                                                                              |

---

## Comparison Summary

| Criteria           | Option 1 (Minimal)             | Option 2 (Complete)                 | Option 3 (Split)                       |
| ------------------ | ------------------------------ | ----------------------------------- | -------------------------------------- |
| Development Effort | 1-2 days                       | 2-3 days                            | 4-5 days                               |
| UX Quality         | Partial -- bugs fixed, gaps remain | Full -- specialist handles all phases | Full -- same as Option 2               |
| Flexibility        | Low -- follow-up needed        | High -- complete lifecycle coverage  | High -- plus modular organization      |
| Risk               | Low                            | Medium (more code, but thin wrappers) | High (refactoring + new code combined) |
| Best For           | Emergency hotfix               | Standard iteration delivery         | Long-term codebase cleanup             |

---

## Recommendation

**I recommend Option 2 because:** it delivers complete alignment between the documented workflow and the specialist agent in a single iteration. The changes are confined to 3 files and consist entirely of thin wrapper functions following established patterns. The 3 bug fixes are critical (they allow agents to bypass workflow validation), and the 7 missing tools represent real capability gaps that would otherwise require human intervention for common operations like implementing an approved CO or checking pending approvals.

Option 1 leaves too many gaps for a follow-up iteration. Option 3 adds unnecessary refactoring risk without delivering additional user value -- the file split can be done later if the template grows unwieldy.

**Alternative consideration:** Choose Option 1 if there is an immediate production incident caused by the buggy tools and you need a same-day fix. The remaining work can be scheduled for the next iteration.

---

## Decision Questions

1. Should `analyze_change_order_impact` be refactored to call `ImpactAnalysisService.analyze_impact()`, or should it remain as-is and a separate `get_change_order_impact` tool be added alongside it? The refactored approach replaces a simplified inline calculation with the real service call but changes the existing tool's behavior.

2. Should `get_change_order_approval_info` be a single composite tool that internally calls multiple service methods, or should the agent be instructed to call `get_change_order` + `analyze_change_order_impact` separately and synthesize the info? A composite tool is more efficient but duplicates data fetching.

3. For the `recover_change_order` tool (admin recovery), should it use `CRITICAL` risk level (requiring EXPERT execution mode) or `HIGH` (allowing STANDARD mode with approval)? Recovery is an admin-only operation but may be needed urgently when workflows get stuck.

---

## References

- `docs/02-architecture/backend/contexts/change-order-workflow/architecture.md` -- Workflow state machine, validation rules, authority hierarchy
- `docs/05-user-guide/change-order-workflow-guide.md` -- Full workflow guide with entity model
- `docs/03-project-plan/iterations/2026-03-09-langgraph-agent-enhancement/phase-3c-ai-change-order-workflows.md` -- Previous AI tool implementation for change orders
- `backend/app/services/change_order_service.py` -- Service methods (submit_for_approval, approve_change_order, reject_change_order, merge_change_order, etc.)
- `backend/app/services/change_order_workflow_service.py` -- Standalone workflow service with state machine
- `backend/app/services/impact_analysis_service.py` -- Impact analysis service with analyze_impact method
- `backend/app/ai/tools/templates/change_order_template.py` -- Current 8 tools (3 buggy)
- `backend/app/ai/subagents/__init__.py` -- Specialist prompt and allowed_tools configuration
- `backend/app/ai/tools/__init__.py` -- Tool registration in create_project_tools()
- `backend/app/ai/tools/decorator.py` -- @ai_tool decorator pattern reference
