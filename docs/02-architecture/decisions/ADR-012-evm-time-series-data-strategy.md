# ADR-012: EVM Time-Series Data Strategy

## Status
✅ Accepted (2026-01-22)

## Context

The EVM Analyzer feature requires time-series data for visualizing EVM metrics over time. Users need to see:

1. **EVM Progression Chart**: PV, EV, and AC trends over time
2. **Cost Comparison Chart**: Forecast vs. Actual cost over time
3. **Multiple Granularities**: Day, week, and month aggregation levels
4. **Time-Travel Support**: Historical views of project performance

We faced several architectural decisions:

1. **Data Storage**: Should we pre-cculate and store time-series data, or calculate on-the-fly?
2. **Caching Strategy**: How to balance freshness vs. performance?
3. **Date Range Selection**: What time range should time-series cover?
4. **Aggregation Method**: How to group data by day/week/month?

## Decision

We adopted an **on-the-fly calculation strategy** with intelligent caching and context-aware date ranges.

### 1. On-the-Fly Calculation

**Decision**: Calculate time-series data on demand without pre-storage or materialized views.

**Implementation**:
```python
async def get_evm_timeseries(
    self,
    entity_type: EntityType,
    entity_id: UUID,
    granularity: EVMTimeSeriesGranularity,
    control_date: datetime,
    branch: str,
    branch_mode: BranchMode,
) -> EVMTimeSeriesResponse:
    # 1. Determine date range based on entity context
    date_range = await self._get_timeseries_date_range(
        entity_type, entity_id, control_date
    )

    # 2. Generate date intervals at specified granularity
    dates = self._generate_date_intervals(
        date_range.start, date_range.end, granularity
    )

    # 3. Fetch all data upfront (batch query optimization)
    cost_element = await ce_service.get_as_of(entity_id, ...)
    cumulative_costs = await cr_service.get_cumulative_costs(...)
    progress_entries = await pe_service.get_progress_history(...)
    schedule_baseline = await sb_service.get_as_of(...)

    # 4. Generate time-series points in-memory
    points = await self._generate_timeseries_points(
        dates, cost_element, cumulative_costs, progress_entries, ...
    )

    return EVMTimeSeriesResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        granularity=granularity,
        points=points,
        total_points=len(points),
    )
```

**Rationale**:
- **Freshness**: Data always reflects latest cost registrations and progress entries
- **Flexibility**: Support arbitrary date ranges and granularities without schema changes
- **Simplicity**: No complex materialized view refresh logic
- **Time-travel**: Respects control_date parameter for historical views
- **Storage efficiency**: No duplicate data storage

### 2. Batch Query Optimization

**Decision**: Fetch all required data in 5 queries, then process in-memory.

**Critical Optimization**:
```python
# ❌ BEFORE: N+1 query problem (156 queries for 1-year weekly data)
for date in dates:  # 52 dates
    pv = await self._get_pv_as_of(date)       # 1 query per date
    ev = await self._get_ev_as_of_date(date)  # 1 query per date
    ac = await self._get_ac_as_of(date)       # 1 query per date
# Total: 52 × 3 = 156 queries

# ✅ AFTER: Batch queries (5 queries total)
bac = await self._get_bac_as_of(...)                           # 1 query
cumulative_costs = await cr_service.get_cumulative_costs(...) # 1 aggregated query
progress_entries = await pe_service.get_progress_history(...) # 1 query
cost_element = await ce_service.get_as_of(...)                # 1 query
schedule_baseline = await sb_service.get_as_of(...)           # 1 query

# Process in-memory (O(1) lookups)
for date in dates:
    pv = calculate_pv_deterministically(...)  # Pure calculation
    ev = lookup_from_pre_fetched_map(...)     # O(1) lookup
    ac = lookup_from_pre_fetched_map(...)     # O(1) lookup
# Total: 5 queries (96.8% reduction)
```

**Performance Impact**:
- **Query reduction**: 156 queries → 5 queries (96.8% reduction)
- **Time reduction**: ~3-5 seconds → <500ms for 1-year weekly time-series
- **Memory usage**: Minimal increase (caches cost and progress data in memory)

**Rationale**:
- **Performance**: Meets <1s performance budget for 1-year time-series
- **Scalability**: Query count independent of date range length
- **Maintainability**: Leverages existing service methods (`get_cumulative_costs`, `get_progress_history`)

### 3. Context-Aware Date Ranges

**Decision**: Date range depends on entity type and project context.

**Implementation**:
```python
async def _get_timeseries_date_range(
    self,
    entity_type: EntityType,
    entity_id: UUID,
    control_date: datetime,
) -> DateRange:
    if entity_type == EntityType.COST_ELEMENT:
        # Cost element: Use schedule baseline date range
        baseline = await sb_service.get_by_cost_element(entity_id)
        return DateRange(
            start=baseline.start_date,
            end=baseline.end_date,
        )

    elif entity_type == EntityType.WBE:
        # WBE: From earliest cost element start to latest end
        cost_elements = await ce_service.get_by_wbe_id(entity_id)
        return DateRange(
            start=min(ce.baseline.start_date for ce in cost_elements),
            end=max(ce.baseline.end_date for ce in cost_elements),
        )

    elif entity_type == EntityType.PROJECT:
        # Project: From project start to max(end_date, control_date)
        project = await project_service.get_as_of(entity_id, ...)
        return DateRange(
            start=project.start_date,
            end=max(project.target_end_date, control_date),
        )
```

