# Bounded Contexts

**Last Updated:** 2026-05-30

This document defines the bounded contexts used to partition the Backcast  system. Each context represents a cohesive functional area with clear boundaries.

## Backend Contexts

### 0. EVCS Core (Entity Versioning Control System)

**Responsibility:** Bitemporal versioning framework, branching, soft delete, time-travel
**Owner:** Backend Team
**Documentation:** [backend/contexts/evcs-core/](backend/contexts/evcs-core/)
**ADR:** [ADR-005: Bitemporal Versioning](decisions/ADR-005-bitemporal-versioning.md)

> [!NOTE]
>
> - **Branchable entities** (Project, WBSElement, ControlAccount, WorkPackage, ScheduleBaseline, Forecast, OrganizationalUnit, ChangeOrder) use `EntityBase + VersionableMixin + BranchableMixin`
> - **Versionable entities** (User, CostElementType, CostElement, CostRegistration, etc.) use `EntityBase + VersionableMixin`
> - **Simple entities** (RBACRole, Notification, DashboardLayout, etc.) use `SimpleEntityBase`

**Key Files:**

- `app/core/base/base.py` - `EntityBase`, `SimpleEntityBase`
- `app/models/mixins.py` - `VersionableMixin`, `BranchableMixin`
- `app/core/versioning/service.py` - `TemporalService[T]`
- `app/core/versioning/commands.py` - Generic Create/Update/Delete commands
- `app/core/simple/service.py` - `SimpleService` for standard CRUD

---

### 1. Authentication & Authorization

**Responsibility:** User identity verification, JWT token management, role-based access control (RBAC)
**Owner:** Backend Team
**Documentation:** [backend/contexts/auth/](backend/contexts/auth/)
**ADR:** [ADR-007: RBAC Service](decisions/ADR-007-rbac-service.md)

**Key Files:**

- `app/core/security.py` - JWT handling, password hashing (Argon2)
- `app/api/routes/auth.py` - Login endpoint, token refresh
- `app/services/rbac.py` - Permission checking, role enforcement

---

### 2. Organizational Unit Management

**Responsibility:** Organizational unit hierarchy for organizational structure
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Bitemporal with branching (via EVCS Core)

**Key Entities:**

- `OrganizationalUnit` - Organizational structure (Branchable)

**Key Files:**

- `app/models/domain/organizational_unit.py` - OrganizationalUnit model
- `app/services/organizational_unit_service.py` - OrganizationalUnitService
- `app/api/routes/organizational_units.py` - Organizational unit endpoints

---

### 3. User Management

**Responsibility:** User CRUD operations, profile management, admin user creation, user history
**Owner:** Backend Team
**Versioning:** Versionable (audit changes, no branching)
**Documentation:** [backend/contexts/user-management/](backend/contexts/user-management/)

**Key Files:**

- `app/models/domain/user.py` - User model, Role enum
- `app/services/user.py` - UserService, user history tracking
- `app/api/routes/users.py` - User endpoints, RBAC enforcement

---

### 4. Cost Element Type Management

**Responsibility:** Standardized cost categorization
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Versionable (no branching) - organizational reference data

**Description:**
Cost Element Types are organizational reference data that enable:

- Consistent cost categorization across projects
- Cross-project cost comparability

**Key Entities:**

- `CostElementType` - Standardized cost category (code, name, description)
- Satisfies: `VersionableProtocol` (NOT branchable)

**Key Files:**

- `app/models/domain/cost_element_type.py` - CostElementType model
- `app/services/cost_element_type_service.py` - CostElementTypeService
- `app/api/routes/cost_element_types.py` - Cost element type endpoints

---

### 5. Project & WBS Element Management

**Responsibility:** Project hierarchy, Work Breakdown Elements (machines), revenue allocation
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Bitemporal with branching (via EVCS Core)

**Key Entities:**

- `Project` - Top-level container for financial data
- `WBSElement` (Work Breakdown Element) - Individual machines/deliverables within projects
  - `budget_allocation` is a **computed attribute** (sum of child CostElement.budget_amount)
  - See [ADR-013: Computed Budget Attribute Pattern](decisions/ADR-013-computed-budget-attribute.md)

**Key Files:**

- `app/models/domain/project.py` - Project model
- `app/models/domain/wbs_element.py` - WBSElement model (with computed budget_allocation)
- `app/services/project_service.py` - ProjectService with EVCS support
- `app/services/wbs_element_service.py` - WBSElementService with budget computation
- `app/api/routes/projects.py` - Project endpoints
- `app/api/routes/wbs_elements.py` - WBS element endpoints

---

### 6. Cost Element & Financial Tracking

**Responsibility:** Departmental budgets, cost registration, forecasts, earned value tracking, schedule registrations
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Mixed — CostElement is Versionable, ScheduleBaseline is Branchable

