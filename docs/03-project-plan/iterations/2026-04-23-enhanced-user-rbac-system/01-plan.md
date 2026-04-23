# Plan: Enhanced User and RBAC System -- Iteration 1

**Created:** 2026-04-23
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 (Provider Abstraction Layer) -- Iteration 1 of 3

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option:** Option 1 from analysis -- Provider Abstraction Layer, delivered incrementally
- **Iteration Scope:** Provider Framework + Database-Backed RBAC + Admin API + Admin UI
- **Key Decisions:**
  1. Start with Database-Backed RBAC + Admin UI; OIDC deferred to Iteration 2
  2. Architecture must already plan for OIDC (ABC interfaces, factory pattern, settings placeholders)
  3. JsonRBACService preserved as default; zero-migration effort required
  4. New RBAC tables use `SimpleEntityBase` (non-versioned; permissions change frequently)
  5. Single-server deployment: in-memory caching acceptable

### Success Criteria

**Functional Criteria:**

- [F-01] `RBAC_PROVIDER=database` setting activates `DatabaseRBACService` that reads roles/permissions from PostgreSQL tables VERIFIED BY: integration test switching provider and verifying permission checks
- [F-02] `RBAC_PROVIDER=json` (default) preserves current `JsonRBACService` behavior exactly, no regression VERIFIED BY: existing test suite passes unchanged
- [F-03] Alembic migration creates `rbac_roles` and `rbac_role_permissions` tables and seeds data from existing `rbac.json` VERIFIED BY: migration test asserting table existence and seeded row count matches rbac.json roles
- [F-04] Admin API `GET /api/v1/admin/rbac/roles` returns list of roles with their permissions VERIFIED BY: API integration test returning expected structure
- [F-05] Admin API `POST /api/v1/admin/rbac/roles` creates a new role with permissions; only accessible by `admin` role VERIFIED BY: API integration test with admin/non-admin users
- [F-06] Admin API `PUT /api/v1/admin/rbac/roles/{id}` updates a role's name and/or permissions VERIFIED BY: API integration test verifying updated data persisted
- [F-07] Admin API `DELETE /api/v1/admin/rbac/roles/{id}` removes a role and its permissions VERIFIED BY: API integration test confirming cascade deletion
- [F-08] Admin API `GET /api/v1/admin/rbac/permissions` returns the distinct set of all known permission strings VERIFIED BY: API integration test
- [F-09] Frontend RBAC Configuration page displays roles and permissions; full CRUD when database provider active; read-only with "switch provider" prompt when JSON provider active VERIFIED BY: Playwright snapshot of both states
- [F-10] `AuthProvider` ABC defined with `LocalAuthProvider` as sole implementation; wraps current JWT+password logic without behavior change VERIFIED BY: unit test confirming LocalAuthProvider replicates current auth flow
- [F-11] `UserProvider` ABC defined with `LocalUserProvider` as sole implementation; wraps current UserService without behavior change VERIFIED BY: unit test confirming delegation to UserService
- [F-12] Factory pattern in `get_rbac_service()` supports configuration-driven provider selection via `RBAC_PROVIDER` setting VERIFIED BY: unit test with each provider type
- [F-13] `DatabaseRBACService` uses in-memory cache with configurable TTL; cache invalidation on write operations VERIFIED BY: unit test verifying cache hit/miss behavior and invalidation after create/update/delete

**Technical Criteria:**

- [T-01] MyPy strict mode: zero errors on all new/modified files VERIFIED BY: `uv run mypy app/`
- [T-02] Ruff: zero errors on all new/modified files VERIFIED BY: `uv run ruff check .`
- [T-03] Test coverage >= 80% on all new backend modules VERIFIED BY: `uv run pytest --cov=app`
- [T-04] ESLint: zero errors on all new/modified frontend files VERIFIED BY: `npm run lint`
- [T-05] Frontend test coverage >= 80% on new components VERIFIED BY: `npm run test:coverage`
- [T-06] All existing backend tests pass unchanged VERIFIED BY: `uv run pytest`
- [T-07] All existing frontend tests pass unchanged VERIFIED BY: `npm test`
- [T-08] `DatabaseRBACService.has_permission()` returns result in < 1ms for cached entries VERIFIED BY: benchmark test with 1000 iterations

