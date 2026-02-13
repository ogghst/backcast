# Phase 3: Impact Analysis - ANALYSIS

**Date Created:** 2026-01-14
**Epic:** E006 (Branching & Change Order Management)
**Phase:** 3 of 4 - Impact Analysis & Comparison
**Status:** Analysis Phase
**Related Docs:**

- [Change Management User Stories](../../../../01-product-scope/change-management-user-stories.md)
- [EVM Requirements](../../../../01-product-scope/evm-requirements.md)
- [Overall Analysis](../00-analysis.md)
- [Phase 1 ACT](../phase1/04-act.md)
- [Phase 2 ACT](../phase2/04-act.md)

---

## Executive Summary

Phase 3 implements **E06-U04: Compare Branch to Main** - the Impact Analysis capability that enables stakeholders to visually compare the proposed Change Order against the current Main Branch before approval. This is a critical decision-support feature in the Change Management workflow.

**Key User Story:** 3.4 Reviewing Change Impacts (Impact Analysis)
> **As a** Project Controller
> **I want to** visually compare the proposed Change Order against the current Main Branch using interactive charts
> **So that** I can instantly spot deviations in Cash Flow, Profitability, and Schedule before approval.

**Estimated Story Points:** 8 points
**Approach:** ✅ **Option 1: API-First Impact Analysis** (Confirmed)
**Status:** Requirements clarified, ready for planning phase

**Confirmed Decisions:**

- ✅ Option 1 (API-First) confirmed
- ✅ EVM metrics deferred to Sprint 8
- ✅ Time-series granularity: Weekly
- ✅ Entity diff: Financial fields only
- ✅ Caching strategy: React Query with 5-minute stale time (see section 7.4)

---

## 1. Request Analysis: Implement Change Order Impact Analysis

### 1.1 Clarified Requirements

The system must provide **visual impact analysis** comparing a Change Order branch to the main branch, including:

1. **KPI Scorecards**: Side-by-side metric comparison

   **Phase 3 Scope (Financial Impact Analysis):**
   - Total Budget (BAC) - Budget at Completion
   - Budget Delta - Difference between branches
   - Gross Margin - Project-level margin comparison

   **Deferred to Sprint 8 (EVM Metrics):**
   - Estimate at Completion (EAC)
   - Cost Performance Index (CPI)
   - Schedule Performance Index (SPI)
   - Planned Value (PV), Earned Value (EV), Actual Cost (AC)

2. **Delta Waterfall Chart**: Cost bridge visualization
   - Current Margin → Cost Changes → New Margin
   - Breakdown by WBE/Cost Element

3. **Time-Phased S-Curves**: Budget/Schedule comparison
   - **Weekly granularity** (confirmed)
   - Main Branch Budget (solid line)
   - Change Branch Budget (dashed line)
   - Overlay visualization

4. **Entity Impact Grid**: Data table of changes
   - Modified WBEs/Cost Elements
   - Added/Removed entities
   - **Financial fields only** - budget_allocation, revenue_allocation, cost

**Key Assumptions:**

- ✅ Phase 1 complete: Change Order CRUD + Auto-branch creation
- ✅ Phase 2 complete: Branch management + In-branch editing
- ✅ Workflow UI complete: Status transitions + Branch locking
- EVM calculations deferred to Sprint 8 - Phase 3 focuses on basic financial comparison (budget, margin)
- Recharts library already available in frontend
- Impact analysis API will compute basic KPIs (BAC, margin) without full EVM calculations

---

## 2. Context Discovery Findings

### 2.1 Product Scope

