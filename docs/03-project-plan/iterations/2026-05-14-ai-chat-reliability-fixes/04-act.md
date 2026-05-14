# Act: AI Chat Reliability Fixes (RBAC Cache + Tab Rendering)

**Completed:** 2026-05-14
**Based on:** [03-check.md](./03-check.md)

---

## 1. Improvements Implemented

### Critical Issues (from CHECK)

| Issue | Resolution | Verification |
| --- | --- | --- |
| `test_middleware_uses_contextvar_session` patches `set_rbac_session` (non-existent) | Updated test to patch `set_unified_rbac_session` and `get_unified_rbac_service` in `backcast_security` module; added `ctx` positional argument to match updated method signature | `pytest tests/security/ai/test_tool_rbac.py::test_middleware_uses_contextvar_session` -- PASS |
| `test_subagents_get_all` asserts `len == 7` but 8 subagents exist | Removed hardcoded count; test now verifies non-empty list, unique names, all expected specialists present, and old names absent. Resilient to future subagent additions. | `pytest tests/ai/test_deep_agents_integration.py::test_subagents_get_all` -- PASS |

### Refactoring Applied

| Change | Rationale | Files Affected |
| --- | --- | --- |
| Replaced `MockRBACService` with `MagicMock`-based unified RBAC service mock | The middleware migrated from `app.core.rbac` (old) to `app.core.rbac_unified` (new); the old mock class no longer matched the interface the middleware calls | `tests/security/ai/test_tool_rbac.py` |
| Replaced hardcoded subagent count with dynamic verification | Avoids test brittleness when subagents are added or removed; verifies structural invariants instead of exact count | `tests/ai/test_deep_agents_integration.py` |

---

## 2. Pattern Standardization

| Pattern | Description | Standardize? | Action |
| --- | --- | --- | --- |
| Patch-at-import-site for ContextVar session injection | Tests patch `set_unified_rbac_session` at the module that imports it, not at the source module | Yes (already standard) | No further action -- test now follows the established pattern |
| Dynamic collection assertions over hardcoded counts | Assert structural invariants (non-empty, unique names, known members present) rather than exact `len()` | Pilot | Adopt for other registry/collection tests if they prove brittle |

---

## 3. Documentation Updates

| Document | Update Needed | Status |
| --- | --- | --- |
| `docs/01-about/changelog/` | No new changelog entry needed -- these are test-only fixes for pre-existing failures on the branch | N/A |

---

## 4. Technical Debt Ledger

### Created This Iteration

None. The two fixes resolved pre-existing test debt, not introduced new debt.

### Resolved This Iteration

| ID | Resolution | Time Spent |
| --- | --- | --- |
| Pre-existing: `test_middleware_uses_contextvar_session` failure | Updated test to match current middleware API (`set_unified_rbac_session`, `get_unified_rbac_service`, positional `ctx`) | 10 min |
| Pre-existing: `test_subagents_get_all` wrong count | Replaced hardcoded `len == 7` with dynamic structural assertions | 5 min |

**Net Debt Change:** -2 items (both pre-existing failures resolved)

### Deferred Debt

| ID | Description | Priority | Target |
| --- | --- | --- | --- |
| TD-068 | Temporal propagation to global chat (P2 from analysis) | P2 | Future iteration |
| TD-069 | Configurable currency (P3 from analysis) | P3 | Future iteration |

---

## 5. Process Improvements

### What Worked Well

- **CHECK-phase gap identification**: The systematic CHECK process caught two pre-existing test failures that would otherwise silently mask real regressions on the branch.
- **Option B for dynamic assertions**: Parameterizing the subagent count test by deriving expectations from the source of truth (`get_all_subagents()`) rather than hardcoding a number prevents the same class of failure from recurring.

### Process Changes for Future

| Change | Rationale | Owner |
| --- | --- | --- |
| Run full AI-related test suite after any refactoring commit on feature branches | Pre-existing failures accumulated because individual refactoring commits did not trigger a full affected-area test run | Developer |

---

## 6. Knowledge Transfer

- [x] Key decisions documented: test fixes use the current unified RBAC API, not the legacy `app.core.rbac` API
- [x] Common pitfalls noted: When the middleware imports from a different module after refactoring, tests must patch at the import site, not the definition site. The `_check_tool_permission` method now requires `ctx` as a positional argument.

---

## 7. Metrics for Monitoring

| Metric | Baseline | Target | Measurement Method |
| --- | --- | --- | --- |
| Test pass rate (AI-related tests) | 42/44 (2 pre-existing failures) | 44/44 | `pytest tests/security/ai/ tests/ai/ tests/unit/ai/` |
| RBAC cache-miss tool filtering | Silent empty toolset | On-demand refresh with logging | Unit tests in `test_role_filtering.py` |

---

## 8. Next Iteration Implications

**Unlocked:**

- The `unified-rbac` branch now has a clean AI test suite (44/44 pass) -- ready for merge without known test debt

**New Priorities:**

- TD-068 (temporal propagation to global chat) remains the next P2 item
- TD-069 (configurable currency) remains the next P3 item

**Invalidated Assumptions:**

- None

---

## 9. Concrete Action Items

- [x] Fix `test_middleware_uses_contextvar_session` -- patch `set_unified_rbac_session` and add `ctx` argument
- [x] Fix `test_subagents_get_all` -- replace hardcoded count with dynamic assertions
- [x] Verify full affected test suite passes (44/44 pass)
- [x] Write ACT document

---

## 10. Iteration Closure

**Final Status:** Complete

**Success Criteria Met:** 5 of 5 (all acceptance criteria from PLAN pass in CHECK; ACT closes the 2 remaining gaps)

**Lessons Learned Summary:**

1. **Silent cache expiry can cause complete feature failure.** The RBAC cache TTL expiry silently dropped all AI tools. On-demand refresh with ERROR-level logging is the correct mitigation. Any in-memory cache without staleness detection or on-demand refresh is a latent bug.
2. **Test assertions that hardcode collection sizes are fragile.** When subagents were added during branch development, the hardcoded `len == 7` assertion failed. Structural assertions (verify expected members present, verify absent members absent) are more resilient and communicate intent better.
3. **Tests must evolve with the code they test.** The middleware migrated from `app.core.rbac` to `app.core.rbac_unified`, but the test was never updated to match. Feature branch refactoring should include updating affected tests in the same commit, not deferred.

**Iteration Closed:** 2026-05-14
