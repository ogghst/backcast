# Analysis: EVM Analyzer with Master-Detail UI

**Date:** 2026-01-22
**Status:** ✅ **COMPLETE** - All User Decisions Recorded
**Analyst:** Claude (Requirements Analyst & Software Architect)
**Feature:** Enhanced EVM Analysis with Master-Detail UI and Reusable Components

---

## Executive Summary

This analysis examines the requirements for transforming the existing EVM Analysis component into a comprehensive master-detail interface with an advanced EVM Analyzer modal. The feature aims to provide users with deeper understanding of Earned Value Management metrics across cost elements, WBEs, and projects through enhanced visualization and reusable architecture.

**Key Findings:**
- Current EVM service and schemas provide solid foundation
- Requires new time-series data endpoints for historical charting
- Frontend needs reusable EVM metric components with gauge visualizations
- Multi-entity aggregation requires backend service layer enhancements
- Timeline charts need new backend API support for historical PV/EV/AC data

**Recommended Approach:** Option 2 - Phased Implementation with Reusable Architecture (detailed below)

---

## 1. Requirements Clarification

### 1.1 User Intent

The user requires enhanced EVM analysis capabilities to:

1. **Transform Existing EVM Analysis Box** (ForecastComparisonCard.tsx) into a master-detail area:
   - Organize metrics by topic (Schedule, Costs, Variance, Performance, Forecast)
   - Display metric descriptions/goals alongside each metric
   - Add "Advanced" button to open "EVM Analyzer" modal

2. **EVM Analyzer Modal** should provide:
   - Thorough evaluation of ALL EVM metrics at control date
   - Metrics explained in numbers AND graphs (gauges, charts)
   - Enhanced user perception of cost element performance
   - Timeline charts:
     - Chart 1: PV/EV/AC over time (progression curves)
     - Chart 2: Forecast vs Actual costs (accuracy tracking)
   - X-axis with scroll and zoom support
   - Ability to summarize by day, week, or month

3. **Reusable Architecture**:
   - Components accept cost elements, WBEs, or projects as input
   - Support multiple entities simultaneously with aggregated values
   - Create EVMMetric class generalizing metrics in both backend (Python) and frontend (TypeScript)

### 1.2 Functional Requirements

#### FR-1: Enhanced Summary View
- Organize metrics into logical topic groups per EVM requirements document
- Display metric name, value, and short description/goal
- Color-coded status indicators (favorable/unfavorable)
- "Advanced" button triggers modal

#### FR-2: EVM Analyzer Modal
- Display same metrics as summary but with enhanced visualizations
- Semi-circle gauges for CPI/SPI (traditional EVM style)
- Dual timeline charts with scroll/zoom:
  - Chart A: PV/EV/AC progression curves over time
  - Chart B: Forecast vs Actual costs over time
- Granularity selector: Day, Week, Month
- Control date integration via TimeMachineContext

#### FR-3: Multi-Entity Support
- Accept list of entities (cost elements, WBEs, or projects)
- Calculate and display aggregated metrics (sum/average as appropriate)
- Maintain single-entity mode for detailed drill-down

#### FR-4: EVMMetric Generalization
- Backend: Create generic EVMMetric Pydantic models
- Frontend: Create TypeScript interfaces/types for EVMMetric
- Support metric aggregation logic at service layer

#### FR-5: Time-Travel Support
- Respect TimeMachineContext for all queries
- Historical chart data supports time-travel queries
- Metrics calculated at control_date

### 1.3 Non-Functional Requirements

#### NFR-1: Performance
- Summary view must render within 500ms
- Modal with charts must render within 2 seconds
- Time-series data queries should be optimized with database indexes

#### NFR-2: Code Quality
- Follow existing backend/frontend coding standards
- TypeScript strict mode with zero errors
- MyPy strict mode with zero errors (backend)
- 80%+ test coverage for new components

#### NFR-3: Reusability
- Components must be generic across entity types
- Service layer must support polymorphic entity types
- Chart components must be reusable across contexts

#### NFR-4: User Experience
- Intuitive metric descriptions
- Clear visual hierarchy
- Responsive design for different screen sizes
- Accessibility compliance (ARIA labels, keyboard navigation)

### 1.4 Constraints

#### C1: Time-Travel Limitations
- Historical EVM calculations limited by existing data (progress entries, cost registrations)
- Past-dated control_date queries work but future projections are static

#### C2: Existing Architecture
- Must use TimeMachineContext for control date
- Must follow existing component patterns (ProgressionPreviewChart, SCurveComparison)
- Must use @ant-design/charts for line charts
- Backend uses FastAPI with Pydantic schemas

#### C3: Budget & Schedule
- Story points: TBD (to be estimated in planning phase)
- Target: Complete within current sprint cycle

---

## 2. Context Discovery

### 2.1 Current State Analysis

#### Backend Architecture

