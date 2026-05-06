# Analysis: Configurable Change Order Workflow

**Created:** 2026-05-05
**Request:** Make the change order workflow configurable -- impact levels, financial thresholds, approval roles, SLA deadlines -- and propose additional configurable aspects based on PMI best practices for wider business applicability.

---

## Clarified Requirements

The user wants to replace hardcoded workflow parameters with a configurable system that allows administrators to adjust change order governance rules without code changes. Beyond the four explicitly mentioned items (impact levels, thresholds, roles, SLA), they want recommendations for what else should be configurable based on PMI and industry standards.

### Functional Requirements

- FR-1: Administrators can define and modify impact levels (currently hardcoded as LOW/MEDIUM/HIGH/CRITICAL)
- FR-2: Financial thresholds per impact level must be configurable (currently hardcoded in class constants)
- FR-3: Approval authority mapping (role-to-authority-level) must be configurable (currently hardcoded in dicts)
- FR-4: SLA deadlines per impact level must be configurable (currently hardcoded in multiple places with inconsistent values)
- FR-5: Configuration changes should take effect on new change orders without requiring application restart
- FR-6: Historical change orders retain the configuration values that were active at their time of submission

### Non-Functional Requirements

- NFR-1: Configuration UI accessible only to Admin role
- NFR-2: Audit trail for all configuration changes
- NFR-3: Zero downtime for configuration updates
- NFR-4: Performance: configuration lookups add < 5ms to workflow operations

### Constraints

- Must be backward compatible with existing change orders in the database
- Must not break the EVCS versioning architecture
- Configuration scope: system-wide (global) vs. project-specific to be decided
- Must align with existing patterns (e.g., `ProjectBudgetSettings` as a precedent)

---

## Context Discovery

### Product Scope

The change order workflow is a core governance feature in the Project Budget Management bounded context. The business guide (`docs/05-user-guide/change-order-business-guide.md`) documents the complete user-facing workflow including the hardcoded approval matrix and SLA rules.

### Architecture Context

**Bounded contexts involved:**
- Change Order Management (primary)
- User/Role Management (for approval authority)
- Project Management (for project-specific scoping)

**Existing patterns to follow:**
- `ProjectBudgetSettingsService` (`backend/app/services/project_budget_settings_service.py`) provides a proven precedent for per-project configuration using EVCS versioning
- `AIConfigService` (`backend/app/services/ai_config_service.py`) shows a database-driven configuration pattern with key-value storage
- The three specialized services (`FinancialImpactService`, `ApprovalMatrixService`, `SLAService`) already separate concerns well and each is the natural injection point for configuration lookups

### Codebase Analysis

#### Current State: What Is Hardcoded and Where

**1. Impact Level Constants** -- `backend/app/models/domain/change_order.py` lines 25-43

The `ImpactLevel` class defines four string constants (LOW, MEDIUM, HIGH, CRITICAL). These are referenced across 15+ files in both backend and frontend. Adding a fifth level (e.g., "MARGINAL") currently requires code changes in at least 10 files.

**2. Financial Thresholds** -- `backend/app/services/financial_impact_service.py` lines 39-42

```python
THRESHOLD_LOW_MAX = Decimal("10000")
THRESHOLD_MEDIUM_MAX = Decimal("50000")
THRESHOLD_HIGH_MAX = Decimal("100000")
```

Used in `_classify_impact_level()` for budget delta classification. Single location in backend but duplicated conceptually in the business guide documentation.

**3. Approval Authority Mapping** -- `backend/app/services/approval_matrix_service.py` lines 47-67

Three hardcoded dictionaries:
- `ROLE_AUTHORITY`: maps roles to authority levels (admin->CRITICAL, manager->HIGH, viewer->LOW)
- `IMPACT_AUTHORITY`: maps impact levels to required authority
- `AUTHORITY_HIERARCHY`: numeric ordering of authority levels

