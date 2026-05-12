# E2E Test Plan: Role Assignment CRUD Operations

**Date**: 2026-05-11
**Iteration**: 2026-05-11_22-02-role-assignments-crud
**Route**: `/admin/role-assignments`

## Objective

Test the full CRUD lifecycle for role assignments across all three scopes (global, project, change_order) via the role assignment modal at `/admin/role-assignments`.

## Prerequisites

### Test Users
| Email | Role | Purpose |
|-------|------|---------|
| `admin@backcast.org` | admin | Primary test user (has all permissions) |
| `pm@backcast.org` | manager | Test subject for assignments |
| `viewer@backcast.org` | viewer | Test subject for assignments |

### Test Data
- **Roles**: admin, manager, viewer, ai-viewer, change_order_approver (11 total available)
- **Projects**: `Test Project E2E` (id: `a7831ad3-66e1-4eaa-97ef-dbad086835c8`)
- **Change Orders**: `Layout Adjustment & Demolition` (id: `216461a2-4d97-4b7b-8221-e8c48d1877af`)

### Current Database State
- 8 global role assignments exist
- 0 project scope assignments exist
- 0 change_order scope assignments exist

## Test Steps

### Step 1: Setup & Login
1. Navigate to `http://localhost:5173/login`
2. Login as `admin@backcast.org` / `adminadmin`
3. Navigate to `/admin/role-assignments`

**Verify**:
- UI: Role assignments page loads
- DB: Query baseline assignments
```sql
SELECT COUNT(*) FROM user_role_assignments WHERE scope_type = 'global';
-- Expected: 8
```

### Step 2: Read - List All Assignments
1. Observe the role assignments list

**Verify**:
- UI: Global scope assignments are displayed
- DB: Count matches UI
```sql
SELECT COUNT(*) FROM user_role_assignments;
-- Expected: 8
```

### Step 3: Create - Global Scope Assignment
1. Click "Add Role Assignment" button (or equivalent)
2. In the modal, select:
   - User: `viewer@backcast.org` (Viewer User)
   - Role: `manager`
   - Scope: Global
3. Click "Save" or "Create"

**Verify**:
- UI: Success notification, new assignment appears in list
- DB: New row exists
```sql
SELECT u.email, r.name, ura.scope_type
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
WHERE u.email = 'viewer@backcast.org' AND ura.scope_type = 'global';
-- Expected: 1 row with role='manager'
```

### Step 4: Create - Project Scope Assignment
1. Click "Add Role Assignment"
2. In the modal, select:
   - User: `pm@backcast.org` (Project Manager)
   - Role: `viewer`
   - Scope: Project
   - Project: `Test Project E2E`
3. Click "Save"

**Verify**:
- UI: New project-scoped assignment appears
- DB: New row with correct scope_id
```sql
SELECT u.email, r.name, ura.scope_type, p.name as project_name
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
LEFT JOIN projects p ON ura.scope_id = p.id
WHERE u.email = 'pm@backcast.org' AND ura.scope_type = 'project';
-- Expected: 1 row, project_name='Test Project E2E', role='viewer'
```

### Step 5: Create - Change Order Scope Assignment
1. Click "Add Role Assignment"
2. In the modal, select:
   - User: `viewer@backcast.org`
   - Role: `change_order_approver`
   - Scope: Change Order
   - Change Order: `Layout Adjustment & Demolition`
   - Authority Level: `HIGH` (if metadata field available)
3. Click "Save"

**Verify**:
- UI: New CO-scoped assignment appears
- DB: New row with metadata containing authority_level
```sql
SELECT u.email, r.name, ura.scope_type, ura.metadata, co.title
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
LEFT JOIN change_orders co ON ura.scope_id = co.id
WHERE u.email = 'viewer@backcast.org' AND ura.scope_type = 'change_order';
-- Expected: 1 row, metadata->>'authority_level' = 'HIGH'
```

### Step 6: Update - Modify Role Assignment
1. Find the project-scoped assignment created in Step 4
2. Click "Edit" button
3. Change role from `viewer` to `project_manager`
4. Click "Update"

