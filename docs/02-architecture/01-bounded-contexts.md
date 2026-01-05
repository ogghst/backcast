# Bounded Contexts

**Last Updated:** 2026-01-05

This document defines the bounded contexts used to partition the Backcast EVS system. Each context represents a cohesive functional area with clear boundaries.

## Backend Contexts

### 0. EVCS Core (Entity Versioning Control System)

**Responsibility:** Bitemporal versioning framework, branching, soft delete, time-travel
**Owner:** Backend Team
**Documentation:** [backend/contexts/evcs-core/](backend/contexts/evcs-core/)
**ADR:** [ADR-005: Bitemporal Versioning](decisions/ADR-005-bitemporal-versioning.md)

> [!NOTE]
>
> - **Versioned entities** (Project, WBE, CostElement) inherit from `TemporalBase`
> - **Non-versioned entities** (UserPreferences, SystemConfig) inherit from `SimpleBase`

**Key Files:**

- `app/core/versioning/temporal.py` - `TemporalBase`, `TemporalService[T]`
- `app/core/versioning/commands.py` - Generic Create/Update/Delete commands
- `app/core/versioning/simple.py` - `SimpleBase`, `SimpleService` for standard CRUD

---

### 1. Authentication & Authorization

**Responsibility:** User identity verification, JWT token management, role-based access control (RBAC)
**Owner:** Backend Team
**Documentation:** [backend/contexts/auth/](backend/contexts/auth/)
**ADR:** [ADR-007: RBAC Service](decisions/ADR-007-rbac-service.md)

**Key Files:**

- `app/core/security.py` - JWT handling, password hashing (Argon2)
- `app/api/v1/auth.py` - Login endpoint, token refresh
- `app/services/rbac.py` - Permission checking, role enforcement

---

### 2. User Management

**Responsibility:** User CRUD operations, profile management, admin user creation, user history
**Owner:** Backend Team
**Versioning:** Not versioned (standard CRUD)
**Documentation:** [backend/contexts/user-management/](backend/contexts/user-management/)

**Key Files:**

- `app/models/user.py` - User model, Role enum
- `app/services/user.py` - UserService, user history tracking
- `app/api/v1/users.py` - User endpoints, RBAC enforcement

---

### Planned (Not Yet Documented)

The following contexts are planned but do not yet have dedicated documentation:

#### 3. Department Management

**Responsibility:** Department CRUD operations for budget tracking
**Owner:** Backend Team

#### 4. Project & WBE Management

**Responsibility:** Project hierarchy, Work Breakdown Elements (machines), revenue allocation
**Owner:** Backend Team
**Versioning:** Bitemporal with branching (via EVCS Core)

#### 5. Cost Element & Financial Tracking

**Responsibility:** Departmental budgets, cost registration, forecasts, earned value tracking
**Owner:** Backend Team
**Versioning:** Bitemporal with branching (via EVCS Core)

#### 6. Change Order Processing

**Responsibility:** Branch creation, modification, comparison, merging
**Owner:** Backend Team

#### 7. EVM Calculations & Reporting

**Responsibility:** Planned Value, Earned Value, Actual Cost, performance indices, variance analysis
**Owner:** Backend Team

---

## Frontend Contexts

### F0. Core Architecture

**Responsibility:** Application shell, routing strategy, foundational patterns
**Owner:** Frontend Team
**Documentation:** [frontend/contexts/01-core-architecture.md](frontend/contexts/01-core-architecture.md)

**Key Files:**

- `frontend/src/main.tsx` - App shell with providers (QueryClient, ConfigProvider, Router)
- `frontend/src/routes/` - Centralized route definitions, lazy loading
- `frontend/src/layouts/` - Layout components (AppLayout, AuthLayout)
- `frontend/src/config/` - Environment variables, static configuration

---

### F1. State & Data Management

**Responsibility:** Server state caching, client state, API layer, data fetching
**Owner:** Frontend Team
**Documentation:** [frontend/contexts/02-state-data.md](frontend/contexts/02-state-data.md)

**Key Files:**

- `frontend/src/api/client.ts` - Axios instance with auth interceptors
- `frontend/src/stores/` - Zustand stores (useAuthStore, UI state)
- `frontend/src/api/generated/` - OpenAPI-generated types and client
- `frontend/src/hooks/` - Custom hooks for data fetching

---

### F2. Authentication & Authorization

**Responsibility:** JWT token management, permission checks, protected routes, auth state
**Owner:** Frontend Team
**Documentation:** [frontend/contexts/06-authentication.md](frontend/contexts/06-authentication.md)

