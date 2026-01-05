# ACT Phase: Project/WBE Implementation Closure

**Date:** 2026-01-06
**Iteration:** Epic 4 Frontend - Project & WBE Display

---

## 1. Implemented Improvements (Option B)

Based on the CHECK phase findings, we implemented the following high-priority improvements:

- **Type Safety Refactoring:**

  - Updated `useTableParams` to support generics (`<T>`).
  - Updated `StandardTable`, `ProjectList`, `WBEList`, and `UserList` to use the strict types.
  - **Result:** Removed fragile `as any` casting and `eslint-disable` directives for table change handlers.

- **E2E Testing:**
  - Created `frontend/tests/e2e/projects_crud.spec.ts` using Playwright.
  - **coverage:** Full CRUD flow (Create, Read, Delete) requiring real backend interaction.

---

## 2. Standardization & Patterns

We have formalized the following patterns for future frontend development:

### A. The "Standard List" Pattern

| Component             | Usage                                                |
| --------------------- | ---------------------------------------------------- |
| `StandardTable<T>`    | Shared table UI with pagination/filtering.           |
| `useTableParams<T>`   | URL-synced state management (Type-safe).             |
| `createResourceHooks` | Standardized React Query hooks for API CRUD.         |
| Path Structure        | `src/pages/<entity>/<Entity>List.tsx` (User-facing). |

### B. Testing Strategy

- **Integration (Vitest):** Use `msw` for API and **Mock Ant Design** (`App`, `Modal`) to avoid JSDOM render issues. Verification focus: Component logic & wiring.
- **E2E (Playwright):** Use for critical paths involving complex UI interactions (Modals, Popconfirms) and Backend integration.

---

## 3. Documentation Updates

- **Walkthrough:** updated to include new file paths and testing instructions.
- **Task List:** All tasks marked complete.
- **Project Structure:** Files moved from `admin/` to `projects/` and `wbes/`.

---

## 4. Retrospective

**Successes:**

- **Velocity:** Successfully expanded scope to include full CRUD and Tests within the iteration.
- **Quality:** Addressed technical debt (types) immediately in Act phase rather than deferring.
- **Responsiveness:** Quickly fixed Backend RBAC bug (403) discovered during manual checks.

**Learnings:**

- **Ant Design Testing:** Explicitly mocking `antd` module is more reliable than trying to make JSDOM render complex interacting components like `App.useApp` modals.
- **Generics:** spending time on strict generics for reusable components (`StandardTable`) pays off in developer experience immediately.

---

## 5. Next Steps

- **Merge:** This feature branch is ready for merge.
- **Next Iteration:** Begin work on **Cost Elements** or **Timesheet Entry** (Epic 5).