**Rationale**:
- **Cost element**: Zoomed to schedule range (focused view)
- **Project**: Extends beyond project end to show actuals (complete view)
- **User experience**: Time-series always covers relevant data without manual range selection

### 4. Granularity Implementation

**Decision**: Server-side aggregation with discrete granularity levels.

**Granularity Options**:
```python
class EVMTimeSeriesGranularity(str, Enum):
    DAY = "day"    # Daily data points (for short-term projects)
    WEEK = "week"  # Weekly data points (default, balanced detail)
    MONTH = "month" # Monthly data points (for long-term projects)
```

**Date Interval Generation**:
```python
def _generate_date_intervals(
    self,
    start: datetime,
    end: datetime,
    granularity: EVMTimeSeriesGranularity,
) -> list[datetime]:
    dates = []
    current = start

    while current <= end:
        dates.append(current)

        if granularity == EVMTimeSeriesGranularity.DAY:
            current += timedelta(days=1)
        elif granularity == EVMTimeSeriesGranularity.WEEK:
            current += timedelta(weeks=1)
        elif granularity == EVMTimeSeriesGranularity.MONTH:
            # Add month, handle year boundary
            month = (current.month % 12) + 1
            year = current.year + (1 if current.month == 12 else 0)
            current = current.replace(year=year, month=month)

    return dates
```

**Period Boundaries**:
- **Daily**: 00:00:00 each day
- **Weekly**: Monday 00:00:00 (ISO week standard)
- **Monthly**: 1st 00:00:00 each month

**Rationale**:
- **Server-side control**: Frontend cannot request arbitrary granularities (performance protection)
- **Deterministic results**: Same granularity always produces same date intervals
- **ISO standards**: Weekly granularity follows ISO 8601 week standard

### 5. Caching Strategy

**Decision**: Use TanStack Query (React Query) for client-side caching with smart cache keys.

**Frontend Implementation**:
```typescript
// Cache key includes granularity for automatic invalidation
export function useEVMTimeSeries(
  entityId: string,
  entityType: EntityType,
  granularity: EVMTimeSeriesGranularity = EVMTimeSeriesGranularity.WEEK
) {
  return useQuery({
    queryKey: evmQueryKeys.timeSeries(entityType, entityId, granularity),
    queryFn: () => api.get(`/evm/${entityType}/${entityId}/timeseries`, {
      params: { granularity }
    }),
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
  });
}
```

**Cache Behavior**:
- **Automatic refetch**: Data considered stale after 5 minutes
- **Granularity changes**: Cache keys differ, so changing granularity triggers new request
- **Time-travel changes**: Cache keys include control_date, so changing date invalidates cache
- **Optimistic updates**: Cost registrations and progress entries trigger cache invalidation

**Rationale**:
- **Freshness**: 5-minute stale time ensures reasonably fresh data
- **Performance**: 10-minute cache time reduces unnecessary API calls
- **Simplicity**: No server-side caching logic required

### 6. Database Indexes

**Decision**: Add targeted indexes for time-series query patterns.

**Migration** (`f69c57fcc47d_add_indexes_for_evm_performance`):
```sql
-- Speed up AC time-series queries
CREATE INDEX ix_cost_registrations_cost_element_date
ON cost_registrations (cost_element_id, registration_date);

-- Speed up EV time-series queries
CREATE INDEX ix_progress_entries_cost_element_reported_date
ON progress_entries (cost_element_id, reported_at);

-- Speed up WBE aggregation for project time-series
CREATE INDEX ix_wbes_project_id
ON wbes (project_id);
```

**Rationale**:
- **Query patterns**: Indexes match actual query patterns (composite indexes)
- **Selective indexing**: Only add indexes for proven query patterns
- **Performance**: Indexes reduce query time for large datasets

## Consequences

### Positive

1. **Performance**: <500ms for 1-year weekly time-series (meets budget)
2. **Freshness**: Data always reflects latest cost/progress entries
3. **Flexibility**: Support arbitrary date ranges without schema changes
4. **Simplicity**: No complex materialized view refresh logic
5. **Scalability**: Batch query optimization prevents N+1 problems
6. **User Experience**: Context-aware date ranges provide relevant data automatically

### Negative

1. **CPU Usage**: On-the-fly calculation consumes CPU (mitigated by caching)
2. **Query Complexity**: Batch queries require careful optimization
3. **Memory Usage**: In-memory processing for large date ranges (acceptable for <1000 points)
4. **Cache Invalidation**: Frontend must manually invalidate on data changes

## Alternatives Considered

### Alternative 1: Materialized Views

**Decision**: Pre-calculate and store time-series data in materialized views.

**Pros**:
- **Fastest queries**: Data already aggregated
- **Predictable performance**: Query time independent of data volume

