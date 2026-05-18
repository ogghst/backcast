# Plan: UI Role Management Alignment with Unified RBAC

**Created:** 2026-05-10
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 core + expanded scope (Admin Page + UserList + UserModal + ProjectMemberManager migration)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 (new Role Assignments admin page) expanded to include UserList column replacement, UserModal GLOBAL assignment management, and full ProjectMemberManager API migration.
- **Architecture**: Frontend-only changes. New feature module at `frontend/src/features/admin/role-assignments/` with TanStack Query hooks consuming the existing backend `/api/v1/role-assignments` CRUD API. Modifications to four existing components (UserList, UserModal, ProjectMemberManager, UserProfile navigation) and the router. No backend changes.
- **Key Decisions**:
  1. Scope entity selector uses searchable Ant Design `Select` with `showSearch` for picking PROJECT/CHANGE_ORDER entities
  2. UserList "View Assignments" action navigates to filtered Role Assignments page (URL with `?userId=` query param)
  3. Expiration date omitted from UI (backend supports it, not exposed)
  4. ProjectMemberManager gets full API swap -- replace `useProjectMembers` hooks with unified `/api/v1/role-assignments` calls, UI stays similar
  5. UserList Role column replaced with compact scope-tagged assignment tags (e.g. `[Admin (Global)] [Manager - Project A]`)
  6. UserModal replaces single `role` dropdown with unified GLOBAL-scoped assignment management
  7. Nav placement: Admin menu in UserProfile dropdown, alongside Users and RBAC Configuration
  8. Table filters on Role Assignments page: by user, by scope type, by role
  9. No changes to `useAuthStore`, `usePermission`, `<Can>`, or `RBACConfiguration.tsx`

### Success Criteria

**Functional Criteria:**

- [ ] FC-1: Admin can view all role assignments in a paginated table with columns: user name, role name, scope type, scope entity, granted by, granted at, actions VERIFIED BY: manual UI test + component test
- [ ] FC-2: Admin can create a new role assignment by selecting user, role, scope type, and (conditionally) scope entity VERIFIED BY: component test
- [ ] FC-3: Admin can delete an existing role assignment from the table VERIFIED BY: component test
- [ ] FC-4: Admin can update the role of an existing assignment VERIFIED BY: component test
- [ ] FC-5: Scope entity selector is hidden when scope type is GLOBAL, shown for PROJECT and CHANGE_ORDER VERIFIED BY: component test
- [ ] FC-6: UserList displays scope-tagged role assignment tags per user instead of single legacy Role tag VERIFIED BY: component test
- [ ] FC-7: Clicking "View Assignments" on a UserList row navigates to Role Assignments page filtered by that user VERIFIED BY: component test
- [ ] FC-8: UserModal creates/edits GLOBAL-scoped assignments via unified API instead of editing `User.role` field VERIFIED BY: component test
- [ ] FC-9: ProjectMemberManager uses unified `/api/v1/role-assignments` API with `scope_type=PROJECT` instead of legacy `/api/v1/projects/{id}/members` VERIFIED BY: component test + manual verification
- [ ] FC-10: Role Assignments page is accessible via admin menu (UserProfile dropdown) for admin users VERIFIED BY: manual UI test
- [ ] FC-11: Filters on Role Assignments page work: filter by user, by scope type, by role VERIFIED BY: component test

**Technical Criteria:**

- [ ] TC-1: TypeScript strict mode passes with zero errors for all new and modified files VERIFIED BY: `npm run typecheck`
- [ ] TC-2: ESLint passes with zero errors for all new and modified files VERIFIED BY: `npm run lint`
- [ ] TC-3: Test coverage >= 80% for new feature files (types, hooks, components) VERIFIED BY: `npm run test:coverage`
- [ ] TC-4: All TanStack Query hooks follow the established pattern (apiClient + queryKeys factory + useQuery/useMutation) VERIFIED BY: code review
- [ ] TC-5: Query key factory extended with `roleAssignments` section following hierarchical pattern VERIFIED BY: code review
- [ ] TC-6: No regressions in existing `usePermission()`, `<Can>`, or `hasRole()` checks VERIFIED BY: existing test suite passes
- [ ] TC-7: Cache invalidation works correctly -- creating/deleting/updating assignments invalidates relevant query keys VERIFIED BY: integration test