Notable gap: the mapping has only 3 roles (admin, manager, viewer) but the business guide references 5 roles (Viewer, Editor/PM, Department Head, Director, Admin). This is a pre-existing inconsistency that configurable settings would resolve.

**4. SLA Deadlines** -- Inconsistent across TWO locations

`sla_service.py` lines 38-43:
```python
SLA_BUSINESS_DAYS = {
    ImpactLevel.LOW: 2, ImpactLevel.MEDIUM: 5,
    ImpactLevel.HIGH: 10, ImpactLevel.CRITICAL: 15,
}
```

`change_order_service.py` lines 981-986 and 1775-1780 (duplicated):
```python
SLA_BUSINESS_DAYS = {
    "LOW": 3, "MEDIUM": 5, "HIGH": 7, "CRITICAL": 10,
}
```

These values DISAGREE. `SLAService` says LOW=2 days while `ChangeOrderService` says LOW=3 days. HIGH is 10 vs 7. This is a pre-existing bug that configurable settings would eliminate.

**5. Impact Score Thresholds** -- `backend/app/services/change_order_service.py` lines 1678-1706

`_map_score_to_impact_level()` uses hardcoded score boundaries:
- Score < 10: LOW
- Score 10-30: MEDIUM
- Score 30-50: HIGH
- Score >= 50: CRITICAL

These are separate from the financial thresholds and govern the weighted impact calculation.

**6. Workflow States** -- Frontend hardcoded in multiple files

`frontend/src/features/change-orders/components/WorkflowConstants.ts` defines 5 workflow steps. `useWorkflowActions.ts` defines 7 workflow actions with status strings. `ChangeOrderRecoveryDialog.tsx` hardcodes impact level options. `ApprovalInfo.tsx` hardcodes impact level colors and SLA status styles.

#### Backend Files Requiring Changes

| File | What Needs Changing |
|------|-------------------|
| `backend/app/services/financial_impact_service.py` | Replace class constants with config lookup |
| `backend/app/services/approval_matrix_service.py` | Replace hardcoded dicts with config lookup |
| `backend/app/services/sla_service.py` | Replace hardcoded SLA days with config lookup |
| `backend/app/services/change_order_service.py` | Remove duplicated SLA_BUSINESS_DAYS (2 locations), replace score thresholds with config |
| `backend/app/models/domain/change_order.py` | ImpactLevel class may become dynamic or reference config |
| New: `backend/app/services/change_order_config_service.py` | New service for configuration CRUD |
| New: `backend/app/models/domain/change_order_config.py` | New domain model for config storage |
| New: `backend/app/api/v1/change_order_config.py` | New API routes |
| New: Alembic migration | Create config table(s) |

#### Frontend Files Requiring Changes

| File | What Needs Changing |
|------|-------------------|
| `frontend/src/features/change-orders/components/WorkflowConstants.ts` | Load workflow steps from config or API |
| `frontend/src/features/change-orders/components/ApprovalInfo.tsx` | Dynamic impact level colors/labels |
| `frontend/src/features/change-orders/components/ChangeOrderRecoveryDialog.tsx` | Dynamic impact level options |
| `frontend/src/features/change-orders/components/ImpactLevelChart.tsx` | Dynamic color mapping |
| `frontend/src/features/change-orders/components/AgingItemsList.tsx` | Dynamic impact level colors |
| `frontend/src/features/change-orders/api/useCanApprove.ts` | Dynamic authority levels array |
| New: `frontend/src/features/change-orders/components/ChangeOrderConfigPage.tsx` | Admin configuration UI |

---

## PMI Best Practices Summary

### PMBOK Change Control Framework

The PMBOK Guide (6th and 7th editions) defines Perform Integrated Change Control as a systematic process. Key principles directly relevant to this feature:

1. **Change Control Board (CCB)**: PMBOK recommends a formally chartered group responsible for reviewing, evaluating, and approving/rejecting/deferring changes. The CCB's authority should be defined in the project charter and should vary by change magnitude. This aligns with configurable approval matrices where different impact levels route to different authorities.

