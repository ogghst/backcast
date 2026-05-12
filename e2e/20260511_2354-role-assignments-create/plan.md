# E2E Test Plan: Role Assignment Modal Create Operations

**Date**: 2026-05-11
**Route**: `/admin/role-assignments`
**Goal**: Verify role assignment creation across all three scopes (global, project, change_order)

---

## Research Summary

### Business Rules (Source: docs/01-product-scope/)
- **Three Scope Levels**: Global (system-wide), Project (per-project), Change Order (per-CO)
- **Admin Role**: Can create role assignments at any scope
- **Validation Rules**:
  - Global scope: `scope_id` must be NULL
  - Project/Change Order scope: `scope_id` must be provided
  - Uniqueness: One user cannot have multiple roles in the same scope (user_id + scope_type + scope_id unique)
- **Audit Trail**: All assignments track `granted_by` and `granted_at`

### Technical Architecture (Source: docs/02-architecture/)
- **Database**: `user_role_assignments` table (SimpleEntityBase - non-versioned)
- **API**: `POST /api/v1/role-assignments`
- **Frontend**: AssignmentModal component with dynamic scope entity dropdowns
- **RBAC**: Requires `role-assignment-create` permission (admin only)

---

## Prerequisites

- **Environment**:
  - Frontend: `http://192.168.1.15:5173`
  - Backend: `http://192.168.1.15:8020`
- **Test User**: `admin@backcast.org` / `adminadmin` (has admin role)
- **Required Permissions**: `role-assignment-create` (admin has this)

---

## Test Steps

### Step 1: Login as Admin
**Action**: Navigate to login and authenticate as admin user
**Expected UI**:
- Redirect to dashboard after login
- User menu shows admin user
**Expected API**: `POST /api/v1/auth/login` returns 200

### Step 2: Navigate to Role Assignments Page
**Action**: Navigate to `/admin/role-assignments`
**Expected UI**:
- Page title: "Role Assignments"
- Table showing existing role assignments
- "Add Assignment" button visible
**Expected API**: `GET /api/v1/role-assignments` returns 200

### Step 3: Open Create Modal
**Action**: Click "Add Assignment" button
**Expected UI**:
- Modal opens with title "Add Role Assignment"
- Form fields: User (dropdown), Role (dropdown), Scope Type (dropdown), Scope Entity (conditional)
- Save and Cancel buttons

### Step 4: Create Global Scope Role Assignment
**Action**:
- Select a user (e.g., "viewer" role user)
- Select role (e.g., "manager")
- Select scope type: "global"
- Click Save
**Expected UI**:
- Modal closes
- Success toast/notification
- New assignment appears in table with "global" tag
**Expected API**: `POST /api/v1/role-assignments` returns 201 with assignment data

### Step 5: Create Project Scope Role Assignment
**Action**:
- Click "Add Assignment"
- Select a user
- Select role (e.g., "viewer")
- Select scope type: "project"
- Select project from dropdown (populated dynamically)
- Click Save
**Expected UI**:
- Modal closes
- Success toast/notification
- New assignment appears in table with "project" tag and project name
**Expected API**: `POST /api/v1/role-assignments` returns 201

### Step 6: Create Change Order Scope Role Assignment
**Action**:
- Click "Add Assignment"
- Select a user
- Select role (e.g., "ai-viewer")
- Select scope type: "change_order"
- Select change order from dropdown (populated dynamically)
- Click Save
**Expected UI**:
- Modal closes
- Success toast/notification
- New assignment appears in table with "change_order" tag and CO number
**Expected API**: `POST /api/v1/role-assignments` returns 201

### Step 7: Verify Validation - Duplicate Assignment
**Action**:
- Click "Add Assignment"
- Select the same user + scope_type + scope_id as Step 4
- Select a different role
- Click Save
**Expected UI**:
- Error message: "User already has a role in this scope"
- Modal remains open
**Expected API**: `POST /api/v1/role-assignments` returns 400 with validation error

### Step 8: Verify Validation - Missing Scope ID
**Action**:
- Click "Add Assignment"
- Select a user
- Select role
- Select scope type: "project"
- Do NOT select a project
- Click Save
**Expected UI**:
- Error message: "Scope entity is required for this scope type"
- Or submit button disabled
**Expected API**: No API call (frontend validation) or 400 if backend validates

---

## Verification Queries

**Note**: Database verification skipped due to MCP port mismatch (DB on 5432, MCP on 5433). Verification will be UI-only.

---

## Cleanup Plan

After testing, delete the created role assignments:
1. Navigate to `/admin/role-assignments`
2. For each assignment created in steps 4-6, click "Delete" button
3. Confirm deletion
4. Verify assignments removed from table

---

## Success Criteria

- ✅ Modal opens and form renders correctly
- ✅ All three scope types can be selected
- ✅ Scope entity dropdowns appear for project/change_order scopes
- ✅ Global scope assignment created successfully
- ✅ Project scope assignment created successfully
- ✅ Change Order scope assignment created successfully
- ✅ Duplicate assignment validation works
- ✅ Missing scope ID validation works
- ✅ API returns correct status codes

---

## Documentation References

- **Schema**: `backend/app/models/domain/user_role_assignment.py`
- **API Routes**: `backend/app/api/routes/user_role_assignments.py`
- **Frontend**: `frontend/src/pages/admin/RoleAssignments.tsx`
- **Modal**: `frontend/src/features/admin/role-assignments/components/AssignmentModal.tsx`
- **ADR-014**: `docs/02-architecture/decisions/ADR-014-unified-rbac.md`
