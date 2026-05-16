# Analysis: ADR-014 Unified RBAC Cleanup -- Remove Legacy Artifacts

**Created:** 2026-05-16
**Request:** Complete the ADR-014 migration by removing three backward-compatibility items: `app/core/rbac.py` (old RBAC ABC + JsonRBACService), `app/models/domain/project_member.py` (deprecated model + DB table), and `User.role` field (replaced by `UserRoleAssignment`).

---

## Clarified Requirements

### Functional Requirements

1. **Remove `app/core/rbac.py`**: Delete the entire module containing `RBACServiceABC`, `JsonRBACService`, `require_permission` decorator, and all global singleton functions (`get_rbac_service`, `set_rbac_service`, `inject_rbac_session`). All production code already delegates to `UnifiedRBACService`.
2. **Remove `app/models/domain/project_member.py`**: Delete the deprecated model. Drop the `project_members` database table via Alembic migration. The `JsonRBACService` is the only consumer.
3. **Remove `User.role` field**: Replace all reads of `User.role` with lookups from `UserRoleAssignment`. This spans: route-level admin checks, auth login response, user schemas, AI agent service, AI tool templates, change order service error messages, and the seeder.
4. **Update ~50 test files**: Replace `RBACServiceABC` mock subclasses with `MockUnifiedRBACService` or direct dependency overrides against the unified system. Remove `get_rbac_service` / `set_rbac_service` / `inject_rbac_session` usage in test setup.

### Non-Functional Requirements

- Zero functional regressions: every existing route must enforce the same permissions after cleanup
- All tests pass after migration
- MyPy strict mode and Ruff zero errors maintained
- No database data loss: the migration dropping `project_members` must only run after confirming `UserRoleAssignment` holds equivalent data

### Constraints

- The `User` model is EVCS versioned (`EntityBase + VersionableMixin`). Removing the `role` column requires an Alembic migration that alters a versioned table.
- `project_members` has FK constraints to `users.user_id` and `projects.project_id`. The drop migration must handle these.
- Test files use `RBACServiceABC` as a mock base class in ~50 files. Bulk replacement must be mechanical and safe.

---

## Context Discovery

### Product Scope

- ADR-014 mandated "Big bang migration with complete data integrity (all users and project members migrated)" and "Deprecated User.role and ProjectMember tables (removed after migration verified)"
- The data migration has already run (Alembic `20260510b_migrate_existing_roles_to_unified_rbac.py`). `UserRoleAssignment` now holds all former `User.role` values (scope_type=GLOBAL) and `ProjectMember` records (scope_type=PROJECT).
- The seeder still reads `user.role` to create `UserRoleAssignment` records, creating a bootstrap dependency that must be inverted.

### Architecture Context

- **Bounded contexts**: Auth (Shared Kernel) spans User Management, Project Management, Change Management, and AI contexts. This cleanup consolidates Auth into a single entry point.
- **Layered architecture**: `RoleChecker` and `ProjectRoleChecker` (API layer dependencies in `auth.py`) already delegate to `UnifiedRBACService`. No route-level changes needed for authorization enforcement.
- **EVCS patterns**: `User` is versioned. Removing a column from a versioned table is safe (non-breaking Alembic operation) as long as application code no longer reads/writes that column.

### Codebase Analysis

**Production code that reads `User.role` (must be replaced):**

| File | Lines | Usage | Replacement Strategy |
|------|-------|-------|---------------------|
| `app/api/routes/users.py` | 136, 169, 228 | `current_user.role != "admin"` admin checks | Call `UnifiedRBACService.get_user_roles(user_id, GLOBAL, None)` and check for "admin" |
| `app/api/routes/auth.py` | 102 | `user.role` in login notification payload | Look up global role from `UnifiedRBACService` |
| `app/models/schemas/user.py` | 115-185 | `UserPublic.from_user()` and `from_user_async()` read `user.role` for permission caching | Change `UserPublic.role` field to derive from `UnifiedRBACService` instead of column |
| `app/ai/agent_service.py` | 274 | `user.role` fallback for AI role resolution | Use `UnifiedRBACService.get_user_roles()` |
| `app/ai/tools/templates/user_management_template.py` | 102, 167, 250, 348 | AI tool templates serialize `user.role` | Resolve role from `UnifiedRBACService` |
| `app/services/change_order_service.py` | 1388, 1550, 2426 | Error messages include `approver.role` | Resolve role from `UnifiedRBACService` |
| `app/api/routes/change_orders.py` | 1083 | Approval info includes `approver.role` | Resolve role from `UnifiedRBACService` |
| `app/db/seeder.py` | 1216 | `user.role` drives `UserRoleAssignment` seeding | Invert: seed `UserRoleAssignment` from config first, derive display role from those assignments |