**Existing EVM Service** (`backend/app/services/evm_service.py`):
- ✅ Well-structured service with comprehensive metric calculations
- ✅ Supports time-travel via `control_date` parameter
- ✅ Supports branch isolation via `branch` and `branch_mode` parameters
- ✅ Calculates all core EVM metrics: BAC, PV, AC, EV, CV, SV, CPI, SPI, EAC, VAC, ETC
- ✅ Includes forecast-based CPI (`cpi_forecast`) as efficiency metric
- ⚠️ Currently only supports single cost element calculations
- ❌ Missing multi-entity aggregation logic
- ❌ Missing time-series data endpoints for historical charting

**Existing EVM Schema** (`backend/app/models/schemas/evm.py`):
- ✅ Comprehensive Pydantic model `EVMMetricsRead`
- ✅ Well-documented with field descriptions and formulas
- ✅ Includes metadata (cost_element_id, control_date, branch, branch_mode)
- ⚠️ Tightly coupled to cost elements (not generic across entity types)
- ❌ Missing aggregated metrics schema
- ❌ Missing time-series data schema for charts

**Current API Endpoint** (`backend/app/api/routes/cost_elements.py:529-546`):
```
GET /api/v1/cost-elements/{cost_element_id}/evm
Query params: as_of (control_date), branch, mode
```

#### Frontend Architecture

**Existing Component** (`frontend/src/features/forecasts/components/ForecastComparisonCard.tsx`):
- ✅ Displays 8 key EVM metrics with Statistic components
- ✅ Color-coded status indicators
- ✅ Tooltips for metric explanations
- ✅ Uses `useCostElementEvmMetrics` hook for data fetching
- ⚠️ Flat metric layout (not organized by topic)
- ❌ No advanced visualization (gauges, charts)
- ❌ No modal interface
- ❌ Single entity only

**Existing Chart Patterns:**
- ✅ `ProgressionPreviewChart` - Custom SVG chart for progression curves
- ✅ `SCurveComparison` - @ant-design/charts Line component
- ✅ Both support time-series data visualization
- ⚠️ No existing gauge component for CPI/SPI
- ❌ No existing EVM-specific timeline charts

**State Management:**
- ✅ TimeMachineContext provides control_date, branch, mode
- ✅ TanStack Query for server state caching
- ✅ Query key factory pattern for cache management

### 2.2 Documentation Review

**EVM Requirements** (`docs/01-product-scope/evm-requirements.md`):
- ✅ Comprehensive metric definitions and formulas
- ✅ ANSI/EIA-748 standard compliance
- ✅ Metric categorization:
  - Schedule Metrics: PV, SV, SPI
  - Cost Metrics: AC, CV, CPI
  - Variance Metrics: CV, SV, VAC
  - Performance Indices: CPI, SPI
  - Forecast Metrics: EAC, ETC, VAC
- ✅ Progression types: Linear, Gaussian, Logarithmic
- ✅ Aggregation rules: Cost Element → WBE → Project
- ✅ Control date and branch context requirements

**Bounded Contexts** (`docs/02-architecture/01-bounded-contexts.md`):
- ✅ Cost Element & Financial Tracking bounded context defined
- ✅ EVM Calculations & Reporting bounded context defined
- ✅ Clear separation of concerns between entities

**Coding Standards:**
- Backend: Protocol-based type system, command pattern, service layer
- Frontend: Feature-based structure, TanStack Query, Ant Design

### 2.3 Technical Feasibility Assessment

#### Backend Feasibility: ✅ **FEASIBLE**

**Strengths:**
- Existing EVMService is well-architected and extensible
- Pydantic schemas provide strong typing and validation
- Service layer pattern supports easy extension

**Gaps to Address:**
1. **Time-series data endpoints**: Need new endpoints to return historical EVM metrics over time
2. **Multi-entity aggregation**: Need service layer to aggregate metrics across multiple entities
3. **Generic EVMMetric models**: Need to refactor schemas to support polymorphic entity types
4. **WBE/Project EVM endpoints**: Need to extend EVM calculations to WBE and project levels

**Complexity: Medium**
- Time-series endpoints require new database queries with date grouping
- Aggregation logic is straightforward (sum for amounts, weighted average for indices)
- Generic schemas require careful design to maintain type safety

#### Frontend Feasibility: ✅ **FEASIBLE**

**Strengths:**
- Existing chart components provide good patterns to follow
- TimeMachineContext integration is well-established
- TanStack Query provides efficient data fetching and caching
- Ant Design provides robust UI components

**Gaps to Address:**
1. **Gauge component**: Need custom SVG gauge for CPI/SPI (similar to ProgressionPreviewChart)
2. **Modal component**: Need EVM Analyzer modal with tabbed/scrollable layout
3. **Multi-entity hooks**: Need hooks to fetch and aggregate metrics for multiple entities
4. **Timeline charts**: Need to integrate two chart types with scroll/zoom controls
5. **Granularity selector**: Need UI control for day/week/month aggregation

