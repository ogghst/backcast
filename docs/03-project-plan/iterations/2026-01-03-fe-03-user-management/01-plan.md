# PLAN Phase: Frontend User Management (Admin)

**Iteration:** IT-FE-03
**Date:** 2026-01-03
**Status:** DRAFT

---

## Phase 1: Context Analysis

### Documentation Review

- **Epic 2 (Core Entity Management):** E02-U01 "User CRUD" is the primary driver. Backend is complete.
- **Current Iteration:** Frontend Authentication is verified. Admin User Management is the next blocked step.
- **Architecture:** We established MSW and Storybook in `IT-FE-02`. This iteration MUST use them.
- **Codebase:** `src/features/users/components/UserList.tsx` exists as a pilot but is likely incomplete/needs polish for full CRUD.

### Codebase Analysis

- `UserList.tsx`: Currently displays users.
- `src/api/generated`: Contains full `UsersService` (CRUD).
- `src/stores/useUserStore`: Implements fetch, create, update, delete.
- **Gap:** Edit functionality, granular error handling, form validation for Create/Update, and granular permissions checks (UI level) are likely missing or basic.

---

## Phase 2: Problem Definition

### 1. Problem Statement

**Problem:** Admins cannot fully manage users (Create, Edit, Delete) through the UI. While a basic list exists, full lifecycle management is missing.
**Importance:** Essential for on-boarding users and managing access.
**Value:** Self-service for admins, removing need for database/backend scripts.

### 2. Success Criteria (Measurable)

**Functional Criteria:**

- [ ] Admin can view paginated list of users.
- [ ] Admin can Create a new user (email, name, role).
- [ ] Admin can Edit an existing user (name, role, active status).
- [ ] Admin can Delete (or Deactivate) a user.
- [ ] Non-admins cannot access this page.

**Technical Criteria:**

- [ ] All API interactions mocked in MSW and tested in Storybook.
- [ ] Integration tests covering full CRUD flow (using `renderWithProviders`).
- [ ] 100% Type safety with generated API types.
- [ ] No manual store mocks (use Real Store + MSW).

### 3. Scope Definition

**In Scope:**

- `UserList` component (Enhanced).
- `UserForm` component (Create/Edit shared).
- Storybook stories for all states (List, Form, Loading, Errors).
- Integration tests.

**Out of Scope:**

- User Profile (Self-edit) - Separate story.
- Department Management - Separate story.

---

## Phase 3: Implementation Options

| Aspect       | Option A: Monolithic Component                            | Option B: Componentized (Recommended)                               |
| ------------ | --------------------------------------------------------- | ------------------------------------------------------------------- |
| **Approach** | Keep everything in `UserList.tsx` (Table + Modal + Form). | Separate `UserList`, `UserManagementTable`, and `UserFormModal`.    |
| **Pros**     | Faster initial write.                                     | Better testability, reusable form logic, cleaner Storybook entries. |
| **Cons**     | Hard to test Form logic in isolation. Huge file.          | More boilerplate files.                                             |
| **Testing**  | 1 large test file.                                        | Targeted tests for Form validation vs Table behaviors.              |
| **Rec**      |                                                           | **YES**                                                             |

**Justification for Option B:**
Separating the Form logic allows us to unit test validation rules (Password complexity, email format) in isolation without rendering the whole table. It also makes Storybook clearer.

---

## Phase 4: Technical Design

### TDD Test Blueprint

```
src/features/users/
├── components/
│   ├── UserList.test.tsx (Integration: Page load, permission check)
│   ├── UserTable.test.tsx (Component: Sort, Filter, Delete action)
│   └── UserForm.test.tsx (Component: Validation, parsing, submit)
```

**Test Cases (Ordered):**

1.  `UserForm`: Validates required fields (Client-side).
2.  `UserForm`: Calls `onSubmit` with formatted data.
3.  `UserTable`: Renders list from Props.
4.  `UserList`: Fetches data from API (MSW) and passes to Table.
5.  `UserList`: Handles "Create Success" by refreshing list.

### Implementation Strategy

1.  **Refactor:** Extract `UserForm` from `UserModal` (or `UserList` if embedded).
2.  **Enhance:** Add "Edit" mode to Form (pre-fill data).
3.  **Store:** Ensure `updateUser` handling in `useUserStore` is robust.
4.  **UI:** Use Antd `ProTable` (if available/decided) or standard `Table` with pagination. _Note: We reverted ProTable in previous sprint 2.1, so we stick to Standard Table._
5.  **Storybook:** Create `UserForm.stories.tsx` (Create vs Edit modes).

---

## Phase 5: Risk Assessment

| Risk Type | Description                                     | Mitigation                                                      |
| --------- | ----------------------------------------------- | --------------------------------------------------------------- |
| Technical | `UserService` wrapper fragility (from IT-FE-02) | Ensure integration tests cover pagination edge cases.           |
| UX        | Error handling for duplicate emails             | Implement field-level error mapping from backend 400 responses. |

---

## Phase 6: Effort Estimation

### Time Breakdown

- **Development:** 0.5 days
- **Testing (Stories + Vitest):** 0.5 days
- **Review:** 0.2 days
- **Total:** ~1.5 days

### Prerequisites

- `IT-FE-02` infrastructure (Done).