**Production code that imports from `app.core.rbac` (must be removed or replaced):**

| File | What it imports | Status |
|------|----------------|--------|
| `app/ai/tools/rbac_tool_node.py` | Docstring references `RBACServiceABC` (lines 73-74) | Comment-only, already uses `UnifiedRBACService` in code. Remove docstring reference. |
| No other production files | | All production imports already migrated to `UnifiedRBACService` |

**Test files that subclass `RBACServiceABC` (~50 files):**

All follow the same pattern: define a `MockRBACService(RBACServiceABC)` that overrides `has_role`, `has_permission`, `get_user_permissions`, `has_project_access`, `get_user_projects`, `get_project_role`. These are used with `app.dependency_overrides[Depends(get_rbac_service)] = lambda: mock_service`.

The `conftest.py` already has a `MockUnifiedRBACService` class (lines 348-421) that provides the same default-allow behavior with the unified API shape. This is the replacement target.

---

## Solution Options

### Option 1: Sequential Cleanup (Recommended)

**Architecture & Design:**

Execute the three removals in a strict dependency order, with each step fully verified before proceeding:

1. **Step A: Remove `app/core/rbac.py`** -- This is the root dependency. After removing it:
   - All ~50 test files must replace `RBACServiceABC` imports and mock subclasses
   - `conftest.py` `MockRBACService` class is deleted
   - `get_rbac_service` / `set_rbac_service` / `inject_rbac_session` references in tests are replaced with unified equivalents
   - `RBACToolNode` docstring is updated (already uses `UnifiedRBACService`)
   - `ProjectRole` enum in `rbac.py` is relocated to `app/core/enums.py` (a duplicate `ProjectRole` already exists there)

2. **Step B: Remove `app/models/domain/project_member.py`** -- Now that `JsonRBACService` is deleted (it was the only consumer), the model is orphaned:
   - Delete the model file
   - Create Alembic migration to drop `project_members` table
   - Update any test files that create `ProjectMember` instances (4 test files: `test_project_role_checker.py`, `test_project_access.py`, `test_project_access_integration.py`)

3. **Step C: Remove `User.role` field** -- The most invasive change:
   - Replace all production code reads (table above)
   - For `UserPublic` schema: populate `role` from `UnifiedRBACService` -- same string values ("admin", "manager", "viewer")
   - For admin checks in `users.py`: replace `current_user.role != "admin"` with `await _is_admin(current_user, session)` helper
   - Update seeder to create `UserRoleAssignment` records first from config, then derive display role from those assignments (inverted bootstrap order)
   - Create Alembic migration to drop `role` column from `users` table
   - Update `_create_mock_user()` in conftest to remove `role` parameter (or make it populate via mock RBAC)

**UX Design:**

No UX changes. The cleanup is purely internal. `UserPublic.role` continues to be populated and returned to the frontend.

**Implementation:**

- Step A touches ~55 files (50 test + conftest + rbac.py + rbac_tool_node docstring + 2 enums)
- Step B touches 5 files (model + migration + 4 test files)
- Step C touches ~15 files (routes, schemas, services, seeder, migration, conftest, user model)

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | - Each step is independently verifiable<br>- Clear rollback points between steps<br>- Step A (largest by file count) is mechanical and low-risk<br>- Step C (highest risk) comes last when patterns are established |
| Cons            | - Three separate commits/deployments<br>- Longer total calendar time |
| Complexity      | Medium |
| Maintainability | Excellent (clean removal with no dead code) |
| Performance     | Neutral (no runtime impact) |