**Complexity: Medium**
- Custom gauges require SVG/Canvas work (moderate complexity)
- Modal layout is straightforward (Ant Design Modal)
- Multi-entity aggregation requires careful state management

#### Integration Feasibility: ✅ **FEASIBLE**

**Strengths:**
- Clear API contract between backend and frontend
- Existing authentication and error handling patterns
- Time-travel semantics are well-defined

**Gaps to Address:**
1. **API versioning**: New endpoints need to follow existing patterns
2. **Error handling**: Time-series queries need graceful degradation
3. **Loading states**: Complex modal needs comprehensive loading states

**Complexity: Low**
- Integration follows established patterns
- Minimal risk to existing functionality

---

## 3. Solution Design

### 3.1 Option 1: Minimal Enhancement (Quick Win)

**Approach:** Enhance existing ForecastComparisonCard with minimal changes, add basic modal.

**Backend Changes:**
- Add new endpoint: `GET /api/v1/cost-elements/{id}/evm/timeseries`
- Return pre-aggregated time-series data for PV/EV/AC and forecast vs actual
- No generic EVMMetric class (reuse existing schemas)

**Frontend Changes:**
- Reorganize ForecastComparisonCard metrics by topic (Layout change only)
- Add "Advanced" button opening modal with:
  - Same metrics as summary
  - Two @ant-design/charts Line charts for time-series
  - Basic granularity selector (Week/Month)
- No multi-entity support
- Custom SVG gauges for CPI/SPI

**Pros:**
- ✅ Fastest to implement (3-5 days)
- ✅ Minimal architectural changes
- ✅ Low risk to existing functionality
- ✅ Addresses core user need (better visualization)

**Cons:**
- ❌ Not reusable across entity types (WBE, Project)
- ❌ No multi-entity comparison/aggregation
- ❌ Doesn't create reusable EVMMetric generalization
- ❌ Limited extensibility for future features
- ❌ Gauge implementation is one-off (not reusable)

**Estimation:** 5-8 story points

---

### 3.2 Option 2: Phased Implementation with Reusable Architecture (RECOMMENDED)

**Approach:** Build reusable EVM metric system in phases, starting with cost elements but designed for extension.

#### Phase 1: Foundation (This Iteration)
**Backend Changes:**
1. **Generic EVMMetric Schemas** (`backend/app/models/schemas/evm.py`):
   ```python
   class EVMMetricBase(BaseModel):
       """Generic EVM metric base class"""
       metric_type: Literal["bac", "pv", "ac", "ev", "cv", "sv", "cpi", "spi", "eac", "vac", "etc"]
       value: Decimal
       description: str
       category: Literal["schedule", "cost", "variance", "performance", "forecast"]

   class EVMMetricsResponse(BaseModel):
       """Generic EVM metrics response for any entity type"""
       entity_type: Literal["cost_element", "wbe", "project"]
       entity_id: UUID
       entity_name: str
       metrics: Dict[str, EVMMetricBase]
       control_date: datetime
       branch: str
       branch_mode: BranchMode

   class EVMTimeSeriesPoint(BaseModel):
       """Single point in EVM time-series"""
       date: datetime
       pv: Decimal | None
       ev: Decimal | None
       ac: Decimal | None
       forecast: Decimal | None
       actual: Decimal | None

   class EVMTimeSeriesResponse(BaseModel):
       """Time-series data for EVM charts"""
       entity_type: Literal["cost_element", "wbe", "project"]
       entity_id: UUID
       granularity: Literal["day", "week", "month"]
       data_points: List[EVMTimeSeriesPoint]
   ```

2. **Multi-Entity EVM Service** (`backend/app/services/evm_service.py`):
   ```python
   class EVMService:
       async def calculate_evm_metrics_batch(
           self,
           entity_ids: List[UUID],
           entity_type: Literal["cost_element", "wbe", "project"],
           control_date: datetime,
           branch: str = "main",
           branch_mode: BranchMode = BranchMode.MERGE,
       ) -> EVMMetricsResponse:
           """Calculate EVM metrics for multiple entities and aggregate"""

       async def get_evm_timeseries(
           self,
           entity_id: UUID,
           entity_type: Literal["cost_element", "wbe", "project"],
           start_date: datetime,
           end_date: datetime,
           granularity: Literal["day", "week", "month"] = "week",
           control_date: datetime | None = None,
           branch: str = "main",
           branch_mode: BranchMode = BranchMode.MERGE,
       ) -> EVMTimeSeriesResponse:
           """Get historical EVM metrics for time-series charts"""
   ```

3. **New API Endpoints**:
   ```
   # Generic EVM metrics (works for any entity type)
   GET /api/v1/evm/{entity_type}/{entity_id}/metrics
   Query: as_of, branch, mode

   # Multi-entity aggregation
   POST /api/v1/evm/{entity_type}/metrics/batch
   Body: { entity_ids: UUID[], as_of, branch, mode }

   # Time-series data
   GET /api/v1/evm/{entity_type}/{entity_id}/timeseries
   Query: start_date, end_date, granularity, as_of, branch, mode
   ```

