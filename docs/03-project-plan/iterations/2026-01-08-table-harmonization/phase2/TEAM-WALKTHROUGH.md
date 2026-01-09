# Team Walkthrough: Server-Side Filtering & Scalability

**Date:** 2026-01-08  
**Iteration:** Table Harmonization - Phase 2  
**Presenter:** AI Assistant / Lead Developer

---

## 1. Overview & Objectives

**Why did we change this?**

- Transition from client-side filtering (Phase 1) to server-side processing (Phase 2).
- Goal: Unlimited scalability, global search, and reduced client-side memory footprint.
- Success: All Project, WBE, and Cost Element tables now support true global search/filter/sort.

## 2. Core Patterns (Backend)

### 2.1 The FilterParser

Located in `backend/app/core/filtering.py`.

- Converts URL params like `filters=status:Active;branch:main` into SQLAlchemy expressions.
- Handles IN clauses: `status:Active,Draft`.
- Security: Forces field whitelisting (`allowed_fields`).

### 2.2 PaginatedResponse

Located in `backend/app/models/schemas/common.py`.

- Standard wrapper for list endpoints.
- `{ items, total, page, per_page }`.

### 2.3 Service Tuple Return

- Services now return `(items, total_count)`.
- Allows calculating the total record count once, then slicing the data.

## 3. Core Patterns (Frontend)

### 3.1 useProjects & unwrapResponse

- Hooks now handle the transition from array responses to object responses.
- `unwrapResponse` helper used to maintain compatibility with existing table data sinks.

### 3.2 Simplified Ant Design Tables

- Removed `sorter` functions and `onFilter` logic from components.
- Components now simply set `sorter: true` and pass the raw table state to the hook.

## 4. Security & Performance

- **Security**: Field whitelisting in `FilterParser` prevents leaking internal columns via filters.
- **Performance**: 5 new indexes added (`status`, `name`, `code`, `level`).

## 5. Live Demo

- Search for projects by name/code.
- Apply status filters.
- Sort by budget allocation.
- Observe consistent performance.

## 6. Q&A and Next Steps

- Transition Technical Debt (TD-003: E2E Tests).
- Standardizing the pattern for future entities.

---

**Related Assets:**

- [ADR-008](../../02-architecture/decisions/ADR-008-server-side-filtering.md)
- [API Response Patterns](../../02-architecture/cross-cutting/api-response-patterns.md)
- [Onboarding Guide](../../00-meta/onboarding.md)
