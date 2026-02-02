/**
 * EVMAnalyzerModal Component
 *
 * A comprehensive modal component for thorough EVM (Earned Value Management) evaluation.
 * Displays all EVM metrics with enhanced visualizations including gauges for CPI/SPI
 * and time-series charts for historical trends.
 *
 * Features:
 * - Modal dialog with open/close control
 * - Gauges for CPI and SPI performance indices
 * - EVMTimeSeriesChart for historical trends (both EVM metrics and cost comparison)
 * - Organized layout with tabs or sections
 * - Proper loading and empty states
 * - All EVM metrics displayed with enhanced visualizations
 * - Viewport-height optimized layout with minimal scrolling
 *
 * @module features/evm/components
 */

import React from "react";
import {
  Modal,
  Spin,
  Empty,
  Tabs,
  Row,
  Col,
  Typography,
  ConfigProvider,
  Card,
  Space,
  theme,
} from "antd";
import { MetricCard } from "./MetricCard";
import { EChartsGauge } from "./charts/EChartsGauge";
import { EVMTimeSeriesChart } from "./EVMTimeSeriesChart";
import type {
  EVMMetricsResponse,
  EVMTimeSeriesResponse,
  EVMTimeSeriesGranularity,
} from "../types";
import { METRIC_DEFINITIONS, getMetricStatus, MetricCategory } from "../types";

const { Title, Text } = Typography;

interface EVMAnalyzerModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback when modal is closed */
  onClose: () => void;
  /** EVM metrics data */
  evmMetrics: EVMMetricsResponse | undefined;
  /** Time-series data for charts */
  timeSeries: EVMTimeSeriesResponse | undefined;
  /** Loading state */
  loading?: boolean;
  /** Callback when granularity changes */
  onGranularityChange: (granularity: EVMTimeSeriesGranularity) => void;
}

/**
 * Organize metrics by category for tabs
 */
function organizeMetricsByCategory(evmMetrics: EVMMetricsResponse) {
  const categories: Record<
    MetricCategory,
    Array<{
      key: string;
      value: number | null;
      status: "good" | "warning" | "bad";
    }>
  > = {
    [MetricCategory.SCHEDULE]: [],
    [MetricCategory.COST]: [],
    [MetricCategory.VARIANCE]: [],
    [MetricCategory.PERFORMANCE]: [],
    [MetricCategory.FORECAST]: [],
  };

  // Get all metric keys from definitions
  const metricKeys = Object.keys(METRIC_DEFINITIONS) as Array<
    keyof typeof METRIC_DEFINITIONS
  >;

  metricKeys.forEach((key) => {
    const definition = METRIC_DEFINITIONS[key];
    const metricKey = definition.key as Exclude<
      typeof definition.key,
      "entity_type" | "entity_id" | "control_date" | "branch"
    >;
    const value = evmMetrics[definition.key] as number | null;
    const status = getMetricStatus(metricKey, value);

    categories[definition.category].push({
      key: definition.key,
      value,
      status,
    });
  });

  return categories;
}

/**
 * EVMAnalyzerModal Component
 */
