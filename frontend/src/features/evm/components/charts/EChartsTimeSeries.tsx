/**
 * EChartsTimeSeries Component
 *
 * Time series chart component for EVM analysis.
 * Displays PV/EV/AC progression or Forecast vs Actual comparison over time.
 * Features zoom, pan, dual Y-axis support, and export to PNG.
 *
 * @module features/evm/components/charts
 */

import React, { useMemo, useRef, useCallback } from "react";
import { Button, Space, Radio } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import type { ECharts } from "echarts";
import ReactECharts from "echarts-for-react";
import { EChartsBaseChart, EChartsBaseChartProps } from "./EChartsBaseChart";
import {
  buildTimeSeriesOptions,
  TimeSeriesConfigOptions,
  createCurrencyFormatter,
  createDateFormatter,
  TimeSeriesChartType,
} from "../../utils/echartsConfig";
import { useEChartsTheme } from "../../utils/echartsTheme";
import {
  transformEVMProgressionData,
  transformPerformanceIndicesData,
  TransformedSeries,
} from "../../utils/dataTransformers";
import type {
  EVMTimeSeriesResponse,
  EVMTimeSeriesGranularity,
} from "../../types";

const { Group: RadioGroup, Button: RadioButton } = Radio;

export interface EChartsTimeSeriesProps extends Omit<
  EChartsBaseChartProps,
  "option"
> {
  /** Time-series data from the API */
  timeSeries: EVMTimeSeriesResponse | undefined;

  /** Chart type to display */
  chartType?: TimeSeriesChartType;

  /** Show both charts (progression and comparison) */
  showBothCharts?: boolean;

  /** Show DataZoom slider and inside zoom */
  showZoom?: boolean;

  /** Show export to PNG button */
  showExport?: boolean;

  /** Use dual Y-axis when showing both charts */
  dualYAxis?: boolean;

  /** Current granularity */
  currentGranularity?: EVMTimeSeriesGranularity;

  /** Callback when granularity changes */
  onGranularityChange?: (granularity: EVMTimeSeriesGranularity) => void;

  /** Currency for formatting (default EUR) */
  currency?: string;

  /** Custom series data (overrides timeSeries transformation) */
  customSeries?: TransformedSeries[];

  /** Whether to fill the container height (for both charts mode) */
  fillContainer?: boolean;
}

/**
 * Time series chart component with ECharts
 */