**Relevant User Story:** [3.4 Reviewing Change Impacts](../../../../01-product-scope/change-management-user-stories.md#34-reviewing-change-impacts-impact-analysis)

**Key Requirements:**

| Capability | Description | Priority | Sprint |
|-----------|-------------|----------|--------|
| **KPI Comparison (Phase 3)** | Side-by-side BAC, Budget Delta, Margin | Critical | Phase 3 |
| **Waterfall Chart** | Cost bridge from current to proposed state | Critical | Phase 3 |
| **S-Curve Overlay** | Budget comparison between branches (weekly) | High | Phase 3 |
| **Entity Grid (Financial)** | List of modified/added/removed with financial fields only | High | Phase 3 |
| **EVM Metrics (Sprint 8)** | EAC, CPI, SPI, PV, EV, AC (deferred) | Critical | Sprint 8 |
| **Interactive Hover** | Expand bars to show contributing elements | Medium | Phase 3 |

**Phase 3 Financial Metrics (Basic):**

- **BAC** (Budget at Completion): Sum of all WBE budget_allocation
- **Budget Delta**: Difference in total budget between branches
- **Gross Margin**: Project-level margin (revenue - cost)

**Sprint 8 EVM Metrics (Deferred):**

- **EAC** (Estimate at Completion): Expected total cost
- **CPI** (Cost Performance Index): EV / AC
- **SPI** (Schedule Performance Index): EV / PV
- **CV** (Cost Variance): EV - AC
- **SV** (Schedule Variance): EV - PV
- **PV** (Planned Value): Budgeted cost of work scheduled
- **EV** (Earned Value): Budgeted cost of work performed
- **AC** (Actual Cost): Realized cost incurred

### 2.2 Architecture Context

**Bounded Contexts Involved:**

1. **E006 (Branching & Change Order Management)** - Primary context
2. **E004 (Project Structure Management)** - Projects, WBEs, Cost Elements
3. **E008 (EVM Calculations & Reporting)** - Metrics computation

**Existing Patterns to Leverage:**

- **BranchableService[T]**: Already supports branch-aware queries
- **TemporalService[T]**: Already supports time-travel queries
- **BranchMode.MERGE**: Already combines main + branch data
- **React Query**: Already used for API data fetching

### 2.3 Codebase Analysis

#### Backend - Existing Infrastructure

**Available APIs:**

| Endpoint | File | Capability | Status |
|----------|------|------------|--------|
| `GET /api/v1/change-orders/{id}` | [change_orders.py](../../../../backend/app/api/routes/change_orders.py:157) | Get CO by ID | ✅ Complete |
| `GET /api/v1/projects` | [projects.py](../../../../backend/app/api/routes/projects.py) | List projects with branch/mode | ✅ Complete |
| `GET /api/v1/wbes` | [wbes.py](../../../../backend/app/api/routes/wbes.py) | List WBEs with branch/mode | ✅ Complete |
| `GET /api/v1/cost-elements` | [cost_elements.py](../../../../backend/app/api/routes/cost_elements.py) | List Cost Elements with branch/mode | ✅ Complete |

**Key Observation:** All entity endpoints already support:

- `branch` parameter (for branch isolation)
- `mode` parameter (MERGE vs STRICT)
- `as_of` parameter (time travel)

**Services Available:**

| Service | File | Methods |
|---------|------|---------|
| `ProjectService` | [services/project.py](../../../../backend/app/services/project.py) | `get_projects()` with branch/mode |
| `ChangeOrderService` | [services/change_order_service.py](../../../../backend/app/services/change_order_service.py) | `get_current()`, `get_current_by_code()` |
| `BranchService` | [services/branch_service.py](../../../../backend/app/services/branch_service.py) | `get_by_name_and_project()` |

**Models Available:**

| Model | File | Key Fields |
|-------|------|------------|
| `Project` | [models/domain/project.py](../../../../backend/app/models/domain/project.py) | `project_id`, `code`, `name`, `budget`, `status` |
| `WBE` | [models/domain/wbe.py](../../../../backend/app/models/domain/wbe.py) | `wbe_id`, `code`, `name`, `budget_allocation`, `parent_wbe_id` |
| `ChangeOrder` | [models/domain/change_order.py](../../../../backend/app/models/domain/change_order.py) | `change_order_id`, `code`, `branch_name`, `status` |

#### Frontend - Existing Infrastructure

**Chart Libraries Available:**

- ✅ **Recharts** (^2.15.0) - Declarative React charting library
- ✅ **@ant-design/charts** (latest) - Additional chart components

**UI Components Available:**

| Component | File | Reusability |
|-----------|------|-------------|
| `BranchSelector` | [components/time-machine/BranchSelector.tsx](../../../../frontend/src/components/time-machine/BranchSelector.tsx) | High - use as-is |
| `ViewModeSelector` | [components/time-machine/ViewModeSelector.tsx](../../../../frontend/src/components/time-machine/ViewModeSelector.tsx) | High - use as-is |
| `StandardTable` | [components/common/StandardTable.tsx](../../../../frontend/src/components/common/StandardTable.tsx) | High - for Entity Grid |
| `ChangeOrderModal` | [features/change-orders/components/ChangeOrderModal.tsx](../../../../frontend/src/features/change-orders/components/ChangeOrderModal.tsx) | Medium - reference for CO forms |

**State Management:**

- **Server State**: TanStack Query (already in use)
- **Time Machine Context**: `useTimeMachineParams()` already provides branch/mode/as_of
- **Routing**: React Router v6 (need to add `/change-orders/:id/impact` route)

**React Query Hooks Available:**

| Hook | File | Capability |
|------|------|------------|
| `useChangeOrders()` | [features/change-orders/api/useChangeOrders.ts](../../../../frontend/src/features/change-orders/api/useChangeOrders.ts) | CRUD operations |
| `useProjects()` | [features/projects/api/useProjects.ts](../../../../frontend/src/features/projects/api/useProjects.ts) | List with branch/mode |
| `useWBEs()` | [features/wbes/api/useWBEs.ts](../../../../frontend/src/features/wbes/api/useWBEs.ts) | List with branch/mode |
| `useCostElements()` | [features/cost-elements/api/useCostElements.ts](../../../../frontend/src/features/cost-elements/api/useCostElements.ts) | List with branch/mode |

---

## 3. Solution Options

### Option 1: API-First Impact Analysis (Recommended)

**Architecture & Design:**

- **Backend**: Create dedicated `/api/v1/change-orders/{id}/impact` endpoint
- **Frontend**: Single-page Impact Dashboard consuming the impact API
- **Calculations**: Backend performs all diff calculations and metric aggregations

**Component Structure:**

```
Backend:
- app/api/routes/change_orders.py
  - Add GET /{change_order_id}/impact endpoint
- app/services/impact_analysis_service.py (new)
  - compare_branches() -> ImpactAnalysisReport
  - calculate_kpi_delta() -> KPIScorecard
  - calculate_entity_changes() -> EntityDiff[]
- app/models/schemas/impact_analysis.py (new)
  - ImpactAnalysisResponse (root schema)
  - KPIScorecard, EntityChange, WaterfallSegment

Frontend:
- src/features/change-orders/
  - components/ImpactAnalysisDashboard.tsx (new)
  - components/KPICards.tsx (new)
  - components/WaterfallChart.tsx (new)
  - components/SCurveComparison.tsx (new)
  - components/EntityImpactGrid.tsx (new)
  - hooks/useImpactAnalysis.ts (new)
```

**API Response Structure:**

```python
class ImpactAnalysisResponse(BaseModel):
    """Complete impact analysis report comparing branches."""
    change_order_id: UUID
    change_order_code: str
    source_branch: str  # e.g., "BR-CO-2026-001"
    target_branch: str  # e.g., "main"
    analyzed_at: datetime

    # KPI Comparison
    kpi_comparison: KPIScorecard

    # Financial Bridge (for waterfall chart)
    financial_bridge: list[WaterfallSegment]

    # Entity Changes
    entity_changes: EntityChanges

    # Time-series data (for S-curves)
    time_series: TimeSeriesData
```

**UX Design:**

- **Layout**: Tabbed dashboard with KPIs always visible
- **Interactions**:
  - Hover on waterfall bars expands to show contributing elements
  - Time scrubber on S-curves to see variance at specific dates
  - Click on Entity Grid rows to jump to entity detail page
- **Loading**: Skeleton screens while fetching impact data
- **Caching**: Cache impact analysis for 5 minutes (React Query)

**Implementation:**

1. **Backend Phase 1**: Create `ImpactAnalysisService` with:
   - `compare_projects()`: Fetch project metrics from both branches
   - `compare_wbes()`: Identify added/modified/removed WBEs
   - `compare_cost_elements()`: Identify cost element changes
   - `calculate_kpi_delta()`: Compute BAC, EAC, Margin deltas

2. **Backend Phase 2**: Add `/impact` endpoint to change_orders.py

3. **Frontend Phase 1**: Create Impact Dashboard layout with KPI Cards

4. **Frontend Phase 2**: Add Waterfall Chart using Recharts

5. **Frontend Phase 3**: Add S-Curve Comparison using Recharts LineChart

6. **Frontend Phase 4**: Add Entity Impact Grid with conditional formatting

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| Pros | - Single API call reduces frontend complexity<br>- Backend controls calculation logic<br>- Easier to cache and optimize<br>- Consistent with existing API patterns |
| Cons | - Backend needs to do more work<br>- Larger API response payload<br>- Need to serialize complex nested data |
| Complexity | Medium |
| Maintainability | Good |
| Performance | Good (can optimize DB queries) |

---

### Option 2: Client-Side Diff Calculation

**Architecture & Design:**

- **Backend**: No new endpoints (use existing entity list APIs)
- **Frontend**: Fetch data separately from both branches, compute diffs client-side
- **Calculations**: Frontend performs all diff logic and metric computation

**Component Structure:**

```
Frontend:
- src/features/change-orders/
  - components/ImpactAnalysisDashboard.tsx (new)
  - hooks/useBranchComparison.ts (new)
    - Fetches WBEs from main branch
    - Fetches WBEs from CO branch
    - Computes diffs client-side
  - utils/comparison.ts (new)
    - computeEntityDiffs()
    - calculateKPIDeltas()
```

**UX Design:**

- Same dashboard layout as Option 1
- **Loading**: Multiple API calls may cause staggered loading

**Implementation:**

1. Create `useBranchComparison()` hook that:
   - Calls `useWBEs({ branch: "main" })`
   - Calls `useWBEs({ branch: "BR-{code}" })`
   - Calls `useCostElements({ branch: "main" })`
   - Calls `useCostElements({ branch: "BR-{code}" })`
   - Merges results and computes diffs in useEffect

2. Create dashboard components consuming the comparison data

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| Pros | - No backend changes required<br>- Frontend has full control over diff logic<br>- Can incrementally load data |
| Cons | - Multiple API calls (4x round trips)<br>- Diff logic duplicated on client<br>- Performance impact for large projects<br>- Harder to cache comprehensive results |
| Complexity | Low (backend), High (frontend) |
| Maintainability | Fair (frontend complexity) |
| Performance | Poor (multiple round trips) |

---

### Option 3: Hybrid Approach (Incremental)

**Architecture & Design:**

- **Backend Phase 1**: Add `/impact` endpoint with KPI comparison only
- **Backend Phase 2**: Extend endpoint with entity diff data
- **Frontend**: Start with KPI cards, add charts incrementally

**Implementation:**

1. **Sprint 1**: Backend KPI endpoint + Frontend KPI Cards
2. **Sprint 2**: Add waterfall chart + financial bridge data
3. **Sprint 3**: Add S-curves + time-series data
4. **Sprint 4**: Add entity grid + detailed diff data

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| Pros | - Early value delivery<br>- Lower risk per sprint<br>- Easier to adjust based on feedback |
| Cons | - More backend iterations<br>- API may be unstable during development<br>- Longer total timeline |
| Complexity | Medium |
| Maintainability | Good |
| Performance | Good (incremental optimization) |

---

## 4. Comparison Summary

| Criteria | Option 1: API-First | Option 2: Client-Side | Option 3: Hybrid |
|----------|---------------------|----------------------|------------------|
| Development Effort | ~8 pts (1 sprint) | ~10 pts (1-2 sprints) | ~8 pts (2 sprints) |
| Time to First Value | Sprint 1 (KPI + basic dashboard) | Sprint 1 (basic comparison) | Sprint 1 (KPI only) |
| Backend Changes | New endpoint + service | None | Incremental endpoint |
| Frontend Complexity | Medium (data visualization) | High (diff logic + visualization) | Low → Medium |
| API Performance | 1 call, ~200-500ms response | 4+ parallel calls | 1 call initially |
| Scalability | Good (backend can optimize) | Poor (client-bound) | Good |
| Cacheability | Excellent (single endpoint) | Fair (multiple endpoints) | Excellent |
| Best For | Production-grade feature | Quick prototype/MVP | Incremental delivery |

---

## 5. Recommendation

**I recommend Option 1: API-First Impact Analysis** for the following reasons:

1. **Proven Pattern**: All existing features use backend-first approach (Phase 1, Phase 2, Workflow UI)
2. **Performance**: Single API call is more efficient than 4+ parallel calls
3. **Consistency**: Aligns with existing API architecture and RBAC patterns
4. **Scalability**: Backend can optimize queries and add caching layers
5. **Maintainability**: Diff logic centralized in one place (service layer)
6. **Type Safety**: Pydantic → TypeScript generation ensures end-to-end type safety

**Alternative consideration:** Choose **Option 2** if:

- Quick proof-of-concept needed for stakeholder validation
- Backend team capacity is limited
- Willing to accept performance trade-offs

---

## 6. Detailed Design (Option 1 - API-First)

### 6.1 Backend Schema Design

**New Schema: `app/models/schemas/impact_analysis.py`**

```python
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class KPIMetric(BaseModel):
    """Single KPI value with delta."""
    main_value: Decimal | None
    branch_value: Decimal | None
    delta: Decimal | None
    delta_percent: float | None
    is_favorable: bool | None  # True if positive change


class KPIScorecard(BaseModel):
    """KPI comparison between branches."""
    bac: KPIMetric  # Budget at Completion
    eac: KPIMetric  # Estimate at Completion
    gross_margin: KPIMetric
    cpi: KPIMetric  # Cost Performance Index
    spi: KPIMetric  # Schedule Performance Index


class EntityChangeType(str):
    """Type of entity change."""
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"


class EntityChange(BaseModel):
    """Single entity change."""
    entity_type: str  # "wbe" or "cost_element"
    entity_id: UUID
    entity_code: str
    entity_name: str
    change_type: EntityChangeType
    field_changes: dict[str, Any] | None  # For modified: field -> {old, new}
    budget_delta: Decimal | None


class EntityChanges(BaseModel):
    """Collection of entity changes."""
    wbes: list[EntityChange]
    cost_elements: list[EntityChange]
    total_added: int
    total_modified: int
    total_removed: int


class WaterfallSegment(BaseModel):
    """Single segment in waterfall chart."""
    label: str
    value: Decimal
    color: str  # Hex color for chart


class TimeSeriesPoint(BaseModel):
    """Single point in time series."""
    date: datetime
    main_value: Decimal
    branch_value: Decimal


class TimeSeriesData(BaseModel):
    """Time-series data for S-curves."""
    points: list[TimeSeriesPoint]


class ImpactAnalysisResponse(BaseModel):
    """Complete impact analysis report."""
    change_order_id: UUID
    change_order_code: str
    project_id: UUID
    project_code: str
    source_branch: str
    target_branch: str
    analyzed_at: datetime

    kpi_comparison: KPIScorecard
    financial_bridge: list[WaterfallSegment]
    entity_changes: EntityChanges
    time_series: TimeSeriesData | None = Field(default=None)
```

### 6.2 Backend Service Design

**New Service: `app/services/impact_analysis_service.py`**

```python
"""Impact Analysis Service for Change Order comparison."""

from decimal import Decimal
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.impact_analysis import (
    ImpactAnalysisResponse,
    KPIScorecard,
    EntityChanges,
    WaterfallSegment,
)


class ImpactAnalysisService:
    """Service for performing impact analysis between branches."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def analyze_impact(
        self,
        change_order_id: UUID,
        target_branch: str = "main",
    ) -> ImpactAnalysisResponse:
        """Perform complete impact analysis for a Change Order.

        Args:
            change_order_id: The Change Order to analyze
            target_branch: Branch to compare against (default: "main")

        Returns:
            Complete impact analysis report
        """
        # 1. Get Change Order metadata
        co = await self._get_change_order(change_order_id)
        source_branch = co.branch_name

        # 2. Compare KPIs
        kpi_comparison = await self._compare_kpis(
            project_id=co.project_id,
            source_branch=source_branch,
            target_branch=target_branch,
        )

        # 3. Identify entity changes
        entity_changes = await self._compare_entities(
            project_id=co.project_id,
            source_branch=source_branch,
            target_branch=target_branch,
        )

        # 4. Build financial bridge (waterfall)
        financial_bridge = self._build_waterfall(
            kpi_comparison=kpi_comparison,
            entity_changes=entity_changes,
        )

        # 5. Generate time-series data (S-curves)
        time_series = await self._generate_time_series(
            project_id=co.project_id,
            source_branch=source_branch,
            target_branch=target_branch,
        )

        return ImpactAnalysisResponse(
            change_order_id=co.change_order_id,
            change_order_code=co.code,
            project_id=co.project_id,
            project_code=co.project.code,
            source_branch=source_branch,
            target_branch=target_branch,
            analyzed_at=datetime.utcnow(),
            kpi_comparison=kpi_comparison,
            financial_bridge=financial_bridge,
            entity_changes=entity_changes,
            time_series=time_series,
        )

    async def _compare_kpis(
        self,
        project_id: UUID,
        source_branch: str,
        target_branch: str,
    ) -> KPIScorecard:
        """Compare KPIs between branches."""
        # Fetch project data from both branches
        # Calculate BAC, EAC, Margin, CPI, SPI
        # Return KPIScorecard with deltas
        pass

    async def _compare_entities(
        self,
        project_id: UUID,
        source_branch: str,
        target_branch: str,
    ) -> EntityChanges:
        """Compare entities between branches.

        Identifies WBEs and Cost Elements that are:
        - Added (exist in source, not in target)
        - Removed (exist in target, not in source)
        - Modified (exist in both with different values)
        """
        pass

    def _build_waterfall(
        self,
        kpi_comparison: KPIScorecard,
        entity_changes: EntityChanges,
    ) -> list[WaterfallSegment]:
        """Build waterfall chart segments."""
        # Start with current margin
        # Add cost increases/decreases by category
        # End with new margin
        pass

    async def _generate_time_series(
        self,
        project_id: UUID,
        source_branch: str,
        target_branch: str,
    ) -> list[TimeSeriesPoint]:
        """Generate time-series data for S-curves."""
        # Generate monthly PV points for both branches
        # Return combined time series
        pass
```

### 6.3 Frontend Component Design

**New Route:** `/change-orders/:changeOrderId/impact`

**Component Structure:**

```
src/features/change-orders/
├── components/
│   ├── impact/
│   │   ├── ImpactAnalysisDashboard.tsx     (main container)
│   │   ├── KPICards.tsx                     (KPI comparison)
│   │   ├── WaterfallChart.tsx               (cost bridge)
│   │   ├── SCurveComparison.tsx             (PV overlay)
│   │   └── EntityImpactGrid.tsx            (entity diff table)
├── hooks/
│   └── useImpactAnalysis.ts                (API hook)
└── types/
    └── impact.ts                           (TypeScript types)
```

**Key Component: `ImpactAnalysisDashboard.tsx`**

```typescript
interface ImpactAnalysisDashboardProps {
  changeOrderId: string;
}

export const ImpactAnalysisDashboard: React.FC<ImpactAnalysisDashboardProps> = ({
  changeOrderId,
}) => {
  const { data: impact, isLoading, error } = useImpactAnalysis(changeOrderId);

  if (isLoading) return <ImpactAnalysisSkeleton />;
  if (error) return <ErrorMessage error={error} />;
  if (!impact) return <EmptyState />;

  return (
    <div className="impact-dashboard">
      {/* Header */}
      <DashboardHeader impact={impact} />

      {/* KPI Cards - Always visible */}
      <KPICards kpiComparison={impact.kpi_comparison} />

      {/* Tabs for detailed views */}
      <Tabs defaultActiveKey="waterfall">
        <TabPane tab="Financial Impact" key="waterfall">
          <WaterfallChart segments={impact.financial_bridge} />
        </TabPane>
        <TabPane tab="Schedule Comparison" key="scurve">
          <SCurveComparison timeSeries={impact.time_series} />
        </TabPane>
        <TabPane tab="Entity Changes" key="entities">
          <EntityImpactGrid changes={impact.entity_changes} />
        </TabPane>
      </Tabs>
    </div>
  );
};
```

**Key Hook: `useImpactAnalysis.ts`**

```typescript
export const useImpactAnalysis = (changeOrderId: string) => {
  return useQuery({
    queryKey: ["impact-analysis", changeOrderId],
    queryFn: () =>
      fetchImpactAnalysis(changeOrderId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
```

### 6.4 Visualization Components

**KPICards.tsx:**

```typescript
interface KPICardsProps {
  kpiComparison: KPIScorecard;
}

export const KPICards: React.FC<KPICardsProps> = ({ kpiComparison }) => {
  const kpis = [
    { label: "BAC", value: kpiComparison.bac },
    { label: "EAC", value: kpiComparison.eac },
    { label: "Gross Margin", value: kpi_comparison.gross_margin },
    { label: "CPI", value: kpiComparison.cpi },
    { label: "SPI", value: kpiComparison.spi },
  ];

  return (
    <Row gutter={16}>
      {kpis.map((kpi) => (
        <Col span={4} key={kpi.label}>
          <Card>
            <Statistic
              title={kpi.label}
              value={kpi.value.branch_value ?? kpi.value.main_value}
              precision={2}
              valueStyle={{
                color: kpi.value.is_favorable ? "#3f8600" : "#cf1322",
              }}
              suffix={
                kpi.value.delta !== null && (
                  <span
                    style={{
                      fontSize: "14px",
                      marginLeft: 8,
                    }}
                  >
                    {kpi.value.is_favorable ? "↑" : "↓"}{" "}
                    {Math.abs(kpi.value.delta_percent ?? 0).toFixed(1)}%
                  </span>
                )
              }
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
};
```

**WaterfallChart.tsx (using Recharts):**

```typescript
interface WaterfallChartProps {
  segments: WaterfallSegment[];
}

export const WaterfallChart: React.FC<WaterfallChartProps> = ({ segments }) => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={segments}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="label" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="value" fill={segments[0]?.color} />
      </BarChart>
    </ResponsiveContainer>
  );
};
```

**SCurveComparison.tsx (using Recharts):**

```typescript
interface SCurveComparisonProps {
  timeSeries: TimeSeriesData;
}

export const SCurveComparison: React.FC<SCurveComparisonProps> = ({
  timeSeries,
}) => {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={timeSeries.points}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="date"
          tickFormatter={(value) => dayjs(value).format("MMM YYYY")}
        />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line
          type="monotone"
          dataKey="main_value"
          stroke="#8884d8"
          name="Main Branch PV"
          strokeWidth={2}
        />
        <Line
          type="monotone"
          dataKey="branch_value"
          stroke="#82ca9d"
          name="Change Branch PV"
          strokeWidth={2}
          strokeDasharray="5 5"
        />
      </LineChart>
    </ResponsiveContainer>
  );
};
```

---

## 7. Confirmed Decisions & Technical Analysis

### 7.1 Option 1: API-First Impact Analysis ✅ CONFIRMED

**Decision:** Use Option 1 (API-First approach)

**Rationale:**

1. **Proven Pattern** - All existing features (Phase 1, Phase 2, Workflow UI) use backend-first approach
2. **Performance** - Single API call is more efficient than 4+ parallel calls
3. **Consistency** - Aligns with existing API architecture and RBAC patterns
4. **Scalability** - Backend can optimize queries and add caching layers
5. **Maintainability** - Diff logic centralized in service layer
6. **Type Safety** - Pydantic → TypeScript generation ensures end-to-end type safety

---

### 7.2 EVM Metrics Scope ✅ DEFERRED TO SPRINT 8

**Decision:** EVM calculations (EAC, CPI, SPI, PV, EV, AC) deferred to Sprint 8

**Phase 3 Scope:**

| Metric | Description | Calculation |
|--------|-------------|-------------|
| **BAC** | Budget at Completion | Sum of all WBE `budget_allocation` |
| **Budget Delta** | Budget difference | `branch_budget - main_budget` |
| **Gross Margin** | Project margin | `revenue - cost` |

**Sprint 8 Scope (EVM Metrics):**

| Metric | Description | Calculation |
|--------|-------------|-------------|
| **EAC** | Estimate at Completion | From forecasts |
| **CPI** | Cost Performance Index | `EV / AC` |
| **SPI** | Schedule Performance Index | `EV / PV` |
| **PV** | Planned Value | Based on schedule baselines |
| **EV** | Earned Value | `BAC × % complete` |
| **AC** | Actual Cost | Sum of cost registrations |
| **CV** | Cost Variance | `EV - AC` |
| **SV** | Schedule Variance | `EV - PV` |

**Rationale:** Phase 3 focuses on branch comparison infrastructure (UI, API, diff logic). Sprint 8 will implement full EVM calculation service that Phase 3 can then leverage.

---

### 7.3 Time-Series Granularity ✅ WEEKLY

**Decision:** Weekly granularity for S-curves

**Trade-offs:**

| Aspect | Weekly | Monthly |
|--------|--------|---------|
| Data Points | ~52 points/year | ~12 points/year |
| Curve Smoothness | Smoother, more detailed | Coarser, less detailed |
| Query Performance | Slower (more data) | Faster (less data) |
| Storage | Higher | Lower |
| User Experience | Better for detailed analysis | Sufficient for high-level view |

**Rationale:** Weekly granularity provides better visualization without significant performance impact. Users can always aggregate to monthly view on the frontend if needed.

---

### 7.4 Entity Diff Detail Level ✅ FINANCIAL FIELDS ONLY

**Decision:** Show only financial fields in Entity Impact Grid

**Fields to Include:**

| Entity | Fields to Compare |
|--------|-------------------|
| **WBE** | `budget_allocation`, `revenue_allocation` |
| **CostElement** | `budgeted_cost`, `estimated_cost` |
| **Project** | `budget`, `revenue` |

**Fields Excluded:**

- `code`, `name`, `description` (identity fields)
- `status`, `level` (metadata fields)
- `created_at`, `updated_at` (timestamps)

**Rationale:** Financial impact is the primary concern for change order analysis. Identity field changes (e.g., renaming a WBE) don't affect the project's financial outcome.

---

### 7.5 Caching Strategy Analysis ✅ REACT QUERY WITH STALE TIME

**Decision:** Use React Query with 5-minute stale time

**Options Comparison:**

| Strategy | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Redis with TTL** | - Shared cache across users<br>- Fast response after first query<br>- Can pre-compute on CO status change | - Additional infrastructure<br>- Cache invalidation complexity<br>- Stale data if not invalidated | ❌ Not recommended for Phase 3 |
| **React Query Only** | - No backend changes<br>- Simple implementation<br>- Per-user cache isolation<br>- Automatic refetch on window focus | - Each user has separate cache<br>- First query always hits DB | ✅ **Recommended for Phase 3** |
| **Pre-compute on CO Change** | - Instant response<br>- Data always ready | - Complex invalidation logic<br>- Storage overhead<br>- May compute unused data | ❌ Over-engineering for Phase 3 |

**React Query Configuration:**

```typescript
export const useImpactAnalysis = (changeOrderId: string) => {
  return useQuery({
    queryKey: ["impact-analysis", changeOrderId],
    queryFn: () => fetchImpactAnalysis(changeOrderId),
    staleTime: 5 * 60 * 1000,  // 5 minutes
    gcTime: 10 * 60 * 1000,   // 10 minutes (formerly cacheTime)
  });
};
```

**Migration Path to Redis (if needed in Sprint 8+):**

1. Add Redis layer in backend service
2. Set cache key pattern: `impact:{change_order_id}:{project_id}`
3. Invalidate cache on CO status change (Draft → Submitted → Approved)
4. Keep React Query for client-side optimization

**Rationale:** React Query provides sufficient caching for current needs. Redis can be added later if performance metrics show DB query bottleneck.

---

## 8. Next Steps

**Analysis Complete** - All decisions confirmed. Ready for planning phase.

**Immediate Actions:**

1. ✅ **Create iteration plan** ([01-plan.md](./01-plan.md)) with detailed tasks
2. ✅ **Set up database queries** for efficient branch comparison
3. ✅ **Define API contracts** in OpenAPI spec
4. ✅ **Create frontend route** for impact dashboard
5. ✅ **Update Sprint 8** with EVM metrics scope for impact analysis enhancement

**Approval Status:** ✅ Approved (Option 1 confirmed, all decisions made)

---

## 9. Success Criteria

Phase 3 will be considered successful when:

### Backend

- ✅ `/api/v1/change-orders/{id}/impact` endpoint returns complete comparison data
- ✅ `ImpactAnalysisService` computes BAC, budget delta, and gross margin
- ✅ Entity diff identifies added/modified/removed WBEs and Cost Elements
- ✅ Financial fields only compared (`budget_allocation`, `revenue_allocation`, etc.)
- ✅ Weekly time-series data generation for S-curves
- ✅ All tests passing with 80%+ coverage

### Frontend

- ✅ Impact Analysis Dashboard displays KPI scorecards (BAC, Budget Delta, Margin)
- ✅ Waterfall chart visualizes cost bridge (current → changes → new)
- ✅ S-curves overlay budget comparison (weekly granularity)
- ✅ Entity Impact Grid lists added/modified/removed entities with financial fields only
- ✅ All tests passing with 80%+ coverage
- ✅ Zero linting errors

### Integration

- ✅ React Query caching with 5-minute stale time
- ✅ Type-safe API integration (Pydantic → TypeScript)
- ✅ Loading states and error handling
- ✅ Responsive design for mobile/tablet

### Deferred to Sprint 8

- ⏸️ EAC (Estimate at Completion) calculation
- ⏸️ CPI (Cost Performance Index) calculation
- ⏸️ SPI (Schedule Performance Index) calculation
- ⏸️ PV/EV/AC calculations for complete EVM analysis
- ⏸️ Redis caching layer (if performance metrics indicate need)

---

## 10. Dependencies & Blocking Items

### Unblocked by Previous Phases

| Phase | Delivered | Status |
|-------|-----------|--------|
| **Phase 1** | Change Order CRUD + Auto-branch creation | ✅ Complete |
| **Phase 2** | Branch management + In-branch editing | ✅ Complete |
| **Workflow UI** | Status transitions + Branch locking | ✅ Complete |

### Sprint 8 Dependency

| Dependency | Impact | Mitigation |
|------------|--------|------------|
| **EVM Calculations** | Phase 3 uses basic KPIs only; Sprint 8 will add EAC/CPI/SPI | Phase 3 infrastructure ready for Sprint 8 enhancement |

---

**Document Status:** ✅ Complete - Ready for Planning Phase
**Next Document:** [01-plan.md](./01-plan.md)