2. **Tiered Authority**: PMI standards explicitly support tiered approval authority where minor changes require only project manager approval while major scope changes require full CCB or steering committee review. The current Backcast system implements this conceptually but hardcodes the tiers.

3. **Change Categories**: PMBOK recommends classifying changes by type (scope, schedule, cost, quality) not just financial impact. Configurable change categories would align with this principle.

4. **Impact Assessment Criteria**: PMBOK requires formal impact assessment considering schedule, cost, quality, and risk. The current weighted score calculation partially addresses this but the weights (budget 40%, schedule 30%, revenue 20%, EVM 10%) are hardcoded.

### Industry Standards from Enterprise Tools

Research into enterprise project management tools reveals common configurable aspects:

- **SAP Project System**: Configurable approval profiles with multi-level release strategies, amount-based thresholds, and role-dependent authorization
- **Oracle Primavera**: Change approval matrices with configurable risk categories, approval workflows, and escalation rules
- **MS Project Server**: Workflow stages configurable per project type, with customizable approval routing and notification rules

Key design patterns from industry research:

1. **Change Approval Matrix (CAM)**: A structured framework mapping change type + risk level + impact scope to approval authorities and required documentation. Multi-dimensional, not just financial threshold based.

2. **Escalation Policies**: Automated escalation when SLA deadlines approach or pass, with configurable escalation chains (e.g., notify backup approver at 75% of SLA time, escalate to next authority level at 100%).

3. **Conditional Routing**: Rules that consider multiple factors beyond financial impact -- project phase, contract type, client requirements, regulatory domain.

4. **Workflow States Pattern**: A database-driven approach using a single configuration table with JSON columns for transitions, permissions, and metadata. This pattern (documented in workflow states pattern literature) claims 60% reduction in development time when business teams can modify workflows.

### References

