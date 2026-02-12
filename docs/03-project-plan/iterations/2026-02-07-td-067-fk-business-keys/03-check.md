# Check: TD-067 FK Constraint: Business Key vs Primary Key in Temporal Entities

**Completed:** 2026-02-07
**Based on:** [02-do.md](./02-do.md)

---

## 1. Acceptance Criteria Verification

| Acceptance Criterion | Test Coverage | Status | Evidence | Notes |
| -------------------- | ------------- | ------ | -------- | ----- |
| `ChangeOrder.assigned_approver_id` holds `user_id` (Business Key) | T-001 | ✅ | Integration test verification | Confirmed `user_id` persistence |
| Database FK constraint removed | T-002 | ✅ | Migration `03b4089c` & Test | Constraint dropped in migration |
| Assignment persists after User update | T-001 | ✅ | Integration test verification | Verified across V1 -> V2 update |
| Service validates `user_id` existence | T-002 | ✅ | Service code & Test | Validated at app level (no DB FK) |

**Status Key:** ✅ Fully met | ⚠️ Partially met | ❌ Not met

---

## 2. Test Quality Assessment

**Coverage:**

- Coverage percentage: ~39% (Service layer)
- Note: Low coverage is expected as we only ran specific integration tests for this feature, not the full suite.
- Uncovered critical paths: None related to this feature.

**Quality Checklist:**

- [x] Tests isolated and order-independent
- [x] No slow tests (>1s)
- [x] Test names communicate intent
- [x] No brittle or flaky tests

---

## 3. Code Quality Metrics

| Metric | Threshold | Actual | Status |
| ------ | --------- | ------ | ------ |
| Tests Passing | 100% | 100% (2/2) | ✅ |
| Type Hints | 100% | 100% | ✅ |
| Ruff Errors | 0 | 0 | ✅ |
| MyPy Errors | 0 | 4 | ⚠️ |

*Note: MyPy errors are pre-existing in `ChangeOrderService` and unrelated to TD-067 changes.*

---

## 4. Security & Performance

**Security:**

- [x] Input validation implemented (Pydantic + Service)
- [x] No injection vulnerabilities (SQLAlchemy ORM)
- [x] Proper error handling (ValueError on invalid input)

**Performance:**

- [x] Database queries optimized: No new N+1 introduced
- [x] Removal of FK constraint slightly improves write performance (no FK check overhead)

---

## 5. Integration Compatibility

- [x] API contracts maintained
- [x] Database migrations compatible (handled via Alembic)
- [x] No breaking changes to public interfaces
- [x] Backward compatibility verified (existing data migrated)

---

## 6. Retrospective

### What Went Well

- **TDD Approach**: Writing the test first immediately revealed the discrepancy between the schema (which ignores `assigned_approver_id`) and the model/database.
- **Migration Strategy**: The pre-existing migration was correct and aligned with the architectural pattern.

### What Went Wrong

- **Test Design Flaw**: The initial test attempted to set `assigned_approver_id` via `ChangeOrderCreate` Pydantic model, but the schema design intentionally excludes this field to enforce workflow-based assignment. This caused the test to fail (silently ignoring the field) until debugged.

---

## 7. Root Cause Analysis

| Problem | Root Cause | Preventable? | Prevention Strategy |
| ------- | ---------- | ------------ | ------------------- |
| Initial test failed to assign approver | `ChangeOrderCreate` schema excludes `assigned_approver_id`, but test assumed it was present. | Yes | Check Pydantic schemas definition before writing tests, or use `model_dump()` to verify data being passed. |

---

## 8. Improvement Options

| Issue | Option A (Quick) | Option B (Thorough) | Option C (Defer) | Recommended |
| ----- | ---------------- | ------------------- | ---------------- | ----------- |
| MyPy Errors in Service | Ignore (out of scope) | Fix generic type checking issues | Defer to tech debt sprint | ⭐ C |

**Decision Required:** Proceed with current implementation.

---

## 9. Stakeholder Feedback

- **Developer observations**: The "no FK for bitemporal entities" pattern is now consistently applied to `ChangeOrder` as well, matching `WBE` and `CostElement`.
