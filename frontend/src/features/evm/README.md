# EVM (Earned Value Management) Feature

## Overview

The EVM feature provides comprehensive Earned Value Management capabilities for analyzing project performance across cost elements, Work Breakdown Elements (WBEs), and projects. It offers real-time metrics, historical trends, and predictive forecasting.

### Key Features

- **Multi-Level EVM Metrics**: Calculate metrics at cost element, WBE, and project levels
- **Time-Travel Support**: All queries respect the TimeMachineContext for historical analysis
- **Interactive Visualizations**: Gauges for performance indices, time-series charts for trends
- **Batch Operations**: Fetch and aggregate metrics across multiple entities
- **Generic Components**: Reusable UI components for any entity type
- **Status Indicators**: Color-coded metrics (good/warning/bad) based on performance thresholds

---

## Architecture

### Directory Structure

```
features/evm/
├── components/
│   ├── MetricCard.tsx              # Individual metric display card
│   ├── EVMGauge.tsx                # Semi-circle gauge for CPI/SPI
│   ├── EVMTimeSeriesChart.tsx      # Time-series trend charts
│   ├── EVMSummaryView.tsx          # Collapsible metric summary
│   ├── EVMAnalyzerModal.tsx        # Comprehensive EVM analysis modal
│   └── __tests__/                  # Component unit tests
├── api/
│   ├── useEVMMetrics.ts            # Custom TanStack Query hooks
│   └── __tests__/                  # Hook tests
├── types.ts                        # TypeScript interfaces and utilities
├── index.ts                        # Public API exports
└── README.md                       # This file
```

### Core Concepts

#### Entity Types

The EVM system supports three entity types:

- **COST_ELEMENT**: Individual cost element (leaf node in hierarchy)
- **WBE**: Work Breakdown Element (intermediate node, aggregates child cost elements)
- **PROJECT**: Project level (root node, aggregates child WBEs)

#### Metric Categories

Metrics are organized by topic for better user experience:

- **Schedule**: Time-based performance (SPI, SV)
- **Cost**: Budget and cost metrics (BAC, AC, CV, CPI)
- **Variance**: Deviation metrics (CV, SV)
- **Performance**: Efficiency indices (CPI, SPI)
- **Forecast**: Projected completion metrics (EAC, VAC, ETC)

---

## Components

### MetricCard

A reusable card component for displaying individual EVM metrics with status indicators.

#### Props

```typescript
interface MetricCardProps {
  metadata: MetricMetadata;      // Metric definition (name, description, format)
  value: number | null;          // Metric value (null = not available)
  status: "good" | "warning" | "bad";  // Color coding
  size: "small" | "medium" | "large";  // Card size
  showDescription?: boolean;     // Show metric description
}
```

#### Usage

```tsx
import { MetricCard, METRIC_DEFINITIONS, getMetricStatus } from "@/features/evm";

<MetricCard
  metadata={METRIC_DEFINITIONS.cpi}
  value={metrics.cpi}
  status={getMetricStatus("cpi", metrics.cpi)}
  size="medium"
  showDescription
/>
```

#### Features

- Color-coded status border (green=good, orange=warning, red=bad)
- Three size variants (small, medium, large)
- Automatic value formatting (currency, percentage, number)
- Accessible with ARIA labels

---

### EVMGauge

Traditional semi-circle gauge component for displaying CPI/SPI ratios with color-coded zones.

#### Props

```typescript
interface EVMGaugeProps {
  value: number | null;           // Current value (null = N/A)
  min: number;                    // Minimum value
  max: number;                    // Maximum value
  label: string;                  // Gauge label (e.g., "CPI", "SPI")
  goodThreshold?: number;         // Good threshold (default 1.0)
  warningThresholdPercent?: number; // Warning threshold % (default 0.9)
  size?: number;                  // Gauge size in pixels (default 200)
  strokeWidth?: number;           // Arc stroke width (default 20)
}
```

