/**
 * WBE-level EVM Analysis page component.
 *
 * Context: Displays aggregated EVM metrics for a specific WBE,
 * including summary cards, historical trends, and advanced analysis.
 * Integrates with TimeMachine for time-travel queries.
 *
 * @module pages/wbes/WBEEVMAnalysis
 */

import { useParams } from "react-router-dom";
import { useState } from "react";
import { Space, Collapse, Spin, theme } from "antd";
import { LineChartOutlined } from "@ant-design/icons";

import {
  useEVMMetrics,
  useEVMTimeSeries,
} from "@/features/evm/api/useEVMMetrics";
import { EVMSummaryView } from "@/features/evm/components/EVMSummaryView";
import { EVMTimeSeriesChart } from "@/features/evm/components/EVMTimeSeriesChart";
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import { EVMTimeSeriesGranularity, EntityType } from "@/features/evm/types";

/**
 * WBE EVM Analysis page.
 *
 * Renders EVM metrics, historical trends chart, and advanced analysis modal
 * for a specific WBE. Uses EntityType.WBE for all EVM queries.
 */
export const WBEEVMAnalysis: React.FC = () => {
  const { wbeId } = useParams<{ projectId: string; wbeId: string }>();
  const { token } = theme.useToken();

  // State for granularity selection and modal visibility
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>(
    EVMTimeSeriesGranularity.WEEK
  );
  const [isEVMModalOpen, setIsEVMModalOpen] = useState(false);

  // Fetch EVM metrics for the WBE
  const {
    data: evmMetrics,
    isLoading: metricsLoading,
    isError: metricsError,
  } = useEVMMetrics(EntityType.WBE, wbeId || "", {});

  // Fetch EVM time series for the WBE
  const {
    data: timeSeries,
    isLoading: timeSeriesLoading,
    isError: timeSeriesError,
  } = useEVMTimeSeries(EntityType.WBE, wbeId || "", granularity);

  // Loading state
  const isLoading = metricsLoading || timeSeriesLoading;

  // Handle missing wbeId
  if (!wbeId) {
    return null;
  }

  // Loading state render
  if (isLoading && !evmMetrics) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          padding: token.paddingXL * 1.5,
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  // Error state
  if (metricsError || timeSeriesError) {
    return (
      <div style={{ padding: token.paddingXL }}>
        <p>Error loading EVM data. Please try again.</p>
      </div>
    );
  }

  return (
    <Space
      direction="vertical"
      size="large"
      style={{ width: "100%", padding: token.paddingXL }}
    >
      {/* Page Title */}
      <h1 style={{ margin: 0 }}>EVM Analysis</h1>

      {/* EVM Summary View */}
      {evmMetrics && (
        <EVMSummaryView
          metrics={evmMetrics}
          onAdvanced={() => setIsEVMModalOpen(true)}
        />
      )}

      {/* Historical Trends Chart */}
      <Collapse
        defaultActiveKey={["historical-trends"]}
        bordered
        style={{ backgroundColor: "transparent" }}
        items={[
          {
            key: "historical-trends",
            label: (
              <Space>
                <LineChartOutlined />
                <span>Historical Trends</span>
              </Space>
            ),
            children: (
              <div
                style={{
                  backgroundColor: token.colorBgContainer,
                  padding: token.paddingMD,
                  borderRadius: token.borderRadiusLG,
                }}
              >
                <EVMTimeSeriesChart
                  timeSeries={timeSeries}
                  loading={timeSeriesLoading}
                  onGranularityChange={setGranularity}
                  currentGranularity={granularity}
                  headless={true}
                  height={400}
                />
              </div>
            ),
          },
        ]}
      />

      {/* EVM Analyzer Modal */}
      <EVMAnalyzerModal
        open={isEVMModalOpen}
        onClose={() => setIsEVMModalOpen(false)}
        evmMetrics={evmMetrics}
        timeSeries={timeSeries}
        loading={timeSeriesLoading}
        onGranularityChange={setGranularity}
      />
    </Space>
  );
};
