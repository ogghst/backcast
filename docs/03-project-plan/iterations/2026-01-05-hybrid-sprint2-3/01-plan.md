# PLAN: Hybrid Sprint 2/3 Implementation

**Iteration:** Sprint 2 Closure + Sprint 3 Foundation  
**Created:** 2026-01-05  
**Status:** ✅ Approved  
**Approach:** Hybrid - Complete Sprint 2 Frontend Admin UI (Days 1-2), then start Epic 4 with EVCS Core (Days 3-7)

---

## Executive Summary

This iteration delivers two critical outcomes:

1. **Phase 1 (Days 1-2):** Complete Sprint 2 by implementing Frontend Admin UI for User and Department Management
2. **Phase 2 (Days 3-7):** Start Epic 4 by implementing Project and WBE entities using EVCS Core architecture from Day 1

**Strategic Value:**

- Closes Sprint 2 cleanly with full admin workflow capabilities
- Validates EVCS Core Protocol-based architecture with hierarchical entities before Epic 5
- Unblocks Epic 5 (Financial Data) and Epic 6 (Change Orders) - the core EVM features

---

## Problem Statement

**What:** Complete deferred Sprint 2 frontend work and begin Epic 4 foundation

**Why Important:**

- Sprint 2 has API complete but UI incomplete
- Epic 4 (Projects/WBEs) is critical path for MVP
- EVCS Core needs validation with hierarchical entities

**Business Value:**

- Admin workflows for user/department management
- Foundation for EVM core business logic
- Architectural validation reduces Epic 5 risk

---

## Success Criteria

### Phase 1: Frontend Admin UI

**Functional:**

- ✅ Admin users can CRUD users via UI
- ✅ Admin users can CRUD departments via UI
- ✅ RBAC prevents non-admin access

**Technical:**

- ✅ All frontend tests passing
- ✅ Coverage ≥ 80% for new code
- ✅ 0 linting/TypeScript errors

### Phase 2: Epic 4 Foundation

**Functional:**

- ✅ Project entity with CRUD + versioning + branching
- ✅ WBE entity with parent-child versioning
- ✅ Time-travel queries work
- ✅ Soft delete cascades from Project to WBEs

**Technical:**

- ✅ All backend tests passing
- ✅ Coverage ≥ 80%
- ✅ MyPy strict mode passes
- ✅ Database migrations apply cleanly

---

## Scope

### In Scope

**Phase 1:**

- UserManagement.tsx page (table + form)
- DepartmentManagement.tsx page (table + form)
- Navigation menu items (admin-only)
- Integration + E2E tests
- Sprint 2 closure documentation

**Phase 2:**

- ProjectVersion model (EntityBase + VersionableMixin + BranchableMixin)
- WBEVersion model (with project_id foreign key)
- Repositories, Services, Commands
- API endpoints (admin-only)
- Comprehensive tests (unit + integration)
- Basic frontend read-only display

### Out of Scope

- User profile self-service editing
- Cost Elements (Epic 4 U03)
- Full Project/WBE CRUD UI (deferred to Sprint 4)
- User/Department migration to EVCS Core

---

## Implementation Approach

### Phase 1: Frontend Admin UI (Days 1-2)

**Approach:** Follow established patterns from existing User features

**Key Technologies:**

- React 18 + TypeScript
- Ant Design (Table, Form, Modal)
- React Query
- `useCrud` hook pattern
- `<Can>` RBAC component

**Integration Points:**

- UsersService, DepartmentsService (existing API clients)
- useAuth hook for role checking
- MSW handlers for testing

### Phase 2: Epic 4 Backend (Days 3-7)

**Approach:** **Option A - EVCS Core from Day 1** ✅ APPROVED

Implement Project/WBE using Protocol-based EVCS Core immediately rather than legacy patterns.

**Rationale:**

- Validates architecture early
- No future migration cost
- Tests EVCS Core with hierarchical entities
- Documentation exists in ADR-005/ADR-006

**Key Technologies:**

- SQLAlchemy 2.0 (async ORM)
- PostgreSQL with GIST indexes
- Alembic migrations
- FastAPI + Pydantic v2

**Integration Points:**

- EntityBase + VersionableMixin + BranchableMixin
- BranchableService pattern
- Existing RBAC decorators
- Existing test fixtures

---

## Test Strategy

### Phase 1: Frontend

