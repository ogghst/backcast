# Analysis: UI Role Management Alignment with Unified RBAC

**Created:** 2026-05-10
**Request:** Align the frontend UI with the new unified RBAC role management system introduced in the 2026-05-10-unified-rbac-refactoring iteration. The backend now has `UserRoleAssignment` with scoped assignments (GLOBAL/PROJECT/CHANGE_ORDER) and a delegation pattern where `RoleChecker`/`ProjectRoleChecker` check the unified system first, falling back to legacy data. The frontend still displays users with a single `User.role` field and manages project members via the separate `ProjectMember` API.

---

## Clarified Requirements

### Functional Requirements

1. **User List page must show unified role assignments** -- A user can now have multiple scoped role assignments (global admin, project manager on Project A, viewer on Project B). The current `UserList.tsx` displays only a single `User.role` tag.
2. **Admin UI for managing role assignments** -- Admins need the ability to create, view, update, and delete `UserRoleAssignment` records via the `/api/v1/role-assignments` API.
3. **Project Member Manager must be aware of the unified system** -- Currently `ProjectMemberManager.tsx` uses a separate `ProjectMember` API and its own `ProjectRole` enum. These project-scoped roles are now also tracked in `UserRoleAssignment` with `scope_type=PROJECT`.
4. **User creation/editing must handle the transition** -- The `UserModal` form currently edits a single `role` field. With unified RBAC, the "global role" is one assignment among potentially many.

### Non-Functional Requirements

- **No backend changes required** -- The API is already built and working via delegation.
- **Backward compatibility** -- Both legacy and unified data sources must be displayed correctly during the transition. The backend delegation pattern means existing permission checks (`usePermission`, `<Can>`) continue to work.
- **Performance** -- Role assignment lists should load efficiently; avoid N+1 queries when displaying assignments per user.
- **Follow existing frontend patterns** -- TanStack Query for data fetching, Zustand for client state, feature-based organization, Ant Design components.

### Constraints

- Frontend-only changes (no backend API modifications).
- Must not break existing `usePermission()`, `<Can>`, or `hasRole()` checks.
- The backend `RoleChecker`/`ProjectRoleChecker` delegation pattern means the system works even without frontend changes -- this is a UI alignment, not a functional fix.
- The `ProjectMember` API continues to work (backend has not removed it).

---

## Context Discovery

### Product Scope

- Role management is a cross-cutting admin concern.
- Primary users: System administrators managing user access, project managers managing project team membership.
- Business requirement: A single coherent view of "who has what access where" across global, project, and change order scopes.

### Architecture Context

**Bounded contexts involved:**
- Auth Context (Shared Kernel) -- authorization is cross-cutting
- User Management Context -- user domain, global role display
- Project Management Context -- project member management

**Existing patterns to follow:**
- TanStack Query hooks pattern: `useRBACRoles()` in `frontend/src/features/admin/rbac/hooks/useRBAC.ts`
- Query key factory: `queryKeys` in `frontend/src/api/queryKeys.ts`
- API client pattern: direct `apiClient` calls for non-generated endpoints (same as RBAC admin)
- Ant Design StandardTable for list views
- UserModal pattern for create/edit forms

**Key architectural constraint:** The `useAuthStore` stores `permissions` (string array) and `user.role` (single string). These power `usePermission()` and `<Can>`. These must NOT change -- they work at the permission level, not the assignment level.

### Codebase Analysis

**Backend (already implemented):**

- `backend/app/api/routes/user_role_assignments.py` -- Full CRUD API at `/api/v1/role-assignments`
- `backend/app/models/schemas/user_role_assignment.py` -- Schemas: `UserRoleAssignmentCreate`, `UserRoleAssignmentUpdate`, `UserRoleAssignmentRead` (enriched with `role_name`, `user_name`, `granted_by_name`)
- `backend/app/core/rbac_unified.py` -- `UnifiedRBACService` with cache-first permission checking
- `backend/app/api/dependencies/auth.py` -- Delegation pattern: `RoleChecker`/`ProjectRoleChecker` try unified first, fall back to legacy

**Frontend (current state):**

- `frontend/src/pages/admin/UserList.tsx` -- Shows `User.role` as single tag, no awareness of scoped assignments
- `frontend/src/features/users/components/UserModal.tsx` -- Edit form with single `role` Select field
- `frontend/src/pages/admin/RBACConfiguration.tsx` -- Manages role definitions (RBACRole/RBACRolePermission), NOT assignments. Works fine as-is.
- `frontend/src/features/projects/components/ProjectMemberManager.tsx` -- Uses legacy `ProjectMember` API, own `ProjectRole` enum
- `frontend/src/features/projects/hooks/useProjectMembers.ts` -- TanStack Query hooks for `/api/v1/projects/{id}/members`
- `frontend/src/types/user.ts` -- `User.role` as single string field
- `frontend/src/api/types/rbac.ts` -- Only has RBACRole types, no UserRoleAssignment types
- `frontend/src/api/queryKeys.ts` -- No query keys for role assignments
- `frontend/src/stores/useAuthStore.ts` -- `hasRole()` checks `user.role` (single string)
- `frontend/src/hooks/usePermission.ts` -- Uses `useAuthStore` permissions array
- `frontend/src/components/auth/Can.tsx` -- Uses `useAuthStore.hasPermission()` and `hasRole()`

