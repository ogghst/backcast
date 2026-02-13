# PLAN Phase: Frontend User History Testing

## Purpose

Implement integration testing for the User History feature in the frontend, verifying that the `VersionHistoryDrawer` correctly displays data fetched from the API, aligning with the recently fixed backend schema.

---

## Phase 1: Context Analysis

### Documentation Review

- **Architecture**: `ADR-004-quality-standards.md` requires "API tests for all endpoints" and "Integration tests". Frontend implementation uses Vitest + MSW.
- **Current Context**: Backend history endpoint now returns `list[UserHistory]` with `valid_time` ranges. Frontend `UserList` component has a "View History" button that triggers `VersionHistoryDrawer`.

### Codebase Analysis

- **Existing Tests**:
  - `Versioning.test.tsx`: Unit test for drawer (isolated).
  - `UserList.test.tsx`: Integration test for list (mocked API).
  - `src/mocks/handlers.ts`: Missing handler for `/api/v1/users/:id/history`.
- **Database Verification**:
  - Observed DB data confirms `valid_time` is stored as `TSTZRANGE` (e.g., `["2024-01-01...", "2024-02-01...")`).
  - API sends this as JSON array of ISO strings.

---

## Phase 2: Problem Definition

### 1. Problem Statement

The "View History" functionality in the user list is currently untested in integration tests. We need to ensure that when a user clicks the history button, the drawer opens and displays the correct historical data, preventing regressions in this critical audit feature.

### 2. Success Criteria

**Functional Criteria:**

- "View History" button is clickable.
- Drawer opens upon checking.
- Historical versions (from mock API) are displayed.
- Timestamps are formatted correctly.

**Technical Criteria:**

- Test passes in CI environment.
- MSW handler mimics production API schema exactly.

### 3. Scope

**In Scope:**

- Update `src/mocks/handlers.ts`
- Update `src/features/users/components/UserList.test.tsx`

**Out of Scope:**

- E2E testing with real backend (Selenium/Cypress).

---

## Phase 3: Implementation Options

### Option A: Extend `UserList.test.tsx` with MSW (Recommended)

Add a test case to the existing `UserList` integration test. Update default MSW handlers to serve history data.

- **Pros**: Reuses existing test setup, fast execution, tests integration of List + Drawer.
- **Cons**: Does not test real backend connection (handled by backend tests).

### Option B: New Isolated Test file

Create `UserHistoryIntegration.test.tsx`.

- **Pros**: Isolation.
- **Cons**: Duplicates setup code for QueryClient, Router, ConfigProvider.

### Recommendation

**Option A**. It's cleaner to test the User List interactions (including history) in the User List test suite.

---

## Phase 4: Technical Design

### Mock Data Structure

Matches Backend `UserHistory` schema:

```json
[
  {
    "full_name": "Version 2",
    "valid_time": ["2024-01-02T00:00:00Z", null],
    "transaction_time": ["2024-01-02T00:00:00Z", null]
  }
]
```

### Test Case Blueprint

1. Render `UserList`.
2. Wait for users to load.
3. Find "View History" button for "Alice Johnson".
4. Click button.
5. Wait for `VersionHistoryDrawer` (role `complementary` or by text "User: Alice Johnson").
6. Verify version items (e.g., check for date text or "Version 2").

---

## Phase 5: Risk Assessment

- **Risk**: Date formatting in test environment (timezone differences).
- **Mitigation**: Use fuzzy matching for dates or specific format mocks.

---

## Phase 6: Effort Estimation

- **Time**: 1 hour.
- **Steps**:
  1. Update `src/mocks/handlers.ts`.
  2. Write test in `UserList.test.tsx`.
  3. Run verification.