**Business Criteria:**

- [B-01] An admin user can create, edit, and delete roles via the Admin UI without redeploying the application VERIFIED BY: manual walkthrough or Playwright E2E test
- [B-02] Switching from JSON to database provider requires only a settings change; no code modification VERIFIED BY: configuration change test

### Scope Boundaries

**In Scope:**

- Provider abstraction ABCs: `AuthProvider`, `UserProvider` (interfaces + local implementations)
- `DatabaseRBACService` implementing existing `RBACServiceABC`
- Database schema: `rbac_roles`, `rbac_role_permissions` tables (Alembic migration)
- Data seeding from `rbac.json` into new tables
- In-memory cache layer for `DatabaseRBACService`
- Admin API endpoints (CRUD for roles/permissions)
- Frontend RBAC Configuration page (admin section)
- Settings additions: `RBAC_PROVIDER`, `AUTH_PROVIDER`, `USER_PROVIDER`
- Factory pattern updates to `get_rbac_service()`

**Out of Scope:**

- OIDC authentication (Iteration 2)
- External user provider / Entra integration (Iteration 3)
- `EntraPermissionProvider` / `EntraUserProvider` / `OIDCAuthProvider` implementations
- Group-to-role mapping from external providers
- Copy-on-login user provisioning from external providers
- Login page UI changes (e.g., "Sign in with Microsoft" button)
- Audit logging for RBAC changes (future iteration)
- RBAC provider hot-reload (server restart acceptable for provider switch)

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|-------------------|------------|
| 1 | Settings additions for provider configuration | `backend/app/core/config.py`, `backend/.env.example` | Prerequisite: AI RBAC iteration merged | Three new settings with defaults preserving current behavior; MyPy passes | Low |
| 2 | AuthProvider ABC + LocalAuthProvider | New `backend/app/core/providers/` package: `__init__.py`, `auth.py` | Task 1 | ABC defines interface; LocalAuthProvider wraps current JWT+password logic; all existing auth tests pass | Medium |
| 3 | UserProvider ABC + LocalUserProvider | `backend/app/core/providers/user.py` | Task 1 | ABC defines interface; LocalUserProvider delegates to existing UserService; all existing user tests pass | Medium |
| 4 | Database models for RBAC tables | New `backend/app/models/domain/rbac.py`: `RBACRole`, `RBACRolePermission` | None | Two models using SimpleEntityBase; correct columns, types, constraints, relationships; MyPy passes | Medium |
| 5 | Alembic migration for RBAC tables + seed | New migration file | Task 4 | Creates `rbac_roles` and `rbac_role_permissions`; seeds from `rbac.json`; migration is idempotent | Medium |
| 6 | DatabaseRBACService implementation | New `backend/app/core/rbac_database.py` | Tasks 1, 4 | Implements all RBACServiceABC methods; in-memory cache with TTL; invalidation on writes; <1ms cached reads | High |
| 7 | Update factory pattern in get_rbac_service | `backend/app/core/rbac.py` | Tasks 1, 6 | `get_rbac_service()` reads `RBAC_PROVIDER` setting; returns correct provider instance; JsonRBACService remains default | Low |
| 8 | RBACService (SimpleService wrapper) | New `backend/app/services/rbac_admin.py` | Tasks 4, 6 | SimpleService-based CRUD for rbac_roles; bridge between Admin API and DatabaseRBACService | Medium |
| 9 | Pydantic schemas for admin API | New `backend/app/models/schemas/rbac.py` | Task 4 | Request/response schemas for roles and permissions; validation rules; OpenAPI-compatible | Low |
| 10 | Admin API routes | New `backend/app/api/routes/rbac_admin.py` | Tasks 8, 9 | 5 endpoints under `/api/v1/admin/rbac/`; admin-only RoleChecker; proper status codes | Medium |
| 11 | Register admin router in main.py | `backend/app/main.py`, `backend/app/api/routes/__init__.py` | Task 10 | Router included at correct prefix; shows in OpenAPI docs | Low |
| 12 | Backend unit tests for DatabaseRBACService | New `backend/tests/unit/core/test_rbac_database.py` | Task 6 | Tests for all RBACServiceABC methods; cache behavior; invalidation; edge cases; >= 80% coverage on rbac_database.py | Medium |
| 13 | Backend unit tests for admin service | New `backend/tests/unit/services/test_rbac_admin.py` | Task 8 | Tests for CRUD operations; permission management; error handling | Low |
| 14 | Backend integration tests for admin API | New `backend/tests/integration/test_rbac_admin_api.py` | Tasks 10, 11 | Tests all 5 endpoints; admin auth; non-admin rejection; response shapes | Medium |
| 15 | Backend unit tests for providers | New `backend/tests/unit/core/providers/` | Tasks 2, 3 | Tests for AuthProvider/LocalAuthProvider; UserProvider/LocalUserProvider; factory pattern | Low |
| 16 | Frontend: RBAC admin API client types | Generated from OpenAPI; `frontend/src/api/generated/` | Task 11 | OpenAPI client regenerated; types available for RBAC admin endpoints | Low |
| 17 | Frontend: RBAC admin hooks | New `frontend/src/features/admin/rbac/` directory | Task 16 | TanStack Query hooks for CRUD on roles and permissions; query invalidation on mutations | Medium |
| 18 | Frontend: RBAC Configuration page | New `frontend/src/pages/admin/RBACConfiguration.tsx` | Task 17 | Ant Design table with inline editing; create/edit/delete modals; provider indicator; read-only state for JSON provider | High |
| 19 | Frontend: route registration | `frontend/src/routes/index.tsx` | Task 18 | Route added at `/admin/rbac`; protected by `admin` role | Low |
| 20 | Frontend: tests for RBAC admin components | `frontend/src/pages/admin/RBACConfiguration.test.tsx` + hooks tests | Task 18 | Tests for CRUD operations; provider indicator display; read-only vs editable states; >= 80% coverage | Medium |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| F-01: DatabaseRBACService activation | T-001 | `tests/unit/core/test_rbac_database.py` | `has_permission("admin", "project-read")` returns True when data seeded from rbac.json |
| F-01: DatabaseRBACService activation | T-002 | `tests/unit/core/test_rbac_database.py` | `get_user_permissions("viewer")` returns exact list matching rbac.json viewer permissions |
| F-02: JsonRBACService preservation | T-003 | `tests/unit/core/test_rbac.py` | Existing tests pass unmodified (regression guard) |
| F-03: Migration creates tables and seeds | T-004 | `tests/integration/test_rbac_migration.py` | After migration, `rbac_roles` has 6 rows matching rbac.json roles |
| F-03: Migration creates tables and seeds | T-005 | `tests/integration/test_rbac_migration.py` | After migration, `rbac_role_permissions` has row count matching total permissions in rbac.json |
| F-04: List roles endpoint | T-006 | `tests/integration/test_rbac_admin_api.py` | `GET /admin/rbac/roles` returns 200 with array of role objects containing name + permissions |
| F-05: Create role endpoint | T-007 | `tests/integration/test_rbac_admin_api.py` | `POST /admin/rbac/roles` with valid data returns 201; non-admin returns 403 |
| F-06: Update role endpoint | T-008 | `tests/integration/test_rbac_admin_api.py` | `PUT /admin/rbac/roles/{id}` updates permissions; returns 200 with updated data |
| F-07: Delete role endpoint | T-009 | `tests/integration/test_rbac_admin_api.py` | `DELETE /admin/rbac/roles/{id}` returns 204; subsequent GET returns 404 |
| F-08: List permissions endpoint | T-010 | `tests/integration/test_rbac_admin_api.py` | `GET /admin/rbac/permissions` returns 200 with distinct permission strings |
| F-10: AuthProvider ABC | T-011 | `tests/unit/core/providers/test_auth_provider.py` | LocalAuthProvider.authenticate() matches current login flow behavior |
| F-11: UserProvider ABC | T-012 | `tests/unit/core/providers/test_user_provider.py` | LocalUserProvider.get_user() delegates to UserService and returns same result |
| F-12: Factory pattern | T-013 | `tests/unit/core/test_rbac_database.py` | get_rbac_service() returns JsonRBACService when RBAC_PROVIDER="json" |
| F-12: Factory pattern | T-014 | `tests/unit/core/test_rbac_database.py` | get_rbac_service() returns DatabaseRBACService when RBAC_PROVIDER="database" |
| F-13: Cache behavior | T-015 | `tests/unit/core/test_rbac_database.py` | Second call to has_permission() hits cache (no DB query); <1ms for 1000 cached lookups |
| F-13: Cache invalidation | T-016 | `tests/unit/core/test_rbac_database.py` | After create/update/delete operation, cache is cleared and next read hits DB |
| T-08: Performance | T-017 | `tests/unit/core/test_rbac_database.py` | 1000 cached has_permission() calls complete in <1000ms total |
| B-02: Config switch | T-018 | `tests/unit/core/test_rbac_database.py` | Changing RBAC_PROVIDER setting and resetting singleton returns correct provider type |
| F-09: Frontend RBAC page | T-019 | `RBACConfiguration.test.tsx` | Page renders role table with data from API; create/edit/delete modals work |
| F-09: Read-only state | T-020 | `RBACConfiguration.test.tsx` | When provider is "json", edit buttons hidden and info banner shown |

