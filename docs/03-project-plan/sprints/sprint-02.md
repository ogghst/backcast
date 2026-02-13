# Sprint 2: Core Infrastructure & User Management

**Goal:** Complete foundation and implement user management
**Status:** Completed
**Story Points:** 23
**Duration:** 2025-12-27 to 2026-01-05

**Stories:**
- [x] E02-U01: User CRUD with repository pattern, Pydantic schemas, comprehensive tests
- [x] E02-U02: Department CRUD
- [x] E02-U03: User roles and permissions management (RBAC)
- [x] E02-U04: Complete test coverage for all CRUD operations
- [x] E02-U05: Frontend User & Department Management (UI/UX) - **Admin Only**
- [x] E02-U06: Frontend Authentication (Login/Logout/Protect Routes)
- [ ] E02-U07: Frontend User Profile (View/Edit) - **Deferred to Sprint 3**

**Tasks:**
- [x] **S02-T01:** Implement User management endpoints (/users/*)
- [x] **S02-T02:** Implement Department management endpoints (/departments/*)
- [x] **S02-T03:** Achieve 80%+ test coverage
- [x] **S02-T04:** Ensure interactive API docs at /docs
- [x] **S02-T05:** Implement User & Department List/Edit/Create pages (**Protected: Admin Role Required**)
- [x] **S02-T06:** Integrate Authentication (JWT handling, Context)
- [ ] **S02-T07:** Build User Profile page with standard UI components - **Deferred**

**Deliverables:**
- User management endpoints (full CRUD with versioning, RBAC)
- Department management endpoints (full CRUD with versioning, RBAC)
- 80%+ test coverage (integration tests + E2E tests)
- Interactive API docs at /docs
- Frontend Admin UI for User & Department management
- RBAC system with `<Can>` component
- E2E tests for admin workflows

**Status Details:**
- Story 2.1 complete (User Management)
- Story 2.2 complete (Departments)
- Story 2.3 complete (RBAC implementation)
- Story 2.4 complete (Test coverage achieved)
- Frontend Stories (2.5, 2.6) complete - Admin UI implemented
- Story 2.7 deferred (User Profile)

**Epic 4 Foundation Completed (Bonus):**
- Project entity with full EVCS support (temporal versioning)
- WBE entity with Project parent-child relationship
- 14 new API endpoints (8 for Project, 6 for WBE)
- 16 integration tests (8 per entity)
- Database migrations applied

**Documentation:**
- See [Epic 4 Foundation - CHECK Phase](../../iterations/2026-01-epic4-foundation/03-check.md)
- See [Hybrid Sprint 2/3 - DO Phase](../../iterations/2026-01-hybrid-sprint2-3/02-do.md)
