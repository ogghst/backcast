# E2E Test Plan: Role Assignment Page

**Date:** 2026-05-11
**Test Target:** http://192.168.1.15:5173/admin/role-assignments
**Test Type:** UI Verification + API Integration

---

## Objective

Verify the Role Assignment page at `/admin/role-assignments` displays correctly, handles user interactions properly, and enforces RBAC permissions for role assignment CRUD operations.

---

## Prerequisites

### Environment Status
- ✅ Frontend: http://192.168.1.15:5173 (verified)
- ✅ Backend API: http://192.168.1.15:8020 (verified)
- ⚠️ Database: Direct PostgreSQL connection unavailable (MCP misconfigured)

### Default Login
- Email: `admin@backcast.org`
- Password: `adminadmin`

### Research Findings

#### Business Rules (from product-scope-analyzer)
- **Purpose**: Role assignments implement RBAC for access control and separation of duties
- **Management Authority**: Only System Administrators and Project Managers can assign/manage roles
- **Five Defined Roles**: admin, manager, department_manager, project_controller, executive_viewer
- **Scope-Based**: Role assignments can be global, project-scoped, or change_order-scoped
- **Permission Enforcement**: All role assignment operations require `role-assignment-*` permissions

#### Technical Architecture (from architecture-search)
- **Primary Tables**: `user_role_assignments`, `rbac_roles`, `rbac_role_permissions`
- **API Routes**: `/api/v1/role-assignments/` (GET, POST, PUT, DELETE)
- **Frontend Page**: `frontend/src/pages/admin/RoleAssignments.tsx`
- **RBAC Config**: `backend/config/rbac.json` (76 permissions for admin role)
- **Required Permissions**:
  - View: `role-assignment-read`
  - Create: `role-assignment-create`
  - Update: `role-assignment-update`
  - Delete: `role-assignment-delete`

---

## Test Steps

### Step 1: Navigate to Role Assignments Page
**Action:** Navigate to http://192.168.1.15:5173/admin/role-assignments

**Expected UI:**
- Page loads without errors
- Login redirect if not authenticated (expect redirect to `/login`)
- After login, role assignments table should be visible

**Expected API:**
- If authenticated, GET request to `/api/v1/role-assignments/`
- Response 200 with list of role assignments

**Verification:**
- Browser snapshot shows either login form or role assignments table
- Console has no errors
- Network requests show 200 status

---

### Step 2: Login as Admin
**Action:** Fill login form with admin credentials

**Form Fields:**
- Email: `admin@backcast.org`
- Password: `adminadmin`
- Click "Log In"

**Expected UI:**
- Successful login redirect to dashboard or role assignments page
- User menu shows admin user in top right

**Expected API:**
- POST to `/api/v1/auth/login` returns 200
- Response includes JWT token

**Verification:**
- Browser snapshot shows authenticated state
- Console has no authentication errors
- Network request returns 200 with token

---

### Step 3: Verify Page Layout and Data
**Action:** Navigate to role assignments page (if not already there)

**Expected UI Elements:**
- Page title: "Role Assignments" or similar
- Table with columns: User, Role, Scope Type, Scope ID, Granted By, Granted At, Actions
- Filter controls: User filter, Scope Type filter, Role filter
- Pagination controls (if data exceeds page size)
- "Create Role Assignment" button (visible only if has `role-assignment-create` permission)

**Expected API:**
- GET `/api/v1/role-assignments/` with query params for filters
- Response 200 with `UserRoleAssignmentRead[]`

**Verification:**
- Browser snapshot shows table with headers
- Table contains at least one role assignment row
- All expected columns are present
- Filters are visible and functional
- Create button is visible

---

### Step 4: Verify Filter Functionality
**Action:** Test scope type filter

**Expected UI:**
- Filter dropdown shows options: All, Global, Project, Change Order
- Selecting a filter updates the table to show only matching assignments

**Expected API:**
- GET `/api/v1/role-assignments/?scope_type=<selected_type>`
- Response 200 with filtered results

