# Analysis: Configurable Change Order Workflow -- Phase C (Auxiliary Features)

**Created:** 2026-05-09
**Request:** Analyze and plan Phase C of the Configurable Change Order Workflow feature, covering auxiliary features: notification rules, custom fields, holiday calendars, multi-currency thresholds, multi-level approval chains, emergency/fast-track paths, and impact categories beyond financial.

---

## Clarified Requirements

Phase C delivers the remaining configurable aspects from the Phase A analysis "Recommended Additional Configurable Aspects" table. Phases A (core config) and B (governance) are complete. The system now has configurable impact levels, financial thresholds, approval rules, SLA rules, impact weights, score boundaries, and workflow transitions -- all managed through a hybrid relational+JSONB config architecture.

Phase C candidates vary significantly in complexity and business value. This analysis evaluates each candidate, identifies dependencies, and proposes a realistic scope for a single iteration.

### Functional Requirements (Candidate Features)

- FR-C1: Notification rules -- define who gets notified at each workflow transition, with configurable urgency/channels
- FR-C2: Multi-level approval chains -- require 2+ approvals in sequence for high-impact changes (CCB-style review)
- FR-C3: Holiday calendars for SLA calculation -- exclude holidays from business-day counting
- FR-C4: Custom fields and metadata -- organization-specific data collection on change orders
- FR-C5: Emergency/fast-track approval paths -- expedited workflow for urgent changes with retroactive review
- FR-C6: Multi-currency thresholds -- threshold conversion for multi-currency projects
- FR-C7: Impact categories beyond financial -- schedule, quality, and risk impact assessment

### Non-Functional Requirements

- NFR-C1: All new config follows the existing hybrid pattern (relational core + JSONB extensions)
- NFR-C2: New config sections integrate into the existing `ChangeOrderConfigPage` tabs
- NFR-C3: Config snapshots at submission include all new config sections
- NFR-C4: All new features are per-project configurable with global defaults
- NFR-C5: Existing services (`SLAService`, `ApprovalMatrixService`, etc.) remain backward-compatible

### Constraints