#### Usage

```tsx
import { EVMGauge } from "@/features/evm";

<EVMGauge
  value={metrics.cpi}
  min={0}
  max={2}
  label="CPI"
  goodThreshold={1.0}
  warningThresholdPercent={0.9}
  size={180}
/>
```

#### Features

- Semi-circle SVG gauge design
- Needle indicator pointing to current value
- Color-coded zones (green/yellow/red)
- Customizable thresholds and size
- Accessible with ARIA labels

---

### EVMTimeSeriesChart

Displays two time-series charts for EVM analysis:
1. **EVM Progression**: PV, EV, AC over time
2. **Cost Comparison**: Forecast vs Actual over time

#### Props

```typescript
interface EVMTimeSeriesChartProps {
  timeSeries: EVMTimeSeriesResponse | undefined;  // Time-series data
  loading?: boolean;                              // Loading state
  onGranularityChange: (granularity: EVMTimeSeriesGranularity) => void;
  currentGranularity?: EVMTimeSeriesGranularity;  // Current granularity
}
```

#### Usage

```tsx
import { EVMTimeSeriesChart } from "@/features/evm";

<EVMTimeSeriesChart
  timeSeries={timeSeriesData}
  loading={isLoading}
  onGranularityChange={(g) => setGranularity(g)}
  currentGranularity={granularity}
/>
```

#### Features

- Granularity selector (day/week/month)
- Ant Design built-in zoom support
- Loading and empty states
- Responsive design
- Automatic currency formatting

---

### EVMSummaryView

A comprehensive summary view for displaying EVM metrics organized by category in collapsible sections.

#### Props

```typescript
interface EVMSummaryViewProps {
  metrics: EVMMetricsResponse;  // EVM metrics to display
  onAdvanced?: () => void;      // Callback for Advanced button
}
```

#### Usage

```tsx
import { EVMSummaryView } from "@/features/evm";

<EVMSummaryView
  metrics={evmMetrics}
  onAdvanced={() => setIsModalOpen(true)}
/>
```

#### Features

- Collapsible sections for each metric category
- MetricCard components for individual metrics
- Advanced button to open EVM Analyzer modal
- Responsive grid layout
- All categories expanded by default

---

### EVMAnalyzerModal

A comprehensive modal component for thorough EVM evaluation with enhanced visualizations.

#### Props

```typescript
interface EVMAnalyzerModalProps {
  open: boolean;                                 // Modal open state
  onClose: () => void;                           // Close callback
  evmMetrics: EVMMetricsResponse | undefined;    // EVM metrics data
  timeSeries: EVMTimeSeriesResponse | undefined;  // Time-series data
  loading?: boolean;                             // Loading state
  onGranularityChange: (granularity: EVMTimeSeriesGranularity) => void;
}
```

#### Usage

```tsx
import { EVMAnalyzerModal } from "@/features/evm";

<EVMAnalyzerModal
  open={isModalOpen}
  onClose={() => setIsModalOpen(false)}
  evmMetrics={evmMetrics}
  timeSeries={timeSeriesData}
  loading={isLoading}
  onGranularityChange={(g) => setGranularity(g)}
/>
```

#### Features

- Modal dialog with open/close control
- Gauges for CPI and SPI performance indices
- Tabbed interface for metric categories
- EVMTimeSeriesChart for historical trends
- Proper loading and empty states
- All EVM metrics displayed with enhanced visualizations

---

## Custom Hooks

### useEVMMetrics

Fetch EVM metrics for a single entity using TanStack Query.

#### Signature

```typescript
function useEVMMetrics(
  entityType: EntityType,
  entityId: string,
  params?: UseEVMMetricsParams
): UseQueryResult<EVMMetricsResponse>
```

#### Parameters

```typescript
interface UseEVMMetricsParams extends EVMQueryParams {
  queryOptions?: Omit<
    UseQueryOptions<EVMMetricsResponse>,
    "queryKey" | "queryFn"
  >;
}

interface EVMQueryParams {
  branch?: string;
  controlDate?: string;
}
```

