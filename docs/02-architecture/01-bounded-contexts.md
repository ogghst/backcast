# Bounded Contexts

**Last Updated:** 2026-01-18

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

### 2. Department Management

**Responsibility:** Department CRUD operations for budget tracking
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Not versioned (standard CRUD)
**Key Files:**

- `app/models/domain/department.py` - Department model
- `app/services/department_service.py` - DepartmentService
- `app/api/routes/departments.py` - Department endpoints

---

### 3. User Management

**Responsibility:** User CRUD operations, profile management, admin user creation, user history
**Owner:** Backend Team
**Versioning:** Not versioned (standard CRUD)
**Documentation:** [backend/contexts/user-management/](backend/contexts/user-management/)

**Key Files:**

- `app/models/user.py` - User model, Role enum
- `app/services/user.py` - UserService, user history tracking
- `app/api/v1/users.py` - User endpoints, RBAC enforcement

---

### 4. Cost Element Type Management

**Responsibility:** Standardized cost categorization owned by departments
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Versionable (no branching) - organizational reference data

**Description:**
Cost Element Types are organizational reference data that enable:

- Consistent cost categorization across projects
- Cross-project cost comparability
- Department ownership of cost types

**Key Entities:**

- `CostElementType` - Standardized cost category (code, name, description, department_id)
- Satisfies: `VersionableProtocol` (NOT branchable)

**Key Files:**

- `app/models/domain/cost_element_type.py` - CostElementType model
- `app/services/cost_element_type_service.py` - CostElementTypeService
- `app/api/routes/cost_element_types.py` - Cost element type endpoints

---

### 5. Project & WBE Management

**Responsibility:** Project hierarchy, Work Breakdown Elements (machines), revenue allocation
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Bitemporal with branching (via EVCS Core)

**Key Entities:**

- `Project` - Top-level container for financial data
- `WBE` (Work Breakdown Element) - Individual machines/deliverables within projects
  - `budget_allocation` is a **computed attribute** (sum of child CostElement.budget_amount)
  - See [ADR-013: Computed Budget Attribute Pattern](decisions/ADR-013-computed-budget-attribute.md)

**Key Files:**

- `app/models/domain/project.py` - Project model
- `app/models/domain/wbe.py` - WBE model (with computed budget_allocation)
- `app/services/project_service.py` - ProjectService with EVCS support
- `app/services/wbe_service.py` - WBEService with budget computation
- `app/api/routes/projects.py` - Project endpoints
- `app/api/routes/wbes.py` - WBE endpoints

---

### 6. Cost Element & Financial Tracking

**Responsibility:** Departmental budgets, cost registration, forecasts, earned value tracking, schedule registrations
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Bitemporal with branching (via EVCS Core)

**Description:**
Cost Elements are the leaf level of the project hierarchy where budgets are allocated and costs are tracked.

**Budget Architecture (Single Source of Truth):**
- `CostElement.budget_amount` is the **sole storage location** for all budget data
- WBE budgets are computed on-the-fly from child CostElements
- See [ADR-013: Computed Budget Attribute Pattern](decisions/ADR-013-computed-budget-attribute.md)

**Key Entities:**

- `CostElement` - Project-specific instance of a Cost Element Type
  - Branchable (supports change orders)
  - Has 1:1 relationship with ScheduleBaseline
  - **Sole source of budget data** via `budget_amount` field
  - Satisfies: `BranchableProtocol`
  - Auto-creates default schedule baseline on creation

- `ScheduleBaseline` - Single schedule baseline defining planned work progression
  - Attributes: start_date, end_date, progression_type (linear/gaussian/logarithmic), description
  - 1:1 relationship with CostElement (enforced at database level)
  - Used for Planned Value (PV) calculations
  - Branchable (supports what-if scenarios via change order branches)
  - Full CRUD with nested endpoints under cost elements

**Relationship Architecture (as of 2026-01-18):**

- **Inverted FK**: cost_elements.schedule_baseline_id → schedule_baselines.schedule_baseline_id
- **Constraint**: Unique constraint on schedule_baseline_id enforces 1:1 relationship
- **API Pattern**: Nested endpoints `/api/v1/cost-elements/{id}/schedule-baseline`
- **ADR**: [ADR-009: Schedule Baseline 1:1 Relationship Inversion](decisions/ADR-009-schedule-baseline-1to1-relationship.md)

**Key Files:**

- `app/models/domain/cost_element.py` - CostElement model (branchable, with schedule_baseline_id FK)
- `app/models/domain/schedule_baseline.py` - ScheduleBaseline model (branchable)
- `app/services/cost_element_service.py` - CostElementService with auto-creation of baselines
- `app/services/schedule_baseline_service.py` - ScheduleBaselineService with 1:1 validation
- `app/api/routes/cost_elements.py` - Cost element endpoints with nested schedule baseline endpoints

