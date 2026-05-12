# E2E Test Plan: Authentication Flow

**Date:** 2026-05-11
**Iteration:** 2026-05-11_18-46-auth-flow
**Objective:** Verify complete authentication lifecycle including login, token management, permissions, and logout

## Research Summary

### Business Rules (Source: product-scope-analyzer)
- **Auth Method:** JWT-based with 15-minute access token expiration
- **Refresh Token:** 30-day validity, rotated on refresh
- **Password Hashing:** Argon2 (via passlib)
- **Default Test User:** admin@backcast.org / adminadmin
- **Other Users:** viewer@backcast.org / backcast, pm@backcast.org / backcast
- **Roles:** admin, manager, viewer, ai-viewer, ai-manager, ai-admin, change_order_approver
- **Session Timeout:** 30 minutes of inactivity
- **Token Storage:** localStorage (access_token, refresh_token, user profile)

### Technical Architecture (Source: architecture-search)
- **Auth API:** `/api/v1/auth/*` endpoints
- **Endpoints:**
  - POST `/login` - Returns TokenResponse with access_token and refresh_token
  - GET `/me` - Returns UserPublic with permissions array
  - POST `/refresh` - Returns new access_token
  - POST `/logout` - Revokes refresh token
  - POST `/register` - Creates new user
- **Database Tables:** users, rbac_roles, rbac_role_permissions, user_role_assignments, refresh_tokens
- **JWT Algorithm:** HS256
- **Frontend Store:** useAuthStore.ts (Zustand)
- **Login Page:** /login (Login.tsx)

## Prerequisites

1. Frontend running on `http://localhost:5173`
2. Backend running on `http://localhost:8020`
3. PostgreSQL running (for DB verification)
4. Test users seeded:
   - admin@backcast.org / adminadmin (admin role)
   - viewer@backcast.org / backcast (viewer role)
   - pm@backcast.org / backcast (manager role)

## Test Steps

### Step 1: Verify Login Form and Validation
**Action:** Navigate to login page and inspect the form
**Expected UI:**
- Login form visible with email and password fields
- Submit button ("Log In")
- No user logged in initially
**Expected DB:** users table has seeded test users with is_active=true
**Verification:**
- browser_snapshot for form elements
- Check for console errors

### Step 2: Successful Login with Admin Credentials
**Action:** Login with admin@backcast.org / adminadmin
**Expected UI:**
- Redirect to dashboard or projects page
- User menu shows admin user name
- Auth state updated (isAuthenticated=true)
**Expected DB:**
- User exists with is_active=true
- refresh_tokens table has new entry
**Verification:**
- browser_snapshot for authenticated state
- browser_network_requests: POST /login returns 200 with TokenResponse
- localStorage has access_token, refresh_token
- DB query: SELECT * FROM users WHERE email='admin@backcast.org'

### Step 3: Verify JWT Token and Permissions
**Action:** Call GET /me API endpoint to get user with permissions
**Expected UI:**
- User profile loaded with admin role
- Permissions array includes admin permissions
**Expected DB:**
- user_role_assignments table has admin role assignments
**Verification:**
- browser_network_requests: GET /me returns 200 with UserPublic
- Response includes permissions array
- DB query: Check user_role_assignments for admin role

### Step 4: Test Protected Route Access
**Action:** Navigate to a protected route (e.g., /projects)
**Expected UI:**
- Page loads successfully
- Project data visible
- No auth error
**Expected API:**
- GET /api/v1/projects returns 200 with Authorization header
**Verification:**
- browser_snapshot for projects page
- browser_network_requests: Check Authorization header present

### Step 5: Verify Admin Permissions
**Action:** Check that admin has full system access
**Expected UI:**
- Admin can access all features
- No permission denied errors
**Expected DB:**
- Admin has admin role in user_role_assignments
**Verification:**
- Navigate to admin-only pages
- Check for permission_denied errors (should be none)

### Step 6: Token Refresh Flow
**Action:** Wait for token to near expiration or manually trigger refresh
**Expected UI:**
- Token refreshed automatically
- User remains authenticated
- No logout or re-login required
**Expected API:**
- POST /refresh returns 200 with new access_token
**Verification:**
- browser_network_requests: Check for /refresh call
- New token in localStorage

### Step 7: Switch User to Viewer Role
**Action:** Logout as admin, login as viewer@backcast.org / backcast
**Expected UI:**
- Logout clears state
- Login as viewer succeeds
- Viewer has limited permissions
**Expected DB:**
- Old refresh token revoked (revoked_at set)
- New refresh token created for viewer
**Verification:**
- browser_snapshot for viewer state
- DB query: Check refresh_tokens for revoked token
- Verify viewer has limited access

### Step 8: Verify Viewer Permissions (Read-Only)
**Action:** Attempt actions that should be denied to viewer
**Expected UI:**
- Edit buttons disabled or hidden
- Create actions blocked
- Permission denied errors for restricted actions
**Expected API:**
- 403 Forbidden or 400 Bad Request for restricted actions
**Verification:**
- Try to access restricted features
- browser_network_requests: Check for 403 responses

### Step 9: Failed Login Attempt
**Action:** Attempt login with invalid credentials
**Expected UI:**
- Error message displayed
- No redirect to dashboard
- User remains unauthenticated
**Expected API:**
- POST /login returns 401 Unauthorized
**Verification:**
- browser_snapshot for error state
- browser_network_requests: 401 response

### Step 10: Logout Flow
**Action:** Logout as viewer
**Expected UI:**
- Redirect to login page
- localStorage cleared
- User menu removed
**Expected API:**
- POST /logout returns 200
- Refresh token revoked
**Verification:**
- browser_snapshot for logged out state
- localStorage empty
- DB query: refresh_tokens.revoked_at is set

## Cleanup Plan

1. Logout any active sessions
2. Close browser
3. No database cleanup needed (test data persists)

## Success Criteria

- [ ] All 10 steps pass
- [ ] No console errors during navigation
- [ ] All API calls return expected status codes
- [ ] Database state verified for each state-changing action
- [ ] Token storage and refresh working correctly
- [ ] Role-based permissions enforced correctly
