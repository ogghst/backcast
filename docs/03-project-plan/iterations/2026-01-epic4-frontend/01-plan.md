# PLAN Phase: Frontend Project/WBE Display (E04-U03)

**Date:** 2026-01-05  
**Iteration:** Epic 4 Frontend - Project & WBE Display  
**Status:** ✅ Approved

---

## Executive Summary

Epic 4 Foundation backend is complete. This iteration implements **read-only** frontend display for Project and WBE entities to validate backend APIs and provide stakeholder visibility.

**Scope:** List views AND CRUD forms (Create/Edit/Delete) plus integration tests.

---

## Problem Definition

### Problem Statement

Backend Project/WBE APIs ready but have no frontend interface, limiting visibility and testing.

**Why Important:**

- Validates backend implementation
- Unblocks stakeholder visibility
- Establishes patterns for remaining Epic 4 entities

**Business Value:** Immediate admin access to Project/WBE data

### Success Criteria

**Functional:**

- ✅ Admin can view Projects list (paginated)
- ✅ Admin can view WBEs for a Project
- ✅ RBAC enforced (`project-read`, `wbe-read`)
- ✅ Navigation menu includes "Projects"

**Technical:**

- ✅ TypeScript client auto-generated from OpenAPI
- ✅ Integration tests for list scenarios
- ✅ E2E test for admin navigation
- ✅ Zero TypeScript/ESLint errors
- ✅ Uses StandardTable + useCrud patterns

### Scope

**In Scope:**

- TypeScript API client generation
- `ProjectList.tsx`
- `WBEList.tsx`
- `ProjectModal.tsx` (Create/Edit)
- `WBEModal.tsx` (Create/Edit)
- Delete functionality
- Navigation menu integration
- Integration + E2E tests
- Documentation updates

**Out of Scope (Deferred):**

- Version history drawer (fetching logic)
- Branch filtering UI
- Cost Elements (E04-U04+)
- WBE tree view

---

## Implementation Approach

### Design Patterns

- **StandardTable** component for entity lists
- **useCrud** hook for API integration
- **RBAC <Can>** wrapper for permission checks
- **React Query** for data fetching/caching

### Components

**ProjectList.tsx:**

- List view with RBAC/Pagination
- Integrates `ProjectModal` for Create/Edit
- Implements Delete with confirmation

**ProjectModal.tsx:**

- Fields: Name, Code, Budget, Contract Value, Start/End Dates
- Validation: Required fields, date logic
- Pattern: AntD Modal + Form

**WBEList.tsx:**

- List view with Project filter
- Integrates `WBEModal` for Create/Edit
- Implements Delete with confirmation

**WBEModal.tsx:**

- Fields: Name, Code, Level, Budget Allocation, Parent WBE
- Pattern: AntD Modal + Form

**Navigation:**

- Add "Projects" menu item (icon: `ProjectOutlined`)
- Route: `/admin/projects`

### Test Strategy

**Integration Tests (Vitest + MSW):**

- ProjectList: renders table, pagination, loading/error states
- ProjectModal: validates inputs, submits data
- WBEList: renders WBEs for project, handles empty list
- WBEModal: validates inputs, submits data
- Delete: verifies confirmation dialog and API call

**E2E Tests (Playwright):**

- Admin navigates to Projects page
- Table displays data
- Admin can create a new Project
- Admin can edit an existing Project
- Admin can delete a Project
- Non-admin blocked by RBAC

**Manual Testing:**

- Browser verification of layout/UX

---

## Risk Assessment

| Risk                             | Probability | Impact | Mitigation                      |
| -------------------------------- | ----------- | ------ | ------------------------------- |
| API response format mismatch     | Low         | Medium | Use generated TypeScript client |
| RBAC permission strings mismatch | Low         | Medium | Follow existing patterns        |
| More complex than estimated      | Low         | Low    | Defer CRUD to future            |

**Risk Level:** Low (proven patterns)

---

## Effort Estimation

- **API Client Generation:** 0.5h (Complete)
- **ProjectList Component:** 2h (Complete)
- **WBEList Component:** 1.5h (Complete)
- **Navigation Integration:** 0.5h (Complete)
- **ProjectModal Component:** 2h
- **WBEModal Component:** 2h
- **Delete Logic:** 1h
- **Integration Tests:** 4h
- **E2E Tests:** 2h
- **Documentation:** 1h

**Total:** 2-3 days

---

## References

- [Epic 4 Backend Walkthrough](file:///home/nicola/.gemini/antigravity/brain/dd65f953-0a5b-4993-b8fb-9695385cde55/walkthrough.md)
- [EVCS Core Architecture](file:///home/nicola/dev/backcast_evs/docs/02-architecture/backend/contexts/evcs-core/architecture.md)
- [Admin UI Pattern KI](file:///home/nicola/.gemini/antigravity/knowledge/admin_ui_implementation_pattern/artifacts/overview.md)