#### Usage

```tsx
import { useEVMMetrics } from "@/features/evm";

function CostElementEVM({ costElementId }: { costElementId: string }) {
  const { data, isLoading, error } = useEVMMetrics(
    "cost_element",
    costElementId
  );

  if (isLoading) return <Spin />;
  if (error) return <Alert message="Error loading EVM metrics" />;
  if (!data) return <Empty />;

  return <EVMSummaryView metrics={data} />;
}
```

#### Features

- Integrates with TimeMachineContext for time-travel queries
- Automatic caching and refetching
- Type-safe responses
- Disabled until valid entityId provided

---

### useEVMTimeSeries

Fetch time-series EVM data for charts with configurable granularity.

#### Signature

```typescript
function useEVMTimeSeries(
  entityType: EntityType,
  entityId: string,
  granularity: EVMTimeSeriesGranularity,
  params?: EVMTimeSeriesParams
): UseQueryResult<EVMTimeSeriesResponse>
```

#### Parameters

```typescript
interface EVMTimeSeriesParams extends EVMQueryParams {
  granularity: EVMTimeSeriesGranularity;
  queryOptions?: Omit<
    UseQueryOptions<EVMTimeSeriesResponse>,
    "queryKey" | "queryFn"
  >;
}
```

#### Usage

```tsx
import { useEVMTimeSeries } from "@/features/evm";

function TimeSeriesChart({ costElementId }: { costElementId: string }) {
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>("week");

  const { data, isLoading } = useEVMTimeSeries(
    "cost_element",
    costElementId,
    granularity
  );

  return (
    <EVMTimeSeriesChart
      timeSeries={data}
      loading={isLoading}
      onGranularityChange={setGranularity}
    />
  );
}
```

#### Features

- Granularity selection (day/week/month)
- Integrates with TimeMachineContext
- Automatic caching per granularity
- Disabled until valid entityId and granularity provided

---

### useEVMMetricsBatch

Fetch aggregated EVM metrics for multiple entities.

#### Signature

```typescript
function useEVMMetricsBatch(
  entityType: EntityType,
  entityIds: string[] | undefined,
  params?: EVMMetricsBatchParams
): UseQueryResult<EVMMetricsBatchResponse>
```

#### Parameters

```typescript
interface EVMMetricsBatchParams extends EVMQueryParams {
  queryOptions?: Omit<
    UseQueryOptions<EVMMetricsBatchResponse>,
    "queryKey" | "queryFn"
  >;
}
```

#### Usage

```tsx
import { useEVMMetricsBatch } from "@/features/evm";

function MultiEntityEVM({ costElementIds }: { costElementIds: string[] }) {
  const { data, isLoading } = useEVMMetricsBatch(
    "cost_element",
    costElementIds
  );

  if (isLoading) return <Spin />;
  if (!data) return <Empty />;

  return (
    <div>
      <h3>Aggregated Metrics</h3>
      <MetricCard metadata={METRIC_DEFINITIONS.bac} value={data.aggregated.bac} status="good" size="medium" />
      {/* Display other aggregated metrics */}
    </div>
  );
}
```

#### Features

- Batch query for multiple entities
- Returns individual entity metrics plus aggregated metrics
- Backend aggregation (weighted averages for indices, sums for amounts)
- Integrates with TimeMachineContext

---

## Types and Utilities

### Core Types

#### EVMMetricsResponse