**Frontend Changes:**
1. **Generic EVM Types** (`frontend/src/features/evm/types.ts`):
   ```typescript
   export type EntityType = "cost_element" | "wbe" | "project";

   export interface EVMMetric {
     metricType: EVMMetricType;
     value: number;
     description: string;
     category: EVMMetricCategory;
     favorable: boolean | null;
   }

   export type EVMMetricType =
     | "bac" | "pv" | "ac" | "ev"
     | "cv" | "sv"
     | "cpi" | "spi"
     | "eac" | "vac" | "etc";

   export type EVMMetricCategory =
     | "schedule" | "cost" | "variance" | "performance" | "forecast";

   export interface EVMMetricsResponse {
     entityType: EntityType;
     entityId: string;
     entityName: string;
     metrics: Record<string, EVMMetric>;
     controlDate: string;
     branch: string;
     branchMode: BranchMode;
   }

   export interface EVMTimeSeriesPoint {
     date: string;
     pv: number | null;
     ev: number | null;
     ac: number | null;
     forecast: number | null;
     actual: number | null;
   }

   export interface EVMTimeSeriesResponse {
     entityType: EntityType;
     entityId: string;
     granularity: "day" | "week" | "month";
     dataPoints: EVMTimeSeriesPoint[];
   }
   ```

2. **Reusable Components** (`frontend/src/features/evm/components/`):

   **MetricCard** - Display single metric with description:
   ```typescript
   interface MetricCardProps {
     metric: EVMMetric;
     size?: "small" | "medium" | "large";
     showDescription?: boolean;
   }
   ```

   **MetricCategorySection** - Group metrics by category:
   ```typescript
   interface MetricCategorySectionProps {
     category: EVMMetricCategory;
     metrics: EVMMetric[];
     layout?: "grid" | "list";
   }
   ```

   **EVMSummaryView** - Reorganized summary card:
   ```typescript
   interface EVMSummaryViewProps {
     entityId: string;
     entityType: EntityType;
     onOpenAdvanced?: () => void;
   }
   ```

   **EVMGauge** - Semi-circle gauge for CPI/SPI:
   ```typescript
   interface EVMGaugeProps {
     value: number;
     type: "cpi" | "spi";
     size?: number;
     showLabels?: boolean;
   }
   ```

   **EVMTimeSeriesChart** - Dual timeline charts:
   ```typescript
   interface EVMTimeSeriesChartProps {
     timeSeries: EVMTimeSeriesResponse;
     chartType: "progression" | "accuracy";
     granularity: "day" | "week" | "month";
     onGranularityChange: (g: "day" | "week" | "month") => void;
   }
   ```

   **EVMAnalyzerModal** - Advanced analysis modal:
   ```typescript
   interface EVMAnalyzerModalProps {
     open: boolean;
     onClose: () => void;
     entityId: string;
     entityType: EntityType;
   }
   ```

3. **Custom Hooks** (`frontend/src/features/evm/api/`):
   ```typescript
   export const useEVMMetrics = (
     entityId: string,
     entityType: EntityType
   ) => { /* ... */ };

   export const useEVMMetricsBatch = (
     entityIds: string[],
     entityType: EntityType
   ) => { /* ... */ };

   export const useEVMTimeSeries = (
     entityId: string,
     entityType: EntityType,
     startDate: string,
     endDate: string,
     granularity: "day" | "week" | "month"
   ) => { /* ... */ };
   ```

4. **Updated ForecastComparisonCard**:
   - Replace existing flat layout with EVMSummaryView
   - Add "Advanced" button
   - Maintain backward compatibility

**Data Layer Changes:**
- New database queries for time-series aggregation
- Optimize with indexes on `cost_registrations.date`, `progress_entries.reported_at`
- Materialized view for pre-aggregated weekly/monthly data (if performance issues)

**Pros:**
- ✅ Fully reusable across entity types (cost elements, WBEs, projects)
- ✅ Supports multi-entity aggregation
- ✅ Creates extensible EVMMetric system
- ✅ Follows existing architecture patterns
- ✅ Testable and maintainable
- ✅ Enables future enhancements (comparisons, benchmarks)
- ✅ Phased approach reduces risk

**Cons:**
- ⚠️ Longer initial implementation (8-12 days)
- ⚠️ More complex upfront design
- ⚠️ Requires careful migration of existing component
- ⚠️ Higher initial testing burden

**Estimation:** 13-21 story points

#### Phase 2: WBE and Project Support (Future Iteration)
- Extend EVMService to calculate metrics for WBEs and projects
- Aggregation logic: sum child entity metrics
- UI components support entity type switching

#### Phase 3: Advanced Features (Future)
- Multi-entity comparison view
- Benchmarking against historical performance
- AI-powered insights (as specified in EVM requirements)

---

