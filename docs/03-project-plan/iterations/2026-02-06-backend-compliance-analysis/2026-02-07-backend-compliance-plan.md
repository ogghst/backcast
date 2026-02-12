# PLAN Phase: Backend RSC Architecture Compliance

## Purpose

Decompose the **approved compliance refactoring** from the Architecture Analysis phase into actionable tasks. This phase defines **WHAT** to test and implement to ensure the backend adheres to the Routes-Services-Commands (RSC) pattern.

**Prerequisite**: [Architecture Analysis](2026-02-07-backend-architecture-analysis.md) completed.

---

## Phase 1: Scope & Success Criteria

### 1.1 Approved Approach Summary

- **Selected Option**: Refactor identified Service layer violations to use **Commands** for all state-changing operations.
- **Architecture**: Strict adherence to **Routes-Services-Commands (RSC)**. Services must not call `session.add`, `session.flush`, or `session.commit` directly for domain entities.
- **Key Decisions**:
  - Introduce `CreateChangeOrderAuditLogCommand` to encapsulate audit logging.
  - Encapsulate parent/child relationship updates (CostElement <-> ScheduleBaseline/Forecast) in Commands.
  - Refactor `merge_change_order` to use `UpdateChangeOrderCommand` (or equivalent) for the final status transition.

### 1.2 Success Criteria (Measurable)

**Functional Criteria:**

- [ ] Audit logs created during Change Order status transitions VERIFIED BY: `test_change_order_audit_log.py` pass
- [ ] Schedule Baseline creation correctly updates Cost Element FK VERIFIED BY: `test_schedule_baseline_ensure_exists_creates_baseline_when_missing` pass
- [ ] Change Order Merge correctly updates status to "Implemented" VERIFIED BY: `test_change_order_merge_endpoint.py` pass

**Technical Criteria:**

- [ ] **Zero** direct `session.add` calls in `ChangeOrderService` related to `ChangeOrderAuditLog`. VERIFIED BY:

  ```bash
  grep -n "session.add.*ChangeOrderAuditLog" app/services/change_order_service.py
  # Expected: 0 results
  ```

- [ ] **Zero** direct `session.flush` calls in `ScheduleBaselineService` for `CostElement` updates. VERIFIED BY:

  ```bash
  grep -n "session.flush" app/services/schedule_baseline_service.py
  # Expected: 0 results
  ```

- [ ] `ChangeOrderService.merge_change_order` uses a Command for status update. VERIFIED BY: Code Review
- [ ] Code Quality: mypy strict + ruff clean VERIFIED BY: CI pipeline

**TDD Criteria:**

- [ ] New Commands have unit tests (`tests/unit/core/commands/`)
- [ ] Refactored Services pass existing unit/integration tests

### 1.3 Scope Boundaries

**In Scope:**

- `ChangeOrderService`: Audit logging and Merge status update.
- `ScheduleBaselineService`: CostElement FK update.
- `ForecastService`: CostElement FK update.
- Creating/Updating Commands in `app/core/commands.py` (or feature-specific command modules).

**Out of Scope:**

- Refactoring the entire `ChangeOrderService`.
- Changing the database schema.
- Frontend changes.

---

## Phase 2: Work Decomposition

### 2.1 Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
| - | ---- | ----- | ------------ | ---------------- | -- |
| 1 | Create `CreateChangeOrderAuditLogCommand` | `app/core/versioning/commands.py` | None | Unit test passes | Low |
| 2 | Refactor `ChangeOrderService` audit logging | `app/services/change_order_service.py` | Task 1 | `test_change_order_audit_log` passes, no `session.add(audit)` | Medium |
| 3 | Create `LinkCostElementtoBaselineCommand` | `app/core/versioning/commands.py` | None | Unit test passes | Low |
| 4 | Refactor `ScheduleBaselineService` side-effect | `app/services/schedule_baseline_service.py` | Task 3 | `test_schedule_baseline*.py` passes, no `session.flush` | Medium |
| 5 | Refactor `ForecastService` side-effect | `app/services/forecast_service.py` | Task 3 | Integration tests pass | Medium |
| 6 | Create `UpdateChangeOrderStatusCommand` + Refactor `merge_change_order` | `app/core/versioning/commands.py`, `app/services/change_order_service.py` | None | `test_change_order_merge` passes, use Command | Medium |

### 2.2 Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| -------------------- | ------- | --------------------------- | ----------------- |
| Audit logs via Command | T-001 | `tests/unit/services/test_change_order_audit_log.py` | Status change creates audit entry (unchanged external behavior) |
| Audit Command Isolation | T-002 | `tests/unit/core/test_commands.py` | `CreateChangeOrderAuditLogCommand` persists entry |
| Baseline Link Persistence | T-003 | `tests/unit/services/test_schedule_baseline_service.py` | Creating baseline updates CostElement FK (unchanged external behavior) |
| Baseline Command Isolation | T-004 | `tests/unit/core/test_commands.py` | `LinkCostElementCommand` updates FK |

---

## Phase 3: Test Specification

### 3.1 Test Hierarchy

```text
├── Unit Tests (tests/unit/)
│   ├── core/commands/test_audit_commands.py (NEW)
│   ├── core/commands/test_link_commands.py (NEW)
│   └── services/ (Existing tests must pass)
└── Integration Tests (tests/integration/)
    └── (Existing tests must pass)
```

### 3.2 Test Cases (New Commands)

| Test ID | Test Name | Criterion | Type | Expected Result |
| ------- | ----------------------------------------------- | --------- | ---- | --------------- |
| T-NEW-1 | `test_audit_command_persists_entry` | AC-2 | Unit | `ChangeOrderAuditLog` added to session |
| T-NEW-2 | `test_link_command_updates_fk` | AC-4 | Unit | `CostElement.schedule_baseline_id` updated |
| T-NEW-3 | `test_update_change_order_status_command` | AC-3 | Unit | `ChangeOrder.status` updated via Command |

### 3.3 Test Infrastructure Needs

- Existing `db_session` fixture.
- No new infrastructure needed.

---

## Phase 4: Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| ----------- | --------------- | ------------ | ------------ | ---------- |
| Regression | Breaking existing audit log flow | Low | Med | Run `test_change_order_audit_log.py` before/after |
| Circular Dep | Service <-> Command dependencies | Low | Med | Keep Commands pure (no Service injection) |
| State | Detached instances in Commands | Med | Med | Ensure Commands receive attached instances or IDs |

---

## Phase 5: Prerequisites & Dependencies

- [x] Architecture Analysis completed
- [x] Existing tests identified (`test_change_order_audit_log.py`, `test_schedule_baseline_service.py`)
- [ ] **Baseline Test Verification** (MUST RUN BEFORE STARTING REFACTORING):

  ```bash
  cd backend
  uv run pytest tests/unit/services/test_change_order_audit_log.py -v
  uv run pytest tests/unit/services/test_schedule_baseline_service.py -v
  uv run pytest tests/integration/test_change_order_service_integration.py -v
  ```

  **Acceptance**: All tests must pass before proceeding to Task 1.
