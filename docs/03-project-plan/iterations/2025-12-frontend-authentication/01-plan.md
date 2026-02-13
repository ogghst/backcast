# PLAN Phase: Frontend Authentication Implementation

**Story:** E02-U06 - Frontend Authentication (Login/Logout/Protect Routes)  
**Created:** 2025-12-30  
**Status:** Awaiting Approval  
**Approver:** TBD

---

## Phase 1: Context Analysis

### Documentation Review

**Product Scope:**
- Sprint 2 includes Story E02-U06: Frontend Authentication (Login/Logout/Protect Routes)
- Related to Story E02-U05: Frontend User & Department Management (Admin Only)
- Related to Story E02-U07: Frontend User Profile (View/Edit)

**Architecture:**
- Backend has complete authentication system:
  - `POST /api/v1/auth/login` - OAuth2 password flow
  - `POST /api/v1/auth/register` - User registration
  - `GET /api/v1/auth/me` - Get current user
  - JWT token-based authentication
- Frontend architecture:
  - React 18 + TypeScript 5+ + Vite
  - TanStack Query v5 for server state
  - Zustand v5 for client state
  - Axios client with interceptors
  - React Router v6 for routing

**Project Plan:**
- Current iteration: Sprint 2 - User Management Quality Improvements
- Backend authentication complete (Story 1.3)
- Frontend scaffolding complete
- Next step: Implement frontend authentication

### Codebase Analysis

**Existing Patterns:**
- Axios client in `src/api/client.ts` with interceptors
- Zustand store in `src/stores/useAppStore.ts` (currently only sidebar state)
- React Router setup in `src/routes/index.tsx`
- AppLayout component for authenticated views
- No AuthLayout component yet
- No authentication state management yet
- No protected route wrapper yet

**Backend Integration Points:**
- Login endpoint: `POST /api/v1/auth/login` (OAuth2PasswordRequestForm)
- Returns: `{ access_token: string, token_type: "bearer" }`
- Current user endpoint: `GET /api/v1/auth/me`
- Returns: `UserPublic` schema

---

## Phase 2: Problem Definition

### 1. Problem Statement

**What:** Users cannot authenticate with the application. All routes are currently public, and there's no way to identify the current user or protect admin-only features.

**Why Important:** Authentication is a prerequisite for:
- User & Department Management (admin-only features)
- User Profile management
- Role-based access control
- Personalized user experience

**Business Value:**
- Enables secure access to the application
- Foundation for all user-specific features
- Required for Sprint 2 deliverables

### 2. Success Criteria (Measurable)

**Functional Criteria:**
- ✅ Users can log in with email/password
- ✅ Users can log out
- ✅ Authentication state persists across page refreshes
- ✅ Protected routes redirect to login when unauthenticated
- ✅ Authenticated users can access protected routes
- ✅ Current user information is available throughout the app
- ✅ Invalid credentials show appropriate error messages
- ✅ Token expiration is handled gracefully

**Technical Criteria:**
- ✅ JWT token stored securely (httpOnly cookie or secure localStorage)
- ✅ Axios interceptor adds Authorization header automatically
- ✅ 401 responses trigger logout and redirect to login
- ✅ Type-safe authentication state
- ✅ No authentication logic in component code (separation of concerns)

**Business Criteria:**
- ✅ Login flow completes in <2 seconds (perceived performance)
- ✅ Zero authentication errors in happy path
- ✅ Clear error messages for authentication failures

### 3. Scope Definition

**In Scope:**
- Authentication state management (login/logout/current user)
- Login page UI (form with email/password)
- Protected route wrapper component
- Axios interceptor for token injection
- Token storage strategy
- Error handling for authentication failures
- Logout functionality
- Redirect to login for unauthenticated users

**Out of Scope:**
- User registration UI (future story)
- Password reset/forgot password (future story)
- Multi-factor authentication (future story)
- Social login (OAuth providers) (future story)
- Session timeout warnings (future story)
- Remember me functionality (future story)

---

## Phase 3: Implementation Options

| Aspect | Option A: Context API | Option B: Zustand Store | Option C: TanStack Query Only |
|--------|----------------------|------------------------|------------------------------|
| **Approach Summary** | React Context for auth state, custom hooks for login/logout | Zustand store for auth state + token, TanStack Query for user data | TanStack Query for all auth operations, no global state |
| **Design Patterns** | Provider pattern, Context + Reducer | Global store pattern, Middleware for persistence | Query-based state, Dependent queries |
| **Pros** | - React native solution<br>- No dependencies<br>- Familiar pattern | - Minimal boilerplate<br>- Built-in persistence<br>- DevTools support<br>- Aligns with architecture docs | - Server state where it belongs<br>- Automatic refetching<br>- Cache invalidation |
| **Cons** | - Performance issues with frequent updates<br>- Manual persistence logic<br>- More boilerplate | - Mixing client/server state concerns<br>- Manual sync with server | - No place for token storage<br>- Complex dependent queries<br>- Logout complexity |
| **Test Strategy Impact** | - Need to mock Context providers<br>- Integration tests complex | - Easy to test store logic<br>- Simple mocking | - Mock TanStack Query<br>- Test query dependencies |
| **Risk Level** | Medium | Low | Medium-High |
| **Estimated Complexity** | Moderate | Simple | Complex |

