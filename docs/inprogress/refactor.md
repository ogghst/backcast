# Codebase Refactoring Plan

**Document:** REF-001  
**Status:** 🔄 In Progress  
**Date:** 2024-12-19  
**Related:** DOC-002 (Data Model), DOC-004 (Technology Stack), DOC-005 (Dev Environment)

---

## Executive Summary

This document outlines the necessary refactoring actions to adapt the current scaffolded FastAPI template to implement the EVM Project Budget Management System as specified in the project documentation. The current codebase is a generic authentication-focused template that needs to be transformed into a domain-specific EVM management system.

**Current State:** Generic FastAPI template with User/Item models  
**Target State:** Full EVM Project Budget Management System with 25+ domain models

---

## 1. Project Structure Compliance

### 1.1 Backend Directory Structure

**Current:**
```
backend/app/
├── api/
│   └── routes/
├── core/
├── models.py          # Contains User/Item only
├── crud.py            # Generic CRUD operations
├── main.py
└── alembic/

Required Additions:
backend/app/
├── api/
│   └── routes/
│       ├── projects.py      # NEW - Project management endpoints
│       ├── wbes.py          # NEW - WBE management endpoints
│       ├── cost_elements.py # NEW - Cost element endpoints
│       ├── budgets.py       # NEW - Budget/revenue allocation
│       ├── costs.py         # NEW - Cost registration
│       ├── earned_value.py  # NEW - EVM recording
│       ├── forecasts.py     # NEW - Forecasting
│       ├── change_orders.py # NEW - Change management
│       ├── reports.py       # NEW - EVM reporting
│       └── calculations.py  # NEW - EVM calculation engine
├── models/
│   ├── __init__.py          # NEW - Model exports
│   ├── user.py              # MOVE from models.py
│   ├── project.py           # NEW - Project model
│   ├── wbe.py               # NEW - WBE model
│   ├── cost_element.py      # NEW - Cost element model
│   ├── schedule.py          # NEW - Schedule baseline
│   ├── earned_value.py      # NEW - Earned value entry
│   ├── forecast.py          # NEW - Forecast model
│   ├── cost_registration.py # NEW - Cost registration
│   ├── baseline_log.py      # NEW - Baseline management
│   ├── change_order.py      # NEW - Change order
│   ├── quality_event.py     # NEW - Quality management
│   └── ... (all 25 entities)
├── schemas/                  # NEW - Pydantic schemas
│   ├── __init__.py
│   ├── user.py              # MOVE from models.py
│   ├── project.py
│   ├── wbe.py
│   ├── evm_calculations.py
│   └── ... (all DTOs)
├── services/                 # NEW - Business logic layer
│   ├── __init__.py
│   ├── project_service.py
│   ├── budget_service.py
│   ├── evm_calculation_service.py  # Critical - EVM engine
│   ├── reconciliation_service.py
│   └── forecast_service.py
├── repositories/             # NEW - Data access layer
│   ├── __init__.py
│   ├── project_repository.py
│   ├── wbe_repository.py
│   └── ... (per-entity repositories)
├── calculations/             # NEW - Calculation engine
│   ├── __init__.py
│   ├── planned_value.py     # PV calculation
│   ├── earned_value.py      # EV calculation
│   ├── performance_indices.py # CPI, SPI, TCPI
│   ├── variance.py           # CV, SV
│   ├── aggregation.py        # Hierarchical rollups
│   └── progression.py        # Schedule progression (linear/gaussian/log)
├── core/
│   ├── config.py             # Already exists
│   ├── db.py                 # Already exists
│   └── security.py           # Already exists
├── crud.py                   # REFACTOR - Move to repositories/
├── models.py                 # REFACTOR - Split into models/
└── main.py                   # Already exists
```

**Key Actions:**
1. Create `models/` directory and split `models.py` into domain-specific files
2. Create `schemas/` directory for Pydantic DTOs (separate from database models)
3. Create `services/` directory for business logic
4. Create `repositories/` directory to replace `crud.py` with typed repositories
5. Create `calculations/` directory for EVM calculation engine
6. Add new API route modules for each domain area

---

### 1.2 Frontend Directory Structure