### 3.3 Option 3: Comprehensive Rewrite (High Risk)

**Approach:** Complete overhaul of EVM system with microservices-style architecture.

**Backend Changes:**
- Create separate EVM microservice
- Event-driven architecture for metric calculation
- Real-time metric updates via websockets
- Complex caching layer with Redis
- Materialized views for all time-series data

**Frontend Changes:**
- Custom charting library (no @ant-design/charts dependency)
- Real-time metric updates
- Complex state management with Redux
- Advanced drag-and-drop dashboard builder

**Pros:**
- ✅ Maximum flexibility and extensibility
- ✅ Real-time updates
- ✅ Best performance at scale

**Cons:**
- ❌ Massive scope (4-6 weeks)
- ❌ High risk to project timeline
- ❌ Deviates from existing architecture patterns
- ❌ Over-engineering for current requirements
- ❌ Difficult to maintain
- ❌ Breaking change to existing functionality

**Estimation:** 40+ story points

**Assessment:** ❌ **NOT RECOMMENDED** - Violates YAGNI principle, exceeds current needs, introduces unnecessary complexity.

---

## 4. Recommendation & Decision

### 4.1 Comparison Matrix

| Criterion | Option 1: Minimal | Option 2: Phased (Recommended) | Option 3: Rewrite |
|-----------|-------------------|-------------------------------|-------------------|
| **Time to Value** | ⭐⭐⭐⭐⭐ (Fast) | ⭐⭐⭐ (Medium) | ⭐ (Slow) |
| **Reusability** | ⭐ (Low) | ⭐⭐⭐⭐⭐ (High) | ⭐⭐⭐⭐⭐ (High) |
| **Extensibility** | ⭐⭐ (Limited) | ⭐⭐⭐⭐⭐ (Excellent) | ⭐⭐⭐⭐⭐ (Excellent) |
| **Risk** | ⭐ (Low) | ⭐⭐ (Medium) | ⭐⭐⭐⭐⭐ (High) |
| **Maintainability** | ⭐⭐⭐ (Good) | ⭐⭐⭐⭐⭐ (Excellent) | ⭐⭐ (Poor) |
| **User Value** | ⭐⭐⭐ (Good) | ⭐⭐⭐⭐⭐ (Excellent) | ⭐⭐⭐⭐⭐ (Excellent) |
| **Architecture Fit** | ⭐⭐⭐ (Good) | ⭐⭐⭐⭐⭐ (Perfect) | ⭐ (Poor) |
| **Cost** | 5-8 SP | 13-21 SP | 40+ SP |
| **Future-Proofing** | ⭐⭐ (Limited) | ⭐⭐⭐⭐⭐ (Excellent) | ⭐⭐⭐⭐⭐ (Excellent) |

### 4.2 Recommended Approach: **Option 2 - Phased Implementation**

**STATUS**: ✅ **APPROVED** - User decisions confirm this approach

**Rationale:**

1. **Architectural Alignment**: Option 2 perfectly aligns with existing patterns:
   - Service layer orchestration (EVMService)
   - Pydantic schemas for type safety
   - Feature-based frontend structure
   - TimeMachineContext integration
   - TanStack Query for data fetching

2. **Reusability**: Creates genuinely reusable components that work across entity types, reducing future development effort for WBE and project EVM views.

3. **User Value**: Delivers immediate value (cost element EVM analysis) while building foundation for enhanced features (multi-entity comparison, benchmarking).

4. **Risk Management**: Phased approach allows validation at each step:
   - Phase 1: Cost element support (validate UI/UX)
   - Phase 2: WBE/Project support (validate aggregation) ✅ **INCLUDED**
   - Phase 3: Advanced features (deferred to backlog) ⏸️ **DEFERRED**

5. **Maintainability**: Clean separation of concerns, well-typed interfaces, and comprehensive testing ensure long-term maintainability.

6. **Cost-Effective**: While more expensive upfront than Option 1, it prevents technical debt and rework, providing better ROI over time.

**Selected Implementation Strategy (Based on User Decisions):**

- **EVMMetric Structure**: Flat response schema with explicit metric definitions (not list-based)
- **Time-series**: Server-side on-the-fly calculation with weekly default granularity
- **Charts**: Ant Design built-in zoom, traditional semi-circle gauges for CPI/SPI
- **Aggregation**: Backend-weighted aggregation by BAC for indices
- **Multi-entity**: Backend aggregation in single API call
- **Scope**: Phase 1 (Cost Elements) + Phase 2 (WBE/Project) in current iteration
- **Advanced Features**: Phase 3 deferred to backlog

### 4.3 Implementation Strategy

**SCOPE CONFIRMED**: Phase 1 (Cost Elements) + Phase 2 (WBE/Project) in current iteration. Phase 3 deferred to backlog.

#### Sprint 1: Cost Element Foundation (Current Iteration - Part 1)
**Goal:** Implement Phase 1 for cost elements only