**Business Criteria:**

- [ ] BC-1: Admin users can manage all role assignments (create, view, edit, delete) from a single unified interface VERIFIED BY: manual acceptance test
- [ ] BC-2: UserList provides accurate visibility into all scoped role assignments per user VERIFIED BY: manual acceptance test

### Scope Boundaries

**In Scope:**

- TypeScript types for `UserRoleAssignment` schemas (mirroring `UserRoleAssignmentRead`, `UserRoleAssignmentCreate`, `UserRoleAssignmentUpdate`)
- TanStack Query hooks for role assignment CRUD (list, create, update, delete)
- Query key factory entries for role assignments
- New "Role Assignments" admin page with StandardTable, filters, and CRUD modal
- Router addition for `/admin/role-assignments`
- Admin menu entry in UserProfile dropdown (between Users and RBAC Configuration)
- UserList Role column replacement with compact scope-tagged assignment tags
- UserList "View Assignments" action button per row
- UserModal replacement of single `role` field with GLOBAL assignment management
- ProjectMemberManager full migration from legacy ProjectMember API to unified role assignments API
- Component tests for all new and modified components

**Out of Scope:**

- Backend API changes (API already exists at `/api/v1/role-assignments`)
- Changes to `useAuthStore`, `usePermission`, `<Can>` -- operate at permission level, unaffected
- Changes to `RBACConfiguration.tsx` -- manages role definitions, not assignments
- Changes to change order approval UI (`useCanApprove.ts`)
- Expiration date UI (backend supports but we do not expose)
- Removal of legacy `User.role` field from backend or types
- Removal of legacy `ProjectMember` API endpoints from backend
- E2E/Playwright tests (component-level tests sufficient for this iteration)

---

## Work Decomposition

### Task Breakdown

