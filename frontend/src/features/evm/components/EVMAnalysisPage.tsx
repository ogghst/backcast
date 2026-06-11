import React, { useState } from "react";
import { Space, Card, Spin } from "antd";
import { LineChartOutlined } from "@ant-design/icons";
import {
  useEVMMetrics,
  useEVMTimeSeries,
} from "@/features/evm/api/useEVMMetrics";
import { EVMSummaryView } from "@/features/evm/components/EVMSummaryView";
import { EVMTimeSeriesChart } from "@/features/evm/components/EVMTimeSeriesChart";
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import { EVMTimeSeriesGranularity, EntityType } from "@/features/evm/types";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { PageContent } from "@/components/layout/PageContent";

interface EVMAnalysisPageProps {
  entityType: EntityType;
  entityId: string;
}

export const EVMAnalysisPage: React.FC<EVMAnalysisPageProps> = ({
  entityType,
  entityId,
}) => {
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
      <PageWrapper>
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            padding: 48,
          }}
        >
          <Spin size="large" />
        </div>
      </PageWrapper>
    );
  }

  if (metricsError || timeSeriesError) {
    return (
      <PageWrapper>
        <p>Error loading EVM data. Please try again.</p>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper>
      <PageContent>
        {evmMetrics && (
          <EVMSummaryView
            metrics={evmMetrics}
            timeSeries={timeSeries}
            onAdvanced={() => setIsEVMModalOpen(true)}
          />
        )}

        <Card
          title={
            <Space>
              <LineChartOutlined />
              <span>Historical Trends</span>
            </Space>
          }
        >
          <EVMTimeSeriesChart
            timeSeries={timeSeries}
            loading={timeSeriesLoading}
            onGranularityChange={setGranularity}
            currentGranularity={granularity}
            headless={true}
            height={400}
          />
        </Card>

        <EVMAnalyzerModal
          open={isEVMModalOpen}
          onClose={() => setIsEVMModalOpen(false)}
          evmMetrics={evmMetrics}
          timeSeries={timeSeries}
          loading={timeSeriesLoading}
          onGranularityChange={setGranularity}
        />
      </PageContent>
    </PageWrapper>
  );
};
