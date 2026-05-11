# Analysis: RBAC Seeding Fix

**Created:** 2026-05-10
**Request:** Fix RBAC seeding issues discovered during the CHECK phase of the unified RBAC refactoring iteration (2026-05-10-unified-rbac-refactoring). The seeder does not create `UserRoleAssignment` records, the seed file is missing the `change_order_approver` role, and the two RBAC config files have diverged.

---

## Clarified Requirements

### Functional Requirements

- **FR-1**: After a fresh reseed, `UserRoleAssignment` records must exist for every seeded user, reflecting their `User.role` as a GLOBAL-scoped assignment in the unified system.
- **FR-2**: The `change_order_approver` role must be present in the seeded RBAC roles after a fresh reseed.
- **FR-3**: `seed/rbac_roles.json` and `config/rbac.json` must be reconciled so that the seed file is the authoritative single source of truth for development/demo seeding.
- **FR-4**: The seeding must be idempotent -- running `seed_all()` multiple times must not create duplicate `UserRoleAssignment` records (enforced by the `uq_user_role_assignment_scope` unique constraint).
- **FR-5**: The seeding must work correctly for both fresh reseeds (empty database) and databases where the Alembic data migration already ran.

### Non-Functional Requirements

- **NFR-1**: Zero breaking changes to the existing reseed flow (`backend/scripts/reseed_db.py`).
- **NFR-2**: Backend-only changes. No frontend modifications.
- **NFR-3**: Idempotent -- safe to run multiple times without error.
- **NFR-4**: Follow existing seeding patterns in `DataSeeder` (using `seed_operation()` context, idempotency checks, logging).
- **NFR-5**: No performance degradation on the seeding process.

### Constraints

- The `UserRoleAssignment` model uses `SimpleEntityBase` and has a unique constraint on `(user_id, scope_type, scope_id)`.
- The `UnifiedRBACService.assign_role()` uses ContextVar session injection, requiring `set_unified_rbac_session(session)` before use.
- The seeder uses service-layer calls (e.g., `UserService.create_user()`) rather than direct DB queries for some entities, but uses direct DB queries for others (e.g., `seed_rbac_roles`).
- The `reseed_db.py` script truncates ALL tables except `alembic_version`, then calls `seed_all()`. The Alembic migration `20260510b_migrate_existing_roles_to_unified_rbac.py` only runs during `alembic upgrade head` and will NOT run during reseed.

---

## Context Discovery

### Product Scope

- The unified RBAC system was introduced to replace the fragmented `User.role` + `ProjectMember` + `ApprovalMatrixService` model with a single `UserRoleAssignment` entity supporting GLOBAL, PROJECT, and CHANGE_ORDER scopes.
- The CHECK phase of the unified RBAC iteration identified that the seeder produces a database where the unified system has zero data, causing all permission checks to fall back to legacy (with logged warnings).

### Architecture Context

- **Bounded contexts involved**: Identity & Access Management (RBAC), Project Management (project members)
- **Existing patterns**: `DataSeeder` class with `seed_*` methods called in dependency order from `seed_all()`. Each method is idempotent via existence checks.
- **Delegation pattern**: `RoleChecker` and `ProjectRoleChecker` in `auth.py` try `UnifiedRBACService` first, then fall back to legacy `RBACServiceABC`. Without `UserRoleAssignment` records, every check hits the fallback path.

### Codebase Analysis

**Backend:**

- `backend/app/db/seeder.py` -- `seed_all()` at line 1266 calls methods in order: `seed_rbac_roles`, `seed_departments`, `seed_users`, then project/entity seeding. No step creates `UserRoleAssignment` records.
- `backend/app/db/seeder.py` -- `seed_users()` at line 71 uses `UserService.create_user()` which creates `User` with legacy `role` field but does not call `UnifiedRBACService`.
- `backend/app/db/seeder.py` -- `seed_rbac_roles()` at line 960 loads `seed/rbac_roles.json` (preferred) or `config/rbac.json` (fallback). The seed file is missing `change_order_approver`.
- `backend/seed/rbac_roles.json` -- 6 roles (admin, manager, viewer, ai-viewer, ai-manager, ai-admin). Missing `change_order_approver`.
- `backend/config/rbac.json` -- 7 roles, including `change_order_approver`. But has diverged from seed file in other ways:
  - `manager` in seed has `change-order-delete`, `change-order-implement`, `forecast-read` that config lacks
  - `admin` and `ai-admin` in seed have MCP permissions that config lacks
  - `ai-manager` in seed has `mcp-tool-execute` that config lacks
  - `viewer` in config has `change-order-approve` (incorrect for read-only role) that seed lacks
