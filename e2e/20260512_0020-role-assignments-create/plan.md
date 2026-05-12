# Role Assignment Create Operations - Test Plan

## Objective

Test the role assignment modal create operations for all three scopes:
- **GLOBAL**: System-wide role assignments
- **PROJECT**: Project-scoped role assignments
- **CHANGE_ORDER**: Change order-scoped role assignments

**Route**: `/admin/role-assignments`

## Prerequisites

### Users (from seed/users.json)
| Email | Role | Purpose |
|-------|------|---------|
| admin@backcast.org | admin | Create role assignments (has admin permissions) |
| viewer@backcast.org | viewer | Test target for assignments |
| pm@backcast.org | manager | Test project-scoped assignments |

### Permissions Required
- `role-assignment-create` - Required to create role assignments
- `role-assignment-read` - Required to view assignments list
- Admin role should have both permissions

### Test Data Needed
- At least 2 users for assignment targets
- At least 1 project for project scope
- At least 1 change order for change order scope
- Available roles from rbac_roles table

## Test Steps

### Step 1: Environment Verification
**Action**: Check frontend and backend are running
**Expected**: Both services respond

### Step 2: Baseline Database State
**Action**: Capture current role assignments
**Query**:
```sql
SELECT id, user_id, role_id, scope_type, scope_id
FROM user_role_assignments
ORDER BY created_at DESC;
```

### Step 3: Login as Admin
**Action**: Navigate to login, authenticate as admin@backcast.org
**Expected**: Dashboard loaded, authenticated state

### Step 4: Navigate to Role Assignments Page
**Action**: Navigate to `/admin/role-assignments`
**Expected**: Role assignments list visible, "New Assignment" button present

### Step 5: Open Create Modal
**Action**: Click "New Assignment" button
**Expected**: Modal opens with form fields

### Step 6: Test GLOBAL Scope Assignment
**Action**:
1. Select scope_type = "global"
2. Select a user (e.g., viewer@backcast.org)
3. Select a role (e.g., manager)
4. Submit form

**Expected UI**: Success notification, assignment appears in list
**Expected DB**: New record with scope_type='global', scope_id=NULL

### Step 7: Test PROJECT Scope Assignment
**Action**:
1. Click "New Assignment"
2. Select scope_type = "project"
3. Select a user (e.g., pm@backcast.org)
4. Select a role (e.g., viewer)
5. Select a project from dropdown
6. Submit form

**Expected UI**: Success notification, assignment appears in list with project name
**Expected DB**: New record with scope_type='project', scope_id=<project_uuid>

### Step 8: Test CHANGE_ORDER Scope Assignment
**Action**:
1. Click "New Assignment"
2. Select scope_type = "change_order"
3. Select a user
4. Select a role
5. Select a project (should appear first)
6. Select a change order from filtered dropdown
7. Submit form

**Expected UI**: Success notification, assignment appears in list with CO name
**Expected DB**: New record with scope_type='change_order', scope_id=<co_uuid>

### Step 9: Verify Unique Constraint Enforcement
**Action**: Attempt to create duplicate assignment (same user + scope_type + scope_id)
**Expected**: Error notification, no duplicate created

### Step 10: Verify Form Validation
**Action**: Try to submit with missing required fields
**Expected**: Field validation errors, form doesn't submit

## Verification Queries

### After each create operation:
```sql
-- Check new assignment was created
SELECT
    ura.id,
    u.email,
    r.name as role_name,
    ura.scope_type,
    ura.scope_id,
    ura.granted_by,
    ura.granted_at
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
WHERE ura.user_id = '<selected_user_id>'
ORDER BY ura.created_at DESC
LIMIT 1;

-- Check for duplicates (should be 0 or 1)
SELECT COUNT(*) as duplicate_count
FROM user_role_assignments
WHERE user_id = '<user_id>'
  AND scope_type = '<scope_type>'
  AND scope_id <operator> <scope_id>;  -- = for non-global, IS NULL for global
```

## Cleanup Plan

Delete test assignments created during testing:
```sql
-- Delete test assignments (save IDs during test)
DELETE FROM user_role_assignments WHERE id = '<test_assignment_id>';
```

## Success Criteria

- [ ] All three scope types (global, project, change_order) can be created
- [ ] Database correctly records scope_type and scope_id for each
- [ ] UI correctly displays created assignments with proper scope context
- [ ] Form validation prevents invalid submissions
- [ ] Unique constraint prevents duplicate assignments
- [ ] No console errors during create operations
- [ ] No backend errors during create operations
