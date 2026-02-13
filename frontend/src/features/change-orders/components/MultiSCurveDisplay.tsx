/**
 * MultiSCurveDisplay Component
 *
 * Container component that renders all 4 EVM S-Curve charts (Budget, PV, EV, AC)
 * in a responsive grid layout for change order impact analysis.
 *
 * Context: Used in the ImpactAnalysisDashboard S-Curve tab to display the complete
 * time-series comparison between Main Branch and Change Order MERGE mode.
 *
 * @module features/change-orders/components
 */

import { useMemo } from "react";
import { Row, Col, Empty } from "antd";
import type { TimeSeriesData } from "@/api/generated";
import { SCurveChart, type SCurveMetric } from "./SCurveChart";

/**
 * Props for MultiSCurveDisplay component.
 */
export interface MultiSCurveDisplayProps {
  /** Array of time series data for all metrics (budget, pv, ev, ac) */
  timeSeries: TimeSeriesData[] | undefined;
  /** Loading state */
  loading?: boolean;
  /** Show PNG export button on each chart (default: false) */
  showExport?: boolean;
  /** Layout mode: grid (2x2) or stacked (1 column) (default: "grid") */
  layout?: "grid" | "stacked";
  /** Additional CSS class name */
  className?: string;
}

/**
 * Chart configuration for each metric.
 */
interface ChartConfig {
  metricName: SCurveMetric;
  title: string;
  color?: string;
}

/**
 * All 4 EVM metrics to display.
 */
const CHART_CONFIGS: ChartConfig[] = [
  { metricName: "budget", title: "Budget Allocation", color: "#5b8ff9" },
  { metricName: "pv", title: "Planned Value (PV)", color: "#5b8ff9" },
  { metricName: "ev", title: "Earned Value (EV)", color: "#5ad8a6" },
  { metricName: "ac", title: "Actual Cost (AC)", color: "#5d7092" },
];

/**
 * Extract TimeSeriesData for a specific metric from the array.
 *
 * @param timeSeries - Array of time series data
 * @param metricName - Metric to extract
 * @returns TimeSeriesData for the metric, or undefined if not found
 */
function extractMetricData(
  timeSeries: TimeSeriesData[] | undefined,
  metricName: string,
): TimeSeriesData | undefined {
  return timeSeries?.find((ts) => ts.metric_name === metricName);
}

/**
 * MultiSCurveDisplay Component
 *
 * Renders a responsive grid of 4 S-Curve charts showing Budget, PV, EV, and AC
 * progression over time with Main Branch vs Change Order MERGE comparison.
 */
export const MultiSCurveDisplay = ({
  timeSeries,
  loading = false,
  showExport = false,
  layout = "grid",
  className,
}: MultiSCurveDisplayProps) => {
  // Extract each metric's data (memoized to avoid recalculation)
  const metricData = useMemo(() => {
    const data: Record<string, TimeSeriesData | undefined> = {};
    CHART_CONFIGS.forEach((config) => {
      data[config.metricName] = extractMetricData(timeSeries, config.metricName);
    });
    return data;
  }, [timeSeries]);

  // Check if we have any data at all
  const hasAnyData = CHART_CONFIGS.some(
    (config) => metricData[config.metricName]?.data_points?.length,
  );

  // Handle loading state
  if (loading) {
    return (
      <div className={className} style={{ padding: 24 }}>
        {/* Loading is handled by individual chart components */}
        <Row gutter={[16, 16]}>
          {CHART_CONFIGS.map((config) => (
            <Col key={config.metricName} xs={24} sm={12} lg={12}>
              <SCurveChart
                title={config.title}
                metricName={config.metricName}
                data={undefined}
                color={config.color}
                loading={true}
                showExport={showExport}
              />
            </Col>
          ))}
        </Row>
      </div>
    );
  }

  // Handle empty state (no data at all)
  if (!timeSeries || timeSeries.length === 0 || !hasAnyData) {
    return (
      <div
        className={className}
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: 48,
        }}
      >
        <Empty
          description="No time-series data available"
          style={{ margin: 0 }}
        />
      </div>
    );
  }

  // Determine column span based on layout
  const getColSpan = () => {
    if (layout === "stacked") {
      return { xs: 24, sm: 24, lg: 24 };
    }
    return { xs: 24, sm: 12, lg: 12 };
  };

  const colSpan = getColSpan();

  return (
    <div className={className}>
      <Row gutter={[16, 16]}>
        {CHART_CONFIGS.map((config) => (
          <Col
            key={config.metricName}
            xs={colSpan.xs}
            sm={colSpan.sm}
            lg={colSpan.lg}
          >
            <SCurveChart
              title={config.title}
              metricName={config.metricName}
              data={metricData[config.metricName]}
              color={config.color}
              loading={false}
              showExport={showExport}
            />
          </Col>
        ))}
      </Row>
    </div>
  );
};

export default MultiSCurveDisplay;
