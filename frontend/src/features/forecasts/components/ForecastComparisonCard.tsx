import { Card, Space, Tooltip, theme, Empty } from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";
import { useState } from "react";
import { useCostElementEvmMetrics } from "@/features/cost-elements/api/useCostElements";
import { EVMSummaryView } from "@/features/evm/components/EVMSummaryView";
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import type { EVMMetricsResponse } from "@/features/evm/types";

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

  // Fetch EVM metrics from the new endpoint
  const { data: evmMetrics, isLoading: evmLoading } =
    useCostElementEvmMetrics(costElementId);

  const metrics = evmMetrics as EVMMetricsResponse | undefined;

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
      <Card
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
      </Card>
    );
  }

  if (!metrics) {
    return (
      <Card
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
      </Card>
    );
  }

  return (
    <>
      <Card
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
      </Card>

      <EVMAnalyzerModal
        open={isModalOpen}
        onClose={handleCloseModal}
        evmMetrics={metrics}
        timeSeries={undefined}
        loading={false}
        onGranularityChange={() => {}}
      />
    </>
  );
};
