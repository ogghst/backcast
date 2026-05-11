# Act: RBAC Seeding Fix

**Completed:** 2026-05-10
**Based on:** [03-check.md](03-check.md)

---

## 1. Improvements Implemented

### Critical Issues (from CHECK)

| Issue | Resolution | Verification |
| ----- | ---------- | ------------ |
| Dual RBAC config file divergence | Both JSON files synchronized to identical role/permission definitions; CI-sync test added | `test_rbac_config_sync.py` -- 4 tests PASS |
| Missing `change_order_approver` role in seed file | Added role with 7 permissions to `seed/rbac_roles.json` | `test_change_order_approver_exists_in_seed` PASS |
| No `UserRoleAssignment` seeding after fresh reseed | Added `seed_user_role_assignments()` method to `DataSeeder` | 6 unit tests PASS |
| Invalid "contributor" role in `seed/users.json` | Changed eng.lead and const.super from "contributor" to "manager" | `test_no_contributor_role_in_users_json` PASS |

### Refactoring Applied

| Change | Rationale | Files Affected |
| ------ | --------- | -------------- |
| Added `seed_user_role_assignments()` method with direct SQLAlchemy queries | Follows established `seed_rbac_roles()` pattern; avoids ContextVar complexity in seeder context | `backend/app/db/seeder.py` |
| Updated `seed_all()` call order | New method must run after `seed_users()` and `seed_rbac_roles()` | `backend/app/db/seeder.py` |
| Synchronized `config/rbac.json` permissions | viewer lost `change-order-approve`; manager gained `change-order-delete`, `change-order-implement`, `forecast-read`; ai-admin/ai-manager gained MCP permissions | `backend/config/rbac.json` |

---

## 2. Pattern Standardization

| Pattern | Description | Standardize? | Action |
| ------- | ----------- | ------------ | ------ |
| CI-sync test for dual config files | `test_rbac_config_sync.py` validates structural parity between `seed/rbac_roles.json` and `config/rbac.json` | Yes (already in place) | None -- pattern established in this iteration |
| Idempotent seeding via `scalar_one_or_none()` | Check existence before INSERT to prevent duplicates on re-seed | Yes (already codified) | Follows existing `seed_rbac_roles()` pattern |
| Pure AsyncMock tests for seeder unit tests | Avoid test DB FK constraint issues by mocking session and query results | Pilot | Applicable when test DB fixture issues prevent integration tests; document tradeoff (logic-only coverage, no schema validation) |

No cross-cutting architecture docs or coding standards require updates -- the patterns are internal to the DataSeeder.

---

## 3. Documentation Updates

| Document | Update Needed | Status |
| -------- | ------------- | ------ |
| `docs/03-project-plan/lessons-learned.md` | Added "Dual Config File Divergence Prevention" lesson under Architecture & Design | Done |
| `docs/03-project-plan/technical-debt-register.md` | Added TD-099 for test DB fixture `create_all()` issue | Done |
| Architecture docs (`docs/02-architecture/`) | No update needed -- seeding is internal to DataSeeder | N/A |
| ADRs | No ADR needed -- no new architectural decisions | N/A |

---

## 4. Technical Debt Ledger

### Created This Iteration

| ID | Description | Impact | Effort | Target Date |
| ---- | ----------- | ------ | ------ | ----------- |
| TD-099 | Test DB fixture uses `create_all()` instead of Alembic migrations, causing FK constraint failures for 13 existing tests | High -- test suite health degraded | 1 day | 2026-05-24 |

### Resolved This Iteration

No technical debt was directly resolved. The dual config file divergence was a production defect, not tracked debt.

**Net Debt Change:** +1 item (TD-099)

---

## 5. Process Improvements

### What Worked Well

- **CI-sync test as regression guard**: Adding `test_rbac_config_sync.py` permanently prevents the dual-file divergence problem from recurring. This is a lightweight, high-value safety net.
- **Pure mock-based seeder tests**: Using AsyncMock instead of the shared `db_session` fixture kept new tests fast and independent of the pre-existing FK constraint issue. The tradeoff (no schema validation) is acceptable for unit-level logic tests.
- **Strict scope control**: The iteration stayed within bounds -- no frontend changes, no service-layer modifications, no migration changes. This made the CHECK phase straightforward.

### Process Changes for Future

| Change | Rationale | Owner |
| ------ | --------- | ----- |
| When two config files share structural data, add CI-sync test immediately | Waiting until divergence occurs means the problem is harder to diagnose | Backend Developer |
| Prefer mock-based seeder tests when test DB fixture is unreliable | Avoids blocking new iteration work on pre-existing infrastructure issues | Backend Developer |

---

## 6. Knowledge Transfer

- [x] Key decisions documented -- seed file authority, global-only scope, direct SQLAlchemy pattern
- [x] Common pitfalls noted -- dual config file divergence, test DB fixture mismatch with Alembic migrations
- [x] Root cause analysis captured -- 5-Whys for both the FK constraint issue and the config divergence

---

## 7. Metrics for Monitoring

| Metric | Baseline | Target | Measurement Method |
| ------ | -------- | ------ | ------------------ |
| RBAC config file parity | Diverged (multiple mismatches) | Zero divergence | CI-sync test runs on every PR |
| Seeder tests passing (new) | 0 | 11 | `pytest tests/unit/db/test_seeder.py -k "UserRoleAssignments or UserAllRole"` |
| Seeder tests passing (pre-existing, blocked) | 0 of 13 | 13 | Blocked by TD-099 |

---

## 8. Next Iteration Implications

**Unlocked:**

- Fresh reseed now creates `UserRoleAssignment` records for all seeded users, matching the unified RBAC system's expectations
- `change_order_approver` role is available in both seed data and runtime RBAC config
- CI-sync test prevents future config file drift

**New Priorities:**

- TD-099: Fix test DB fixture to use Alembic migrations instead of `create_all()` (unblocks 13 existing seeder tests)
- Project-scoped `UserRoleAssignment` seeding (deferred from this iteration's scope boundaries)

**Invalidated Assumptions:**

- None. The iteration confirmed that `config/rbac.json` is runtime-critical for `JsonRBACService` and cannot be deleted (Option 2 was correct over Option 1).

---

## 9. Concrete Action Items

- [ ] TD-099: Fix test DB fixture to apply Alembic migrations -- @Backend Developer -- by 2026-05-24
- [ ] Consider project-scoped `UserRoleAssignment` seeding in next RBAC iteration -- @Backend Developer -- when needed
- [ ] Validate TD-098 (delete deprecated RBAC files) after 1-2 weeks production validation of unified RBAC -- @Backend Developer -- by 2026-05-24

---

## 10. Iteration Closure

**Final Status:** PASS

**Success Criteria Met:** 8 of 8

**Lessons Learned Summary:**

1. Dual config files serving overlapping purposes will diverge without automated enforcement. Add CI-sync tests at creation time, not after the first incident.
2. The test DB fixture's `create_all()` approach is fragile when cross-table FK relationships are introduced via migrations. This is now tracked as TD-099.
3. Pure mock-based seeder tests are a pragmatic workaround for infrastructure issues, but should not become the permanent pattern -- the underlying fixture problem needs fixing.

**Iteration Closed:** 2026-05-10
