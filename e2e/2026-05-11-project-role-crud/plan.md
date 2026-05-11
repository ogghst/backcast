# E2E Test Plan: Project Role CRUD Operations

**Date:** 2026-05-11
**Objective:** Test the full CRUD lifecycle for project-level role assignments via the UI, verifying database state at each step.

## Prerequisites

### Test Users
| Email | System Role | Purpose |
|-------|-------------|---------|
| admin@backcast.org | admin | Full CRUD operations |
| viewer@backcast.org | viewer | RBAC denial testing |

### Target Project
- **Demo Project 1** (`d54fbbe6-f3df-51db-9c3e-9408700442be`)
- Existing members: admin@backcast.org (project_admin), pm@backcast.org (project_manager), viewer@backcast.org (project_viewer)
- No additional projects will be modified

### RBAC Roles (from `rbac_roles` table)
All 7 system roles exist. Project scope roles are mapped via `useProjectRoleMap()` hook.

---

## Test Steps

### T1: Login as Admin
- **Action:** Navigate to `/login`, fill `admin@backcast.org` / `admin`, click Login
- **Expected:** Dashboard loads, user menu shows "System Administrator"
- **DB verify:** N/A (auth state only)

### T2: Navigate to Project Members Page
- **Action:** Navigate to `/projects/d54fbbe6-f3df-51db-9c3e-9408700442be/members`
- **Expected:** ProjectMemberManager component loads, shows existing members table
- **DB verify:** `project_members` rows match displayed members for project

### T3: Add Project Member (CREATE)
- **Action:** Click "Add Member", search for a user (eng.lead@backcast.org), select role, confirm
- **Expected:** User appears in table with selected role
- **DB verify:** New row in `project_members` + new row in `user_role_assignments` with `scope_type='project'`
- **API verify:** POST `/api/v1/role-assignments/` returns 200

### T4: Update Project Role (UPDATE)
- **Action:** Change eng.lead's role dropdown from current to a different project role
- **Expected:** Role tag updates in table immediately
- **DB verify:** `user_role_assignments` row updated with new `role_id`
- **API verify:** PUT `/api/v1/role-assignments/{id}` returns 200

### T5: Remove Project Member (DELETE)
- **Action:** Click "Remove" on eng.lead, confirm the modal
- **Expected:** User disappears from members table
- **DB verify:** Row deleted from `user_role_assignments` (and/or `project_members`)
- **API verify:** DELETE `/api/v1/role-assignments/{id}` returns 204

### T6: RBAC Enforcement — Viewer Cannot Manage Members
- **Action:** Logout, login as `viewer@backcast.org` / `viewer`, navigate to same project members page
- **Expected:** Member management UI is read-only or access denied (no Add/Remove/Edit buttons)
- **DB verify:** No state changes possible

### T7: Admin Role Assignments Page (Global Roles)
- **Action:** Login as admin, navigate to `/admin/role-assignments`
- **Expected:** Table shows all global role assignments, filter controls work
- **DB verify:** Matches `user_role_assignments` where `scope_type='global'`

---

## Verification Queries

```sql
-- Count members for target project
SELECT COUNT(*) FROM project_members WHERE project_id = 'd54fbbe6-f3df-51db-9c3e-9408700442be';

-- Check specific user assignment
SELECT ura.*, rr.name as role_name
FROM user_role_assignments ura
JOIN rbac_roles rr ON ura.role_id = rr.id
WHERE ura.scope_type = 'project' AND ura.scope_id = 'd54fbbe6-f3df-51db-9c3e-9408700442be';

-- Global assignments
SELECT ura.*, u.email, rr.name as role_name
FROM user_role_assignments ura
JOIN rbac_roles rr ON ura.role_id = rr.id
JOIN users u ON ura.user_id = u.user_id
WHERE ura.scope_type = 'global';
```

## Cleanup Plan
- Test user eng.lead will be added and removed within the test — no residual data expected
- If test fails mid-way, manually clean: `DELETE FROM user_role_assignments WHERE scope_id = 'd54fbbe6-f3df-51db-9c3e-9408700442be' AND user_id = 'dce2e861-bdb7-5887-beaf-6a22837d266d'`
