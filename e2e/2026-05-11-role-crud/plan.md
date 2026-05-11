# E2E Test Plan: System Role CRUD Operations

**Date:** 2026-05-11
**Objective:** Verify full CRUD lifecycle for system roles via the RBAC admin UI

## Prerequisites

- Frontend: http://localhost:5173
- Backend: http://localhost:8020
- Test user: admin@backcast.org / adminadmin (admin role)
- Existing roles: admin, manager, viewer, ai-viewer, ai-manager, ai-admin, change_order_approver (all system roles)
- RBAC admin page: /admin/rbac

## Database Schema (verified)

```
rbac_roles: id (UUID PK), name (VARCHAR UNIQUE), description (TEXT), is_system (BOOL), created_at, updated_at
rbac_role_permissions: id (UUID PK), role_id (UUID FK CASCADE), permission (VARCHAR) — unique(role_id, permission)
```

## Test Steps

### T1: Login as Admin
- Action: Navigate to /login, fill credentials, submit
- Expected UI: Redirected to dashboard, admin access
- Verify: Auth token set

### T2: Navigate to RBAC Admin Page
- Action: Navigate to /admin/rbac
- Expected UI: RBAC configuration page with list of roles
- Verify DB: `SELECT count(*) FROM rbac_roles;` should show 7 roles

### T3: Create a Custom Role
- Action: Click create/add role button, fill name "Test Role" + description, assign permissions ["user-read", "project-read"], save
- Expected UI: New role appears in the list
- Verify DB: `SELECT name, description, is_system FROM rbac_roles WHERE name = 'Test Role';`
- Verify DB: `SELECT permission FROM rbac_role_permissions WHERE role_id = (SELECT id FROM rbac_roles WHERE name = 'Test Role');`

### T4: Read/View Custom Role Details
- Action: Click on "Test Role" to view details
- Expected UI: Role details with permissions listed
- Verify: Permissions shown match DB state

### T5: Update Custom Role
- Action: Edit "Test Role" → change name to "Updated Test Role", add "wbe-read" permission, remove "user-read"
- Expected UI: Updated name and permissions reflected
- Verify DB: `SELECT name FROM rbac_roles WHERE name = 'Updated Test Role';`
- Verify DB: `SELECT permission FROM rbac_role_permissions WHERE role_id = (SELECT id FROM rbac_roles WHERE name = 'Updated Test Role') ORDER BY permission;`
  Expected: project-read, wbe-read

### T6: Verify System Role Cannot Be Deleted
- Action: Attempt to delete the "admin" system role
- Expected UI: Delete action blocked or error shown (system roles cannot be deleted)
- Verify DB: `SELECT count(*) FROM rbac_roles WHERE name = 'admin';` → still 1

### T7: Delete Custom Role
- Action: Delete "Updated Test Role"
- Expected UI: Role removed from list, confirmation dialog
- Verify DB: `SELECT count(*) FROM rbac_roles WHERE name = 'Updated Test Role';` → 0

### T8: Verify Permission Enforcement (Viewer)
- Action: Logout, login as viewer@backcast.org, navigate to /admin/rbac
- Expected UI: Either access denied (403/redirect) or read-only (no create/edit/delete buttons)
- Verify: No role modification possible

## Verification Queries

```sql
-- Count all roles
SELECT count(*) FROM rbac_roles;

-- Get specific role with permissions
SELECT r.name, r.is_system, array_agg(rp.permission) as permissions
FROM rbac_roles r
LEFT JOIN rbac_role_permissions rp ON r.id = rp.role_id
GROUP BY r.id, r.name, r.is_system;

-- Check for custom role
SELECT * FROM rbac_roles WHERE is_system = false;
```

## Cleanup
- Delete any custom test roles created during testing
- Verify only system roles remain at end
