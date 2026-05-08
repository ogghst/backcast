# Plan: Phase C - Holiday Calendars + In-App Notifications + Custom Fields

**Created:** 2026-05-08
**Status:** Planning
**Analysis:** `00-analysis.md`

---

## Decisions (from analysis)

1. **Holiday calendar source:** Python `holidays` library with configurable `country_code` on config. No DB holiday table, no admin holiday management UI.
2. **Notification scope:** Per-user in-app notification center with bell icon, notification list, read/unread tracking. New `notifications` DB table. Per-user targeting.
3. **Custom fields:** Simple fields only -- name, type (text/number/date/select), required flag, options for select types. No conditional visibility. Always visible on all COs.
4. **Feature priority:** Holidays (P0) > Notifications (P1) > Custom Fields (P2).
5. **Multi-level approval chains:** Deferred to dedicated iteration.
6. **Emergency/fast-track, multi-currency, impact categories:** All deferred.

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option:** Option 2 (Broader Scope) from analysis, with three independent features: Holiday Calendars, In-App Notification Center, Custom Fields.
- **Architecture:** Each feature extends the existing config architecture (JSONB on `co_workflow_config`) and integrates with existing services. Notifications introduce a new domain entity and API surface.
- **Key Decisions:** Python `holidays` library (zero-maintenance), per-user notifications with DB table, simple custom fields with no conditional logic, drop priority order for scope management.

### Success Criteria

**Functional Criteria:**

- [ ] `SLAService._is_business_day()` excludes public holidays for the configured country code VERIFIED BY: unit tests with known holiday dates
- [ ] Config page exposes a "Holiday Country" dropdown that persists `holiday_country_code` VERIFIED BY: integration test
- [ ] Workflow transition events (submit, approve, reject, escalate) create per-user notification records VERIFIED BY: integration test
- [ ] `GET /api/v1/notifications` returns paginated notifications for the authenticated user VERIFIED BY: API test
- [ ] `PUT /api/v1/notifications/{id}/read` marks a single notification as read VERIFIED BY: API test
- [ ] `PUT /api/v1/notifications/read-all` marks all user notifications as read VERIFIED BY: API test
- [ ] Frontend header displays a notification bell with unread count badge VERIFIED BY: UI verification
- [ ] Config snapshot at CO submission includes `holiday_country_code`, `custom_fields`, and `notification_rules` VERIFIED BY: unit test
- [ ] Custom field definitions are stored as JSONB on config and validated on CO create/update VERIFIED BY: unit tests
- [ ] Custom field values are stored per-CO as JSONB and returned in CO detail responses VERIFIED BY: API test
- [ ] Config page has "Custom Fields" tab with field builder UI (add/remove/reorder fields) VERIFIED BY: UI verification

**Technical Criteria:**

- [ ] MyPy strict mode: zero errors on all new and modified files VERIFIED BY: `uv run mypy app/`
- [ ] Ruff: zero errors on all new and modified files VERIFIED BY: `uv run ruff check .`
- [ ] Test coverage >= 80% on all new modules VERIFIED BY: `uv run pytest --cov=app`
- [ ] Frontend: TypeScript strict, ESLint clean VERIFIED BY: `npm run lint && npm run typecheck`
- [ ] All new Alembic migrations apply cleanly forward and backward VERIFIED BY: `alembic upgrade head` then `alembic downgrade -1`

**Business Criteria:**

- [ ] SLA deadlines no longer count public holidays as business days VERIFIED BY: comparing deadline calculation with and without holiday awareness for a known holiday period
- [ ] Approvers receive in-app notifications when a CO is assigned to them VERIFIED BY: submitting a CO and verifying the assigned approver has a notification

### Scope Boundaries

**In Scope:**