```typescript
interface EVMMetricsResponse {
  entity_type: EntityType;      // "cost_element" | "wbe" | "project"
  entity_id: string;            // Entity UUID
  bac: number;                  // Budget at Completion
  pv: number;                   // Planned Value
  ac: number;                   // Actual Cost
  ev: number;                   // Earned Value
  cv: number;                   // Cost Variance (EV - AC)
  sv: number;                   // Schedule Variance (EV - PV)
  cpi: number | null;           // Cost Performance Index (EV / AC)
  spi: number | null;           // Schedule Performance Index (EV / PV)
  eac: number | null;           // Estimate at Completion
  vac: number | null;           // Variance at Completion (BAC - EAC)
  etc: number | null;           // Estimate to Complete (EAC - AC)
  control_date: string;         // ISO 8601 date string
  branch: string;               // Branch name
}
```

#### EVMTimeSeriesResponse

```typescript
interface EVMTimeSeriesResponse {
  granularity: EVMTimeSeriesGranularity;  // "day" | "week" | "month"
  points: EVMTimeSeriesPoint[];           // Data points
  start_date: string;                     // ISO 8601
  end_date: string;                       // ISO 8601
  total_points: number;                   // Count
}

interface EVMTimeSeriesPoint {
  date: string;        // ISO 8601
  pv: number;          // Planned Value
  ev: number;          // Earned Value
  ac: number;          // Actual Cost
  forecast: number;    // Forecast value
  actual: number;      // Actual value
}
```

#### MetricMetadata

```typescript
interface MetricMetadata {
  key: keyof EVMMetricsResponse;    // Field name
  name: string;                      // Display name
  description: string;               // Explanation
  category: MetricCategory;          // Grouping category
  targetRanges: MetricTargetRanges;  // Thresholds
  higherIsBetter: boolean;           // Direction
  format: "currency" | "percentage" | "number";
}
```

### Helper Functions

#### getMetricStatus

Determine if a metric value is favorable.

```typescript
function getMetricStatus(
  key: MetricKey,
  value: number | null
): "good" | "warning" | "bad"

// Examples:
getMetricStatus("cpi", 1.07)  // "good" (above 1.0)
getMetricStatus("cpi", 0.95)  // "warning" (0.9-1.0)
getMetricStatus("cpi", 0.85)  // "bad" (below 0.9)
getMetricStatus("vac", -5000) // "bad" (negative variance)
getMetricStatus("vac", 5000)  // "good" (positive variance)
```

#### getMetricsByCategory

Get all metrics for a specific category.

```typescript
function getMetricsByCategory(
  category: MetricCategory
): MetricMetadata[]

// Example:
const scheduleMetrics = getMetricsByCategory(MetricCategory.SCHEDULE);
// Returns [SPI definition, SV definition]
```

#### getMetricMetadata

Get metadata for a specific metric.

```typescript
function getMetricMetadata(
  key: MetricKey
): MetricMetadata | undefined

// Example:
const cpiMeta = getMetricMetadata("cpi");
// Returns { key: "cpi", name: "Cost Performance Index", ... }
```

---

## TimeMachineContext Integration

All EVM hooks automatically integrate with the TimeMachineContext to support time-travel queries.

### How It Works

1. **Control Date**: Uses `asOf` from TimeMachineContext as the default `controlDate`
2. **Branch**: Uses `branch` from TimeMachineContext as the default branch
3. **Mode**: Uses `mode` from TimeMachineContext for branch mode (ISOLATED/MERGE)

### Example

```tsx
import { useEVMMetrics } from "@/features/evm";

function EVMWithTimeTravel({ costElementId }: { costElementId: string }) {
  // TimeMachineContext provides:
  // - asOf: "2024-01-15T00:00:00Z"
  // - branch: "feature/change-order-1"
  // - mode: "isolated"

  const { data } = useEVMMetrics("cost_element", costElementId);

  // Query automatically uses TimeMachineContext values:
  // GET /api/v1/cost-elements/{id}/evm?control_date=2024-01-15&branch=feature/change-order-1&branch_mode=isolized

  return <EVMSummaryView metrics={data} />;
}
```

### Override TimeMachineContext

You can override TimeMachineContext values by passing explicit parameters:

