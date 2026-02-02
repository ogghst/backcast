# PLAN: Fix Merge Temporal Consistency Tests

**Iteration:** 2026-01-28-merge-temporal-consistency
**Date:** 2026-01-28
**Status:** PLAN READY FOR APPROVAL
**Planner:** PDCA Orchestrator
**Based On:** ANALYSIS.md (2026-01-28)

---

## Executive Summary

**Plan Overview:** Fix 3 failing integration tests in `test_change_order_workflow_full_temporal.py` by correcting test assertions to use proper temporal query semantics.

**Root Cause:** Test design flaw - tests use historical timestamps (`as_of=T1`) to verify post-merge state, which violates Valid Time Travel semantics.

**Solution Strategy:** Fix test assertions to use `get_current()` or post-merge timestamps (Option 1 from analysis).

**Expected Outcome:** All 5 tests passing, no code changes to production merge logic.

---

## Objectives

### Primary Objectives

1. **Fix Test Temporal Semantics** (MUST)
   - Replace incorrect `get_as_of(as_of=T1)` calls with `get_current()`
   - Ensure tests query current state, not historical state
   - Verify merge functionality works as designed

2. **Maintain Test Coverage** (MUST)
   - No regressions in 2 passing tests
   - Cover all merge scenarios
   - Maintain ≥80% coverage threshold

3. **Validate Merge Functionality** (MUST)
   - Confirm merge creates correct versions
   - Verify temporal consistency
   - Check version chain integrity

### Secondary Objectives

4. **Document Test Patterns** (SHOULD)
   - Add comments explaining temporal query choices
   - Document when to use `get_current()` vs `get_as_of()`
   - Provide examples for future tests

5. **Update Test Run Guide** (SHOULD)
   - Document temporal testing best practices
   - Explain Valid Time Travel semantics
   - Add troubleshooting section

---

## Implementation Plan

### Phase 1: Fix Test Assertions (DO THIS FIRST)

**Files to Modify:**
- `backend/tests/integration/test_change_order_workflow_full_temporal.py`

**Specific Changes:**

#### Change Set 1: Lines 276-281 (Temporal Boundary Verification)
```python
# BEFORE (INCORRECT):
co_before = await co_service.get_as_of(
    entity_id=co_id,
    as_of=T1_before,  # ❌ Historical timestamp
    branch="main",
    branch_mode=BranchMode.STRICT,
)

# AFTER (CORRECT):
co_before = await co_service.get_as_of(
    entity_id=co_id,
    as_of=T1_before,  # ✅ CORRECT - verifying zombie check
    branch="main",
    branch_mode=BranchMode.STRICT,
)
# NOTE: This one is CORRECT - it's testing that CO doesn't exist before T1
```

#### Change Set 2: Lines 295-301 (STRICT Mode Verification)
```python
# BEFORE (INCORRECT):
wbe1_co_strict = await wbe_service.get_as_of(
    entity_id=wbe1_id,
    as_of=T1_after,  # ❌ Wrong timestamp context
    branch=source_branch,
    branch_mode=BranchMode.STRICT,
)

# AFTER (CORRECT):
wbe1_co_strict = await wbe_service.get_current(
    root_id=wbe1_id,  # ✅ Use get_current for current state
    branch=source_branch,
)
```

#### Change Set 3: Lines 383-389, 391-397 (Branch Isolation Verification)
```python
# BEFORE (INCORRECT):
wbe1_main = await wbe_service.get_as_of(
    entity_id=wbe1_id,
    as_of=T2,  # ❌ Wrong - T2 is modification time, not query time
    branch="main",
    branch_mode=BranchMode.STRICT,
)

# AFTER (CORRECT):
wbe1_main = await wbe_service.get_current(
    root_id=wbe1_id,  # ✅ Use get_current for current state
    branch="main",
)
assert wbe1_main.name == "Assembly Station 1"  # Unchanged
```

#### Change Set 4: Lines 431-437, 440-446 (Post-Merge Verification)
```python
# BEFORE (INCORRECT):
wbe1_main_merged = await wbe_service.get_as_of(
    entity_id=wbe1_id,
    as_of=T3,  # ❌ T3 is merge time, but we need current state
    branch="main",
    branch_mode=BranchMode.STRICT,
)

# AFTER (CORRECT):
wbe1_main_merged = await wbe_service.get_current(
    root_id=wbe1_id,  # ✅ Use get_current for current state
    branch="main",
)
assert wbe1_main_merged.name == "Assembly Station 1 - EXPANDED"
```

