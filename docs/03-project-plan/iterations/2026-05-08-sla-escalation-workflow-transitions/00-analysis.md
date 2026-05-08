# Analysis: Phase B - SLA Escalation Rules + Configurable Workflow Transitions

**Created:** 2026-05-08
**Request:** Implement Phase B of the Configurable Change Order Workflow feature: (1) SLA Escalation Rules with escalation_trigger_pct activation and (2) Configurable Workflow Transitions moving hardcoded state machine rules into the database.

---

## Clarified Requirements

### Functional Requirements

**FR-1: SLA Escalation Status**
- Add `ESCALATED = "escalated"` to `SLAStatus` class (alongside PENDING, APPROACHING, OVERDUE)
- The `sla_status` column is `String(20)` -- "escalated" (10 chars) fits within the constraint
- Escalation is triggered when elapsed time exceeds `escalation_trigger_pct` of the total SLA duration
- The `escalation_trigger_pct` column already exists in `co_sla_rule_config` but no logic reads it yet

**FR-2: Escalation Service Methods**
- `check_escalation_eligible(change_order)` -- reads escalation_trigger_pct from config, compares elapsed vs total SLA time
- `get_escalatable_change_orders()` -- queries COs in "Submitted for Approval" or "Under Review" status where sla_status is not already "escalated" and elapsed time exceeds trigger threshold
- `escalate_change_order(change_order_id, actor_id)` -- sets sla_status to "escalated", creates audit log entry

**FR-3: SLA Status Calculation Update**
- `calculate_sla_status()` must return "escalated" when the CO is past the escalation trigger percentage but not yet overdue
- Status priority order: PENDING -> APPROACHING -> ESCALATED -> OVERDUE

**FR-4: Config Snapshot Enhancement**
- `generate_snapshot()` in ChangeOrderConfigService must include `escalation_trigger_pct` in the `sla_rules` section (currently omitted)

**FR-5: Escalation API Endpoint**
- `POST /api/v1/change-orders/{change_order_id}/escalate` -- manual escalation trigger
- RBAC: requires `change-order-escalate` permission (or reuse `change-order-approve` authority)

**FR-6: Frontend Escalated Badge**
- `getSLAStatusStyle()` in ApprovalInfo.tsx must handle "escalated" status with appropriate color (purple/warning)
- AgingItemsList.tsx and ChangeOrderStatsResponse may also need "escalated" handling

**FR-7: Configurable Workflow Transitions (Database)**
- Move hardcoded `_TRANSITIONS`, `_LOCK_TRANSITIONS`, `_UNLOCK_TRANSITIONS`, `_EDITABLE_STATUSES` from ChangeOrderWorkflowService into a `workflow_transitions` JSONB column on `co_workflow_config`
- Alembic migration adds column and seeds current hardcoded values as the default

**FR-8: Workflow Transitions Schema**
- New `WorkflowTransitionsSchema` Pydantic model with cross-validation:
  - transitions: dict mapping status -> list of allowed target statuses
  - lock_transitions: list of [from, to] pairs
  - unlock_transitions: list of [from, to] pairs
  - editable_statuses: list of status strings
  - Validation: all status strings in transitions keys/values must be consistent
  - Validation: lock/unlock pairs must reference valid transitions

**FR-9: Config Service Integration**
- `ChangeOrderConfigService` gets `get_workflow_transitions(project_id)` method
- CRUD operations (create/update) include the new `workflow_transitions` field
- Response schemas include the new field

**FR-10: Workflow Service Reads from Config**
- `ChangeOrderWorkflowService` reads transitions from config with fallback to hardcoded defaults
- Constructor accepts optional config_service or transitions dict
- All methods (`is_valid_transition`, `get_available_transitions`, `should_lock_on_transition`, `should_unlock_on_transition`, `can_edit_on_status`) use the loaded config
- `ChangeOrderService.__init__` wires config injection into `ChangeOrderWorkflowService`

**FR-11: Frontend Workflow Configuration Tab**
- Add "Workflow" tab (5th tab) to ChangeOrderConfigPage
- Editable transition graph: status dropdowns, allowed transitions table
- Lock/unlock transition pairs configuration
- Editable statuses list

### Non-Functional Requirements

- Backward compatible: existing COs with current hardcoded transitions continue to work
- No changes to EVCS versioning mechanics (ChangeOrder remains branchable entity)
- Migration must be reversible (downgrade drops the column)
- Performance: config reads cached per-request; no N+1 on workflow transitions
- MyPy strict mode, Ruff clean, 80%+ test coverage
- TypeScript strict, ESLint clean on frontend