**Key insight:** The permission infrastructure (`usePermission`, `<Can>`, `useAuthStore.hasPermission`) operates on the **permission** level (string arrays) and does not need to change. The `hasRole()` method checks `user.role` which is still populated by the backend from legacy data. The only things that need to change are the **admin-facing role assignment management** and **display of role information**.

---

## Solution Options

### Option 1: Add Unified Role Assignment Admin Page (Minimal Overlay)

**Architecture & Design:**

Add a new "Role Assignments" admin page that provides full CRUD for `UserRoleAssignment` via the `/api/v1/role-assignments` API. Keep existing `UserList.tsx` and `ProjectMemberManager.tsx` as-is, but add a visual indicator and link to the new unified view.

- New feature directory: `frontend/src/features/admin/role-assignments/`
- New page: `frontend/src/pages/admin/RoleAssignments.tsx`
- New hooks: `useRoleAssignments.ts` (list, create, update, delete)
- New types: Add `UserRoleAssignment` types to `frontend/src/api/types/rbac.ts`
- Add query keys for role assignments to `queryKeys.ts`
- Modify `UserList.tsx` to show a summary of unified assignments alongside the legacy `role` field (read-only Tags showing assigned roles)
- `ProjectMemberManager.tsx` stays unchanged -- it continues using the `ProjectMember` API which works via backend delegation

**UX Design:**

- New admin page "Role Assignments" with a table showing: user name, role name, scope type (Global/Project/Change Order), scope entity name, granted by, granted at, expiration, actions.
- Filters: by user, by scope type, by scope entity.
- Create modal: user selector, role selector (from existing RBAC roles), scope type selector, scope entity selector (conditional on scope type), optional expiration date.
- In `UserList.tsx`: add a "View Assignments" button per user row that navigates to the Role Assignments page filtered by that user. Optionally display the primary (global) role assignment as a tag.
- The existing "Role" column in UserList.tsx continues showing `User.role` from legacy data but gets a supplementary info icon or tooltip showing "Unified: X assignments" count.

**Implementation:**

**Key files to create:**
- `frontend/src/api/types/roleAssignment.ts` -- TypeScript types mirroring backend schemas
- `frontend/src/features/admin/role-assignments/hooks/useRoleAssignments.ts` -- TanStack Query hooks
- `frontend/src/pages/admin/RoleAssignments.tsx` -- Main admin page
- `frontend/src/features/admin/role-assignments/components/AssignmentModal.tsx` -- Create/edit modal

**Key files to modify:**
- `frontend/src/api/queryKeys.ts` -- Add `roleAssignments` key factory
- `frontend/src/pages/admin/UserList.tsx` -- Add "View Assignments" action button, show assignment count
- Router config -- Add `/admin/role-assignments` route

**No changes to:**
- `useAuthStore.ts` -- permission checking stays the same
- `usePermission.ts` / `Can.tsx` -- operate at permission level, not affected
- `RBACConfiguration.tsx` -- role definitions, not assignments
- `ProjectMemberManager.tsx` -- continues using its own API (backend delegation handles consistency)

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros | Minimal surface area of change; new functionality is additive; no risk to existing flows; admin gets unified view; ProjectMemberManager continues working; clear separation between "manage roles" (RBACConfiguration) and "assign roles" (new page) |
| Cons | Two separate systems visible to users (legacy UserList role + unified assignments page); ProjectMemberManager still uses old API; UserList still shows legacy `User.role` field; admin must manage global and project roles in different places during transition |
| Complexity | Low |
| Maintainability | Good -- new code is isolated in its own feature directory |
| Performance | Good -- single API call for assignment list, no N+1 |

---

### Option 2: Unified User Detail with Integrated Assignment Management

**Architecture & Design:**

Transform the user management experience from a flat list to a master-detail pattern. Keep `UserList.tsx` as the master list, but enhance it to show a summary of role assignments per user. Replace the `UserModal` role field with a full role assignment section. Replace `ProjectMemberManager.tsx` with the unified assignment API.

- Same new hooks and types as Option 1
- **Modify** `UserList.tsx` to replace the single "Role" column with a "Roles" column showing all scope-tagged assignments
- **Modify** `UserModal.tsx` to remove the `role` field and instead show a role assignments section where admins can add/remove scoped roles inline
- **Modify** `ProjectMemberManager.tsx` to use the unified `/api/v1/role-assignments` API instead of the `ProjectMember` API
- Keep the legacy `User.role` field hidden but functional for backward compatibility