#### Change Set 5: Lines 820-827 (Time Travel Verification)
```python
# BEFORE (INCORRECT):
ce1_at_t1 = await ce_service.get_as_of(
    entity_id=ce1_id,
    as_of=T1_after,  # ❌ This CORRECTLY returns pre-merge state
    branch="main",
    branch_mode=BranchMode.STRICT,
)
assert ce1_at_t1.budget_amount == Decimal("100000.00")  # ❌ Wrong expectation

# AFTER (CORRECT - REDESIGN TEST):
# Option A: Remove this assertion (temporal correctness means T1 shows pre-merge)
# Option B: Add comment explaining why this is pre-merge state

# RECOMMENDED: Add explanatory comment
# Note: get_as_of(as_of=T1_after) returns pre-merge state because
# merge happens at 'now' (after T1). This is CORRECT temporal behavior.
ce1_at_t1 = await ce_service.get_as_of(
    entity_id=ce1_id,
    as_of=T1_after,
    branch="main",
    branch_mode=BranchMode.STRICT,
)
assert ce1_at_t1.budget_amount == Decimal("100000.00")  # ✅ Pre-merge (correct)

# Verify current state has merged values
ce1_current = await ce_service.get_current(
    root_id=ce1_id,
    branch="main",
)
assert ce1_current.budget_amount == Decimal("150000.00")  # ✅ Post-merge (correct)
```

### Phase 2: Fix Workflow Validation Issue

**Files to Modify:**
- `backend/tests/integration/test_change_order_workflow_full_temporal.py`

**Specific Changes:**

#### Change Set 6: Line 247-256 (Status Transition)
```python
# BEFORE (INCORRECT):
co_approved = await co_service.update_change_order(
    change_order_id=co_id,
    change_order_in=ChangeOrderUpdate(status="Approved"),  # ❌ Invalid transition
    actor_id=actor_id,
    control_date=T2,
)

# AFTER (CORRECT):
co_approved = await co_service.update_change_order(
    change_order_id=co_id,
    change_order_in=ChangeOrderUpdate(status="Submitted for Approval"),  # ✅ Valid transition
    actor_id=actor_id,
    control_date=T2,
)

# Then approve in a separate step:
co_approved2 = await co_service.update_change_order(
    change_order_id=co_id,
    change_order_in=ChangeOrderUpdate(status="Approved"),
    actor_id=actor_id,
    control_date=T2,
)
```

**Alternative:** Check workflow service for valid transitions and update test accordingly.

### Phase 3: Documentation Updates

**Files to Create/Modify:**
- `backend/tests/integration/TEST_RUN_GUIDE.md` (update)
- Add comments in test file explaining temporal choices

**Documentation Tasks:**
1. Add section: "Temporal Testing Best Practices"
2. Document when to use `get_current()` vs `get_as_of()`
3. Explain Valid Time Travel semantics
4. Add troubleshooting guide for temporal issues

---

## Detailed Task Breakdown

### Task 1: Fix Test Temporal Assertions
**Owner:** Backend Developer
**Estimated Effort:** 2 hours
**Priority:** HIGH (MUST)

**Steps:**
1. Read test file and identify all `get_as_of` calls
2. Determine which should use `get_current()` instead
3. Replace incorrect `get_as_of` calls with `get_current()`
4. Update assertions to match correct temporal behavior
5. Add explanatory comments where needed

**Acceptance Criteria:**
- [ ] All temporal assertions use correct semantics
- [ ] No use of historical timestamps for current state verification
- [ ] Comments explain temporal choices

---

### Task 2: Fix Workflow Validation
**Owner:** Backend Developer
**Estimated Effort:** 1 hour
**Priority:** MEDIUM (SHOULD)

**Steps:**
1. Check valid status transitions in workflow service
2. Update test to use valid transitions
3. Verify multi-step status changes work correctly

**Acceptance Criteria:**
- [ ] Test uses valid status transitions
- [ ] Multi-step workflow works
- [ ] No workflow validation errors

---

### Task 3: Run Tests and Verify
**Owner:** Backend Developer / QA
**Estimated Effort:** 1 hour
**Priority:** HIGH (MUST)

**Steps:**
1. Run all 5 tests in temporal test file
2. Verify all pass
3. Run full test suite to check for regressions
4. Check code coverage (≥80%)

**Acceptance Criteria:**
- [ ] All 5 tests in file pass
- [ ] No regressions in other tests
- [ ] Coverage ≥80%

---

### Task 4: Document Changes
**Owner:** Technical Writer / Developer
**Estimated Effort:** 1 hour
**Priority:** MEDIUM (SHOULD)

**Steps:**
1. Update TEST_RUN_GUIDE.md with temporal testing patterns
2. Add inline comments in test file
3. Create troubleshooting section

**Acceptance Criteria:**
- [ ] TEST_RUN_GUIDE.md updated
- [ ] Inline comments added
- [ ] Troubleshooting guide created

---

## Dependencies

### Task Dependencies
- **Task 1** (Fix Temporal Assertions) - NO DEPENDENCIES
- **Task 2** (Fix Workflow Validation) - NO DEPENDENCIES
- **Task 3** (Run Tests) - DEPENDS ON: Task 1, Task 2
- **Task 4** (Document) - DEPENDS ON: Task 1, Task 2, Task 3

### External Dependencies
- None