**Key Files:**

- `frontend/src/stores/authStore.ts` - Zustand auth state (token, user, permissions)
- `frontend/src/hooks/usePermission.ts` - Permission checking hook
- `frontend/src/components/permissions/Can.tsx` - Declarative `<Can>` component
- `frontend/src/api/auth.ts` - Auth API calls (login, refresh)

---

### F3. UI/UX

**Responsibility:** Component library integration, theming, styling patterns
**Owner:** Frontend Team
**Documentation:** [frontend/contexts/03-ui-ux.md](frontend/contexts/03-ui-ux.md)

**Key Files:**

- `frontend/src/components/` - Reusable UI components
- `frontend/src/i18n/` - Internationalization (i18next)

---

### F4. Quality & Testing

**Responsibility:** Testing strategy, linting, type checking, coverage standards
**Owner:** Frontend Team
**Documentation:** [frontend/contexts/04-quality-testing.md](frontend/contexts/04-quality-testing.md)

**Key Files:**

- `frontend/tests/` - Vitest unit tests, Playwright E2E tests
- `frontend/src/mocks/` - MSW API mocks
- `frontend/eslint.config.js` - ESLint configuration
- `frontend/tsconfig.json` - TypeScript strict mode

---

### F5. User Management (Feature)

**Responsibility:** User CRUD, user list, user forms, RBAC UI
**Owner:** Frontend Team
**Documentation:** [frontend/src/features/users/](frontend/src/features/users/)

**Key Files:**

- `frontend/src/features/users/components/` - UserList, UserForm, DeleteButton
- `frontend/src/features/users/api/` - User API hooks (useUsers, useUpdateUser)

---

## Cross-Cutting Concerns

### CC1. API Layer

**Responsibility:** REST conventions, request/response format, error handling, OpenAPI docs
**Documentation:** [cross-cutting/api-conventions.md](cross-cutting/api-conventions.md)

**Key Files:**

- `backend/app/api/dependencies.py` - Common dependencies (auth, RBAC)
- `backend/app/api/routes/` - API route definitions (auth, users, departments)
- `backend/app/main.py` - FastAPI app, CORS, middleware

---

### CC2. Database

**Responsibility:** Connection pooling, migrations, indexing strategy, bitemporal queries
**Documentation:** [cross-cutting/database-strategy.md](cross-cutting/database-strategy.md)

**Key Files:**

- `backend/app/db/session.py` - AsyncSession factory, connection pooling
- `backend/alembic/` - Database migrations
- `backend/app/core/versioning/` - Temporal base classes, range queries

---

### CC3. Security

**Responsibility:** Authentication, authorization, CORS, password hashing, JWT handling
**Documentation:** [cross-cutting/security-practices.md](cross-cutting/security-practices.md)

**Key Files:**

- `backend/app/core/security.py` - JWT handling, password hashing (Argon2)
- `backend/app/services/rbac.py` - Role-based access control
- `frontend/src/api/client.ts` - Token injection in requests

---

## Context Interaction Rules

### Backend Interactions

1. **EVCS Core** provides the versioning framework used by all versioned entities
2. **Authentication** is used by all contexts for identifying current user
3. **User Management** provides user data for audit trails in all versioned entities
4. **Project/WBE** hierarchy contains **Cost Elements** (planned)
5. **Financial Tracking** operates on **Cost Elements** (planned)
6. **Change Orders** create branches via EVCS Core affecting **Project/WBE/Cost Elements** (planned)
7. **EVM Calculations** read from **Financial Tracking** data with time-travel support (planned)

### Frontend Interactions

1. **Core Architecture (F0)** provides app shell and routing for all features
2. **State & Data (F1)** manages API caching and data fetching for all features
3. **Authentication (F2)** provides auth state and permission checks for all protected UI
4. **Features (F5+)** use components and patterns from Core, State, and Auth contexts

### Cross-Cutting Interactions

1. **API Layer (CC1)** conventions are followed by all backend API routes
2. **Database (CC2)** strategy is used by all repositories and services
3. **Security (CC3)** practices are enforced across all API endpoints and frontend auth flows

---

## Adding New Contexts

When adding a new bounded context:

1. Create directory in `docs/02-architecture/backend/contexts/{context-name}/`
2. Create `architecture.md`, `data-models.md`, `api-contracts.md`, `code-locations.md`
3. Add entry to this document
4. Update [00-system-map.md](00-system-map.md) with context reference