**Backend Tasks:**
1. Create generic EVMMetric schemas with flat structure (2-3 hours)
2. Implement `calculate_evm_metrics_batch()` for aggregation (3-4 hours)
3. Implement `get_evm_timeseries()` endpoint with on-the-fly calculation (4-6 hours)
4. Create new API routes for generic EVM (2-3 hours)
5. Write unit tests for new service methods (3-4 hours)

**Frontend Tasks:**
1. Create EVM types and interfaces with flat EVMMetricsResponse (1-2 hours)
2. Build MetricCard component (2-3 hours)
3. Build EVMGauge component (traditional semi-circle) (3-4 hours)
4. Build EVMTimeSeriesChart component with Ant Design zoom (3-4 hours)
5. Build EVMAnalyzerModal component with weekly default granularity (4-5 hours)
6. Refactor ForecastComparisonCard to use EVMSummaryView (2-3 hours)
7. Create custom hooks for data fetching (2-3 hours)
8. Write component tests (4-5 hours)

**Total Effort:** 35-50 hours (~13-21 story points)

#### Sprint 2: WBE and Project Support (Current Iteration - Part 2)
**Goal:** Extend to WBE and project entities ✅ **INCLUDED IN SCOPE**

**Tasks:**
1. Backend aggregation logic for child entities (6-8 hours)
2. WBE/Project EVM endpoints (3-4 hours)
3. Frontend entity type switching (2-3 hours)
4. Multi-entity batch API calls with backend aggregation (3-4 hours)
5. Weighted BAC aggregation for CPI/SPI indices (2-3 hours)
6. Context-dependent time-series range calculation (2-3 hours)
7. Testing and validation (4-5 hours)

**Total Effort:** 22-33 hours (~10-15 story points)

#### Sprint 3: Advanced Features (DEFERRED TO BACKLOG)
**Goal:** Multi-entity comparison and benchmarking ⏸️ **DEFERRED**

**Tasks:**
1. Comparison view component (6-8 hours)
2. Benchmarking against historical baselines (4-6 hours)
3. Performance optimizations (3-4 hours)
4. Testing and validation (3-4 hours)

**Total Effort:** 16-22 hours (~8-13 story points)

**Status:** Deferred to future iteration. Focus on core functionality first.

### 4.4 Success Criteria

**SCOPE**: Phase 1 + Phase 2 (Current Iteration) | Phase 3 (Deferred)

#### Phase 1 Success Criteria (Cost Elements):
- [ ] ForecastComparisonCard displays metrics organized by topic
- [ ] "Advanced" button opens EVM Analyzer modal
- [ ] Modal displays all metrics with traditional semi-circle gauges for CPI/SPI
- [ ] Modal displays two timeline charts (PV/EV/AC and Forecast vs Actual)
- [ ] Timeline charts support day/week/month granularity (default: weekly)
- [ ] Charts use Ant Design built-in zoom functionality
- [ ] All queries respect TimeMachineContext
- [ ] Components are reusable (accept generic entity types)
- [ ] Backend endpoints support batch queries
- [ ] Time-series data calculated server-side on-the-fly
- [ ] Metric descriptions are static (hardcoded in frontend)
- [ ] Empty state shown when no historical data available
- [ ] EVMMetricsResponse uses flat structure (not list-based)
- [ ] 80%+ test coverage for new code
- [ ] Zero MyPy and ESLint errors
- [ ] Performance: Summary renders in <500ms, modal in <2s

#### Phase 2 Success Criteria (WBE and Project Support) ✅ INCLUDED:
- [ ] WBE EVM metrics calculate correctly from child cost elements
- [ ] Project EVM metrics calculate correctly from child WBEs
- [ ] Multi-entity aggregation produces correct sums for amounts
- [ ] CPI/SPI aggregation uses weighted average by BAC
- [ ] Backend handles multi-entity aggregation in single API call
- [ ] UI seamlessly switches between entity types
- [ ] Time-series range is context-dependent:
  - [ ] Cost element: zoomed to its schedule range
  - [ ] Project: from project start to max(project end, control_date)
- [ ] All Phase 1 criteria maintained
- [ ] Entity type polymorphism working in backend and frontend
- [ ] 80%+ test coverage for WBE/project code

#### Phase 3 Success Criteria (Advanced Features) ⏸️ DEFERRED:
- [ ] Multi-entity comparison view functional
- [ ] Benchmarking against historical baselines works
- [ ] Performance optimizations effective (large datasets)
- [ ] All previous criteria maintained

**Status**: Phase 3 criteria deferred to backlog. Focus on Phase 1 + 2 completion.