export const EChartsTimeSeries: React.FC<EChartsTimeSeriesProps> = ({
  timeSeries,
  chartType = "evm-progression",
  showBothCharts = false,
  showZoom = true,
  showExport = false,
  dualYAxis = false,
  currentGranularity = "week",
  onGranularityChange,
  currency = "EUR",
  customSeries,
  loading,
  error,
  className,
  style,
  onChartReady,
  emptyDescription,
  delayRender = false,
  height,
  fillContainer = false,
}) => {
  const chartRef = useRef<ReactECharts | null>(null);
  const chart2Ref = useRef<ReactECharts | null>(null);

  // Get theme configuration at top level (hook must be called at component level)
  const echartsTheme = useEChartsTheme();

  // Create formatters
  const currencyFormatter = useMemo(
    () => createCurrencyFormatter(currency),
    [currency],
  );

  const dateFormatter = useMemo(
    () => createDateFormatter(currentGranularity as EVMTimeSeriesGranularity),
    [currentGranularity],
  );

  // Transform data for charts
  const progressionSeries = useMemo(() => {
    if (customSeries) return customSeries;
    if (timeSeries) return transformEVMProgressionData(timeSeries);
    return [];
  }, [customSeries, timeSeries]);

  const performanceIndicesSeries = useMemo(() => {
    if (timeSeries) return transformPerformanceIndicesData(timeSeries);
    return [];
  }, [timeSeries]);

  // Build chart options
  const progressionOptions = useMemo(() => {
    if (progressionSeries.length === 0) return null;

    return buildTimeSeriesOptions(
      {
        chartType: "evm-progression",
        series: progressionSeries,
        showZoom,
        dualYAxis,
        yFormatter: currencyFormatter,
        xFormatter: dateFormatter,
      } as TimeSeriesConfigOptions,
      echartsTheme,
    );
  }, [
    progressionSeries,
    showZoom,
    dualYAxis,
    currencyFormatter,
    dateFormatter,
    echartsTheme,
  ]);

  const performanceIndicesOptions = useMemo(() => {
    if (performanceIndicesSeries.length === 0) return null;

    return buildTimeSeriesOptions(
      {
        chartType: "performance-indices",
        series: performanceIndicesSeries,
        showZoom,
        dualYAxis,
        yFormatter: (v) => v.toFixed(2),
        xFormatter: dateFormatter,
      } as TimeSeriesConfigOptions,
      echartsTheme,
    );
  }, [
    performanceIndicesSeries,
    showZoom,
    dualYAxis,
    dateFormatter,
    echartsTheme,
  ]);

  // Export chart to PNG
  const handleExport = useCallback(() => {
    const charts = [
      chartRef.current?.getEchartsInstance?.(),
      chart2Ref.current?.getEchartsInstance?.(),
    ].filter(Boolean) as ECharts[];

    if (charts.length === 0) return;

    // Export each chart
    charts.forEach((chart, index) => {
      const url = chart.getDataURL({
        type: "png",
        pixelRatio: 2,
        backgroundColor: "#fff",
      });

      const link = document.createElement("a");
      link.download = `evm-chart-${chartType}-${index + 1}-${Date.now()}.png`;
      link.href = url;
      link.click();
    });
  }, [chartType]);

  // Handle chart ready
  const handleChartReady = useCallback(
    (chart: ECharts) => {
      if (onChartReady) {
        onChartReady(chart);
      }
    },
    [onChartReady],
  );

  // Header with controls
  const renderHeader = () => {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: fillContainer ? 12 : 16,
        }}
      >
        <div />
        <Space>
          {onGranularityChange && (
            <RadioGroup
              value={currentGranularity}
              onChange={(e) =>
                onGranularityChange(e.target.value as EVMTimeSeriesGranularity)
              }
              size="small"
            >
              <RadioButton value="day">Day</RadioButton>
              <RadioButton value="week">Week</RadioButton>
              <RadioButton value="month">Month</RadioButton>
            </RadioGroup>
          )}
          {showExport && (
            <Button
              icon={<DownloadOutlined />}
              size="small"
              onClick={handleExport}
            >
              Export
            </Button>
          )}
        </Space>
      </div>
    );
  };

  // Check if we have data
  const hasData =
    (chartType === "evm-progression" || showBothCharts) &&
    progressionSeries.length > 0;
  const hasPerformanceIndicesData =
    (chartType === "performance-indices" || showBothCharts) &&
    performanceIndicesSeries.length > 0;

  // Single chart mode
  if (!showBothCharts) {
    const options =
      chartType === "evm-progression" ? progressionOptions : performanceIndicesOptions;

    if (!options) {
      return (
        <EChartsBaseChart
          option={{}}
          loading={loading}
          error={error}
          emptyDescription={emptyDescription ?? "No time-series data available"}
          height={height ?? 300}
          className={className}
          style={style}
          delayRender={delayRender}
        />
      );
    }

    return (
      <div className={className} style={style}>
        {renderHeader()}
        <EChartsBaseChart
          ref={chartRef}
          option={options}
          loading={loading}
          error={error}
          height={height ?? 300}
          onChartReady={handleChartReady}
          delayRender={delayRender}
        />
      </div>
    );
  }

  // Both charts mode
  const containerStyle = fillContainer
    ? { display: "flex", flexDirection: "column" as const, height: "100%", overflow: "hidden" as const }
    : {};

  const chartWrapperStyle = fillContainer
    ? { flex: 1, display: "flex", flexDirection: "column" as const, minHeight: 0, overflow: "hidden" as const }
    : {};

  const chartContainerStyle = fillContainer
    ? { flex: 1, minHeight: 0, display: "flex", flexDirection: "column" as const }
    : {};

  const chartHeight = fillContainer ? "100%" : (height ?? 300);

  return (
    <div className={className} style={{ ...style, ...containerStyle }}>
      {renderHeader()}
      {fillContainer ? (
        <>
          {hasData && progressionOptions && (
            <div style={{ ...chartWrapperStyle, marginBottom: hasPerformanceIndicesData ? 12 : 0 }}>
              <div
                style={{
                  marginBottom: 8,
                  fontSize: 14,
                  fontWeight: 500,
                  color: "rgba(0,0,0,0.88)",
                  flexShrink: 0,
                }}
              >
                EVM Progression
                <span
                  style={{
                    marginLeft: 8,
                    fontSize: 12,
                    color: "rgba(0,0,0,0.45)",
                    fontWeight: 400,
                  }}
                >
                  PV (Planned Value), EV (Earned Value), AC (Actual Cost)
                </span>
              </div>
              <div style={chartContainerStyle}>
                <EChartsBaseChart
                  ref={chartRef}
                  option={progressionOptions}
                  loading={loading}
                  error={error}
                  height={chartHeight}
                  onChartReady={handleChartReady}
                  delayRender={delayRender}
                />
              </div>
            </div>
          )}
          {hasPerformanceIndicesData && performanceIndicesOptions && (
            <div style={chartWrapperStyle}>
              <div
                style={{
                  marginBottom: 8,
                  fontSize: 14,
                  fontWeight: 500,
                  color: "rgba(0,0,0,0.88)",
                  flexShrink: 0,
                }}
              >
                Performance Indices (CPI vs SPI)
                <span
                  style={{
                    marginLeft: 8,
                    fontSize: 12,
                    color: "rgba(0,0,0,0.45)",
                    fontWeight: 400,
                  }}
                >
                  Cost Performance Index (CPI), Schedule Performance Index (SPI)
                </span>
              </div>
              <div style={chartContainerStyle}>
                <EChartsBaseChart
                  ref={chart2Ref}
                  option={performanceIndicesOptions}
                  loading={loading}
                  error={error}
                  height={chartHeight}
                  onChartReady={handleChartReady}
                  delayRender={delayRender}
                />
              </div>
            </div>
          )}
        </>
      ) : (
        <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
          {hasData && progressionOptions && (
            <div>
              <div
                style={{
                  marginBottom: 8,
                  fontSize: 14,
                  fontWeight: 500,
                  color: "rgba(0,0,0,0.88)",
                }}
              >
                EVM Progression
                <span
                  style={{
                    marginLeft: 8,
                    fontSize: 12,
                    color: "rgba(0,0,0,0.45)",
                    fontWeight: 400,
                  }}
                >
                  PV (Planned Value), EV (Earned Value), AC (Actual Cost)
                </span>
              </div>
              <EChartsBaseChart
                ref={chartRef}
                option={progressionOptions}
                loading={loading}
                error={error}
                height={height ?? 300}
                onChartReady={handleChartReady}
                delayRender={delayRender}
              />
            </div>
          )}
          {hasPerformanceIndicesData && performanceIndicesOptions && (
            <div>
              <div
                style={{
                  marginBottom: 8,
                  fontSize: 14,
                  fontWeight: 500,
                  color: "rgba(0,0,0,0.88)",
                }}
              >
                Performance Indices (CPI vs SPI)
                <span
                  style={{
                    marginLeft: 8,
                    fontSize: 12,
                    color: "rgba(0,0,0,0.45)",
                    fontWeight: 400,
                  }}
                >
                  Cost Performance Index (CPI), Schedule Performance Index (SPI)
                </span>
              </div>
              <EChartsBaseChart
                ref={chart2Ref}
                option={performanceIndicesOptions}
                loading={loading}
                error={error}
                height={height ?? 300}
                onChartReady={handleChartReady}
                delayRender={delayRender}
              />
            </div>
          )}
        </Space>
      )}
    </div>
  );
};

/**
 * Default export for convenient importing
 */
export default EChartsTimeSeries;
