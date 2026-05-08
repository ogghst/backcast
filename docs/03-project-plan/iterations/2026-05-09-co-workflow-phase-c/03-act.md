# Act: Phase C - Holiday Calendars + In-App Notifications + Custom Fields

**Completed:** 2026-05-08
**Based on:** `02-check.md`

---

## 1. Iteration Summary

Phase C delivered three independent features extending the Change Order Workflow configuration system:

1. **Holiday Calendars** -- `SLAService._is_business_day()` now excludes public holidays for the configured country code via the Python `holidays` library. Config page exposes a "Holiday Country" dropdown.

2. **In-App Notifications** -- Per-user notification center with `notifications` table, `NotificationService`, 4 API endpoints, frontend `NotificationBell` component integrated into `AppLayout` header. Workflow transitions (submit, approve, reject) dispatch notifications using a fire-and-forget pattern.

3. **Custom Fields** -- JSONB field definitions on config (`custom_fields`) and per-CO values (`custom_field_values`). `CustomFieldService` validates field types, required constraints, and select options. Config page includes a Custom Fields tab with a field builder UI.

All 11 functional acceptance criteria passed. All 4 technical quality criteria passed. Test coverage on new service modules: 100% (`notification_service.py`) and 96.3% (`custom_field_service.py`).

---

## 2. Improvements Implemented

### Critical Issues (from CHECK)

| Issue | Resolution | Verification |
|-------|------------|--------------|
| `calculate_business_days_remaining()` did not pass `country_code` to `_is_business_day()`, causing inconsistent holiday awareness across SLA methods | Added `country_code` parameter to `calculate_business_days_remaining()` and forwarded it to every `_is_business_day()` call within that method | 2 new tests: `test_calculate_business_days_remaining_excludes_holidays` and `test_calculate_business_days_remaining_with_no_country_code` |

### High-Value Improvements (from CHECK)

| Change | Rationale | Files Affected | Verification |
|--------|-----------|----------------|--------------|
| Added snapshot test for new config keys | `generate_snapshot()` output was only verified by code review, not by automated test. `holiday_country_code` and `custom_fields` keys could silently disappear if the method were refactored. | `tests/unit/services/test_change_order_config_service.py` | `test_snapshot_includes_new_config_keys` asserts both keys exist in snapshot output |
| Added notification integration test | CHECK identified missing integration test for notification lifecycle (create, read, mark read cycle). This is the critical user path. | `tests/integration/services/test_notification_lifecycle.py`, `tests/conftest.py` | `test_create_read_and_mark_as_read_lifecycle` exercises full create -> list -> mark read -> verify cycle |

### Deferred Items (from CHECK)

| Item | Reason Deferred | Target |
|------|-----------------|--------|
| Frontend `NotificationBell.test.tsx` component test | Low risk; component is simple (render badge + click handler). Frontend component test template not yet established. | Dedicated frontend testing iteration |
| RBAC `notification-read` permission seeding | CHECK concluded that user-scoped endpoints (personal notifications) correctly use only `get_current_active_user`. RBAC RoleChecker is unnecessary for endpoints where data is already scoped to the authenticated user. | No action needed; plan specification was over-engineered |
| `mark_all_as_read` bulk UPDATE optimization | Current implementation loads all unread notifications into memory before updating. Acceptable at current scale (users unlikely to have thousands of unread notifications). | Address if performance becomes measurable issue |

---

## 3. Standards and Patterns Established

