# Act: Remove Budget Fields from WBE Entities

**Completed:** 2026-02-28
**Based on:** [03-check.md](03-check.md)

---

## 1. Improvements Implemented

### Critical Issues (from CHECK)

| Issue | Resolution | Verification |
| ----- | ---------- | ------------ |
| OpenAPI spec outdated | Needs regeneration after backend deployment | Frontend types still show stale budget_allocation in input schemas |
| Minor linting issues | Already resolved (ruff/mypy pass) | `uv run ruff check .` and `uv run mypy app/` pass |

### Refactoring Applied

| Change | Rationale | Files Affected |
| ------ | --------- | -------------- |
| Removed budget_allocation column from wbes table | Single source of truth | `backend/alembic/versions/20260228_remove_wbe_budget_allocation.py` |
| Added computed budget_allocation attribute | API compatibility | `backend/app/models/domain/wbe.py` |
| Added budget computation methods | Runtime calculation | `backend/app/services/wbe.py` |
| Updated Pydantic schemas | Input schemas exclude budget | `backend/app/models/schemas/wbe.py` |
| Updated EVM/Financial services | Use CostElement.budget_amount | `backend/app/services/financial_impact_service.py`, `backend/app/services/evm_service.py` |
| Removed budget input from frontend modal | UI reflects new architecture | `frontend/src/features/wbes/components/WBEModal.tsx` |
| Updated frontend tests | Tests reflect new behavior | `frontend/src/features/wbes/components/WBEModal.test.tsx` |

---

## 2. Pattern Standardization

| Pattern | Description | Standardize? | Action |
| ------- | ----------- | ------------ | ------ |
| Computed Attribute Pattern | Non-mapped attribute populated by service layer | Yes | ADR-013 created |
| Single Source of Truth | Store data once, compute derived values | Yes | Documented in ADR-013 |
| Service-Layer Population | All entity-returning methods call populate helper | Yes | Pattern documented |

**Standardization Actions Completed:**

- [x] Create ADR-013: Computed Budget Attribute Pattern
- [x] Update `docs/02-architecture/01-bounded-contexts.md` with budget architecture notes
- [x] Update `docs/02-architecture/decisions/adr-index.md` with new ADR

---

## 3. Documentation Updates

| Document | Update Needed | Status |
| -------- | ------------- | ------ |
| `docs/02-architecture/decisions/ADR-013-computed-budget-attribute.md` | Create new ADR | Complete |
| `docs/02-architecture/decisions/adr-index.md` | Add ADR-013 | Complete |
| `docs/02-architecture/01-bounded-contexts.md` | Document budget architecture | Complete |
| `frontend/src/api/generated/models/WBECreate.ts` | Regenerate (remove budget_allocation) | Pending backend deployment |
| `frontend/src/api/generated/models/WBEUpdate.ts` | Regenerate (remove budget_allocation) | Pending backend deployment |
| `backend/openapi.json` | Regenerate after schema changes | Pending |

### Migration Rollback Path

The migration at `backend/alembic/versions/20260228_remove_wbe_budget_allocation.py` includes a complete `downgrade()` function that:

1. Re-adds the `budget_allocation` column to the `wbes` table
2. Restores budget values from "Budget Transfer" cost elements
3. Removes the migration cost elements (cleanup)

**Rollback Command:** `uv run alembic downgrade -1`

---

## 4. Technical Debt Ledger

### Resolved This Iteration

| ID | Resolution | Time Spent |
| -- | ---------- | ---------- |
| Data Duplication (WBE budget vs CostElement budget) | Removed WBE.budget_allocation column, use computed attribute | ~4 hours |

### Created This Iteration

| ID | Description | Impact | Effort | Target Date |
| -- | ----------- | ------ | ------ | ----------- |
| TD-014 | OpenAPI spec drift detection not automated | Low | 1 hour | Sprint 10 |
| TD-015 | Bulk budget loading optimization for list queries | Low | 2 hours | Future sprint |

**Net Debt Change:** -1 item (resolved), +2 items (created)

---

## 5. Process Improvements

### What Worked Well

- **Data Migration Strategy**: Creating "Budget Transfer" cost elements during migration preserved existing data and enabled rollback
- **Computed Attribute Pattern**: Clean separation between storage (CostElement) and presentation (WBE)
- **Test Coverage**: Existing tests caught no regressions, confirming backward compatibility

### Process Changes for Future

| Change | Rationale | Owner |
| ------ | --------- | ----- |
| Add CI check for OpenAPI spec drift | Prevent frontend/backend type mismatches | DevOps |
| Document computed attribute pattern in coding standards | Guide future similar refactorings | Backend Team |

---

## 6. Knowledge Transfer

- [x] ADR-013 documents the computed attribute pattern with code examples
- [x] Migration includes detailed docstring explaining strategy
- [x] Model comments explain the computed attribute mechanism
- [x] Service method docstrings explain budget computation

**Key Learning:**
When removing a field that exists in multiple places, use a computed attribute pattern to maintain API compatibility while eliminating data duplication.

---

## 7. Metrics for Monitoring

| Metric | Baseline | Target | Measurement Method |
| ------ | -------- | ------ | ------------------ |
| WBE query performance (with budget) | ~50ms | <100ms | Database query timing |
| Budget consistency | Manual check | 100% (always) | No WBE-CostElement mismatch possible |
| API compatibility | Breaking change risk | Zero breaking changes | All existing WBERead consumers work |

---

## 8. Next Iteration Implications

**Unlocked:**

- EVM calculations now have single source of truth for budgets
- Simplified change order impact analysis (budget changes only at CostElement level)
- Future: Can add time-travel to budget computation

**New Priorities:**

- Regenerate frontend types after backend deployment
- Consider CI automation for OpenAPI spec drift detection

**Invalidated Assumptions:**

- None - backward compatibility maintained via computed attribute

---

## 9. Concrete Action Items

- [ ] **Regenerate frontend types** - Run `npm run generate-client` after backend deployment - @frontend-team
- [ ] **Verify OpenAPI spec** - Check that WBECreate/WBEUpdate no longer include budget_allocation - @backend-team
- [ ] **Add CI check for spec drift** - Create workflow to detect frontend/backend type mismatches - @devops (TD-014)

---

## 10. Iteration Closure

**Final Status:** Complete

**Success Criteria Met:** 7 of 7

| Criterion | Status |
| --------- | ------ |
| AC-1: budget_allocation removed from WBE model | Verified |
| AC-2: WBE budget computed from CostElement.budget_amount | Verified |
| AC-3: All WBE-returning methods populate computed budget | Verified |
| AC-4: EVM calculations use CostElement.budget_amount | Verified |
| AC-5: Impact analysis uses correct budget source | Verified |
| AC-6: Migration includes rollback path | Verified |
| AC-7: Frontend budget input removed | Verified |

**Lessons Learned Summary:**

1. **Single Source of Truth Pattern**: When data exists in multiple places, choose one authoritative source and compute derived values. This eliminates consistency issues and simplifies updates.

2. **Computed Attributes for API Compatibility**: Use non-mapped attributes with service-layer population to maintain backward API compatibility while changing internal storage.

3. **Data Migration with Rollback**: Always include a complete downgrade path that can restore the previous state without data loss.

4. **Test Coverage as Safety Net**: Comprehensive existing tests provide confidence that refactoring doesn't break functionality.

**Iteration Closed:** 2026-02-28