**Current:**
```
frontend/src/
├── components/
│   ├── Admin/        # Template example
│   ├── Items/        # Template example
│   ├── Common/       # Navbar, Sidebar
│   └── ui/           # Chakra UI components
├── routes/
│   ├── _layout/
│   ├── login.tsx
│   └── signup.tsx
├── client/           # Generated OpenAPI client
├── hooks/
├── theme/
└── utils.ts

Required Additions:
frontend/src/
├── components/
│   ├── Common/       # Keep Navbar, Sidebar
│   ├── Projects/     # NEW
│   │   ├── ProjectList.tsx
│   │   ├── ProjectForm.tsx
│   │   └── ProjectCard.tsx
│   ├── WBEs/         # NEW
│   │   ├── WBEList.tsx
│   │   ├── WBETree.tsx
│   │   └── WBEForm.tsx
│   ├── CostElements/ # NEW
│   │   └── CostElementManager.tsx
│   ├── Budgets/      # NEW
│   │   ├── BudgetAllocation.tsx
│   │   └── RevenueDistribution.tsx
│   ├── Schedules/    # NEW
│   │   ├── ScheduleBaseline.tsx
│   │   └── TimePhasedPlanning.tsx
│   ├── Costs/        # NEW
│   │   ├── CostRegistration.tsx
│   │   └── CostHistory.tsx
│   ├── EarnedValue/  # NEW
│   │   ├── EVRecording.tsx
│   │   └── EVBaseline.tsx
│   ├── EVMReports/   # NEW
│   │   ├── PerformanceDashboard.tsx
│   │   ├── VarianceReport.tsx
│   │   ├── CostPerformanceReport.tsx
│   │   └── EVMTrendChart.tsx
│   ├── Forecasts/    # NEW
│   │   ├── ForecastEntry.tsx
│   │   └── ForecastTrend.tsx
│   ├── ChangeOrders/ # NEW
│   │   └── ChangeOrderWorkflow.tsx
│   └── ui/           # Keep existing
├── routes/
│   ├── projects.tsx    # NEW
│   ├── wbes.tsx        # NEW
│   ├── budgets.tsx     # NEW
│   ├── costs.tsx       # NEW
│   ├── evm-reports.tsx # NEW
│   └── forecasts.tsx   # NEW
├── pages/              # NEW (alternative organization)
│   ├── Projects/
│   ├── Reports/
│   └── Management/
├── services/           # NEW - API client functions
│   ├── api.ts
│   ├── projects.ts
│   ├── evm.ts
│   └── ...
├── store/              # NEW - State management
│   ├── projectStore.ts
│   └── evmStore.ts
├── types/              # NEW - TypeScript domain types
│   ├── project.ts
│   ├── wbe.ts
│   ├── evm.ts
│   └── api.ts
├── utils/
│   ├── calculations.ts  # NEW - Client-side EVM calcs
│   ├── formatting.ts    # NEW
│   └── validation.ts    # NEW
└── (existing files)
```

**Key Actions:**
1. Create domain-specific component directories (Projects, WBEs, etc.)
2. Remove template examples (Items, Admin if not needed)
3. Create `services/` for typed API client functions
4. Create `types/` for domain TypeScript interfaces
5. Create `store/` for global state management (Zustand)
6. Add calculation utilities for client-side EVM metrics
7. Build reusable chart/dashboard components

---

## 2. Database Model Implementation

### 2.1 Create Domain Models

**Priority 1 (Core Structure):**
- [ ] `Project` - Top-level entity
- [ ] `WBE` - Work Breakdown Element (machine/deliverable)
- [ ] `CostElement` - Department-level budget tracking
- [ ] `CostElementType` - Lookup table for departments
- [ ] `User` - Already exists, may need role extensions

**Priority 2 (Financial Tracking):**
- [ ] `BudgetAllocation` - Budget assignment to cost elements
- [ ] `RevenueAllocation` - Revenue distribution across WBEs/elements
- [ ] `CostRegistration` - Actual cost recording
- [ ] `BaselineLog` - Baseline tracking system

**Priority 3 (EVM Functionality):**
- [ ] `CostElementSchedule` - Schedule baseline (start date, end date, progression type)
- [ ] `EarnedValueEntry` - Work completion percentage recording
- [ ] `Forecast` - Estimate at Completion (EAC) tracking

