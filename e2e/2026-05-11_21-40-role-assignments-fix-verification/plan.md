# E2E Test Plan: Role Assignments Fix Verification

**Date:** 2026-05-11
**Goal:** Verify that Bug #1 (user_name: null) and Bug #2 (missing permissions) are fixed
**Base URL:** http://192.168.1.15:5173

---

## Business Rules (from Research)

### Permissions Required
| Action | Permission | Admin Has? |
|--------|------------|------------|
| View page | `role-assignment-read` | ✅ Yes |
| Create button | `role-assignment-create` | ✅ Yes |
| Edit button | `role-assignment-update` | ✅ Yes |
| Delete button | `role-assignment-delete` | ✅ Yes |

### Scope Types
- **GLOBAL**: System-wide roles (admin, manager, viewer)
- **PROJECT**: Project-specific roles
- **CHANGE_ORDER**: Change order approvers with authority levels

### Expected User Name Population
- Backend queries `User.full_name` via batch query
- `user_name` should NOT be null for seeded users

---

## Prerequisites

### Test User
- **Email:** admin@backcast.org
- **Password:** adminadmin
- **Role:** admin (all 76 permissions including role-assignment-*)

### Database Verification Queries

```sql
-- Check if role_assignment permissions exist
SELECT jsonb_array_elements_text(permissions) 
FROM rbac_roles 
WHERE name = 'admin' 
  AND value @> '{"role-assignment-read","role-assignment-create","role-assignment-update","role-assignment-delete"}';

-- Check user names are populated
SELECT u.user_id, u.full_name, COUNT(ra.id) as assignment_count
FROM users u
JOIN user_role_assignments ra ON u.user_id = ra.user_id
GROUP BY u.user_id, u.full_name
ORDER BY assignment_count DESC
LIMIT 5;

-- Check role assignments exist
SELECT ra.scope_type, r.name as role_name, COUNT(*) as count
FROM user_role_assignments ra
JOIN rbac_roles r ON ra.role_id = r.id
GROUP BY ra.scope_type, r.name
ORDER BY ra.scope_type, r.name;
```

---

## Test Steps

### Step 1: Navigate to Role Assignments (Unauthenticated)
**Action:** Navigate to `http://192.168.1.15:5173/admin/role-assignments`
**Expected:** Redirect to `/login`
**DB Check:** None needed

### Step 2: Login as Admin
**Action:** Fill login form with admin@backcast.org / adminadmin
**Expected:** Successful login, redirected to role assignments
**API Check:**
- `POST /api/v1/auth/login` → 200 OK
- `GET /api/v1/auth/me` → 200 OK, returns permissions

### Step 3: Verify Page Layout and Data
**Action:** Take snapshot of loaded page
**Expected:**
- Table with columns: User Name, Role, Scope Type, Scope Entity, Granted By, Granted At, Actions
- Filters visible: User, Scope, Role
- Pagination controls
**CRITICAL:** User Name column should show actual names, NOT "—"

### Step 4: Verify User Names Are Populated (Bug #1 Fix)
**Action:** Check table data for user_name values
**Expected:**
- At least one row should have a non-null user_name
- Expected names: "System Administrator", "Project Manager", "Viewer User"
**API Check:**
- `GET /api/v1/role-assignments/` → 200 OK
- Response should have `"user_name": "System Administrator"` not `null`
**DB Check:**
```sql
SELECT u.full_name FROM users u WHERE u.user_id IN (
  SELECT DISTINCT user_id FROM user_role_assignments LIMIT 5
);
```

### Step 5: Verify Create Button Visible (Bug #2 Fix)
**Action:** Check for "Add Assignment" button
**Expected:**
- Button with PlusOutlined icon visible
- Uses `<Can permission="role-assignment-create">`
**Check:** Button exists in DOM

### Step 6: Verify Edit Buttons Visible (Bug #2 Fix)
**Action:** Check Actions column for Edit buttons
**Expected:**
- Each row should have an EditOutlined button
- Uses `<Can permission="role-assignment-update">`
**Check:** At least one Edit button exists

### Step 7: Verify Delete Buttons Visible (Bug #2 Fix)
**Action:** Check Actions column for Delete buttons
**Expected:**
- Each row should have a DeleteOutlined button
- Uses `<Can permission="role-assignment-delete">`
**Check:** At least one Delete button exists

### Step 8: Test Filter Functionality
**Action:** Select a user from "Filter by User" dropdown
**Expected:**
- API called with `?userId=<uuid>`
- Table updates to show filtered results
**API Check:**
- `GET /api/v1/role-assignments/?userId=...` → 200 OK

### Step 9: Test Pagination
**Action:** Click "Next Page" button
**Expected:**
- URL updates to `?page=2&per_page=10`
- Table shows second page of data

---

## Cleanup

No cleanup needed - read-only test

---

## Success Criteria

| Bug | Fix Verification |
|-----|------------------|
| **Bug #1: user_name: null** | ✅ At least 50% of rows have non-null user_name |
| **Bug #2: Missing permissions** | ✅ All three button types visible (Create, Edit, Delete) |

---

## Expected Results Summary

- ✅ Page loads successfully
- ✅ User names populated (not null)
- ✅ Create button visible
- ✅ Edit buttons visible
- ✅ Delete buttons visible
- ✅ Filters work
- ✅ Pagination works

**If any step fails:** Capture screenshot, console errors, network response