- [Change Approval Matrices for Enterprise Scheduling Success](https://www.myshyft.com/blog/change-approval-matrices/) -- myshyft.com
- [A Scalable Approval Matrix: Key Design Patterns and Best Practices](https://www.moxo.com/blog/scalable-approval-matrix-best-practices) -- moxo.com
- [PMBOK Guide 6th Edition - Perform Integrated Change Control](https://trainupinstitute.com/wp-content/uploads/2022/03/Project-Management-Institute-A-Guide-to-the-Project-Management-Body-of-Knowledge-PMBOK%C2%AE-Guide%E2%80%93Sixth-Edition-Project-Management-Institute-2017.pdf) -- PMI
- [The Ultimate Multifunctional Database Table Design: Workflow States Pattern](https://medium.com/@herihermawan/the-ultimate-multifunctional-database-table-design-workflow-states-pattern-156618996549) -- Medium
- [How Automated Escalation Rules Reduce Approval Bottlenecks](https://www.cflowapps.com/how-automated-escalation-rules-reduce-approval-bottlenecks/) -- cflowapps.com

---

## Recommended Additional Configurable Aspects

Based on PMI standards and industry research, the following aspects should also be configurable (beyond the four explicitly requested):

| Priority | Aspect | Rationale |
|----------|--------|-----------|
| **P0** | SLA escalation rules | PMI requires timely decisions; automated escalation prevents bottlenecks. Currently no escalation exists. |
| **P0** | Impact calculation weights | The current weighted score (budget 40%, schedule 30%, revenue 20%, EVM 10%) and score thresholds (<10=LOW, <30=MEDIUM, <50=HIGH, >=50=CRITICAL) are hardcoded. Different project types need different weighting. |
| **P1** | Workflow states and transitions | The 6-state workflow (Draft->Submitted->Under Review->Approved->Implemented + Rejected) should be configurable per project type. Some organizations need a "Deferred" state or parallel review states. |
| **P1** | Multi-level approval chains | Currently single-approver per impact level. PMI recommends CCB-style multi-person review for high-impact changes. Some changes should require 2+ approvals in sequence. |
| **P1** | Notification rules | Who gets notified at each workflow transition, with what urgency. Currently no notification system exists. |
| **P2** | Impact categories beyond financial | PMBOK recommends assessing schedule impact, quality impact, and risk impact separately. Currently only financial impact drives classification. |
| **P2** | Currency and locale for thresholds | Multi-currency projects need threshold conversion. Currently hardcoded in EUR. |
| **P2** | Emergency/fast-track approval paths | PMI standards require expedited paths for urgent changes with retroactive review. Currently no fast-track mechanism. |
| **P3** | Custom fields and metadata | Organization-specific data collection on change orders (e.g., client approval reference, contract clause). |
| **P3** | Holiday calendars for SLA calculation | The SLA service currently only excludes weekends. Holiday support was explicitly noted as a future enhancement in the code comments. |

---

## Solution Options

### Option 1: Single Configuration Table with JSONB (System-Wide)

**Architecture & Design:**

Create a single `change_order_workflow_config` table that stores the entire workflow configuration as a JSONB document. One active configuration record per project (or a global default). The configuration is loaded once on first access and cached for the request lifecycle.

Schema:
```
change_order_workflow_config
  - id (PK)
  - project_id (FK, nullable -- null = global default)
  - config_type (VARCHAR) -- "impact_levels", "sla_rules", "approval_matrix", "workflow_states", "escalation_rules"
  - config_value (JSONB)
  - is_active (BOOLEAN)
  - version (INTEGER) -- optimistic locking
  - created_by (FK to users)
  - created_at, updated_at (timestamps)
```

**UX Design:**

Admin settings page with tabbed sections: Impact Levels, Financial Thresholds, Approval Matrix, SLA Rules, Workflow States, Escalation. Each section is a form with "Save" and "Reset to Defaults" buttons. Changes require confirmation dialog.

**Implementation:**

- New `ChangeOrderWorkflowConfigService` reads from the config table, falls back to current hardcoded defaults for missing keys
- Each existing service (`FinancialImpactService`, `ApprovalMatrixService`, `SLAService`) receives the config service via dependency injection
- Frontend fetches active config on change order page load, caches in TanStack Query
- Alembic migration seeds the table with current hardcoded values as initial defaults

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Minimal schema changes (single table); follows JSONB pattern already used in the project (AI configs, dashboard layouts); easy to extend without migrations; simple caching strategy |
| Cons            | JSONB queries are less type-safe; no foreign key constraints within JSONB; harder to validate config integrity; JSONB indexes needed for performance |
| Complexity      | Low -- one new table, one new service, existing services modified to use config |
| Maintainability | Good -- new configurable aspects added by extending JSONB schema without DB changes |
| Performance     | Good -- single row lookup cached per request; JSONB access is fast in PostgreSQL |

---

### Option 2: Dedicated Relational Tables (Normalized)

**Architecture & Design:**

Create normalized tables for each configurable aspect with foreign keys and proper constraints. This is the "database purist" approach with full referential integrity.

Tables:
```
co_impact_level_config
  - id (PK), level_name, level_order, threshold_amount, currency, is_active

co_approval_authority_config
  - id (PK), role, authority_level, authority_rank

co_sla_config
  - id (PK), impact_level_id (FK), business_days, escalation_after_pct

co_workflow_state_config
  - id (PK), state_name, is_initial, is_final, allowed_transitions (JSONB)

co_workflow_transition_config
  - id (PK), from_state_id (FK), to_state_id (FK), required_role, required_authority_level
```

**UX Design:**

Same admin UI as Option 1, but backed by relational CRUD operations. More structured forms with dropdowns populated from foreign key relationships.

**Implementation:**

- New service per config table (or one aggregated service with typed methods)
- Each config service provides typed access methods (e.g., `get_thresholds() -> list[ImpactLevelConfig]`)
- Alembic migration creates tables and seeds from current hardcoded values
- Existing services modified to call config services instead of class constants
- EVCS versioning on config tables for audit trail

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Full type safety; referential integrity; easy to query and report on config; familiar relational patterns; Alembic can autogenerate migrations |
| Cons            | Many new tables and migrations; adding new configurable aspects requires schema migrations; more boilerplate code; potentially overkill for relatively static configuration |
| Complexity      | Medium -- multiple new tables, services, schemas, and API routes |
| Maintainability | Fair -- adding new aspects requires migrations, but each aspect is clearly separated |
| Performance     | Good -- standard relational queries, easy to index, no JSONB parsing overhead |

---

### Option 3: Hybrid Approach (Relational Core + JSONB Extensions)

**Architecture & Design:**

Use relational tables for the "core" configuration that has strong relational meaning (impact levels, approval authority, SLA rules) and JSONB for extension points (custom fields, notification rules, metadata). This balances type safety for the critical path with flexibility for auxiliary features.

Core relational tables:
```
co_workflow_config  (one row per project or global)
  - id (PK), project_id (FK, nullable), is_active, version, created_by, created_at, updated_at

co_impact_level  (child of co_workflow_config)
  - id (PK), config_id (FK), level_name, level_order, threshold_amount, score_threshold_min, score_threshold_max, is_active

co_approval_rule  (child of co_workflow_config)
  - id (PK), config_id (FK), impact_level_id (FK), required_authority_level, approver_role

co_sla_rule  (child of co_workflow_config)
  - id (PK), config_id (FK), impact_level_id (FK), business_days, escalation_trigger_pct
```

JSONB extensions on `co_workflow_config`:
```
  - workflow_states (JSONB) -- configurable state machine
  - notification_rules (JSONB) -- who gets notified when
  - custom_fields (JSONB) -- org-specific fields
  - metadata (JSONB) -- holiday calendar ref, currency, etc.
```

**UX Design:**

Admin settings page with a project selector (or "Global Default"). Configuration sections: Impact Levels (editable table), Approval Matrix (role x impact grid), SLA Rules (editable table), Workflow (visual state editor), Notifications (rule builder), Custom Fields (field builder). All changes are versioned.

**Implementation:**

- `ChangeOrderConfigService` manages the config tree, loads active config for a project with fallback to global
- Typed Pydantic schemas for the relational parts, dict/JSON for the flexible parts
- Each existing service gets config injected
- Frontend config page uses optimistic locking with version checks
- The `co_workflow_config` parent table provides a single versioning/audit point

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Type safety for critical paths; flexibility for extensions; single config tree makes versioning and audit easier; relational integrity for the approval matrix; can grow into project-specific configs naturally |
| Cons            | Moderate complexity; hybrid pattern requires discipline to decide what goes where; more tables than Option 1 but fewer than Option 2 |
| Complexity      | Medium -- balanced between Options 1 and 2 |
| Maintainability | Good -- clear separation of typed vs. flexible config; new aspects start as JSONB and graduate to relational if they prove stable |
| Performance     | Good -- relational joins for core lookups (fast), JSONB for infrequently accessed extensions |

---

## Comparison Summary

| Criteria           | Option 1 (JSONB) | Option 2 (Normalized) | Option 3 (Hybrid) |
| ------------------ | ---------------- | --------------------- | ----------------- |
| Development Effort | Low (3-5 days)   | Medium-High (7-10 days) | Medium (5-7 days) |
| Type Safety        | Poor             | Excellent              | Good              |
| Flexibility        | Excellent        | Fair                   | Good              |
| Audit Trail        | Basic            | Full EVCS versioning   | Full EVCS versioning |
| Best For           | Quick iteration, prototyping | Strict governance, regulatory compliance | Production-ready with growth path |
| Data Integrity     | Low              | High                   | Medium-High       |
| Migration Pain     | Minimal          | Significant            | Moderate          |

---

## Recommendation

**I recommend Option 3 (Hybrid Approach) because:** it provides the right balance of type safety for the critical approval matrix and financial thresholds (where wrong values cause real business harm) while maintaining JSONB flexibility for emergent configurable aspects like notification rules and custom fields. The parent `co_workflow_config` table naturally supports project-specific overrides (by setting `project_id`) while maintaining a global default (when `project_id` is null). This aligns with the existing `ProjectBudgetSettingsService` pattern and the PMI principle that "CCB authority varies by change magnitude and project context."

**Alternative consideration:** Choose Option 1 if the priority is speed of delivery and the team accepts the risk of JSONB configuration errors. This would be appropriate for an MVP or internal tool where a configuration mistake is easily corrected. Choose Option 2 if the system must comply with regulatory frameworks (e.g., government contracts, aerospace) that require full audit trails with typed, validated configuration records.

---

## Decisions

1. **Configuration scope: Per-project overrides.** Global defaults apply to all projects, but each project can override any setting. Follows existing `ProjectBudgetSettingsService` pattern. Admin manages global defaults; project-level admins manage per-project overrides.

2. **SLA defaults: Fully configurable with admin-defined seeds.** The admin sets the default SLA values during initial configuration (no hardcoded seed). Per-project overrides allow different SLA policies. The existing inconsistency between `SLAService` and `ChangeOrderService` is eliminated — both read from the same config source.

3. **Role system: Expand to full 5-role system.** The configurable approval matrix will support Viewer, Editor/PM, Department Head, Director, and Admin — aligning with the business guide and PMI tiered authority. The current 3-role mapping in `ApprovalMatrixService` is a pre-existing gap that this feature resolves.

4. **Phasing: Phased delivery across three iterations.**
   - **Phase A (core):** Impact levels, financial thresholds, SLA rules, approval authority matrix. Config storage, admin API, frontend config page.
   - **Phase B (governance):** Impact calculation weights, SLA escalation rules, workflow states/transitions configuration.
   - **Phase C (auxiliary):** Notification rules, custom fields, holiday calendars, multi-currency thresholds.

5. **Impact levels: Fixed 4 levels with configurable parameters.** The 4 levels (LOW/MEDIUM/HIGH/CRITICAL) are fixed in the system — admins configure thresholds, SLA deadlines, and approval authority per level, but cannot add or remove levels. This keeps the frontend predictable (colors, badges, charts all map to 4 known levels) while allowing full parameter customization.

6. **Per-project override permission: Dedicated RBAC permission.** Create a specific permission (e.g., `change-order-workflow-config:override`) for per-project configuration overrides. Assigned to Admin role by default in seeding. Admin owns global config; the override permission controls who can customize per-project. This prevents PMs from loosening governance rules on their own projects unless explicitly authorized.

7. **Historical integrity: Snapshot at submission.** When a change order transitions from Draft to Submitted for Approval, the active configuration (thresholds, SLA, approval matrix) is snapshotted onto the CO record. Future config changes do not affect in-flight or historical change orders. This preserves audit trail and legal traceability.

8. **Approval model: Single approver per level.** Phase A keeps the current model where one role approves each impact level. Multi-approver chains are deferred — the architecture should not prevent adding them in Phase B, but Phase A ships with single-approver simplicity.

9. **Admin UI placement: Split between global admin and project settings.** Global config lives under a global admin settings area. Per-project config lives under each project's settings tab with a "Use Global Defaults" toggle. When toggled off, override sections appear for editing. This separates system-wide governance from project-specific customization.

10. **New project behavior: Lazy inheritance.** New projects auto-inherit global defaults with no per-project config record. A config record is only created when someone with the override permission explicitly toggles off "Use Global Defaults" in project settings. Zero setup friction for standard projects.

11. **Currency: Single currency per project.** Thresholds are stored in the project's currency. The config stores the currency code alongside threshold values. No conversion logic — admin sets values in the project's own currency. Multi-currency conversion deferred to Phase C.

12. **Revert to defaults: Supported with reset button.** Project settings page includes a "Reset to Global Defaults" button that deletes the per-project config record. The project immediately falls back to global defaults. Clean, reversible override model.

13. **Config snapshot storage: JSONB column on change_orders.** A `config_snapshot` JSONB column is added to the change_orders table, written once at submission and immutable thereafter. Co-loaded with the CO — no joins needed. Contains impact levels, thresholds, SLA rules, and approval matrix as they were at submission time.

14. **Impact score weights: Configurable in Phase A.** The impact calculation weights (budget 40%, schedule 30%, revenue 20%, EVM 10%) and score boundaries (<10=LOW, <30=MEDIUM, <50=HIGH, >=50=CRITICAL) are included in Phase A scope. Admins can tune how impact is calculated, not just the thresholds.

15. **Config audit: Simple audit log.** Config tables have `updated_at` and `updated_by` columns. A separate `co_config_audit_log` table records every change with `old_values` and `new_values` as JSONB. No EVCS versioning on config — lighter than full temporal tracking but still answers "who changed what and when."

16. **Config export/import: Deferred.** Phase A is CRUD only. Export/import of config between projects deferred to a later phase.

17. **Override mode: All-or-nothing.** When a project overrides global config, it must override all sections at once (thresholds, approval matrix, SLA rules, score weights). No mixing of global and per-project sections. Simpler fallback logic — if per-project config exists, use it entirely; otherwise use global.

18. **Safety net: Fail loudly if config missing.** No hardcoded fallback values in the service layer. If no config record exists, operations fail with a clear error directing admin to configure. Eliminates the risk of silent fallback to outdated hardcoded values. The Alembic migration must seed the global config to prevent this on fresh installs.

19. **Existing COs migration: Leave null, use current config for display.** Historical change orders keep `config_snapshot` as null. When displaying COs without a snapshot, the UI reads from the current global config. Acceptable inaccuracy for terminal-state COs. No backfill script needed.

20. **Concurrency: Optimistic locking with version column.** The config table includes a `version` integer column. On update, the service checks that version hasn't changed since the admin fetched the config. If it has, the update is rejected with a conflict error and the admin must re-fetch. Prevents silent overwrites from concurrent edits.

---

## References

- `backend/app/services/financial_impact_service.py` -- hardcoded financial thresholds
- `backend/app/services/approval_matrix_service.py` -- hardcoded approval authority mapping
- `backend/app/services/sla_service.py` -- hardcoded SLA deadlines (version A)
- `backend/app/services/change_order_service.py` -- duplicated SLA deadlines (version B, inconsistent)
- `backend/app/services/project_budget_settings_service.py` -- precedent for per-project configuration
- `backend/app/models/domain/change_order.py` -- ImpactLevel and SLAStatus constants
- `frontend/src/features/change-orders/components/WorkflowConstants.ts` -- hardcoded workflow steps
- `frontend/src/features/change-orders/components/ApprovalInfo.tsx` -- hardcoded impact level colors
- `docs/05-user-guide/change-order-business-guide.md` -- user-facing workflow documentation
- [Change Approval Matrices for Enterprise Scheduling Success](https://www.myshyft.com/blog/change-approval-matrices/)
- [A Scalable Approval Matrix: Key Design Patterns and Best Practices](https://www.moxo.com/blog/scalable-approval-matrix-best-practices)
- [Workflow States Pattern](https://medium.com/@herihermawan/the-ultimate-multifunctional-database-table-design-workflow-states-pattern-156618996549)
- [How Automated Escalation Rules Reduce Approval Bottlenecks](https://www.cflowapps.com/how-automated-escalation-rules-reduce-approval-bottlenecks/)