### Blocking Issues
- None

---

## Risk Management

### Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Fixing tests reveals actual merge bugs | LOW | HIGH | Investigation already complete; merge works correctly |
| Workflow fix breaks test logic | MEDIUM | MEDIUM | Check workflow service for valid transitions first |
| Code coverage drops below 80% | LOW | MEDIUM | Add coverage for any missing scenarios |
| Documentation incomplete | LOW | LOW | Allocate sufficient time for documentation |

### Contingency Plans

**If tests still fail after fixes:**
1. Run debug script to verify merge behavior
2. Check if issue is in merge logic (not test design)
3. Re-run analysis with new data

**If workflow fix is complex:**
1. Skip workflow fix for now
2. Focus on temporal assertion fixes
3. Create separate task for workflow validation

**If coverage drops:**
1. Identify missing coverage areas
2. Add test cases as needed
3. Document any excluded scenarios

---

## Quality Gates

### Entry Criteria (Before Starting)
- [x] Analysis complete
- [x] Root cause identified
- [x] Solution approach approved
- [x] Test environment available

### Exit Criteria (After Completion)
- [ ] All 5 tests passing
- [ ] No regressions in test suite
- [ ] Code coverage ≥80%
- [ ] Documentation updated
- [ ] Code passes quality checks (mypy, ruff)

---

## Success Metrics

### Primary Metrics
1. **Test Pass Rate:** 100% (5/5 tests passing)
2. **Test Coverage:** ≥80% for merge-related code
3. **Code Quality:** Zero mypy/ruff errors

### Secondary Metrics
1. **Documentation Completeness:** All temporal patterns documented
2. **Maintainability:** Clear comments explaining temporal choices
3. **Performance:** No significant test runtime increase

---

## Timeline

### Sprint Schedule

**Day 1 (Today):**
- Morning: Task 1 (Fix Temporal Assertions) - 2 hours
- Afternoon: Task 2 (Fix Workflow Validation) - 1 hour

**Day 1 (Evening):**
- Task 3 (Run Tests and Verify) - 1 hour

**Day 2 (Tomorrow):**
- Morning: Task 4 (Document Changes) - 1 hour
- Afternoon: Buffer time for unforeseen issues - 2 hours

**Total Estimated Time:** 5-7 hours

### Milestones
- ✅ **Milestone 1:** Analysis complete (DONE)
- ⏳ **Milestone 2:** Test fixes complete (IN PROGRESS)
- ⏳ **Milestone 3:** All tests passing (PENDING)
- ⏳ **Milestone 4:** Documentation complete (PENDING)

---

## Resources

### Team Allocation
- **Backend Developer:** 1 person (implementation and testing)
- **Technical Writer:** 0.5 person (documentation - can be same as developer)

### Tools and Environment
- Python 3.12+ with pytest
- PostgreSQL 15+ (running via docker-compose)
- Virtual environment (`.venv`)
- IDE with Python support

### References
- **Analysis Report:** `ANALYSIS.md` (this directory)
- **Temporal Query Reference:** `docs/02-architecture/cross-cutting/temporal-query-reference.md`
- **Test File:** `backend/tests/integration/test_change_order_workflow_full_temporal.py`
- **Backend Coding Standards:** `docs/02-architecture/backend/coding-standards.md`

---

## Approval

**Prepared By:** PDCA Orchestrator
**Date:** 2026-01-28
**Status:** ✅ READY FOR DO PHASE

**Approved By:** _________________ **Date:** _________

---

## Appendix

### A. Test File Locations

**Test File:** `backend/tests/integration/test_change_order_workflow_full_temporal.py`

**Test Methods:**
1. `test_full_workflow_with_temporal_dates` (lines 42-493)
2. `test_temporal_boundary_co_creation` (lines 495-560)
3. `test_branch_isolation_with_temporal_queries` (lines 562-680)
4. `test_merge_with_cost_registrations_and_progress` (lines 684-828)
5. `test_merge_temporal_consistency` (lines 830-949)

### B. Key Code Locations

**Merge Command:** `backend/app/core/branching/commands.py` (lines 309-368)
**Branchable Service:** `backend/app/core/branching/service.py` (lines 276-287)
**Change Order Service:** `backend/app/services/change_order_service.py` (lines 570-686)

### C. Temporal Semantics Quick Reference

**`get_current(entity_id)`:**
- Returns the current active version
- Uses `clock_timestamp()` for temporal query
- Always returns latest version
- Use for: Verifying current state after operations

**`get_as_of(entity_id, as_of=T)`:**
- Returns the version valid at time T
- Uses explicit timestamp for temporal query
- Returns historical state if T < merge_time
- Use for: Time-travel queries, historical analysis, zombie checks

**When to Use Which:**
- Use `get_current()` for post-operation verification
- Use `get_as_of()` for time-travel scenarios
- Never use `get_as_of(as_of=past)` to verify current state

---

**END OF PLAN**