**Description:**
Cost Elements are the leaf level of the project hierarchy where budgets are allocated and costs are tracked.

**Budget Architecture (Single Source of Truth):**
- `CostElement.budget_amount` is the **sole storage location** for all budget data
- WBS Element budgets are computed on-the-fly from child CostElements
- See [ADR-013: Computed Budget Attribute Pattern](decisions/ADR-013-computed-budget-attribute.md)

**Key Entities:**

- `CostElement` - Project-specific instance of a Cost Element Type
  - Versionable (financial facts are global across branches)
  - Has 1:1 relationship with ScheduleBaseline
  - **Sole source of budget data** via `budget_amount` field
  - Satisfies: `VersionableProtocol`
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

- `app/models/domain/cost_element.py` - CostElement model (versionable, with schedule_baseline_id FK)
- `app/models/domain/schedule_baseline.py` - ScheduleBaseline model (branchable)
- `app/services/cost_element_service.py` - CostElementService with auto-creation of baselines
- `app/services/schedule_baseline_service.py` - ScheduleBaselineService with 1:1 validation
- `app/api/routes/cost_elements.py` - Cost element endpoints with nested schedule baseline endpoints

---

### 7. Change Order Processing

**Responsibility:** Branch creation, modification, comparison, merging
**Owner:** Backend Team
**Status:** Implemented
**Versioning:** Bitemporal with branching — ChangeOrder is a Branchable entity

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

**Responsibility:** Planned Value, Earned Value, Actual Cost, performance indices, variance analysis, portfolio-level rollup
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Read-only aggregation over EVCS-valid-time actuals (as-of cuts via bitemporal queries)

**Key Calculations:**

- PV = BAC × % Planned Completion (using schedule baselines)
- EV = BAC × % Physical Completion (progress entries)
- AC = Sum of cost registrations (as-of valid_time)
- CPI, SPI, TCPI, CV, SV, VAC

**Key Endpoints:** (mounted at `/api/v1/evm`)

- `GET /portfolio` — portfolio-level EVM rollup across the caller's accessible projects (`portfolio-read` RBAC)
- `GET /{entity_type}/{entity_id}/metrics` — single-entity EVM metrics (project/wbs-element/cost-element)
- `GET /{entity_type}/{entity_id}/timeseries` — EVM metric time series
- `POST /batch` — batch metrics for multiple entities

**Key Files:**

- `app/services/evm_service.py` - EVM calculation engine
- `app/api/routes/evm.py` - EVM endpoints (portfolio, metrics, timeseries, batch)

**Documentation:** [EVM Requirements](../../01-product-scope/evm-requirements.md)

---

### 9. Cost Event Management

**Responsibility:** Track cost events and their types for project cost analysis
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Versionable (no branching)

**Key Entities:**

- `CostEvent` - Cost event record (Versionable)
- `CostEventType` - Cost event classification (Versionable)

**Key Files:**

- `app/models/domain/cost_event.py` - CostEvent model
- `app/models/domain/cost_event_type.py` - CostEventType model
- `app/services/cost_event_service.py` - CostEventService
- `app/services/cost_event_type_service.py` - CostEventTypeService
- `app/api/routes/cost_events.py` - Cost event endpoints
- `app/api/routes/cost_event_types.py` - Cost event type endpoints

