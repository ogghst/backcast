# IT-FE-02: Testing Infrastructure - ACT

**Status:** ✅ Complete
**Date:** 2026-01-03

---

## 1. Prioritized Improvements

### Addressed in this Phase

- **Generated Code Brittleness:** User selected **Option B (Leave as Technical Debt)**.
  - **Action:** Verified via `npm run generate-client` followed by `npm test`.
  - **Result:** Tests passed. `src/features/users/api/userService.ts` is a manual wrapper file and is NOT overwritten by the generator. The manual fix is safe. No further action needed.

### Deferred Items

- **Test Console Noise:** "Not implemented: window.getComputedStyle". Low impact, deferred.

---

## 2. Pattern Standardization

**MSW (Mock Service Worker)**

- **Decision:** **Standardize**.
- **Usage:** All future integrations requiring backend data should use MSW handlers.
- **Action:** Updated `docs/02-architecture/frontend/contexts/04-quality-testing.md`.

**Storybook Decorators**

- **Decision:** **Standardize**.
- **Usage:** Use `.storybook/withProviders.tsx` pattern for checking component context requirements.

---

## 3. Documentation Updates

| Document                | Update                                            |
| ----------------------- | ------------------------------------------------- |
| `04-quality-testing.md` | Added MSW and Storybook testing strategy sections |
| `task.md`               | Marked iteration as complete                      |

---

## 4. Technical Debt Ledger

**New Debt:**

- **Item:** Generated Code / Wrapper discrepancy.
- **Description:** `src/features/users/api/userService.ts` manually patches the generated client response structure (pagination object vs array).
- **Risk:** If backend API changes structure significantly, this wrapper might break. It's not fully type-safe against the generated client's return type (uses `as unknown`).

---

## 5. Process Retrospective

**What Worked:**

- **Pilot Component:** Implementing `UserList` first validated the entire stack (MSW -> Store -> UI) before scaling.
- **MSW:** Proved its worth immediately by catching a data parsing bug.

**What Could Improve:**

- **Linting Config:** Generated files and build outputs (`storybook-static`) need to be aggressively excluded from linting to avoid noise.

---

## 6. Next Steps

- **IT-FE-03:** Begin planning for next iteration (likely feature implementation using this new infrastructure).
