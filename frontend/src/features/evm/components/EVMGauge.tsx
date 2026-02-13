/**
 * EVMGauge Component
 *
 * Semi-circle gauge component for displaying CPI/SPI ratios.
 * Shows value with needle indicator and color-coded zones (green/yellow/red).
 *
 * Now implemented using Apache ECharts for enhanced visualizations.
 *
 * Features:
 * - Semi-circle ECharts gauge design
 * - Needle indicator pointing to current value
 * - Color-coded zones based on target ranges
 * - Accessible with proper ARIA labels
 * - Smooth animations and responsive design
 */

import React from "react";
import { Typography } from "antd";
import { EChartsGauge } from "./charts/EChartsGauge";

const { Text } = Typography;

export interface EVMGaugeProps {
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

  /** Size of the gauge in pixels (default 200) */
  size?: number;

  /** Stroke width of the gauge arc (default 20) - kept for API compatibility */
  strokeWidth?: number;
}

/**
 * Main EVMGauge component with label using ECharts
 */
export const EVMGauge: React.FC<EVMGaugeProps> = ({
  value,
  min,
  max,
  label,
  goodThreshold = 1.0,
  warningThresholdPercent = 0.9,
  size = 200,
  // strokeWidth: Accepted for API compatibility but not used in ECharts version
}) => {
  return (
    <div style={{ textAlign: "center" }}>
      <Text strong style={{ fontSize: 14, display: "block", marginBottom: 8 }}>
        {label}
      </Text>
      <EChartsGauge
        value={value}
        min={min}
        max={max}
        label={label}
        goodThreshold={goodThreshold}
        warningThresholdPercent={warningThresholdPercent}
        variant="semi-circle"
        size={size}
      />
    </div>
  );
};

export default EVMGauge;