**Priority 4 (Change Management):**
- [ ] `ChangeOrder` - Scope change documentation
- [ ] `ChangeOrderItem` - Individual change details
- [ ] `QualityEvent` - Quality issue tracking

**Reference:** See `docs/data_model.md` for complete schema specifications

**Key Actions:**
1. Create SQLModel classes for all 25 entities defined in data model
2. Define relationships (Project → WBE → CostElement hierarchy)
3. Add validation rules (budget reconciliation, date ranges, etc.)
4. Create Alembic migrations for all tables
5. Add indexes for performance (foreign keys, lookup fields)

---

## 3. API Layer Refactoring

### 3.1 Create Domain-Specific Endpoints

**Current API Routes:**
- `/api/v1/users/` - User management ✅
- `/api/v1/login/` - Authentication ✅
- `/api/v1/items/` - Template CRUD ❌ Remove or repurpose
- `/api/v1/utils/` - Health check ✅

**Required New Routes:**

#### Project Management
- `POST   /api/v1/projects/` - Create project
- `GET    /api/v1/projects/` - List projects
- `GET    /api/v1/projects/{id}` - Get project details
- `PUT    /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

#### WBE Management
- `POST   /api/v1/projects/{project_id}/wbes/` - Create WBE
- `GET    /api/v1/projects/{project_id}/wbes/` - List WBEs for project
- `GET    /api/v1/wbes/{id}` - Get WBE details
- `PUT    /api/v1/wbes/{id}` - Update WBE
- `DELETE /api/v1/wbes/{id}` - Delete WBE

#### Cost Element Management
- `POST   /api/v1/wbes/{wbe_id}/cost-elements/` - Create cost element
- `GET    /api/v1/wbes/{wbe_id}/cost-elements/` - List cost elements
- `GET    /api/v1/cost-elements/{id}` - Get cost element
- `PUT    /api/v1/cost-elements/{id}` - Update cost element

#### Budget & Revenue
- `POST   /api/v1/cost-elements/{id}/budget` - Allocate budget
- `GET    /api/v1/cost-elements/{id}/budget` - Get budget
- `POST   /api/v1/projects/{id}/revenue-distribution` - Distribute revenue
- `GET    /api/v1/projects/{id}/budget-summary` - Get summary

#### Schedule Baseline
- `POST   /api/v1/cost-elements/{id}/schedule` - Create schedule baseline
- `GET    /api/v1/cost-elements/{id}/schedule` - Get schedule
- `PUT    /api/v1/schedules/{id}` - Update schedule
- `POST   /api/v1/baselines/` - Create baseline log entry

#### Cost Recording
- `POST   /api/v1/cost-elements/{id}/costs` - Register cost
- `GET    /api/v1/cost-elements/{id}/costs` - List costs
- `GET    /api/v1/costs/{id}` - Get cost details
- `PUT    /api/v1/costs/{id}` - Update cost

#### Earned Value
- `POST   /api/v1/cost-elements/{id}/earned-value` - Record earned value
- `GET    /api/v1/cost-elements/{id}/earned-value` - Get EV history
- `GET    /api/v1/cost-elements/{id}/evm-metrics` - Get current EVM metrics

#### EVM Calculations
- `GET    /api/v1/projects/{id}/evm-summary` - Project-level EVM
- `GET    /api/v1/wbes/{id}/evm-summary` - WBE-level EVM
- `GET    /api/v1/cost-elements/{id}/evm-summary` - Element EVM
- `GET    /api/v1/projects/{id}/planned-value` - Calculate PV
- `GET    /api/v1/projects/{id}/earned-value` - Calculate EV

#### Reporting
- `GET    /api/v1/projects/{id}/cost-performance-report` - Full report
- `GET    /api/v1/projects/{id}/variance-analysis` - Variance report
- `GET    /api/v1/projects/{id}/performance-dashboard` - Dashboard data
- `GET    /api/v1/reports/export` - CSV/Excel export

#### Forecasting
- `POST   /api/v1/cost-elements/{id}/forecasts` - Create forecast
- `GET    /api/v1/cost-elements/{id}/forecasts` - List forecasts
- `PUT    /api/v1/forecasts/{id}` - Update forecast
- `GET    /api/v1/cost-elements/{id}/forecast-trend` - Forecast history

#### Change Orders
- `POST   /api/v1/projects/{id}/change-orders` - Create change order
- `GET    /api/v1/projects/{id}/change-orders` - List change orders
- `PUT    /api/v1/change-orders/{id}` - Update change order
- `POST   /api/v1/change-orders/{id}/approve` - Approve change order

**Key Actions:**
1. Remove or deprecate `/api/v1/items/` route
2. Create route modules for each domain area
3. Implement pagination for list endpoints
4. Add filtering and sorting to queries
5. Implement proper error handling and validation

---

## 4. Business Logic Layer

### 4.1 Create Service Layer

**Critical Services:**

#### EVM Calculation Service
```python
# app/services/evm_calculation_service.py
class EVMCalculationService:
    def calculate_planned_value(
        self, cost_element: CostElement, as_of_date: date
    ) -> Decimal
    """Calculate PV = BAC × planned completion %"""
    
    def calculate_earned_value(
        self, cost_element: CostElement, as_of_date: date
    ) -> Decimal
    """Calculate EV = BAC × physical completion %"""
    
    def calculate_actual_cost(
        self, cost_element: CostElement, as_of_date: date
    ) -> Decimal
    """Calculate AC from cost registrations"""
    
    def calculate_performance_indices(
        self, pv: Decimal, ev: Decimal, ac: Decimal
    ) -> dict[str, Decimal]
    """Calculate CPI, SPI, TCPI"""
    
    def calculate_variances(
        self, ev: Decimal, pv: Decimal, ac: Decimal
    ) -> dict[str, Decimal]
    """Calculate CV, SV"""
    
    def aggregate_evm_hierarchy(
        self, project: Project, as_of_date: date
    ) -> dict
    """Roll up EVM metrics from elements → WBEs → Project"""