---

### 7. Change Order Processing

**Responsibility:** Branch creation, modification, comparison, merging
**Owner:** Backend Team
**Status:** Implemented
**Versioning:** Uses EVCS Core branching capabilities

**Key Operations:**

- Automatic branch creation for change orders (`BR-{id}`)
- Branch isolation for modifications
- Branch comparison for impact analysis
- Branch merge for approved change orders
- Branch locking/unlocking

> **For workflow states, approval matrix, and user stories**, see: [Change Management User Stories](../../01-product-scope/change-management-user-stories.md)
>
> **For technical implementation**, see: [Time Travel & Branching Architecture](cross-cutting/temporal-query-reference.md)

---

### 8. EVM Calculations & Reporting

**Responsibility:** Planned Value, Earned Value, Actual Cost, performance indices, variance analysis
**Owner:** Backend Team
**Status:** Planned

**Key Calculations:**

- PV = BAC × % Planned Completion (using schedule registrations)
- EV = BAC × % Physical Completion
- AC = Sum of cost registrations
- CPI, SPI, TCPI, CV, SV, VAC

**Documentation:** [EVM Requirements](../../01-product-scope/evm-requirements.md)

---

### 9. Quality Event Management

**Responsibility:** Track quality-related costs that impact project profitability without corresponding revenue increases
**Owner:** Backend Team
**Status:** Planned
**Versioning:** Bitemporal with branching (via EVCS Core)

**Description:**
Quality events capture costs associated with rework, defects, warranty claims, and other quality-related issues that reduce project profitability.

**Key Entities:**

- `QualityEvent` - Root event record (date, description, severity, status)
- `QualityEventCost` - Cost attribution to cost elements
- `RootCause` - Classification system (rework, defects, warranty, design error)
- `PreventiveAction` - Improvement tracking and verification

**Key Responsibilities:**

- Register quality events with detailed descriptions
- Attribute costs to specific cost elements
- Classify root causes for analysis
- Track corrective and preventive actions
- Generate quality cost analysis reports
- Calculate quality cost as % of total project costs

**Dependencies:**

- Cost Element & Financial Tracking (cost attribution)
- Project & WBE Management (project context)
- Reporting & Analytics (quality reports)

**Boundaries:**

- Does NOT handle warranty claims processing (external system)
- Does NOT handle supplier quality management (separate context)
- Does NOT handle quality assurance planning (project management)

