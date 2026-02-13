/**
 * EChartsBaseChart Component
 *
 * Base wrapper component for all ECharts-based charts.
 * Provides consistent responsive behavior, loading states, and error handling.
 *
 * @module features/evm/components/charts
 */

import React, { useRef, useCallback, useEffect, useState } from "react";
import { Spin, Alert, Empty } from "antd";
import ReactECharts from "echarts-for-react";
import type { EChartsOption, EChartsReactProps } from "echarts-for-react";
import type { ECharts } from "echarts";

export interface EChartsBaseChartProps {
  /** ECharts option object */
  option: EChartsOption;
  /** Loading state */
  loading?: boolean;
  /** Error message */
  error?: string | null;
  /** Whether to show the chart when empty (no data) */
  showWhenEmpty?: boolean;
  /** Chart height in pixels */
  height?: number | string;
  /** Additional CSS class name */
  className?: string;
  /** Additional styles */
  style?: React.CSSProperties;
  /** Chart theme (not used, keeping for API compatibility) */
  theme?: string;
  /** ECharts instance initialization callback */
  onChartReady?: (chart: ECharts) => void;
  /** Chart events */
  onEvents?: EChartsReactProps["onEvents"];
  /** Whether the chart should be resizable */
  resizable?: boolean;
  /** Custom empty description */
  emptyDescription?: string;
  /** Custom empty image */
  emptyImage?: React.ReactNode;
  /** Whether to delay rendering (for modals) */
  delayRender?: boolean;
}

/**
 * Base wrapper component for ECharts
 */
export const EChartsBaseChart = React.forwardRef<
  ReactECharts,
  EChartsBaseChartProps
>(
  (
    {
      option,
      loading = false,
      error = null,
      showWhenEmpty = false,
      height = 300,
      className,
      style,
      onChartReady,
      onEvents,
      resizable = true,
      emptyDescription = "No data available",
      emptyImage,
      delayRender = false,
    },
    ref,
  ) => {
    const chartRef = useRef<ReactECharts | null>(null);
    const resizeObserverRef = useRef<ResizeObserver | null>(null);
    const [isReady, setIsReady] = useState(!delayRender);
    const containerStyle = React.useMemo<React.CSSProperties>(() => {
      const isPercentageHeight = typeof height === "string" && height.endsWith("%");
      return {
        height: typeof height === "number" ? `${height}px` : height,
        width: "100%",
        minHeight: isPercentageHeight ? undefined : (typeof height === "number" ? `${height}px` : height),
        ...style,
      };
    }, [height, style]);

    // Delay rendering for modals to allow DOM to settle
    useEffect(() => {
      if (delayRender) {
        const timer = setTimeout(() => {
          setIsReady(true);
        }, 50);
        return () => clearTimeout(timer);
      }
    }, [delayRender]);

    // Handle chart ready
    const handleChartReady = useCallback(
      (chart: ECharts) => {
        // Force a resize after chart is ready to ensure proper dimensions
        setTimeout(() => {
          chart.resize();
        }, 0);

        if (onChartReady) {
          onChartReady(chart);
        }
      },
      [onChartReady],
    );

    // Setup resize observer for responsive behavior
    const chartRefCallback = useCallback(
      (node: ReactECharts | null) => {
        // Handle local ref
        chartRef.current = node;

        // Handle forwarded ref
        if (typeof ref === "function") {
          ref(node);
        } else if (ref) {
          (ref as React.MutableRefObject<ReactECharts | null>).current = node;
        }

        if (node) {
          if (resizable) {
            // Cleanup previous observer
            if (resizeObserverRef.current) {
              resizeObserverRef.current.disconnect();
            }

            // Create new observer
            resizeObserverRef.current = new ResizeObserver(() => {
              const chart = node.getEchartsInstance();
              if (chart && !chart.isDisposed()) {
                chart.resize();
              }
            });

            // Observe the chart container
            const container = node.echartsElement?.parentElement;
            if (container) {
              resizeObserverRef.current.observe(container);
            }

            // Also observe the parent's parent for modal scenarios
            const parentContainer = container?.parentElement;
            if (parentContainer) {
              resizeObserverRef.current.observe(parentContainer);
            }
          }

          // Trigger an initial resize after mount
          setTimeout(() => {
            const chart = node.getEchartsInstance();
            if (chart && !chart.isDisposed()) {
              chart.resize();
            }
          }, 100);
        } else {
          // Cleanup on unmount
          if (resizeObserverRef.current) {
            resizeObserverRef.current.disconnect();
            resizeObserverRef.current = null;
          }
        }
      },
      [resizable, ref],
    );

    // Show loading state
    if (loading) {
      return (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            ...containerStyle,
          }}
          className={className}
        >
          <Spin size="large" />
        </div>
      );
    }

    // Show error state
    if (error) {
      return (
        <div className={className} style={containerStyle}>
          <Alert
            message="Chart Error"
            description={error}
            type="error"
            showIcon
            closable
          />
        </div>
      );
    }

    // Check if chart has data
    const hasData = checkHasData(option);

    // Show empty state
    if (!hasData && !showWhenEmpty) {
      return (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            ...containerStyle,
          }}
          className={className}
        >
          <Empty
            description={emptyDescription}
            image={emptyImage ?? Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </div>
      );
    }

    // Wait for ready state if delayRender is enabled
    if (!isReady) {
      return (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            ...containerStyle,
          }}
          className={className}
        >
          <Spin size="small" />
        </div>
      );
    }

    // Common chart props
    const chartProps: EChartsReactProps = {
      ref: chartRefCallback,
      option,
      style: containerStyle,
      className,
      onChartReady: handleChartReady,
      onEvents,
      notMerge: false,
      lazyUpdate: true,
      showLoading: false,
    };

    return <ReactECharts {...chartProps} />;
  },
);

EChartsBaseChart.displayName = "EChartsBaseChart";

/**
 * Check if an ECharts option has data to display.
 * Recursively checks series data for non-empty values.
 */
function checkHasData(option: EChartsOption): boolean {
  // Check series data
  if (option.series) {
    const series = Array.isArray(option.series)
      ? option.series
      : [option.series];

    for (const s of series) {
      if (s) {
        // Check data array
        if (s.data) {
          const data = Array.isArray(s.data) ? s.data : [];
          if (data.length > 0) {
            return true;
          }
        }

        // For gauge charts, check value
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if (s.type === "gauge" && (s as any).data) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const gaugeData = (s as any).data;
          if (Array.isArray(gaugeData) && gaugeData.length > 0) {
            const value = gaugeData[0].value;
            if (value !== null && value !== undefined) {
              return true;
            }
          }
        }
      }
    }
  }

  // Check dataset
  if (option.dataset) {
    const datasets = Array.isArray(option.dataset)
      ? option.dataset
      : [option.dataset];
    for (const ds of datasets) {
      if (ds && ds.source && Array.isArray(ds.source) && ds.source.length > 0) {
        return true;
      }
    }
  }

  return false;
}

export default EChartsBaseChart;
