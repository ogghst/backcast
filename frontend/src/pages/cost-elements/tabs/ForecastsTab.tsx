import { useState } from "react";
import { Button, Card, Space, Modal, Tag, theme, Typography, Grid } from "antd";
import { PlusOutlined, EditOutlined, HistoryOutlined, InfoCircleOutlined, CaretUpOutlined, CaretDownOutlined, MinusOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import type { CostElementRead } from "@/api/generated";
import {
  useCostElementForecast,
  useUpdateCostElementForecast,
} from "@/features/cost-elements/api/useCostElements";
import { ForecastModal, ForecastHistoryView } from "@/features/forecasts/components";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { queryKeys } from "@/api/queryKeys";
import { formatRangeDate } from "@/utils/temporal";

const { Text, Title } = Typography;

interface ForecastsTabProps {
  costElement: CostElementRead;
}

interface ForecastData {
  forecast_id: string;
  eac_amount: string | number;
  basis_of_estimate: string;
  branch: string;
  created_at: string;
  updated_at: string;
}

export const ForecastsTab = ({ costElement }: ForecastsTabProps) => {
  const { token } = theme.useToken();
  const { branch: tmBranch, asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();
  const currentBranch = tmBranch || costElement.branch || "main";
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showHistoryView, setShowHistoryView] = useState(false);

  const { data: forecastData, isLoading, isError } = useCostElementForecast(
    costElement.cost_element_id,
    currentBranch
  );
  const forecast = forecastData as ForecastData | null;

  const updateMutation = useUpdateCostElementForecast({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forecasts.byCostElement(costElement.cost_element_id, currentBranch, { asOf })
      });
      setIsModalOpen(false);
    },
  });

  const handleSave = (values: Record<string, unknown>) => {
    updateMutation.mutate({
      costElementId: costElement.cost_element_id,
      data: values,
      branch: currentBranch,
    });
  };

  const bac = Number(costElement.budget_amount);
  const eac = forecast ? Number(forecast.eac_amount) : null;
  const vac = eac !== null ? bac - eac : null;
  const vacPercentage = vac !== null && bac > 0 ? (vac / bac) * 100 : null;

  const getVacStatus = () => {
    if (vac === null) return { color: "default", icon: <MinusOutlined />, text: "No Forecast" };
    if (vac > 0) return { color: "#52c41a", icon: <CaretDownOutlined />, text: "Under Budget" };
    if (vac < 0) return { color: "#ff4d4f", icon: <CaretUpOutlined />, text: "Over Budget" };
    return { color: token.colorTextSecondary, icon: <MinusOutlined />, text: "On Budget" };
  };

  const vacStatus = getVacStatus();

  if (isLoading) {
    return (
      <Card>
        <div style={{ textAlign: "center", padding: "40px 0", color: token.colorTextSecondary }}>
          Loading forecast...
        </div>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <div style={{ textAlign: "center", padding: "40px 0", color: "#ff4d4f" }}>
          Error loading forecast. Please try again.
        </div>
      </Card>
    );
  }

  if (!forecast) {
    return (
      <Card>
        <div style={{ textAlign: "center", padding: "40px 20px" }}>
          <InfoCircleOutlined style={{ fontSize: "48px", color: token.colorTextSecondary, marginBottom: "16px" }} />
          <Title level={4} style={{ marginBottom: "8px" }}>No Forecast Set</Title>
          <Text type="secondary" style={{ display: "block", marginBottom: "24px" }}>
            Create a forecast to track projected costs and variance against budget
          </Text>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsModalOpen(true)} size="large">
            Create Forecast
          </Button>
          <div style={{ marginTop: "24px", padding: "12px", background: token.colorFillSecondary, borderRadius: "8px" }}>
            <Text type="secondary" style={{ fontSize: "12px" }}>
              <strong>Budget (BAC):</strong> €{bac.toLocaleString()}
            </Text>
          </div>
        </div>
        <ForecastModal
          open={isModalOpen}
          onCancel={() => setIsModalOpen(false)}
          onOk={handleSave}
          confirmLoading={updateMutation.isPending}
          currentBranch={currentBranch}
          costElementId={costElement.cost_element_id}
          costElementName={`${costElement.code} - ${costElement.name}`}
          budgetAmount={bac}
        />
      </Card>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* EVM Summary Card */}
      <Card bodyStyle={{ padding: isMobile ? "16px" : "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
          <div>
            <Text type="secondary" style={{ fontSize: "12px" }}>
              ESTIMATE AT COMPLETE
            </Text>
            <Title level={2} style={{ margin: "4px 0", fontSize: isMobile ? "28px" : "36px", fontWeight: 600 }}>
              €{eac.toLocaleString()}
            </Title>
          </div>
          <Tag
            icon={vacStatus.icon}
            color={vac > 0 ? "success" : vac < 0 ? "error" : "default"}
            style={{
              fontSize: "13px",
              padding: "4px 12px",
              borderRadius: "16px",
              height: "auto",
              lineHeight: "20px",
            }}
          >
            {vacStatus.text}
          </Tag>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "repeat(3, 1fr)", gap: "16px", marginBottom: "16px" }}>
          <div style={{ padding: "12px", background: token.colorFillSecondary, borderRadius: "8px" }}>
            <Text type="secondary" style={{ fontSize: "11px", display: "block", marginBottom: "4px" }}>
              BUDGET (BAC)
            </Text>
            <Text style={{ fontSize: isMobile ? "16px" : "18px", fontWeight: 600 }}>
              €{bac.toLocaleString()}
            </Text>
          </div>
          <div style={{ padding: "12px", background: token.colorFillSecondary, borderRadius: "8px" }}>
            <Text type="secondary" style={{ fontSize: "11px", display: "block", marginBottom: "4px" }}>
              VARIANCE (VAC)
            </Text>
            <Text style={{ fontSize: isMobile ? "16px" : "18px", fontWeight: 600, color: vacStatus.color }}>
              {vac >= 0 ? "+" : ""}€{vac.toLocaleString()}
            </Text>
          </div>
          <div style={{ padding: "12px", background: token.colorFillSecondary, borderRadius: "8px" }}>
            <Text type="secondary" style={{ fontSize: "11px", display: "block", marginBottom: "4px" }}>
              VARIANCE %
            </Text>
            <Text style={{ fontSize: isMobile ? "16px" : "18px", fontWeight: 600, color: vacStatus.color }}>
              {vacPercentage >= 0 ? "+" : ""}{vacPercentage?.toFixed(1)}%
            </Text>
          </div>
        </div>

        <Space size="middle" wrap>
          <Button type="primary" icon={<EditOutlined />} onClick={() => setIsModalOpen(true)}>
            Edit Forecast
          </Button>
          <Button icon={<HistoryOutlined />} onClick={() => setShowHistoryView(true)}>
            History
          </Button>
        </Space>
      </Card>

      {/* Basis of Estimate Card */}
      <Card
        title={<Text style={{ fontSize: "14px", fontWeight: 500 }}>Basis of Estimate</Text>}
        size="small"
        bodyStyle={{ padding: "16px" }}
      >
        <Text style={{ fontSize: "14px", lineHeight: "1.6" }}>{forecast.basis_of_estimate}</Text>
        {forecast.transaction_time && (
          <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: `1px solid ${token.colorBorderSecondary}` }}>
            <Text type="secondary" style={{ fontSize: "12px" }}>
              Last updated: {formatRangeDate(forecast.transaction_time)}
            </Text>
          </div>
        )}
      </Card>

      <ForecastModal
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        onOk={handleSave}
        confirmLoading={updateMutation.isPending}
        initialValues={forecast}
        currentBranch={currentBranch}
        costElementId={costElement.cost_element_id}
        costElementName={`${costElement.code} - ${costElement.name}`}
        budgetAmount={bac}
      />

      <Modal
        title="Forecast History & Time Travel"
        open={showHistoryView}
        onCancel={() => setShowHistoryView(false)}
        footer={null}
        width={1000}
      >
        <ForecastHistoryView
          costElementId={costElement.cost_element_id}
          currentBranch={currentBranch}
        />
      </Modal>
    </div>
  );
};