```

#### Budget Reconciliation Service
```python
# app/services/budget_service.py
class BudgetService:
    def allocate_budget(
        self, cost_element: CostElement, amount: Decimal
    ) -> bool
    """Allocate budget with validation"""
    
    def reconcile_budgets(
        self, wbe: WBE
    ) -> bool
    """Ensure WBE budgets sum to allocations"""
    
    def check_overflow(
        self, cost_element: CostElement, amount: Decimal
    ) -> bool
    """Validate no budget overrun"""
```

#### Schedule Service
```python
# app/services/schedule_service.py
class ScheduleService:
    def calculate_planned_completion(
        self, schedule: CostElementSchedule, 
        as_of_date: date
    ) -> Decimal
    """Calculate planned % based on progression type"""
    
    def apply_progression(
        self, start_date: date, end_date: date,
        as_of_date: date, progression_type: str
    ) -> Decimal
    """Apply linear/gaussian/logarithmic progression"""
```

#### Forecast Service
```python
# app/services/forecast_service.py
class ForecastService:
    def create_forecast(
        self, cost_element: CostElement, eac: Decimal
    ) -> Forecast
    """Create forecast version"""
    
    def mark_current_forecast(
        self, forecast: Forecast
    ) -> None
    """Set forecast as current version"""
```

**Key Actions:**
1. Create service classes for each domain area
2. Move business logic from API routes to services
3. Implement transaction management for multi-step operations
4. Add comprehensive error handling and validation
5. Create unit tests for all calculation logic

---

## 5. Data Access Layer

### 5.1 Replace CRUD with Repository Pattern

**Current:** Single `crud.py` with mixin functions  
**Target:** Typed repositories per entity

```python
# app/repositories/project_repository.py
class ProjectRepository:
    def create(
        self, session: Session, project_create: ProjectCreate
    ) -> Project
    def get_by_id(self, session: Session, project_id: UUID) -> Project | None
    def list(
        self, session: Session, skip: int, limit: int
    ) -> list[Project]
    def update(
        self, session: Session, project: Project, 
        project_update: ProjectUpdate
    ) -> Project
    def delete(self, session: Session, project: Project) -> None
