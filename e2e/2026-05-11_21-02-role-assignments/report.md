# E2E Test Report: Role Assignment Page

**Date:** 2026-05-11
**Test Target:** http://192.168.1.15:5173/admin/role-assignments
**Branch:** `unified-rbac`
**Test Duration:** ~5 minutes

---

## Executive Summary

**Result:** ❌ **FAILED** - Multiple critical bugs discovered

The Role Assignment page loads and displays data but has significant issues that prevent core functionality:

1. **Critical Bug:** User names not populated in API response (`user_name: null`)
2. **Critical Bug:** Missing `role-assignment-*` permissions in rbac.json
3. **UI Issue:** No Create button visible (permission-related)
4. **UI Issue:** No Edit/Delete actions in table (permission-related)

**Pass/Fail Counts:** 5 Pass / 4 Fail / 1 Skipped

---

## Test Results by Step

### Step 1: Navigate to Role Assignments Page
**Status:** ✅ PASS

**Expected:** Redirect to login when unauthenticated
**Actual:** Redirected to `/login` as expected

**Evidence:**
- URL changed from `/admin/role-assignments` to `/login`
- Login form displayed correctly
- Console errors: Non-critical (favicon 404)

---

### Step 2: Login as Admin
**Status:** ✅ PASS

**Expected:** Successful authentication and navigation
**Actual:** Login successful, redirected to role assignments page

**API Calls:**
- POST `/api/v1/auth/login` → 200 OK (JWT token received)
- GET `/api/v1/auth/me` → 200 OK

**Evidence:**
- User menu visible (user icon in top right)
- Page title: "Role Assignments"
- No authentication errors

---

### Step 3: Verify Page Layout and Data
**Status:** ⚠️ PARTIAL (Data Issue)

**Expected:** Table with all columns and role assignment data
**Actual:** Table displays but User Name column shows "—" for all rows

**API Call:**
- GET `/api/v1/role-assignments/` → 200 OK

**Bug Found:** `user_name` field is `null` for all role assignments in API response

**Evidence:**
```json
{
  "user_id": "e03556f3-4385-5d68-a685-af307fc8af5c",
  "user_name": null,  // ❌ Should be "System Administrator"
  "role_name": "admin"  // ✅ Correctly populated
}
```

**Table Columns Present:** User Name, Role, Scope Type, Scope Entity, Granted By, Granted At, Actions ✅

**Filters Present:** Filter by User, Filter by Scope, Filter by Role ✅

**Pagination:** 1-10 of 20 items ✅

---

### Step 4: Verify Filter Functionality
**Status:** ✅ PASS

**Expected:** Filter dropdown updates table via API call
**Actual:** Filter triggers API call with query parameters

**API Call:**
- GET `/api/v1/role-assignments/?userId=e03556f3-4385-5d68-a685-af307fc8af5c` → 200 OK

**Evidence:** Selected "System Administrator" from dropdown, API called with userId parameter

---

### Step 5: Verify Create Role Assignment Button
**Status:** ❌ FAIL (Permission Bug)

**Expected:** "Create Role Assignment" button visible for admin users
**Actual:** No Create button found on the page

**Root Cause:** The `admin` role in `rbac.json` lacks the `role-assignment-create` permission

**Impact:** Admin users cannot create new role assignments via the UI

---

### Step 6: Verify Edit Functionality
**Status:** ❌ FAIL (Permission Bug)

**Expected:** Edit buttons in Actions column for each row
**Actual:** Actions column cells are empty for all rows

**Root Cause:** The `admin` role lacks `role-assignment-update` permission

**Impact:** Admin users cannot edit existing role assignments via the UI

---

### Step 7: Verify Delete Functionality
**Status:** ❌ FAIL (Permission Bug)

**Expected:** Delete buttons in Actions column for each row
**Actual:** No Delete buttons visible (Actions column empty)

**Root Cause:** The `admin` role lacks `role-assignment-delete` permission

**Impact:** Admin users cannot delete role assignments via the UI

---

### Step 8: Verify Pagination
**Status:** ✅ PASS

**Expected:** Pagination controls navigate between pages
**Actual:** Next Page button works correctly

**API Behavior:**
- Clicking Next Page triggers: GET `/api/v1/role-assignments/` → 200 OK
- **Issue:** No pagination params (skip/limit) in request - appears to use client-side pagination

**Evidence:**
- URL updates to `?page=2&per_page=10`
- Active page indicator shows "2"
- Table updates with second page of data

---

### Step 9: Verify Error Handling
**Status:** ⏭️ SKIPPED

**Reason:** Cannot test invalid role assignment creation without Create functionality

---

### Step 10: Verify Permission Denial
**Status:** ⏭️ SKIPPED

**Reason:** Would require switching users, but core CRUD operations already blocked by missing permissions

---

## Critical Bugs Discovered

### Bug #1: Missing User Names in API Response
**Severity:** High
**Component:** Backend API