- Holiday awareness in SLA calculation via Python `holidays` library
- `holiday_country_code` field on config (JSONB key on `co_workflow_config`)
- Country dropdown on config page SLA Rules tab
- New `notifications` table with user_id, event_type, title, message, resource_type, resource_id, read_at
- `NotificationService` for creating and querying notifications
- New CO workflow events in `NotificationEvent` enum
- Notification dispatch in `ChangeOrderWorkflowService` transition methods
- Notification API endpoints (list, mark read, mark all read)
- Frontend notification bell component in `AppLayout` header
- Frontend notification dropdown/list panel
- `custom_fields` JSONB column on `co_workflow_config` for field definitions
- `custom_field_values` JSONB column on `change_orders` for per-CO data
- `CustomFieldService` for validation of values against definitions
- Custom Fields tab on config page
- Dynamic custom field inputs on CO create/edit forms
- Config snapshot includes all new config sections
- Alembic migrations for new tables and columns
- RBAC permissions for notification endpoints

**Out of Scope:**

- Multi-level approval chains (deferred to dedicated iteration)
- Emergency/fast-track approval paths (deferred)
- Multi-currency thresholds (deferred)
- Impact categories beyond financial (deferred)
- Email or push notification channels (in-app only for now)
- Notification rules configuration UI (hardcoded event-to-recipient mapping for Phase C)
- Conditional visibility on custom fields
- Admin UI for managing individual holiday dates (library handles this)

---

## Work Decomposition

### Feature 1: Holiday Calendars (P0 -- 1-2 days)

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| 1   | Add `holidays` dependency and `holiday_country_code` to config model | `backend/pyproject.toml`, `backend/app/models/domain/change_order_config.py` | None | `holidays` in deps; `holiday_country_code` column exists on `ChangeOrderWorkflowConfig` | Low |
| 2 | Alembic migration for `holiday_country_code` column | `backend/alembic/versions/20260509_*.py` | Task 1 | Migration adds nullable string column with default "IT"; `alembic upgrade head` succeeds | Low |
| 3 | Update config schemas and service to handle `holiday_country_code` | `backend/app/models/schemas/change_order_config.py`, `backend/app/services/change_order_config_service.py`, `backend/app/api/routes/change_order_config.py` | Task 1 | `WorkflowConfigUpdateRequest` includes `holiday_country_code`; `generate_snapshot()` includes it; API round-trips the value | Low |
| 4 | Modify `SLAService._is_business_day()` for holiday awareness | `backend/app/services/sla_service.py` | Task 1 | `_is_business_day()` returns False for known holidays in configured country; unit tests pass with IT holidays | Med |
| 5 | Write holiday calendar tests | `backend/tests/unit/services/test_sla_service.py` (extend) | Task 4 | Tests cover: holiday excluded, non-holiday included, no country code falls back to weekday check, multiple years | Low |
| 6 | Frontend: add Holiday Country dropdown to SLA Rules tab | `frontend/src/features/change-orders/api/useWorkflowConfig.ts`, `frontend/src/features/change-orders/components/ChangeOrderConfigPage.tsx` | Task 3 | Dropdown renders with country list; selected value persists on save; TypeScript types updated | Low |