### Recommendation: **Option B (Zustand Store) + TanStack Query**

**Justification:**
1. **Aligns with existing architecture**: Frontend docs specify Zustand for "User authentication token" as an example use case
2. **Separation of concerns**: 
   - Zustand manages authentication state (token, isAuthenticated)
   - TanStack Query manages user data (current user profile)
3. **Best practices**: Token is client state (persisted), user data is server state (cached)
4. **Developer experience**: Built-in persistence middleware, DevTools, minimal boilerplate
5. **Testability**: Easy to mock Zustand store, straightforward testing
6. **Performance**: Better than Context API for frequent auth checks
7. **Maintainability**: Clear boundaries between auth state and user data

**Hybrid Approach Details:**
- **Zustand**: Store token, isAuthenticated flag, login/logout actions
- **TanStack Query**: Fetch and cache current user data (enabled only when authenticated)
- **Axios Interceptor**: Read token from Zustand store, inject into requests

---

## Phase 4: Technical Design

### TDD Test Blueprint

```
├── Unit Tests (isolated component behavior)
│   ├── useAuthStore tests
│   │   ├── ✅ Initial state (not authenticated)
│   │   ├── ✅ Login action stores token
│   │   ├── ✅ Logout action clears token
│   │   └── ✅ Token persistence (localStorage)
│   ├── ProtectedRoute component tests
│   │   ├── ✅ Redirects to login when not authenticated
│   │   ├── ✅ Renders children when authenticated
│   │   └── ✅ Preserves redirect URL
│   └── Login form tests
│       ├── ✅ Renders form fields
│       ├── ✅ Validates email format
│       ├── ✅ Validates password required
│       └── ✅ Submits credentials
│
├── Integration Tests (component interactions)
│   ├── Authentication flow tests
│   │   ├── ✅ Successful login updates store and redirects
│   │   ├── ✅ Failed login shows error message
│   │   ├── ✅ Logout clears state and redirects
│   │   └── ✅ Token refresh on page reload
│   └── Protected route integration
│       ├── ✅ Unauthenticated access redirects to login
│       └── ✅ Authenticated access renders content
│
└── End-to-End Tests (manual browser testing)
    ├── ✅ Complete login flow (login → dashboard → logout)
    ├── ✅ Protected route access (direct URL when logged out)
    └── ✅ Token expiration handling (401 response)
```

**First 5 Test Cases (ordered simplest to most complex):**

1. **useAuthStore - Initial State**
   - Verify store initializes with `isAuthenticated: false` and `token: null`

2. **useAuthStore - Login Action**
   - Call `login(token)`, verify `isAuthenticated: true` and token stored

3. **Login Form - Validation**
   - Submit empty form, verify error messages appear

4. **ProtectedRoute - Redirect**
   - Render ProtectedRoute when not authenticated, verify redirect to `/login`

5. **Integration - Successful Login**
   - Submit valid credentials, mock API response, verify store update and navigation

### Implementation Strategy

**High-Level Approach:**
1. Create authentication Zustand store (`useAuthStore`)
2. Create authentication API service layer
3. Build Login page component
4. Implement ProtectedRoute wrapper
5. Update Axios interceptor for token injection
6. Add 401 response interceptor for logout
7. Update routing configuration
8. Create AuthLayout for login page

**Key Technologies/Patterns:**
- **Zustand** with `persist` middleware for token storage
- **TanStack Query** for current user data fetching
- **React Router** `Navigate` component for redirects
- **Axios Interceptors** for request/response handling
- **Ant Design** components for UI (Form, Input, Button)

**Component Breakdown:**

1. **`src/stores/useAuthStore.ts`**
   - State: `token`, `isAuthenticated`
   - Actions: `login(token)`, `logout()`
   - Middleware: `persist` to localStorage

2. **`src/api/auth.ts`**
   - `loginUser(email, password)` → calls `/auth/login`
   - `getCurrentUser()` → calls `/auth/me`
   - Type-safe with Pydantic schema types

3. **`src/hooks/useAuth.ts`**
   - Custom hook combining `useAuthStore` + `useQuery` for current user
   - Returns: `{ user, isAuthenticated, login, logout, isLoading }`

4. **`src/pages/Login.tsx`**
   - Ant Design Form with email/password fields
   - Calls `login` mutation from `useAuth`
   - Redirects to dashboard on success

5. **`src/components/ProtectedRoute.tsx`**
   - Checks `isAuthenticated` from `useAuthStore`
   - Redirects to `/login` if not authenticated
   - Preserves intended destination in URL params

6. **`src/layouts/AuthLayout.tsx`**
   - Simple centered layout for login page
   - No sidebar/header

7. **`src/api/client.ts` (update)**
   - Request interceptor: inject token from `useAuthStore`
   - Response interceptor: handle 401 → logout + redirect

8. **`src/routes/index.tsx` (update)**
   - Add `/login` route with AuthLayout
   - Wrap protected routes with ProtectedRoute component

