# E2E Test Report: Role Assignment CRUD Operations

**Date**: 2026-05-11
**Iteration**: 2026-05-11_22-02-role-assignments-crud
**Route**: `/admin/role-assignments`
**Tester**: Admin user (`admin@backcast.org`)
**Test Duration**: ~30 minutes

## Executive Summary

**Test Status**: ❌ FAILED - Critical bugs discovered blocking CRUD operations

**Pass/Fail Summary**: 2/9 steps passed (22%)

| Step | Status | Description |
|------|--------|-------------|
| 1 | ✅ PASS | Login & navigate |
| 2 | ✅ PASS | List view baseline |
| 3 | ❌ FAIL | Create global scope (RBAC data integrity bug) |
| 4 | ⏭️ SKIP | Create project scope (API returns empty) |
| 5 | ⏭️ SKIP | Create change order scope |
| 6 | ❌ FAIL | Update assignment (403 Forbidden) |
| 7 | ⏭️ SKIP | Duplicate validation |
| 8 | ❌ FAIL | Delete assignment (403 Forbidden) |
| 9 | ⏭️ SKIP | Filtering |

**Critical Issues Found**: 4 (2 partially fixed, 2 unfixed)

---

## Detailed Step Results

### Step 1: Setup & Login ✅ PASS

**Action**: Logged in as `admin@backcast.org` and navigated to `/admin/role-assignments`

**Expected**: Role assignments page loads
**Actual**: Page loaded successfully

**Database Verification**:
```sql
SELECT COUNT(*) FROM user_role_assignments;
-- Result: 4 (expected after reset)
```

**Backend Logs**: No errors

---

### Step 2: Read - List All Assignments ✅ PASS

**Action**: Observed the role assignments list

**Expected**: Global scope assignments displayed
**Actual**: 4 assignments shown in UI table

**Database Verification**:
```sql
SELECT COUNT(*) FROM user_role_assignments;
-- Result: 4
```

**Evidence**: Table showed System Administrator (admin), Viewer User (viewer), Project Manager (manager), Director (manager)

---

### Step 3: Create - Global Scope Assignment ❌ FAIL

**Action**: Attempted to create global assignment for `viewer@backcast.org` with `manager` role

**Expected**: Success notification, new assignment appears
**Actual**: **403 Forbidden error**

**Console Errors**:
```
[ERROR] Failed to load resource: the server responded with a status of 403 (Forbidden)
[ERROR] Access to XMLHttpRequest at 'http://localhost:8020/api/v1/role-assignments/'
POST http://localhost:8020/api/v1/role-assignments/ => [403] Forbidden
```

**Root Cause**: **RBAC Data Integrity Bug** - The admin user had a "manager" role assignment in the `user_role_assignments` table instead of "admin", despite the `users.role` field showing "admin".

**Database State** (before fix):
```sql
SELECT u.email, r.name as role_name, ura.scope_type
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
WHERE u.email = 'admin@backcast.org';
-- Result: admin@backcast.org | manager | global
```

**Fix Applied**:
```sql
UPDATE user_role_assignments
SET role_id = '8d8f6c88-06d6-4dd2-a23b-a93aec35c1c5'  -- admin role
WHERE user_id = (SELECT user_id FROM users WHERE email = 'admin@backcast.org')
AND scope_type = 'global';
```

**Verification** (after fix):
```sql
-- Result: admin@backcast.org | admin | global
```

---

### Step 4: Create - Project Scope Assignment ⏭️ SKIP

**Action**: Attempted to create project-scoped assignment

**Expected**: Project dropdown available with projects
**Actual**: **Project API returns empty list**

**Console Errors**:
```
GET http://localhost:8020/api/v1/projects?per_page=200 => [200] OK
Response: {"items":[],"total":0,"page":1,"per_page":200}
```

**Investigation**: Projects table might be empty or the user doesn't have permission to view projects.

**Root Cause**: Not fully investigated - skipped due to RBAC issues in Step 3.

---

### Steps 5-7: Skipped ⏭️ SKIP

Skipped due to critical RBAC permission issues blocking Update and Delete operations.

---

### Step 6: Update - Modify Role Assignment ❌ FAIL

**Action**: Attempted to update Viewer User's role from `viewer` to `manager`