- `backend/app/core/rbac_unified.py` -- `UnifiedRBACService.assign_role()` at line 396 creates `UserRoleAssignment` records. Requires ContextVar session injection.
- `backend/app/models/domain/user_role_assignment.py` -- `UserRoleAssignment` entity with unique constraint `uq_user_role_assignment_scope` on `(user_id, scope_type, scope_id)`.
- `backend/alembic/versions/20260510b_migrate_existing_roles_to_unified_rbac.py` -- Data migration that copies `User.role` to global `UserRoleAssignment` and `ProjectMember` to project `UserRoleAssignment`. Only runs during `alembic upgrade head`, not during reseed.
- `backend/scripts/reseed_db.py` -- Truncates all tables, then calls `seed_all()`. Does not re-run Alembic migrations.
- `backend/seed/users.json` -- 5 users with roles: admin, viewer, manager, contributor, contributor. Note: "contributor" is NOT a defined RBAC role in either config file.
- `backend/app/core/rbac.py` -- `JsonRBACService` reads from `config/rbac.json` at initialization (line 343). The `.env` sets `RBAC_POLICY_FILE=config/rbac.json` with `RBAC_PROVIDER=json` (default). This means `config/rbac.json` IS consumed at runtime by the legacy RBAC fallback path and CANNOT be deleted.
- `backend/app/core/config.py` -- `Settings.RBAC_PROVIDER` defaults to `"json"`, `Settings.RBAC_POLICY_FILE` set to `"config/rbac.json"` in `.env`.
- `backend/.env` -- `RBAC_POLICY_FILE=config/rbac.json`

**Key Observation 1**: The `users.json` file has two users with role "contributor" which does not exist in either RBAC config. This means the migration SQL `JOIN rbac_roles r ON r.name = u.role` will silently skip these users. The new `seed_user_role_assignments()` method must handle this gracefully.

**Key Observation 2**: `config/rbac.json` is a runtime-critical file consumed by `JsonRBACService` (the legacy RBAC service). With `RBAC_PROVIDER=json` in `.env`, the legacy fallback reads permissions from this file for every authorization check. It CANNOT be deleted. Both files must be synchronized.

---

## Solution Options

### Option 1: Synchronize Seed File + Add `seed_user_role_assignments()` Method

**Architecture & Design:**

1. Reconcile `seed/rbac_roles.json` to be the single source of truth, incorporating the correct `change_order_approver` role from config and resolving all permission discrepancies.
2. Add a new `seed_user_role_assignments()` method to `DataSeeder` that:
   - Reads all users from the database (after `seed_users` completes)
   - Looks up each user's `role` field
   - Looks up the corresponding `RBACRole.id` by name
   - Creates a `UserRoleAssignment` record with `scope_type='global'`, `scope_id=None`
   - Uses direct SQLAlchemy INSERT with existence checks for idempotency
3. Call this method from `seed_all()` after `seed_users()` and before project seeding.
4. Delete `config/rbac.json` to eliminate the dual-source confusion. The seeder already prefers the seed file.

**Implementation:**

- Modify `backend/seed/rbac_roles.json` -- add `change_order_approver`, reconcile all permission differences
- Add `seed_user_role_assignments()` to `backend/app/db/seeder.py`
- Update `seed_all()` to call the new method after `seed_users()`
- Remove `backend/config/rbac.json`
- Update `seed_rbac_roles()` to remove the fallback logic (since seed file is now sole source)

**Trade-offs:**

| Aspect          | Assessment                                                     |
| --------------- | -------------------------------------------------------------- |
| Pros            | Single source of truth; direct DB queries match existing patterns; idempotent by design; eliminates config file confusion |
| Cons            | Seed file becomes the ONLY RBAC definition file (no env-specific override); requires careful permission reconciliation |
| Complexity      | Low-Med -- mostly data file fixes and one new seeding method   |
| Maintainability | Good -- one file to update, clear flow                         |
| Performance     | Negligible -- 5 users, 5-7 role lookups, 5 INSERTs            |

---

### Option 2: Synchronize Both Files + Add Seeding Method + Keep Fallback

**Architecture & Design:**

Same as Option 1 for the seeding method, but instead of deleting `config/rbac.json`, synchronize both files to contain identical role definitions. Keep the existing fallback logic in `seed_rbac_roles()` that prefers `seed/rbac_roles.json` and falls back to `config/rbac.json`.

The rationale for keeping both files is that `config/rbac.json` may be used at application startup or by other runtime code for permission validation, while `seed/rbac_roles.json` is specifically for database seeding.

**Implementation:**

- Modify `backend/seed/rbac_roles.json` -- add `change_order_approver`, reconcile all permissions
- Modify `backend/config/rbac.json` -- make permissions identical to seed file
- Add `seed_user_role_assignments()` to `backend/app/db/seeder.py`
- Update `seed_all()` to call the new method after `seed_users()`

**Trade-offs:**