### Constraints

- Phase A is complete; Phase B builds on top of existing config tables and service patterns
- The `escalation_trigger_pct` column exists but is nullable -- must handle NULL (no escalation configured)
- `ChangeOrderWorkflowService` is instantiated without arguments at line 60 of `change_order_service.py`
- Existing COs in production must not break when workflow transitions move to database
- All-or-nothing override model: project override replaces all global settings (including transitions)
- Fail loudly if no config exists (no silent fallback to hardcoded defaults in production)

---

## Context Discovery

### Product Scope

- Relevant user stories: Section 3.5 "Submitting the Change" and 3.6 "Accepting the Change" in `change-management-user-stories.md`
- The SLA escalation concept supports the approval workflow governance -- ensuring COs do not languish unattended
- Configurable transitions allow different organizations/projects to customize the workflow without code changes

### Architecture Context

- Bounded contexts involved: Change Management (primary), Configuration Management
- Existing patterns to follow:
  - Config pattern: `co_workflow_config` parent with child tables (`co_impact_level_config`, `co_approval_rule_config`, `co_sla_rule_config`)
  - All-or-nothing override: project config replaces entire global config
  - Optimistic locking with `version` column
  - Snapshot generation at CO submission time (immutable thereafter)
  - Audit log via `co_config_audit_log`
- Architectural constraints:
  - EVCS versioning must not be affected -- ChangeOrder is a Branchable entity
  - JSONB columns on config parent table (like `impact_weights` and `score_boundaries`) -- `workflow_transitions` follows same pattern
  - Simple entity base (non-versioned, non-branchable) for config records

### Codebase Analysis

**Backend:**

- `/backend/app/models/domain/change_order.py` -- `SLAStatus` class (PENDING, APPROACHING, OVERDUE). Column `sla_status: String(20)`.
- `/backend/app/models/domain/change_order_config.py` -- `ChangeOrderWorkflowConfig` parent with `impact_weights` and `score_boundaries` as JSONB columns. Pattern: JSONB on parent for structured config data. `ChangeOrderSLARuleConfig` has `escalation_trigger_pct: Numeric(5,2), nullable`.
- `/backend/app/services/change_order_workflow_service.py` -- Hardcoded `_TRANSITIONS`, `_LOCK_TRANSITIONS`, `_UNLOCK_TRANSITIONS`, `_EDITABLE_STATUSES`. Pure state machine with no DB dependency.
- `/backend/app/services/sla_service.py` -- `calculate_sla_status()` uses heuristic (< 1 business day = APPROACHING). `SLAService.__init__` accepts optional `config_service`.
- `/backend/app/services/change_order_config_service.py` -- `generate_snapshot()` omits `escalation_trigger_pct` from sla_rules section. No `get_workflow_transitions()` method.
- `/backend/app/services/change_order_service.py` -- Line 60: `self.workflow = ChangeOrderWorkflowService()` with no args. `ChangeOrderService.__init__` takes only `session`.
- `/backend/app/models/schemas/change_order_config.py` -- `WorkflowConfigUpdateRequest` and `WorkflowConfigResponse` schemas. No `workflow_transitions` field yet.
- `/backend/app/api/routes/change_order_config.py` -- PUT endpoints serialize/deserialize `WorkflowConfigUpdateRequest`. No workflow_transitions forwarding.
- `/backend/app/api/routes/change_orders.py` -- 18 endpoint functions. No escalation endpoint yet.

**Frontend:**

- `/frontend/src/features/change-orders/components/ChangeOrderConfigPage.tsx` -- 4 tabs: Impact Levels, Approval Rules, SLA Rules, Weights & Scores. Uses `useGlobalConfig` and `useUpdateGlobalConfig`.
- `/frontend/src/features/change-orders/components/ApprovalInfo.tsx` -- `getSLAStatusStyle()` maps "pending"/"approaching"/"overdue" to colors. No "escalated" entry.
- `/frontend/src/features/change-orders/api/useWorkflowConfig.ts` -- TypeScript types for `WorkflowConfigResponse` and `WorkflowConfigUpdateRequest`. No `workflow_transitions` field.
- `/frontend/src/api/generated/` -- Auto-generated OpenAPI types; will regenerate after backend changes.

---

## Solution Options

### Option 1: Incremental Enhancement (Minimal Refactor)

**Architecture & Design:**

Keep the current architecture largely unchanged. Add escalation as a new SLA status alongside the existing three. Move workflow transitions into the existing `co_workflow_config` table as a JSONB column, following the same pattern as `impact_weights` and `score_boundaries`. `ChangeOrderWorkflowService` accepts optional transitions at construction and falls back to hardcoded defaults only when no config is available (during migration bootstrapping).