---

## Test Specification

### Test Hierarchy

```
backend/tests/
  unit/
    core/
      test_rbac.py                        (existing -- regression guard)
      test_rbac_database.py               (new -- DatabaseRBACService)
      providers/
        test_auth_provider.py             (new -- AuthProvider ABC + LocalAuthProvider)
        test_user_provider.py             (new -- UserProvider ABC + LocalUserProvider)
    services/
      test_rbac_admin.py                  (new -- RBAC admin service CRUD)
  integration/
    test_rbac_migration.py                (new -- migration + seed verification)
    test_rbac_admin_api.py                (new -- Admin API endpoint tests)

frontend/src/
  pages/admin/
    RBACConfiguration.test.tsx            (new -- component tests)
  features/admin/rbac/
    __tests__/
      useRBACRoles.test.ts                (new -- TanStack Query hooks)
```

### Test Cases (First 5 Priority Tests)

| Test ID | Test Name | Criterion | Type | Verification |
|---|---|---|---|---|
| T-001 | `test_database_rbac_has_permission_seeded_data` | F-01 | Unit | `has_permission("admin", "user-read")` returns True after seeding from rbac.json |
| T-002 | `test_database_rbac_get_user_permissions_viewer` | F-01 | Unit | `get_user_permissions("viewer")` returns exactly ["department-read", "project-read", ...] matching rbac.json |
| T-013 | `test_factory_returns_json_service_by_default` | F-12 | Unit | `get_rbac_service()` with `RBAC_PROVIDER="json"` returns `JsonRBACService` instance |
| T-014 | `test_factory_returns_database_service_when_configured` | F-12 | Unit | `get_rbac_service()` with `RBAC_PROVIDER="database"` returns `DatabaseRBACService` instance |
| T-015 | `test_cache_returns_same_result_without_db_query` | F-13 | Unit | Two consecutive `has_permission()` calls; second call does not execute SQL query |

