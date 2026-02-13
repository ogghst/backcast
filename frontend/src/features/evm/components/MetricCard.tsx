import React from "react";
import { Card, theme, Typography, Space } from "antd";
import { MetricMetadata } from "../types";

const { Text } = Typography;

/**
 * Size configuration for MetricCard variants.
 */
interface SizeConfig {
  padding: string;
  titleFontSize: string;
  valueFontSize: string;
  descriptionFontSize: string;
}

/**
 * Size configurations for different card sizes.
 */
const SIZE_CONFIGS: Record<"small" | "medium" | "large", SizeConfig> = {
  small: {
    padding: "8px 12px",
    titleFontSize: "12px",
    valueFontSize: "16px",
    descriptionFontSize: "10px",
  },
  medium: {
    padding: "12px 16px",
    titleFontSize: "14px",
    valueFontSize: "20px",
    descriptionFontSize: "11px",
  },
  large: {
    padding: "16px 20px",
    titleFontSize: "16px",
    valueFontSize: "24px",
    descriptionFontSize: "12px",
  },
};

/**
 * Status color mapping for EVM metric indicators.
 */
const STATUS_COLORS: Record<"good" | "warning" | "bad", string> = {
  good: "#52c41a", // green
  warning: "#faad14", // orange
  bad: "#ff4d4f", // red
};

export interface MetricCardProps {
  /** Metadata for the metric */
  metadata: MetricMetadata;
  /** Value of the metric (can be null if not calculated) */
  value: number | null;
  /** Status indicator for color coding */
  status: "good" | "warning" | "bad";
  /** Size variant for the card */
  size: "small" | "medium" | "large";
  /** Whether to show the description */
  showDescription?: boolean;
}

/**
 * Format a numeric value based on the format type.
 *
 * @param value - The numeric value to format (can be null)
 * @param format - The format type (currency, percentage, or number)
 * @returns Formatted string representation of the value
 */
const formatValue = (
  value: number | null,
  format: "currency" | "percentage" | "number",
): string => {
  if (value === null || value === undefined) return "N/A";

  switch (format) {
    case "currency":
      return new Intl.NumberFormat("en-IE", {
        style: "currency",
        currency: "EUR",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value);

    case "percentage":
      return new Intl.NumberFormat("en-IE", {
        style: "percent",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(value);

    case "number":
      return new Intl.NumberFormat("en-IE", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value);

    default:
      return String(value);
  }
};

/**
 * MetricCard Component
 *
 * A reusable card component for displaying individual EVM metrics.
 * Shows metric value, label, description, and status indicator.
 *
 * Features:
 * - Color-coded status border (good=green, warning=orange, bad=red)
 * - Three size variants (small, medium, large)
 * - Optional metric description
 * - Proper value formatting (currency, percentage, number)
 * - Accessible with ARIA labels
 *
 * @example
 * ```tsx
 * <MetricCard
 *   metadata={METRIC_DEFINITIONS.cpi}
 *   value={1.07}
 *   status="good"
 *   size="medium"
 *   showDescription
 * />
 * ```
 */
export const MetricCard: React.FC<MetricCardProps> = ({
  metadata,
  value,
  status,
  size,
  showDescription = false,
}) => {
  const { token } = theme.useToken();

  const formattedValue = formatValue(value, metadata.format);
  const statusColor = STATUS_COLORS[status];
  const sizeConfig = SIZE_CONFIGS[size];

  return (
    <Card
      variant="outlined"
      style={{
        borderColor: statusColor,
        borderWidth: "2px",
        borderRadius: token.borderRadiusLG,
        backgroundColor: token.colorBgContainer,
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
      styles={{
        body: {
          padding: sizeConfig.padding,
        },
      }}
      aria-label={`${metadata.name}: ${formattedValue}`}
      aria-describedby={
        showDescription ? `metric-desc-${metadata.key}` : undefined
      }
    >
      <Space
        orientation="vertical"
        size={size === "small" ? "small" : "middle"}
        style={{ width: "100%" }}
      >
        {/* Metric Label */}
        <Text
          type="secondary"
          style={{
            fontSize: sizeConfig.titleFontSize,
            fontWeight: 500,
            display: "block",
          }}
        >
          {metadata.name}
        </Text>

        {/* Metric Value */}
        <Text
          strong
          style={{
            fontSize: sizeConfig.valueFontSize,
            color: statusColor,
            display: "block",
          }}
        >
          {formattedValue}
        </Text>

        {/* Metric Description (optional) */}
        {showDescription && metadata.description && (
          <Text
            id={`metric-desc-${metadata.key}`}
            type="secondary"
            style={{
              fontSize: sizeConfig.descriptionFontSize,
              display: "block",
              marginTop: "4px",
            }}
          >
            {metadata.description}
          </Text>
        )}
      </Space>
    </Card>
  );
};

export default MetricCard;