```tsx
const { data } = useEVMMetrics("cost_element", costElementId, {
  branch: "main",           // Override TimeMachineContext branch
  controlDate: "2024-01-01" // Override TimeMachineContext asOf
});
```

---

## Usage Patterns

### Basic EVM Display

```tsx
import { EVMSummaryView, useEVMMetrics } from "@/features/evm";

function CostElementEVM({ costElementId }: { costElementId: string }) {
  const { data, isLoading, error } = useEVMMetrics("cost_element", costElementId);

  if (isLoading) return <Spin />;
  if (error) return <Alert message="Error loading EVM" />;
  if (!data) return <Empty description="No EVM data available" />;

  return <EVMSummaryView metrics={data} />;
}
```

### EVM with Advanced Analysis Modal

```tsx
import { useState } from "react";
import { EVMSummaryView, EVMAnalyzerModal, useEVMMetrics, useEVMTimeSeries } from "@/features/evm";

function CostElementEVMWithModal({ costElementId }: { costElementId: string }) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>("week");

  const { data: evmMetrics } = useEVMMetrics("cost_element", costElementId);
  const { data: timeSeries } = useEVMTimeSeries("cost_element", costElementId, granularity);

  return (
    <>
      <EVMSummaryView
        metrics={evmMetrics}
        onAdvanced={() => setIsModalOpen(true)}
      />
      <EVMAnalyzerModal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        evmMetrics={evmMetrics}
        timeSeries={timeSeries}
        onGranularityChange={setGranularity}
      />
    </>
  );
}
```

### WBE-Level EVM (Aggregation from Children)

```tsx
import { useEVMMetrics } from "@/features/evm";

function WBEEVM({ wbeId }: { wbeId: string }) {
  // WBE metrics aggregate from child cost elements
  const { data } = useEVMMetrics("wbe", wbeId);

  if (!data) return <Spin />;

  return (
    <div>
      <h3>WBE EVM Metrics</h3>
      <MetricCard metadata={METRIC_DEFINITIONS.bac} value={data.bac} status="good" size="medium" />
      {/* Display other metrics - these are aggregated from child cost elements */}
    </div>
  );
}
```

### Batch EVM for Multiple Cost Elements

```tsx
import { useEVMMetricsBatch } from "@/features/evm";

function MultiCostElementEVM({ costElementIds }: { costElementIds: string[] }) {
  const { data, isLoading } = useEVMMetricsBatch("cost_element", costElementIds);

  if (isLoading) return <Spin />;
  if (!data) return <Empty />;

  return (
    <div>
      <h3>Aggregated EVM Metrics</h3>
      <Row gutter={16}>
        <Col span={8}>
          <MetricCard
            metadata={METRIC_DEFINITIONS.bac}
            value={data.aggregated.bac}
            status="good"
            size="medium"
          />
        </Col>
        <Col span={8}>
          <MetricCard
            metadata={METRIC_DEFINITIONS.cpi}
            value={data.aggregated.cpi}
            status={getMetricStatus("cpi", data.aggregated.cpi)}
            size="medium"
          />
        </Col>
        {/* Display other aggregated metrics */}
      </Row>
    </div>
  );
}
```

### Custom Metric Card with Status Calculation

```tsx
import { MetricCard, METRIC_DEFINITIONS, getMetricStatus } from "@/features/evm";

function CustomMetricDisplay({ metrics }: { metrics: EVMMetricsResponse }) {
  return (
    <Row gutter={16}>
      <Col span={8}>
        <MetricCard
          metadata={METRIC_DEFINITIONS.cpi}
          value={metrics.cpi}
          status={getMetricStatus("cpi", metrics.cpi)}
          size="medium"
          showDescription
        />
      </Col>
      <Col span={8}>
        <MetricCard
          metadata={METRIC_DEFINITIONS.spi}
          value={metrics.spi}
          status={getMetricStatus("spi", metrics.spi)}
          size="medium"
          showDescription
        />
      </Col>
      <Col span={8}>
        <MetricCard
          metadata={METRIC_DEFINITIONS.vac}
          value={metrics.vac}
          status={getMetricStatus("vac", metrics.vac)}
          size="medium"
          showDescription
        />
      </Col>
    </Row>
  );
}
```

