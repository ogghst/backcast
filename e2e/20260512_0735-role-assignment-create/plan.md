# Role Assignment Modal Create Operations - E2E Test Plan

**Iteration:** `20260512_0735-role-assignment-create`
**Route:** `/admin/role-assignments`
**Date:** 2026-05-12

---

## Objective

Test the role assignment modal create operations for all three scope types:
1. **GLOBAL** scope - System-wide role assignments
2. **PROJECT** scope - Project-scoped role assignments
3. **CHANGE_ORDER** scope - Change order scoped role assignments

---

## Prerequisites

### Users (from seed data)
- **Admin:** `admin@backcast.org` / `adminadmin` - Has `role-assignment-create` permission
- **Viewer:** `viewer@backcast.org` - For GLOBAL scope testing (no existing global role)
- **PM:** `pm@backcast.org` - Has `manager` global role
- **Director:** `director@backcast.org` - Has `viewer` global role

### Roles (from rbac.json)
- `admin` - Full system access
- `manager` - Project management
- `viewer` - Read-only access
- `project_admin` - Full project management
- `project_manager` - Project CRUD with cost elements
- `project_editor` - Create/update cost elements
- `project_viewer` - Read-only project access
- `change_order_approver` - Change order approval

### Required Data
- At least one active project for PROJECT scope testing
- At least one change order for CHANGE_ORDER scope testing

---

## Test Steps

### Step 1: Environment Verification
**Action:** Check frontend and backend services are running
**Expected:** Both services respond
**Command:** `curl -s http://192.168.1.15:8020/docs | head -5`

---

### Step 2: Database Baseline
**Action:** Capture current role assignments
**Query:**
```sql
SELECT id, user_id, role_id, scope_type, scope_id
FROM user_role_assignments
ORDER BY created_at DESC;
```
**Expected:** See existing baseline assignments

---

### Step 3: Login as Admin
**Action:** Navigate to login and authenticate
**Expected:** Dashboard loaded, authenticated state
**Snapshot:** `snapshots/01-admin-login.png`

---

### Step 4: Navigate to Role Assignments
**Action:** Navigate to `/admin/role-assignments`
**Expected:** Role assignments list visible with "Add Assignment" button
**Snapshot:** `snapshots/02-assignments-page.md`

---

### Step 5: Open Create Modal
**Action:** Click "Add Assignment" button
**Expected:** Modal opens with form fields (User, Role, Scope Type)
**Snapshot:** `snapshots/03-create-modal.md`

---

### Step 6: GLOBAL Scope - Form Validation
**Action:** Click "Create" without filling required fields
**Expected:** Field validation errors, form doesn't submit
**Snapshot:** `snapshots/04-validation-errors.md`

---