| #  | Task | Files | Dependencies | Success Criteria | Complexity |
|----|------|-------|-------------|------------------|------------|
| FE-001 | Add role assignment TypeScript types | `frontend/src/api/types/roleAssignment.ts` | None | Types mirror backend schemas, TypeScript compiles without errors | Low |
| FE-002 | Extend query key factory with roleAssignment keys | `frontend/src/api/queryKeys.ts` | None | `queryKeys.roleAssignments` has all/ list/ detail/ filtered keys, TypeScript compiles | Low |
| FE-003 | Create TanStack Query hooks for role assignments CRUD | `frontend/src/features/admin/role-assignments/hooks/useRoleAssignments.ts` | FE-001, FE-002 | All 4 hooks (useRoleAssignments, useCreateRoleAssignment, useUpdateRoleAssignment, useDeleteRoleAssignment) follow useRBAC.ts pattern, unit tests pass | Medium |
| FE-004 | Create Role Assignments admin page | `frontend/src/pages/admin/RoleAssignments.tsx` | FE-003 | Page renders StandardTable with assignment data, supports filters by user/scope/role, displays enriched data (role_name, user_name, granted_by_name) | Medium |
| FE-005 | Create AssignmentModal component | `frontend/src/features/admin/role-assignments/components/AssignmentModal.tsx` | FE-003 | Modal creates/edits assignments with user selector, role selector, scope type selector, conditional scope entity selector, validation works | High |
| FE-006 | Add route and nav entry for Role Assignments | `frontend/src/routes/index.tsx`, `frontend/src/components/UserProfile.tsx` | FE-004 | `/admin/role-assignments` route renders page, admin menu shows entry between Users and RBAC Config | Low |
| FE-007 | Replace UserList Role column with unified assignment tags | `frontend/src/pages/admin/UserList.tsx` | FE-003 | Role column shows scope-tagged tags per user, "View Assignments" button navigates to filtered page, existing tests updated and pass | Medium |
| FE-008 | Replace UserModal role field with GLOBAL assignment management | `frontend/src/features/users/components/UserModal.tsx` | FE-003 | On create: after user creation, creates GLOBAL assignment. On edit: shows current GLOBAL assignments, allows add/remove. Form no longer sends `role` field for new users | High |
| FE-009 | Migrate ProjectMemberManager to unified API | `frontend/src/features/projects/components/ProjectMemberManager.tsx`, `frontend/src/features/projects/hooks/useProjectMembers.ts` | FE-003 | Uses unified role assignments API with scope_type=PROJECT, role dropdown shows RBAC roles instead of ProjectRole enum, add/remove/update use unified endpoints | High |
| FE-010 | Component tests for all new and modified components | `frontend/src/pages/admin/RoleAssignments.test.tsx`, `frontend/src/features/admin/role-assignments/**/*.test.tsx`, `frontend/src/pages/admin/UserList.test.tsx` (update), `frontend/src/features/users/components/UserModal.test.tsx` (update), `frontend/src/features/projects/components/ProjectMemberManager.test.tsx` (update) | FE-004 through FE-009 | All tests pass, coverage >= 80% for new files, no regressions in existing tests | Medium |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|----------------------|---------|-----------|-------------------|
| FC-1 | T-001 | `RoleAssignments.test.tsx` | Table renders with assignment data showing user name, role name, scope type, scope entity, granted by, granted at columns |
| FC-2 | T-002 | `AssignmentModal.test.tsx` | Create form submits with user, role, scope_type, scope_id; validation requires scope_id for non-GLOBAL scopes |
| FC-3 | T-003 | `RoleAssignments.test.tsx` | Delete button triggers confirmation, calls delete mutation, invalidates list |
| FC-4 | T-004 | `AssignmentModal.test.tsx` | Edit form pre-fills existing assignment data, update mutation fires on submit |
| FC-5 | T-005 | `AssignmentModal.test.tsx` | Scope entity selector hidden when scope_type=GLOBAL, shown for PROJECT and CHANGE_ORDER |
| FC-6 | T-006 | `UserList.test.tsx` | Role column renders multiple scope-tagged Tags per user instead of single Tag |
| FC-7 | T-007 | `UserList.test.tsx` | "View Assignments" button navigates to `/admin/role-assignments?userId={id}` |
| FC-8 | T-008 | `UserModal.test.tsx` | Create flow: after user created, GLOBAL assignment created via unified API. Edit flow: GLOBAL assignments displayed and editable |
| FC-9 | T-009 | `ProjectMemberManager.test.tsx` | Uses role-assignments API with scope_type=PROJECT; add/remove/update operations call unified endpoints |
| FC-10 | T-010 | `UserProfile.test.tsx` (existing) | Admin menu shows "Role Assignments" entry, clicking navigates to `/admin/role-assignments` |
| FC-11 | T-011 | `RoleAssignments.test.tsx` | Filter controls render; selecting user/scope/role filters the displayed table data |
| TC-4 | T-012 | `useRoleAssignments.test.tsx` | Hooks use apiClient, queryKeys factory, proper cache invalidation on mutations |
| TC-7 | T-013 | `useRoleAssignments.test.tsx` | After create/delete/update mutation, relevant query keys are invalidated |

---

## Test Specification

### Test Hierarchy

