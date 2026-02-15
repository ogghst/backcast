# Plan: Phase 7 - Change Order Dashboard & Reporting

## Purpose

Implement a comprehensive analytics and reporting dashboard for Change Orders to provide project-level visibility into cost, schedule, and risk impacts, as well as approval workflow bottlenecks.

**Analysis Reference**: `00-analysis.md` - Option 1 (Embedded Analytics Tab) selected

---

## Success Criteria

1. **Functional**:
   - Users can view aggregated Change Order statistics for a project
   - Dashboard shows total cost exposure, status breakdown, and impact level distribution
   - Trend chart displays cumulative cost impact over time
   - Aging items list highlights stuck/overdue change orders
   - Approval workload metrics show pending approvals by approver

2. **Technical**:
   - Backend provides efficient aggregation endpoints (< 500ms response time)
   - Frontend uses existing `@ant-design/charts` library (consistent with WaterfallChart)
   - All endpoints respect RBAC permissions
   - 80%+ test coverage for new code

3. **UX**:
   - Tab navigation between "List View" and "Analytics View"
   - Responsive charts with proper loading states
   - Export capability for analytics data (future enhancement)

---

## Architecture

### Backend

```
backend/app/
├── services/
│   └── change_order_reporting_service.py  (NEW)
├── api/routes/
│   └── change_orders.py                    (MODIFY - add stats endpoints)
└── models/schemas/
    └── change_order_reporting.py           (NEW - response schemas)
```

### Frontend

```
frontend/src/
├── features/change-orders/
│   ├── api/
│   │   └── useChangeOrderStats.ts          (NEW - query hook)
│   └── components/
│       ├── ChangeOrderAnalytics.tsx        (NEW - main analytics component)
│       ├── StatusDistributionChart.tsx     (NEW - bar chart by status)
│       ├── ImpactLevelChart.tsx            (NEW - pie chart by impact)
│       ├── CostTrendChart.tsx              (NEW - line chart over time)
│       ├── ApprovalWorkloadTable.tsx       (NEW - pending approvals table)
│       └── AgingItemsList.tsx              (NEW - stuck/overdue COs)
└── pages/projects/change-orders/
    └── ChangeOrderUnifiedPage.tsx          (MODIFY - add analytics tab)
```

---

## Task Dependency Graph

```
[T1] Backend: Reporting Service & Schemas
   |
   +--[T2] Backend: API Endpoints
          |
          +--[T3] Frontend: API Query Hooks
                 |
                 +--[T4] Frontend: Analytics Components
                        |
                        +--[T5] Frontend: Page Integration
                               |
                               +--[T6] Testing & Quality
```

---

## Detailed Tasks

### T1: Backend - Reporting Service & Schemas

**Estimated Time**: 3 hours
**Priority**: P0 (Blocking)

#### T1.1 Create Response Schemas

File: `backend/app/models/schemas/change_order_reporting.py`

```python
# Pydantic schemas for reporting endpoints

class ChangeOrderStatusStats(BaseModel):
    """Statistics by change order status."""
    status: str
    count: int
    total_value: Decimal | None

class ChangeOrderImpactStats(BaseModel):
    """Statistics by impact level."""
    impact_level: str
    count: int
    total_value: Decimal | None

class ChangeOrderTrendPoint(BaseModel):
    """Single point in the cost trend."""
    date: date
    cumulative_value: Decimal
    count: int

class ApprovalWorkloadItem(BaseModel):
    """Pending approval workload by approver."""
    approver_id: UUID
    approver_name: str
    pending_count: int
    overdue_count: int
    avg_days_waiting: float

class AgingChangeOrder(BaseModel):
    """Change order that is stuck or aging."""
    change_order_id: UUID
    code: str
    title: str
    status: str
    days_in_status: int
    impact_level: str | None
    sla_status: str | None

class ChangeOrderStatsResponse(BaseModel):
    """Aggregated statistics for change orders."""
    # Summary KPIs
    total_count: int
    total_cost_exposure: Decimal
    pending_value: Decimal
    approved_value: Decimal

    # Distributions
    by_status: list[ChangeOrderStatusStats]
    by_impact_level: list[ChangeOrderImpactStats]

    # Trend data
    cost_trend: list[ChangeOrderTrendPoint]

    # Approval metrics
    avg_approval_time_days: float | None
    approval_workload: list[ApprovalWorkloadItem]

    # Aging items
    aging_items: list[AgingChangeOrder]
    aging_threshold_days: int  # Config: default 7
```