### Test Infrastructure Needs

- **Fixtures needed:** `rbac_service` fixture returning `DatabaseRBACService` with in-memory test data; `admin_user` fixture with `admin` role for API tests; `viewer_user` fixture with `viewer` role for permission denial tests
- **Database state:** Migration test requires clean database; admin API tests require seeded rbac_roles and rbac_role_permissions tables
- **Frontend mocks:** Mock API responses for `GET /admin/rbac/roles`, `GET /admin/rbac/permissions`, and provider status endpoint

---

## Detailed Design

### Database Schema

**Table: `rbac_roles`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, default uuid4 | Primary key |
| `name` | VARCHAR(100) | NOT NULL, UNIQUE | Role name (e.g., "admin", "viewer") |
| `description` | TEXT | NULLABLE | Human-readable role description |
| `is_system` | BOOLEAN | NOT NULL, DEFAULT false | True for seeded roles that should not be deleted |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default now() | Last update timestamp |

**Table: `rbac_role_permissions`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, default uuid4 | Primary key |
| `role_id` | UUID | NOT NULL, FK -> rbac_roles.id ON DELETE CASCADE | Reference to role |
| `permission` | VARCHAR(100) | NOT NULL | Permission string (e.g., "project-read") |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | Creation timestamp |

**Constraints:**
- `rbac_role_permissions`: UNIQUE (`role_id`, `permission`) -- no duplicate permission assignments
- `rbac_roles`: UNIQUE (`name`) -- role names must be unique

