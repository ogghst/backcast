/**
 * Project-level EVM Analysis page component.
 *
 * Context: Displays aggregated EVM metrics for an entire project,
 * including summary cards, historical trends, and advanced analysis.
 * Integrates with TimeMachine for time-travel queries.
 *
 * @module pages/projects/ProjectEVMAnalysis
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
 * Project EVM Analysis page.
 *
 * Renders EVM metrics, historical trends chart, and advanced analysis modal
 * for a specific project. Uses EntityType.PROJECT for all EVM queries.
 */
export const ProjectEVMAnalysis: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = theme.useToken();

  // State for granularity selection and modal visibility
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>(
    EVMTimeSeriesGranularity.WEEK
  );
  const [isEVMModalOpen, setIsEVMModalOpen] = useState(false);

  // Fetch EVM metrics for the project
  const {
    data: evmMetrics,
    isLoading: metricsLoading,
    isError: metricsError,
  } = useEVMMetrics(EntityType.PROJECT, projectId || "", {});

  // Fetch EVM time series for the project
  const {
    data: timeSeries,
    isLoading: timeSeriesLoading,
    isError: timeSeriesError,
  } = useEVMTimeSeries(
    EntityType.PROJECT,
    projectId || "",
    granularity,
    {}
  );

  // Loading state
  const isLoading = metricsLoading || timeSeriesLoading;

  // Handle missing projectId
  if (!projectId) {
    return null;
  }

  // Loading state render
  if (isLoading && !evmMetrics) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 48 }}>
        <Spin size="large" role="status" />
      </div>
    );
  }

  // Error state
  if (metricsError || timeSeriesError) {
    return (
      <div style={{ padding: 24 }}>
        <p>Error loading EVM data. Please try again.</p>
      </div>
    );
  }

  return (
    <Space
      direction="vertical"
      size="large"
      style={{ width: "100%", padding: 24 }}
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
                  padding: 16,
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