**UX Design:**

- `UserList.tsx`: Replace single Tag with a list of scope-aware tags: `[Admin (Global)]`, `[Manager - Project A]`, `[Viewer - Project B]`
- `UserModal.tsx`: Replace role dropdown with an assignment table/section. Each row: scope type (select), scope entity (select, conditional), role (select from RBAC roles), expiration (optional). Add/remove rows.
- `ProjectMemberManager.tsx`: Replace `useProjectMembers` hooks with unified assignment hooks filtered by `scope_type=PROJECT` and `scope_id=projectId`. Same UX (member list with role dropdowns) but backed by the unified API.
- New admin page for bulk assignment management (optional, same as Option 1).

**Implementation:**

**Key files to create (same as Option 1):**
- `frontend/src/api/types/roleAssignment.ts`
- `frontend/src/features/admin/role-assignments/hooks/useRoleAssignments.ts`

**Key files to modify (more than Option 1):**
- `frontend/src/api/queryKeys.ts` -- Add role assignment keys
- `frontend/src/pages/admin/UserList.tsx` -- Replace Role column with multi-assignment display
- `frontend/src/features/users/components/UserModal.tsx` -- Replace role field with assignment management
- `frontend/src/features/projects/components/ProjectMemberManager.tsx` -- Migrate to unified API
- `frontend/src/features/projects/hooks/useProjectMembers.ts` -- Replace with unified assignment hooks or add adapter

**Risk areas:**
- `UserModal.tsx` transformation is complex -- managing multiple assignments inline with create/delete API calls
- `ProjectMemberManager.tsx` migration requires careful mapping between `ProjectRole` enum and `RBACRole` IDs
- Both legacy and unified data may coexist, requiring merge logic in the display

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros | Fully unified experience; no separate systems visible to users; single source of truth for role display; ProjectMemberManager uses canonical API; cleaner long-term state |
| Cons | Large surface area of change; modifies 4+ existing components that work; risk of regressions; complex inline assignment management in modal; must handle legacy+unified data merge; `ProjectRole` enum must be mapped to RBACRole IDs |
| Complexity | High |
| Maintainability | Good long-term, but risky transition |
| Performance | Fair -- UserList may need to fetch assignments per user or batch-load all assignments |

---

### Option 3: Minimal Bridge -- Show Unified Roles Read-Only, Keep Legacy Management

**Architecture & Design:**

Add read-only display of unified role assignments in `UserList.tsx` alongside the legacy `User.role` field. Do not add any management UI -- role assignments are managed through the backend API directly or through a future iteration.

- Same types and query keys as Option 1, but only query hooks (no mutations)
- Modify `UserList.tsx` to fetch all role assignments and display them alongside the legacy role
- Do NOT modify `UserModal.tsx` -- keep the single role field as-is
- Do NOT modify `ProjectMemberManager.tsx` -- keep using ProjectMember API
- Do NOT create a new admin page

**UX Design:**

- `UserList.tsx`: Add a "Unified Roles" column showing multiple scope-tagged tags. The legacy "Role" column remains.
- No new pages, no new modals, no new management interfaces.
- Visual indicator showing the transition state: legacy role + unified assignments.

**Implementation:**

**Key files to create:**
- `frontend/src/api/types/roleAssignment.ts` -- Types only
- `frontend/src/features/admin/role-assignments/hooks/useRoleAssignments.ts` -- Query hooks only

**Key files to modify:**
- `frontend/src/api/queryKeys.ts` -- Add role assignment keys
- `frontend/src/pages/admin/UserList.tsx` -- Add unified roles column

**No changes to:**
- `UserModal.tsx`, `ProjectMemberManager.tsx`, `RBACConfiguration.tsx`, router

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros | Smallest possible change; zero risk to existing flows; provides visibility into unified system; easy to validate; clear stepping stone |
| Cons | Read-only -- admins cannot manage assignments from UI; two role displays (legacy + unified) may confuse; no path to replacing legacy system; does not solve the ProjectMemberManager migration question |
| Complexity | Very Low |
| Maintainability | Poor long-term -- read-only display without management is not useful |
| Performance | Good -- single batch query for all assignments |

---

## Comparison Summary