### Feature 2: In-App Notification Center (P1 -- 4-5 days)

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| 7 | Create `Notification` domain model + Alembic migration | `backend/app/models/domain/notification.py`, `backend/alembic/versions/20260509_*.py` | None | `notifications` table created with columns: id, user_id (FK to users), event_type, title, message, resource_type, resource_id, read_at (nullable), created_at; migration up/down clean | Med |
| 8 | Create notification Pydantic schemas | `backend/app/models/schemas/notification.py` | Task 7 | `NotificationResponse`, `NotificationListResponse` schemas defined; `read_at` is optional datetime; pagination fields present | Low |
| 9 | Create `NotificationService` | `backend/app/services/notification_service.py` | Task 7 | `create_notification()`, `get_user_notifications()` (paginated), `mark_as_read()`, `mark_all_as_read()`, `get_unread_count()` all functional; MyPy strict clean | Med |
| 10 | Add CO workflow events to `NotificationEvent` enum | `backend/app/core/notifications/_types.py` | None | New events: CO_SUBMITTED, CO_APPROVED, CO_REJECTED, CO_ESCALATED, CO_STATUS_CHANGED; existing events unchanged | Low |
| 11 | Integrate notification dispatch into `ChangeOrderWorkflowService` | `backend/app/services/change_order_workflow_service.py` | Tasks 9, 10 | `submit_for_approval()` notifies assigned approver; `approve_change_order()` notifies submitter; `reject_change_order()` notifies submitter; `escalate_change_order()` notifies admin/approver | Med |
| 12 | Create notification API routes | `backend/app/api/routes/notifications.py`, `backend/app/api/routes/__init__.py` (register router) | Tasks 8, 9 | `GET /api/v1/notifications` (paginated, filtered by user), `PUT /api/v1/notifications/{id}/read`, `PUT /api/v1/notifications/read-all`; RBAC requires `notification-read` permission; OpenAPI docs show endpoints | Med |
| 13 | Write notification backend tests | `backend/tests/unit/services/test_notification_service.py`, `backend/tests/integration/services/test_notification_lifecycle.py` | Tasks 9, 11, 12 | Unit tests: create, paginate, mark read, mark all read, unread count. Integration: full lifecycle from CO submit to notification delivery | Med |
| 14 | Frontend: notification types, hooks, query keys | `frontend/src/api/queryKeys.ts`, new `frontend/src/features/notifications/api/useNotifications.ts` | Task 12 | `queryKeys.notifications` defined; `useNotifications()` hook fetches paginated list; `useMarkNotificationRead()` mutation; `useMarkAllNotificationsRead()` mutation; `useUnreadNotificationCount()` hook | Med |
| 15 | Frontend: notification bell + dropdown component | New `frontend/src/features/notifications/components/NotificationBell.tsx`, `frontend/src/features/notifications/components/NotificationList.tsx` | Task 14 | Bell icon in AppLayout header shows unread count badge; dropdown lists recent notifications with read/unread styling; clicking a notification navigates to the CO detail page | Med |
| 16 | Integrate NotificationBell into AppLayout | `frontend/src/layouts/AppLayout.tsx` | Task 15 | NotificationBell renders in the header alongside UserProfile; responsive layout not broken | Low |
| 17 | Frontend notification tests | `frontend/src/features/notifications/components/__tests__/NotificationBell.test.tsx` | Task 15 | Component renders with count; dropdown opens on click; mark-read fires mutation | Low |

### Feature 3: Custom Fields (P2 -- 2-3 days)

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| 18 | Add `custom_fields` JSONB to config model + `custom_field_values` JSONB to CO model + migration | `backend/app/models/domain/change_order_config.py`, `backend/app/models/domain/change_order.py`, `backend/alembic/versions/20260509_*.py` | None | `custom_fields` nullable JSONB on `co_workflow_config`; `custom_field_values` nullable JSONB on `change_orders`; migration up/down clean | Low |
| 19 | Create custom field Pydantic schemas | `backend/app/models/schemas/custom_field.py` | None | `CustomFieldDefinition` schema: name (str), type (enum: text/number/date/select), required (bool), options (list[str] for select); `CustomFieldValues` schema: dict[str, Any] | Low |
| 20 | Create `CustomFieldService` for validation | `backend/app/services/custom_field_service.py` | Tasks 18, 19 | `validate_field_values()` checks: all required fields present, values match declared types, select values are in options list; returns list of validation errors | Med |
| 21 | Extend config schemas and service for custom fields | `backend/app/models/schemas/change_order_config.py`, `backend/app/services/change_order_config_service.py`, `backend/app/api/routes/change_order_config.py` | Tasks 18, 19 | `WorkflowConfigUpdateRequest` includes `custom_fields`; `generate_snapshot()` includes `custom_fields`; config CRUD round-trips the definitions | Low |
| 22 | Extend CO schemas and service for custom field values | `backend/app/models/schemas/change_order.py`, `backend/app/services/change_order_service.py` | Tasks 20, 21 | `ChangeOrderCreate`/`ChangeOrderUpdate` accept optional `custom_field_values`; validation runs on create/update; values stored in `custom_field_values` JSONB; values returned in `ChangeOrderDetailResponse` | Med |
| 23 | Write custom field backend tests | `backend/tests/unit/services/test_custom_field_service.py`, update `backend/tests/unit/services/test_change_order_config_service.py` | Tasks 20, 22 | Unit tests: validation passes for valid data, rejects missing required fields, rejects invalid types, rejects invalid select options; integration: config CRUD with custom fields, CO CRUD with custom field values | Med |
| 24 | Frontend: custom field types and config tab | `frontend/src/features/change-orders/api/useWorkflowConfig.ts`, `frontend/src/features/change-orders/components/ChangeOrderConfigPage.tsx` | Task 21 | TypeScript types for custom fields; new "Custom Fields" tab with add/remove field UI; field type dropdown; required toggle; options editor for select type; values persist on config save | Med |
| 25 | Frontend: dynamic custom fields on CO form | `frontend/src/features/change-orders/components/ChangeOrderModal.tsx` | Tasks 22, 24 | Custom field inputs render dynamically based on active config field definitions; validation errors display inline; values submit with CO create/update payload | Med |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph - Phase C
# Three independent feature tracks that can run in parallel