```text
tests/
  Unit Tests (Vitest + React Testing Library)
  ├── Hook tests
  │   ├── useRoleAssignments.test.tsx -- query and mutation hook behaviors
  │   └── Cache invalidation verification
  ├── Component tests (new)
  │   ├── RoleAssignments.test.tsx -- page render, filters, table interactions
  │   └── AssignmentModal.test.tsx -- create/edit form, validation, conditional fields
  └── Component tests (updated)
      ├── UserList.test.tsx -- new role column, View Assignments button
      ├── UserModal.test.tsx -- GLOBAL assignment management
      └── ProjectMemberManager.test.tsx -- unified API integration
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Expected Result |
|---------|-----------|-----------|------|-----------------|
| T-001 | `test_role_assignments_page_renders_table_with_data` | FC-1 | Component | Table displays columns with enriched data (role_name, user_name, scope_type, granted_by_name, granted_at) |
| T-002 | `test_assignment_modal_create_submits_valid_payload` | FC-2 | Component | Modal submits UserRoleAssignmentCreate with required fields; validation rejects missing scope_id for non-GLOBAL scopes |
| T-003 | `test_delete_assignment_calls_mutation_and_invalidates` | FC-3, TC-7 | Component | Delete button triggers confirmation dialog; on confirm, delete mutation fires and query cache invalidates |
| T-005 | `test_scope_entity_selector_conditional_visibility` | FC-5 | Component | Scope entity Select hidden when GLOBAL selected; visible and required when PROJECT or CHANGE_ORDER selected |
| T-006 | `test_user_list_role_column_shows_scope_tagged_assignments` | FC-6 | Component | Role column renders multiple Tags with scope labels; no single legacy Tag shown |
| T-008 | `test_user_modal_creates_global_assignment_on_user_create` | FC-8 | Component | After user creation succeeds, a GLOBAL role assignment mutation fires with the new user_id and selected role |
| T-009 | `test_project_member_manager_uses_unified_api` | FC-9 | Component | Component queries role-assignments with scope_type=PROJECT; add/remove/update call unified endpoints |
| T-011 | `test_role_assignments_page_filters_by_scope_type` | FC-11 | Component | Selecting a scope type filter passes the filter param to the query and updates displayed data |
| T-012 | `test_use_role_assignments_hooks_use_query_keys_factory` | TC-4 | Hook | Hooks reference queryKeys.roleAssignments keys; mutations invalidate all/list keys |
| T-013 | `test_create_assignment_invalidates_role_assignment_cache` | TC-7 | Hook | After create mutation resolves, queryClient.invalidateQueries called with roleAssignments.all key |

### Test Infrastructure Needs

- **MSW handlers**: Add handlers for `/api/v1/role-assignments` CRUD (GET, POST, PUT, DELETE) in `src/mocks/handlers.ts` or test-level setup
- **Mock data**: Sample `UserRoleAssignmentRead` objects with varied scope_types (GLOBAL, PROJECT, CHANGE_ORDER)
- **Existing test updates**: UserList.test.tsx and ProjectMemberManager.test.tsx need updated mocks to reflect new data flow
- **Fixture needs**: Mock RBAC roles list for role selector dropdowns (reuse existing `useRBACRoles` mock data)

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|-----------|-------------|-------------|--------|------------|
| Technical | ProjectRole-to-RBACRole mapping in PMM migration -- legacy `ProjectRole` enum values (project_admin, project_manager, etc.) must map to RBAC role UUIDs | Medium | High | Query `/api/v1/admin/rbac/roles` to get role list, then match by name convention (project_admin -> RBAC role with name "Project Admin"). Log a warning for unmappable roles. |
| Technical | UserModal now creates user AND assignment in two sequential API calls -- first call success + second call failure leaves orphaned user | Low | Medium | Create user first, then create GLOBAL assignment. If assignment fails, show error but keep user. The admin can manually assign the role from Role Assignments page. |
| Technical | UserList performance when fetching assignments for all users -- potential N+1 or large payload | Low | Medium | Fetch all assignments in a single query (backend returns full list). Group by user_id in the frontend. Backend list endpoint already supports batch with enrichment. |
| Integration | Legacy and unified data coexisting during transition -- UserList may show both legacy role and unified assignments | Medium | Low | Replace legacy Role column entirely. Do not display `User.role` tag at all. Show only unified assignment tags. The backend migration script has already synced legacy roles to unified assignments. |
| Regression | PMM migration breaks existing project member management flows | Medium | High | Implement PMM migration as last task (FE-009). Verify all existing PMM test cases still pass with the new API integration. Keep the legacy `useProjectMembers.ts` file but replace its internals to call the unified API. |
| UX | Scope entity selector for CHANGE_ORDER requires fetching change orders list, which may be large | Low | Low | Use Ant Design Select with `showSearch` and server-side search. Fetch change orders for the selected project only. For now, implement basic searchable select; pagination can be added later if needed. |

---

## Documentation References

### Required Reading

- Backend API routes: `backend/app/api/routes/user_role_assignments.py`
- Backend schemas: `backend/app/models/schemas/user_role_assignment.py`
- Backend domain model: `backend/app/models/domain/user_role_assignment.py` (ScopeType enum)
- Existing hooks pattern: `frontend/src/features/admin/rbac/hooks/useRBAC.ts`
- Query key factory: `frontend/src/api/queryKeys.ts`
- API client setup: `frontend/src/api/client.ts`

### Code References

- Backend CRUD API: `backend/app/api/routes/user_role_assignments.py` -- endpoints for list (GET with filters), create (POST), update (PUT), delete (DELETE)
- Frontend hooks pattern: `frontend/src/features/admin/rbac/hooks/useRBAC.ts` -- use as template for new hooks
- Frontend table pattern: `frontend/src/pages/admin/UserList.tsx` -- StandardTable usage with toolbar, columns, actions
- Frontend modal pattern: `frontend/src/features/users/components/UserModal.tsx` -- Ant Design Modal with Form
- Frontend admin nav: `frontend/src/components/UserProfile.tsx` lines 53-128 -- getAdminItems() function
- Frontend router: `frontend/src/routes/index.tsx` -- route definitions
- PMM current hooks: `frontend/src/features/projects/hooks/useProjectMembers.ts` -- hooks to be replaced
- PMM types: `frontend/src/features/projects/types/projectMembers.ts` -- ProjectRole enum to map from

---

## Prerequisites

### Technical

- [x] Backend `/api/v1/role-assignments` CRUD API deployed and functional
- [x] Backend `user_role_assignments` table and migration exist
- [x] Backend delegation pattern (unified first, legacy fallback) in place
- [x] Frontend dependencies installed (Ant Design, TanStack Query, React Router)

### Documentation

- [x] Analysis phase approved (`00-analysis.md`)
- [x] Backend API routes reviewed
- [x] Frontend patterns (useRBAC, queryKeys, StandardTable) reviewed

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
# All tasks are frontend-only. The backend API already exists.
# FE-001 and FE-002 have no dependencies and can start immediately in parallel.
# FE-003 depends on both types and query keys.
# FE-004 through FE-009 depend on hooks being ready.
# FE-010 (tests) is split across the tasks it tests.

tasks:
  # ---- Level 0: Foundation (can run in parallel) ----
  - id: FE-001
    name: "Add role assignment TypeScript types"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-002
    name: "Extend query key factory with roleAssignment keys"
    agent: pdca-frontend-do-executor
    dependencies: []

  # ---- Level 1: Hooks (depends on types + keys) ----
  - id: FE-003
    name: "Create TanStack Query hooks for role assignments CRUD"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002]

  # ---- Level 2: UI Components (depends on hooks) ----
  # These four tasks can potentially run in parallel but are
  # grouped for sequential execution to avoid merge conflicts
  # in shared files (queryKeys, routes, etc.)

  - id: FE-004
    name: "Create Role Assignments admin page"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  - id: FE-005
    name: "Create AssignmentModal component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  - id: FE-006
    name: "Add route and nav entry for Role Assignments"
    agent: pdca-frontend-do-executor
    dependencies: [FE-004, FE-005]

  - id: FE-007
    name: "Replace UserList Role column with unified assignment tags"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  - id: FE-008
    name: "Replace UserModal role field with GLOBAL assignment management"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  - id: FE-009
    name: "Migrate ProjectMemberManager to unified API"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  # ---- Level 3: Tests (depends on all UI tasks) ----
  # Tests must run sequentially (single test runner, shared mocks)
  - id: FE-010
    name: "Component tests for all new and modified components"
    agent: pdca-frontend-do-executor
    dependencies: [FE-004, FE-005, FE-006, FE-007, FE-008, FE-009]
    kind: test
```