**UX Design:**

- SLA status progression: PENDING -> APPROACHING -> ESCALATED -> OVERDUE, displayed as blue -> orange -> purple -> red badges
- Config page gets a 5th "Workflow" tab with a table-based editor (rows = source statuses, columns = allowed targets)
- Manual escalation via button in CO detail view (visible when SLA is approaching/eligible)

**Implementation:**

- Backend: ~15 files modified/created
  - Add ESCALATED to SLAStatus class
  - Add escalation methods to SLAService
  - Update calculate_sla_status() to use config-based trigger percentage
  - Add workflow_transitions JSONB column to ChangeOrderWorkflowConfig model
  - Create WorkflowTransitionsSchema Pydantic model
  - Add get_workflow_transitions() to ChangeOrderConfigService
  - Modify ChangeOrderWorkflowService constructor to accept optional transitions
  - Wire config injection in ChangeOrderService.__init__
  - Add POST /api/v1/change-orders/{change_order_id}/escalate route
  - Alembic migration with data seeding
  - Update generate_snapshot() to include escalation_trigger_pct
  - Update config API routes to forward workflow_transitions
- Frontend: ~5 files modified
  - Add "escalated" to getSLAStatusStyle()
  - Add WorkflowTab component to ChangeOrderConfigPage
  - Update useWorkflowConfig types and API calls
  - Add escalation button/mutation hook
- Tests: Service unit tests, API integration tests, frontend component tests

**Trade-offs:**

| Aspect          | Assessment                                                                   |
| --------------- | ---------------------------------------------------------------------------- |
| Pros            | Follows existing patterns exactly; minimal new abstractions; safe migration  |
| Cons            | JSONB column means no referential integrity on status strings; manual validation needed |
| Complexity      | Low-Medium                                                                   |
| Maintainability | Good -- consistent with existing impact_weights/score_boundaries pattern      |
| Performance     | Good -- JSONB loaded with config via selectin; no extra queries               |

---

### Option 2: Extracted Workflow Transitions Child Table

**Architecture & Design:**

Instead of storing workflow transitions as JSONB on the parent config, create a dedicated child table `co_workflow_transition_config` with one row per (from_status, to_status, is_lock_transition, is_unlock_transition, editable) -- similar to how `co_impact_level_config` is a child table of `co_workflow_config`. This provides full SQL queryability and referential integrity.

**UX Design:**

- Same as Option 1 for escalation features
- Config page "Workflow" tab shows transitions as a relational table with individual rows per transition, lock/unlock checkboxes, editable toggle
- More structured editing experience but potentially more complex UI for many-to-many status relationships

**Implementation:**

- Backend: ~18 files modified/created
  - All escalation work same as Option 1
  - New SQLAlchemy model: `ChangeOrderWorkflowTransitionConfig`
  - New migration: create child table with FK to parent, seed hardcoded values
  - New relationship on ChangeOrderWorkflowConfig (lazy="selectin")
  - New Pydantic schema for transition rows
  - ChangeOrderConfigService: load transitions from child rows, convert to dict format for workflow service
  - Update all CRUD operations to manage child rows (delete-recreate pattern like existing children)
  - Update snapshot generation to include transitions from child table
- Frontend: Same scope as Option 1

**Trade-offs:**

| Aspect          | Assessment                                                                   |
| --------------- | ---------------------------------------------------------------------------- |
| Pros            | Full referential integrity; SQL queryable; consistent with child table pattern |
| Cons            | Significantly more code for CRUD; over-engineered for a small config object (5-6 statuses, ~10 transitions); migration complexity |
| Complexity      | Medium-High                                                                  |
| Maintainability | Fair -- more moving parts, more schema/migration surface area                |
| Performance     | Good -- loaded via selectin, but extra table join and more rows              |

---

### Option 3: Hybrid -- JSONB Column with Dedicated Validation Layer

**Architecture & Design:**

Same as Option 1 (JSONB column on parent config) but with a dedicated `WorkflowTransitionValidator` class that provides schema validation, graph integrity checks (no orphan states, no cycles, terminal state detection), and a `to_workflow_service_format()` method. This separates the validation concern from both the config service and the workflow service.

**UX Design:**

- Same as Option 1
- Config page "Workflow" tab includes validation feedback (e.g., "Draft has no outgoing transitions", "Detected cycle: Approved -> Under Review -> Approved")

**Implementation:**