| Pattern | Description | Standardize? | Action |
|---------|-------------|--------------|--------|
| Fire-and-forget notification dispatch | Wrap notification creation in `try/except` with `logging.exception()`. Notification failure must never block the primary workflow operation. | Yes | Already used in `ChangeOrderWorkflowService`. Adopt for all future notification integration points. Add to code review checklist. |
| User-scoped endpoints without RBAC | Endpoints returning data scoped to `current_user.user_id` (e.g., personal notifications) use `get_current_active_user` dependency only. No `RoleChecker` needed because the data is already filtered to the requesting user. | Yes | Document in API conventions. Add to `docs/02-architecture/` API route patterns. |
| JSONB config + Pydantic schema + Service validation | Store structured config as JSONB on `co_workflow_config`, define a Pydantic schema for validation, add a dedicated service method for reading/validating. Pattern used for `custom_fields`, `impact_weights`, `score_boundaries`, `workflow_transitions`. | Yes (already established) | Continue following this pattern for future config sections (e.g., approval chains). |
| Independent feature parallelism | Three features sharing zero files can be developed and tested in parallel. Any can be dropped without affecting the others. | Yes | Apply this principle when planning future iterations with multiple features. Verify file-level independence during PLAN phase. |
| Caller grep when modifying shared dependencies | When modifying a method signature or behavior (like adding `country_code` to `_is_business_day`), grep for all callers and update every one. | Yes | Add to code review checklist. The `calculate_business_days_remaining` bug was caused by missing this step. |

---

## 4. Technical Debt Ledger

### Created This Iteration

| ID | Description | Impact | Effort | Target |
|----|-------------|--------|--------|--------|
| TD-PC-1 | `mark_all_as_read` loads all unread notifications into memory before updating | Low | 0.5 day | When performance data justifies |
| TD-PC-2 | Notification event-to-recipient mapping is hardcoded in `ChangeOrderWorkflowService` dispatch calls | Low | 1 day | When notification rules UI is built |
| TD-PC-3 | No frontend component test for `NotificationBell` | Low | 0.5 day | Frontend testing iteration |

### Resolved This Iteration

| ID | Resolution | Time Spent |
|----|------------|------------|
| TD-PA-1 (pre-existing) | `SLAService._is_business_day()` had explicit TODO comment requesting holiday awareness | Holiday awareness implemented via `holidays` library with configurable `country_code` | Included in iteration scope |

**Net Debt Change:** +3 items (all low impact, deferred by design)

---

## 5. Lessons Learned

### What Went Well

1. **Feature independence reduced risk.** Holiday calendars, notifications, and custom fields shared no source files. This allowed isolated development, testing, and potential drop of any feature without side effects.

2. **JSONB config pattern continues to deliver.** Adding `holiday_country_code`, `custom_fields`, and `custom_field_values` as JSONB required zero schema changes to the CO entity (already had `config_snapshot` JSONB) and minimal migration effort.

3. **Notification fire-and-forget is robust.** Wrapping notification dispatch in `try/except` with logging ensured that the one integration issue (notification creation failure) could never block the primary CO workflow. This should be the default pattern.

4. **Test quality was high from the start.** Descriptive test names, isolated mocks, deterministic assertions (fixed dates for holiday tests). This made the CHECK phase efficient.

### What to Improve

1. **Grepping for all callers is mandatory when modifying shared methods.** The `calculate_business_days_remaining` bug was a direct result of modifying `_is_business_day` without updating all its callers. This must be a checklist item.

2. **User-scoped endpoints do not need RBAC RoleChecker.** The plan specified `notification-read` permission, but authentication alone is sufficient and correct for personal data endpoints. Future plans should distinguish between "data the user is allowed to see" (needs RBAC) and "the user's own data" (needs only authentication).

3. **At least one integration test per feature should be non-negotiable.** Unit tests covered service logic well, but the notification lifecycle integration test was nearly skipped. Integration tests catch wiring bugs that unit tests with mocks cannot.

---

## 6. Process Improvements

### Effective Practices to Continue

- **Feature independence check during planning:** Verify that planned features share no source files. If they do, flag the coupling explicitly.
- **Config snapshot testing:** After adding new config sections, assert their presence in `generate_snapshot()` output via automated test.
- **Fire-and-forget for cross-cutting side effects:** Any operation that should not block the primary flow (notifications, logging, analytics) must be wrapped in try/except with logging.

### Process Changes for Future Iterations