#### T1.2 Create Reporting Service

File: `backend/app/services/change_order_reporting_service.py`

```python
# Service with aggregation methods:
# - get_change_order_stats(project_id, branch, as_of)
# - get_cost_trend(project_id, branch, as_of)
# - get_approval_workload(project_id, branch)
# - get_aging_items(project_id, branch, threshold_days)

# Uses SQLAlchemy aggregations:
# - func.count(), func.sum(), func.avg()
# - group_by status, impact_level
# - Date truncation for trend (by week/month)
```

**Key Implementation Details**:
- Use `func.coalesce` for NULL handling in aggregations
- Calculate cost exposure from `impact_analysis_results.budget_delta`
- Derive days_in_status from `change_order_audit_log` table
- Use CTEs for complex trend calculations

---

### T2: Backend - API Endpoints

**Estimated Time**: 2 hours
**Priority**: P0 (Depends on T1)

File: `backend/app/api/routes/change_orders.py` (MODIFY)

Add new endpoint:

```python
@router.get(
    "/stats",
    response_model=ChangeOrderStatsResponse,
    operation_id="get_change_order_stats",
    dependencies=[Depends(RoleChecker(required_permission="change-order-read"))],
)
async def get_change_order_stats(
    project_id: UUID = Query(..., description="Project ID"),
    branch: str = Query("main", description="Branch name"),
    as_of: datetime | None = Query(None, description="Time travel timestamp"),
    aging_threshold_days: int = Query(7, ge=1, le=30),
    service: ChangeOrderReportingService = Depends(get_reporting_service),
) -> ChangeOrderStatsResponse:
    """Get aggregated statistics for change orders in a project."""
    ...
```

**RBAC**: Requires `change-order-read` permission

---

### T3: Frontend - API Query Hooks

**Estimated Time**: 1.5 hours
**Priority**: P0 (Depends on T2)

File: `frontend/src/features/change-orders/api/useChangeOrderStats.ts`

```typescript
// TanStack Query hook for fetching change order statistics
// Uses generated API client types
// Implements proper caching with staleTime
// Handles error states gracefully
```

**Key Implementation**:
- Use `useQuery` with proper query key structure
- Include project_id in query key for cache isolation
- Add optimistic updates support (future)

---

### T4: Frontend - Analytics Components

**Estimated Time**: 5 hours
**Priority**: P0 (Depends on T3)

#### T4.1 StatusDistributionChart

Bar chart showing CO count by status (Draft, Submitted, Under Review, Approved, Rejected, Implemented)

#### T4.2 ImpactLevelChart

Pie/Donut chart showing distribution by impact level (LOW, MEDIUM, HIGH, CRITICAL)

#### T4.3 CostTrendChart

Line chart showing cumulative cost impact over time (monthly aggregation)

#### T4.4 ApprovalWorkloadTable

Table showing pending approvals by approver with:
- Approver name
- Pending count
- Overdue count
- Avg days waiting

#### T4.5 AgingItemsList

List/table of change orders that are:
- In "Submitted for Approval" or "Under Review" for > threshold days
- SLA overdue items
- Clickable to navigate to detail page

#### T4.6 ChangeOrderAnalytics (Main Component)

Container component that:
- Fetches stats via query hook
- Renders summary KPI cards at top
- Arranges charts in responsive grid
- Shows loading states and error handling

