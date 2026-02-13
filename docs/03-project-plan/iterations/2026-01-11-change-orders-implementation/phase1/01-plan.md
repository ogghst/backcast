# Phase 1: Change Order Creation & Auto-Branch Management - Plan

**Date Created:** 2026-01-11
**Epic:** E006 (Branching & Change Order Management)
**Phase:** 1 of 4 - Core CO Creation + Auto-Branch Generation
**Status:** Plan Phase
**Related Docs:**

- [Analysis](./00-analysis.md)
- [Change Management User Stories](../../../01-product-scope/change-management-user-stories.md)
- [Product Backlog](../../product-backlog.md)
- [Coding Standards](../../../02-architecture/coding-standards.md)
- [EVCS Architecture](../../../02-architecture/backend/contexts/evcs-core/architecture.md)

---

## Phase 1: Context Analysis

### Documentation Review

**Product Scope Alignment:**

This phase implements:

- **User Story 3.1:** Creation of a Change (and Branch Generation)
- **User Story 3.3:** Updating the Change Metadata (partial - CRUD operations)

Deferred to later phases:

- Story 3.2: Performing Work on a Change (Phase 2)
- Story 3.4: Impact Analysis (Phase 3)
- Story 3.5: Submitting the Change (Phase 2)
- Story 3.6: Accepting/Merging (Phase 4)
- Story 3.7: Rejecting/Deleting (Phase 2)
- Story 3.8: View Mode Toggle (Phase 2)

**UI/UX Requirements from Chapter 5:**

The implementation must incorporate:

