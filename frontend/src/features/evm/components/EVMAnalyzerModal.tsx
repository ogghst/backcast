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
  Collapse,
} from "antd";
import { MetricCard } from "./MetricCard";
import { EVMGauge } from "./EVMGauge";
import { EVMTimeSeriesChart } from "./EVMTimeSeriesChart";
import type {
  EVMMetricsResponse,
  EVMTimeSeriesResponse,
  EVMTimeSeriesGranularity,
} from "../types";
import { METRIC_DEFINITIONS, getMetricStatus, MetricCategory } from "../types";

const { Title } = Typography;
const { Panel } = Collapse;

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
  // State to trigger chart re-render when modal opens
  const [modalOpen, setModalOpen] = React.useState(open);
  const [chartKey, setChartKey] = React.useState(0);

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
   * Render performance indices section content
   */
  const renderPerformanceIndicesContent = () => {
    if (!evmMetrics) return null;

    return (
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12}>
          <EVMGauge
            key={`cpi-${chartKey}`}
            value={evmMetrics.cpi}
            min={0}
            max={2}
            label="CPI"
            goodThreshold={1.0}
            warningThresholdPercent={0.9}
            size={180}
            delayRender={true}
          />
        </Col>
        <Col xs={24} sm={12}>
          <EVMGauge
            key={`spi-${chartKey}`}
            value={evmMetrics.spi}
            min={0}
            max={2}
            label="SPI"
            goodThreshold={1.0}
            warningThresholdPercent={0.9}
            size={180}
            delayRender={true}
          />
        </Col>
      </Row>
    );
  };

  /**
   * Render metrics organized by category
   */
  const renderMetricsTabs = () => {
    if (!evmMetrics) return null;

    const categories = organizeMetricsByCategory(evmMetrics);

    const tabItems = [
      {
        key: "overview",
        label: "Overview",
        children: (
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8}>
              <MetricCard
                metadata={METRIC_DEFINITIONS.bac}
                value={evmMetrics.bac}
                status="good"
                size="medium"
                showDescription
              />
            </Col>
            <Col xs={24} sm={12} md={8}>
              <MetricCard
                metadata={METRIC_DEFINITIONS.eac}
                value={evmMetrics.eac}
                status={getMetricStatus("eac", evmMetrics.eac)}
                size="medium"
                showDescription
              />
            </Col>
            <Col xs={24} sm={12} md={8}>
              <MetricCard
                metadata={METRIC_DEFINITIONS.vac}
                value={evmMetrics.vac}
                status={getMetricStatus("vac", evmMetrics.vac)}
                size="medium"
                showDescription
              />
            </Col>
            <Col xs={24} sm={12} md={8}>
              <MetricCard
                metadata={METRIC_DEFINITIONS.etc}
                value={evmMetrics.etc}
                status={getMetricStatus("etc", evmMetrics.etc)}
                size="medium"
                showDescription
              />
            </Col>
          </Row>
        ),
      },
      {
        key: "schedule",
        label: "Schedule",
        children: (
          <Row gutter={[16, 16]}>
            {categories[MetricCategory.SCHEDULE].map((metric) => (
              <Col xs={24} sm={12} md={8} key={metric.key}>
                <MetricCard
                  metadata={
                    METRIC_DEFINITIONS[
                      metric.key as keyof typeof METRIC_DEFINITIONS
                    ]
                  }
                  value={metric.value}
                  status={metric.status}
                  size="medium"
                  showDescription
                />
              </Col>
            ))}
          </Row>
        ),
      },
      {
        key: "cost",
        label: "Cost",
        children: (
          <Row gutter={[16, 16]}>
            {categories[MetricCategory.COST].map((metric) => (
              <Col xs={24} sm={12} md={8} key={metric.key}>
                <MetricCard
                  metadata={
                    METRIC_DEFINITIONS[
                      metric.key as keyof typeof METRIC_DEFINITIONS
                    ]
                  }
                  value={metric.value}
                  status={metric.status}
                  size="medium"
                  showDescription
                />
              </Col>
            ))}
          </Row>
        ),
      },
      {
        key: "variance",
        label: "Variance",
        children: (
          <Row gutter={[16, 16]}>
            {categories[MetricCategory.VARIANCE].map((metric) => (
              <Col xs={24} sm={12} md={8} key={metric.key}>
                <MetricCard
                  metadata={
                    METRIC_DEFINITIONS[
                      metric.key as keyof typeof METRIC_DEFINITIONS
                    ]
                  }
                  value={metric.value}
                  status={metric.status}
                  size="medium"
                  showDescription
                />
              </Col>
            ))}
          </Row>
        ),
      },
      {
        key: "forecast",
        label: "Forecast",
        children: (
          <Row gutter={[16, 16]}>
            {categories[MetricCategory.FORECAST].map((metric) => (
              <Col xs={24} sm={12} md={8} key={metric.key}>
                <MetricCard
                  metadata={
                    METRIC_DEFINITIONS[
                      metric.key as keyof typeof METRIC_DEFINITIONS
                    ]
                  }
                  value={metric.value}
                  status={metric.status}
                  size="medium"
                  showDescription
                />
              </Col>
            ))}
          </Row>
        ),
      },
    ];

    return (
      <Tabs
        defaultActiveKey="overview"
        items={tabItems}
        style={{ marginTop: 0 }}
      />
    );
  };

  // Don't render anything if modal is closed
  if (!open) {
    return null;
  }

  return (
    <ConfigProvider>
      <Modal
        title={
          <Title level={4} style={{ margin: 0 }}>
            EVM Analysis
          </Title>
        }
        open={open}
        onCancel={onClose}
        onOk={onClose}
        okText="OK"
        cancelText="Cancel"
        width={1200}
        destroyOnClose
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
          <Collapse defaultActiveKey={["1"]}>
            <Panel header="EVM Time Series Analysis" key="1">
              <EVMTimeSeriesChart
                key={`timeseries-${chartKey}`}
                timeSeries={timeSeries}
                loading={false}
                onGranularityChange={onGranularityChange}
                delayRender={true}
                headless={true}
                height="50vh"
              />
            </Panel>
            <Panel header="Performance Indices" key="2">
              {renderPerformanceIndicesContent()}
            </Panel>
            <Panel header="Metrics" key="3">
              {renderMetricsTabs()}
            </Panel>
          </Collapse>
        )}
      </Modal>
    </ConfigProvider>
  );
};

export default EVMAnalyzerModal;
