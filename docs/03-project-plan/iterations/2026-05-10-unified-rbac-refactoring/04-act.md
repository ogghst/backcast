# ACT: Unified RBAC Refactoring

**Date:** 2026-05-10 | **Status:** Complete

---

## Fixes Applied

| # | Issue | Approach | Result |
|---|-------|----------|--------|
| 1 | Ruff import sort error in auth.py:10 (I001) | Added `logging` import and sorted imports alphabetically (stdlib -> third-party -> local) | PASS - ruff check clean |
| 2 | Service coverage at 67.53% (target 80%+) | Added 17 new tests covering `refresh_permissions_cache`, `get_user_roles` DB path, `get_assignments_by_scope`, `get_all_user_assignments`, `update_assignment` | PASS - 93.81% coverage (44 tests total) |
| 3 | No logging for unified-to-legacy fallback | Added `logger.warning()` with user_id and exc_info in both RoleChecker and ProjectRoleChecker except blocks | PASS - fallback now observable in production |
| 4 | N+1 query in list_assignments endpoint | Replaced per-assignment role name queries with single batch query using `IN` clause | PASS - O(1) queries instead of O(N) |
| 5 | MyPy type error from N+1 fix | Added explicit `dict[UUID, str]` type annotation and row-by-row dict construction | PASS - mypy clean |

## Deferred

| Item | Reason | Tracked In |
|------|--------|------------|
| Migration verification tests (BE-020) | High priority but not blocking merge. Needs integration test scaffolding. | TD-095 |
| Security tests for RBAC edge cases (BE-025) | Medium priority. Fail-secure defaults are tested. | TD-096 |
| Performance benchmarks (BE-024) | Low priority. Cache design is sound. | TD-097 |
| Delete deprecated RBAC files (BE-027) | Requires 1-2 weeks production validation with zero fallback triggers. | TD-098 |

## Standardized

| Pattern | Doc Updated |
|---------|-------------|
| Delegation pattern for service migration | `docs/03-project-plan/lessons-learned.md` |
| N+1 query prevention in list endpoints | `docs/03-project-plan/lessons-learned.md` |

## Tech Debt

- **Created:** TD-095 (migration verification), TD-096 (security tests), TD-097 (performance benchmarks), TD-098 (deprecated file cleanup)
- **Resolved:** None
- **Net:** +4 items, +2 days estimated effort

## Lessons Learned

1. **Delegation over replacement for high-risk migrations:** Using RoleChecker/ProjectRoleChecker to delegate to UnifiedRBACService preserves backward compatibility while achieving unified RBAC. Logging fallback triggers enables production monitoring before legacy removal.

2. **Batch enrichment in list endpoints:** The N+1 pattern in list_assignments (individual queries per row) is a common pitfall when adding enrichment to list endpoints. Single batch query with `IN` clause is the standard fix.

## Quality Gates

| Gate | Threshold | Result |
|------|-----------|--------|
| Ruff check | 0 errors | 0 errors |
| Ruff format | All formatted | All formatted |
| MyPy strict | 0 errors | 0 errors |
| Tests | All pass | 44/44 passed |
| Coverage (rbac_unified.py) | >=80% | 93.81% |

## Files Changed

| File | Change |
|------|--------|
| `backend/app/api/dependencies/auth.py` | Added logging import, sorted imports, added fallback logging in RoleChecker and ProjectRoleChecker |
| `backend/app/api/routes/user_role_assignments.py` | Fixed N+1 query in list_assignments with batch role name lookup |
| `backend/tests/unit/core/test_rbac_unified.py` | Added 17 new tests for uncovered methods |
| `docs/03-project-plan/technical-debt-register.md` | Added TD-095 through TD-098 |
| `docs/03-project-plan/lessons-learned.md` | Added 2 new lessons |

## Next Iteration

- **Unlocked:** Production deployment of unified RBAC system with fallback monitoring
- **New priorities:** TD-095 (migration verification before production), TD-096 (security tests before production)
- **Invalidated assumptions:** None -- delegation pattern validated as effective

**Closed:** 2026-05-10
