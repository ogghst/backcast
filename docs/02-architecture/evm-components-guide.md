# EVM Components Guide

**Last Updated:** 2026-04-14
**Related Iteration:** [2026-01-22-evm-analyzer-master-detail-ui](../../03-project-plan/iterations/2026-01-22-evm-analyzer-master-detail-ui/)

---

## Overview

The EVM (Earned Value Management) UI components provide reusable, type-safe React components for displaying EVM metrics across multiple entity types (Cost Elements, WBEs, Projects). All components are **generic** and work with any entity type through the `EntityType` parameter.

---

## Component Architecture

```
features/evm/
├── components/
│   ├── MetricCard.tsx              # Individual metric display card
│   ├── EVMGauge.tsx                # Semi-circle gauge for CPI/SPI
│   ├── EVMSummaryView.tsx          # Organized summary view by category
│   ├── EVMTimeSeriesChart.tsx      # Dual time-series charts
│   └── EVMAnalyzerModal.tsx        # Comprehensive analysis modal
├── api/
│   ├── hooks.ts                    # Custom hooks for EVM data fetching
│   └── client.ts                   # EVM API client
├── types.ts                        # TypeScript types and interfaces
└── index.ts                        # Feature exports
```

---

## Component Reference

### 1. MetricCard

Displays a single EVM metric with value, label, description, and status indicator.

**File:** `frontend/src/features/evm/components/MetricCard.tsx`

**Props:**

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `value` | `number \| null` | Yes | - | Metric value (null displays "N/A") |
| `label` | `string` | Yes | - | Metric label (e.g., "Cost Performance Index") |
| `description` | `string` | No | - | Optional description (shown when `showDescription=true`) |
| `showDescription` | `boolean` | No | `false` | Whether to display description |
| `size` | `'small' \| 'medium' \| 'large'` | No | `'medium'` | Card size variant |
| `status` | `'good' \| 'warning' \| 'bad' \| 'neutral'` | No | `'neutral'` | Status indicator (affects border color) |

**Status Colors:**

| Status | Border Color | Use Case |
|--------|-------------|----------|
| `good` | Green (`#52c41a`) | CPI > 1.0, SPI > 1.0, positive CV/SV |
| `warning` | Orange (`#faad14`) | Metrics near thresholds |
| `bad` | Red (`#ff4d4f`) | CPI < 1.0, SPI < 1.0, negative CV/SV |
| `neutral` | Gray (`#d9d9d9`) | Neutral or unknown status |

**Usage Example:**

```tsx
import { MetricCard } from '@/features/evm/components';

// Display CPI with status
<MetricCard
  value={0.85}
  label="Cost Performance Index"
  description="Efficiency of cost usage (< 1.0 = over budget)"
  showDescription={true}
  size="medium"
  status="bad"
/>

// Display budget (currency format)
<MetricCard
  value={100000}
  label="Budget at Completion"
  size="large"
  status="neutral"
/>

// Display null value
<MetricCard
  value={null}
  label="Schedule Performance Index"
  size="small"
/>
```

**Automatic Formatting:**

The component automatically formats values based on the `label`:

| Label Pattern | Format | Example |
|--------------|--------|---------|
| Contains "Budget", "Cost", "Variance" | Currency (€) | `€100,000.00` |
| Contains "Index" | Percentage | `85%` |
| Contains "Progress" | Percentage | `50%` |
| Other | Number with decimals | `1,234.56` |

---

### 2. EVMGauge

Semi-circle gauge for visualizing CPI and SPI performance indices (traditional EVM style).

**File:** `frontend/src/features/evm/components/EVMGauge.tsx`

**Props:**

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `value` | `number \| null` | Yes | - | Index value (typically 0-2+, null displays "N/A") |
| `label` | `string` | Yes | - | Gauge label (e.g., "CPI", "SPI") |
| `size` | `number` | No | `200` | Gauge diameter in pixels |

**Color Zones:**

