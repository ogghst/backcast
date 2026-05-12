# E2E Test Plan: Role Assignment CRUD Operations

## Objective
Test CRUD operations for role assignments across all three scopes (Global, Project, Change Order) at `/admin/role-assignments` UI.

## Prerequisites
- **Test Users** (from seed data):
  - `admin@backcast.org` / `adminadmin` - System Administrator (full CRUD access)
  - `viewer@backcast.org` - Viewer (read-only)
  - `pm@backcast.org` - Project Manager (read-only for role assignments)

- **Test Data Required**:
  - At least one project in the database
  - At least one change order in the database
  - Existing roles: admin, manager, controller, viewer

- **Database Tables**:
  - `user_role_assignments` - Main table for assignments
  - `users` - User records
  - `rbac_roles` - Available roles
  - `projects` - For project scope
  - `change_orders` - For change order scope

## Test Steps

### Step 1: Setup and Baseline
**Action**: Login as admin, navigate to role assignments page

**UI Expected**: 
- Page loads at `/admin/role-assignments`
- Table shows existing role assignments
- Filters are visible (user, scope type, role)

**DB Verification**:
```sql
-- Count existing assignments
SELECT COUNT(*) as total_assignments, scope_type
FROM user_role_assignments
GROUP BY scope_type
ORDER BY scope_type;

-- Get baseline assignments
SELECT id, user_id, role_id, scope_type, scope_id, granted_by, granted_at
FROM user_role_assignments
ORDER BY created_at;
```

### Step 2: CREATE - Global Scope Role Assignment
**Action**: 
- Click "New Assignment" button
- Select user: `viewer@backcast.org`
- Select role: `manager`
- Select scope type: `global`
- Click Save

**UI Expected**:
- Modal closes
- Success notification appears
- New row appears in table with:
  - User: "Viewer User"
  - Role: "manager" (green tag)
  - Scope Type: "global" (blue badge)

**DB Verification**:
```sql
-- Verify new assignment created
SELECT ura.id, u.email, u.full_name, r.name as role_name, ura.scope_type, ura.scope_id, ura.granted_by, ura.granted_at
FROM user_role_assignments ura
JOIN users u ON u.user_id = ura.user_id
JOIN rbac_roles r ON r.id = ura.role_id
WHERE u.email = 'viewer@backcast.org'
  AND ura.scope_type = 'global'
  AND r.name = 'manager'
ORDER BY ura.created_at DESC
LIMIT 1;
```

### Step 3: CREATE - Project Scope Role Assignment
**Action**:
- Click "New Assignment"
- Select user: `pm@backcast.org`
- Select role: `controller`
- Select scope type: `project`
- Select project: (first available project)
- Click Save

**UI Expected**:
- Modal closes
- Success notification appears
- New row shows project name in Scope Entity column

**DB Verification**:
```sql
-- Verify project-scoped assignment
SELECT ura.id, u.email, r.name as role_name, ura.scope_type, ura.scope_id, p.name as project_name
FROM user_role_assignments ura
JOIN users u ON u.user_id = ura.user_id
JOIN rbac_roles r ON r.id = ura.role_id
LEFT JOIN projects p ON p.project_id = ura.scope_id
WHERE u.email = 'pm@backcast.org'
  AND ura.scope_type = 'project'
  AND r.name = 'controller';
```

### Step 4: CREATE - Change Order Scope Role Assignment
**Action**:
- Click "New Assignment"
- Select user: `viewer@backcast.org`
- Select role: `manager`
- Select scope type: `change_order`
- Select project: (first available project)
- Select change order: (first available CO for that project)
- Click Save

**UI Expected**:
- Modal closes with cascading selectors working correctly
- Success notification appears
- Scope Entity shows CO identifier/name

**DB Verification**:
```sql
-- Verify change order scoped assignment
SELECT ura.id, u.email, r.name as role_name, ura.scope_type, ura.scope_id, 
       co.change_order_id, co.title as co_title
FROM user_role_assignments ura
JOIN users u ON u.user_id = ura.user_id
JOIN rbac_roles r ON r.id = ura.role_id
LEFT JOIN change_orders co ON co.change_order_id = ura.scope_id
WHERE u.email = 'viewer@backcast.org'
  AND ura.scope_type = 'change_order';
```

### Step 5: READ - Filter Functionality
**Action**:
- Set Scope Type filter to `global`
- Observe table updates
- Clear filter
- Set User filter to `viewer@backcast.org`
- Observe table updates