**Cons**:
- **Staleness**: Data only as fresh as last refresh
- **Complexity**: Requires refresh triggers or scheduled jobs
- **Storage**: Duplicate data storage (bloat)
- **Flexibility**: Schema changes required for new granularities
- **Time-travel**: Complex to support historical views

**Rejected**: On-the-fly calculation provides better freshness and flexibility with acceptable performance

### Alternative 2: Client-Side Aggregation

**Decision**: Return raw cost/progress data, aggregate on frontend.

**Pros**:
- **Simplest backend**: Just return raw data
- **Flexible frontend**: Client controls aggregation

**Cons**:
- **Network overhead**: Transfer all raw data (larger payloads)
- **Inconsistency risk**: Frontend implementations may diverge
- **Performance**: Frontend CPU-bound for large datasets
- **Validation**: Harder to ensure correct EVM calculations

**Rejected**: Server-side aggregation ensures consistency and reduces network overhead

### Alternative 3: Fixed Date Ranges

**Decision**: Use fixed date ranges (e.g., "last 90 days", "last 12 months").

**Pros**:
- **Simpler implementation**: No context-aware logic
- **Predictable query patterns**: Easier to optimize

**Cons**:
- **Poor UX**: Users must manually select ranges
- **Missing data**: Fixed ranges may exclude relevant project data
- **Redundant requests**: Users may need multiple requests to see full picture

**Rejected**: Context-aware ranges provide better user experience

## Performance Benchmarks

**Test Scenario**: 1-year time-series with weekly granularity (52 data points)

| Metric | Before Optimization | After Optimization | Improvement |
| ------ | ------------------- | ------------------ | ----------- |
| **Database Queries** | 156 | 5 | 96.8% reduction |
| **Query Time** | ~3-5 seconds | <500ms | 6-10x faster |
| **Memory Usage** | Baseline | +2-3 MB | Acceptable |
| **CPU Usage** | High (many queries) | Moderate (in-memory) | Acceptable |

**Performance Budgets**:
- ✅ Time-series queries: <1s for 1-year range (achieved <500ms)
- ✅ Summary view render: <500ms (achieved)
- ✅ Modal with charts render: <2s (achieved)

## Implementation Notes

### Backend Implementation

**Service Layer** (`backend/app/services/evm_service.py`):
- `get_evm_timeseries()`: Main entry point
- `_generate_timeseries_points()`: In-memory data point generation
- `_generate_date_intervals()`: Date interval creation
- `_get_timeseries_date_range()`: Context-aware range selection
- `@log_performance`: Decorator logs execution time and warns on budget overruns

**API Routes** (`backend/app/api/routes/evm.py`):
- `GET /api/v1/evm/{entity_type}/{entity_id}/timeseries`
- Query parameters: `granularity` (day/week/month), `control_date`, `branch`, `branch_mode`

### Frontend Implementation

**Component** (`frontend/src/features/evm/components/EVMTimeSeriesChart.tsx`):
- Two separate charts: EVM Progression (PV/EV/AC) and Cost Comparison (Forecast/Actual)
- Granularity selector with Day/Week/Month options
- Uses Ant Design built-in zoom (brush-x interaction)

**Hook** (`frontend/src/features/evm/api/hooks.ts`):
```typescript
export function useEVMTimeSeries(
  entityId: string,
  entityType: EntityType,
  granularity: EVMTimeSeriesGranularity = EVMTimeSeriesGranularity.WEEK
) {
  return useQuery({
    queryKey: evmQueryKeys.timeSeries(entityType, entityId, granularity),
    queryFn: () => api.get(`/evm/${entityType}/${entityId}/timeseries`, {
      params: { granularity }
    }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
```

## Future Enhancements

### Potential Optimizations (If Needed):

1. **Redis Caching**: Cache time-series results server-side for 5-15 minutes
   - **Trigger**: If API load increases significantly
   - **Trade-off**: Slight staleness for reduced CPU usage

2. **Incremental Updates**: Only calculate new data points since last calculation
   - **Trigger**: If time-series queries exceed 1s budget
   - **Trade-off**: Complexity vs. performance

3. **Data Point Reduction**: Limit maximum points (e.g., 100 points max)
   - **Trigger**: If date ranges exceed 2-3 years
   - **Trade-off**: Reduced detail for longer ranges

### Monitoring:

- **Performance logging**: `@log_performance` decorator tracks query times
- **Budget warnings**: Logs warnings when operations exceed budgets
- **Query analysis**: Use `EXPLAIN ANALYZE` to verify index usage

## References

- [ADR-011: Generic EVM Metric System](./ADR-011-generic-evm-metric-system.md) - EVM aggregation strategy
- [EVM Calculation Guide](../evm-calculation-guide.md) - EVM formulas and time-series usage
- [Performance Optimization Session](../../03-project-plan/iterations/2026-01-22-evm-analyzer-master-detail-ui/02-do.md#2026-01-22-session-10---be-fe-001-performance-optimization-and-profiling) - Detailed optimization analysis

## Review Date

2026-04-01 (reassess after 3 months of production use, consider Redis caching if needed)
