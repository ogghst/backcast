/**
 * EChartsGauge Component
 *
 * Gauge chart component for displaying EVM metrics like CPI and SPI.
 * Supports semi-circle and full-circle variants with color-coded zones.
 *
 * @module features/evm/components/charts
 */

import React, { useMemo } from "react";
import { EChartsBaseChart, EChartsBaseChartProps } from "./EChartsBaseChart";
import {
  buildGaugeOptions,
  GaugeConfigOptions,
} from "../../utils/echartsConfig";
import { useEChartsColors } from "../../utils/echartsTheme";

export interface EChartsGaugeProps extends Omit<
  EChartsBaseChartProps,
  "option"
> {
  /** Current value to display (null = not available) */
  value: number | null;

  /** Minimum value for the gauge range */
  min: number;

  /** Maximum value for the gauge range */
  max: number;

  /** Label for the gauge (e.g., "CPI", "SPI") */
  label: string;

  /** Good threshold value (defaults to 1.0 for CPI/SPI) */
  goodThreshold?: number;

  /** Warning threshold percentage (default 0.9 = 90% of good) */
  warningThresholdPercent?: number;

  /** Chart variant: semi-circle or full-circle */
  variant?: "semi-circle" | "full-circle";

  /** Size of the gauge in pixels (affects height) */
  size?: number;
}

/**
 * Gauge chart component with ECharts
 */
export const EChartsGauge: React.FC<EChartsGaugeProps> = ({
  value,
  min,
  max,
  label,
  goodThreshold = 1.0,
  warningThresholdPercent = 0.9,
  variant = "semi-circle",
  size = 200,
  loading,
  error,
  className,
  style,
  onChartReady,
  onEvents,
  emptyDescription,
  delayRender,
}) => {
  // Get theme colors at top level (hook must be called at component level)
  const colors = useEChartsColors();

  // Build chart options using memoization
  const option = useMemo(() => {
    return buildGaugeOptions(
      {
        value,
        min,
        max,
        label,
        goodThreshold,
        warningThresholdPercent,
        variant,
        size,
      } as GaugeConfigOptions,
      colors,
    );
  }, [
    value,
    min,
    max,
    label,
    goodThreshold,
    warningThresholdPercent,
    variant,
    size,
    colors,
  ]);

  // Calculate chart height based on variant and size
  const chartHeight = useMemo(() => {
    if (variant === "semi-circle") {
      // Semi-circle needs less vertical space with new center positioning
      return Math.floor(size * 0.65);
    }
    return size;
  }, [size, variant]);

  // Merge default 100% width style with any custom style
  const chartStyle = useMemo(() => {
    return { width: "100%", ...style };
  }, [style]);

  return (
    <EChartsBaseChart
      option={option}
      loading={loading}
      error={error}
      height={chartHeight}
      className={className}
      style={chartStyle}
      onChartReady={onChartReady}
      onEvents={onEvents}
      showWhenEmpty={value === null}
      emptyDescription={emptyDescription ?? `${label} not available`}
      delayRender={delayRender}
    />
  );
};

/**
 * Default export for convenient importing
 */
export default EChartsGauge;