```

**Benefits:**
- Type safety
- Easier testing (mock repositories)
- Clear separation of concerns
- Consistent query patterns

**Key Actions:**
1. Create repository classes for each entity
2. Implement common operations (CRUD, filtering, pagination)
3. Add query optimization (eager loading, select fields)
4. Replace `crud.py` imports with repository injection
5. Add repository tests

---

## 6. Pydantic Schemas

### 6.1 Create DTO Layer

**Separate concerns:**
- **Database Models** (`models/`) - SQLModel classes for ORM
- **API Schemas** (`schemas/`) - Pydantic models for request/response

**Required Schemas:**

#### Project
- `ProjectCreate` - POST request
- `ProjectUpdate` - PUT request
- `ProjectPublic` - API response
- `ProjectDetail` - Full project with nested WBEs

#### WBE
- `WBECreate`
- `WBEUpdate`
- `WBEPublic`
- `WBEDetail` - With cost elements

#### Cost Element
- `CostElementCreate`
- `CostElementUpdate`
- `CostElementPublic`
- `CostElementDetail` - With schedule, costs, EV

#### EVM Metrics
- `EVMSummary` - PV, EV, AC, CPI, SPI, etc.
- `VarianceSummary` - CV, SV
- `PerformanceIndices` - CPI, SPI, TCPI

#### Reports
- `CostPerformanceReport` - Tabular data
- `VarianceAnalysisReport`
- `PerformanceDashboardData`

**Key Actions:**
1. Create schema classes in `schemas/`
2. Implement proper validation rules
3. Add field descriptions for OpenAPI docs
4. Create nested schemas for relationships
5. Add example values for documentation

---

## 7. Calculation Engine

### 7.1 Implement EVM Calculations

**Core Calculations:**

#### Planned Value (PV)
```
PV = BAC × Planned Completion %
Planned Completion % = f(schedule_start, schedule_end, progression_type, as_of_date)
```

**Progression Types:**
- **Linear:** Even distribution over duration
- **Gaussian:** Normal distribution peak at midpoint
- **Logarithmic:** Slow start, accelerating completion

#### Earned Value (EV)
```
EV = BAC × Physical Completion %
Physical Completion % = from EarnedValueEntry
```

#### Actual Cost (AC)
```
AC = Sum of all CostRegistration.amount where registration_date <= as_of_date
```

#### Performance Indices
```
CPI = EV / AC   (Cost Performance Index)
SPI = EV / PV   (Schedule Performance Index)
TCPI = (BAC - EV) / (BAC - AC)  (To-Complete Performance Index)
```

#### Variances
```
CV = EV - AC    (Cost Variance)
SV = EV - PV    (Schedule Variance)
```

#### Aggregation
```
Project_PV = Sum(all WBE PVs)
WBE_PV = Sum(all Cost Element PVs in WBE)
```

**Key Actions:**
1. Create calculation modules in `calculations/`
2. Implement progression type formulas
3. Add hierarchical aggregation logic
4. Create comprehensive unit tests with known values
5. Validate against manual calculations
6. Document calculation formulas

---

## 8. Database Configuration

### 8.1 Migration Path

**Current:** PostgreSQL configured in docker-compose.yml  
**Documentation:** SQLite for MVP, PostgreSQL for production

**Key Actions:**
1. **Option A:** Use SQLite for MVP (simplest)
   - Update `backend/app/core/config.py` to support SQLite
   - Use file-based database during development
   - Migrate to PostgreSQL for production

2. **Option B:** Keep PostgreSQL (current setup)
   - Aligns with production environment
   - No migration needed later
   - Requires Docker or local PostgreSQL

**Recommendation:** Start with PostgreSQL to avoid migration complexity

---

## 9. Frontend Refactoring

### 9.1 Remove Template Code

**To Remove:**
- `frontend/src/components/Items/` - Template CRUD example
- `frontend/src/components/Admin/` - Generic admin
- `frontend/src/components/Pending/` - Template example
- `frontend/src/routes/_layout/items.tsx` - Template route

**To Keep:**
- `frontend/src/components/Common/` - Navbar, Sidebar
- `frontend/src/components/UserSettings/` - User preferences
- `frontend/src/components/ui/` - Chakra UI base components

**Key Actions:**
1. Delete template component directories
2. Remove template routes
3. Update navigation menu
4. Clean up unused imports

---

### 9.2 Create Domain Components

**Priority 1 (Sprint 1):**
- Project creation form
- WBE creation form
- Cost element creation form
- Project list view
- WBE tree/hierarchy view

**Priority 2 (Sprint 2):**
- Budget allocation interface
- Revenue distribution interface
- Schedule baseline creation
- Time-phased planning UI

**Priority 3 (Sprint 3):**
- Cost registration form
- Cost history table
- Baseline log management

**Priority 4 (Sprint 4):**
- Earned value recording interface
- EVM summary displays
- Performance dashboard

**Priority 5 (Sprint 5):**
- Cost performance report table
- Variance analysis report
- EVM trend charts
- Report export functionality

**Key Actions:**
1. Create component skeletons
2. Implement forms with React Hook Form
3. Add data tables with TanStack Table
4. Build charts with Recharts
5. Implement responsive layouts

---

### 9.3 State Management

**Current:** TanStack Query for server state only  
**Target:** Add Zustand for global client state

**Store Structure:**
```typescript
// app/stores/projectStore.ts
interface ProjectStore {
  selectedProject: Project | null
  setSelectedProject: (project: Project | null) => void
  