- Must extend, not replace, the existing config architecture from Phases A/B
- Must not require breaking changes to existing API contracts
- Must follow the all-or-nothing override model (Decision #17)
- Fixed 4 impact levels remain (Decision #5)
- Single currency per project (Decision #11)

---

## Context Discovery

### Product Scope

The change order workflow is a core governance feature. Phase A established the config foundation. Phase B added escalation and workflow transitions. Phase C targets the remaining gaps identified through PMI standards analysis and the Phase B completion review.

### Architecture Context

**Existing config architecture (Phases A/B):**
- `co_workflow_config` parent table (SimpleEntityBase) with `project_id` nullable
- Three child relational tables: `co_impact_level_config`, `co_approval_rule_config`, `co_sla_rule_config`
- JSONB columns on parent: `impact_weights`, `score_boundaries`, `workflow_transitions`
- `ChangeOrderConfigService` manages CRUD with optimistic locking
- `generate_snapshot()` creates immutable JSONB snapshot at CO submission
- Config audit via `co_config_audit_log`
- Frontend `ChangeOrderConfigPage` with 5 tabs

**Existing notification infrastructure:**
- `app/core/notifications/` -- Telegram-based fire-and-forget notification system
- `TelegramNotifier` singleton with `NotificationEvent` enum (3 events: SYSTEM_STARTUP, UNHANDLED_EXCEPTION, USER_LOGIN)
- `NotificationPayload` with event, message, details fields
- `send_fire_and_forget()` for non-blocking notification dispatch
- Currently admin-only (single Telegram channel), no per-user targeting

**Services consuming config:**
- `FinancialImpactService` -- reads thresholds via `ChangeOrderConfigService.get_thresholds()`
- `ApprovalMatrixService` -- reads approval rules via `get_role_authority_mapping()`, `get_impact_authority_mapping()`
- `SLAService` -- reads SLA days via `get_sla_days()`, escalation via `get_escalation_triggers()`
- `ChangeOrderWorkflowService` -- reads transitions via `get_workflow_transitions()`
- `ChangeOrderService` -- reads score boundaries, impact weights

### Codebase Analysis

**Backend files relevant to Phase C:**

| File | Relevance |
|------|-----------|
| `backend/app/core/notifications/_types.py` | Notification event enum to extend |
| `backend/app/core/notifications/_telegram.py` | Telegram notifier to keep or generalize |
| `backend/app/services/sla_service.py` | `_is_business_day()` needs holiday awareness |
| `backend/app/services/approval_matrix_service.py` | Currently single-approver; multi-approver chains here |
| `backend/app/services/change_order_workflow_service.py` | Fast-track paths need workflow modification |
| `backend/app/services/change_order_service.py` | Custom fields storage on CO entity |
| `backend/app/models/domain/change_order.py` | `config_snapshot` JSONB already supports extension |
| `backend/app/models/domain/change_order_config.py` | Parent config model to extend with JSONB columns |
| `backend/app/models/schemas/change_order_config.py` | Schemas to extend for new config sections |
| `backend/app/services/change_order_config_service.py` | Central config service to add new config readers |
| `backend/app/api/routes/change_order_config.py` | API routes may need new endpoints |

**Frontend files relevant to Phase C:**

| File | Relevance |
|------|-----------|
| `frontend/src/features/change-orders/components/ChangeOrderConfigPage.tsx` | Add new tabs |
| `frontend/src/features/change-orders/api/useWorkflowConfig.ts` | Extend types and hooks |

**Key technical observations:**

1. The notification system is Telegram-only, fire-and-forget, admin-channel-only. Extending it to support per-user, per-event, configurable notification rules is a significant architectural change.
2. The SLA service's `_is_business_day()` has an explicit comment: "Holidays are not yet supported. Can be added by checking against a holiday calendar table in future iterations." This is the lowest-hanging fruit.
3. The approval matrix service currently returns a single approver via `get_approver_for_impact()`. Multi-level chains require a new concept of approval sequences.
4. The CO entity already has a `config_snapshot` JSONB column that captures all config at submission time -- new config sections are naturally included without schema changes to `change_orders`.
5. The `co_workflow_config` JSONB columns (`impact_weights`, `score_boundaries`, `workflow_transitions`) demonstrate the established pattern for adding new config sections: add a new JSONB column for structured config, create a Pydantic schema for validation, add reader methods to `ChangeOrderConfigService`.

---

## Feature-by-Feature Analysis

### F1: Holiday Calendars for SLA Calculation

**Business value:** HIGH -- SLA deadlines are currently inaccurate when they span public holidays. The code has an explicit TODO comment acknowledging this gap. Directly affects SLA compliance tracking and escalation accuracy.

**Complexity:** LOW -- uses Python `holidays` library with country code stored in config. No holiday table needed, no admin UI for managing individual holidays.

**Dependencies:** None. Fully independent.

**Implementation sketch:**
- Add `holidays` Python package to project dependencies
- Add `holiday_country_code` field to config (stored as JSONB key on `co_workflow_config` or new column)
- Modify `SLAService._is_business_day()` to accept country code and check `holidays` library
- Config page gets a "Country" dropdown in SLA Rules tab for holiday calendar selection
- Default country code seeded in migration (e.g., "IT")

**Estimated effort:** 1-2 days

---

### F2: Custom Fields and Metadata

**Business value:** MEDIUM -- organizations have unique data requirements. However, this is a "nice to have" not a "must have" for the workflow engine itself. The CO entity already supports `description` and `justification` as free-text fields.

**Complexity:** MEDIUM -- requires a custom field definition schema, storage on the CO entity, dynamic form rendering in the frontend, and validation logic.

**Dependencies:** None. Independent.

**Implementation sketch:**
- JSONB column `custom_fields` on `co_workflow_config` defining available custom fields (name, type, required, options)
- JSONB column `custom_field_values` on `change_orders` for per-CO custom data
- Schema validation using the field definitions from config
- Frontend dynamic form fields on CO create/edit pages
- Config page tab for defining custom field schemas

**Estimated effort:** 3-4 days

**DECISION: Simple fields only (no conditional visibility).** Fields always visible on all COs. Supports name, type (text, number, date, select), required flag, options for select types. Reduces effort to ~2-3 days.

---

### F3: Notification Rules

**Business value:** HIGH -- currently no one is notified when a change order transitions states, is assigned for approval, or escalates. Approvers must manually check the dashboard. This is a significant usability gap.

**Complexity:** HIGH -- the existing notification system is Telegram-only and admin-channel-only. Extending to per-user, per-event, configurable rules requires:
- A new `notification_rules` config section (JSONB on config, or separate table)
- Per-user notification preferences (in-app, email, Telegram)
- An in-app notification center (new UI component) or email integration
- Integration with the workflow service to emit events on state transitions
- Background task processing for notification dispatch

**Dependencies:** May need a notification event bus or observer pattern on workflow transitions.

**Implementation sketch:**
- Add `notification_rules` JSONB column to `co_workflow_config`
- Define rule schema: `{trigger: "status_transition", from_status: "Draft", to_status: "Submitted for Approval", recipients: ["approver", "submitter", "role:dept_head"], channel: "in_app"}`
- Extend `NotificationEvent` enum with CO workflow events
- Add `NotificationRule` service to evaluate rules and dispatch
- In-app notification storage table for notification history
- Frontend notification bell component and notification list

**Estimated effort:** 5-7 days (full notification system) or 2-3 days (extend existing Telegram-only system with configurable rules)

**DECISION: Per-user in-app notification center.** Build notification center with bell icon, notification list, read/unread tracking. Per-user targeting. New DB table for notifications. ~4-5 days effort.

---

### F4: Multi-Level Approval Chains

**Business value:** MEDIUM-HIGH -- PMI recommends CCB-style multi-person review for high-impact changes. Currently only one approver is assigned per CO. However, this is an advanced governance feature that most organizations can live without initially.

**Complexity:** HIGH -- requires:
- A new concept of "approval steps" or "approval chain" (ordered sequence of required approvals)
- Modification to `ApprovalMatrixService` to support chain-based approval
- `ChangeOrder` entity needs to track multi-approver state (currently `assigned_approver_id` is single)
- `ChangeOrderWorkflowService.approve_change_order()` needs to advance through chain steps
- New state management for partial approvals
- Frontend changes to display approval chain progress

**Dependencies:** Modifies core approval flow. Risk of regression if not carefully implemented.

**Implementation sketch:**
- Add `approval_chain` JSONB column to `co_workflow_config` defining ordered approval steps per impact level
- Example: `{"CRITICAL": [{"step": 1, "role": "dept_head", "authority": "HIGH"}, {"step": 2, "role": "director", "authority": "CRITICAL"}]}`
- Add `approval_chain_progress` JSONB column to `change_orders` tracking completed steps
- Modify `approve_change_order()` to check if all chain steps are complete before final approval
- Introduce "Partially Approved" intermediate status or track progress within "Under Review"

**Estimated effort:** 4-5 days

---

### F5: Emergency/Fast-Track Paths

**Business value:** MEDIUM -- PMI standards require expedited paths for urgent changes. However, the current system is used for end-of-line automation projects where all changes are significant. Fast-track is an edge case.

**Complexity:** MEDIUM -- requires:
- A new "fast-track" flag on change orders
- Modified SLA rules for fast-track (shorter deadlines)
- Modified approval rules (potentially single-approver even for high-impact)
- Modified workflow transitions (skip "Under Review" step)
- New UI for marking a CO as emergency and the retroactive review flow

**Dependencies:** Builds on workflow transitions config (Phase B). May conflict with approval chains if both are implemented.

**Estimated effort:** 3-4 days

---

### F6: Multi-Currency Thresholds

**Business value:** LOW -- Decision #11 from Phase A explicitly deferred multi-currency to Phase C. However, the system currently operates in EUR for all projects. The complexity of currency conversion (live rates, historical rates, rate tables) is significant for a feature with uncertain demand.

**Complexity:** HIGH -- requires currency conversion service, rate storage, threshold conversion at comparison time, and handling of rate fluctuations.

**Dependencies:** None technically, but high complexity for uncertain value.

**Estimated effort:** 5-7 days

---

### F7: Impact Categories Beyond Financial

**Business value:** MEDIUM -- PMBOK recommends assessing schedule, quality, and risk impact separately. Currently only financial impact drives classification. This would improve the weighted score calculation.

**Complexity:** MEDIUM-HIGH -- requires:
- New impact assessment dimensions (schedule, quality, risk)
- Data collection for each dimension (currently only financial data is auto-calculated)
- New config section for dimension weights (extends existing `impact_weights` JSONB)
- Potentially manual input fields for non-financial dimensions
- Modified impact score calculation algorithm

**Dependencies:** Extends the impact scoring system from Phase A. Requires careful design to not break existing score calculations.

**Estimated effort:** 4-5 days

---

## Solution Options

### Option 1: Focused Scope -- Holiday Calendars + Notification Rules (Telegram-extended)

**Architecture & Design:**

Deliver two features that provide the highest business value with the lowest complexity:

1. **Holiday calendars** as a new JSONB column on `co_workflow_config`, with admin UI for managing holidays per-project or globally. Modification to `SLAService._is_business_day()`.

2. **Notification rules** extending the existing Telegram notification system with configurable rules stored as JSONB on `co_workflow_config`. Rules define which events trigger notifications to the admin Telegram channel. This is an incremental extension, not a full notification system overhaul.

**UX Design:**

- Holiday Calendar tab on `ChangeOrderConfigPage`: table of holiday dates with add/remove/import. Country/year selector for bulk import of common holidays.
- Notification Rules tab: table of rules with trigger (status transition), recipient scope (admin channel), and enable/disable toggle.

**Implementation:**

- New JSONB columns: `holiday_calendar` and `notification_rules` on `co_workflow_config`
- New Pydantic schemas: `HolidayCalendarSchema`, `NotificationRuleSchema`
- Extend `ChangeOrderConfigService` with readers for both
- Modify `SLAService._is_business_day()` to accept holiday list parameter
- Extend `NotificationEvent` enum with CO workflow events (SUBMITTED, APPROVED, REJECTED, ESCALATED, IMPLEMENTED)
- Add `notifier.send_fire_and_forget()` calls in `ChangeOrderWorkflowService` at transition points
- Extend `generate_snapshot()` to include both new config sections
- New Alembic migration for JSONB columns
- Frontend new tabs on config page

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Delivers two high-value features; holiday calendar has explicit code TODO; notification rules leverage existing infrastructure; minimal schema changes (JSONB columns); both features are independent |
| Cons            | Notification rules are Telegram-only (no per-user targeting); no in-app notification center; holiday import is manual |
| Complexity      | Low-Medium |
| Maintainability | Good -- follows established JSONB-on-config pattern |
| Performance     | Good -- holiday lookup is a simple date comparison; notification is fire-and-forget |

---

### Option 2: Broader Scope -- Holiday Calendars + Custom Fields + Notification Rules (Telegram-extended)

**Architecture & Design:**

Deliver three features: holiday calendars, custom fields, and notification rules. This addresses the three most commonly requested configurable aspects.

Custom fields allow organizations to add domain-specific metadata to change orders (e.g., "Client Approval Reference", "Contract Clause", "Safety Impact Assessment"). Field definitions are stored as JSONB on the config, and per-CO values are stored in a new `custom_field_values` JSONB column on `change_orders`.

**UX Design:**

- Holiday Calendar tab (same as Option 1)
- Notification Rules tab (same as Option 1)
- Custom Fields tab: field builder with name, type (text, number, date, select), required flag, and option list for select types. Preview of how fields appear on the CO form.

**Implementation:**

Everything from Option 1, plus:
- New JSONB column `custom_fields` on `co_workflow_config` for field definitions
- New JSONB column `custom_field_values` on `change_orders` for per-CO data
- `CustomFieldService` for validation of custom field values against definitions
- Extend `ChangeOrderCreate` and `ChangeOrderUpdate` schemas with optional `custom_field_values`
- Frontend dynamic form rendering on CO create/edit pages based on active field definitions
- Config snapshot includes custom field definitions
- Custom field values are versioned with the CO (part of EVCS versioning)

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Addresses three high-value gaps; custom fields enable organization-specific workflows; all features are independent; follows established patterns |
| Cons            | Higher scope increases iteration risk; custom field dynamic rendering adds frontend complexity; more testing surface |
| Complexity      | Medium |
| Maintainability | Good -- each feature is isolated in its own config section |
| Performance     | Good -- JSONB lookups are fast; custom field validation is lightweight |

---

### Option 3: Maximum Scope -- All P1/P2 Features (Holiday Calendars + Notification Rules + Custom Fields + Multi-Level Approval Chains)

**Architecture & Design:**

Deliver four features including multi-level approval chains. This is the most ambitious option and addresses the PMI CCB recommendation.

Multi-level approval chains introduce the concept of sequential approval steps. For CRITICAL and HIGH impact levels, the config can define multiple approval steps. The CO tracks which steps have been completed.

**UX Design:**

- Holiday Calendar tab (same as Option 1)
- Notification Rules tab (same as Option 1)
- Custom Fields tab (same as Option 2)
- Approval Chains tab: ordered list of approval steps per impact level. Each step defines the required role/authority. Drag-to-reorder steps. "Single Approver" toggle for levels that do not need chain approval.

**Implementation:**

Everything from Option 2, plus:
- New JSONB column `approval_chains` on `co_workflow_config`
- New JSONB column `approval_chain_progress` on `change_orders`
- Modify `ApprovalMatrixService.get_approver_for_impact()` to return the first uncompleted step
- Modify `ChangeOrderWorkflowService.approve_change_order()` to advance chain progress
- Introduce logic: if all chain steps complete, transition to "Approved"; otherwise, assign next approver and stay in "Under Review"
- Frontend approval chain progress indicator on CO detail page
- Audit log entries for each chain step approval

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Addresses all P1 features; CCB-style approval is PMI best practice; most complete governance story |
| Cons            | Highest complexity and risk; multi-level approval modifies core workflow (regression risk); approval chain + fast-track interaction is complex; may not fit in single iteration |
| Complexity      | High |
| Maintainability | Fair -- approval chains interact with multiple services and affect core workflow flow |
| Performance     | Good -- chain lookups are small JSONB reads |

---

## Comparison Summary

| Criteria           | Option 1 (Focused) | Option 2 (Broader) | Option 3 (Maximum) |
| ------------------ | ------------------- | ------------------- | ------------------- |
| Development Effort | 4-5 days            | 7-9 days            | 12-15 days          |
| Business Value     | Medium              | High                | Very High           |
| Risk               | Low                 | Medium              | High                |
| Iteration Fit      | Comfortable         | Tight but feasible  | Too large for one iteration |
| Testability        | Easy                | Moderate            | Complex             |
| Regression Risk    | Minimal             | Low                 | Significant (approval flow) |
| Best For           | Safe, high-ROI delivery | Balanced scope | Full PMI compliance |

---

## Recommendation

**I recommend Option 2 (Broader Scope: Holiday Calendars + Custom Fields + Notification Rules) because:**

1. **Holiday calendars** are the lowest-hanging fruit with explicit code comments requesting them, and they directly fix SLA accuracy.

2. **Notification rules** (in-app notification center) address the most painful usability gap -- approvers currently have no way to know when a CO is assigned to them without manually checking the dashboard. Building per-user in-app notifications with a bell icon and notification list provides significantly better UX than Telegram-only alerts.

3. **Custom fields** (simple, no conditional visibility) enable organization-specific data collection without schema changes, which is a frequently requested feature in project management tools and makes the workflow genuinely configurable.

4. **Multi-level approval chains (excluded)** are valuable but carry significant regression risk to the core approval flow. They should be a separate dedicated iteration to allow thorough testing. This feature modifies `approve_change_order()`, `reject_change_order()`, and `get_approver_for_impact()` -- the most critical code paths in the workflow. Rushing it into a multi-feature iteration increases the risk of shipping a broken approval flow.

5. The three selected features are fully independent of each other, enabling parallel development and isolated testing. If time runs short, any one can be dropped without affecting the others.

**Alternative consideration:** Choose Option 1 if the iteration timeline is shorter than 7 days, or if the team wants to ship quickly and gather user feedback before building custom fields. Choose Option 3 only if there is explicit business demand for multi-approver chains and the iteration can be extended to 3 weeks.

**Deferred to future iterations:**
- Multi-level approval chains (Option 3 component) -- dedicated iteration recommended
- Emergency/fast-track paths -- depends on approval chains being implemented first
- Multi-currency thresholds -- low business value, high complexity
- Impact categories beyond financial -- requires design of new data collection and scoring dimensions

---

## Decisions

1. **Notification scope: Per-user in-app notification center.** Build a notification center with in-app bell icon, notification list, and read/unread tracking. This provides per-user targeting and is significantly more useful for approvers than Telegram-only alerts. Adds ~3-4 days of effort over Telegram-only approach. Requires new DB table for notification storage and new frontend components.

2. **Custom fields: Simple fields only.** No conditional visibility. Custom fields are always visible on all COs regardless of impact level or status. Field definitions support: name, type (text, number, date, select), required flag, and option list for select types. Keeps implementation clean and predictable. Conditional visibility can be added in a future iteration if needed.

3. **Holiday calendar source: Python `holidays` library.** Use the `holidays` Python package with a configurable `country_code` stored in the config. Zero admin maintenance, supports 150+ countries, always up-to-date. Country code stored as a new `holiday_country_code` field on the config (string, e.g., "IT", "DE", "US"). No database holiday table needed. No admin UI for managing individual holidays.

4. **Feature priority: Holidays > Notifications > Custom Fields.** Holiday calendars fix SLA accuracy (explicit TODO in code) and are lowest effort. In-app notifications address the biggest usability gap (approvers don't know about assignments). Custom fields are the first feature to drop if time runs short.

5. **Multi-level approval chains: Deferred to dedicated iteration.** Approval chains carry significant regression risk to the core approval flow (`approve_change_order()`, `get_approver_for_impact()`, `assigned_approver_id`). They should be a standalone iteration with dedicated testing, not bundled with other features.

6. **Emergency/fast-track paths: Deferred.** Depends on approval chains being implemented first. Low business value for current use case (end-of-line automation projects where all changes are significant).

7. **Multi-currency thresholds: Deferred.** Low business value, high complexity. Current single-currency-per-project model (Decision #11) is sufficient.

8. **Impact categories beyond financial: Deferred.** Requires design of new data collection and scoring dimensions. Extends the impact scoring system and risks breaking existing score calculations. Worth a dedicated design analysis before implementation.

---

## Updated Scope and Effort Estimate

With the decisions above, Phase C scope and effort:

| Feature | Effort | Priority |
|---------|--------|----------|
| Holiday calendars (Python `holidays` library) | 1-2 days | P0 (must ship) |
| In-app notification center | 4-5 days | P1 (should ship) |
| Custom fields (simple, no conditions) | 2-3 days | P2 (nice to have) |
| **Total** | **7-10 days** | |

### Updated Implementation Notes

**Holiday calendars (Python `holidays`):**
- Add `holiday_country_code: str` field to config schemas and `co_workflow_config` domain model (or as a new JSONB key)
- Add `holidays` Python package to project dependencies
- Modify `SLAService._is_business_day()` to accept optional `country_code` and check `holidays` library
- `SLAService` reads `holiday_country_code` from config via `ChangeOrderConfigService`
- Config page gets a "Country" dropdown in SLA Rules tab or a new "Holidays" section
- Minimal migration: add column/field for country code with default (e.g., "IT")

**In-app notification center:**
- New `notifications` table: `id`, `user_id` (FK), `event_type`, `title`, `message`, `resource_type`, `resource_id`, `read_at` (nullable), `created_at`
- New `NotificationService` for creating and querying notifications
- Extend `NotificationEvent` enum with CO workflow events: CO_SUBMITTED, CO_APPROVED, CO_REJECTED, CO_ESCALATED, CO_IMPLEMENTED, CO_STATUS_CHANGED
- `ChangeOrderWorkflowService` emits notification events at each transition point (submit_for_approval, approve_change_order, reject_change_order, escalate_change_order)
- Notification recipients determined by context: submitter gets status updates, assigned approver gets assignment/escalation alerts, admin gets all
- New API endpoints: `GET /api/v1/notifications` (list), `PUT /api/v1/notifications/{id}/read` (mark read), `PUT /api/v1/notifications/read-all` (mark all read)
- Frontend: notification bell icon in header, dropdown with recent notifications, link to relevant CO
- Notification rules stored as JSONB on `co_workflow_config`: which events trigger which recipient groups

**Custom fields (simple):**
- New JSONB column `custom_fields` on `co_workflow_config` for field definitions: `[{name, type, required, options}]`
- New JSONB column `custom_field_values` on `change_orders` for per-CO values
- `CustomFieldService` validates values against field definitions from config
- Extend `ChangeOrderCreate` and `ChangeOrderUpdate` schemas with optional `custom_field_values`
- Frontend dynamic form fields on CO create/edit pages based on active field definitions
- Config page gets "Custom Fields" tab with field builder UI
- Custom field values are versioned with the CO (part of EVCS versioning)

---

## References

- Phase A analysis: `docs/03-project-plan/iterations/2026-05-05-configurable-change-order-workflow/00-analysis.md`
- Phase A plan: `docs/03-project-plan/iterations/2026-05-05-configurable-change-order-workflow/phase-a/01-plan-phase-a.md`
- Config domain model: `backend/app/models/domain/change_order_config.py`
- Config service: `backend/app/services/change_order_config_service.py`
- SLA service: `backend/app/services/sla_service.py` (line 199-213: `_is_business_day()` with holiday TODO)
- Notification system: `backend/app/core/notifications/_telegram.py`
- Frontend config page: `frontend/src/features/change-orders/components/ChangeOrderConfigPage.tsx`
- Telegram notification docs: `docs/02-architecture/cross-cutting/telegram-notifications.md`
- Change order domain model: `backend/app/models/domain/change_order.py`