**Integration Points:**
- Axios client reads from Zustand store (no circular dependency)
- TanStack Query enabled only when `isAuthenticated === true`
- React Router handles navigation based on auth state

---

## Phase 5: Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
|-----------|-------------|-------------|--------|---------------------|
| Technical | Token stored in localStorage vulnerable to XSS | Medium | High | 1. Use httpOnly cookies if backend supports<br>2. Implement CSP headers<br>3. Sanitize all user inputs<br>4. Document security trade-offs |
| Technical | Circular dependency between Axios and Zustand | Low | Medium | Import store directly in interceptor, not via hooks |
| Integration | Backend token expiration not communicated | Medium | Medium | 1. Handle 401 responses globally<br>2. Test token expiration scenarios<br>3. Add token refresh logic (future) |
| UX | Redirect loops if login fails | Low | High | 1. Clear error messages<br>2. Prevent redirect if already on login page<br>3. Test edge cases |
| Schedule | Ant Design Form API unfamiliarity | Low | Low | 1. Review Ant Design docs first<br>2. Use existing form examples<br>3. Allocate buffer time |

---

## Phase 6: Effort Estimation

### Time Breakdown
- **Development:** 4-6 hours
  - Zustand store + persistence: 1 hour
  - API service layer: 1 hour
  - Login page UI: 1.5 hours
  - ProtectedRoute + routing: 1 hour
  - Axios interceptors: 1 hour
  - AuthLayout: 0.5 hours
- **Testing:** 2-3 hours
  - Unit tests: 1.5 hours
  - Integration tests: 1 hour
  - Manual browser testing: 0.5 hours
- **Documentation:** 0.5 hours
  - Update architecture docs
  - Add code comments
- **Review & Deployment:** 0.5 hours
  - Code review
  - Merge to main
- **Total Estimated Effort:** 7-10 hours (1-1.5 days)

### Prerequisites
- ✅ Backend authentication endpoints functional
- ✅ Frontend scaffolding complete
- ✅ Ant Design 6 installed
- ✅ TanStack Query configured
- ✅ Zustand installed
- ⚠️ Need to verify backend CORS configuration for credentials
- ⚠️ Need to verify backend token expiration time

### Dependencies
- Backend `/auth/login` endpoint must return JWT token
- Backend `/auth/me` endpoint must validate JWT and return user
- Frontend must handle CORS if backend on different domain

---

## Verification Plan

### Automated Tests

**Unit Tests:**
```bash
# Run from frontend directory
npm run test -- src/stores/useAuthStore.test.ts
npm run test -- src/components/ProtectedRoute.test.tsx
npm run test -- src/pages/Login.test.tsx
```

**Integration Tests:**
```bash
# Run all tests
npm run test
```

**Expected Coverage:**
- `useAuthStore`: 100%
- `ProtectedRoute`: 100%
- Login page: >80%

### Manual Verification

**Test Case 1: Successful Login Flow**
1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to `http://localhost:5173/users` (protected route)
4. Verify redirect to `/login`
5. Enter valid credentials (create test user if needed)
6. Submit form
7. Verify redirect to `/users`
8. Verify user info displayed in header/profile
9. **Expected:** Successful login, redirect to intended page

**Test Case 2: Invalid Credentials**
1. Navigate to `/login`
2. Enter invalid email/password
3. Submit form
4. **Expected:** Error message displayed, no redirect, form remains

**Test Case 3: Logout Flow**
1. Log in successfully
2. Click logout button (in header/profile menu)
3. **Expected:** Redirect to `/login`, token cleared, cannot access protected routes

**Test Case 4: Token Persistence**
1. Log in successfully
2. Refresh page (F5)
3. **Expected:** User remains authenticated, no redirect to login

**Test Case 5: Direct Protected Route Access**
1. Log out (or open incognito window)
2. Navigate directly to `http://localhost:5173/users`
3. **Expected:** Redirect to `/login?redirect=/users`
4. Log in
5. **Expected:** Redirect back to `/users`

**Test Case 6: 401 Response Handling**
1. Log in successfully
2. Manually expire token (or wait for expiration)
3. Make an API request (e.g., navigate to users page)
4. **Expected:** Automatic logout, redirect to login, error message

---

## Related Documentation

- [Frontend Core Architecture](file:///home/nicola/dev/backcast_evs/docs/02-architecture/frontend/contexts/01-core-architecture.md)
- [Frontend State Management](file:///home/nicola/dev/backcast_evs/docs/02-architecture/frontend/contexts/02-state-data.md)
- [Backend Authentication](file:///home/nicola/dev/backcast_evs/backend/app/api/routes/auth.py)
- [Sprint 2 Plan](file:///home/nicola/dev/backcast_evs/docs/03-project-plan/sprints/sprint-02.md)

---

## Approval

**Status:** ⏳ Awaiting Review  
**Reviewer:** TBD  
**Date Approved:** TBD

> [!IMPORTANT]
> **Human Decision Point**: Please review the implementation options and recommended approach. Approve to proceed to DO phase, or request changes to the plan.