---

### T5: Frontend - Page Integration

**Estimated Time**: 2 hours
**Priority**: P0 (Depends on T4)

File: `frontend/src/pages/projects/change-orders/ChangeOrderUnifiedPage.tsx` (MODIFY)

Add tab switching between:
- "List View" (existing ChangeOrderList)
- "Analytics View" (new ChangeOrderAnalytics)

**Pattern**: Match existing tab patterns in `ImpactAnalysisDashboard.tsx`

---

### T6: Testing & Quality

**Estimated Time**: 3 hours
**Priority**: P1 (Final)

#### Backend Tests

- `tests/unit/services/test_change_order_reporting_service.py`
  - Test aggregation calculations
  - Test trend data generation
  - Test aging item detection
  - Test with edge cases (no COs, all approved, etc.)

- `tests/api/test_change_order_stats.py`
  - Test endpoint authentication
  - Test RBAC permissions
  - Test response schema validation

#### Frontend Tests

- `ChangeOrderAnalytics.test.tsx`
  - Test loading state
  - Test error state
  - Test chart rendering with mock data
  - Test tab switching

#### Quality Gates

- [ ] Backend: `uv run ruff check . && uv run mypy app/`
- [ ] Frontend: `npm run lint`
- [ ] Coverage: 80%+ for new files

---

## Technical Decisions

### 1. Cost Exposure Calculation

Cost exposure is derived from the `impact_analysis_results` JSONB field:

```sql
-- Extract budget_delta from impact_analysis_results
SELECT
  SUM((impact_analysis_results->'kpi_scorecard'->'budget_delta'->>'delta')::numeric)
FROM change_orders
WHERE project_id = :project_id
  AND branch = :branch
  AND deleted_at IS NULL;
```

### 2. Trend Aggregation Strategy

Use PostgreSQL `date_trunc` for weekly/monthly grouping:

```sql
SELECT
  date_trunc('week', lower(transaction_time)) as week_start,
  COUNT(*) as count,
  SUM(...) as cumulative_value
FROM change_orders
WHERE ...
GROUP BY date_trunc('week', lower(transaction_time))
ORDER BY week_start;
```

### 3. Aging Detection

Query `change_order_audit_log` to calculate days in current status:

```sql
SELECT
  co.change_order_id,
  co.code,
  EXTRACT(day FROM NOW() - audit.changed_at) as days_in_status
FROM change_orders co
JOIN change_order_audit_log audit ON ...
WHERE audit.new_status = co.status
  AND EXTRACT(day FROM NOW() - audit.changed_at) > :threshold;
```

### 4. Frontend State Management

Use existing TanStack Query patterns:
- Query key: `['change-orders', 'stats', projectId, branch]`
- Stale time: 5 minutes (analytics can be slightly stale)
- Refetch on window focus: true

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Slow aggregation queries | Add database indexes on `status`, `impact_level`, `project_id`; use query explain analyze |
| Large datasets | Implement pagination for aging items; limit trend to 12 months |
| Missing impact data | Handle NULL values gracefully; show "N/A" for items without analysis |
| Chart rendering performance | Use Ant Design Charts' built-in data sampling for large datasets |

---

## Definition of Done

- [ ] All T1-T6 tasks completed
- [ ] Backend quality gates pass (ruff, mypy, tests)
- [ ] Frontend quality gates pass (lint, tests)
- [ ] Manual testing on local environment
- [ ] Code review approved
- [ ] Documentation updated (if needed)

---

## Future Enhancements (Out of Scope)

1. **Historical Snapshots**: "What were the stats on Jan 1st?"
2. **Export to CSV/Excel**: Download analytics data
3. **Real-time Updates**: WebSocket notifications for status changes
4. **Executive Dashboard**: Cross-project aggregation
5. **BI Tool Integration**: OData/JSON export endpoints