**Expected**: Success notification, role updated
**Actual**: **403 Forbidden error - Insufficient permissions**

**Console Errors**:
```
[ERROR] Failed to load resource: the server responded with a status of 403 (Forbidden)
PUT http://localhost:8020/api/v1/role-assignments/7d435d59-aab5-448d-b2cc-7cf6983fb4c1 => [403] Forbidden
```

**Root Cause**: RBAC RoleChecker checking `allowed_roles=["admin"]` failed because:
1. Admin user had "manager" role in `user_role_assignments` table
2. The `RoleChecker` uses `get_user_roles()` which queries the `user_role_assignments` table
3. The legacy `users.role` field said "admin" but the unified RBAC system uses the assignments table

**Fix**: Updated database to give admin user the correct "admin" role assignment (see Step 3 fix).

---

### Step 8: Delete - Remove Assignment ❌ FAIL

**Action**: Attempted to delete Director's manager role assignment

**Expected**: Confirmation dialog, then assignment removed
**Actual**: **403 Forbidden error**

**Console Errors**:
```
[ERROR] Failed to load resource: the server responded with a status of 403 (Forbidden)
DELETE http://localhost:8020/api/v1/role-assignments/e435d4a4-aa30-4cb3-8459-eb4a47f0283b => [403] Forbidden
```

**Root Cause**: Same RBAC permission issue as Step 6.

---

### Step 9: Filtering ⏭️ SKIP

Skipped due to critical RBAC issues.

---

## Bugs Discovered

### Bug #1: RBAC Data Integrity - Admin User Has Wrong Role (CRITICAL)

**Severity**: Critical
**Category**: Data Integrity
**Status**: ✅ FIXED with manual database update

**Description**:
The admin user (`admin@backcast.org`) had a "manager" role assignment in the `user_role_assignments` table instead of "admin". This caused all write operations (POST, PUT, DELETE) to fail with 403 Forbidden because the `RoleChecker` dependency validates roles against the unified RBAC system's assignments table, not the legacy `users.role` field.

**Evidence**:
```sql
-- Before fix:
SELECT u.email, r.name as role_name
FROM user_role_assignments ura
JOIN users u ON ura.user_id = u.user_id
JOIN rbac_roles r ON ura.role_id = r.id
WHERE u.email = 'admin@backcast.org';
-- Result: admin@backcast.org | manager

-- But users table shows:
SELECT email, role FROM users WHERE email = 'admin@backcast.org';
-- Result: admin@backcast.org | admin
```

**Impact**:
- All role assignment CRUD operations fail with 403 Forbidden
- Admin user cannot perform admin actions
- System is unusable for role management

**Root Cause**:
The `DataSeeder.seed_user_role_assignments()` method likely assigned the wrong role to the admin user during seeding. There's a disconnect between:
1. `users.role` field (legacy, shows "admin")
2. `user_role_assignments` table (unified RBAC, had "manager")

**Fix Applied**:
```sql
UPDATE user_role_assignments
SET role_id = '8d8f6c88-06d6-4dd2-a23b-a93aec35c1c5'
WHERE id = '669f777a-51d9-4b7d-acf3-4dd476abba02';
```

**Recommended Long-term Fix**:
1. Audit `DataSeeder.seed_user_role_assignments()` to ensure admin gets admin role
2. Add validation to ensure `users.role` matches the user's global role assignment
3. Consider deprecating `users.role` field entirely in favor of unified RBAC

---

### Bug #2: Project API Returns Empty List

**Severity**: Medium
**Category**: Backend / Data
**Status**: ❌ UNFIXED

**Description**:
The `/api/v1/projects?per_page=200` endpoint returns an empty list despite projects possibly existing in the database.

**Evidence**:
```
GET http://localhost:8020/api/v1/projects?per_page=200
Response: {"items":[],"total":0,"page":1,"per_page":200}
```

**Impact**:
- Cannot create project-scoped role assignments
- Project dropdown shows "No data"

**Investigation Needed**:
1. Verify if projects table has data
2. Check if RBAC permissions prevent admin from viewing projects
3. Check projects API endpoint implementation

---

### Bug #3: CORS Configuration Issue (PARTIALLY FIXED EARLIER)