---

### Option 2: Big Bang Removal

**Architecture & Design:**

Remove all three items in a single commit/migration:

1. Delete `app/core/rbac.py`
2. Delete `app/models/domain/project_member.py`
3. Remove `User.role` column from model and all consumers
4. Create combined Alembic migration (drop `project_members` table + drop `users.role` column)
5. Bulk-update all ~50 test files

**UX Design:**

No UX changes.

**Implementation:**

- Single PR with all changes
- All ~70 files modified in one shot
- Combined Alembic migration

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | - Single deployment, no intermediate states<br>- Faster calendar time<br>- No risk of partial state in production |
| Cons            | - Very large diff (~70 files) makes review difficult<br>- Harder to isolate failures during testing<br>- Rollback is all-or-nothing<br>- Higher cognitive load on reviewer |
| Complexity      | High |
| Maintainability | Excellent (same end state as Option 1) |
| Performance     | Neutral |

---

### Option 3: Conservative -- Remove Old Code Only, Keep User.role as Derived Cache

**Architecture & Design:**

Remove `rbac.py` and `project_member.py` (the clean items) but keep `User.role` as a **denormalized cache** of the global role from `UserRoleAssignment`:

1. Delete `app/core/rbac.py` (same as Option 1 Step A)
2. Delete `app/models/domain/project_member.py` (same as Option 1 Step B)
3. Keep `User.role` column but change its semantics:
   - Write: When `UserRoleAssignment` changes for a user, update `User.role` in the same transaction
   - Read: All current `user.role` reads continue to work without changes
   - Seeder: Continue seeding `user.role` and also creating `UserRoleAssignment`

**UX Design:**

No UX changes.

**Implementation:**

- ~55 files for Step A + 5 files for Step B + minimal changes for Step C
- No `User.role` removal migration needed
- No production code changes for the ~10 files that read `user.role`

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | - Least production code changes<br>- No risky column removal on versioned table<br>- Zero risk of breaking role reads<br>- Faster implementation |
| Cons            | - Violates ADR-014 which explicitly says "replaced by UserRoleAssignment"<br>- Introduces data synchronization requirement (dual writes)<br>- `User.role` becomes a cache that can go stale<br>- Does not fully complete the ADR-014 migration |
| Complexity      | Low |
| Maintainability | Poor (dual-source-of-truth for roles) |
| Performance     | Excellent (no additional queries) |

---

## Comparison Summary

| Criteria           | Option 1 (Sequential) | Option 2 (Big Bang) | Option 3 (Conservative) |
| ------------------ | --------------------- | -------------------- | ----------------------- |
| Development Effort | 3-4 days              | 2-3 days             | 1-2 days                |
| Risk Level         | Low-Medium            | Medium-High          | Low                     |
| Completes ADR-014  | Yes                   | Yes                  | No (partial)            |
| Review Burden      | Low (per-step)        | High (single large PR) | Low                   |
| Rollback           | Easy (per-step)       | All-or-nothing       | Easy                    |
| Best For           | Safe, thorough cleanup | Fast execution      | Quick partial cleanup   |

---

## Recommendation

**I recommend Option 1 (Sequential Cleanup) because:**

1. It fully completes ADR-014 as designed, leaving no legacy artifacts.
2. The dependency order is natural: removing `rbac.py` first eliminates the `ProjectMember` consumer, making the model deletion safe. Removing `User.role` last allows patterns established in Steps A and B to guide the more invasive changes.
3. Each step is independently testable. A failure in Step C does not block the cleanups from Steps A and B.
4. The test file migration (~50 files) is mechanical and can be partially automated with search-and-replace patterns.

**Alternative consideration:** Choose Option 2 if the team prefers a single deployment window and can dedicate focused review time to a large PR. The end state is identical.

**Do NOT choose Option 3** because it violates ADR-014's explicit directive to replace `User.role` with `UserRoleAssignment`, and it introduces a dual-write synchronization problem that is worse than the current state.

---

## Decisions (Approved 2026-05-16)

