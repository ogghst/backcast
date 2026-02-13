# Plan: Epic 6 - Branch Archival (E06-U08)

**Iteration:** 2026-02-07-epic-06-branch-archival
**Status:** 🏗️ Approved

---

## 1. Scope & Success Criteria

### 1.1 Approved Approach

- **Selected Option:** Option 1 (Explicit `archive` method in `ChangeOrderService`)
- **Key Decisions:**
  - Use `BranchService.soft_delete` to hide branches.
  - Only allow archival for "Implemented" or "Rejected" Change Orders.

### 1.2 Success Criteria

- [ ] `archive_change_order_branch` implemented in `ChangeOrderService`
- [ ] Integration test verifies:
  - Successfully archived branch is hidden from standard lists.
  - Archival fails for active (Draft/Submitted/Approved) Change Orders.
  - Archived branch is still accessible via time-travel queries.

---

## 2. Work Decomposition

| # | Task | Files | Dependencies | Verification |
|---|---|---|---|---|
| 1 | Create Integration Test | `tests/integration/test_change_order_branch_archive.py` | None | Test fails (RED) |
| 2 | Implement Archive Method | `backend/app/services/change_order_service.py` | Task 1 | Test passes (GREEN) |

---

## 3. Test Specification

### 3.1 Integration Tests

**File:** `tests/integration/test_change_order_branch_archive.py`

| Test ID | Test Name | Criterion | Expected Result |
|---|---|---|---|
| T-001 | `test_archive_implemented_change_order` | Valid Archival | Branch hidden from `get_branches`, visible in `get_branches_as_of` |
| T-002 | `test_archive_active_change_order_fails` | Invalid State | `ValueError` raised |
| T-003 | `test_archive_rejected_change_order` | Valid Archival | Branch hidden |

---

## 4. Risks

- **Risk:** `BranchService.soft_delete` might not be exposed or working as expected.
- **Mitigation:** Verify `BranchService` inheritance from `TemporalService` during implementation.
