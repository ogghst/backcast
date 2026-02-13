import React, { useMemo, useCallback } from "react";
import { Collapse, Button, Space, Typography, Row, Col, type CollapseProps } from "antd";
import {
  LineChartOutlined,
  DollarOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { MetricCard } from "./MetricCard";
import { EVMMetricsResponse, MetricCategory, getMetricStatus, getMetricsByCategory, type MetricMetadata } from "../types";

const { Title } = Typography;

/**
 * Props for the EVMSummaryView component.
 */
export interface EVMSummaryViewProps {
  /** EVM metrics to display */
  metrics: EVMMetricsResponse;
  /** Callback when Advanced button is clicked */
  onAdvanced?: () => void;
}

/**
 * Category configuration for organizing metrics.
 */
interface CategoryConfig {
  key: string;
  title: string;
  icon: React.ReactNode;
}

/**
 * Default active keys for Collapse (all categories expanded).
 */
const DEFAULT_ACTIVE_KEYS = ["Schedule", "Cost", "Performance", "Forecast"] as const;

/**
 * Category configurations with icons and titles.
 */
const CATEGORY_CONFIGS: readonly CategoryConfig[] = [
  {
    key: "Schedule",
    title: "Schedule Metrics",
    icon: <ClockCircleOutlined />,
  },
  {
    key: "Cost",
    title: "Cost Metrics",
    icon: <DollarOutlined />,
  },
  {
    key: "Performance",
    title: "Performance Metrics",
    icon: <ThunderboltOutlined />,
  },
  {
    key: "Forecast",
    title: "Forecast Metrics",
    icon: <LineChartOutlined />,
  },
] as const;

/**
 * Render metric cards for a specific category.
 */
function renderMetricCards(
  categoryMetrics: readonly MetricMetadata[],
  metrics: EVMMetricsResponse
): React.ReactNode {
  return (
    <Row gutter={[16, 16]}>
      {categoryMetrics.map((metadata) => {
        const value = metrics[metadata.key] as number | null;
        const status = getMetricStatus(metadata.key, value);

        return (
          <Col xs={24} sm={12} lg={8} key={metadata.key}>
            <MetricCard
              metadata={metadata}
              value={value}
              status={status}
              size="medium"
              showDescription
            />
          </Col>
        );
      })}
    </Row>
  );
}

/**
 * EVMSummaryView Component
 *
 * A comprehensive summary view for displaying EVM (Earned Value Management) metrics.
 * Organizes metrics by category (Schedule, Cost, Performance, Forecast) in collapsible sections.
 *
 * Features:
 * - Collapsible sections for each metric category
 * - MetricCard components for individual metrics with status indicators
 * - Short descriptions next to each metric
 * - Advanced button to open EVM Analyzer modal
 * - Responsive grid layout for metric cards
 * - Proper TypeScript typing
 * - Memoized collapse items for performance
 *
 * @example
 * ```tsx
 * <EVMSummaryView
 *   metrics={evmMetrics}
 *   onAdvanced={() => setIsModalOpen(true)}
 * />
 * ```
 */
export const EVMSummaryView: React.FC<EVMSummaryViewProps> = ({
  metrics,
  onAdvanced,
}) => {
  /**
   * Handle Advanced button click.
   * Memoized to prevent unnecessary recreations.
   */
  const handleAdvancedClick = useCallback(() => {
    onAdvanced?.();
  }, [onAdvanced]);

  /**
   * Generate collapse items for each metric category.
   * Memoized to prevent unnecessary recalculations when metrics change.
   */
  const collapseItems: CollapseProps['items'] = useMemo(
    () => CATEGORY_CONFIGS.map((categoryConfig) => {
      const categoryMetrics = getMetricsByCategory(categoryConfig.key as MetricCategory);

      return {
        key: categoryConfig.key,
        label: (
          <Space>
            {categoryConfig.icon}
            <span>{categoryConfig.title}</span>
          </Space>
        ),
        children: renderMetricCards(categoryMetrics, metrics),
      };
    }),
    [metrics]
  );

  return (
    <Space
      orientation="vertical"
      size="large"
      style={{ width: "100%" }}
    >
      {/* Header with Advanced button */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Title level={3} style={{ margin: 0 }}>
          EVM Summary
        </Title>
        <Button
          type="primary"
          icon={<LineChartOutlined />}
          onClick={handleAdvancedClick}
        >
          Advanced
        </Button>
      </div>

      {/* Collapsible metric categories */}
      <Collapse
        defaultActiveKey={[...DEFAULT_ACTIVE_KEYS]}
        items={collapseItems}
        bordered
        style={{ backgroundColor: "transparent" }}
      />
    </Space>
  );
};

export default EVMSummaryView;