| Range | Color | Interpretation |
|-------|-------|----------------|
| `< 0.9` | Red (`#ff4d4f`) | Poor performance |
| `0.9 - 1.1` | Yellow (`#faad14`) | Near target |
| `> 1.1` | Green (`#52c41a`) | Good performance |

**Usage Example:**

```tsx
import { EVMGauge } from '@/features/evm/components';

// Display CPI gauge
<EVMGauge
  value={0.85}
  label="CPI"
  size={200}
/>

// Display SPI gauge
<EVMGauge
  value={1.15}
  label="SPI"
  size={200}
/>

// Display null value
<EVMGauge
  value={null}
  label="CPI"
/>
```

**SVG Structure:**

The gauge renders as an SVG with:
- Semi-circle path (180° arc)
- Color zones based on value ranges
- Tick marks at 0, 0.5, 1.0, 1.5, 2.0
- Value label centered below gauge
- Needle pointing to current value

---

### 3. EVMSummaryView

Organized summary view displaying all EVM metrics grouped by category with an "Advanced" button to open the full EVM Analyzer modal.

**File:** `frontend/src/features/evm/components/EVMSummaryView.tsx`

**Props:**

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `evmMetrics` | `EVMMetricsResponse` | Yes | - | EVM metrics data |
| `onAdvanced` | `() => void` | No | - | Callback when "Advanced" button clicked |

**Metric Categories:**

| Category | Metrics |
|----------|---------|
| **Schedule** | PV, SPI |
| **Cost** | AC, CPI |
| **Performance** | EV, SV |
| **Forecast** | EAC, VAC, ETC |

**Usage Example:**

```tsx
import { EVMSummaryView } from '@/features/evm/components';
import { useEVMMetrics } from '@/features/evm/api/hooks';

function CostElementPage({ costElementId }: { costElementId: string }) {
  const { data: evmMetrics, isLoading } = useEVMMetrics(
    costElementId,
    EntityType.COST_ELEMENT
  );

  const [modalOpen, setModalOpen] = useState(false);

  if (isLoading) return <Spin />;
  if (!evmMetrics) return <Empty />;

  return (
    <>
      <EVMSummaryView
        evmMetrics={evmMetrics}
        onAdvanced={() => setModalOpen(true)}
      />
      <EVMAnalyzerModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        evmMetrics={evmMetrics}
        {/* ... other props */}
      />
    </>
  );
}
```

**Layout:**

- All categories expanded by default (using Ant Design Collapse)
- Each category displays 2-4 metrics using MetricCard components
- "Advanced" button in top-right corner
- Responsive grid layout (2 columns on desktop, 1 on mobile)

---

### 4. EVMTimeSeriesChart

Dual time-series charts displaying EVM metrics over time with granularity selector.

**File:** `frontend/src/features/evm/components/EVMTimeSeriesChart.tsx`

**Props:**

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `timeSeries` | `EVMTimeSeriesResponse` | Yes | - | Time-series data from API |
| `onGranularityChange` | `(granularity: EVMTimeSeriesGranularity) => void` | Yes | - | Callback when granularity changes |
| `loading` | `boolean` | No | `false` | Loading state |

**Chart 1: EVM Progression**

Displays PV, EV, and AC trends over time:

| Metric | Color | Line Style |
|--------|-------|------------|
| PV (Planned Value) | Blue (`#5b8ff9`) | Solid |
| EV (Earned Value) | Green (`#5ad8a6`) | Solid |
| AC (Actual Cost) | Gray (`#5d7092`) | Solid |

**Chart 2: Cost Comparison**

Displays Forecast vs. Actual cost over time:

| Metric | Color | Line Style |
|--------|-------|------------|
| Forecast (EAC) | Orange (`#faad14`) | Dashed |
| Actual (AC) | Red (`#ff4d4f`) | Solid |

**Granularity Options:**

| Option | Description | Use Case |
|--------|-------------|----------|
| Day | Daily data points | Short-term projects |
| Week | Weekly data points (default) | Balanced detail |
| Month | Monthly data points | Long-term projects |

**Usage Example:**