---

## Estimated Effort

| Task | Effort | Rationale |
|------|--------|-----------|
| FE-001 (Types) | 0.5h | Mirror 3 backend schemas to TypeScript interfaces |
| FE-002 (Query Keys) | 0.5h | Add one section to existing factory following pattern |
| FE-003 (Hooks) | 2h | 4 hooks (list, create, update, delete) with cache invalidation; follow existing pattern |
| FE-004 (Admin Page) | 3h | StandardTable with columns, filters, toolbar; follow UserList pattern |
| FE-005 (Modal) | 4h | Complex form with conditional scope entity selector, user/role dropdowns, create vs edit mode |
| FE-006 (Route + Nav) | 1h | Add one route + one menu item in two files |
| FE-007 (UserList Column) | 3h | Replace column renderer, add batch assignment query per user, "View Assignments" navigation |
| FE-008 (UserModal) | 4h | Replace role field with inline GLOBAL assignment management; handle create vs edit flows |
| FE-009 (PMM Migration) | 5h | Replace entire API layer, map ProjectRole to RBAC roles, adapt add/remove/update flows |
| FE-010 (Tests) | 5h | New tests for 2 components, update tests for 3 components, MSW handlers |
| **Total** | **~28h** | Spread across ~4 working days for a single developer |

---

