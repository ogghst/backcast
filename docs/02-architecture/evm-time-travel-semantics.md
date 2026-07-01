# EVM Time-Travel Semantics

**Last Updated:** 2026-07-01
**Related Iteration:** [2026-01-22-evm-analyzer-master-detail-ui](../../03-project-plan/iterations/2026-01-22-evm-analyzer-master-detail-ui/)

---

## Overview

The EVM system supports **Valid Time Travel** queries, allowing you to retrieve EVM metrics as they were at any point in the past. This is enabled by the bitemporal versioning system, which tracks both **valid time** (business time) and **transaction time** (system time) for all versioned entities.

---

## Bitemporal Versioning Basics

### Two Time Dimensions

| Dimension | Description | Example |
|-----------|-------------|---------|
| **Valid Time** | When the fact was true in the real world | Budget effective from Jan 1 to Dec 31, 2026 |
| **Transaction Time** | When the fact was recorded in the system | Budget created on Dec 15, 2025 |

### Key Concepts

**Versioned Entities:**

- Cost Elements, WBEs, Projects, Schedule Baselines
- Have `valid_time` (TSTZRANGE) and `transaction_time` (TSTZRANGE)
- Support time-travel queries via `get_as_of(id, control_date)` methods

**Non-Versioned Entities (also bitemporally time-traveled):**

- Cost Registrations, Progress Entries, Forecasts
- Not EVCS-versioned (no `branch`, no version rows), but they do carry a `valid_time` range
- **Time-traveled via `valid_time`**: AC and EV honor `control_date` through `_apply_bitemporal_filter` on these tables (see `cost_registration_service.get_total_for_work_package(..., as_of)` and `progress_entry_service.get_latest_progress(..., as_of)`). They are *not* branched (shared across change-order branches), but they *are* point-in-time filtered.

---

## Valid Time Travel Semantics

### How It Works

When you specify a `control_date` in an EVM query:

1. **Versioned entities** (BAC, PV) are fetched as they were at `control_date` (Valid Time Travel)
2. **AC / EV** are computed point-in-time as of `control_date`: Actual Cost sums `CostRegistration` rows whose `valid_time` contains `control_date` (`_apply_bitemporal_filter`), and Earned Value uses the latest `ProgressEntry` valid as of `control_date`. These tables are not branched, but they *are* bitemporally filtered.
3. EVM metrics are calculated from the combination of both

### Example Scenario

```
Timeline:
- Dec 1, 2025: Cost element created with BAC = €100,000
- Jan 1, 2026: Cost registrations begin
- Jan 15, 2026: Progress updated to 50%
- Feb 1, 2026: Budget increased to €120,000
```

**Query at control_date = Jan 15, 2026:**

```json
{
  "bac": "100000.00",  // BAC as of Jan 15 (before increase)
  "ac": "30000.00",    // AC as of Jan 15 (cost registrations valid at control_date)
  "ev": "50000.00",    // EV = BAC × 50% (progress valid as of Jan 15)
  "control_date": "2026-01-15T00:00:00Z"
}
```

**Query at control_date = Feb 15, 2026:**

```json
{
  "bac": "120000.00",  // BAC as of Feb 15 (after increase)
  "ac": "30000.00",    // AC as of Feb 15 (cost registrations valid at control_date)
  "ev": "60000.00",    // EV = BAC × 50% (progress valid as of Feb 15)
  "control_date": "2026-02-15T00:00:00Z"
}
```

---

## EVM Query Parameters

### control_date

**Description:** Control date for Valid Time Travel query (ISO 8601 format)

**Default:** Current datetime (`datetime.now(tz=UTC)`)

**Behavior:**

- **Versioned entities**: Fetched as they were at `control_date`
- **AC / EV**: Computed from `CostRegistration` / `ProgressEntry` rows whose `valid_time` contains `control_date` (bitemporally filtered, not branched)

**Example:**

```bash
# Get EVM metrics as of January 1, 2026
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2026-01-01T00:00:00Z

# Get EVM metrics as of current time (default)
GET /api/v1/evm/cost_element/{id}/metrics
```

### branch

**Description:** Branch name to query

**Default:** `"main"`

**Behavior:**

- Fetches versioned entities from the specified branch
- Cost registrations and progress entries are **not branched** (shared across branches) but are still bitemporally filtered by `control_date`

**Example:**

```bash
# Get EVM for main branch
GET /api/v1/evm/cost_element/{id}/metrics?branch=main

# Get EVM for change order branch
GET /api/v1/evm/cost_element/{id}/metrics?branch=BR-001-feature-addition
```

### branch_mode

**Description:** Branch isolation mode

**Values** (see `BranchMode` enum in `backend/app/core/versioning/enums.py`):

