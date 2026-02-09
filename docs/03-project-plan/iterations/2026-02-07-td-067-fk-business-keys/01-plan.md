# Plan: TD-067 FK Constraint: Business Key vs Primary Key in Temporal Entities

**Status**: [COMPLETE]
**Date**: 2026-02-07
**Author**: Antigravity (Backend Developer)
**Iteration**: 2026-02-07-td-067-fk-business-keys

## 1. Scope & Success Criteria

### 1.1 Approved Approach Summary

**Selected Option:** Option 1 (Standard Application-Level Integrity)

We will remove the incorrect database Foreign Key constraint on `ChangeOrder.assigned_approver_id` (which points to `users.id` / Version ID) and migrate existing data to point to `users.user_id` (Business Key). This aligns `ChangeOrder` with the established pattern used by `WBE` and `CostElement` for bitemporal relationships.

### 1.2 Success Criteria (Measurable)

**Functional Criteria:**

- [x] `ChangeOrder.assigned_approver_id` columns in DB hold `user_id` (Business Key) values, not `id` (Version ID). VERIFIED BY: Database Audit
- [x] Database Foreign Key constraint `fk_change_orders_assigned_approver` is REMOVED. VERIFIED BY: Schema Inspection
- [x] Assigning a Change Order to a User persists correct assignment even after the User is updated (creating a new Version ID). VERIFIED BY: Integration Test
- [x] `ChangeOrderService` correctly validates `user_id` existence during assignment. VERIFIED BY: Service-level validation in workflow methods

**Technical Criteria:**

- [x] No regression in existing Change Order or User tests. VERIFIED BY: Test Suite
- [x] Codebase consistency: `ChangeOrder` model matches `WBE`/`CostElement` pattern. VERIFIED BY: Code Review

**TDD Criteria:**

- [x] Zombie/Update Persistence test written before implementation.
- [x] Test coverage for Change Order assignment logic verified.

### 1.3 Scope Boundaries

**In Scope:**

- Database migration (schema + data).
- `ChangeOrder` model verification.
- `ChangeOrderService` logic update (if needed) for validation.
- New integration tests for assignment persistence.

**Out of Scope:**

- Changes to `User` entity.
- Changes to `WBE` or `CostElement` entities.
- Complex "As Of" query resolution for the *User* entity within the Change Order fetch (retrieving the fetching of the user details is standard `UserService` behavior).

## 2. Work Decomposition

### 2.1 Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Create/Verify Tests** | `tests/integration/test_td_067_assignment_persistence.py` | None | Red failing test confirming the issue | Low |
| 2 | **Database Migration** | `backend/alembic/versions/XXXX_fix_change_order_fk.py` | Task 1 | DB has no FK, data converted | Medium |
| 3 | **Service Layer Update** | `backend/app/services/change_order_service.py` | Task 2 | Assignment uses `user_id` validation | Low |
| 4 | **Model Consistency** | `backend/app/models/domain/change_order.py` | Task 2 | Docs/Comments updated | Low |

### 2.2 Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| :--- | :--- | :--- | :--- |
| Assignment persists after User update | T-001 | `tests/integration/test_td_067_assignment_persistence.py` | `co.assigned_approver_id` remains constant (Business Key) after User triggers new version |
| Assignment validation | T-002 | `tests/unit/test_change_order_service.py` | Rejects assignment if `user_id` does not exist |

## 3. Test Specification

### 3.1 Test Hierarchy

```text
├── Integration Tests (tests/integration/)
│   └── test_td_067_assignment_persistence.py
│       ├── test_assignment_persistence_across_versions
│       └── test_assignment_to_non_existent_user
```

### 3.2 Test Cases

| Test ID | Test Name | Criterion | Type | Expected Result |
| :--- | :--- | :--- | :--- | :--- |
| T-001 | `test_assignment_persistence_across_versions` | AC-1 | Integration | 1. Create User (V1).<br>2. Assign CO to User.<br>3. Update User (V2).<br>4. Fetch CO.<br>5. Assert `assigned_approver_id` == `user.user_id`. |
| T-002 | `test_assign_approver_validation` | AC-2 | Unit/Int | 1. Attempt invalid `user_id`.<br>2. Expect `EntityNotFound` or `ValidationError`. |

### 3.3 Test Infrastructure Needs

- `UserService` and `ChangeOrderService` fixtures.
- DB Session.

## 4. Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| :--- | :--- | :--- | :--- | :--- |
| Data Integrity | Migration fails to match `id` to `user_id` correctly | Low | High | Use strictly joined UPDATE statement; backup if needed (dev env) |
| Logic Regression | Application relies on FK for internal joins | Low | Medium | Verify queries in `ChangeOrderService` don't use implicit joins on this field |

## 5. Prerequisites & Dependencies

- [x] Analysis phase approved
- [ ] Database backup (for prod/staging, n/a for local dev)