## Implementation Notes for DO Phase

### FE-001: TypeScript Types

Create `frontend/src/api/types/roleAssignment.ts` mirroring backend schemas:

- `ScopeType` enum: `GLOBAL = "global"`, `PROJECT = "project"`, `CHANGE_ORDER = "change_order"`
- `UserRoleAssignmentCreate`: `user_id`, `role_id`, `scope_type`, `scope_id?`, `metadata_?`, `granted_by?`, `expires_at?`
- `UserRoleAssignmentUpdate`: `role_id?`, `metadata_?`, `expires_at?`
- `UserRoleAssignmentRead`: all fields from `UserRoleAssignmentResponse` plus optional `role_name`, `user_name`, `granted_by_name`

### FE-002: Query Keys

Add `roleAssignments` section to `queryKeys` following the `adminRbac` pattern:

```typescript
roleAssignments: {
  all: ["role-assignments"] as const,
  lists: () => ["role-assignments", "list"] as const,
  list: (params?: { userId?: string; scopeType?: string; scopeId?: string; roleId?: string }) =>
    ["role-assignments", "list", params] as const,
  details: () => ["role-assignments", "detail"] as const,
  detail: (id: string) => ["role-assignments", "detail", id] as const,
},
```

### FE-005: AssignmentModal Scope Entity Selector

When `scope_type` is PROJECT: fetch projects list (reuse `useProjects` or query directly) and display in searchable `Select`.
When `scope_type` is CHANGE_ORDER: fetch change orders for context and display in searchable `Select`.
When `scope_type` is GLOBAL: hide scope entity selector entirely.

### FE-007: UserList Batch Assignment Loading

Fetch all role assignments in a single query (no N+1). Group results by `user_id` in the frontend. For each user row, render compact Tags:
- `[Admin (Global)]` for scope_type=GLOBAL
- `[Manager - Project A]` for scope_type=PROJECT (show entity name if available)
- `[Approver - CO-001]` for scope_type=CHANGE_ORDER

### FE-008: UserModal GLOBAL Assignment Flow

**Create mode**: After user creation succeeds, immediately create a GLOBAL role assignment using the selected role. The form captures: full_name, email, password, role (for GLOBAL assignment). On submit: call user create API, then call role assignment create API.

**Edit mode**: Display current GLOBAL assignments. Allow adding a new GLOBAL assignment or removing existing one. If user has exactly one GLOBAL assignment, show it as the role selector. If multiple or none, show a section for managing GLOBAL assignments.

### FE-009: ProjectRole to RBAC Role Mapping

The backend migration script (`20260510b_migrate_existing_roles_to_unified_rbac.py`) created RBAC roles with names matching the ProjectRole values. The frontend should:
1. Fetch RBAC roles via `useRBACRoles()`
2. For display: show the RBAC role name
3. For create/update: send the RBAC role's UUID as `role_id`
4. The mapping: `project_admin` -> RBAC role "Project Admin", `project_manager` -> "Project Manager", etc.

### Critical Files Reference

| Purpose | File Path |
|---------|-----------|
| New types | `frontend/src/api/types/roleAssignment.ts` |
| New hooks | `frontend/src/features/admin/role-assignments/hooks/useRoleAssignments.ts` |
| New page | `frontend/src/pages/admin/RoleAssignments.tsx` |
| New modal | `frontend/src/features/admin/role-assignments/components/AssignmentModal.tsx` |
| Modified query keys | `frontend/src/api/queryKeys.ts` |
| Modified router | `frontend/src/routes/index.tsx` |
| Modified nav | `frontend/src/components/UserProfile.tsx` |
| Modified UserList | `frontend/src/pages/admin/UserList.tsx` |
| Modified UserModal | `frontend/src/features/users/components/UserModal.tsx` |
| Modified PMM | `frontend/src/features/projects/components/ProjectMemberManager.tsx` |
| Modified PMM hooks | `frontend/src/features/projects/hooks/useProjectMembers.ts` |
