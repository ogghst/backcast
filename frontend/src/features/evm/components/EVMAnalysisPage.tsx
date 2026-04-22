import React, { useState } from "react";
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

interface EVMAnalysisPageProps {
  entityType: EntityType;
  entityId: string;
}

export const EVMAnalysisPage: React.FC<EVMAnalysisPageProps> = ({
  entityType,
  entityId,
}) => {
  const { token } = theme.useToken();

  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>(
    EVMTimeSeriesGranularity.WEEK,
  );
  const [isEVMModalOpen, setIsEVMModalOpen] = useState(false);

  const {
    data: evmMetrics,
    isLoading: metricsLoading,
    isError: metricsError,
  } = useEVMMetrics(entityType, entityId, {});

  const {
    data: timeSeries,
    isLoading: timeSeriesLoading,
    isError: timeSeriesError,
  } = useEVMTimeSeries(entityType, entityId, granularity);

  const isLoading = metricsLoading || timeSeriesLoading;

  if (!entityId) return null;

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
      <h1 style={{ margin: 0 }}>EVM Analysis</h1>

      {evmMetrics && (
        <EVMSummaryView
          metrics={evmMetrics}
          onAdvanced={() => setIsEVMModalOpen(true)}
        />
      )}

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
