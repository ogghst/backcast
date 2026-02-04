# DO Phase: Backend Implementation - E04-U04

**Date:** 2026-02-03
**User Story:** E04-U04 - Allocate Revenue across WBEs
**Approach:** Option 1 - Service-Layer Validation with Error Enforcement
**Executor:** pdca-backend-do-executor

---

## Progress Summary

| Metric | Count |
|--------|-------|
| Tasks Completed | 7 of 9 (BE-001 through BE-007) |
| Tests Written | 3 unit tests (simplified from 9) |
| Tests Passing | 1 of 3 |
| Files Modified | 4 (model, schemas, service, migration) |
| MyPy Errors | 3 pre-existing (not from our changes) |
| Ruff Errors | 0 (all fixed) |

---

## TDD Cycle Log

| Test Name | RED Reason | GREEN Implementation | REFACTOR Notes | Date |
|-----------|------------|---------------------|----------------|------|
| T-001 Valid allocation | N/A (test written after GREEN) | Validation logic with `flush()` to ensure new WBE visible | Added `is_not(None)` filter to skip unallocated WBEs | 2026-02-03 |
| T-002 Exceeds contract | N/A | Validation raises ValueError with formatted message | None | 2026-02-03 |
| T-004 None contract value | N/A | Validation returns early if `contract_value is None` | None | 2026-02-03 |

**Status:** ⚠️ **INCOMPLETE** - Tests T-001 and T-002 failing due to test logic issues (test may need adjustment for incremental allocation workflow)

---

## Files Changed

### 1. Database Migration
**File:** `backend/alembic/versions/20260203_add_revenue_allocation_to_wbes.py`
- Created migration to add `revenue_allocation DECIMAL(15, 2)` column to wbes table
- Nullable with default None for backward compatibility
- Downgrade method removes column cleanly
- Status: ✅ Applied successfully

### 2. WBE Model
**File:** `backend/app/models/domain/wbe.py`
- Added `revenue_allocation: Mapped[Decimal | None]` field (line 66-68)
- Uses `mapped_column(DECIMAL(15, 2), nullable=True, default=None)`
- Status: ✅ Complete

### 3. WBE Schemas
**File:** `backend/app/models/schemas/wbe.py`
- Updated `WBEBase` to include `revenue_allocation: Decimal | None` with `ge=0` validation (line 19-21)
- Updated `WBEUpdate` to include `revenue_allocation: Decimal | None` (line 49)
- Status: ✅ Complete

### 4. WBE Service
**File:** `backend/app/services/wbe.py`
- Added `_validate_revenue_allocation()` method (lines 37-108)
  - Queries project contract_value
  - Sums WBE revenue allocations (excluding None values)
  - Validates exact match with 2-decimal precision
  - Raises ValueError with clear message showing totals and difference
  - Skips validation if contract_value is None or total_allocated is 0
- Integrated validation in `create_wbe()` method (lines 447-507)
  - Calls validation after WBE creation
  - Uses `flush()` to ensure new WBE visible to validation query
- Integrated validation in `update_wbe()` method (lines 510-585)
  - Passes `exclude_wbe_id` to prevent double-counting old value
  - Validates after update
- Status: ⚠️ Complete but tests failing

---

## Decisions Made

### Decision 1: Skip Validation for Unallocated WBEs
**Reason:** Allow incremental workflow where WBEs are created without revenue, then updated later.
**Implementation:** Added `.is_not(None)` filter to validation query to only sum WBEs with revenue_allocation set.
**Impact:** Users can create WBEs first, then allocate revenue in a second step.

### Decision 2: Allow Zero Total (Initial State)
**Reason:** When no WBEs have revenue allocated yet, validation should pass.
**Implementation:** Added early return if `total_allocated == Decimal("0")`.
**Impact:** Supports incremental allocation workflow.

### Decision 3: Flush Before Validation
**Reason:** Ensure newly created WBE is visible to validation query.
**Implementation:** Added `await self.session.flush()` after `cmd.execute()` and before validation.
**Impact:** Validation sees the complete state including the new WBE.

### Decision 4: Exact Match Validation (Option 1)
**Reason:** Following approved approach from plan document (FR 15.4 requirement).
**Implementation:** Use `quantize(Decimal("0.01"))` comparison for exact match.
**Impact:** Strict enforcement - revenue allocations must equal contract value at all times once allocation begins.

---

## Quality Gate Results

### MyPy (Type Checking)
```bash
uv run mypy app/services/wbe.py --no-error-summary
```
**Result:** ⚠️ **3 errors** - All pre-existing, not from our changes:
- Line 158: Type variable issue with CreateVersionCommand (pre-existing)
- Line 808: Missing type annotation (pre-existing)
- Line 882: Signature incompatibility with supertype (pre-existing)

### Ruff (Linting)
```bash
uv run ruff check app/services/wbe.py app/models/domain/wbe.py app/models/schemas/wbe.py --fix
```
**Result:** ✅ **All checks passed!**
- Fixed 5 auto-fixable errors (import sorting, unused imports)

### Test Coverage
```bash
uv run pytest tests/unit/services/test_wbe_service_revenue.py --cov=app/services/wbe
```
**Result:** ⚠️ **INCOMPLETE** - 1 of 3 tests passing
- ✅ T-004: None contract value skips validation (PASS)
- ❌ T-001: Valid allocation exact match (FAIL - test hanging)
- ❌ T-002: Exceeds contract raises error (FAIL)