**Verification:**
- Browser snapshot after filter shows filtered results
- Network request shows correct query parameter

---

### Step 5: Verify Create Role Assignment Modal
**Action:** Click "Create Role Assignment" button

**Expected UI:**
- Modal opens with form fields:
  - User selector (dropdown or search)
  - Role selector (dropdown)
  - Scope Type selector (global, project, change_order)
  - Scope ID field (conditional, shown only if scope_type != global)
  - Metadata (optional JSON input)
  - Expires At (optional datetime picker)
- Submit and Cancel buttons

**Expected API:**
- No API call yet (modal opens client-side)

**Verification:**
- Browser snapshot shows modal with all expected form fields
- Form fields are properly labeled
- Submit button is enabled

---

### Step 6: Verify Permission Enforcement (Attempt Edit)
**Action:** Find an existing role assignment and click the "Edit" button

**Expected UI:**
- Edit modal opens with pre-filled form fields
- All fields from step 5 are present
- Current assignment values are displayed

**Expected API:**
- GET `/api/v1/role-assignments/{id}` (for fetching single assignment details)
- Response 200 with `UserRoleAssignmentRead`

**Verification:**
- Browser snapshot shows edit modal
- Form is pre-filled with correct values
- Console has no errors

---

### Step 7: Verify Table Actions
**Action:** Check available actions on role assignment rows

**Expected UI:**
- Each row has action buttons: Edit, Delete
- Buttons are enabled/disabled based on user permissions

**Expected API:**
- None (this is UI state check)

**Verification:**
- Browser snapshot shows action buttons
- At least one row has Edit and Delete buttons visible

---

### Step 8: Verify Responsive Design
**Action:** Resize browser window to different viewport sizes

**Expected UI:**
- Table remains readable at different widths
- No horizontal scroll at standard desktop width (1280px+)
- Mobile/tablet view adapts appropriately

**Expected API:**
- None (this is UI layout check)

**Verification:**
- Screenshots at different widths show proper responsive behavior

---

### Step 9: Verify Error Handling
**Action:** Try to create an invalid role assignment (duplicate user+scope)

**Expected UI:**
- Form validation error displayed
- Error message explains the constraint
- Modal remains open for correction

**Expected API:**
- POST `/api/v1/role-assignments/` returns 400 or 409
- Response includes error details

**Verification:**
- Browser snapshot shows error message
- Network request returns error status
- Console shows the error

---

### Step 10: Verify Permission Denial (Negative Test)
**Action:** This step requires switching to a non-admin user

**Expected UI:**
- User with `manager` role can view but limited actions
- User with `viewer` role cannot access page or sees read-only view

**Expected API:**
- If no permission: 403 Forbidden response
- If read-only: GET works but POST/PUT/DELETE return 403

**Verification:**
- Document observed behavior
- Note any discrepancies from expected RBAC behavior

---

## Expected Outcomes

1. **Success Criteria:**
   - Page loads and displays role assignments table
   - Admin user can create, edit, and view role assignments
   - Filters work correctly
   - Modals open with proper form fields
   - API calls return expected responses

2. **Edge Cases to Observe:**
   - Empty state behavior (no role assignments)
   - Permission-based UI hiding
   - Form validation for invalid inputs
   - Concurrent edit conflicts

3. **Potential Issues:**
   - Database MCP unavailable for direct state verification
   - Test data availability (seeded users and roles)
   - Permission boundary enforcement

---

## Cleanup Plan

1. **Do NOT delete** any role assignments created during testing (they may be needed for other tests)
2. Logout from admin account
3. Close browser
4. Document any test data created in the report

---

## Notes

- **Database Verification Limitation:** PostgreSQL MCP is misconfigured (port 5433), so direct database state verification is not available. Will rely on API responses and UI state for verification.
- **Test Data:** Need to discover available test users and roles through API since DB query is unavailable.
- **Branch:** Current branch is `unified-rbac` - testing the newly implemented unified RBAC system from ADR-014.
