# E2E Smoke Test Guide - Query Key Factory Verification

**Created:** 2026-01-19
**Purpose:** Runtime verification of query key factory migration

---

## Overview

This document outlines manual smoke test scenarios to verify that the query key factory migration works correctly in runtime. These tests complement the automated E2E suite by providing quick manual verification of critical cache behaviors.

## Prerequisites

1. **Running Application Stack:**
   ```bash
   # Terminal 1: Backend
   cd backend
   uv run uvicorn app.main:app --reload

   # Terminal 2: Frontend
   cd frontend
   npm run dev

   # Terminal 3: Database (if not running)
   docker-compose up -d postgres
   ```

2. **Test Data:**
   - At least one project exists
   - User has appropriate permissions (project-create, cost-element-create, etc.)

3. **Browser DevTools:**
   - React Query DevTools enabled (press `Ctrl+Shift+Q` or `Cmd+Shift+Q`)
   - Browser Console open (for error monitoring)

---

## Test Scenarios

### Scenario 1: Cost Element CRUD with Cache Invalidation

**Objective:** Verify that component-level mutations use factory keys with proper Time Machine context.

**Steps:**

1. **Navigate to Cost Elements:**
   - Go to http://localhost:5173/cost-elements
   - Verify table loads successfully

2. **Create Cost Element:**
   - Click "Add Cost Element"
   - Fill in: Code=`SMOKE-001`, Name="Smoke Test", Budget="10000"
   - Click "Create"
   - **Verify:** Modal closes, new row appears in table

3. **Edit Cost Element:**
   - Find the row with code `SMOKE-001`
   - Click "Edit" button
   - Change Budget to "15000"
   - Click "Save"
   - **Verify:** Modal closes, budget updates in table WITHOUT page refresh
   - **Verify:** Budget Status (if visible) also updates automatically

4. **Check React Query DevTools:**
   - Open DevTools (`Ctrl+Shift+Q`)
   - Look for query keys matching pattern:
     - `['cost-elements', 'all']`
     - `['cost-elements', 'detail', id, { branch: 'main', asOf: ... }]`
   - **Verify:** No manual keys like `['cost_element', id]`

**Expected Result:** All mutations trigger cache invalidations using factory keys. No stale data after edits.

---

### Scenario 2: Time Machine Context Switching

**Objective:** Verify that Time Machine context switches use factory `all` keys to clear caches.

**Steps:**

1. **Start in Current View:**
   - Go to http://localhost:5173/cost-elements
   - Note the number of rows in the table

2. **Switch to Historical View:**
   - Click "Time Machine" button
   - Set "As Of Date" to "2024-01-01"
   - Click "Apply"
   - **Verify:** Table refreshes with different data (or empty if no old data)

3. **Check React Query DevTools:**
   - Look for invalidation events after clicking "Apply"
   - **Verify:** Queries invalidated using `queryKeys.projects.all`, `queryKeys.costElements.all`, etc.

4. **Switch Back to Current:**
   - Click "Time Machine" button
   - Clear "As Of Date"
   - Click "Apply"
   - **Verify:** Original data reappears

**Expected Result:** Context switches clear all relevant caches using factory `all` keys. No cross-context cache pollution.

---

### Scenario 3: Branch Isolation

**Objective:** Verify that query keys include branch context to prevent cache pollution.

**Steps:**

1. **Create in Main Branch:**
   - Ensure Time Machine shows Branch: "main"
   - Create cost element: Code=`BRANCH-001`, Budget="20000"
   - **Verify:** Element appears in table

2. **Switch to Feature Branch:**
   - Click "Time Machine"
   - Change Branch to "feature-branch" (or create one)
   - Click "Apply"
   - **Verify:** `BRANCH-001` does NOT appear in table

3. **Create in Feature Branch:**
   - Create cost element: Code=`BRANCH-002`, Budget="30000"
   - **Verify:** Only `BRANCH-002` appears, not `BRANCH-001`

4. **Switch Back to Main:**
   - Return to main branch
   - **Verify:** `BRANCH-001` appears, `BRANCH-002` does not

**Expected Result:** Branch context is properly included in query keys. No cache leakage between branches.

---

### Scenario 4: Dependent Query Invalidation

**Objective:** Verify that mutations invalidate dependent queries (e.g., cost element → forecast).

**Steps:**