```
Frontend User Management
├── Integration Tests (Vitest)
│   ├── UserManagement.test.tsx (table rendering, CRUD actions, RBAC)
│   └── UserForm.test.tsx (validation, error handling)
└── E2E Tests (Playwright)
    └── admin_user_management.spec.ts (full user CRUD flow)

Frontend Department Management
├── Integration Tests (Vitest)
│   ├── DepartmentManagement.test.tsx
│   └── DepartmentForm.test.tsx
└── E2E Tests (Playwright)
    └── admin_department_management.spec.ts
```

### Phase 2: Backend

```
Project Entity
├── Unit Tests
│   ├── test_project_model.py (Protocol satisfaction, clone, soft_delete)
│   ├── test_project_commands.py (Create, Update, Branch, Merge)
│   └── test_project_repository.py (find_current, find_by_branch, find_at_time)
├── Integration Tests
│   ├── test_project_service.py (end-to-end service operations)
│   └── test_project_api.py (REST API endpoints)

WBE Entity
├── Unit Tests
│   ├── test_wbe_model.py (Protocol, foreign key, clone)
│   └── test_wbe_commands.py (CRUD with parent context)
└── Integration Tests
    ├── test_wbe_repository.py (parent-child versioning, cascade)
    └── test_wbe_service.py (cascade delete, branch inheritance)
```

---

## Risk Assessment

| Risk                                   | Probability | Impact | Mitigation                                   |
| -------------------------------------- | ----------- | ------ | -------------------------------------------- |
| EVCS Core gaps discovered              | Medium      | High   | Incremental implementation, unit tests first |
| Parent-child versioning complexity     | Medium      | High   | Research spike, create test cases first      |
| Phase 1 extends beyond 2 days          | Low         | Low    | Established patterns reduce risk             |
| Cascade delete breaks EVCS assumptions | Medium      | High   | Design cascade strategy upfront, test early  |

---

## Effort Estimation

**Phase 1:** 2 days (16 hours)

- Development: 10h
- Testing: 4h
- Documentation: 2h

**Phase 2:** 5 days (40 hours)

- Development: 24h
- Testing: 8h
- Migrations: 2h
- Documentation: 4h
- Buffer: 2h

**Total:** 7 days

---

## Prerequisites

**Phase 1:**

- ✅ Backend User/Department API complete
- ✅ OpenAPI TypeScript client generated
- ✅ RBAC `<Can>` component exists
- ✅ useCrud hook pattern established

**Phase 2:**

- ✅ EVCS Core architecture documented
- ✅ Database migrations infrastructure (Alembic)
- ✅ Test infrastructure (pytest, fixtures)
- ⚠️ **Need:** Review parent-child versioning patterns
- ⚠️ **Need:** Design cascade delete strategy

---

## Verification Plan

### Automated Tests

**Phase 1:**

```bash
npm run test -- src/pages/admin/
npm run test:coverage
npx playwright test tests/e2e/admin_*.spec.ts
npm run lint
```

**Phase 2:**

```bash
pytest tests/unit/models/test_project.py -v
pytest tests/integration/services/test_project_service.py -v
pytest --cov=app/models/project --cov-report=term-missing
mypy app/models/project.py --strict
ruff check app/models/project.py
alembic upgrade head
```

### Manual Verification

**Phase 1:**

- Admin can CRUD users/departments via UI
- Non-admin users blocked from admin pages
- Responsive layout works on different screen sizes

**Phase 2:**

- Project versioning creates immutable history
- Branching creates isolated copies
- Parent-child relationship maintained across versions
- Cascade delete works correctly

---

## Related Documentation

- [ADR-005: Bitemporal Versioning](file:///home/nicola/dev/backcast_evs/docs/02-architecture/decisions/ADR-005-bitemporal-versioning.md)
- [ADR-006: Protocol-Based Type System](file:///home/nicola/dev/backcast_evs/docs/02-architecture/decisions/ADR-006-protocol-evcs-types.md)
- [EVCS Core Architecture](file:///home/nicola/dev/backcast_evs/docs/02-architecture/backend/contexts/evcs-core/architecture.md)
- [Functional Requirements](file:///home/nicola/dev/backcast_evs/docs/01-product-scope/functional-requirements.md)
- [Current Iteration Status](file:///home/nicola/dev/backcast_evs/docs/03-project-plan/current-iteration.md)

---

## Approval

**Status:** ✅ Approved  
**Approver:** User  
**Date:** 2026-01-05  
**Approved Approach:** Option A (EVCS Core from Day 1) for Phase 2