**Documentation:** [Functional Requirements Section 9](../../01-product-scope/functional-requirements.md#9-quality-event-management)

---

### 10. AI/ML Integration

**Responsibility:** Provide intelligent analysis, natural language interaction, and AI-assisted data operations
**Owner:** Backend Team
**Status:** Planned
**Versioning:** AI operations are logged; entity changes follow EVCS versioning

**Description:**
AI/ML Integration provides a generalistic conversational AI interface built on LangGraph, enabling natural language interaction and AI-assisted CRUD operations with controlled write access through explicit user confirmation workflows.

**Architecture Components:**

- **LangGraph Agent Graph**: Core orchestration layer managing conversation flow, tool invocation, and state management
- **OpenAI Provider**: Configurable connector to OpenAI-compatible endpoints (supports OpenAI, Azure OpenAI, self-hosted models)
- **WebSocket Streamer**: Real-time bidirectional communication for streaming conversations to frontend
- **Tool Layer**: Backend services exposed as LangGraph tools for entity operations

**Key Responsibilities:**

**Session Management:**
- Support multiple concurrent sessions per user
- Maintain conversation history and context per session
- Associate sessions with project/branch context
- Handle session persistence and resumption

**Multimodal Input/Output:**
- Accept text input from users
- Accept image input (screenshots, diagrams, documents)
- Accept file attachments (PDFs, spreadsheets, etc.)
- Output text with Markdown formatting
- Output Mermaid diagrams for visualizations
- Stream responses in real-time via WebSocket

**Tool Integration (Backend Services as Tools):**
- Project & WBE Management tools (CRUD operations)
- Cost Element & Financial Tracking tools
- EVM Calculations & Reporting tools
- Change Order Processing tools
- Quality Event Management tools
- Department & Cost Element Type tools
- User Management tools (admin operations)

**AI-Assisted Operations:**
- Full CRUD operations on all entities via natural language
- Create Projects, WBEs, Cost Elements from descriptions
- Update any entity attributes via conversational interface
- Soft delete entities (with confirmation workflow)
- Generate change order drafts from user requirements
- Suggest budget allocations based on project context
- Assist with schedule baseline configuration

**Analysis & Insights:**
- Generate project assessments using AI (Section 12.6 of FR)
- Detect anomalies in EVM metrics
- Predict cost/schedule overruns
- Suggest optimization opportunities
- Analyze forecast accuracy trends

**Output Formatting:**
- Markdown rendering for structured text responses
- Mermaid diagram generation for:
  - Project hierarchy visualization
  - Workflow diagrams
  - Timeline/Gantt charts
  - Entity relationship diagrams

**Dependencies:**

- All bounded contexts (full CRUD access via tools)
- LangGraph (agent orchestration)
- OpenAI SDK (LLM provider)
- WebSocket infrastructure (real-time streaming)
- Authentication & Authorization (RBAC enforcement for tool calls)

**Boundaries:**

- Does NOT replace human decision-making
- All AI-initiated write operations require explicit user confirmation
- AI operations are fully audit logged with user attribution
- Project data anonymized before sending to external AI services for analysis
- Entity changes made via AI follow standard EVCS versioning and approval workflows
- AI cannot bypass RBAC - user permissions are enforced for all tool operations
- AI-generated change orders follow the same workflow as manually created ones
- LLM endpoint is configurable (not locked to specific provider)

**Documentation:** [Functional Requirements Section 12.6](../../01-product-scope/functional-requirements.md#126-ai-integration)

---

### 11. Reporting & Analytics

**Responsibility:** Generate standard and custom reports from project data
**Owner:** Backend Team
**Status:** Planned
**Versioning:** Not versioned (read-only aggregation)

**Description:**
Reporting & Analytics provides comprehensive reporting capabilities across all bounded contexts without modifying source data.

**Key Entities:**

- `ReportTemplate` - Reusable report definitions (name, query_spec, format)
- `ReportSchedule` - Automated report generation (frequency, recipients)
- `ReportInstance` - Generated report tracking (created_at, status, file_url)
- `DashboardConfiguration` - User dashboard settings (widgets, layout, filters)

**Key Responsibilities:**

- Generate standard EVM reports (Section 13.1 of FR)
- Create variance analysis reports with trends
- Build forecast comparison reports
- Generate baseline comparison reports
- Support custom report builder (Section 13.3 of FR)
- Export to CSV, Excel, PDF formats
- Provide visual dashboards (Section 13.2 of FR)

**Dependencies:**

- All bounded contexts (data sources)
- Portfolio Management (cross-project reports)
- Authentication & Authorization (report access control)

**Boundaries:**

- Does NOT modify source data (read-only)
- Does NOT handle report distribution (email, etc.)
- Does NOT provide ad-hoc query interface (use API)

**Documentation:** [Functional Requirements Sections 13.1-13.4](../../01-product-scope/functional-requirements.md#13-reporting)

---

### 12. Portfolio Management

**Responsibility:** Aggregate and analyze data across multiple projects for executive oversight
**Owner:** Backend Team
**Status:** Planned
**Versioning:** Not versioned (aggregated view)

**Description:**
Portfolio Management enables executive-level oversight by aggregating data across 50+ concurrent projects.

**Key Entities:**

- `Portfolio` - Project groupings (name, description, project_ids)
- `PortfolioMetric` - Aggregated measurements (metric_name, value, calculated_at)
- `ResourceAllocation` - Cross-project resources (resource_id, project_allocations)
- `ExecutiveDashboard` - Portfolio view configuration (widgets, kpis, filters)

**Key Responsibilities:**

- Aggregate metrics across 50+ concurrent projects
- Provide portfolio-level performance dashboards
- Support multi-project resource allocation
- Generate executive summary reports
- Track portfolio-wide trends and benchmarks
- Enable project comparison and ranking

**Dependencies:**

- All bounded contexts (data aggregation)
- Reporting & Analytics (portfolio reports)
- Authentication & Authorization (executive access)

**Boundaries:**

- Does NOT manage individual project details
- Does NOT handle resource scheduling (project-level)
- Does NOT make project-level decisions

**Documentation:** [Functional Requirements Section 17](../../01-product-scope/functional-requirements.md#17-performance-and-scalability-requirements)

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
4. **Departments** own **Cost Element Types** for organizational cost categorization
5. **Cost Element Types** are referenced by **Cost Elements** for standardized categorization
6. **Project/WBE** hierarchy contains **Cost Elements** (implemented)
7. **Financial Tracking** operates on **Cost Elements** with **Schedule Registrations** for PV calculations
8. **Change Orders** create branches via EVCS Core affecting **Project/WBE/Cost Elements** (planned)
9. **Quality Events** attribute costs to **Cost Elements** for profitability analysis
10. **EVM Calculations** provide metrics for **AI/ML** analysis and **Reporting**
11. **Reporting & Analytics** aggregates data from all bounded contexts (read-only)
12. **Portfolio Management** aggregates metrics across all projects for executive oversight

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
