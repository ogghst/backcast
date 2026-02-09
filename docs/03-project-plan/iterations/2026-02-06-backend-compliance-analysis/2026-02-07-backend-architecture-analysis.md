# Backend Architecture Analysis Report

**Date:** 2026-02-07
**Scope:** Backend Routes, Services, and Commands (RSC) Architecture Layer Compliance

## Executive Summary

This report details the findings of a backend codebase analysis against the Routes-Services-Commands (RSC) architecture pattern defined in the [EVCS Core Architecture](../../02-architecture/backend/contexts/evcs-core/architecture.md).

**Overall Compliance:** High.
The core architecture is well-respected across the codebase.
- **Routes Layer**: 100% Compliant. No direct database access or business logic found.
- **Services Layer**: Mostly Compliant. Minor localized violations found in complex services (`ChangeOrderService`, `ScheduleBaselineService`).
- **Commands Layer**: 100% Compliant. Commands properly encapsulate persistence logic without leaking business rules.

## Detailed Findings

### 1. Routes Layer Compliance

**Status:** ✅ **Pass**
**Files Analyzed:** `backend/app/api/routes/*.py`

- **Observations:**
  - Zero instances of `session.execute`, `session.add`, `session.commit`, or `session.delete`.
  - Routes correctly delegate all business logic to Services via `Depends()`.
  - Validation logic is appropriately handled by Pydantic schemas before reaching the route handler.

### 2. Service Layer Compliance

**Status:** ⚠️ **Minor Violations**
**Files Analyzed:** `backend/app/services/*.py`

The Service layer correctly orchestrates business logic and generally delegates writes to Commands. However, specific violations were identified where Services bypass the Command pattern for "side-effect" updates.

#### Violation 1: Direct Session Write for Audit Logs
- **Location:** `app/services/change_order_service.py` (Line 415)
- **Code:** `self.session.add(audit_entry)`
- **Issue:** `ChangeOrderAuditLog` entries are added directly to the session without a Command wrapper.
- **Recommendation:** Create a simple `CreateAuditLogCommand` or encompass audit logging within the primary Command (e.g., `UpdateChangeOrderCommand`).

#### Violation 2: Direct Session Write for Related Entity Updates
- **Location:** `app/services/schedule_baseline_service.py` (Line 361) & `app/services/forecast_service.py`
- **Code:**
  ```python
  cost_element.schedule_baseline_id = baseline_id
  await self.session.flush()
  ```
- **Issue:** When creating a child entity (Baseline/Forecast), the Service directly updates the parent `CostElement`'s foreign key reference and flushes. This modifies the `CostElement` state outside of a `UpdateCostElementCommand`.
- **Recommendation:** encapsulate this relationship update in a localized Command or ensuring `CostElementService.update` is called (though cross-service circular dependency risks must be managed). Given the tightness of the aggregate, this is a low-severity violation.

#### Violation 3: Direct Entity Update in `merge_change_order`
- **Location:** `app/services/change_order_service.py` (Line 716)
- **Code:**
  ```python
  merged_co.status = "Implemented"
  self.session.add(merged_co)
  ```
- **Issue:** The status of the merged Change Order is updated directly. While `merge_branch` (Command) handles the heavy lifting, this final status transition bypasses the `UpdateCommand` which normally handles versioning/auditing.
- **Severity:** Medium. It risks bypassing validation logic in `UpdateCommand`.

### 3. Command Layer Compliance

**Status:** ✅ **Pass**
**Files Analyzed:** `app/core/versioning/commands.py`, `app/core/branching/commands.py`

- **Observations:**
  - Commands are strictly focused on atomic persistence operations.
  - No external service dependencies or complex business rules found.
  - Bitemporal logic (timestamp handling) is correctly encapsulated here using raw SQL for precision, which is the correct place for it.

## Recommendations

1.  **Refactor Audit Logging:** Introduce a lightweight Command for audit log creation to maintain consistency.
2.  **Standardize Status Transitions:** Ensure the final status update in `merge_change_order` uses `UpdateCommand` or is explicitly part of `MergeBranchCommand` logic.
3.  **Monitor "Side Effect" Updates:** Keep an eye on direct FK updates (like `CostElement` linking). If they grow complex, enforce Command usage. For now, the current pattern is acceptable for maintaining aggregate consistency.