1. **Create Cost Element with Forecast:**
   - Create cost element: Code=`DEP-001`, Budget="50000"
   - Go to Overview tab
   - Click "Forecasts" tab
   - Create forecast: EAC="45000"
   - **Verify:** Forecast appears, EVM metrics calculated

2. **Update Cost Element Budget:**
   - Go back to Overview tab
   - Edit cost element: Change Budget to "60000"
   - Click "Save"
   - **Verify:** Success toast appears

3. **Check Forecast Cache:**
   - Go to Forecasts tab
   - **Verify:** EVM metrics updated automatically (no manual refresh needed)
   - **Verify:** No console errors about stale data

**Expected Result:** Cost element mutations invalidate forecast queries. Dependent data stays consistent.

---

### Scenario 5: Login/Logout with Cache Clearing

**Objective:** Verify that authentication state changes clear user-specific caches.

**Steps:**

1. **Login:**
   - Go to http://localhost:5173/login
   - Enter credentials
   - Click "Login"
   - **Verify:** Redirected to dashboard, user data loads

2. **Check User Query:**
   - Open React Query DevTools
   - Look for `['users', 'me']` query key
   - **Verify:** Current user data cached

3. **Logout:**
   - Click "Logout" button
   - **Verify:** Redirected to login page

4. **Verify Cache Cleared:**
   - In DevTools, check that user queries are removed or stale
   - **Verify:** No sensitive user data remains in cache

**Expected Result:** Authentication changes clear user-specific caches using `queryKeys.users.me`.

---

## Automated E2E Test Execution

For automated testing, run the dedicated query key consistency test suite:

```bash
# Run all E2E tests
npm run e2e

# Run only query key consistency tests
npm run e2e -- query-key-consistency.spec.ts
```

**Test File:** `frontend/tests/e2e/query-key-consistency.spec.ts`

**Coverage:**
- Cache invalidation on mutations
- Time Machine context switching
- Branch isolation
- Dependent query invalidation
- Factory key pattern verification

---

## Verification Checklist

After completing smoke tests, verify the following:

- [ ] No stale data after mutations (edits, creates, deletes)
- [ ] Time Machine context switches refresh all relevant data
- [ ] Branch context prevents cross-branch cache pollution
- [ ] Dependent queries invalidate automatically
- [ ] No console errors related to query keys or cache
- [ ] React Query DevTools show factory key patterns (not manual arrays)
- [ ] Login/logout clears user-specific caches

---

## Common Issues and Solutions

### Issue: Stale Data After Mutation

**Symptom:** Data doesn't update after edit/create without page refresh.

**Possible Causes:**
1. Mutation callback not using factory keys
2. Missing Time Machine context in invalidation
3. Dependent queries not invalidated

**Solution:**
- Check mutation `onSuccess` callback
- Verify `queryKeys.{entity}.detail(id, { branch, asOf })` pattern
- Add dependent query invalidations (e.g., `queryKeys.forecasts.all`)

### Issue: Cache Pollution Between Branches

**Symptom:** Data from main branch appears in feature branch.

**Possible Causes:**
1. Query keys missing branch context
2. Using manual keys without context parameters

**Solution:**
- Ensure all versioned entity queries include `{ branch, asOf, mode }`
- Check query key factory has context parameters

### Issue: Time Machine Not Clearing Caches

**Symptom:** Switching "As Of" date shows old data.

**Possible Causes:**
1. Time Machine context not using `all` keys
2. Manual arrays in invalidation

**Solution:**
- Verify `queryKeys.{entity}.all` pattern in TimeMachineContext
- Check that all versioned entities are invalidated

---

## Success Criteria

Smoke testing is successful if:

1. **All scenarios pass** without manual page refresh
2. **Zero console errors** related to query keys or cache
3. **React Query DevTools** show factory key patterns
4. **No cache staleness** observed in any scenario
5. **Branch isolation** works correctly
6. **Time Machine context** properly clears caches

---

## Next Steps

After successful smoke testing:

1. **Document any issues** found during testing
2. **Create bug reports** for failures
3. **Update CHECK phase report** with test results
4. **Proceed to ACT phase** improvements

---

## References

- **Query Key Factory:** `frontend/src/api/queryKeys.ts`
- **Time Machine Context:** `frontend/src/contexts/TimeMachineContext.tsx`
- **E2E Test Suite:** `frontend/tests/e2e/`
- **State Management Architecture:** `docs/02-architecture/frontend/contexts/02-state-data.md`