tasks:
  # === Feature 1: Holiday Calendars (P0) ===
  - id: BE-001
    name: "Add holidays dependency + holiday_country_code to config model"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Alembic migration for holiday_country_code column"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Update config schemas, service, and API routes for holiday_country_code"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-004
    name: "Modify SLAService._is_business_day() for holiday awareness"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-005
    name: "Write holiday calendar unit tests"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: FE-001
    name: "Add Holiday Country dropdown to config page SLA Rules tab"
    agent: pdca-frontend-do-executor
    dependencies: [BE-003]

  # === Feature 2: In-App Notifications (P1) ===
  - id: BE-006
    name: "Create Notification domain model + Alembic migration"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-007
    name: "Create notification Pydantic schemas"
    agent: pdca-backend-do-executor
    dependencies: [BE-006]

  - id: BE-008
    name: "Create NotificationService (CRUD + queries)"
    agent: pdca-backend-do-executor
    dependencies: [BE-006]

  - id: BE-009
    name: "Add CO workflow events to NotificationEvent enum"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-010
    name: "Integrate notification dispatch into ChangeOrderWorkflowService"
    agent: pdca-backend-do-executor
    dependencies: [BE-008, BE-009]

  - id: BE-011
    name: "Create notification API routes (list, mark read, mark all read)"
    agent: pdca-backend-do-executor
    dependencies: [BE-007, BE-008]

  - id: BE-012
    name: "Write notification backend tests (unit + integration)"
    agent: pdca-backend-do-executor
    dependencies: [BE-010, BE-011]

  - id: FE-002
    name: "Notification query keys, types, and TanStack Query hooks"
    agent: pdca-frontend-do-executor
    dependencies: [BE-011]

  - id: FE-003
    name: "NotificationBell + NotificationList components"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-004
    name: "Integrate NotificationBell into AppLayout header"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  - id: FE-005
    name: "Frontend notification component tests"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  # === Feature 3: Custom Fields (P2) ===
  - id: BE-013
    name: "Add custom_fields JSONB to config + custom_field_values JSONB to CO + migration"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-014
    name: "Create custom field Pydantic schemas"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-015
    name: "Create CustomFieldService for validation"
    agent: pdca-backend-do-executor
    dependencies: [BE-013, BE-014]

  - id: BE-016
    name: "Extend config schemas, service, and API for custom fields"
    agent: pdca-backend-do-executor
    dependencies: [BE-013, BE-014]

  - id: BE-017
    name: "Extend CO schemas and service for custom field values"
    agent: pdca-backend-do-executor
    dependencies: [BE-015, BE-016]

  - id: BE-018
    name: "Write custom field backend tests (unit + integration)"
    agent: pdca-backend-do-executor
    dependencies: [BE-017]

  - id: FE-006
    name: "Custom field types and Custom Fields tab on config page"
    agent: pdca-frontend-do-executor
    dependencies: [BE-016]

  - id: FE-007
    name: "Dynamic custom field inputs on CO create/edit form"
    agent: pdca-frontend-do-executor
    dependencies: [BE-017, FE-006]

  # === Cross-cutting: Backend test suite (must run sequentially) ===
  - id: BE-019
    name: "Run full backend quality gate (mypy + ruff + pytest --cov)"
    agent: pdca-backend-do-executor
    dependencies: [BE-005, BE-012, BE-018]
    group: quality-gate
    kind: test

  # === Cross-cutting: Frontend quality gate ===
  - id: FE-008
    name: "Run frontend quality gate (lint + typecheck + test:coverage)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-005, FE-007]
    group: quality-gate
    kind: test
