# Analysis: Unified RBAC Post-E2E Bugfix

**Created:** 2026-05-11
**Request:** Address 1 unfixed data/architecture bug and 3 open findings from project role CRUD E2E testing. Bugs 1-3 (Pydantic alias, query param mismatch, MissingGreenlet) were fixed inline. Bug 4 (migration gap) and Findings 1-3 require architectural decisions and code changes.

---

## Clarified Requirements

### Functional Requirements

- **FR-1:** The data migration MUST correctly populate `user_role_assignments` with project-scoped entries from `project_members`, resolving the role name mismatch between `project_members.role` (e.g., `project_admin`, `project_editor`) and `rbac_roles.name` (e.g., `admin`, `manager`, `viewer`).
- **FR-2:** Non-admin users with project-scoped role assignments in `user_role_assignments` MUST be able to access project pages. The unified RBAC path (`ProjectRoleChecker` -> `UnifiedRBACService.has_permission`) MUST work for project-level permission checks without requiring fallback to legacy `ProjectMember` queries.
- **FR-3:** The "Add Member" role dropdown in the Project Settings page MUST show only roles applicable at project scope (admin, manager, viewer), filtering out AI-specific roles and `change_order_approver`.
- **FR-4:** The Admin Role Assignments page MUST display user names alongside role assignments, not raw UUIDs or dash marks.

### Non-Functional Requirements

- **NFR-1:** No regression in existing admin or manager access patterns.
- **NFR-2:** Migration must be idempotent and reversible.
- **NFR-3:** Permission checks must remain performant (cache-first, no N+1 queries).
- **NFR-4:** The transition away from `ProjectMember`-based legacy checks must be gradual -- both systems must coexist until full cutover.

### Constraints

- The `rbac_roles` table already has 7 roles seeded. Adding new roles requires a migration and seed data update.
- The `user_role_assignments` unique constraint is `(user_id, scope_type, scope_id)` -- one role per user per scope.
- The frontend `ProjectMemberManager` already delegates to `useRoleAssignments` hooks; it does not use the legacy `project_members` API endpoints.
- The `read_projects` list endpoint in `app/api/routes/projects.py` directly calls `rbac_service.get_user_projects()` which queries `project_members`. This is the critical legacy path.

---

## Context Discovery

### Product Scope

- The unified RBAC system was designed to replace three separate authorization mechanisms with a single `user_role_assignments` table (see `app/models/domain/user_role_assignment.py` docstring).
- Project-scoped access is a core requirement: users who are project members must see and interact with their assigned projects.

### Architecture Context

- **Bounded contexts involved:** Identity & Access Management (RBAC), Project Management
- **Existing pattern:** `ProjectRoleChecker` in `app/api/dependencies/auth.py` tries `UnifiedRBACService.has_permission()` first, then falls back to legacy `RBACServiceABC.has_project_access()` which queries `project_members`.
- **Architectural constraint (ADR):** The EVCS system uses `user_id` (root ID, not PK) for foreign keys. `user_role_assignments.user_id` references `users.user_id` (root ID).

### Codebase Analysis

**Backend -- Legacy paths still querying `project_members`:**

1. `app/core/rbac.py` -- `JsonRBACService.has_project_access()` (line 461): queries `ProjectMember`
2. `app/core/rbac.py` -- `JsonRBACService.get_user_projects()` (line 527): queries `ProjectMember`
3. `app/core/rbac.py` -- `JsonRBACService.get_project_role()` (line 576): queries `ProjectMember`
4. `app/core/rbac_database.py` -- `DatabaseRBACService`: same three methods, same queries
5. `app/api/routes/projects.py` (line 114): `read_projects` calls `rbac_service.get_user_projects()`
6. `app/services/approval_matrix_service.py` (line 163): queries `ProjectMember` for approver lookup
7. `app/services/global_search_service.py` (line 388): calls `rbac_service.get_user_projects()`
8. `app/ai/tools/context_tools.py` (line 302): calls `rbac_service.get_user_projects()`
9. `app/ai/tools/project_tools.py` (line 86): calls `rbac_service.get_user_projects()`
10. `app/ai/middleware/backcast_security.py` (line 244): calls `rbac_service.has_project_access()`
11. `app/ai/tools/rbac_tool_node.py` (line 114): calls `rbac_service.has_project_access()`
12. `app/ai/tools/types.py` (line 313): calls `rbac_service.has_project_access()`

