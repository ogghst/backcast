# E2E Test Report: System Role CRUD Operations

**Date:** 2026-05-11
**Tester:** Claude (automated via Playwright)
**Environment:** Frontend http://localhost:5173 / Backend http://localhost:8020

---

## Summary

| Metric | Count |
|--------|-------|
| Total Tests | 8 |
| Passed | 8 |
| Failed | 0 |
| Issues Found | 1 (UX) |

**Result: ALL PASS**

---

## Test Results

### T1: Login as Admin — PASS
- **Action:** Navigate to /login, fill admin@backcast.org / adminadmin, click Login
- **Expected:** Redirected to dashboard with admin access
- **Actual:** Redirected to `/`, dashboard shows "Welcome back, System" with full project data
- **Evidence:** `snapshots/t1-admin-dashboard.png`

### T2: Navigate to RBAC Admin page — PASS
- **Action:** Navigate to /admin/rbac
- **Expected:** RBAC Configuration page with list of 7 system roles
- **Actual:** Table displays 7 roles (admin, ai-admin, ai-manager, ai-viewer, change_order_approver, manager, viewer), all with "System" badge, all with disabled delete buttons
- **DB Verification:** `SELECT name, is_system, perm_count FROM rbac_roles` — matches UI exactly (72, 18, 39, 14, 7, 46, 10 permissions respectively)
- **Evidence:** `snapshots/t2-rbac-roles-list.png`

### T3: Create Custom Role — PASS
- **Action:** Click "Create Role", fill name="Test Role", description="E2E test role for CRUD testing", select user-read + project-read permissions, click OK
- **Expected:** New role appears in table with 2 permissions, no System badge, delete button enabled
- **Actual:** "Test Role" appears at top of table, description shown, "2 permissions", enabled edit/delete buttons
- **DB Verification:**
  ```sql
  SELECT name, description, is_system, permissions FROM rbac_roles ...
  → name=Test Role, is_system=false, permissions={user-read, project-read}
  ```
- **Evidence:** `snapshots/t3-role-created.png`

### T4: View Custom Role Details — PASS
- **Action:** Click edit button on "Test Role"
- **Expected:** Edit dialog shows correct name, description, and selected permissions
- **Actual:** Edit Role dialog opens with:
  - Name: "Test Role"
  - Description: "E2E test role for CRUD testing"
  - User Management: 1/4 (Read checked with checkmark icon)
  - Project: 1/4 (Read checked with checkmark icon)
  - All other categories: 0/N
- **Evidence:** `snapshots/t4-view-role-details.png`

### T5: Update Custom Role — PASS
- **Action:** In edit dialog, rename to "Updated Test Role", uncheck user-read, check wbe-read, click OK
- **Expected:** Role name updated, permissions changed from {user-read, project-read} to {project-read, wbe-read}
- **Actual:** Table shows "Updated Test Role" with "2 permissions"
- **DB Verification:**
  ```sql
  → name=Updated Test Role, permissions={project-read, wbe-read}
  ```
  Name and permissions atomically updated correctly.
- **Evidence:** `snapshots/t5-role-updated.png`

### T6: System Role Deletion Blocked — PASS
- **Action:** Verify delete button is disabled for admin role; attempt API DELETE on admin role
- **Expected:** UI blocks deletion (disabled button), API returns error
- **Actual:**
  - UI: Delete button `[disabled]` on all 7 system roles
  - API: `DELETE /api/v1/admin/rbac/roles/{admin_id}` → `{"detail": "Cannot delete system role"}`
- **DB Verification:** Admin role still exists (count=1)
- **Evidence:** Visible in T2/T5 screenshots

### T7: Delete Custom Role — PASS
- **Action:** Click delete on "Updated Test Role", confirm with "Yes, Delete" button
- **Expected:** Confirmation dialog appears, then role removed from table and DB
- **Actual:**
  - Confirmation dialog: "Are you sure you want to delete this role? Role 'Updated Test Role' will be permanently removed."
  - After confirm: Table reverts to 7 items ("1-7 of 7 items"), only system roles remain
- **DB Verification:**
  ```sql
  SELECT count(*) as total, count(*) FILTER (WHERE is_system = false) as custom FROM rbac_roles;
  → total=7, custom=0
  ```
- **Evidence:** `snapshots/t7-role-deleted.png`

### T8: Viewer Permission Enforcement — PASS (UX note)
- **Action:** Logout, login as viewer@backcast.org, navigate to /admin/rbac
- **Expected:** Access denied or read-only interface
- **Actual:**
  - Page loads but shows "No data" (API returned 403 for roles list)
  - "Create Role" button is **disabled**
  - Three toast notifications: "Insufficient permissions"
  - Write operations fully blocked
- **UX Note:** Page renders an empty table instead of showing a clear "access denied" message or redirecting away. Functional but confusing UX.
- **Evidence:** `snapshots/t8-viewer-rbac-access.png`

---

## Issues Found

### Issue #1: Viewer RBAC page shows empty table instead of access denied (UX)
- **Severity:** Low (UX enhancement)
- **Category:** UX
- **Description:** When a viewer navigates to `/admin/rbac`, the page renders with an empty table ("No data") rather than informing the user they don't have permission to view this page.
- **Reproduction:** Login as viewer@backcast.org, navigate to /admin/rbac
- **Suggested fix:** Either redirect to a "forbidden" page or show an explicit "You don't have permission to manage roles" message instead of the empty table
- **Impact:** No security risk — data is properly protected via 403 responses

---

## Database State After Test

- 7 system roles remain (unchanged from baseline)
- 0 custom roles (test data cleaned up)
- No orphaned data in rbac_role_permissions

## Test Data Cleanup

- "Test Role" → created, renamed to "Updated Test Role", deleted. No residual data.