| Change | Rationale | Owner |
|--------|-----------|-------|
| Add "grep all callers" to code review checklist | Prevents consistency bugs like `calculate_business_days_remaining` missing `country_code` | Code reviewer |
| Clarify RBAC vs authentication during planning | Avoid specifying unnecessary RBAC permissions for user-scoped endpoints | Plan author |
| Require minimum one integration test per feature | Prevents gaps where unit tests pass but wiring is broken | Developer |

---

## 7. Documentation Updates

| Document | Update Needed | Status |
|----------|---------------|--------|
| `docs/02-architecture/cross-cutting/` | Add fire-and-forget notification dispatch pattern | Pending |
| `docs/02-architecture/` API conventions | Document that user-scoped endpoints use only `get_current_active_user`, not `RoleChecker` | Pending |
| Code review checklist | Add "grep all callers when modifying shared methods" | Pending |
| Sprint backlog | Mark Phase C tasks complete | Pending |

---

## 8. Deferred Items

The following items from the Phase C analysis were explicitly deferred and are not part of this iteration's debt:

| Item | Reason | Recommended Timing |
|------|--------|--------------------|
| Multi-level approval chains | High regression risk to core approval flow. Modifies `approve_change_order()`, `get_approver_for_impact()`, `assigned_approver_id`. Requires dedicated iteration. | Dedicated Phase D iteration |
| Emergency/fast-track approval paths | Depends on approval chains being implemented first. Low business value for current use case. | After approval chains |
| Multi-currency thresholds | Low business value, high complexity. Single-currency-per-project model sufficient. | When business demand emerges |
| Impact categories beyond financial | Requires new data collection and scoring dimensions. Risks breaking existing score calculations. Needs dedicated design analysis. | After Phase D |
| Email/push notification channels | In-app only for now. Adding channels requires notification abstraction layer. | When user demand emerges |
| Notification rules configuration UI | Event-to-recipient mapping is hardcoded. A rules engine + UI would make this configurable. | When rules change frequently |
| Conditional visibility on custom fields | Fields always visible on all COs. Conditional visibility adds significant UI complexity. | When users request it |
| Bulk UPDATE optimization for `mark_all_as_read` | Acceptable at current scale. | When unread counts exceed ~1000 per user |

---

## 9. Recommendations for Next Iteration

### Unlocked Capabilities

- **Notification infrastructure** is now in place. Future features (email notifications, notification preferences, notification rules engine) build on `NotificationService` and the `notifications` table.
- **Custom field validation** is extensible. New field types (checkbox, multi-select, file reference) can be added to `CustomFieldService` with minimal changes.
- **Holiday-aware SLA** is live. Future time-based calculations (schedule impact, deadline tracking) can reuse `_is_business_day()` with country code.

### Recommended Next Phase

**Phase D: Multi-Level Approval Chains** is the logical next step, based on:

1. It was the highest-value deferred feature from the Phase C analysis.
2. It addresses a PMI best practice (CCB-style review for high-impact changes).
3. The notification system now provides a mechanism to notify each approver in the chain.
4. It requires dedicated iteration scope due to regression risk on the core approval flow.

### Key Risks for Next Iteration

- Multi-level approval modifies `approve_change_order()` and `get_approver_for_impact()` -- the most critical code paths in the workflow. Thorough integration testing is essential.
- The `assigned_approver_id` column on `change_orders` is single-valued. Approval chains may require `approval_chain_progress` JSONB to track multi-step state.
- Frontend needs to display chain progress and indicate "Partially Approved" status.

---

## 10. Iteration Closure

### Final Status

- [x] All 11 functional acceptance criteria from PLAN phase verified (PASS)
- [x] All 4 technical quality criteria passed (MyPy, Ruff, coverage, TypeScript)
- [x] Consistency bug fixed (`calculate_business_days_remaining` now passes `country_code`)
- [x] Snapshot test added for new config keys
- [x] Notification integration test added for lifecycle coverage
- [x] All approved CHECK improvements implemented
- [x] Lessons learned documented

**Iteration Status:** COMPLETE

**Success Criteria Met:** 11 of 11 functional, 4 of 4 technical

**Iteration Closed:** 2026-05-08