**Total: 12 call sites** still read from `project_members` through the legacy RBAC service.

**Backend -- The `ProjectRoleChecker` fallback chain:**

```
Request arrives
  -> ProjectRoleChecker.__call__()
    -> Try unified: UnifiedRBACService.has_permission(user_id, "project-read", scope_type="project", scope_id=project_id)
       -> get_user_roles(user_id, "global", None) -> checks user_role_assignments
       -> get_user_roles(user_id, "project", project_id) -> checks user_role_assignments
       -> _check_permission_from_roles() -> checks permissions cache from rbac_roles
    -> If unified fails/returns false -> Fallback: JsonRBACService.has_project_access()
       -> Queries project_members table
```

The unified path works correctly in isolation. The problem is that:
1. No project-scoped assignments exist in `user_role_assignments` (Bug #4: migration failed)
2. The `read_projects` list endpoint never goes through `ProjectRoleChecker` at all -- it calls `rbac_service.get_user_projects()` directly

**Frontend:**

- `ProjectMemberManager.tsx` already delegates to `useRoleAssignments` hooks
- `useProjectMembers.ts` maps `UserRoleAssignmentRead` -> `ProjectMemberRead` shape
- The role dropdown iterates `roles` from `useRBACRoles()` which returns ALL 7 roles
- The `useRoleAssignments` hooks call `/api/v1/role-assignments` (unified API)

**Root Cause Analysis:**

| Issue | Root Cause | Layer |
|-------|-----------|-------|
| Bug #4 | `project_members.role` uses `project_admin`/`project_editor`/`project_viewer` but `rbac_roles.name` has `admin`/`manager`/`viewer`/`ai-*`/`change_order_approver`. Migration `JOIN rbac_roles r ON r.name = pm.role` produces 0 rows. | Data migration |
| Finding #1 | Two problems: (a) no project-scoped assignments exist (Bug #4), so unified RBAC returns no roles; (b) `read_projects` calls `rbac_service.get_user_projects()` directly, which queries `project_members` table (legacy path), NOT `user_role_assignments` | Auth dependency + list endpoint |
| Finding #2 | Role dropdown renders `roles.map(...)` without filtering. All 7 RBAC roles shown. | Frontend |
| Finding #3 | `list_assignments` endpoint does not join `users` table. Schema has `user_name` field but it is never populated. | Backend API |

---

## Solution Options

### Option 1: Minimal Fix -- Role Name Mapping + Dual-Read Path

**Architecture & Design:**

Fix the migration by adding an explicit name mapping clause (`CASE WHEN pm.role = 'project_admin' THEN 'admin' WHEN pm.role = 'project_editor' THEN 'manager' ... END`) so project members are migrated into existing `rbac_roles`. Keep both the unified RBAC and legacy `project_members` read paths active. Add user enrichment to the list endpoint.

**UX Design:**

- No UX changes for project access (fixes are backend-only).
- Role dropdown still shows all 7 roles (not addressed in this option).
- Admin page shows user names after enrichment fix.

**Implementation:**

1. **Migration fix** (Bug #4): Write a new Alembic migration that re-runs the project member migration with a `CASE` mapping:
   - `project_admin` -> `admin`
   - `project_manager` -> `manager`
   - `project_editor` -> `manager`
   - `project_viewer` -> `viewer`
2. **List endpoint fix** (Finding #1, partial): The `ProjectRoleChecker` unified path will now work because project assignments exist. However, `read_projects` still calls `rbac_service.get_user_projects()` directly. Patch this one call site to also check unified RBAC.
3. **User enrichment** (Finding #3): Join `users` table in `list_assignments` to populate `user_name`.
4. **Role dropdown filtering** (Finding #2): Filter in the frontend component to show only `admin`, `manager`, `viewer` when `scopeType === "project"`.

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Minimal migration change; reuses existing roles; no new RBAC roles needed |
| Cons            | Role mapping is lossy (`project_editor` and `project_manager` both map to `manager`); the dual-read path (unified + legacy) persists for 12 call sites; `project_members` table and legacy routes remain active indefinitely |
| Complexity      | Low |
| Maintainability | Fair -- dual system continues, technical debt increases |
| Performance     | Good -- no additional queries |

---

### Option 2: Full Cutover -- Add Project Roles + Migrate Legacy Call Sites

**Architecture & Design:**

Add dedicated project-scoped roles to `rbac_roles` (`project_admin`, `project_manager`, `project_editor`, `project_viewer`) with appropriate permissions that mirror the current `ProjectRole` enum in `app/core/rbac.py`. Migrate the 12 legacy call sites to use `UnifiedRBACService` instead of querying `project_members`. Remove or deprecate the legacy `project_members` API routes and `ProjectMemberService`.

**UX Design:**

- Role dropdown shows 4 project-specific roles with clear labels.
- Admin page shows user names.
- All project access works through the unified system.

**Implementation:**

1. **New migration**: Add 4 project-specific roles to `rbac_roles` with permissions aligned to `ProjectRole` enum.
2. **Seed data update**: Add the 4 new roles to `config/rbac.json` and `seed/rbac_roles.json`.
3. **Data migration**: Map `project_members` entries to the new roles by exact name match.
4. **Migrate `read_projects`** (Finding #1): Replace `rbac_service.get_user_projects()` with unified RBAC query.
5. **Migrate 12 call sites**: Replace all `rbac_service.has_project_access()` / `get_user_projects()` calls with `UnifiedRBACService` equivalents.
6. **Deprecate legacy routes**: Mark `project_members` routes as deprecated (do not remove yet).
7. **User enrichment** (Finding #3): Join users in list endpoint.
8. **Role dropdown filter** (Finding #2): Show project-specific roles in project context, system roles in global context.

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Clean separation of concerns (project roles vs system roles); single source of truth for permissions; eliminates dual-read confusion; paves way for eventual `project_members` table removal |
| Cons            | Larger scope: requires seed data changes, migration, and touching 12+ files; introduces role proliferation (11 total roles); the `ProjectRole` enum in `rbac.py` and `rbac_roles` table must be kept in sync |
| Complexity      | High |
| Maintainability | Good -- single RBAC path, but more roles to manage |
| Performance     | Good -- unified cache-first approach |

---

### Option 3: Hybrid -- Map to Existing Roles + Unify Read Path

**Architecture & Design:**

Use the role mapping from Option 1 (project members map to existing `admin`/`manager`/`viewer` roles) but also consolidate the read path: replace the 12 legacy call sites with unified RBAC queries. This eliminates the dual-read problem while avoiding role proliferation.

**UX Design:**

- Role dropdown shows 3 applicable roles (admin, manager, viewer) filtered by context.
- Admin page shows user names.
- All project access works through unified RBAC.

**Implementation:**

1. **Migration fix** (Bug #4): Same `CASE` mapping as Option 1.
2. **Unify `read_projects`** (Finding #1): Replace `rbac_service.get_user_projects()` with a new method on `UnifiedRBACService` that returns project IDs a user has access to.
3. **Add `get_accessible_projects()` to UnifiedRBACService**: Queries `user_role_assignments` with `scope_type='project'` for the given user.
4. **Migrate critical call sites**: Update `read_projects`, `global_search_service`, and the AI tools to use `UnifiedRBACService` instead of legacy RBAC.
5. **Keep legacy as safety net**: Leave `ProjectRoleChecker` fallback chain intact. Legacy routes remain active but are no longer the primary path.
6. **User enrichment** (Finding #3): Join users in list endpoint.
7. **Role dropdown filter** (Finding #2): Filter to show only `admin`, `manager`, `viewer` in project context.

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Moderate scope; eliminates the critical dual-read bug; no new roles needed; `read_projects` and other endpoints use unified RBAC; keeps legacy as safety net during transition |
| Cons            | Lossy role mapping (`project_editor` -> `manager`) loses granularity; `project_members` table still exists alongside `user_role_assignments` (dual writes possible); some call sites still have legacy fallback |
| Complexity      | Medium |
| Maintainability | Good -- clear migration path toward full cutover |
| Performance     | Good -- fewer legacy queries, cache-first |

---

## Comparison Summary

| Criteria           | Option 1 (Minimal)       | Option 2 (Full Cutover)    | Option 3 (Hybrid)           |
| ------------------ | ------------------------ | -------------------------- | --------------------------- |
| Development Effort | ~1 day                   | ~3-4 days                  | ~2 days                     |
| UX Quality         | Partial (Finding #2 not fully addressed) | Complete          | Complete                    |
| Flexibility        | Low (dual system stays)  | High (clean architecture)  | Medium (pragmatic middle)   |
| Risk               | Low (targeted changes)   | Medium (large scope, 12+ files) | Low-Medium (moderate scope) |
| Best For           | Quick hotfix, unblock users | Final architecture       | Iterative improvement       |
| Addresses All Issues | No (dual-read persists) | Yes                        | Yes (all 4 issues resolved) |

---

## Recommendation

**I recommend Option 3 (Hybrid) because:** it resolves all 4 issues within a manageable 2-day effort, eliminates the critical access bug (Finding #1) by unifying the read path, and positions the project for eventual full removal of the `project_members` table without requiring a big-bang migration. The lossy role mapping (`project_editor` -> `manager`) is acceptable because the original `project_editor` and `project_manager` roles have nearly identical permission sets in the `ProjectRole` enum.

**Alternative consideration:** Choose Option 1 if the immediate priority is unblocking non-admin users within hours and the team cannot allocate 2 days. Choose Option 2 if the team is committed to completing the unified RBAC migration in this iteration and wants to eliminate all legacy paths.

---

## Decision Questions

1. Is the lossy role mapping (`project_editor` -> `manager`) acceptable, or does the business require preserving the editor/manager distinction? If the distinction is required, Option 2 becomes the only viable path.
2. Should we deprecate or disable the legacy `/projects/{id}/members` API endpoints in this iteration, or keep them active as a fallback?
3. For the `read_projects` list endpoint specifically: should non-admin users only see projects where they have a `user_role_assignments` entry, or should the legacy `project_members` table remain the source of truth for project visibility during a transition period?

---

## References

- `backend/app/api/dependencies/auth.py` -- `ProjectRoleChecker` and `RoleChecker` with unified/legacy fallback
- `backend/app/core/rbac_unified.py` -- `UnifiedRBACService` (unified RBAC)
- `backend/app/core/rbac.py` -- `JsonRBACService` (legacy RBAC with `ProjectMember` queries)
- `backend/app/api/routes/projects.py` -- `read_projects` with `rbac_service.get_user_projects()` call
- `backend/app/api/routes/user_role_assignments.py` -- CRUD for unified role assignments
- `backend/alembic/versions/20260510b_migrate_existing_roles_to_unified_rbac.py` -- Broken data migration
- `backend/config/rbac.json` -- RBAC role/permission configuration
- `frontend/src/features/projects/components/ProjectMemberManager.tsx` -- Member management UI
- `frontend/src/features/projects/hooks/useProjectMembers.ts` -- Hooks bridging unified API to legacy shape
- `docs/03-project-plan/technical-debt-register.md` -- TD-095 (migration verification), TD-099 (test DB fixture)