**Indexes:**
- `rbac_role_permissions.role_id` -- foreign key index for join performance
- `rbac_role_permissions.permission` -- index for "list all known permissions" query

### API Endpoint Design

**Base path:** `/api/v1/admin/rbac/`
**Auth requirement:** All endpoints require authenticated user with `admin` role (`RoleChecker(["admin"])`)

| Method | Path | Request Body | Response | Status Codes |
|---|---|---|---|---|
| GET | `/roles` | -- | `[{id, name, description, is_system, permissions: [{id, permission}]}]` | 200 |
| POST | `/roles` | `{name, description?, permissions: [string]}` | `{id, name, description, is_system, permissions}` | 201, 400 (duplicate name), 422 (validation) |
| PUT | `/roles/{id}` | `{name?, description?, permissions?: [string]}` | `{id, name, description, is_system, permissions}` | 200, 404 |
| DELETE | `/roles/{id}` | -- | -- | 204, 404, 400 (system role) |
| GET | `/permissions` | -- | `["project-read", "project-write", ...]` | 200 |

**Additional endpoint:**

| Method | Path | Response | Description |
|---|---|---|---|
| GET | `/provider-status` | `{provider: "json" or "database", editable: boolean}` | Returns current RBAC provider type and whether admin UI should be editable |

### Pydantic Schemas

```
RBACRoleCreate: name (str, min_length=1, max_length=100), description (str | None), permissions (list[str])
RBACRoleUpdate: name (str | None), description (str | None), permissions (list[str] | None)
RBACPermissionRead: id (UUID), permission (str)
RBACRoleRead: id (UUID), name (str), description (str | None), is_system (bool), permissions (list[RBACPermissionRead]), created_at (datetime), updated_at (datetime)
RBACProviderStatus: provider (str), editable (bool)
```

### Frontend Component Design

**Page: `RBACConfiguration`** at `/admin/rbac`

Layout:
1. **Provider indicator banner** at top: Shows current provider type (e.g., "RBAC Provider: JSON (read-only)" or "RBAC Provider: Database"). When JSON provider, includes a message: "To manage roles and permissions, switch to the database provider by setting RBAC_PROVIDER=database in your configuration."
2. **StandardTable** listing roles with columns: Name, Description, Permission Count, Is System, Actions
3. **Create button** (disabled when JSON provider): Opens modal with name, description, and permission multi-select
4. **Edit action** (hidden when JSON provider): Opens modal pre-filled with role data
5. **Delete action** (hidden when JSON provider; disabled for system roles): Confirmation modal
6. **Permissions drawer/panel**: Shows all permissions for a selected role in a tag cloud layout