**Description:** The `/api/v1/role-assignments/` endpoint returns `"user_name": null` for all assignments, despite the schema defining this field.

**Impact:** Role assignments table shows "—" instead of actual user names, making the page difficult to use.

**Evidence:**
- API Response shows: `"user_name": null` for all 20 assignments
- `role_name` is correctly populated
- `granted_by_name` is also null

**Likely Cause:** Backend query not joining with users table to populate `user_name` field

**Files to Check:**
- `backend/app/api/v1/endpoints/role_assignments.py`
- `backend/app/services/rbac_unified.py`

---

### Bug #2: Missing RBAC Permissions for Role Assignments
**Severity:** Critical
**Component:** RBAC Configuration

**Description:** The `rbac.json` configuration does not include `role-assignment-*` permissions for any role, including `admin`.

**Missing Permissions:**
- `role-assignment-read` (though page still loads - possible fallback or missing check)
- `role-assignment-create` (Create button not visible)
- `role-assignment-update` (Edit buttons not visible)
- `role-assignment-delete` (Delete buttons not visible)

**Impact:** Admin users cannot manage role assignments via the UI, breaking a core feature of the unified RBAC system.

**Files to Check:**
- `backend/config/rbac.json` (add missing permissions)
- Frontend permission checks for `role-assignment-read` (may be missing)

---

## Minor Issues

### Issue #1: Console Errors
**Type:** Non-critical

**Errors:**
- Multiple 404 errors for `favicon.ico`
- Antd deprecation warning: `destroyOnClose` is deprecated, use `destroyOnHidden` instead

**Impact:** None on functionality

---

### Issue #2: Client-Side Pagination
**Type:** Performance/Architecture

**Description:** Pagination appears to be client-side - all 20 records fetched at once, no pagination parameters in API requests.

**Impact:** For large datasets (100+ role assignments), this could impact performance.

**Recommendation:** Implement server-side pagination with `skip`/`limit` parameters.

---

## Test Data

### Discovered Role Assignments (20 total)

**Global Assignments:**
1. admin (e03556f3-4385-5d68-a685-af307fc8af5c)
2. manager (533a7e61-6b73-5978-a751-7862efa734f7)
3. viewer (85b44758-76ab-5a80-9d47-836a09d00e03)

**Project Scopes:**
- d54fbbe6-f3df-51db-9c3e-9408700442be: admin, manager, viewer
- 33180155-2634-4773-823c-570d1edbf4f2: project_manager, project_editor, project_viewer
- fac1bcef-8c67-4dc0-a179-e019c0572a52: project_manager, project_editor, project_viewer
- 2245885f-27ea-412d-919c-fd766b8b1c5f: project_manager, project_editor, project_viewer
- 406a9c3e-d35b-4340-897d-ba314feb9b64: project_admin, project_manager, project_viewer

**Admin User Permissions:**
76 permissions confirmed, but notably missing all `role-assignment-*` permissions.

---

## Screenshots

1. `snapshots/01-role-assignments-page.png` - Initial page load showing "—" for user names
2. `snapshots/02-page-2-pagination.png` - Page 2 with pagination

---

## Recommendations

### Immediate Fixes (Required)

1. **Add `role-assignment-*` permissions to rbac.json:**
   ```json
   "admin": {
     "permissions": [
       // ... existing permissions ...
       "role-assignment-read",
       "role-assignment-create", 
       "role-assignment-update",
       "role-assignment-delete"
     ]
   }
   ```

2. **Fix `user_name` population in role assignments API:**
   - Ensure backend query joins with users table
   - Populate both `user_name` and `granted_by_name` fields

### Follow-up Improvements

1. Implement server-side pagination for role assignments endpoint
2. Add `role-assignment-read` permission check to the GET endpoint
3. Fix Antd deprecation warning (`destroyOnClose` → `destroyOnHidden`)
4. Add favicon.ico to eliminate 404 errors

---

## Documentation Discrepancies

**From Research vs. Actual Implementation:**

| Documented | Actual |
|------------|--------|
| Role assignments API requires permissions | Permissions don't exist in rbac.json |
| `user_name` field in schema | Always null in response |
| Scoped role assignments (global/project/change_order) | ✅ Correctly implemented |
| 5 defined roles (admin, manager, etc.) | ✅ Confirmed in data |

---

## Conclusion

The unified RBAC system's role assignment page is **non-functional for core CRUD operations** due to missing permissions in the configuration. The page loads and displays data, but admin users cannot create, edit, or delete role assignments via the UI. Additionally, the `user_name` field being null significantly degrades the user experience.

These issues should be addressed before the unified RBAC system is considered production-ready.

---

## Next Test Iterations

Once critical bugs are fixed:
1. Test create role assignment flow (modal validation, form submission)
2. Test edit role assignment flow (pre-filling form, updating values)
3. Test delete role assignment flow (confirmation dialog, removal)
4. Test permission denial with non-admin users
5. Test change_order scoped role assignments
6. Verify user names populate correctly after backend fix