**UI Expected**:
- Table filters show only matching records
- Filter counts match expected numbers

**DB Verification**:
```sql
-- Verify filter counts
SELECT scope_type, COUNT(*) as count
FROM user_role_assignments
WHERE user_id = (SELECT user_id FROM users WHERE email = 'viewer@backcast.org')
GROUP BY scope_type;
```

### Step 6: UPDATE - Modify Role Assignment
**Action**:
- Find the assignment created in Step 3 (pm@backcast.org, project scope, controller role)
- Click Edit button
- Change role from `controller` to `manager`
- Click Save

**UI Expected**:
- Modal closes
- Row updates to show new role with updated tag styling

**DB Verification**:
```sql
-- Verify role was updated
SELECT ura.id, u.email, r.name as role_name, ura.scope_type, ura.updated_at
FROM user_role_assignments ura
JOIN users u ON u.user_id = ura.user_id
JOIN rbac_roles r ON r.id = ura.role_id
WHERE u.email = 'pm@backcast.org'
  AND ura.scope_type = 'project'
  AND r.name = 'manager';
```

### Step 7: UPDATE - Modify Scope (Global to Project)
**Action**:
- Find global assignment for viewer@backcast.org (created in Step 2)
- Click Edit
- Change scope type to `project`
- Select a project
- Click Save

**UI Expected**:
- Modal closes
- Scope Type updates from "global" to "project"
- Scope Entity shows project name

**DB Verification**:
```sql
-- Verify scope was modified
SELECT ura.id, u.email, r.name as role_name, ura.scope_type, ura.scope_id, p.name as project_name
FROM user_role_assignments ura
JOIN users u ON u.user_id = ura.user_id
JOIN rbac_roles r ON r.id = ura.role_id
LEFT JOIN projects p ON p.project_id = ura.scope_id
WHERE u.email = 'viewer@backcast.org'
  AND ura.scope_type = 'project'
  AND r.name = 'manager'
ORDER BY ura.updated_at DESC
LIMIT 1;
```

### Step 8: DELETE - Remove Role Assignment
**Action**:
- Find an assignment to delete (e.g., the CO-scoped assignment from Step 4)
- Click Delete button
- Confirm deletion in confirmation dialog
- Observe row removal

**UI Expected**:
- Confirmation dialog appears
- After confirming, row is removed from table
- Success notification appears

**DB Verification**:
```sql
-- Verify assignment was deleted
SELECT COUNT(*) as exists
FROM user_role_assignments ura
JOIN users u ON u.user_id = ura.user_id
WHERE u.email = 'viewer@backcast.org'
  AND ura.scope_type = 'change_order';
-- Expected: 0
```

### Step 9: Permission Check - Non-Admin User
**Action**:
- Logout as admin
- Login as `pm@backcast.org` (manager - read-only)
- Navigate to `/admin/role-assignments`

**UI Expected**:
- Page may load with data visible
- "New Assignment" button is NOT visible or disabled
- Edit/Delete buttons are NOT visible or disabled

**DB Verification**: No changes should be possible

### Step 10: Validation - Prevent Duplicate Assignment
**Action**:
- Login as admin again
- Try to create duplicate assignment for same user + role + scope
- Expected: Validation error or warning

**UI Expected**:
- Either duplicate prevention in UI (user already has this role in this scope)
- Or backend error message about unique constraint

**DB Verification**:
```sql
-- Verify no duplicate was created
SELECT user_id, role_id, scope_type, scope_id, COUNT(*) as count
FROM user_role_assignments
GROUP BY user_id, role_id, scope_type, scope_id
HAVING COUNT(*) > 1;
-- Expected: 0 rows
```

## Cleanup Plan
- Delete test role assignments created during testing
- Restore original state for test users

### Cleanup Queries
```sql
-- Remove test assignments (example - adjust IDs based on actual created records)
-- DELETE FROM user_role_assignments WHERE user_id IN (
--   SELECT user_id FROM users WHERE email IN ('viewer@backcast.org', 'pm@backcast.org')
-- ) AND scope_type != 'global';  -- Preserve original global roles
```

## Success Criteria
- All CRUD operations complete successfully for all three scopes
- Database state verified after each state-changing operation
- UI reflects database state accurately
- Permissions properly enforced (non-admin cannot modify)
- Validation prevents duplicate assignments
- No console errors or backend errors during operations