- Same file scope as Option 1 plus one new validator module
- `WorkflowTransitionValidator` class with:
  - `validate_schema(data)` -- structural validation (matching Pydantic model)
  - `validate_graph_integrity(transitions)` -- checks for orphans, cycles, terminal states
  - `to_service_format(config_transitions)` -- converts JSONB to the dict/set format ChangeOrderWorkflowService expects
- Integrated into config service create/update methods

**Trade-offs:**

| Aspect          | Assessment                                                                   |
| --------------- | ---------------------------------------------------------------------------- |
| Pros            | Strong validation; early error detection; clean separation of concerns       |
| Cons            | Slightly more code than Option 1; validator needs to stay in sync with schema |
| Complexity      | Medium                                                                       |
| Maintainability | Good -- validation logic isolated, testable independently                    |
| Performance     | Good -- validation at write time only, no runtime overhead                   |

---

## Comparison Summary

| Criteria           | Option 1: Incremental JSONB | Option 2: Child Table | Option 3: JSONB + Validator |
| ------------------ | --------------------------- | ---------------------- | --------------------------- |
| Development Effort | 3-4 days                    | 5-6 days              | 4-5 days                    |
| UX Quality         | Good                        | Good                  | Good                        |
| Flexibility        | Good                        | High                  | Good                        |
| Best For           | Shipping fast, consistency  | Complex query needs   | Safety-critical validation  |
| Migration Risk     | Low                         | Medium                | Low                         |
| Code Volume        | Low                         | High                  | Medium                      |

---

## Recommendation

**I recommend Option 1 (Incremental Enhancement with JSONB) because:**

1. It follows the exact same pattern already established by `impact_weights` and `score_boundaries` -- two JSONB columns on the parent config table that store structured configuration data. `workflow_transitions` is the same category of data.
2. The transition graph is small (5-6 statuses, ~10 transitions) and rarely queried independently -- JSONB is the right tool for this size.
3. The existing Pydantic cross-validation pattern (see `ImpactWeightsSchema.validate_weights_sum_to_one`, `ScoreBoundariesSchema.validate_boundaries_ascending`) is sufficient for integrity. A dedicated validator class (Option 3) adds marginal value for this data shape.
4. Lowest migration risk -- adding a nullable JSONB column with a seed default is the simplest possible migration.
5. The Phase A migration (`20260505_co_workflow_config_tables.py`) already seeds config data, so seeding workflow transitions follows the established precedent.

**Alternative consideration:** Choose Option 3 if the team anticipates complex transition graph validation requirements (e.g., mandatory exit transitions, time-based transition rules) in future phases. The validator layer would make those extensions cleaner.

---

## Decision Questions

1. Should escalation be a manual action only (button click), or also automatic (background job that periodically checks escalatable COs)? The request mentions `get_escalatable_change_orders()` which suggests a batch query pattern -- is a scheduler/cron integration expected in this phase?

2. What RBAC permission should govern the escalation endpoint? Options: (a) new `change-order-escalate` permission, (b) reuse `change-order-approve`, (c) require admin role. This affects the permission seed data.

3. For the Workflow tab frontend, should the transition graph be editable as (a) a simple table with status dropdown pairs, or (b) a visual node-edge graph editor? The table approach is simpler to implement and sufficient for 5-6 statuses.

4. Should the hardcoded defaults in `ChangeOrderWorkflowService` remain as the ultimate fallback (for bootstrapping before any config exists), or should the system refuse to operate without config? The request says "fail loudly if no config exists" but also "fallback to hardcoded defaults" -- these are contradictory.

---

## References

- Phase A migration: `/backend/alembic/versions/20260505_add_co_workflow_config_tables.py`
- Config domain model: `/backend/app/models/domain/change_order_config.py`
- Config service: `/backend/app/services/change_order_config_service.py`
- Workflow service: `/backend/app/services/change_order_workflow_service.py`
- SLA service: `/backend/app/services/sla_service.py`
- CO service (wiring point): `/backend/app/services/change_order_service.py` (line 60)
- Config API routes: `/backend/app/api/routes/change_order_config.py`
- Config Pydantic schemas: `/backend/app/models/schemas/change_order_config.py`
- Frontend config page: `/frontend/src/features/change-orders/components/ChangeOrderConfigPage.tsx`
- Frontend config hooks: `/frontend/src/features/change-orders/api/useWorkflowConfig.ts`
- Frontend SLA badge rendering: `/frontend/src/features/change-orders/components/ApprovalInfo.tsx`
- Change management user stories: `/docs/01-product-scope/change-management-user-stories.md`