export const EVMAnalyzerModal = ({
  open,
  onClose,
  evmMetrics,
  timeSeries,
  loading = false,
  onGranularityChange,
}: EVMAnalyzerModalProps) => {
  const { token } = theme.useToken();
  // State to trigger chart re-render when modal opens
  const [modalOpen, setModalOpen] = React.useState(open);
  const [chartKey, setChartKey] = React.useState(0);
  const [activeTab, setActiveTab] = React.useState("overview");

  // Handle modal open/close
  React.useEffect(() => {
    if (open && !modalOpen) {
      // Modal is opening - increment key to trigger chart re-render
      setModalOpen(true);
      setChartKey((prev) => prev + 1);
    } else if (!open && modalOpen) {
      setModalOpen(false);
    }
  }, [open, modalOpen]);

  // Sync with external open prop
  React.useEffect(() => {
    setModalOpen(open);
  }, [open]);

  /**
   * Render loading state
   */
  const renderLoading = () => (
    <div style={{ textAlign: "center", padding: "40px" }}>
      <Spin size="large" />
      <div style={{ marginTop: "16px" }}>Loading EVM analysis...</div>
    </div>
  );

  /**
   * Render empty state
   */
  const renderEmpty = () => (
    <Empty description="No EVM data available" style={{ padding: "40px" }} />
  );

  /**
   * Render metrics organized by category in a compact grid layout.
   */
  const renderMetricsCards = (category: MetricCategory) => {
    if (!evmMetrics) return null;

    const categories = organizeMetricsByCategory(evmMetrics);
    const categoryMetrics = categories[category];

    if (categoryMetrics.length === 0) return null;

    return (
      <Row gutter={[12, 12]} style={{ marginTop: 8 }}>
        {categoryMetrics.map((metric) => (
          <Col xs={12} sm={8} md={6} key={metric.key}>
            <MetricCard
              metadata={
                METRIC_DEFINITIONS[
                  metric.key as keyof typeof METRIC_DEFINITIONS
                ]
              }
              value={metric.value}
              status={metric.status}
              size="small"
              showDescription={false}
            />
          </Col>
        ))}
      </Row>
    );
  };

  /**
   * Render key financial metrics section for All Metrics tab.
   */
  const renderKeyFinancialMetrics = () => {
    if (!evmMetrics) return null;

    const keyMetrics = [
      { key: "bac", label: "BAC", value: evmMetrics.bac },
      { key: "eac", label: "EAC", value: evmMetrics.eac },
      { key: "vac", label: "VAC", value: evmMetrics.vac },
      { key: "etc", label: "ETC", value: evmMetrics.etc },
    ] as const;

    return (
      <Row gutter={[12, 12]}>
        {keyMetrics.map((metric) => {
          const definition = METRIC_DEFINITIONS[metric.key];
          return (
            <Col xs={12} sm={12} md={6} key={metric.key}>
              <Card
                variant="outlined"
                size="small"
                style={{
                  height: "100%",
                  borderColor: token.colorBorderSecondary,
                }}
                styles={{ body: { padding: "12px" } }}
              >
                <Text
                  type="secondary"
                  style={{ fontSize: 12, display: "block" }}
                >
                  {definition.name}
                </Text>
                <Text
                  strong
                  style={{
                    fontSize: 18,
                    display: "block",
                    marginTop: 4,
                    color:
                      getMetricStatus(metric.key, metric.value) === "good"
                        ? token.colorSuccess
                        : getMetricStatus(metric.key, metric.value) ===
                            "warning"
                          ? token.colorWarning
                          : token.colorError,
                  }}
                >
                  {metric.value !== null
                    ? new Intl.NumberFormat("en-IE", {
                        style: "currency",
                        currency: "EUR",
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                      }).format(metric.value)
                    : "N/A"}
                </Text>
              </Card>
            </Col>
          );
        })}
      </Row>
    );
  };

  // Don't render anything if modal is closed
  if (!open) {
    return null;
  }

  /**
   * Build tab items for the modal.
   */
  const tabItems = [
    {
      key: "overview",
      label: "Overview",
      children: (
        <div
          style={{
            height: "calc(85vh - 200px)",
            display: "flex",
            flexDirection: "row",
            overflow: "hidden",
          }}
        >
          {/* Left: Charts (80% width) */}
          <div
            style={{
              flex: "0 0 80%",
              paddingRight: 16,
              height: "100%",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            <Card
              title={
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 500,
                    color: "rgba(0,0,0,0.88)",
                  }}
                >
                  Historical Trends
                </div>
              }
              size="small"
              variant="outlined"
              styles={{
                body: { padding: "16px", height: "100%", overflow: "hidden" },
              }}
              style={{
                height: "100%",
                backgroundColor: token.colorBgContainer,
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  overflow: "hidden",
                }}
              >
                <EVMTimeSeriesChart
                  key={`timeseries-${chartKey}`}
                  timeSeries={timeSeries}
                  loading={false}
                  onGranularityChange={onGranularityChange}
                  delayRender={true}
                  headless={true}
                  height="100%"
                  fillContainer={true}
                />
              </div>
            </Card>
          </div>

          {/* Right: Performance Indices Card (20% width) */}
          <div
            style={{
              flex: "0 0 20%",
              height: "100%",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Card
              title={
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 500,
                    color: "rgba(0,0,0,0.88)",
                  }}
                >
                  Performance Indices
                </div>
              }
              size="small"
              variant="outlined"
              styles={{
                body: {
                  padding: "16px",
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  gap: 16,
                },
              }}
              style={{
                height: "100%",
                backgroundColor: token.colorBgContainer,
                display: "flex",
                flexDirection: "column",
              }}
            >
              {/* CPI Gauge */}
              <div
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "flex-start",
                  alignItems: "top",
                  minHeight: 0,
                }}
              >
                <EChartsGauge
                  key={`cpi-${chartKey}`}
                  value={evmMetrics?.cpi ?? null}
                  min={0}
                  max={2}
                  label="CPI"
                  goodThreshold={1.0}
                  warningThresholdPercent={0.9}
                  variant="semi-circle"
                  size={280}
                  delayRender={true}
                  style={{ width: "100%" }}
                />
              </div>

              {/* SPI Gauge */}
              <div
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "flex-start",
                  alignItems: "top",
                  minHeight: 0,
                }}
              >
                <EChartsGauge
                  key={`spi-${chartKey}`}
                  value={evmMetrics?.spi ?? null}
                  min={0}
                  max={2}
                  label="SPI"
                  goodThreshold={1.0}
                  warningThresholdPercent={0.9}
                  variant="semi-circle"
                  size={280}
                  delayRender={true}
                  style={{ width: "100%" }}
                />
              </div>
            </Card>
          </div>
        </div>
      ),
    },
    {
      key: "all-metrics",
      label: "All Metrics",
      children: (
        <div style={{ height: "calc(85vh - 200px)", overflowY: "auto" }}>
          <Space orientation="vertical" size="large" style={{ width: "100%" }}>
            {/* Key Financial Metrics */}
            <Card
              title={<Text strong>Key Financial Metrics</Text>}
              size="small"
              variant="outlined"
              style={{ backgroundColor: token.colorBgContainer }}
            >
              {renderKeyFinancialMetrics()}
            </Card>

            {/* Schedule Metrics */}
            <Card
              title={<Text strong>Schedule Performance Metrics</Text>}
              size="small"
              variant="outlined"
              style={{ backgroundColor: token.colorBgContainer }}
            >
              {renderMetricsCards(MetricCategory.SCHEDULE)}
            </Card>

            {/* Cost Metrics */}
            <Card
              title={<Text strong>Cost Performance Metrics</Text>}
              size="small"
              variant="outlined"
              style={{ backgroundColor: token.colorBgContainer }}
            >
              {renderMetricsCards(MetricCategory.COST)}
            </Card>

            {/* Variance Metrics */}
            <Card
              title={<Text strong>Variance Analysis</Text>}
              size="small"
              variant="outlined"
              style={{ backgroundColor: token.colorBgContainer }}
            >
              {renderMetricsCards(MetricCategory.VARIANCE)}
            </Card>

            {/* Forecast Metrics */}
            <Card
              title={<Text strong>Forecast Metrics</Text>}
              size="small"
              variant="outlined"
              style={{ backgroundColor: token.colorBgContainer }}
            >
              {renderMetricsCards(MetricCategory.FORECAST)}
            </Card>
          </Space>
        </div>
      ),
    },
  ];

  return (
    <ConfigProvider
      theme={{
        token: {
          borderRadiusLG: 8,
        },
      }}
    >
      <Modal
        title={
          <Title level={4} style={{ margin: 0 }}>
            EVM Analysis Dashboard
          </Title>
        }
        open={open}
        onCancel={onClose}
        onOk={onClose}
        okText="Close"
        cancelText={null}
        width={1200}
        style={{ top: 20 }}
        styles={{
          body: {
            padding: 16,
            maxHeight: "85vh",
            overflow: "hidden",
          },
        }}
        destroyOnHidden
        forceRender
        afterOpenChange={(visible) => {
          // Trigger chart resize after modal animation completes
          if (visible) {
            setTimeout(() => {
              // Force a resize of all ECharts instances
              window.dispatchEvent(new Event("resize"));
            }, 300);
          }
        }}
      >
        {loading ? (
          renderLoading()
        ) : !evmMetrics ? (
          renderEmpty()
        ) : (
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
            style={{ height: "100%" }}
            tabBarStyle={{ marginBottom: 12 }}
          />
        )}
      </Modal>
    </ConfigProvider>
  );
};

export default EVMAnalyzerModal;
