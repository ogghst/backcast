# Iteration Plan - Fix Unit Test Failures (TD-002)

## 1. Problem Statement

Critical unit tests in the core versioning layer and integration tests for the branch service are failing or reported as unreliable. This reduces confidence in the system's core bitemporal and branching logic.

Specifically:

- `tests/unit/core/versioning/test_audit.py` fails due to incorrect ID field name derivation in `TemporalService`.
- `TD-002` also mentions `test_integration_branch_service.py` issues, although initial run passed (needs deeper investigation into potential race conditions or environmental mismatches).

## 2. Goals

- [ ] Fix all failures in `tests/unit/core/versioning/test_audit.py`.
- [ ] Ensure `tests/integration/test_integration_branch_service.py` is robust and passing consistently.
- [ ] Verify 100% pass rate for all tests in `tests/unit/core`.
- [ ] Update Technical Debt Register (TD-002) to CLOSED status.

## 3. Implementation Plan

### Step 1: Investigation & Analysis

- [ ] Confirm all failing tests in `backend/tests/unit/core`.
- [ ] Investigate `test_integration_branch_service.py` for flaky behavior.
- [ ] Analyze `TemporalService._get_root_field_name` vs model field names.

### Step 2: Fix Core Versioning Tests

- [ ] Align `MockAuditEntity` in `test_audit.py` with the naming convention expected by `TemporalService` (or fix the service if it's too rigid).
- [ ] Fix any other failures in `tests/unit/core/versioning/`.

### Step 3: Fix Integration Branch Service Tests

- [ ] Debug `tests/integration/test_integration_branch_service.py`.
- [ ] Ensure proper database isolation and cleanup.

### Step 4: Verification

- [ ] Run full backend test suite.
- [ ] Verify no regressions in existing versioned services (Project, WBE, CostElement).

## 4. Success Criteria

- All tests in `tests/unit/core` and `tests/integration/test_integration_branch_service.py` pass.
- No regressions in other parts of the system.