1. **Header Branch Indicator** (5.4): Always visible, distinct styling for change branches
2. **Professional Color Palette** (5.3): State-based colors (Draft: #F59E0B Amber)
3. **Notifications** (5.4): Toaster confirmations for state changes (branch creation)
4. **Branch Selector Enhancement**: Visual indicators for change order branches (BR-* prefix)
5. **Time Machine Independence**: Date selector independent of branch selection

### Codebase Analysis

**Existing Patterns to Follow:**

| Pattern | Location | Application |
|---------|----------|-------------|
| Branchable Entity Model | `models/domain/project.py` | Use `BranchableMixin` for `ChangeOrderVersion` |
| Branchable Service | `core/branching/service.py` | Extend `BranchableService[T]` for CO operations |
| API Route Conventions | `api/routes/projects.py` | Same RBAC, response patterns, operation IDs |
| Pydantic Schemas | `models/schemas/project.py` | `ChangeOrderCreate`, `ChangeOrderUpdate`, `ChangeOrderPublic` |
| Frontend State | `stores/useTimeMachineStore.ts` | Extend for CO context |
| Branch Selector | `components/time-machine/BranchSelector.tsx` | Add CO status badges |

**Key Dependencies:**

- **Backend:** `BranchableService`, `CreateBranchCommand`, `TemporalService`
- **Frontend:** TanStack Query (React Query), Zustand, Ant Design
- **Database:** PostgreSQL TSTZRANGE for bitemporal tracking

**Test Infrastructure:**

- **Backend Fixtures:** `db_session`, `client` from `tests/conftest.py`
- **Frontend Tests:** Vitest + React Testing Library
- **E2E Tests:** Playwright (incremental testing per user requirement)

---

## Phase 2: Problem Definition

### 1. Problem Statement

**What:** Implement Change Order creation with automatic branch generation for isolated project modifications.

**Why:** Project Managers need a structured way to propose changes without affecting the production baseline. Currently, users can only modify data on the `main` branch, risking accidental changes to live project data.

**Business Value:**

- Enables formal change control workflows (PMI/PMBOK compliance)
- Provides audit trail for all proposed changes
- Isolates work-in-progress from production data
- Foundation for impact analysis and approval workflows

**If Not Addressed:**

- No change control governance
- Risk of accidental production data modification
- Inability to track change proposals
- No foundation for impact analysis

### 2. Success Criteria (Measurable)

**Functional Criteria:**

- [ ] PM can create CO with ID, title, description, justification, effective date
- [ ] System auto-creates branch `BR-{change_order_id}` on CO creation
- [ ] CO list displays with status badges (Draft color: #F59E0B)
- [ ] PM can update CO metadata (description, justification, effective date)
- [ ] PM can delete draft CO (soft delete + branch cleanup)
- [ ] Branch selector shows CO branches with visual distinction
- [ ] Switching to CO branch shows visual indicator (amber header)
- [ ] Time machine controls work independently of branch selection

**Technical Criteria:**

- [ ] API response time < 200ms for CO CRUD operations
- [ ] All endpoints protected with RBAC (`change-order-create`, `change-order-read`, etc.)
- [ ] Type safety: 100% coverage (MyPy strict mode, TypeScript strict mode)
- [ ] Test coverage ≥ 80% for new code
- [ ] Zero linting errors (Ruff, ESLint)
- [ ] Database migrations auto-applied in tests

**Business Criteria:**

- [ ] Change Orders are per-project (scoped by `project_id`)
- [ ] Full audit trail (created_by, created_at, updated_by, updated_at)
- [ ] Soft delete with recovery capability
- [ ] Branch names are unique and deterministic (`BR-{id}`)

### 3. Scope Definition

**In Scope:**

| Item | Description |
|------|-------------|
| **Backend Model** | `ChangeOrderVersion` with `BranchableMixin` |
| **Backend Service** | `ChangeOrderService` extending `BranchableService` |
| **Backend API** | `/api/v1/change-orders/` CRUD endpoints |
| **Database Migration** | `change_order_versions` table with indexes |
| **Frontend Types** | TypeScript interfaces matching Pydantic schemas |
| **Frontend Components** | `ChangeOrderList`, `ChangeOrderForm` (create/edit) |
| **Frontend Hooks** | `useChangeOrders` via `createResourceHooks` |
| **Frontend Routes** | `/change-orders`, `/change-orders/:id` |
| **Branch Integration** | Extend `BranchSelector` with CO status badges |
| **Header Indicator** | Amber color when in CO branch |
| **State Management** | Extend `useTimeMachineStore` for CO context |
| **Unit Tests** | Backend service tests, Frontend component tests |
| **E2E Tests** | Create CO, update CO, delete draft CO |
| **Documentation** | API docs (auto-generated), component docs |

**Out of Scope (Deferred):**

| Item | Deferred To Phase |
|------|-------------------|
| In-branch editing (WBEs, Cost Elements) | Phase 2 |
| Impact analysis dashboard | Phase 3 |
| Submit/Approve/Reject workflow | Phase 2/4 |
| Merge operations | Phase 4 |
| Branch locking | Phase 2 |
| View mode toggle (Isolated/Merged) | Phase 2 |
| Visual impact charts (waterfall, S-curves) | Phase 3 |

**Assumptions:**

1. User has confirmed parallel frontend/backend work is acceptable
2. Incremental E2E testing (test after each feature) is acceptable
3. Tabular + chart data comparison will be provided in Phase 3
4. Change management is per-project (confirmed)
5. EVCS Core (`BranchableService`, `CreateBranchCommand`) is stable

---

## Phase 3: Implementation Options

### Option A: Full-Stack Feature Approach (Recommended)

**Approach Summary:**
Implement complete Change Order entity with auto-branch creation, following existing patterns for Project/WBE entities. Frontend and backend developed in parallel with clear API contract.

**Design Patterns:**

- **Backend:** `BranchableProtocol` → `ChangeOrderVersion` model
- **Service:** Extend `BranchableService[ChangeOrderVersion]`
- **Command Pattern:** Use `CreateBranchCommand` for auto-branch creation
- **API:** Standard CRUD with RBAC dependencies
- **Frontend:** Feature-based organization (`features/change-orders/`)
- **State:** TanStack Query for server state, Zustand for UI state
- **Components:** Ant Design forms with status badges

**Component Structure:**

```
Backend:
├── app/models/domain/change_order.py          # ChangeOrderVersion model
├── app/models/schemas/change_order.py         # Pydantic schemas
├── app/services/change_order_service.py       # Business logic
├── app/api/routes/change_orders.py            # API endpoints
└── alembic/versions/xxx_create_change_orders.py # Migration

Frontend:
├── src/features/change-orders/
│   ├── components/
│   │   ├── ChangeOrderList.tsx               # List with status badges
│   │   ├── ChangeOrderForm.tsx               # Create/edit modal
│   │   └── ChangeOrderStatusBadge.tsx        # Status indicator (colored)
│   ├── hooks/
│   │   └── useChangeOrders.ts                # TanStack Query hooks
│   ├── types.ts                              # TypeScript interfaces
│   └── api/change-orders.ts                  # API service
├── src/components/time-machine/
│   └── BranchSelector.tsx                    # Extend with CO badges
└── src/stores/
    └── useTimeMachineStore.ts                # Extend for CO context
```

**Pros:**

- Follows established patterns (Project, WBE, CostElement)
- Type-safe end-to-end (Pydantic → TypeScript)
- Clear separation of concerns
- Easy to test in isolation
- Reuses existing infrastructure (RBAC, filtering, pagination)

**Cons:**

- Requires parallel frontend/backend coordination
- More initial code than minimal approach
- Needs API contract alignment

**Test Strategy Impact:**

- Unit tests for service layer (business logic)
- Integration tests for API endpoints
- Component tests for React components
- E2E tests for critical flows (create, update, delete)

**Risk Level:** Low
**Estimated Complexity:** Simple

---

### Option B: Backend-First MVP

**Approach Summary:**
Implement complete backend first, use generic UI (table + form) initially. Polish frontend in follow-up.

**Design Patterns:**

- Same backend patterns as Option A
- Frontend: Generic `StandardTable` with minimal customization
- No dedicated change order UI components initially

**Pros:**

- Faster backend validation
- Lower frontend development cost initially
- Can test API contracts immediately

**Cons:**

- Poor initial UX (no status badges, no branch indicators)
- Frontend debt to address later
- Doesn't meet Chapter 5 UI requirements

**Test Strategy Impact:**

- Full backend test coverage
- Minimal frontend testing
- API-focused E2E tests

**Risk Level:** Medium
**Estimated Complexity:** Simple

---

### Option C: Minimal Viable Change

**Approach Summary:**
Simplest implementation: CO as non-versioned entity, manual branch creation via API.

**Design Patterns:**

- Backend: `SimpleBase` for ChangeOrder (no versioning)
- Frontend: Basic CRUD only
- Branch creation: Separate API call

**Pros:**

- Fastest initial implementation
- Least code to write

**Cons:**

- Doesn't follow EVCS patterns (inconsistent architecture)
- No audit trail for CO itself
- Requires two API calls (create CO, create branch)
- Doesn't meet user story requirements (auto-branch)
- Technical debt immediately

**Test Strategy Impact:**

- Basic CRUD tests
- No versioning tests

**Risk Level:** High (architectural inconsistency)
**Estimated Complexity:** Simple

---

### Recommendation

**I recommend Option A: Full-Stack Feature Approach**

**Justification:**

1. **Pattern Consistency:** Change Orders are core to the EVCS architecture. Using `BranchableProtocol` ensures consistency with Projects, WBEs, and CostElements.

2. **UI/UX Requirements:** Chapter 5 specifies professional UI (status badges, colors, notifications). Option A delivers these from day one.

3. **Type Safety:** Full-stack approach ensures end-to-end type safety (Pydantic → TypeScript).

4. **Testability:** Clear component boundaries make testing straightforward.

5. **Parallel Work:** User confirmed parallel frontend/backend work is acceptable.

6. **Incremental Delivery:** E2E tests can be written incrementally as features complete.

7. **Low Risk:** Following established patterns reduces uncertainty.

**Approval Required:** Proceed with Option A?

---

## Phase 4: Technical Design

### TDD Test Blueprint

```
├── Unit Tests (isolated component behavior)
│   ├── Backend Service Layer
│   │   ├── test_change_order_create_success
│   │   ├── test_change_order_create_with_auto_branch
│   │   ├── test_change_order_update_metadata
│   │   ├── test_change_order_soft_delete
│   │   ├── test_change_order_get_by_project
│   │   ├── test_change_order_branch_already_exists
│   │   └── test_change_order_invalid_project_id
│   └── Frontend Components
│       ├── test_change_order_list_renders
│       ├── test_change_order_status_badge_colors
│       ├── test_change_order_form_validation
│       └── test_branch_selector_shows_co_branches
│
├── Integration Tests (component interactions)
│   ├── Database Integration
│   │   ├── test_change_order_crud_persists
│   │   ├── test_branch_created_on_co_creation
│   │   └── test_soft_delete_preserves_audit
│   └── API Integration
│       ├── test_create_change_order_endpoint
│       ├── test_list_change_orders_with_pagination
│       ├── test_update_change_order_endpoint
│       ├── test_delete_change_order_endpoint
│       └── test_rbac_permissions_enforced
│
└── End-to-End Tests (critical user flows)
    ├── test_pm_creates_change_order
    ├── test_pm_updates_change_order_metadata
    ├── test_pm_deletes_draft_change_order
    ├── test_user_switches_to_co_branch
    └── test_header_shows_amber_in_co_branch
```

### First 5 Test Cases (Simplest → Most Complex)

**1. `test_change_order_create_success`**

- **Given:** Valid project exists, authenticated PM user
- **When:** Create ChangeOrder with valid data
- **Then:** CO created with Draft status, correct project_id

**2. `test_change_order_create_with_auto_branch`**

- **Given:** Valid project exists
- **When:** Create ChangeOrder
- **Then:** Branch `BR-{id}` automatically created in database

**3. `test_change_order_list_renders`**

- **Given:** Multiple COs exist (different statuses)
- **When:** Navigate to `/change-orders`
- **Then:** Table shows all COs with correct status badges

**4. `test_create_change_order_endpoint`**

- **Given:** Valid project, authenticated user with permission
- **When:** POST `/api/v1/change-orders/`
- **Then:** Returns 201 with CO data, branch created

**5. `test_pm_creates_change_order` (E2E)**

- **Given:** User logged in as PM, on change orders page
- **When:** Click "Add Change Order", fill form, submit
- **Then:** CO appears in list, branch selector shows new branch

### Implementation Strategy

**High-Level Approach:**

1. **Backend First (Parallel Track 1):**
   - Create `ChangeOrderVersion` model with `BranchableMixin`
   - Generate database migration
   - Implement `ChangeOrderService` with auto-branch logic
   - Create API routes with RBAC
   - Write unit + integration tests

2. **Frontend Second (Parallel Track 2):**
   - Generate TypeScript types from OpenAPI spec
   - Create API service layer
   - Implement `useChangeOrders` hooks
   - Build `ChangeOrderList` and `ChangeOrderForm` components
   - Extend `BranchSelector` with CO status badges
   - Add header color change for CO branches
   - Write component tests

3. **Integration:**
   - Update routing configuration
   - Add navigation menu items
   - Wire up time machine store integration
   - Write E2E tests

**Key Technologies/Patterns:**

| Layer | Technology | Pattern |
|-------|-----------|---------|
| Model | SQLAlchemy 2.0 | `BranchableMixin` inheritance |
| Service | `BranchableService[T]` | Generic service extension |
| API | FastAPI | Dependency injection, RBAC |
| Database | PostgreSQL 15+ | TSTZRANGE for bitemporal |
| Frontend | React 18 + TypeScript | Feature-based organization |
| State | TanStack Query | Server state management |
| UI | Ant Design | Form components, badges |
| Testing | pytest, Vitest, Playwright | TDD approach |

**Integration Points:**

1. **Branching System:**
   - `ChangeOrderService` calls `CreateBranchCommand`
   - Branch name format: `BR-{change_order_id}`
   - Source branch: `main` (default) or specified CO

2. **Project Context:**
   - CO belongs to exactly one project (`project_id`)
   - Time machine store filters by current project

3. **RBAC:**
   - New permissions: `change-order-create`, `change-order-read`, `change-order-update`, `change-order-delete`
   - Role checks at API layer

4. **Frontend Routing:**
   - New route: `/projects/:projectId/change-orders`
   - Nested under project context

**Component Breakdown:**

| Component | Responsibility | Dependencies |
|-----------|----------------|--------------|
| `ChangeOrderVersion` | Database model | `BranchableMixin`, `VersionableMixin` |
| `ChangeOrderCreate/Update/Public` | Pydantic schemas | Base models |
| `ChangeOrderService` | Business logic | `BranchableService`, `CreateBranchCommand` |
| `change_orders` API | HTTP endpoints | `ChangeOrderService`, RBAC |
| `useChangeOrders` | Data fetching | TanStack Query, API client |
| `ChangeOrderList` | Table view | `StandardTable`, status badges |
| `ChangeOrderForm` | Create/edit | Ant Design Form |
| `ChangeOrderStatusBadge` | Visual indicator | Color by status |
| `BranchSelector` (extended) | Branch switching | CO branch indicators |

---

## Phase 5: Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
|-----------|-------------|-------------|--------|---------------------|
| **Technical** | Branch creation fails (race condition) | Low | Medium | Use database transaction, check for existing branch |
| **Technical** | Breaking changes in EVCS Core | Low | High | Pin to specific commit, write integration tests |
| **Schedule** | Frontend/backend API contract drift | Medium | Medium | Generate TypeScript from OpenAPI spec, validate in CI |
| **Integration** | Time machine store conflicts | Low | Low | Extend existing store, maintain backward compatibility |
| **Testing** | E2E test flakiness with async operations | Medium | Low | Use proper waiting strategies, test in isolation |
| **Requirements** | UI/UX Chapter 5 requirements unclear | Low | Low | Reference existing components (ProjectList), validate with PO |
| **Performance** | Branch selector slows with many COs | Low | Low | Implement pagination/debouncing (future) |

---

## Phase 6: Effort Estimation

### Time Breakdown

| Activity | Backend | Frontend | Testing | Total |
|----------|---------|----------|---------|-------|
| **Model & Migration** | 2h | - | 1h | 3h |
| **Service Layer** | 4h | - | 2h | 6h |
| **API Routes** | 3h | - | 2h | 5h |
| **Type Generation** | 0.5h | 0.5h | - | 1h |
| **API Service Layer** | - | 1h | 0.5h | 1.5h |
| **Hooks (useChangeOrders)** | - | 2h | 1h | 3h |
| **ChangeOrderList Component** | - | 3h | 1.5h | 4.5h |
| **ChangeOrderForm Component** | - | 3h | 1.5h | 4.5h |
| **StatusBadge Component** | - | 1h | 0.5h | 1.5h |
| **BranchSelector Extension** | - | 2h | 1h | 3h |
| **Header Color Indicator** | - | 1h | 0.5h | 1.5h |
| **Routing & Navigation** | - | 1h | 0.5h | 1.5h |
| **Integration & Polish** | 1h | 2h | 1h | 4h |
| **E2E Tests** | - | - | 3h | 3h |
| **Documentation** | 1h | 0.5h | - | 1.5h |
| **Buffer (20%)** | 3h | 3h | 2h | 8h |
| **Total** | **14.5h** | **20h** | **17.5h** | **52h** |

**Estimated Duration:** ~6.5 days (assuming 8h/day)

**With Parallel Work:**

- Backend-focused developer: ~3 days (14.5h + 3h buffer + support)
- Frontend-focused developer: ~3 days (20h + 3h buffer + support)
- Testing/QA: ~2 days (17.5h)
- **Calendar Time:** ~3-4 days (parallel execution)

### Prerequisites

**Before Starting:**

1. **Database:**
   - PostgreSQL 15+ running locally or via Docker
   - Alembic migrations up to date

2. **Backend:**
   - EVCS Core (`BranchableService`) verified stable
   - RBAC permissions added to database
   - Test database configured

3. **Frontend:**
   - Ant Design installed
   - TanStack Query configured
   - Routing structure updated

4. **Documentation:**
   - Update [Bounded Contexts](../../../02-architecture/01-bounded-contexts.md) with E006 changes
   - Update [API Response Patterns](../../../02-architecture/cross-cutting/api-response-evcs-implementation-guide.md)

**Infrastructure Needs:**

- Test user accounts (PM, Controller, Admin roles)
- Sample project data for E2E tests
- OpenAPI spec regeneration after API completion

---

## Definition of Done

**Phase 1 is complete when:**

- [ ] All acceptance criteria met
- [ ] Backend: MyPy strict mode passes, Ruff passes, pytest ≥80% coverage
- [ ] Frontend: TypeScript strict mode passes, ESLint passes, Vitest ≥80% coverage
- [ ] E2E: Playwright tests pass for create, update, delete flows
- [ ] API docs auto-generated and accessible at `/docs`
- [ ] Code reviewed and merged to main
- [ ] Documentation updated (ADR if needed)
- [ ] Demo: PM can create CO, see auto-branch, update metadata, delete draft

---

**Document Status:** Ready for Review
**Next Document:** `02-do.md` (after approval)
**Approval Required From:** Product Owner, Tech Lead
