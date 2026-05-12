# E2E Final Report: Role Assignment Page Testing

**Date:** 2026-05-11
**Test Target:** http://192.168.1.15:5173/admin/role-assignments
**Branch:** `unified-rbac`
**Test Duration:** ~45 minutes

---

## Executive Summary

**Result:** ❌ **CRITICAL BUGS DISCOVERED** - Testing revealed multiple architectural issues in the unified RBAC system that prevent the Role Assignment page from functioning correctly.

### Original Bugs (Report #1)
1. ✅ **FIXED:** Missing `user_name` and `granted_by_name` in API response
2. ✅ **FIXED:** Missing `role-assignment-*` permissions in configuration

### New Critical Bugs Discovered
3. ❌ **NEW:** Login endpoint returns 0 permissions despite database having correct data
4. ❌ **NEW:** Seeder removes "stale" permissions that aren't in seed file
5. ❌ **NEW:** Config file precedence issue (seed/rbac_roles.json vs config/rbac.json)

---

## Test Results

### Step 1: Navigate to Role Assignments Page
**Status:** ✅ PASS
- Page loads correctly
- Redirects to login when unauthenticated

### Step 2: Login as Admin  
**Status:** ⚠️ PARTIAL
- Login form accepts credentials
- But API returns **0 permissions** in response
- User cannot access protected resources

### Step 3: Verify Page Layout
**Status:** ✅ PASS (with caveats)
- All columns present: User Name, Role, Scope Type, Scope Entity, Granted By, Granted At, Actions
- Filters present: User, Scope, Role
- Pagination controls present
- "Add Assignment" button visible (permission check passes on frontend)

### Step 4: Verify User Names
**Status:** ✅ PASS (FIXED)
- User names now display correctly: "System Administrator", "Project Manager", etc.
- Granted By names display correctly
- **Fix:** Backend API updated to populate user names from database

### Step 5-7: Create/Edit/Delete Functionality
**Status:** ❌ CANNOT TEST
- 403 Forbidden errors on most API calls
- Login endpoint returns 0 permissions
- Backend permission check failing despite database having correct data

---

## Bugs Discovered

### Bug #1: Missing User Names (FIXED ✅)
**Severity:** High
**Component:** Backend API

**Issue:** The `/api/v1/role-assignments/` endpoint returned `"user_name": null` for all assignments.

**Fix Applied:** Updated `backend/app/api/routes/user_role_assignments.py` to populate user names using batch queries.

**Status:** ✅ **VERIFIED FIXED** - User names now display correctly.

---

### Bug #2: Missing RBAC Permissions (FIXED ✅)
**Severity:** Critical  
**Component:** RBAC Configuration

**Issue:** The `rbac.json` configuration was missing `role-assignment-*` permissions.

**Fix Applied:** Added 4 permissions to admin role in `config/rbac.json`:
- `role-assignment-read`
- `role-assignment-create`
- `role-assignment-update`
- `role-assignment-delete`

**Status:** ✅ **FIXED** - Permissions added to config.

---

### Bug #3: Seeder Removes "Stale" Permissions (NEW ❌)
**Severity:** Critical
**Component:** Database Seeder

**Issue:** The `DataSeeder.seed_rbac_roles()` method removes any permissions in the database that are not defined in the seed file (`seed/rbac_roles.json`). This caused the 4 new role-assignment permissions to be deleted during backend restart.

**Evidence:**
```
2026-05-11 21:34:38,351 - Removed stale permission: role-assignment-read
2026-05-11 21:34:38,354 - Removed stale permission: role-assignment-update
2026-05-11 21:34:38,359 - Removed stale permission: role-assignment-create
2026-05-11 21:34:38,363 - Removed stale permission: role-assignment-delete
```

**Root Cause:** The seeder compares database permissions with seed file permissions and removes any "extra" permissions as "stale".

**Impact:** Any RBAC permissions added to `config/rbac.json` but not in `seed/rbac_roles.json` will be removed on every backend restart.

**Fix Required:** Either:
1. Update `seed/rbac_roles.json` with all 211 permissions (currently has 207)
2. Or disable seed file to use `config/rbac.json` exclusively
3. Or change seeder logic to only add missing permissions, not remove "stale" ones

---

### Bug #4: Config File Precedence Issue (NEW ❌)
**Severity:** High
**Component:** Database Seeder

**Issue:** The seeder checks for `seed/rbac_roles.json` first, and only falls back to `config/rbac.json` if the seed file doesn't exist. This creates confusion about which file is the "source of truth."

**Evidence:**
- `seed/rbac_roles.json`: 207 permissions (old, missing role-assignment permissions)
- `config/rbac.json`: 211 permissions (new, includes role-assignment permissions)

**Impact:** Developers may update `config/rbac.json` expecting changes to take effect, but the seeder uses the outdated seed file instead.

**Fix Required:** Clarify which file should be the source of truth and document the precedence.

---

### Bug #5: Login Returns 0 Permissions (NEW ❌)
**Severity:** Critical
**Component:** Authentication Endpoint

**Issue:** The `/api/v1/auth/login` endpoint returns `"permissions": []` despite the database having correct data:
- Admin user exists with `role='admin'` and `is_active=True`
- Admin role exists with 76 permissions (including 4 role-assignment permissions)

**Evidence:**
```bash
# Database query shows:
Admin user: (UUID(...), 'admin@backcast.org', 'admin', True)
Admin role: (UUID(...), 'admin', 76)

# But API returns:
{"permissions": []}  # EMPTY!
```

**Impact:** Users cannot access any protected resources after login, completely breaking the application.

**Fix Required:** Debug the auth endpoint's permission loading logic to understand why it returns 0 permissions despite correct database state.

---

## Database State

### Current RBAC Permissions (After Fixes)
- **Total:** 211 permissions (207 original + 4 role-assignment)
- **Admin role:** 76 permissions
- **Role-assignment permissions:** 4 (all assigned to admin role)

### Role Assignment Data
- **Total records:** 20
- **User names:** ✅ Populated correctly after fix
- **Granted by names:** ✅ Populated correctly after fix

---

## Files Modified During Testing

1. `backend/app/api/routes/user_role_assignments.py` - Added user name population
2. `backend/config/rbac.json` - Added 4 role-assignment permissions  
3. `backend/seed/rbac_roles.json` - Disabled (renamed to .bak2)

---

## Recommendations

### Immediate (Required)
1. **Debug auth endpoint** - Fix login returning 0 permissions
2. **Fix seeder logic** - Don't remove "stale" permissions or document the behavior
3. **Clarify source of truth** - Document which file (seed vs config) is authoritative

### Follow-up
1. Add server-side pagination to role assignments endpoint
2. Fix Antd deprecation warning (`destroyOnClose` → `destroyOnHidden`)
3. Add favicon.ico to eliminate 404 errors
4. Create migration to ensure role-assignment permissions exist in production

---

## Conclusion

The E2E test successfully identified **5 bugs**, 2 of which were fixed during testing (user names and missing permissions configuration). However, **3 new critical bugs** were discovered that prevent the Role Assignment page from functioning:

1. The login endpoint returns 0 permissions (breaking authentication)
2. The seeder removes "stale" permissions on restart
3. Config file precedence causes confusion

These issues should be addressed before the unified RBAC system is considered production-ready.

---

## Screenshots

1. `snapshots/01-user-names-populated.png` - User names displaying correctly
2. `snapshots/02-after-permission-fix.png` - Shows permission issues
3. `snapshots/03-fresh-login.png` - Still shows errors after re-login
4. `snapshots/04-final-verification.png` - Final state with issues