| Aspect          | Assessment                                                     |
| --------------- | -------------------------------------------------------------- |
| Pros            | Preserves any runtime usage of `config/rbac.json`; maintains existing fallback pattern; lower risk of breaking unknown consumers |
| Cons            | Two files to keep in sync (maintenance burden); risk of future divergence again |
| Complexity      | Low-Med -- same seeding method, but two files to maintain      |
| Maintainability | Fair -- two sources of truth that must be kept identical       |
| Performance     | Negligible -- same as Option 1                                 |

---

### Option 3: Replace Config File with Seed File + Use UnifiedRBACService for Seeding

**Architecture & Design:**

Same file reconciliation as Option 1, but instead of using direct DB queries in the new seeding method, use the `UnifiedRBACService.assign_role()` method. This exercises the actual service code path during seeding, providing early validation that the service works correctly.

Requires:
1. Setting the ContextVar session via `set_unified_rbac_session(session)` before calling the service
2. Handling the `ValueError` raised by `assign_role()` when a duplicate exists (for idempotency)
3. Clearing the ContextVar after seeding

**Implementation:**

- Same file changes as Option 1
- Add `seed_user_role_assignments()` that uses `UnifiedRBACService.assign_role()` instead of direct DB queries
- Must handle session injection and duplicate-graceful handling

**Trade-offs:**

| Aspect          | Assessment                                                     |
| --------------- | -------------------------------------------------------------- |
| Pros            | Exercises the actual service code path; validates service works during seeding; automatic cache invalidation |
| Cons            | Tighter coupling between seeder and service layer; ContextVar setup adds complexity; service raises ValueError on duplicate requiring try/except; breaks the pattern where seeder uses direct DB queries for idempotent operations |
| Complexity      | Medium -- ContextVar management + exception handling            |
| Maintainability | Fair -- seeder now depends on service internals (session injection) |
| Performance     | Slightly slower (service overhead) but negligible for 5 users  |

---

## Comparison Summary

| Criteria           | Option 1 (Sync + Direct DB) | Option 2 (Sync Both Files) | Option 3 (Use Service) |
| ------------------ | --------------------------- | -------------------------- | ---------------------- |
| Development Effort | Low (2-3 hours)             | Low (2-3 hours)            | Med (3-4 hours)        |
| Maintainability    | Good (1 file)               | Fair (2 files)             | Fair (service coupling)|
| Risk               | Low                         | Low                        | Med (ContextVar issues) |
| Best For           | Long-term simplicity        | Preserving fallback compat | Service validation     |

---

## Recommendation

**I recommend Option 2 because:**

1. **`config/rbac.json` is runtime-critical.** Codebase investigation confirmed that `JsonRBACService` (in `app/core/rbac.py:343`) reads from `config/rbac.json` at initialization. The `.env` sets `RBAC_POLICY_FILE=config/rbac.json` with `RBAC_PROVIDER=json` (default). This file powers the legacy RBAC fallback for every permission check. Deleting it would break all authorization in environments using the default `json` provider.

2. **Both files must be synchronized.** The seed file is the authoritative source for database seeding (preferred by the seeder), while the config file is the authoritative source for runtime permission checks. By making them identical, we eliminate the divergence problem while preserving both usage paths.

3. **Direct DB queries** in the new `seed_user_role_assignments()` method match the existing seeding pattern used in `seed_rbac_roles()`, which also uses direct SQLAlchemy queries with existence checks. This keeps the seeder consistent.

4. **Low complexity and low risk** -- the changes are straightforward data file synchronization plus one new seeding method following established patterns.

**Preventing future divergence:** Add a comment to both files referencing each other, and consider adding a test that validates the two files are structurally identical in their role and permission definitions.

---

## Decision Questions

1. Should the two users with role "contributor" in `users.json` be mapped to a specific RBAC role (e.g., "viewer" or "manager") or should they remain unmapped (no unified role assignment)?
2. Should project-scoped `UserRoleAssignment` records also be seeded during `seed_projects()`, or is global-only sufficient for this fix?
3. Should we add a CI test that validates `seed/rbac_roles.json` and `config/rbac.json` stay in sync?

---

## References

- `backend/seed/rbac_roles.json` -- current seed RBAC definitions (6 roles)
- `backend/config/rbac.json` -- current config RBAC definitions (7 roles, diverged)
- `backend/app/db/seeder.py` -- DataSeeder class with all seeding methods
- `backend/scripts/reseed_db.py` -- reseed entry point
- `backend/app/core/rbac_unified.py` -- UnifiedRBACService with assign_role()
- `backend/app/models/domain/user_role_assignment.py` -- UserRoleAssignment entity model
- `backend/alembic/versions/20260510b_migrate_existing_roles_to_unified_rbac.py` -- data migration
- `docs/03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/03-check.md` -- CHECK report identifying these issues