  projects: Project[]
  loading: boolean
  loadProjects: () => Promise<void>
}

// app/stores/evmStore.ts
interface EVMStore {
  activeDate: Date
  setActiveDate: (date: Date) => void
  
  evmMetrics: Record<string, EVMSummary>
  loading: boolean
}
```

**Key Actions:**
1. Install Zustand
2. Create stores for global state
3. Keep server state in TanStack Query
4. Coordinate between stores and queries

---

### 9.4 Charting Library Integration

**Required Charts:**
- EVM Curves (PV, EV, AC over time)
- Variance trends
- Performance index trends
- Forecast progression
- Budget vs Actual comparison

**Key Actions:**
1. Install and configure Recharts
2. Create reusable chart components
3. Implement date range filtering
4. Add export to image functionality

---

## 10. Testing Strategy

### 10.1 Backend Testing

**Unit Tests:**
- [ ] All calculation functions (PV, EV, CPI, SPI, etc.)
- [ ] Service layer business logic
- [ ] Repository data access
- [ ] Validation rules

**Integration Tests:**
- [ ] API endpoint testing
- [ ] Database operations
- [ ] Authentication/authorization
- [ ] EVM calculation flows

**Test Files:**
```
backend/tests/
├── unit/
│   ├── calculations/
│   │   ├── test_planned_value.py
│   │   ├── test_earned_value.py
│   │   ├── test_performance_indices.py
│   │   └── test_variance.py
│   └── services/
│       ├── test_evm_service.py
│       └── test_budget_service.py
├── integration/
│   ├── api/
│   │   ├── test_projects.py
│   │   ├── test_wbes.py
│   │   └── test_evm_endpoints.py
│   └── database/
│       ├── test_relationships.py
│       └── test_aggregations.py
└── fixtures/
    ├── project_data.py
    └── evm_test_data.py
```

**Key Actions:**
1. Create calculation unit tests with known values
2. Add API integration tests
3. Test hierarchical aggregations
4. Validate EVM calculations against manual results
5. Aim for >80% code coverage

---

### 10.2 Frontend Testing

**Component Tests:**
- [ ] Form validation
- [ ] Data table rendering
- [ ] Chart rendering
- [ ] User interactions

**E2E Tests:**
- [ ] Project creation flow
- [ ] Budget allocation flow
- [ ] Cost registration flow
- [ ] EVM report generation

**Key Actions:**
1. Add React Testing Library tests
2. Create Playwright E2E scenarios
3. Test responsive layouts
4. Validate calculations client-side

---

## 11. Data Migration

### 11.1 Initial Data

**Lookup Tables:**
- [ ] Cost Element Types (departments)
- [ ] Project Status values
- [ ] WBE Status values
- [ ] Cost Categories
- [ ] Progression Types

**Seed Script:**
```python
# backend/app/initial_data.py
def init_lookup_data(session: Session):
    # Create cost element types
    departments = ["sales", "syseng", "ut", "sw", "field", "pm", 
                   "produzione", "collaudi", "cliente"]
    for dept in departments:
        # Create CostElementType records
        
    # Create other lookup data