**Verify**:
- UI: Assignment shows updated role
- DB: Role updated, updated_at changed
```sql
SELECT u.email, r.name, ura.updated_at > ura.created_at as was_updated
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
WHERE u.email = 'pm@backcast.org' AND ura.scope_type = 'project';
-- Expected: role='project_manager', was_updated=true
```

### Step 7: Validation - Duplicate Assignment Prevention
1. Click "Add Role Assignment"
2. Select:
   - User: `pm@backcast.org`
   - Role: `viewer`
   - Scope: Project
   - Project: `Test Project E2E` (same as Step 4)
3. Click "Save"

**Verify**:
- UI: Error message about duplicate/unique constraint
- DB: No new row created
```sql
SELECT COUNT(*) FROM user_role_assignments
WHERE user_id = (SELECT user_id FROM users WHERE email = 'pm@backcast.org')
  AND scope_type = 'project'
  AND scope_id = 'a7831ad3-66e1-4eaa-97ef-dbad086835c8';
-- Expected: 1 (unchanged from Step 6)
```

### Step 8: Delete - Remove Assignment
1. Find the global assignment created in Step 3
2. Click "Delete" button
3. Confirm deletion

**Verify**:
- UI: Assignment removed from list
- DB: Row deleted
```sql
SELECT COUNT(*) FROM user_role_assignments
WHERE user_id = (SELECT user_id FROM users WHERE email = 'viewer@backcast.org')
  AND scope_type = 'global'
  AND role_id = (SELECT id FROM rbac_roles WHERE name = 'manager');
-- Expected: 0
```

### Step 9: Filtering (Optional)
1. Use scope filter to show only "project" assignments
2. Use user filter to show only assignments for `viewer@backcast.org`

**Verify**:
- UI: Filtered results match selected filters
- DB: Results match query
```sql
SELECT u.email, r.name, ura.scope_type
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
WHERE ura.scope_type = 'project';
-- Should match UI filter results
```

## Cleanup Plan

Delete test assignments created during testing:
```sql
-- Delete global scope assignment (Step 3)
DELETE FROM user_role_assignments
WHERE user_id = (SELECT user_id FROM users WHERE email = 'viewer@backcast.org')
  AND scope_type = 'global'
  AND role_id = (SELECT id FROM rbac_roles WHERE name = 'manager');

-- Delete project scope assignment (Step 4, updated in Step 6)
DELETE FROM user_role_assignments
WHERE user_id = (SELECT user_id FROM users WHERE email = 'pm@backcast.org')
  AND scope_type = 'project';

-- Delete change order scope assignment (Step 5)
DELETE FROM user_role_assignments
WHERE user_id = (SELECT user_id FROM users WHERE email = 'viewer@backcast.org')
  AND scope_type = 'change_order';
```

## Expected Outcomes Summary

| Step | Action | Expected UI | Expected DB |
|------|--------|-------------|-------------|
| 1 | Login & navigate | Dashboard loads | 8 global assignments |
| 2 | List view | All global assignments shown | COUNT = 8 |
| 3 | Create global | Success, new row appears | viewer@backcast.org = manager (global) |
| 4 | Create project | Success, project scope shown | pm@backcast.org = viewer (Test Project E2E) |
| 5 | Create CO | Success, CO scope shown | viewer@backcast.org = change_order_approver + metadata |
| 6 | Update | Role changed to project_manager | pm@backcast.org = project_manager, updated_at > created_at |
| 7 | Duplicate | Error message | No new row (constraint violation) |
| 8 | Delete | Assignment removed | 0 rows for deleted assignment |
| 9 | Filter | Filtered results | DB query matches UI |

## Notes

- Database schema: Table uses `metadata` column (not `metadata_` as in some docs)
- Unique constraint: `(user_id, scope_type, scope_id)` prevents duplicates
- Foreign key cascade: Deleting a role cascades to assignments
- All timestamps: `created_at`, `updated_at`, `granted_at` use TIMESTAMPTZ