1. **Frontend contract**: ~~RESOLVED -- No decision needed.~~ The unified role names in `config/rbac.json` are identical to the old `User.role` values ("admin", "manager", "viewer"). `UserPublic.role` will continue returning the same strings -- just sourced from `UnifiedRBACService` instead of the database column.

2. **Seeder bootstrap**: **Approved -- Create `UserRoleAssignment` records first.** The seeder will invert its current order: instead of reading `user.role` to create assignments, it will seed assignments from config/seed data first, then derive any display role from those assignments.

3. **`project_members` table data**: **Approved -- Yes, include verification.** The Alembic migration dropping `project_members` will include a SQL assertion that every row has a corresponding `UserRoleAssignment` row. This catches any data gaps from the original `20260510b` migration.

---

## Sequencing Detail (Option 1)

### Step A: Remove `app/core/rbac.py`

**Files deleted:**
- `app/core/rbac.py`

**Files modified (production):**
- `app/ai/tools/rbac_tool_node.py` -- Remove docstring references to `RBACServiceABC` (lines 73-74)

**Files modified (test):**
- `tests/conftest.py` -- Delete `MockRBACService(RBACServiceABC)` class, delete `mock_rbac_service` and `mock_rbac_service_no_ai` fixtures, update `_create_mock_user` if needed
- ~50 test files -- Replace `from app.core.rbac import RBACServiceABC, get_rbac_service, set_rbac_service` with unified imports. Replace `MockRBACService(RBACServiceABC)` subclasses with `MockUnifiedRBACService` usage or `UnifiedRBACService` mocks.

**Effort:** 2 days (1 day for mechanical test updates, 0.5 day for conftest, 0.5 day for verification)

### Step B: Remove `app/models/domain/project_member.py`

**Files deleted:**
- `app/models/domain/project_member.py`

**Files modified:**
- New Alembic migration to drop `project_members` table
- `tests/api/test_dependencies/test_project_role_checker.py` -- Replace `ProjectMember` creation with `UserRoleAssignment`
- `tests/api/routes/test_project_access.py` -- Replace `ProjectMember` with `UserRoleAssignment`
- `tests/integration/ai/test_project_access_integration.py` -- Replace `ProjectMember` with `UserRoleAssignment`

**Effort:** 0.5 days

### Step C: Remove `User.role` field

**Files modified (production):**
- `app/models/domain/user.py` -- Remove `role` column
- `app/models/schemas/user.py` -- Update `UserBase`, `UserRegister`, `UserUpdate`, `UserPublic` to resolve role from `UnifiedRBACService`
- `app/api/routes/users.py` -- Replace `current_user.role != "admin"` with `UnifiedRBACService.get_user_roles()` calls
- `app/api/routes/auth.py` -- Resolve role from `UnifiedRBACService` for login notification
- `app/ai/agent_service.py` -- Replace `user.role` with role lookup
- `app/ai/tools/templates/user_management_template.py` -- Replace `user.role` with role resolution
- `app/services/change_order_service.py` -- Replace `approver.role` in error messages
- `app/api/routes/change_orders.py` -- Replace `approver.role` in response data
- `app/db/seeder.py` -- Invert seeding order (seed roles from config, not from `user.role`)
- New Alembic migration to drop `users.role` column

**Files modified (test):**
- `tests/conftest.py` -- Remove `role` from `_create_mock_user` or adjust mock pattern

**Effort:** 1.5 days

**Total estimated effort:** 4 days

---

## References

- [ADR-014: Unified RBAC System](/home/nicola/dev/backcast/docs/02-architecture/decisions/ADR-014-unified-rbac.md)
- [Original Analysis](/home/nicola/dev/backcast/docs/03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/00-analysis.md)
- `backend/app/core/rbac_unified.py` -- UnifiedRBACService (replacement)
- `backend/app/core/rbac.py` -- Legacy module (to be deleted)
- `backend/app/models/domain/project_member.py` -- Deprecated model (to be deleted)
- `backend/app/models/domain/user.py` -- User model with `role` column (to be modified)
- `backend/app/api/dependencies/auth.py` -- RoleChecker/ProjectRoleChecker (already use unified system)
- `backend/tests/conftest.py` -- MockRBACService + MockUnifiedRBACService fixtures