**Data hooks:**
- `useRBACRoles()`: TanStack Query hook for `GET /admin/rbac/roles`
- `useCreateRBACRole()`: Mutation hook for `POST /admin/rbac/roles`
- `useUpdateRBACRole()`: Mutation hook for `PUT /admin/rbac/roles/{id}`
- `useDeleteRBACRole()`: Mutation hook for `DELETE /admin/rbac/roles/{id}`
- `useRBACPermissions()`: Query hook for `GET /admin/rbac/permissions`
- `useRBACProviderStatus()`: Query hook for `GET /admin/rbac/provider-status`

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | Cache staleness after admin edits causes stale permission checks on concurrent requests | Medium | Low | Invalidate cache on every write operation; TTL safety net (5 min); single-server means no distributed cache issue |
| Technical | Migration seed from rbac.json fails on non-standard JSON format | Low | Medium | Parse rbac.json robustly with error logging; migration validates data before inserting |
| Integration | Active AI RBAC iteration not yet merged, causing merge conflicts | Medium | Medium | This iteration is designed to build ON the AI RBAC changes; complete that iteration first |
| Integration | Factory pattern change to get_rbac_service() breaks tests that set _rbac_service directly | Low | Medium | Preserve `set_rbac_service()` override mechanism; existing tests already use it |
| Technical | DatabaseRBACService does not replicate JsonRBACService project-level access logic | Low | High | DatabaseRBACService reuses the same project membership DB queries; only role-to-permission mapping differs |
| Frontend | OpenAPI client regeneration adds unwanted types or changes existing types | Low | Low | Review generated client diff; pin OpenAPI spec version |

---

## Prerequisites

### Technical

- [x] Active iteration `2026-04-23-standardize-ai-assistant-rbac` merged to `develop`
- [x] `contextvars` session injection available in `rbac.py`
- [x] AI roles (`ai-viewer`, `ai-manager`, `ai-admin`) present in `rbac.json`
- [ ] Database accessible for migration execution
- [ ] Python virtual environment active

### Documentation

- [x] Analysis phase approved
- [x] ADR-007 (RBAC Service Design) reviewed
- [x] EVCS entity classification guide reviewed (SimpleEntityBase for new tables)
- [x] SimpleService pattern reviewed for RBAC admin service

---

## Documentation References

### Required Reading

- ADR-007: `docs/02-architecture/decisions/ADR-007-rbac-service.md`
- EVCS Entity Guide: `docs/02-architecture/backend/contexts/evcs-core/entity-classification.md`
- SimpleService Pattern: `backend/app/core/simple/service.py`
- SimpleEntityBase: `backend/app/core/base/base.py`

### Code References

- Existing RBAC ABC + JsonRBACService: `backend/app/core/rbac.py`
- Auth dependencies pattern: `backend/app/api/dependencies/auth.py`
- Admin page UI pattern: `frontend/src/pages/admin/CostElementTypeManagement.tsx`
- CRUD hooks pattern: `frontend/src/hooks/useCrud.ts`
- StandardTable component: `frontend/src/components/common/StandardTable.tsx`
- Can component (auth): `frontend/src/components/auth/Can.tsx`
- Test pattern (RBAC): `backend/tests/unit/core/test_rbac.py`
- Migration pattern: `backend/alembic/versions/`

---

## Task Dependency Graph