```

**Execution levels (parallel opportunity):**

- **Level 0 (immediate):** BE-001, BE-006, BE-009, BE-013, BE-014 -- all independent, can start immediately
- **Level 1:** BE-002, BE-003, BE-004, BE-007, BE-008, BE-015, BE-016
- **Level 2:** BE-005, BE-010, BE-011, BE-017, FE-001, FE-002, FE-006
- **Level 3:** BE-012, BE-018, FE-003, FE-007
- **Level 4:** FE-004, FE-005
- **Level 5:** BE-019, FE-008

---

## Test Specification

### Test Hierarchy

```
tests/
├── unit/
│   ├── services/
│   │   ├── test_sla_service.py              (extend: holiday tests)
│   │   ├── test_notification_service.py     (new)
│   │   ├── test_custom_field_service.py     (new)
│   │   └── test_change_order_config_service.py  (extend: custom fields, holiday_country_code)
│   └── ...
├── integration/
│   ├── services/
│   │   ├── test_notification_lifecycle.py   (new)
│   │   └── test_change_order_config_lifecycle.py  (extend)
│   └── ...
└── frontend/
    └── features/
        └── notifications/
            └── components/
                └── __tests__/
                    └── NotificationBell.test.tsx (new)
```

### Test Cases

#### Holiday Calendar Tests

| Test ID | Test Name | Criterion | Type | Expected Result |
| ------- | --------- | --------- | ---- | --------------- |
| T-001 | `test_is_business_day_excludes_known_holiday` | Holiday excluded | Unit | Returns False for April 25 (Liberation Day, IT) |
| T-002 | `test_is_business_day_includes_non_holiday_weekday` | Non-holiday included | Unit | Returns True for a regular weekday that is not a holiday |
| T-003 | `test_is_business_day_no_country_code_falls_back_to_weekday` | Fallback behavior | Unit | Returns True for Mon-Fri, False for Sat-Sun when no country code |
| T-004 | `test_is_business_day_weekend_still_excluded_with_holidays` | Weekend exclusion | Unit | Returns False for a Saturday even with country code set |
| T-005 | `test_sla_deadline_skips_holidays` | End-to-end SLA | Unit | Deadline calculated over Easter holiday period excludes the holiday |

#### Notification Tests

| Test ID | Test Name | Criterion | Type | Expected Result |
| ------- | --------- | --------- | ---- | --------------- |
| T-006 | `test_create_notification_stores_record` | Notification creation | Unit | Notification record exists in DB with correct user_id, event_type, message |
| T-007 | `test_get_user_notifications_returns_only_users_notifications` | Per-user isolation | Unit | User A's query does not return User B's notifications |
| T-008 | `test_mark_as_read_sets_read_at_timestamp` | Read marking | Unit | `read_at` changes from None to a datetime |
| T-009 | `test_mark_all_as_read_marks_all_unread` | Bulk read marking | Unit | All user's notifications have `read_at` set |
| T-010 | `test_get_unread_count_excludes_read_notifications` | Unread count | Unit | Count matches only notifications where `read_at` is None |
| T-011 | `test_submit_for_approval_creates_approver_notification` | Workflow integration | Integration | After submit, assigned approver has a notification |
| T-012 | `test_approve_change_order_creates_submitter_notification` | Workflow integration | Integration | After approval, CO submitter has a notification |
| T-013 | `test_reject_change_order_creates_submitter_notification` | Workflow integration | Integration | After rejection, CO submitter has a notification |

#### Custom Field Tests

| Test ID | Test Name | Criterion | Type | Expected Result |
| ------- | --------- | --------- | ---- | --------------- |
| T-014 | `test_validate_field_values_passes_valid_data` | Valid input | Unit | No validation errors returned |
| T-015 | `test_validate_field_values_rejects_missing_required` | Required check | Unit | Returns error for missing required field |
| T-016 | `test_validate_field_values_rejects_wrong_type_number` | Type check | Unit | Returns error when string provided for number field |
| T-017 | `test_validate_field_values_rejects_invalid_select_option` | Select validation | Unit | Returns error when select value not in options list |
| T-018 | `test_validate_field_values_allows_optional_field_missing` | Optional fields | Unit | No error when optional field is not provided |
| T-019 | `test_custom_field_values_stored_and_retrieved` | CRUD round-trip | Integration | Values stored on create, returned on read, updated on edit |
| T-020 | `test_config_snapshot_includes_custom_fields` | Snapshot integrity | Unit | `generate_snapshot()` output contains `custom_fields` key |

### Test Infrastructure Needs

- **Fixtures:** Test user records for notification targeting (submitter, approver, admin); test project with config
- **Mocks:** `holidays` library behavior for deterministic testing (no need to mock -- library is deterministic given country + year)
- **Database state:** Notification table requires clean state for count assertions; tests that create notifications should clean up or use isolated user IDs

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --------- | ----------- | ----------- | ------ | ---------- |
| Technical | `holidays` library version change breaks country codes | Low | Low | Pin version in pyproject.toml; library is mature and stable |
| Technical | Notification creation slows down CO workflow transitions | Low | Med | Notification creation is async-compatible (single INSERT); no external service calls; profile if needed |
| Integration | Notification table grows unbounded | Med | Low | Add pagination to list endpoint; consider archiving in future iteration |
| Integration | Custom field validation errors surface as confusing UI messages | Med | Med | Map validation errors to user-friendly messages in frontend; test error display |
| Regression | Holiday awareness changes existing SLA deadline calculations | Med | High | Migration sets default "IT" which matches current behavior (no holidays excluded); only activates when country code is explicitly set and library returns holidays |
| Regression | Notification dispatch in workflow service breaks CO submission flow | Low | High | Wrap notification creation in try/except with logging; notification failure must not block the primary workflow operation |

---

## Migration Plan

### Migration 1: Holiday country code (Feature 1)

**File:** `backend/alembic/versions/20260509_add_holiday_country_code.py`

- Add `holiday_country_code` column to `co_workflow_config`: `String(10), nullable=True, server_default='IT'`
- This is a non-breaking addition. Existing configs get default "IT" which is a no-op until `SLAService` is updated to use it.

### Migration 2: Notifications table (Feature 2)

**File:** `backend/alembic/versions/20260509_create_notifications_table.py`

- Create `notifications` table with columns:
  - `id`: UUID PK (using `gen_random_uuid()`)
  - `user_id`: UUID NOT NULL, FK to `users.user_id` (or application-level reference matching existing pattern)
  - `event_type`: String(50) NOT NULL
  - `title`: String(200) NOT NULL
  - `message`: Text NOT NULL
  - `resource_type`: String(50) nullable (e.g., "change_order")
  - `resource_id`: UUID nullable (e.g., change_order_id)
  - `read_at`: TIMESTAMP WITH TIME ZONE nullable
  - `created_at`: TIMESTAMP WITH TIME ZONE NOT NULL, default `now()`
- Indexes: `ix_notifications_user_id` on `user_id`, `ix_notifications_user_read` on `(user_id, read_at)` for unread queries
- Add `notification-read` permission to RBAC seed data

### Migration 3: Custom fields (Feature 3)

**File:** `backend/alembic/versions/20260509_add_custom_fields_columns.py`

- Add `custom_fields` column to `co_workflow_config`: `JSONB, nullable=True`
- Add `custom_field_values` column to `change_orders`: `JSONB, nullable=True`
- Both nullable -- existing records are unaffected

---

## Prerequisites

### Technical

- [ ] `holidays` Python package added to `pyproject.toml` dependencies
- [ ] Database migrations applied in order
- [ ] RBAC seed data includes `notification-read` permission

### Documentation

- [x] Analysis phase approved
- [x] Existing config architecture (Phases A/B) understood
- [x] Notification system (`app/core/notifications/`) reviewed
- [x] SLA service holiday TODO reviewed
- [x] Frontend layout (`AppLayout.tsx`) reviewed for bell placement

---

## Documentation References

### Required Reading

- Config domain model: `backend/app/models/domain/change_order_config.py`
- Config service: `backend/app/services/change_order_config_service.py`
- SLA service: `backend/app/services/sla_service.py` (lines 199-213: holiday TODO)
- Notification system: `backend/app/core/notifications/_types.py`, `backend/app/core/notifications/_telegram.py`
- Workflow service: `backend/app/services/change_order_workflow_service.py`
- CO domain model: `backend/app/models/domain/change_order.py`
- Frontend config page: `frontend/src/features/change-orders/components/ChangeOrderConfigPage.tsx`
- Frontend config hooks: `frontend/src/features/change-orders/api/useWorkflowConfig.ts`
- Frontend layout: `frontend/src/layouts/AppLayout.tsx`
- Query keys: `frontend/src/api/queryKeys.ts`

### Code References

- JSONB column pattern: `co_workflow_config.workflow_transitions` (Phase B)
- Config service reader pattern: `ChangeOrderConfigService.get_workflow_transitions()`
- Config snapshot pattern: `ChangeOrderConfigService.generate_snapshot()`
- API route pattern: `backend/app/api/routes/change_order_config.py`
- Frontend tab pattern: `ChangeOrderConfigPage.tsx` existing tabs
- Frontend TanStack Query hook pattern: `useWorkflowConfig.ts`
- SimpleEntityBase pattern: `backend/app/core/base/base.py`

---

## Verification Steps

After all tasks are complete:

1. **Holiday verification:** Create a CO with SLA spanning a known Italian holiday. Confirm the deadline is pushed by one day compared to the same calculation without holiday awareness.

2. **Notification verification:** Submit a CO for approval. Log in as the assigned approver. Confirm the notification bell shows "1" unread. Open the dropdown. Confirm the notification links to the CO. Mark it as read. Confirm the badge clears.

3. **Custom fields verification:** On the config page Custom Fields tab, add a required "Client Reference" text field and a "Priority" select field with options (Low/Medium/High). Save config. Open CO create form. Confirm both custom fields render. Submit without filling the required field. Confirm validation error. Fill it in and submit. Confirm the CO detail page shows the custom field values.

4. **Config snapshot verification:** Submit a CO for approval. Inspect the `config_snapshot` JSONB on the CO record. Confirm it includes `holiday_country_code`, `custom_fields`, and `notification_rules` (if applicable).

5. **Quality gate:** Run `uv run mypy app/ && uv run ruff check . && uv run pytest --cov=app` -- zero errors, >= 80% coverage. Run `npm run lint && npm run typecheck` -- zero errors.

6. **Migration verification:** `alembic upgrade head` succeeds. `alembic downgrade -1` succeeds. `alembic upgrade head` succeeds again.