```tsx
import { EVMTimeSeriesChart } from '@/features/evm/components';
import { useEVMTimeSeries } from '@/features/evm/api/hooks';
import { useState } from 'react';

function EVMAnalysis({ entityId, entityType }: { entityId: string; entityType: EntityType }) {
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>(
    EVMTimeSeriesGranularity.WEEK
  );

  const { data: timeSeries, isLoading } = useEVMTimeSeries(
    entityId,
    entityType,
    granularity
  );

  if (isLoading) return <Spin />;
  if (!timeSeries) return <Empty />;

  return (
    <EVMTimeSeriesChart
      timeSeries={timeSeries}
      onGranularityChange={setGranularity}
      loading={isLoading}
    />
  );
}
```

**Features:**

- Ant Design built-in zoom (brush-x interaction)
- Responsive charts (resize with container)
- Automatic currency/percentage formatting
- Tooltip on hover showing exact values
- Legend for all metrics

---

### 5. EVMAnalyzerModal

Comprehensive modal component displaying all EVM metrics with enhanced visualizations.

**File:** `frontend/src/features/evm/components/EVMAnalyzerModal.tsx`

**Props:**

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `open` | `boolean` | Yes | - | Whether modal is open |
| `onClose` | `() => void` | Yes | - | Callback when modal closes |
| `evmMetrics` | `EVMMetricsResponse \| undefined` | Yes | - | EVM metrics data |
| `timeSeries` | `EVMTimeSeriesResponse \| undefined` | Yes | - | Time-series data |
| `loading` | `boolean` | No | `false` | Loading state |
| `onGranularityChange` | `(granularity: EVMTimeSeriesGranularity) => void` | Yes | - | Callback when granularity changes |

**Modal Layout:**

1. **Header**: "EVM Analysis" title with close button
2. **Performance Indices**: CPI and SPI gauges (side-by-side)
3. **Time-Series Charts**: EVM Progression and Cost Comparison (outside tabs for visibility)
4. **Tabbed Metrics**:
   - **Overview**: BAC, EAC, VAC, ETC
   - **Schedule**: PV, SPI, SV
   - **Cost**: AC, CPI, CV
   - **Variance**: CV, SV
   - **Forecast**: EAC, VAC, ETC

**Usage Example:**

```tsx
import { EVMAnalyzerModal } from '@/features/evm/components';
import { useEVMMetrics, useEVMTimeSeries } from '@/features/evm/api/hooks';
import { useState } from 'react';

function CostElementDetail({ costElementId }: { costElementId: string }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>(
    EVMTimeSeriesGranularity.WEEK
  );

  const { data: evmMetrics, isLoading: metricsLoading } = useEVMMetrics(
    costElementId,
    EntityType.COST_ELEMENT
  );

  const { data: timeSeries, isLoading: timeSeriesLoading } = useEVMTimeSeries(
    costElementId,
    EntityType.COST_ELEMENT,
    granularity
  );

  return (
    <>
      <Button onClick={() => setModalOpen(true)}>Advanced Analysis</Button>

      <EVMAnalyzerModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        evmMetrics={evmMetrics}
        timeSeries={timeSeries}
        loading={metricsLoading || timeSeriesLoading}
        onGranularityChange={setGranularity}
      />
    </>
  );
}
```

**Features:**

- Responsive layout (scrollable on mobile)
- Loading state with Spin component
- Empty state with Empty component
- Proper ARIA attributes (role="dialog")
- Keyboard navigation (Esc to close)
- Destroy on close (cleanup)

---

## Custom Hooks

### useEVMMetrics

Fetches EVM metrics for a single entity.

**Signature:**

```typescript
function useEVMMetrics(
  entityId: string,
  entityType: EntityType
): UseQueryResult<EVMMetricsResponse, Error>
```

**Usage:**