- `"merged"` (default): Fall back to the main branch if the entity is not in the current branch
- `"isolated"`: Only query the current branch, no fallback

**Behavior:**

| Mode | Entity Found in Branch | Entity Not Found in Branch |
|------|------------------------|----------------------------|
| `merged` | Return entity | Fall back to main branch |
| `isolated` | Return entity | Return 404 Not Found |

> **Note:** The frontend (`TimeMachineContext`) sends the value as `tmMode`; the EVM API accepts `branch_mode`. The enum string values are lowercase `merged` / `isolated`.

**Example:**

```bash
# Merged mode: Fall back to main if not in branch
GET /api/v1/evm/cost_element/{id}/metrics?branch=BR-001&branch_mode=merged

# Isolated mode: Only current branch
GET /api/v1/evm/cost_element/{id}/metrics?branch=BR-001&branch_mode=isolated
```

---

## Use Cases

### 1. Historical Analysis

Query EVM metrics at past dates to see project performance at that point:

```bash
# Get EVM metrics month-over-month
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2026-01-01T00:00:00Z
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2026-02-01T00:00:00Z
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2026-03-01T00:00:00Z
```

**Use Cases:**

- Audit historical project performance
- Compare current vs. past performance
- Generate trend reports
- Identify performance degradation points

### 2. Branch Comparison

Compare EVM metrics across change order branches:

```bash
# Baseline budget (main branch)
GET /api/v1/evm/cost_element/{id}/metrics?branch=main

# Change order budget (BR-001 branch)
GET /api/v1/evm/cost_element/{id}/metrics?branch=BR-001-feature-addition
```

**Use Cases:**

- Compare baseline budget vs. change order budget
- Analyze cost impact of proposed changes
- Validate change order justifications
- "What-if" scenario analysis

### 3. Time-Series Analysis

Generate time-series charts with historical EVM data:

```bash
# Get weekly time-series for 2026
GET /api/v1/evm/cost_element/{id}/timeseries?granularity=week&control_date=2026-12-31T23:59:59Z
```

**Use Cases:**

- Visualize EVM trends over time
- Identify performance patterns
- Forecast completion based on historical data
- Generate S-curves for stakeholder reports

---

## Frontend Integration

### TimeMachineContext

The `TimeMachineContext` provides time-travel settings to all EVM components:

```tsx
interface TimeMachineState {
  asOf: Date;          // Control date
  branch: string;       // Branch name
  mode: BranchMode;     // Branch mode (ISOLATED or MERGE)
  isHistorical: boolean; // Whether asOf is in the past
}
```

**Usage Example:**

```tsx
import { TimeMachineProvider } from '@/contexts/TimeMachineContext';
import { EVMSummaryView } from '@/features/evm/components';

function App() {
  const [timeMachine, setTimeMachine] = useState({
    asOf: new Date('2026-01-15'),
    branch: 'main',
    mode: BranchMode.MERGE,
  });

  return (
    <TimeMachineProvider state={timeMachine} setState={setTimeMachine}>
      <CostElementPage costElementId="..." />
    </TimeMachineProvider>
  );
}

function CostElementPage({ costElementId }: Props) {
  // useEVMMetrics automatically uses TimeMachineContext
  const { data: evmMetrics } = useEVMMetrics(
    costElementId,
    EntityType.COST_ELEMENT
  );

  return <EVMSummaryView evmMetrics={evmMetrics} />;
}
```

### Automatic Query Parameters

All EVM hooks automatically inject TimeMachineContext parameters:

```typescript
// useEVMMetrics hook implementation
export function useEVMMetrics(
  entityId: string,
  entityType: EntityType
) {
  const { asOf, branch, mode } = useTimeMachineParams();

  return useQuery({
    queryKey: evmQueryKeys.metrics(entityType, entityId, asOf, branch, mode),
    queryFn: () => api.get(`/evm/${entityType}/${entityId}/metrics`, {
      params: {
        control_date: asOf.toISOString(),
        branch,
        branch_mode: mode.toLowerCase(),
      },
    }),
  });
}
```

### Cache Invalidation

When TimeMachineContext changes, all EVM queries are automatically invalidated:

```tsx
// User changes control date
setTimeMachine({ ...state, asOf: new Date('2026-02-01') });

// All EVM queries automatically refetch:
// - useEVMMetrics()
// - useEVMTimeSeries()
// - useEVMMetricsBatch()
```

---

## Backend Implementation

### Service Layer

All EVM service methods accept time-travel parameters:

```python
async def calculate_evm_metrics(
    self,
    cost_element_id: UUID,
    control_date: datetime,
    branch: str,
    branch_mode: BranchMode,
) -> EVMMetricsRead:
    # Fetch versioned entities with time-travel
    cost_element = await ce_service.get_as_of(
        cost_element_id,
        as_of=control_date,
        branch=branch,
        branch_mode=branch_mode,
    )

    schedule_baseline = await sb_service.get_by_cost_element_as_of(
        cost_element_id,
        as_of=control_date,
        branch=branch,
        branch_mode=branch_mode,
    )

    # Fetch actuals with bitemporal valid_time filtering (AC, EV)
    ac = await cr_service.get_total_for_work_package(
        work_package_id, as_of=control_date,   # _apply_bitemporal_filter on CostRegistration.valid_time
    )

    progress_entry = await pe_service.get_latest_progress(
        work_package_id, as_of=control_date,   # _apply_bitemporal_filter on ProgressEntry.valid_time
    )

    # Calculate EVM metrics
    ...
```

### Service / Query Layer (how time-travel is actually implemented)

There is no hand-written repository `get_as_of` with raw `valid_time`/`transaction_time`
clauses. Valid Time Travel is centralized in the EVCS service base classes:

- **`TemporalService._apply_bitemporal_filter(stmt, as_of)`**
  (`backend/app/core/versioning/service.py`) — appends the canonical WHERE clauses:
  `valid_time @> as_of`, `lower(valid_time) <= as_of`, and the temporal-soft-delete check
  (`deleted_at IS NULL OR deleted_at > as_of`). **Filtering is on `valid_time` only.**
- **`BranchableService`** (subclass, `backend/app/core/branching/service.py`) layers
  `_apply_branch_mode_filter` on top for `ISOLATED` vs `MERGED` resolution.
- **`get_as_of(entity_id, as_of, branch, branch_mode)`** on these services is the public
  entry point used by `evm_service` and the EVM route.

> ⚠️ `transaction_time` is **not** used to filter query results — it exists for audit /
> late-correction tracking only (see the docstring in `_apply_bitemporal_filter`). The
> legacy "System Time Travel" / `transaction_time.contains(...)` pattern shown in older
> docs is deprecated and must not be used for EVM queries. For the canonical reference see
> [temporal-query-reference](./cross-cutting/temporal-query-reference.md).

---

## Edge Cases and Considerations

### 1. Future Control Dates

If `control_date` is in the future:

- Versioned entities: Fetched as of the future date (may not exist yet → zeroed metrics)
- AC / EV: Computed only from cost registrations / progress valid at that future date (typically empty, since future actuals haven't been recorded)
- **Result**: EVM metrics for a future date usually reflect the future plan with zero AC/EV

**Recommendation**: Use `min(control_date, now())` for realistic queries

### 2. Pre-Creation Control Dates

If `control_date` is before the entity version's `valid_time` lower bound (e.g. a
WBS element or Project queried before its baseline starts):

- The versioned entity resolves to `None` (no version valid at `control_date`).
- For **WBS / Project** the EVM route returns an **empty, zeroed `EVMMetricsResponse`
  with a `warning`** (e.g. `"No 'wbe' data available as of {date}"`) rather than 404 —
  see `backend/app/api/routes/evm.py`.