---

## API Integration

### Endpoint Mapping

| Entity Type | Metrics Endpoint | Time-Series Endpoint | Batch Endpoint |
|-------------|------------------|----------------------|----------------|
| cost_element | `/api/v1/cost-elements/{id}/evm` | `/api/v1/cost-elements/{id}/evm/timeseries` | `/api/v1/evm/cost_element/batch` |
| wbe | `/api/v1/evm/wbe/{id}/metrics` | `/api/v1/evm/wbe/{id}/timeseries` | `/api/v1/evm/wbe/batch` |
| project | `/api/v1/evm/project/{id}/metrics` | `/api/v1/evm/project/{id}/timeseries` | `/api/v1/evm/project/batch` |

### Query Parameters

All EVM endpoints support the following query parameters:

- `control_date`: ISO 8601 date string for time-travel queries
- `branch`: Branch name for branching support
- `branch_mode`: "isolated" or "merge" (default: "merge")
- `granularity`: "day", "week", or "month" (time-series only)

### Response Format

#### Metrics Response

```json
{
  "entity_type": "cost_element",
  "entity_id": "uuid",
  "bac": 100000.00,
  "pv": 50000.00,
  "ac": 55000.00,
  "ev": 45000.00,
  "cv": -10000.00,
  "sv": -5000.00,
  "cpi": 0.82,
  "spi": 0.90,
  "eac": 121951.22,
  "vac": -21951.22,
  "etc": 66951.22,
  "control_date": "2024-01-15T00:00:00Z",
  "branch": "main"
}
```

#### Time-Series Response

```json
{
  "granularity": "week",
  "points": [
    {
      "date": "2024-01-01T00:00:00Z",
      "pv": 10000.00,
      "ev": 9500.00,
      "ac": 10500.00,
      "forecast": 10000.00,
      "actual": 10500.00
    }
  ],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-15T00:00:00Z",
  "total_points": 2
}
```

---

## Testing

### Component Tests

All EVM components have comprehensive unit tests:

```bash
# Run all EVM component tests
npm test -- features/evm/components

# Run specific component test
npm test -- MetricCard.test.tsx
```

### Hook Tests

Custom hooks have unit tests with mocked API responses:

```bash
# Run hook tests
npm test -- features/evm/api
```

### Integration Tests

EVM integration tests verify component composition and behavior:

```bash
# Run integration tests
npm test -- tests/integration/evm
```

---

## Performance Considerations

### Query Caching

- TanStack Query automatically caches EVM metrics by query key
- Time-series data is cached separately per granularity
- Cache invalidation occurs when TimeMachineContext changes

### Optimistic Updates

For future enhancement: Consider optimistic updates for cost registrations that affect EVM metrics.

### Batch Queries

When fetching metrics for multiple entities, use `useEVMMetricsBatch` instead of multiple `useEVMMetrics` calls for better performance.

---

## Future Enhancements

Out of scope for current implementation, deferred to backlog:

- **Multi-Entity Comparison View**: Side-by-side comparison of multiple entities
- **Benchmarking**: Compare against historical baselines
- **AI Insights**: Generate recommendations based on EVM trends
- **Real-Time Updates**: WebSocket-based metric updates
- **Materialized Views**: Performance optimization for large datasets
- **Custom Zoom Controls**: Beyond Ant Design built-in zoom
- **Internationalization**: Translations for metric descriptions

---

## Support

For issues, questions, or contributions related to the EVM feature, please refer to:

- Backend API docs: `/docs` (Swagger UI) when backend is running
- Backend implementation: `backend/app/services/evm_service.py`
- Frontend tests: `frontend/src/features/evm/**/__tests__/`