```

**Key Actions:**
1. Create seed migration
2. Load initial lookup data
3. Add data validation
4. Document initial data structure

---

## 12. Documentation Updates

### 12.1 API Documentation

**Auto-generated:**
- Swagger UI at `/docs` ✅ (FastAPI default)
- OpenAPI JSON at `/openapi.json` ✅
- ReDoc at `/redoc` ✅

**Manual:**
- [ ] Calculation formulas documentation
- [ ] Progression type examples
- [ ] EVM metric explanations
- [ ] API usage examples

---

### 12.2 Code Documentation

**Docstrings:**
- [ ] All service methods
- [ ] Calculation functions
- [ ] Complex query logic
- [ ] Business rules

**Comments:**
- [ ] EVM formula explanations
- [ ] Architecture decisions
- [ ] Performance optimizations

---

## 13. DevOps & CI/CD

### 13.1 Current State

**Already Configured:**
- ✅ Docker & Docker Compose
- ✅ GitHub Actions (from template)
- ✅ Pre-commit hooks (Ruff, mypy)
- ✅ Test automation

**To Verify:**
- [ ] Backend tests run in CI
- [ ] Frontend tests run in CI
- [ ] Linting enforced
- [ ] Type checking enforced

**Key Actions:**
1. Update CI workflows for domain tests
2. Add performance tests for calculations
3. Configure deployment automation
4. Set up staging environment

---

## 14. Sprint Execution Plan

### Sprint 1: Foundation (E1-001 to E1-007)

**Tasks:**
1. Create directory structure (models/, schemas/, services/, repositories/, calculations/)
2. Split models.py into domain files
3. Create Project, WBE, CostElement models
4. Create API routes for Project/WBE/CostElement
5. Create basic CRUD operations
6. Add validation rules
7. Write initial tests

**Deliverables:**
- ✅ Users can create projects
- ✅ Users can create WBEs within projects
- ✅ Users can create cost elements within WBEs

---

### Sprint 2: Budget & Revenue (E2-001 to E2-006)

**Tasks:**
1. Create BudgetAllocation and RevenueAllocation models
2. Build budget allocation UI
3. Build revenue distribution UI
4. Implement reconciliation logic
5. Create schedule baseline model
6. Build time-phased planning UI
7. Add progression type calculation

**Deliverables:**
- ✅ Users can allocate budgets
- ✅ Users can distribute revenue
- ✅ Users can create schedule baselines

---

### Sprint 3: Cost Recording (E3-001 to E3-005)

**Tasks:**
1. Create CostRegistration model
2. Build cost registration UI
3. Implement cost aggregation logic
4. Create BaselineLog model
5. Build cost history views
6. Add baseline management

**Deliverables:**
- ✅ Users can record actual costs
- ✅ Users can view cost history
- ✅ Users can manage baselines

---

### Sprint 4: EVM Calculations (E3-006, E4-001 to E4-006)

**Tasks:**
1. Create EarnedValueEntry model
2. Build earned value recording UI
3. Implement PV calculation engine
4. Implement EV calculation engine
5. Calculate CPI, SPI, TCPI
6. Calculate variances
7. Create EVM summary displays
8. Add aggregation logic

**Deliverables:**
- ✅ Complete EVM calculation engine
- ✅ Users can record earned value
- ✅ System calculates all EVM metrics
- ✅ Users can view EVM summaries

---

### Sprint 5: Reporting (E4-007 to E4-011)

**Tasks:**
1. Build cost performance report
2. Build variance analysis report
3. Create performance dashboard
4. Add report export (CSV/Excel)
5. Implement filtering and date ranges
6. Add EVM trend charts

**Deliverables:**
- ✅ Comprehensive EVM reports
- ✅ Visual dashboards
- ✅ Report export capability

---

### Sprint 6: Forecasting & Change Orders (E5-001 to E5-007)

**Tasks:**
1. Create Forecast model
2. Build forecast interface
3. Create ChangeOrder models
4. Build change order workflow
5. Implement budget adjustment logic
6. Add forecast integration in reports
7. Build forecast trend visualization

**Deliverables:**
- ✅ Forecast management
- ✅ Change order processing
- ✅ Complete MVP functionality

---

## 15. Risk Mitigation

### 15.1 Technical Risks

**Risk:** EVM calculation complexity  
**Mitigation:**
- Prototype calculations in Sprint 4 early
- Create extensive test cases with known values
- Manual validation against example data
- Code review for formulas

**Risk:** Performance with large datasets  
**Mitigation:**
- Add database indexes early
- Implement query optimization
- Consider caching for aggregate views
- Profile and benchmark queries

**Risk:** Frontend bundle size  
**Mitigation:**
- Code splitting with TanStack Router
- Lazy load charts
- Tree-shake unused Chakra UI components
- Monitor bundle size

---

### 15.2 Process Risks

**Risk:** Scope creep  
**Mitigation:**
- Strict adherence to sprint plan
- Defer non-MVP features to backlog
- Regular stakeholder reviews

**Risk:** Integration issues  
**Mitigation:**
- E2E tests from Sprint 1
- Continuous integration
- Feature flags for new functionality

---

## 16. Success Criteria

### 16.1 Technical

- [ ] All 25 data model entities implemented
- [ ] All EVM calculations validated
- [ ] >80% test coverage
- [ ] <5s report generation for 50 projects
- [ ] All API endpoints documented
- [ ] Zero critical bugs

### 16.2 Functional

- [ ] Users can create complete project hierarchy
- [ ] Users can allocate budgets and revenue
- [ ] Users can record costs and earned value
- [ ] System calculates accurate EVM metrics
- [ ] Users can generate all required reports
- [ ] Users can create forecasts and change orders

---

## 17. Resource Requirements

### 17.1 Development

- 2 full-stack developers (already available)
- 12-week timeline (Sprint 1-6)
- Access to fastapi full-stack template (already scaffolded)

### 17.2 Testing

- Manual test cases for EVM calculations
- Sample data set for integration testing
- UAT with Project Management Directorate

---

## 18. Next Immediate Actions

**Priority 1 (This Week):**
1. ✅ Review this refactoring plan
2. Create `models/` directory structure
3. Split `models.py` into domain-specific files
4. Create Project, WBE, CostElement models
5. Write first Alembic migration

**Priority 2 (Next Week):**
1. Create API routes for Project/WBE/CostElement
2. Implement basic CRUD operations
3. Build frontend forms for project creation
4. Test end-to-end flow
5. Begin Sprint 1 work

**Priority 3 (Week 3-4):**
1. Complete Sprint 1 deliverables
2. Add validation and business rules
3. Expand test coverage
4. Prepare for Sprint 2

---

## 19. References

- **Data Model:** `docs/data_model.md`
- **Technology Stack:** `docs/technology_stack_selection.md`
- **Project Status:** `docs/project_status.md`
- **Project Plan:** `docs/plan.md`
- **PRD:** `docs/prd.md`

---

## 20. Appendix: Migration Checklist

### Phase 1: Backend Structure (Week 1)
- [ ] Create `models/` directory
- [ ] Create `schemas/` directory
- [ ] Create `services/` directory
- [ ] Create `repositories/` directory
- [ ] Create `calculations/` directory
- [ ] Split `models.py` into domain files
- [ ] Create `__init__.py` exports

### Phase 2: Core Models (Week 1-2)
- [ ] Implement Project model
- [ ] Implement WBE model
- [ ] Implement CostElement model
- [ ] Create migration files
- [ ] Test migrations

### Phase 3: API Layer (Week 2)
- [ ] Create project routes
- [ ] Create WBE routes
- [ ] Create cost element routes
- [ ] Add validation
- [ ] Test endpoints

### Phase 4: Business Logic (Week 2-3)
- [ ] Implement service layer
- [ ] Implement repositories
- [ ] Add business rules
- [ ] Unit tests

### Phase 5: Frontend (Week 3-4)
- [ ] Remove template code
- [ ] Create domain components
- [ ] Build forms
- [ ] Implement state management
- [ ] Integration tests

---

**Document Owner:** Development Team  
**Last Updated:** 2024-12-19  
**Status:** 🔄 Ready for Execution