**Documentation:** [Functional Requirements Section 9](../../01-product-scope/functional-requirements.md#9-quality-event-management)

---

### 10. AI/ML Integration

**Responsibility:** Provide intelligent analysis, natural language interaction, and AI-assisted data operations
**Owner:** Backend Team
**Status:** ✅ Implemented (E09-MULTIMODAL)
**Versioning:** AI operations are logged; entity changes follow EVCS versioning

**Description:**
AI/ML Integration provides a conversational AI interface built on LangGraph, enabling natural language interaction and AI-assisted CRUD operations with controlled write access through explicit user confirmation workflows. Supports multimodal input/output including text, images, and file attachments.

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
- Project & WBS Element Management tools (CRUD operations)
- Cost Element & Financial Tracking tools
- EVM Calculations & Reporting tools
- Change Order Processing tools
- Cost Event Management tools
- Organizational Unit & Cost Element Type tools
- User Management tools (admin operations)

**AI-Assisted Operations:**
- Full CRUD operations on all entities via natural language
- Create Projects, WBS Elements, Cost Elements from descriptions
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

**Key Files:**

- `backend/app/ai/agent_service.py` - LangGraph agent orchestration
- `backend/app/ai/tools/` - AI tool implementations
- `backend/app/ai/tools/templates/` - AI tool template system
- `backend/app/ai/tools/context_tools.py` - Context-aware tools
- `backend/app/ai/file_extractors.py` - File extraction for attachments
- `backend/app/ai/telemetry.py` - OpenTelemetry integration
- `backend/app/api/routes/ai_chat.py` - Chat endpoints with WebSocket streaming
- `backend/app/api/routes/ai_upload.py` - Image/file upload endpoints
- `backend/app/api/routes/ai_config.py` - AI configuration management
- `backend/app/api/routes/agent_schedules.py` - Cron-based agent scheduling endpoints (`/api/v1/ai/agent-schedules`)
- `backend/app/api/routes/mcp_servers.py` - MCP (Model Context Protocol) server registry endpoints (`/api/v1/mcp/servers`)
- `backend/app/models/domain/ai.py` - AI entities (sessions, messages, attachments)
- `backend/app/services/ai_config_service.py` - AI configuration service
- `backend/app/services/agent_schedule_service.py` - Agent schedule lifecycle + cron trigger service
- `backend/app/services/mcp_server_service.py` - MCP server config CRUD + encrypted credential storage
- `frontend/src/features/ai/chat/` - React chat interface components
- `frontend/src/hooks/navigation/` - Navigation abstraction hooks

**Dependencies:**

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
**Status:** Not yet built (report generation, scheduling, and export remain planned)
**Versioning:** Not versioned (read-only aggregation)

**Description:**
Reporting & Analytics provides comprehensive reporting capabilities across all bounded contexts without modifying source data. Interactive dashboards are served today via the **Dashboard & Widget Layouts** context (section 13); the entities below are the not-yet-built report-generation layer.

> [!NOTE]
> The following entities are **planned, not implemented** — no model/service/route exists for them yet:
> `ReportTemplate`, `ReportSchedule`, `ReportInstance`. (`DashboardConfiguration` is superseded by the live `DashboardLayout` model — see section 13.)

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
**Status:** ✅ Implemented (no dedicated entity — exposed as EVM endpoints + dashboard layout discriminator)
**Versioning:** Not versioned (aggregated view)

**Description:**
Portfolio Management provides executive-level oversight by aggregating data across the caller's accessible projects. Backcast is project-scoped (no `Portfolio` table); portfolio views are computed live and surfaced through two mechanisms:

1. **EVM rollup** — `GET /api/v1/evm/portfolio` aggregates CPI/SPI/VAC/EAC/BAC/TCPI across RBAC-accessible projects.
2. **Portfolio-scoped dashboard layouts** — `DashboardLayout.scope = "portfolio"` (vs `"project"`) plus an optional `role` tag selects which portfolio template defaults to a given role.

**Key Endpoints / Models:**

- `GET /api/v1/evm/portfolio` — portfolio EVM rollup (`portfolio-read` RBAC; see section 8)
- `DashboardLayout` columns: `scope` (`"project"` | `"portfolio"`), `role` (role-tagged portfolio templates), `is_template`, `is_default` (see section 13)

> [!NOTE]
> Earlier iterations of this doc listed phantom entities `Portfolio`, `PortfolioMetric`, `ResourceAllocation`, and `ExecutiveDashboard`. **None of these exist as code** — portfolio is a view, not a persisted entity. Project groupings / resource allocation remain out of scope.

**Dependencies:**

- All bounded contexts (data aggregation)
- Reporting & Analytics (portfolio reports)
- Authentication & Authorization (`portfolio-read` for executive access)

**Boundaries:**

- Does NOT manage individual project details
- Does NOT handle resource scheduling (project-level)
- Does NOT make project-level decisions

**Documentation:** [Functional Requirements Section 17](../../01-product-scope/functional-requirements.md#17-performance-and-scalability-requirements)

---

### 13. Dashboard & Widget Layouts

**Responsibility:** Composable dashboard grid, user/project/portfolio layouts, reusable templates
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Simple entities (not versioned)

**Description:**
Persisted dashboard compositions built on `react-grid-layout`. Layouts are scoped per user and per project, or global (portfolio). Templates are role-tagged for default rollout.

**Key Entities:**

- `DashboardLayout` - Persisted layout (widgets, layout config)
  - `scope`: `"project"` | `"portfolio"` discriminator
  - `role`: role tag for portfolio templates
  - `is_template`, `is_default` flags

**Key Files:**

- `app/models/domain/dashboard_layout.py` - DashboardLayout model (scope/role/is_template)
- `app/services/dashboard_service.py` - Dashboard composition service
- `app/services/dashboard_layout_service.py` - Layout CRUD + template management
- `app/api/routes/dashboard.py` - Dashboard endpoints
- `app/api/routes/dashboard_layouts.py` - Layout endpoints

---

### 14. Unified Notifications

**Responsibility:** Single pub/sub notification funnel with pluggable channels (in-app WebSocket + Telegram)
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Simple entities (not versioned)

**Description:**
`NotificationDispatcher` is the single funnel for all domain events (change orders, agents, broadcasts). Delivery is deferred to after-commit to avoid FK races. Channels include in-app WebSocket and Telegram (bot deep-link linking).

**Key Entities:**

- `Notification` - Notification record
- `NotificationDelivery` - Per-channel delivery tracking
- `UserNotificationPreference` - Per-user channel/category preferences
- `TelegramAccount` - Telegram user link

**Key Files:**

- `app/models/domain/notification.py` - Notification model
- `app/models/domain/notification_delivery.py` - Delivery model
- `app/models/domain/notification_preference.py` - Preference model
- `app/models/domain/telegram_account.py` - Telegram link model
- `app/services/notification_service.py` - NotificationDispatcher + emission
- `app/services/notification_preference_service.py` - Preference CRUD
- `app/services/telegram_link_service.py` - Telegram linking flow
- `app/api/routes/notifications.py` - Notification endpoints

---

### 15. Custom Fields

**Responsibility:** Admin-defined custom entity templates with typed, queryable JSONB field values
**Owner:** Backend Team
**Status:** ✅ Implemented (Phase 0+1; field queryability/indexes in progress)
**Versioning:** Templates ride EVCS clone(); per-version values stored in JSONB `custom_fields` dict

**Description:**
`CustomEntityTemplate` defines a set of typed field definitions (object-oriented field classes). Values are stored as a JSONB `custom_fields` dict on each versioned entity row, riding EVCS `clone()`/`UpdateCommand` for free versioning. `ai_visible` gates LLM exposure; `searchable` gates global-search inclusion.

**Key Entities:**

- `CustomEntityTemplate` - Admin template (branchable)
- Field definition OO package - Typed field classes (string/number/date/enum/...)

**Key Files:**

- `app/models/custom_fields/` - Field definition OO package (`base.py`, `fields.py`, `registry.py`)
- `app/models/domain/custom_entity_template.py` - CustomEntityTemplate model
- `app/services/custom_entity_template_service.py` - Template service
- `app/services/custom_field_service.py` - Field definition service
- `app/api/routes/custom_entity_templates.py` - Template endpoints (`/api/v1/custom-entity-templates`)

---

### 16. Global Search

**Responsibility:** Cross-entity text search with FilterParser (incl. JSONB custom-field filter/sort)
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Read-only over current versions

**Key Files:**

- `app/services/global_search_service.py` - Search + FilterParser
- `app/api/routes/search.py` - Search endpoint

---

### 17. Documents

**Responsibility:** Document upload, metadata, folder hierarchy, processing/extraction
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Simple entities (not versioned)

**Key Files:**

- `app/services/document_service.py` - Document CRUD
- `app/services/document_folder_service.py` - Folder hierarchy
- `app/services/document_processing_service.py` - Extraction/processing
- `app/api/routes/documents.py` - Document endpoints

---

### 18. MCP (Model Context Protocol) Servers

**Responsibility:** Registry of external MCP servers for AI tool integration, with encrypted config
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Simple entity (not versioned)

**Description:**
Admins register MCP servers (with encrypted credentials via Fernet) so the AI agent subsystem can connect to external tool sources.

**Key Files:**

- `app/services/mcp_server_service.py` - MCPServerService (CRUD + encrypt/decrypt config)
- `app/api/routes/mcp_servers.py` - MCP server endpoints (`/api/v1/mcp/servers`)

---

### 19. Agent Scheduling

**Responsibility:** Cron-based scheduling of AI agent runs (global/project/WBS scoped)
**Owner:** Backend Team
**Status:** ✅ Implemented
**Versioning:** Simple entity (not versioned); runs spawn fresh AI sessions

**Description:**
In-process lifespan task fires scheduled runs via `trigger_schedule_run` (shared overlap-guarded launcher). Scope discriminator mirrors AI chat (Global/Project/WBS). Skip-missed grace; fire-and-forget task held in strong-ref set.

**Key Files:**

- `app/services/agent_schedule_service.py` - Schedule lifecycle + cron trigger
- `app/api/routes/agent_schedules.py` - Schedule endpoints (`/api/v1/ai/agent-schedules`)

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

- `frontend/src/stores/useAuthStore.ts` - Zustand auth state (token, user, permissions)
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
- `backend/app/api/routes/` - API route definitions (auth, users, organizational units)
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
4. **Organizational Units** provide structure for **Cost Element Types** for organizational cost categorization
5. **Cost Element Types** are referenced by **Cost Elements** for standardized categorization
6. **Project/WBS Element** hierarchy contains **Cost Elements** (implemented)
7. **Financial Tracking** operates on **Cost Elements** (Versionable — financial facts are global, not branch-isolated) with **Schedule Registrations** for PV calculations
8. **Change Orders** are themselves **Branchable entities** that create branches via EVCS Core affecting **Project/WBS Element** hierarchy
9. **Cost Events** attribute costs to **Cost Elements** for profitability analysis
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