---

## Deviations from Plan

### Deviation 1: Simplified Test Suite
**Planned:** 9 comprehensive unit tests (T-001 through T-009)
**Actual:** 3 simplified unit tests written
**Reason:** Complexity of test fixture setup and test logic issues
**Impact:** Reduced test coverage for edge cases (branch isolation, soft-deleted WBEs, decimal precision, sequential creates)

### Deviation 2: Test Logic Issue
**Planned:** T-001 creates WBEs incrementally with revenue (50,000 + 50,000 = 100,000)
**Actual:** Test fails/hangs due to validation blocking incremental allocation
**Root Cause:** Option 1 (strict validation) doesn't support incremental allocation workflow
**Workaround Attempted:** Modified test to create WBEs without revenue first, then update them
**Status:** Still failing - tests may need fundamental redesign or Option 2 approach

### Deviation 3: Incomplete Integration Tests
**Planned:** API integration tests (T-006 through T-009) for versioning and branch isolation
**Actual:** Not written - unit tests not passing yet
**Reason:** Foundation (unit tests) not stable enough to build upon

---

## Lessons Learned

### 1. Strict Validation vs. Incremental Workflow
**Issue:** Option 1 (exact match validation) conflicts with natural workflow of allocating revenue incrementally across multiple WBEs.
**Observation:** Users expect to create WBEs first, then allocate revenue gradually. Strict validation blocks this.
**Recommendation:** Consider Option 2 (warning-only mode) for better UX, or add "validation bypass" flag for initial allocation phase.

### 2. Test Design for TDD with Validation
**Issue:** Tests must account for validation logic timing (before/after entity creation).
**Learning:** Need `flush()` to ensure entity visible to validation queries.
**Recommendation:** Document test patterns for validation logic in TDD workflow.

### 3. Fixture Complexity in Async Tests
**Issue:** Setting up Projects, WBEs, and users in async tests requires careful fixture management.
**Learning:** `db_session` fixture is key, not `session`. Use `uuid4()` inline for test users.
**Recommendation:** Create helper fixtures for common test data (project_with_contract, wbe_with_revenue, etc.)

### 4. MyPy Type Variables in Generic Commands
**Issue:** Pre-existing MyPy errors with `CreateVersionCommand[WBE]` type variable.
**Learning:** Generic command patterns have type-checking challenges in strict mode.
**Recommendation:** Review command pattern typing for better MyPy compatibility.

---

## Next Steps (Required for Completion)

### Priority 1: Fix Failing Unit Tests
- [ ] Debug why T-001 test hangs (transaction issue?)
- [ ] Verify T-002 error message format matches expectations
- [ ] Add remaining 6 unit tests (T-005 through T-009) once basic tests pass

### Priority 2: Complete Integration Tests
- [ ] Write T-006: Create WBE API endpoint with revenue validation
- [ ] Write T-007: Update WBE API endpoint with revenue validation
- [ ] Write T-008: Versioning history query
- [ ] Write T-009: Branch isolation test

### Priority 3: Achieve 80% Test Coverage
- [ ] Run full test suite with coverage report
- [ ] Add tests for edge cases (None revenue, decimal precision, soft-delete)

### Priority 4: Code Review
- [ ] Self-review validation logic for edge cases
- [ ] Verify all docstrings follow LLM-optimized format
- [ ] Ensure Decimal.quantize() used consistently

---

## Known Issues

### Issue 1: Test Hanging
**Symptom:** T-001 test hangs indefinitely
**Suspected Cause:** Transaction deadlock or infinite loop in validation
**Next Debug Step:** Add logging to validation query, check for session management issues
**Priority:** HIGH - blocks all other testing

### Issue 2: Incremental Allocation Workflow
**Symptom:** Tests show that creating WBEs with revenue one-by-one fails validation
**Root Cause:** Option 1 enforces exact match at all times, not allowing partial allocation
**Proposed Solution:** Use Option 2 (warning-only) or add "allocate_revenue=False" parameter to skip validation during bulk creation
**Priority:** MEDIUM - UX concern, not functional blocker

---

## API Contract Changes

### New Field: `revenue_allocation`
**Type:** `Decimal | None`
**Precision:** DECIMAL(15, 2) (up to 999,999,999,999.99)
**Validation:** `ge=0` (non-negative)
**Default:** `None`
**Endpoints Affected:**
- `POST /api/v1/wbes` - WBECreate schema includes revenue_allocation
- `PUT /api/v1/wbes/{id}` - WBEUpdate schema includes revenue_allocation
- `GET /api/v1/wbes` - WBERead schema includes revenue_allocation

### Validation Error Response
**HTTP Status:** 400 Bad Request (if validation fails)
**Error Message Format:**
```json
{
  "detail": "Total revenue allocation (€50,000.00) does not match project contract value (€100,000.00). Difference: €50,000.00"
}
```

---

## References

- [Plan Document](./01-plan.md) - Detailed task breakdown and test specifications
- [Analysis Document](./00-analysis.md) - Option comparison and validation pseudocode
- [Backend Coding Standards](../../../../02-architecture/backend/coding-standards.md) - MyPy, Ruff, docstring requirements

---

**Status:** ⚠️ **INCOMPLETE** - Backend foundation implemented but tests failing. Requires debugging before CHECK phase.

**Recommendation:** Pause for human review of test strategy (Option 1 vs Option 2) before proceeding with test fixes.