### Step 7: GLOBAL Scope - Select User
**Action:** Select a user (e.g., viewer@backcast.org if they don't have global role)
**Expected:** User selected successfully

---

### Step 8: GLOBAL Scope - Select Role
**Action:** Select a role (e.g., `manager`)
**Expected:** Role selected successfully

---

### Step 9: GLOBAL Scope - Submit
**Action:** Click "Create" button
**Expected:**
- Success notification
- Modal closes
- New assignment appears in list
**DB Verification:**
```sql
SELECT ura.id, u.email, r.name, ura.scope_type, ura.scope_id
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
WHERE ura.scope_type = 'global'
ORDER BY ura.created_at DESC
LIMIT 5;
```
**Snapshot:** `snapshots/05-global-success.md`

---

### Step 10: PROJECT Scope - Open Modal Again
**Action:** Click "Add Assignment" button
**Expected:** Modal opens with empty form

---

### Step 11: PROJECT Scope - Select Scope Type
**Action:** Change scope type to "Project"
**Expected:** Project selection dropdown appears
**Snapshot:** `snapshots/06-project-scope-selected.md`

---

### Step 12: PROJECT Scope - Select User and Role
**Action:** Select user and role (e.g., `project_viewer`)
**Expected:** Fields populated

---

### Step 13: PROJECT Scope - Select Project
**Action:** Select a project from dropdown
**Expected:** Project selected, form ready to submit

---

### Step 14: PROJECT Scope - Submit
**Action:** Click "Create" button
**Expected:**
- Success notification
- Modal closes
- New project-scoped assignment appears
**DB Verification:**
```sql
SELECT ura.id, u.email, r.name, ura.scope_type, p.name as project_name
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
LEFT JOIN projects p ON ura.scope_id = p.project_id
WHERE ura.scope_type = 'project'
ORDER BY ura.created_at DESC
LIMIT 5;
```
**Snapshot:** `snapshots/07-project-success.md`

---

### Step 15: CHANGE_ORDER Scope - Open Modal
**Action:** Click "Add Assignment" button
**Expected:** Modal opens with empty form

---

### Step 16: CHANGE_ORDER Scope - Select Scope Type
**Action:** Change scope type to "Change Order"
**Expected:** Project selection dropdown appears first
**Snapshot:** `snapshots/08-co-scope-selected.md`

---

### Step 17: CHANGE_ORDER Scope - Select User and Role
**Action:** Select user and `change_order_approver` role
**Expected:** Fields populated

---

### Step 18: CHANGE_ORDER Scope - Cascade Selection
**Action:**
1. Select a project
2. Verify change order dropdown appears
3. Select a change order
**Expected:** Cascade works correctly, CO selected

---

### Step 19: CHANGE_ORDER Scope - Submit
**Action:** Click "Create" button
**Expected:**
- Success notification
- Modal closes
- New CO-scoped assignment appears
**DB Verification:**
```sql
SELECT ura.id, u.email, r.name, ura.scope_type, co.name as co_name
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
LEFT JOIN change_orders co ON ura.scope_id = co.change_order_id
WHERE ura.scope_type = 'change_order'
ORDER BY ura.created_at DESC
LIMIT 5;
```
**Snapshot:** `snapshots/09-co-success.md`

---

### Step 20: Unique Constraint Test
**Action:** Attempt to create duplicate assignment (same user + scope)
**Expected:**
- 409 Conflict error
- Error notification: "User already has a role assignment for this scope"
- No duplicate in database
**Snapshot:** `snapshots/10-duplicate-error.md`

---

## Verification Queries

### Check All Assignments After Test
```sql
SELECT
    ura.id,
    u.email,
    r.name as role_name,
    ura.scope_type,
    CASE ura.scope_type
        WHEN 'global' THEN 'N/A'
        WHEN 'project' THEN p.name
        WHEN 'change_order' THEN co.name
    END as scope_entity,
    ura.granted_at,
    ura.expires_at
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
LEFT JOIN projects p ON ura.scope_type = 'project' AND ura.scope_id = p.project_id
LEFT JOIN change_orders co ON ura.scope_type = 'change_order' AND ura.scope_id = co.change_order_id
ORDER BY ura.created_at DESC;
```

### Check API Response for Projects
After selecting PROJECT scope, verify the projects dropdown loads correctly:
```bash
curl -s "http://192.168.1.15:8020/api/v1/projects?per_page=200&branch=main&mode=merged" \
  -H "Authorization: Bearer <token>" | jq '.items | length'
```

---

## Cleanup

Delete test assignments created during testing:
```sql
-- Delete test assignments (use specific IDs from test)
DELETE FROM user_role_assignments
WHERE scope_type = 'global' AND user_id = '<test_user_id>'
  AND created_at >= '2026-05-12 07:35:00';
```

---

## Success Criteria

- ✅ All three scope types can be created successfully
- ✅ Form validation works correctly
- ✅ Cascade selection works for CHANGE_ORDER scope
- ✅ Database state matches UI after each creation
- ✅ Unique constraint is enforced
- ✅ No console errors during any operation
- ✅ Backend logs show no errors for create operations

---

## Notes

- The previous E2E test found a bug where `get_accessible_projects()` returned `Project.id` instead of `project_id`, causing empty projects dropdown. This should be fixed.
- Change order selection requires project selection first (cascade pattern)
- All state changes must be verified in the database
