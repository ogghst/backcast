/**
 * EVMTimeSeriesChart Component
 *
 * Displays time-series charts for EVM analysis:
 * 1. EVM Progression Chart: Shows PV (Planned Value), EV (Earned Value), and AC (Actual Cost) over time
 * 2. Cost Comparison Chart: Shows Forecast vs Actual costs over time
 *
 * Now implemented using Apache ECharts for enhanced visualizations.
 *
 * Features:
 * - Granularity selector (day/week/month)
 * - Built-in zoom and pan support
 * - Loading and empty states
 * - Responsive design
 * - Export to PNG functionality
 *
 * @module features/evm/components
 */

import { Card, Typography } from "antd";
import { EChartsTimeSeries } from "./charts/EChartsTimeSeries";
import type { EVMTimeSeriesResponse, EVMTimeSeriesGranularity } from "../types";

const { Title } = Typography;

interface EVMTimeSeriesChartProps {
  /** Time-series data from the API */
  timeSeries: EVMTimeSeriesResponse | undefined;
  /** Loading state */
  loading?: boolean;
  /** Callback when granularity changes */
  onGranularityChange: (granularity: EVMTimeSeriesGranularity) => void;
  /** Current granularity (optional, derived from timeSeries if not provided) */
  currentGranularity?: EVMTimeSeriesGranularity;
  /** Show export button */
  showExport?: boolean;
  /** Whether to delay rendering (for modals) */
  delayRender?: boolean;
  /** Whether to render without the Card wrapper */
  headless?: boolean;
  /** Chart height */
  height?: number | string;
}

/**
 * EVMTimeSeriesChart Component using ECharts
 */
export const EVMTimeSeriesChart = ({
  timeSeries,
  loading = false,
  onGranularityChange,
  currentGranularity,
  showExport = false,
  delayRender = false,
  headless = false,
  height,
}: EVMTimeSeriesChartProps) => {
  // Get current granularity from timeSeries or prop
  const granularity =
    currentGranularity ||
    timeSeries?.granularity ||
    ("week" as EVMTimeSeriesGranularity);

  const chartContent = (
    <EChartsTimeSeries
      timeSeries={timeSeries}
      showBothCharts={true}
      showZoom={true}
      showExport={showExport}
      currentGranularity={granularity}
      onGranularityChange={onGranularityChange}
      currency="EUR"
      delayRender={delayRender}
      height={height}
    />
  );

  if (headless) {
    return chartContent;
  }

  // Wrap in Card for consistent styling
  return (
    <Card
      title={
        <Title level={4} style={{ margin: 0 }}>
          EVM Time Series Analysis
        </Title>
      }
      loading={loading}
    >
      {chartContent}
    </Card>
  );
};

export default EVMTimeSeriesChart;
