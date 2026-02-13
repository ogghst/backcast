/**
 * ECharts Theme Configuration
 *
 * Maps Ant Design theme tokens to ECharts colors and styles.
 * Ensures consistent styling across the application.
 *
 * @module features/evm/utils/echartsTheme
 */

import { theme } from "antd";
import { useMemo } from "react";

/**
 * Color palette for ECharts charts.
 */
export interface EChartsColorPalette {
  // Primary colors for series
  primary: string;
  success: string;
  warning: string;
  error: string;
  info: string;

  // Metric colors (matching existing Ant Design chart colors)
  pv: string; // Blue - Planned Value
  ev: string; // Green - Earned Value
  ac: string; // Gray - Actual Cost
  forecast: string; // Orange - Forecast
  actual: string; // Red - Actual

  // Gauge zone colors
  gaugeGood: string; // Green
  gaugeWarning: string; // Yellow
  gaugeBad: string; // Red

  // Neutral colors
  text: string;
  textSecondary: string;
  border: string;
  bg: string;
}

/**
 * Axis configuration for ECharts.
 */
export interface EChartsAxisConfig {
  axisLine: { lineStyle: { color: string } };
  axisLabel: { color: string; fontSize: number };
  axisTick: { lineStyle: { color: string } };
  splitLine: { lineStyle: { color: string; type: "dashed" } };
}

/**
 * Tooltip configuration for ECharts.
 */
export interface EChartsTooltipConfig {
  backgroundColor: string;
  borderColor: string;
  borderWidth: number;
  textStyle: { color: string; fontSize: number };
  padding: number[];
  extraCssText: string;
}

/**
 * Legend configuration for ECharts.
 */
export interface EChartsLegendConfig {
  textStyle: { color: string; fontSize: number };
  itemGap: number;
  itemWidth: number;
  itemHeight: number;
}

/**
 * Hook to get ECharts color palette based on Ant Design theme.
 * Returns colors for chart series, axes, and UI elements.
 *
 * This must be called at the component level (top level), not inside utility functions.
 */
export function useEChartsColors(): EChartsColorPalette {
  const { token } = theme.useToken();

  return {
    // Primary colors for series
    primary: token.colorPrimary,
    success: token.colorSuccess,
    warning: token.colorWarning,
    error: token.colorError,
    info: token.colorInfo,

    // Metric colors (matching existing Ant Design chart colors)
    pv: "#5b8ff9", // Blue - Planned Value
    ev: "#5ad8a6", // Green - Earned Value
    ac: "#5d7092", // Gray - Actual Cost
    forecast: "#faad14", // Orange - Forecast
    actual: "#ff4d4f", // Red - Actual

    // Gauge zone colors
    gaugeGood: "#52c41a", // Green
    gaugeWarning: "#faad14", // Yellow
    gaugeBad: "#ff4d4f", // Red

    // Neutral colors
    text: token.colorText,
    textSecondary: token.colorTextSecondary,
    border: token.colorBorder,
    bg: token.colorBgContainer,
  };
}

/**
 * Build ECharts axis configuration with given colors.
 *
 * @param colors - Color palette from useEChartsColors()
 * @param borderSecondary - Secondary border color from theme
 */
export function buildAxisConfig(colors: EChartsColorPalette, borderSecondary: string): EChartsAxisConfig {
  return {
    axisLine: {
      lineStyle: {
        color: colors.border,
      },
    },
    axisLabel: {
      color: colors.textSecondary,
      fontSize: 12,
    },
    axisTick: {
      lineStyle: {
        color: colors.border,
      },
    },
    splitLine: {
      lineStyle: {
        color: borderSecondary,
        type: "dashed" as const,
      },
    },
  };
}

/**
 * Build ECharts tooltip configuration with given colors and theme.
 *
 * @param colors - Color palette from useEChartsColors()
 * @param bgElevated - Elevated background color from theme
 * @param boxShadow - Box shadow from theme
 * @param borderRadius - Border radius from theme
 */
export function buildTooltipConfig(
  colors: EChartsColorPalette,
  bgElevated: string,
  boxShadow: string,
  borderRadius: number
): EChartsTooltipConfig {
  return {
    backgroundColor: bgElevated,
    borderColor: colors.border,
    borderWidth: 1,
    textStyle: {
      color: colors.text,
      fontSize: 12,
    },
    padding: [8, 12],
    extraCssText: `box-shadow: ${boxShadow}; border-radius: ${borderRadius}px;`,
  };
}

/**
 * Build ECharts legend configuration with given colors.
 *
 * @param colors - Color palette from useEChartsColors()
 */
export function buildLegendConfig(colors: EChartsColorPalette): EChartsLegendConfig {
  return {
    textStyle: {
      color: colors.text,
      fontSize: 12,
    },
    itemGap: 16,
    itemWidth: 16,
    itemHeight: 12,
  };
}

/**
 * Hook to get all ECharts theme configuration at once.
 * Returns colors, axis config, tooltip config, and legend config.
 *
 * This is the recommended way to get theme configuration for charts.
 */
export function useEChartsTheme(): {
  colors: EChartsColorPalette;
  axisConfig: EChartsAxisConfig;
  tooltipConfig: EChartsTooltipConfig;
  legendConfig: EChartsLegendConfig;
} {
  const { token } = theme.useToken();
  const colors = useEChartsColors();

  const axisConfig = useMemo(
    () => buildAxisConfig(colors, token.colorBorderSecondary),
    [colors, token.colorBorderSecondary]
  );

  const tooltipConfig = useMemo(
    () => buildTooltipConfig(colors, token.colorBgElevated, token.boxShadow, token.borderRadius),
    [colors, token.colorBgElevated, token.boxShadow, token.borderRadius]
  );

  const legendConfig = useMemo(() => buildLegendConfig(colors), [colors]);

  return {
    colors,
    axisConfig,
    tooltipConfig,
    legendConfig,
  };
}

/**
 * Complete ECharts theme object for registerTheme.
 * Can be used with echarts.registerTheme() for global theme application.
 */
export const antDesignTheme = {
  color: [
    "#5b8ff9", // PV - Blue
    "#5ad8a6", // EV - Green
    "#5d7092", // AC - Gray
    "#faad14", // Forecast - Orange
    "#ff4d4f", // Actual - Red
    "#13c2c2", // Teal
    "#722ed1", // Purple
    "#eb2f96", // Pink
  ],
  backgroundColor: "transparent",
  textStyle: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  title: {
    textStyle: {
      fontWeight: 600,
    },
  },
  line: {
    smooth: true,
    smoothMonotone: "x" as const,
  },
};
