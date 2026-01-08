# ACT: Frontend Table Harmonization - Phase 1

**Iteration:** 2026-01-08-table-harmonization  
**Phase:** 3 of 3 (Act Phase)  
**Status:** ✅ Complete  
**Date:** 2026-01-08

---

## 1. Summary

In this iteration, we successfully harmonized the frontend table experience across 6 core components. By standardizing on `StandardTable` and `useTableParams`, we introduced consistent Global Search, Per-Column Text Filtering, and URL State Synchronization.

This work significantly improves the user experience by allowing deep-linking to filtered views and providing familiar interaction patterns across the application.

## 2. Improvements & Standardization

### Pattern Adoption

- **Artifact:** `docs/02-architecture/frontend/ui-patterns.md` created.
- **Standard:** All future list views **MUST** use `StandardTable` and `useTableParams`.
- **Search:** Global search is now a standard feature, not an optional add-on.

### Developer Experience

- New entities can be scaffolded with search/filter capabilities in minutes by copying the `getColumnSearchProps` pattern and connecting `useTableParams`.
- Strict typing prevents common bugs related to `any` usage in table columns.

## 3. Future Considerations (Phase 2)

While the current Client-Side Filtering approach provides excellent responsiveness for current data volumes, we must prepare for scale.

- **Server-Side Filtering:** As datasets grow >1000 records, we will need to implement backend support for flexible filtering (e.g., generic RSQL or specific query params).
- **Migration Path:** The frontend is architected to support this transition seamlessly. The `useTableParams` hook already serializes state correctly; the next step would be connecting this state to API calls instead of local `useMemo` logic.

## 4. Retrospective

### What Went Well

- Refactoring `StandardTable` to be generic paid off immediately, allowing rapid adoption across components.
- Early focus on URL state synchronization ensured a robust user experience (back button works!).

### What Could Be Better

- **E2E Test Flakiness:** Adding search introduced timing variability (debounce vs. test typing speed). Future tests should rely more on explicit state waits (e.g., wait for "loading" spinner to vanish) rather than fixed timeouts.
- **Strict Mode:** Playwright's strict mode required some adjustments to our locators. We should adopt unique `data-testid` attributes for key interaction elements to avoid ambiguity.

## 5. Closing

This iteration is complete. The codebase is cleaner, consistent, and more capable.

**Next Priority:** [Check Backlog] - Likely focusing on Phase 2 (Server-Side) or moving to a new feature set.