- A **404** is reserved for genuinely missing or unsupported entities (entity not found
  by id, or an entity type the route doesn't support).

**Recommendation**: Treat a zeroed response with a `warning` as "no data yet", not an error.

### 3. AC / EV ARE Point-In-Time (bitemporal `valid_time`)

Cost registrations and progress entries are **not EVCS-versioned** (no branch rows), but
they **are** bitemporally filtered by `control_date` on their own `valid_time`:

- `AC` = sum of `CostRegistration` rows whose `valid_time @> control_date`
  (`cost_registration_service.get_total_for_work_package(..., as_of=...)` →
  `_apply_bitemporal_filter`)
- `EV` uses the latest `ProgressEntry` whose `valid_time @> control_date`
  (`progress_entry_service.get_latest_progress(..., as_of=...)`)

**Example**:

```
- Jan 1, 2026: Cost element created (BAC = €100,000)
- Feb 1, 2026: Cost registration of €10,000 (valid_time starts Feb 1)
- Mar 1, 2026: Budget increased to €120,000

Query with control_date = Jan 15, 2026:
- BAC = €100,000 (as of Jan 15, before increase)
- AC  = €0       (the €10,000 registration is NOT yet valid on Jan 15)
```

### 4. Branch Isolation

Change order branches can modify versioned entities; cost registrations and progress
entries are **not branched** (they are shared across branches):

- **Versioned / branched**: Cost element, schedule baseline (BAC, PV)
- **Not branched (shared)**: Cost registrations, progress entries — but still
  point-in-time filtered by `control_date` on their `valid_time`

**Example**:

```
Main branch: BAC = €100,000
BR-001 branch: BAC = €120,000 (change order)

Cost registrations are SHARED across branches:
- AC is the same in both branches
- EV is the same in both branches (uses shared progress)
```

---

## Performance Considerations

### Query Performance

Time-travel queries use the PostgreSQL `TSTZRANGE` contains operator on `valid_time`
(`transaction_time` is **not** used for filtering — only `valid_time`):

```sql
WHERE valid_time @> :control_date
```

**Performance**: <50ms for single entity queries (with indexes)

### Indexes

The following indexes optimize time-travel queries:

- `ix_cost_elements_valid_time` - Speeds up Valid Time Travel
- `ix_schedule_baselines_valid_time` - Speeds up baseline time-travel
- (GIST/expression indexes on `valid_time` for the versioned and actuals tables — see migrations for the canonical list)

### Caching

Frontend TanStack Query cache includes time-travel parameters:

```typescript
queryKey: [
  'evm',
  'metrics',
  entityType,
  entityId,
  asOf,      // Cache key includes control date
  branch,    // Cache key includes branch
  mode,      // Cache key includes branch mode
]
```

**Result**: Different time-travel settings = different cache entries

---

## Best Practices

### 1. Validate Control Dates

Always validate `control_date` is reasonable:

```typescript
const controlDate = new Date(userInput);

// Ensure date is not too far in the past
if (controlDate < new Date('2020-01-01')) {
  throw new Error('Control date must be after 2020-01-01');
}

// Ensure date is not too far in the future
if (controlDate > new Date(Date.now() + 365 * 24 * 60 * 60 * 1000)) {
  throw new Error('Control date cannot be more than 1 year in the future');
}
```

### 2. Use ISO 8601 Format

Always use ISO 8601 format for `control_date`:

```bash
# ✅ GOOD: ISO 8601 format
GET /api/v1/evm/cost_element/{id}/metrics?control_date=2026-01-15T00:00:00Z

# ❌ BAD: Non-standard format
GET /api/v1/evm/cost_element/{id}/metrics?control_date=01/15/2026
```

### 3. Document Time-Travel Queries

When generating reports, document the time-travel settings:

```tsx
function EVMReport({ evmMetrics }: { evmMetrics: EVMMetricsResponse }) {
  return (
    <div>
      <h3>EVM Analysis Report</h3>
      <p>
        Generated on: {new Date().toLocaleString()}
        <br />
        Control date: {new Date(evmMetrics.control_date).toLocaleString()}
        <br />
        Branch: {evmMetrics.branch} ({evmMetrics.branch_mode})
      </p>
      {/* ... metrics ... */}
    </div>
  );
}
```

### 4. Handle Missing Entities Gracefully

Always handle 404 responses for invalid time-travel queries:

```tsx
const { data, error, isLoading } = useEVMMetrics(entityId, entityType);

if (isLoading) return <Spin />;
if (error) {
  if (error.response?.status === 404) {
    return <Empty description="Entity not found or unsupported type" />;
  }
  return <Alert message={error.message} type="error" />;
}
if (!data) return <Empty />;
// Note: a zeroed response with `data.warning` means "no version valid as of
// control_date" (pre-baseline) — not an error. Surface `data.warning` to the user.
```

---

## References

- [ADR-005: Bitemporal Versioning](./decisions/ADR-005-bitemporal-versioning.md) - Detailed bitemporal architecture
- [EVM API Guide](./evm-api-guide.md) - API endpoint documentation
- [EVCS Core Architecture](./backend/contexts/evcs-core/architecture.md) - Versioning system implementation
- [TimeMachineContext](../../frontend/src/contexts/TimeMachineContext.tsx) - Frontend time-travel integration

---

## Changelog

### 2026-07-01

- **Corrected (critical):** AC and EV **are** time-traveled. `CostRegistration` and
  `ProgressEntry` are bitemporally filtered by `control_date` on their `valid_time`
  (`_apply_bitemporal_filter`); they are not branched, but they are no longer described as
  "global facts fetched as of current time".
- Removed the deprecated `transaction_time @> :control_date` filter from the backend
  sample, the SQL example, and the index list — EVM filters on `valid_time` only.
- Replaced the fictional repository `get_as_of` pseudocode with a pointer to the real
  implementation: `TemporalService._apply_bitemporal_filter` / `BranchableService`
  (`backend/app/core/versioning/service.py`, `backend/app/core/branching/service.py`).
- Aligned `branch_mode` literals to the `BranchMode` enum (`merged` / `isolated`) and
  noted the FE sends `tmMode` → API `branch_mode`.
- Corrected the pre-creation 404 claim: WBS/Project pre-baseline now return an empty
  zeroed `EVMMetricsResponse` with a `warning`; 404 is for missing/unsupported entities.

### 2026-01-22

- Documented Valid Time Travel semantics for EVM queries
- Documented branch isolation modes (merge vs. strict)
- Documented frontend integration with TimeMachineContext
- Documented edge cases and best practices