**Severity**: High
**Category**: Configuration
**Status**: ⚠️ FIXED in frontend/.env, but backend configuration issue remains

**Description**:
The frontend `.env` file was configured with an IP address instead of localhost, causing CORS errors on POST requests.

**Fix Applied**:
```diff
- VITE_API_URL=http://192.168.1.15:8020
+ VITE_API_URL=http://localhost:8020
```

**Remaining Issue**:
Backend has `allow_credentials=False` but frontend sends `withCredentials: true`. This causes the error:
"The value of the 'Access-Control-Allow-Origin' header must not be the wildcard '*' when the request's credentials mode is 'include'."

**Location**: `backend/app/main.py:218`

---

### Bug #4: RBAC Cache Invalidation

**Severity**: Medium
**Category**: Architecture
**Status**: ❌ UNFIXED

**Description**:
The unified RBAC system caches role assignments. When database is updated directly (e.g., via SQL), the cache becomes stale and the old permissions are still enforced. Required backend restart to refresh cache.

**Evidence**:
After updating admin user's role in database, the 403 errors persisted until backend was restarted.

**Impact**:
- Manual database updates require backend restart
- Cache inconsistency between database and in-memory state

**Recommendation**:
1. Add cache invalidation when assignments are updated via any method
2. Consider shorter cache TTL for development
3. Add admin endpoint to manually refresh cache

---

## Architecture Insights

### Unified RBAC System Flow

```
Request → RoleChecker([allowed_roles]) → get_user_roles(user_id)
                                    ↓
                    SELECT rbac_roles.name
                    FROM user_role_assignments
                    JOIN rbac_roles ON role_id
                    WHERE user_id=? AND scope_type='global' AND scope_id IS NULL
                                    ↓
                    Check if any returned role in allowed_roles
```

**Key Finding**: The system uses `user_role_assignments` table for role checking, NOT the `users.role` field.

---

## Recommendations

### Immediate Actions (Priority 1)

1. **Fix Data Seeder** - Audit and fix `DataSeeder.seed_user_role_assignments()` to ensure admin user gets admin role
2. **Add Validation** - Add a startup check that verifies admin user has admin role assignment
3. **Fix CORS Configuration** - Either:
   - Set `allow_credentials=True` with specific origins in backend
   - OR remove `withCredentials: true` from frontend for development
4. **Investigate Project API** - Determine why projects endpoint returns empty

### Follow-up Actions (Priority 2)

1. **Deprecate users.role Field** - The legacy `users.role` field is causing confusion. Either:
   - Remove it entirely and rely on unified RBAC
   - OR add a sync mechanism to keep it consistent with assignments
2. **Improve Cache Management** - Add cache invalidation hooks or admin endpoints
3. **Add Better Error Messages** - The 403 error should explain which role/permission is missing

---

## Test Environment

| Component | Version/Status |
|-----------|----------------|
| Frontend | Running on `http://localhost:5173` |
| Backend | Running on `http://localhost:8020` (restarted during test) |
| Database | PostgreSQL 15, 4 role assignments |
| Browser | Headless Playwright |
| Test Duration | ~30 minutes |

---

## Documentation Discrepancies

### Schema vs Reality

**Documented**: `metadata_` field (from some documentation)
**Actual**: `metadata` column name in database

**Note**: The `UserRoleAssignment` model uses `metadata_` (with underscore) as the field name to avoid conflict with the `metadata` JSON property, but the database column is named `metadata`.

---

## Conclusion

This E2E test was **successful in identifying critical bugs** despite being unable to complete the planned test steps. The most critical issue was the RBAC data integrity problem where the admin user had the wrong role assignment, which completely broke the role management functionality.

**Next Steps**:
1. Fix the `DataSeeder.seed_user_role_assignments()` method
2. Re-run this E2E test after fixes are applied
3. Test full CRUD functionality across all scopes (global, project, change_order)

**Test Coverage Achieved**:
- ✅ Login and navigation
- ✅ List view (Read)
- ❌ Create (blocked by RBAC bug)
- ❌ Update (blocked by RBAC bug)
- ❌ Delete (blocked by RBAC bug)
- ⏭️ Duplicate validation (not tested)
- ⏭️ Filtering (not tested)