### 4.5 Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Time-series query performance** | Medium | High | - Add database indexes<br>- Implement caching<br>- Use materialized views if needed |
| **Gauge component complexity** | Low | Medium | - Reference ProgressionPreviewChart pattern<br>- Keep design simple<br>- Reuse existing SVG patterns |
| **Multi-entity aggregation bugs** | Medium | High | - Comprehensive unit tests<br>- Integration tests with known datasets<br>- Manual validation against manual calculations |
| **Scope creep** | Medium | Medium | - Strict phase boundaries<br>- Prioritize Phase 1 features<br>- Defer advanced features to Phase 3 |
| **Breaking existing functionality** | Low | High | - Comprehensive regression tests<br>- Canary releases<br]- Rollback plan |

---

## 5. User Decisions

### 5.1 Technical Decisions

1. **EVMMetric Structure**: ✅ **DECIDED** - Flat structure in response, NOT a list of EVMMetricBase. All metrics explicitly defined as individual properties in EVMMetricsRead model. This maintains backward compatibility and provides better type safety.

2. **Phase 2 Inclusion**: ✅ **DECIDED** - Include Phase 2 (WBE and Project support) in this analysis iteration. Phase 3 (Advanced Features) deferred to backlog.

3. **Time-series Granularity**: ✅ **DECIDED** - Pre-calculate server-side on-the-fly. New request required when granularity changes (day/week/month). Optimize with database indexes initially, add materialized views if performance issues arise.

4. **Chart Zoom Implementation**: ✅ **DECIDED** - Use Ant Design (@ant-design/charts) built-in zoom functionality. No custom zoom controls needed initially.

5. **Gauge Design**: ✅ **DECIDED** - Traditional semi-circle gauge (like car speedometer). Matches EVM industry standard and user specification.

6. **Multi-entity Aggregation**: ✅ **DECIDED** - Backend aggregation (single API call). Perform calculations server-side for performance and consistency. Frontend displays aggregated results.

7. **Metric Descriptions**: ✅ **DECIDED** - Static (hardcoded in frontend). Define descriptions in frontend components for performance. Consider internationalization in future iterations.

8. **Default Chart View**: ✅ **DECIDED** - Weekly granularity as default. Balances detail level with readability for most use cases.

### 5.2 User Experience Decisions

9. **Historical Data Handling**: ✅ **DECIDED** - Empty state when no data available. Display user-friendly message: "No historical data available for this time range" when time-series queries return empty results.

### 5.3 Business Logic Decisions

10. **Aggregation Method for Indices**: ✅ **DECIDED** - Weighted by BAC (Budget at Completion). CPI and SPI aggregation uses weighted average: Σ(metric_i × BAC_i) / Σ(BAC_i). More accurate for project-level metrics.

11. **Time-series Data Range**: ✅ **DECIDED** - Context-dependent:
    - **Cost Element**: Zoomed to its schedule range (start_date to end_date)
    - **Project**: From project start to max(project end, control_date)
    - Ensures relevant context without excessive empty data

### 5.4 Scope Clarification

12. **Phase 2 Scope**: ✅ **DEFINED** - WBE and Project support included in current iteration:
    - Extend EVMService to calculate metrics for WBEs and projects
    - Implement aggregation logic: sum child entity metrics
    - UI components support entity type switching
    - Backend handles multi-entity queries with proper aggregation

13. **Phase 3 Deferral**: ✅ **DEFERRED** - Advanced Features moved to backlog:
    - Multi-entity comparison view (future iteration)
    - Benchmarking against historical performance (future iteration)
    - AI-powered insights (future iteration)
    - Real-time metric updates (future iteration)

### 5.5 Decision Summary Table

| Decision Area | Choice | Rationale |
|--------------|--------|-----------|
| **EVMMetric Structure** | Flat response | Type safety, backward compatibility |
| **Phase 2 Inclusion** | Included | Complete entity hierarchy support |
| **Time-series Granularity** | Server-side on-the-fly | Performance, flexibility, simpler caching |
| **Chart Zoom** | Ant Design built-in | Leverage existing library capabilities |
| **Gauge Design** | Traditional semi-circle | Industry standard, user preference |
| **Multi-entity Aggregation** | Backend | Performance, consistency, single source of truth |
| **Metric Descriptions** | Static (hardcoded) | Performance, simplicity |
| **Default Granularity** | Weekly | Balance of detail and readability |
| **Historical Data** | Empty state | Clear user feedback |
| **Index Aggregation** | Weighted by BAC | Mathematical accuracy for project metrics |
| **Time-series Range** | Context-dependent | Relevant data per entity type |
| **Phase 3** | Deferred to backlog | Focus on core functionality first |

---

## 6. Next Steps

### 6.1 Immediate Actions (Planning Phase)

**STATUS**: ✅ **ANALYSIS COMPLETE** - All user decisions recorded

1. ~~**User Confirmation**: Confirm this analysis addresses all requirements~ ✅ **COMPLETE**
2. ~~**Approach Approval**: Obtain approval for Option 2 (Phased Implementation)~ ✅ **APPROVED**
3. ~~**Clarify Open Questions**: Resolve decisions in Section 5~ ✅ **RESOLVED** (See Section 5: User Decisions)
4. **Create ADR**: Document architectural decision for generic EVM system ⏭️ **NEXT STEP**
5. **Begin Planning Phase**: Create detailed implementation plan ⏭️ **READY**