```tsx
import { useEVMMetrics } from '@/features/evm/api/hooks';
import { EntityType } from '@/features/evm/types';

function MyComponent({ costElementId }: { costElementId: string }) {
  const { data, isLoading, error } = useEVMMetrics(
    costElementId,
    EntityType.COST_ELEMENT
  );

  if (isLoading) return <Spin />;
  if (error) return <Alert message={error.message} type="error" />;
  if (!data) return <Empty />;

  return <div>BAC: {data.bac}</div>;
}
```

**Features:**

- Integrates with TimeMachineContext (branch, control_date)
- Disabled when `entityId` is empty
- 5-minute stale time, 10-minute cache time
- Automatic refetch on TimeMachineContext changes

---

### useEVMTimeSeries

Fetches time-series data for EVM charts.

**Signature:**

```typescript
function useEVMTimeSeries(
  entityId: string,
  entityType: EntityType,
  granularity: EVMTimeSeriesGranularity = EVMTimeSeriesGranularity.WEEK
): UseQueryResult<EVMTimeSeriesResponse, Error>
```

**Usage:**

```tsx
import { useEVMTimeSeries } from '@/features/evm/api/hooks';
import { EntityType, EVMTimeSeriesGranularity } from '@/features/evm/types';

function MyComponent({ costElementId }: { costElementId: string }) {
  const [granularity, setGranularity] = useState(EVMTimeSeriesGranularity.WEEK);

  const { data, isLoading } = useEVMTimeSeries(
    costElementId,
    EntityType.COST_ELEMENT,
    granularity
  );

  if (isLoading) return <Spin />;
  if (!data) return <Empty />;

  return (
    <>
      <Radio.Group value={granularity} onChange={(e) => setGranularity(e.target.value)}>
        <Radio.Button value={EVMTimeSeriesGranularity.DAY}>Day</Radio.Button>
        <Radio.Button value={EVMTimeSeriesGranularity.WEEK}>Week</Radio.Button>
        <Radio.Button value={EVMTimeSeriesGranularity.MONTH}>Month</Radio.Button>
      </Radio.Group>
      <EVMTimeSeriesChart timeSeries={data} onGranularityChange={setGranularity} />
    </>
  );
}
```

**Features:**

- Integrates with TimeMachineContext
- Cache key includes granularity (auto-refetch on change)
- 5-minute stale time, 10-minute cache time

---

### useEVMMetricsBatch

Fetches aggregated EVM metrics for multiple entities.

**Signature:**

```typescript
function useEVMMetricsBatch(
  entityIds: string[],
  entityType: EntityType
): UseQueryResult<EVMMetricsResponse, Error>
```

**Usage:**

```tsx
import { useEVMMetricsBatch } from '@/features/evm/api/hooks';
import { EntityType } from '@/features/evm/types';

function ProjectDashboard({ projectIds }: { projectIds: string[] }) {
  const { data, isLoading } = useEVMMetricsBatch(
    projectIds,
    EntityType.PROJECT
  );

  if (isLoading) return <Spin />;
  if (!data) return <Empty />;

  return <div>Combined BAC: {data.bac}</div>;
}
```

**Features:**

- Disabled when `entityIds` is empty
- Server-side aggregation (sum + weighted avg)
- Integrates with TimeMachineContext

---

## Type Definitions

### EntityType

Enum representing supported entity types.

```typescript
enum EntityType {
  COST_ELEMENT = "cost_element",
  WBE = "wbe",
  PROJECT = "project",
}
```

### EVMMetricsResponse

EVM metrics response from API.

```typescript
interface EVMMetricsResponse {
  entity_type: EntityType;
  entity_id: string;
  bac: number | null;
  pv: number | null;
  ac: number | null;
  ev: number | null;
  cv: number | null;
  sv: number | null;
  cpi: number | null;
  spi: number | null;
  eac: number | null;
  vac: number | null;
  etc: number | null;
  control_date: string;
  branch: string;
  branch_mode: BranchMode;
  progress_percentage: number | null;
  warning: string | null;
}
```

### EVMTimeSeriesResponse

Time-series data response from API.