| Criteria | Option 1 (New Admin Page) | Option 2 (Unified Detail) | Option 3 (Read-Only Bridge) |
|----------|--------------------------|--------------------------|-----------------------------|
| Development Effort | 2-3 days | 5-7 days | 0.5-1 day |
| Risk to Existing Flows | None | Medium (modifies 4+ components) | None |
| User Value | Full CRUD management | Full CRUD + integrated experience | Visibility only |
| Completeness | Partial (admin gets tool, but ProjectMemberManager unchanged) | Complete (all surfaces unified) | Minimal (read-only) |
| Maintainability | Good | Good (after transition) | Poor (dead-end) |
| ProjectMemberManager Migration | Deferred to separate iteration | Included | Not addressed |
| Best For | Incremental delivery with low risk | Complete overhaul in one pass | Quick validation of backend integration |

---

## Recommendation

**I recommend Option 1: Add Unified Role Assignment Admin Page** because:

1. **Risk containment** -- No existing components are modified except a minor addition to UserList (an action button). All new functionality is in new files.
2. **Delivers immediate value** -- Admins get a working CRUD interface for managing scoped role assignments across global, project, and change order scopes.
3. **Follows established pattern** -- The RBACConfiguration page already manages role definitions. A parallel "Role Assignments" page manages role assignments. Clean conceptual separation.
4. **Defers ProjectMemberManager migration** -- The backend delegation pattern means ProjectMemberManager continues working correctly. Migrating it to the unified API can be a separate iteration with focused scope.
5. **Incremental** -- After Option 1 is stable, Option 2's improvements (UserList integration, ProjectMemberManager migration) can be delivered incrementally.

**Alternative consideration:** Choose Option 2 if the project requires a fully unified experience immediately and the team can absorb the risk of modifying multiple working components simultaneously. Choose Option 3 only as a quick validation step before Option 1.

---

## Decision Questions

1. **Should the new Role Assignments admin page be the primary management surface, or should role assignment be embedded within the UserList/UserModal?** The recommendation is a separate admin page for clean separation, but embedding in user management is also valid.

2. **Should ProjectMemberManager.tsx be migrated to the unified API in this iteration or deferred?** The recommendation is to defer it, since the backend delegation pattern makes both APIs functionally equivalent. Migration is a separate task with its own testing surface.

3. **Should the UserList.tsx "Role" column show the legacy `User.role` field, the unified assignments, or both during transition?** The recommendation is to keep the legacy column and add a "View Assignments" action, avoiding data merge complexity.

4. **Should the `UserModal.tsx` role field remain as-is (editing `User.role`), or should it be changed to create a GLOBAL-scoped `UserRoleAssignment`?** The recommendation is to keep it as-is for now. The backend migration script (`20260510b_migrate_existing_roles_to_unified_rbac.py`) already syncs `User.role` to `UserRoleAssignment`. Changing the modal to use the unified API is part of a future "remove legacy field" iteration.

---

## Scope Boundaries

**In scope (Option 1):**
- TypeScript types for `UserRoleAssignment` schemas
- TanStack Query hooks for role assignment CRUD
- Query key factory entries for role assignments
- New "Role Assignments" admin page with table, filters, and CRUD modal
- Router addition for `/admin/role-assignments`
- Minor enhancement to `UserList.tsx` (action button to view user's assignments)

**Out of scope:**
- Changes to `useAuthStore`, `usePermission`, `<Can>` -- these work at the permission level
- Changes to `RBACConfiguration.tsx` -- this manages role definitions, not assignments
- Migration of `ProjectMemberManager.tsx` to unified API
- Removal or deprecation of `User.role` field in `UserModal.tsx`
- Changes to `ProjectMember` types or hooks
- Changes to change order approval UI (`useCanApprove.ts`)
- Backend API changes

---

## References

### Architecture Documentation
- [Unified RBAC Analysis](/home/nicola/dev/backcast/docs/03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/00-analysis.md)

### Backend API
- `backend/app/api/routes/user_role_assignments.py` -- CRUD endpoints at `/api/v1/role-assignments`
- `backend/app/models/schemas/user_role_assignment.py` -- `UserRoleAssignmentRead` schema with `role_name`, `user_name`, `granted_by_name` enrichment
- `backend/app/core/rbac_unified.py` -- `UnifiedRBACService` with scoped role assignment logic
- `backend/app/api/dependencies/auth.py` -- Delegation pattern (unified first, legacy fallback)

### Frontend Files
- `frontend/src/pages/admin/UserList.tsx` -- Current user list with single role display
- `frontend/src/features/users/components/UserModal.tsx` -- User create/edit with single role field
- `frontend/src/pages/admin/RBACConfiguration.tsx` -- Role definition management (works as-is)
- `frontend/src/features/projects/components/ProjectMemberManager.tsx` -- Project member management (stays as-is)
- `frontend/src/features/admin/rbac/hooks/useRBAC.ts` -- Pattern to follow for new hooks
- `frontend/src/api/types/rbac.ts` -- Where to add new types
- `frontend/src/api/queryKeys.ts` -- Where to add new query keys
- `frontend/src/stores/useAuthStore.ts` -- Permission state (no changes needed)