### 6.2 Planning Phase Inputs

✅ **READY FOR PLANNING** - This analysis provides:

1. **Clear Scope**: Phase 1 + Phase 2 defined with specific deliverables (Phase 3 deferred)
2. **Architecture Design**: Component structure, API contracts, data models
3. **Effort Estimates**: Task breakdown with hour estimates (55-83 hours total)
4. **Risk Register**: Identified risks with mitigations
5. **Success Criteria**: Measurable acceptance criteria for both phases
6. **Technical Decisions**: All implementation choices resolved (11 decisions recorded)
7. **User Decisions**: All open questions answered and documented

### 6.3 Dependencies

**Blocked By:**
- None ✅ **UNBLOCKED**

**Blocks:**
- WBE EVM analysis feature (included in current scope)
- Project EVM analysis feature (included in current scope)
- Multi-entity comparison dashboard (deferred to backlog)
- EVM benchmarking features (deferred to backlog)

---

## 7. Appendix

### 7.1 Metric Categorization

Per EVM requirements document, metrics organized by category:

**Schedule Metrics:**
- PV (Planned Value)
- SV (Schedule Variance)
- SPI (Schedule Performance Index)

**Cost Metrics:**
- AC (Actual Cost)
- CV (Cost Variance)
- CPI (Cost Performance Index)

**Variance Metrics:**
- CV (Cost Variance)
- SV (Schedule Variance)
- VAC (Variance at Completion)

**Performance Indices:**
- CPI (Cost Performance Index)
- SPI (Schedule Performance Index)

**Forecast Metrics:**
- EAC (Estimate at Completion)
- ETC (Estimate to Complete)
- VAC (Variance at Completion)

**Base Metrics:**
- BAC (Budget at Completion)
- PV (Planned Value)
- AC (Actual Cost)
- EV (Earned Value)

### 7.2 Existing Code References

**Backend:**
- `/home/nicola/dev/backcast_evs/backend/app/services/evm_service.py` - EVM calculation logic
- `/home/nicola/dev/backcast_evs/backend/app/models/schemas/evm.py` - EVM Pydantic schemas
- `/home/nicola/dev/backcast_evs/backend/app/api/routes/cost_elements.py:529-546` - EVM endpoint

**Frontend:**
- `/home/nicola/dev/backcast_evs/frontend/src/features/forecasts/components/ForecastComparisonCard.tsx` - Current EVM display
- `/home/nicola/dev/backcast_evs/frontend/src/features/schedule-baselines/components/ProgressionPreviewChart.tsx` - SVG chart pattern
- `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/components/SCurveComparison.tsx` - @ant-design/charts pattern
- `/home/nicola/dev/backcast_evs/frontend/src/contexts/TimeMachineContext.tsx` - Time-travel integration
- `/home/nicola/dev/backcast_evs/frontend/src/features/cost-elements/api/useCostElements.ts` - EVM data fetching

**Documentation:**
- `/home/nicola/dev/backcast_evs/docs/01-product-scope/evm-requirements.md` - EVM requirements
- `/home/nicola/dev/backcast_evs/docs/02-architecture/01-bounded-contexts.md` - Bounded contexts

### 7.3 Glossary

- **BAC**: Budget at Completion - Total planned budget
- **PV**: Planned Value - Budgeted cost of work scheduled
- **EV**: Earned Value - Budgeted cost of work performed
- **AC**: Actual Cost - Realized cost incurred
- **CV**: Cost Variance - EV - AC
- **SV**: Schedule Variance - EV - PV
- **CPI**: Cost Performance Index - EV / AC
- **SPI**: Schedule Performance Index - EV / PV
- **EAC**: Estimate at Completion - Projected total cost
- **ETC**: Estimate to Complete - EAC - AC
- **VAC**: Variance at Completion - BAC - EAC
- **Control Date**: Time-travel date for historical queries
- **Branch**: Isolated versioning context for change orders
- **Branch Mode**: ISOLATED (single branch) or MERGE (with parent branches)

---

## Analysis Sign-Off

**Analyst:** Claude (Requirements Analyst & Software Architect)
**Date:** 2026-01-22
**Status:** ✅ **ANALYSIS COMPLETE** - All user decisions recorded
**Recommendation:** Option 2 - Phased Implementation with Reusable Architecture ✅ **APPROVED**

**Decisions Made:**
- ✅ 11 technical and business decisions resolved (see Section 5)
- ✅ Phase 1 + Phase 2 included in current iteration
- ✅ Phase 3 deferred to backlog
- ✅ Implementation approach confirmed
- ✅ All open questions resolved

**Next Phase:** PLAN - Create detailed implementation plan based on these decisions

---

*This analysis document follows the PDCA methodology defined in `/home/nicola/dev/backcast_evs/docs/04-pdca-prompts/analysis-prompt.md`*