```typescript
interface EVMTimeSeriesResponse {
  entity_type: EntityType;
  entity_id: string;
  granularity: EVMTimeSeriesGranularity;
  points: EVMTimeSeriesPoint[];
  total_points: number;
}

interface EVMTimeSeriesPoint {
  date: string;
  bac: number | null;
  pv: number | null;
  ac: number | null;
  ev: number | null;
  cv: number | null;
  sv: number | null;
  cpi: number | null;
  spi: number | null;
  eac: number | null;
  vac: number | null;
  etc: number | null;
}
```

### EVMTimeSeriesGranularity

Time granularity options for time-series.

```typescript
enum EVMTimeSeriesGranularity {
  DAY = "day",
  WEEK = "week",
  MONTH = "month",
}
```

---

## Integration with TimeMachineContext

All EVM hooks automatically integrate with `TimeMachineContext` to respect time-travel settings.

**TimeMachineContext provides:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `asOf` | `Date` | Control date for time-travel queries |
| `branch` | `string` | Branch name |
| `mode` | `BranchMode` | Branch mode (ISOLATED or MERGE) |

**Example:**

```tsx
import { TimeMachineProvider } from '@/contexts/TimeMachineContext';

function App() {
  const [timeMachineState, setTimeMachineState] = useState({
    asOf: new Date(),
    branch: 'main',
    mode: BranchMode.MERGE,
  });

  return (
    <TimeMachineProvider state={timeMachineState} setState={setTimeMachineState}>
      <MyEVMComponent />
    </TimeMachineProvider>
  );
}

// MyEVMComponent automatically uses TimeMachineContext settings
function MyEVMComponent() {
  const { data } = useEVMMetrics(entityId, EntityType.COST_ELEMENT);
  // Query includes: asOf, branch, mode from context
}
```

**Cache Invalidation:**

When TimeMachineContext changes, all EVM queries are automatically invalidated and refetched:

```tsx
// When user changes control date
setTimeMachineState({ ...state, asOf: new Date('2026-01-01') });
// All useEVMMetrics, useEVMTimeSeries hooks automatically refetch
```

---

## Best Practices

### 1. Entity Type Support

Always design components to work with all entity types:

```tsx
// ✅ GOOD: Generic component
function EVMCard({ entityId, entityType }: { entityId: string; entityType: EntityType }) {
  const { data } = useEVMMetrics(entityId, entityType);
  return <MetricCard value={data?.cpi} label="CPI" />;
}

// ❌ BAD: Tightly coupled to cost elements
function CostElementEVMCard({ costElementId }: { costElementId: string }) {
  const { data } = useEVMMetrics(costElementId, EntityType.COST_ELEMENT);
  return <MetricCard value={data?.cpi} label="CPI" />;
}
```

### 2. Loading and Error States

Always handle loading and error states:

```tsx
function MyEVMComponent({ entityId, entityType }: Props) {
  const { data, isLoading, error } = useEVMMetrics(entityId, entityType);

  if (isLoading) return <Spin />;
  if (error) return <Alert message={error.message} type="error" />;
  if (!data) return <Empty description="No EVM data available" />;

  return <EVMSummaryView evmMetrics={data} />;
}
```

### 3. Null Value Handling

EVM metrics can be null (e.g., CPI when AC = 0):

```tsx
// ✅ GOOD: Handle null values
<MetricCard
  value={evmMetrics.cpi} // Can be null
  label="Cost Performance Index"
/>

// MetricCard displays "N/A" for null values
```

### 4. Granularity State

Manage granularity state at the page level for consistency:

```tsx
function EVMPage({ entityId, entityType }: Props) {
  // Page-level granularity state
  const [granularity, setGranularity] = useState(EVMTimeSeriesGranularity.WEEK);

  const { data: timeSeries } = useEVMTimeSeries(entityId, entityType, granularity);

  return (
    <>
      <EVMSummaryView evmMetrics={evmMetrics} />
      <EVMTimeSeriesChart
        timeSeries={timeSeries}
        onGranularityChange={setGranularity}
      />
    </>
  );
}
```

### 5. Modal Management

Use proper modal state management:

```tsx
function MyPage() {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setModalOpen(true)}>Open Analysis</Button>

      <EVMAnalyzerModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        {/* ... other props */}
      />
    </>
  );
}
```

---

## Testing

### Unit Tests

Component unit tests use `@testing-library/react`:

```tsx
import { render, screen } from '@testing-library/react';
import { MetricCard } from './MetricCard';

describe('MetricCard', () => {
  it('displays metric value correctly', () => {
    render(<MetricCard value={100000} label="Budget at Completion" />);
    expect(screen.getByText('€100,000.00')).toBeInTheDocument();
  });

  it('displays N/A for null values', () => {
    render(<MetricCard value={null} label="Cost Performance Index" />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });
});
```

### Integration Tests

Integration tests verify component interactions:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EVMAnalyzerModal } from './EVMAnalyzerModal';

describe('EVMAnalyzerModal Integration', () => {
  it('opens modal and displays gauges', async () => {
    const onClose = jest.fn();
    render(
      <EVMAnalyzerModal
        open={true}
        onClose={onClose}
        evmMetrics={mockMetrics}
        timeSeries={mockTimeSeries}
        onGranularityChange={jest.fn()}
      />
    );

    expect(screen.getByText('EVM Analysis')).toBeInTheDocument();
    expect(screen.getByText('CPI')).toBeInTheDocument();
    expect(screen.getByText('SPI')).toBeInTheDocument();
  });
});
```

### E2E Tests

E2E tests use Playwright:

```typescript
test('EVM Analyzer modal opens and displays charts', async ({ page }) => {
  await page.goto('/cost-elements/123e4567-e89b-12d3-a456-426614174000');

  // Click Advanced button
  await page.click('button:has-text("Advanced")');

  // Verify modal opens
  await expect(page.locator('.ant-modal')).toBeVisible();

  // Verify charts render
  await expect(page.locator('canvas')).toHaveCount(2); // 2 charts
});
```

---

## Performance

### Component Optimization

- **React.memo**: Components use React.memo implicitly via hooks
- **TanStack Query**: Automatic caching and deduplication
- **Modal cleanup**: `destroyOnClose` prop for cleanup

### Query Optimization

- **Stale time**: 5 minutes (balances freshness vs. API calls)
- **Cache time**: 10 minutes (retains data in background)
- **Disabled queries**: Queries disabled when inputs are invalid

### Rendering Performance

| Component | Render Time | Notes |
|-----------|-------------|-------|
| MetricCard | <10ms | Simple component |
| EVMGauge | <20ms | SVG rendering |
| EVMSummaryView | <50ms | 8-10 MetricCard components |
| EVMTimeSeriesChart | <100ms | Ant Design charts |
| EVMAnalyzerModal | <500ms | All components + charts |

---

## Accessibility

All components follow WCAG 2.1 AA standards:

- **ARIA labels**: Proper ARIA attributes on interactive elements
- **Keyboard navigation**: Full keyboard support (Tab, Enter, Esc)
- **Screen readers**: Semantic HTML and ARIA descriptions
- **Color contrast**: All text meets contrast requirements
- **Focus indicators**: Visible focus states on all controls

---

## References

- [EVM API Guide](./evm-api-guide.md) - Backend API documentation
- [ADR-011: Generic EVM Metric System](./decisions/ADR-011-generic-evm-metric-system.md) - Architecture decisions
- [EVM Calculation Guide](./evm-calculation-guide.md) - EVM formulas and interpretation
- [Time-Travel Semantics](./evm-time-travel-semantics.md) - TimeMachineContext integration

---

## Changelog

### 2026-01-22
- Initial release of EVM component library
- MetricCard, EVMGauge, EVMSummaryView, EVMTimeSeriesChart, EVMAnalyzerModal
- Generic hooks (useEVMMetrics, useEVMTimeSeries, useEVMMetricsBatch)
- Full TypeScript support with strict mode
- TimeMachineContext integration
- Comprehensive test coverage (unit, integration, E2E)
