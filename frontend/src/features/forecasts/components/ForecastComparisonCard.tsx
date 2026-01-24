import { Space, Tooltip, theme, Empty } from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";
import { useState } from "react";
import { useCostElementEvmMetrics } from "@/features/cost-elements/api/useCostElements";
import { EVMSummaryView } from "@/features/evm/components/EVMSummaryView";
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import type { EVMMetricsResponse } from "@/features/evm/types";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { useEVMTimeSeries } from "@/features/evm/api/useEVMMetrics";
import { EntityType, EVMTimeSeriesGranularity } from "@/features/evm/types";

interface ForecastComparisonCardProps {
  costElementId: string;
  budgetAmount: number; // BAC
}

export const ForecastComparisonCard = ({
  costElementId,
  budgetAmount: _budgetAmount, // eslint-disable-line @typescript-eslint/no-unused-vars
}: ForecastComparisonCardProps) => {
  const { token } = theme.useToken();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>(
    EVMTimeSeriesGranularity.WEEK,
  );

  // Fetch EVM metrics from the new endpoint
  const { data: evmMetrics, isLoading: evmLoading } =
    useCostElementEvmMetrics(costElementId);

  const metrics = evmMetrics as EVMMetricsResponse | undefined;

  // Fetch time-series data for the modal
  const { data: timeSeries, isLoading: timeSeriesLoading } = useEVMTimeSeries(
    EntityType.COST_ELEMENT,
    costElementId,
    granularity,
    {
      enabled: isModalOpen, // Only fetch when modal is open
    },
  );

  // Handle opening the modal
  const handleAdvancedClick = () => {
    setIsModalOpen(true);
  };

  // Handle closing the modal
  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  if (evmLoading) {
    return (
      <CollapsibleCard
        id="evm-analysis-loading"
        title={
          <Space>
            <span>EVM Analysis</span>
            <Tooltip title="Earned Value Management metrics based on current forecast">
              <InfoCircleOutlined style={{ color: token.colorTextTertiary }} />
            </Tooltip>
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        <Empty
          description="Loading EVM metrics..."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </CollapsibleCard>
    );
  }

  if (!metrics) {
    return (
      <CollapsibleCard
        id="evm-analysis-empty"
        title={
          <Space>
            <span>EVM Analysis</span>
            <Tooltip title="Earned Value Management metrics based on current forecast">
              <InfoCircleOutlined style={{ color: token.colorTextTertiary }} />
            </Tooltip>
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        <Empty
          description="No forecast created yet. Create a forecast to see EVM analysis."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </CollapsibleCard>
    );
  }

  return (
    <>
      <CollapsibleCard
        id="evm-analysis-card"
        title={
          <Space>
            <span>EVM Analysis</span>
            <Tooltip title="Earned Value Management metrics based on current forecast">
              <InfoCircleOutlined style={{ color: token.colorTextTertiary }} />
            </Tooltip>
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        <EVMSummaryView metrics={metrics} onAdvanced={handleAdvancedClick} />
      </CollapsibleCard>

      <EVMAnalyzerModal
        open={isModalOpen}
        onClose={handleCloseModal}
        evmMetrics={metrics}
        timeSeries={timeSeries}
        loading={timeSeriesLoading}
        onGranularityChange={setGranularity}
      />
    </>
  );
};