```yaml
# Task Dependency Graph -- Iteration 1: Provider Framework + Database-Backed RBAC + Admin API + Admin UI
#
# Prerequisite: 2026-04-23-standardize-ai-assistant-rbac iteration merged to develop

tasks:
  # === LEVEL 0: Foundation (no dependencies, can run in parallel) ===

  - id: BE-001
    name: "Add RBAC/AUTH/USER provider settings to config.py"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Create AuthProvider ABC + LocalAuthProvider in core/providers/"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Create UserProvider ABC + LocalUserProvider in core/providers/"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-004
    name: "Create RBACRole and RBACRolePermission domain models"
    agent: pdca-backend-do-executor
    dependencies: []

  # === LEVEL 1: Database layer ===

  - id: BE-005
    name: "Create Alembic migration for rbac_roles + rbac_role_permissions tables with seed from rbac.json"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-006
    name: "Implement DatabaseRBACService with cache layer"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-004]

  # === LEVEL 2: Service + API ===

  - id: BE-007
    name: "Update get_rbac_service() factory for provider selection"
    agent: pdca-backend-do-executor
    dependencies: [BE-006]

  - id: BE-008
    name: "Create RBAC admin Pydantic schemas"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-009
    name: "Create RBAC admin service (SimpleService wrapper)"
    agent: pdca-backend-do-executor
    dependencies: [BE-006]

  - id: BE-010
    name: "Create Admin API routes (5 endpoints) and register in main.py"
    agent: pdca-backend-do-executor
    dependencies: [BE-007, BE-008, BE-009]

  # === LEVEL 3: Backend tests (sequential -- share database) ===

  - id: BE-011
    name: "Unit tests: DatabaseRBACService (RBACServiceABC methods, cache, invalidation, performance)"
    agent: pdca-backend-do-executor
    dependencies: [BE-006, BE-007]
    kind: test

  - id: BE-012
    name: "Unit tests: RBAC admin service CRUD"
    agent: pdca-backend-do-executor
    dependencies: [BE-009]
    kind: test

  - id: BE-013
    name: "Unit tests: AuthProvider and UserProvider ABCs + local implementations"
    agent: pdca-backend-do-executor
    dependencies: [BE-002, BE-003]
    kind: test

  - id: BE-014
    name: "Integration tests: Admin API endpoints (auth, CRUD, error cases)"
    agent: pdca-backend-do-executor
    dependencies: [BE-010, BE-011, BE-012]
    kind: test

  - id: BE-015
    name: "Integration test: Migration + seed verification"
    agent: pdca-backend-do-executor
    dependencies: [BE-005]
    kind: test

  # === LEVEL 4: Frontend (depends on backend API being available) ===

  - id: FE-001
    name: "Regenerate OpenAPI client types"
    agent: pdca-frontend-do-executor
    dependencies: [BE-010]

  - id: FE-002
    name: "Create RBAC admin TanStack Query hooks (CRUD + provider status)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-003
    name: "Create RBAC Configuration page with table, modals, provider indicator"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-004
    name: "Register /admin/rbac route in routes/index.tsx"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  - id: FE-005
    name: "Frontend tests: RBAC Configuration page + hooks"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003, FE-004]
    kind: test
```

### Execution Order Summary

```
Level 0 (parallel):  BE-001, BE-004
Level 1 (parallel):  BE-002, BE-003 (after BE-001), BE-005, BE-006
Level 2 (parallel):  BE-007, BE-008, BE-009 (after respective L1 deps)
Level 3:             BE-010 (after BE-007 + BE-008 + BE-009)
Tests (sequential):  BE-011, BE-012, BE-013, BE-014, BE-015
Frontend (parallel): FE-001 (after BE-010), then FE-002 -> FE-003 -> FE-004 -> FE-005
```

Note: Backend test tasks (BE-011 through BE-015) share the database and should be executed sequentially to avoid data conflicts. The `kind: test` metadata signals this constraint to the orchestrator.

---

## Iteration-Level Success Gate

Before marking this iteration as complete, ALL of the following must be true:

1. `RBAC_PROVIDER=database` activates DatabaseRBACService and all 6 seeded roles from rbac.json are queryable
2. `RBAC_PROVIDER=json` (default) causes zero regression in existing tests
3. All 5 admin API endpoints return correct status codes and data shapes
4. Non-admin users receive 403 on all admin RBAC endpoints
5. Frontend `/admin/rbac` page renders roles table and respects provider editable state
6. `uv run mypy app/` reports zero errors
7. `uv run ruff check .` reports zero errors
8. `npm run lint` reports zero errors
9. New code test coverage >= 80% (both backend and frontend)
10. All pre-existing tests continue to pass
