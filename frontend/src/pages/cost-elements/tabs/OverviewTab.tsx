import { useState } from "react";
import { Descriptions, Card, Progress, Statistic, Row, Col, Alert, Button, Empty } from "antd";
import { EditOutlined } from "@ant-design/icons";
import type { CostElementRead } from "@/api/generated";
import { useBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";
import { useUpdateCostElement } from "@/features/cost-elements/api/useCostElements";
import { CostElementModal } from "@/features/cost-elements/components/CostElementModal";
import { useForecasts } from "@/features/forecasts/api";
import { ForecastComparisonCard } from "@/features/forecasts/components";
import { useQueryClient } from "@tanstack/react-query";

interface OverviewTabProps {
  costElement: CostElementRead;
}

export const OverviewTab = ({ costElement }: OverviewTabProps) => {
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: budgetStatus, isLoading } = useBudgetStatus(
    costElement.cost_element_id
  );

  // Fetch forecasts for this cost element (for EVM comparison)
  const { data: forecastsData } = useForecasts({
    cost_element_id: costElement.cost_element_id,
    branch: costElement.branch || "main",
    pagination: { current: 1, pageSize: 1 }, // Only need the latest forecast
  });

  // Get the latest forecast (if any)
  const latestForecast = forecastsData?.items?.[0];
  const actualCost = budgetStatus?.used ? Number(budgetStatus.used) : 0;

  const updateMutation = useUpdateCostElement({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["cost_element", costElement.cost_element_id]
      });
      queryClient.invalidateQueries({
        queryKey: ["cost_element_breadcrumb", costElement.cost_element_id]
      });
      queryClient.invalidateQueries({
        queryKey: ["budget_status", costElement.cost_element_id]
      });
      queryClient.invalidateQueries({
        queryKey: ["forecasts"]
      });
      setIsEditModalOpen(false);
    },
  });

  const budget = budgetStatus?.budget
    ? Number(budgetStatus.budget)
    : Number(costElement.budget_amount);
  const used = budgetStatus?.used ? Number(budgetStatus.used) : 0;
  const remaining = budgetStatus?.remaining
    ? Number(budgetStatus.remaining)
    : budget - used;
  const percentage = budgetStatus?.percentage
    ? Number(budgetStatus.percentage)
    : budget > 0
      ? (used / budget) * 100
      : 0;

  // Determine status color
  let statusColor = "#52c41a"; // green
  let statusText = "Healthy";

  if (percentage >= 100) {
    statusColor = "#ff4d4f"; // red
    statusText = "Exceeded";
  } else if (percentage >= 90) {
    statusColor = "#faad14"; // orange
    statusText = "Warning";
  } else if (percentage >= 75) {
    statusColor = "#1890ff"; // blue
    statusText = "Monitoring";
  }

  const handleUpdate = (values: any) => {
    updateMutation.mutate({
      id: costElement.cost_element_id,
      data: {
        ...values,
        branch: costElement.branch || "main",
      },
    });
  };

  return (
    <div>
      {/* Budget Section */}
      <Card title="Budget Status" style={{ marginBottom: 16 }}>
        {isLoading ? (
          <Progress percent={0} />
        ) : (
          <>
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Statistic
                  title="Budget"
                  value={budget}
                  precision={2}
                  prefix="€"
                  styles={{ content: { color: "#1890ff" } }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Used"
                  value={used}
                  precision={2}
                  prefix="€"
                  styles={{ content: { color: percentage >= 100 ? "#ff4d4f" : "#52c41a" } }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Remaining"
                  value={remaining}
                  precision={2}
                  prefix="€"
                  styles={{ content: { color: remaining < 0 ? "#ff4d4f" : "#52c41a" } }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Used"
                  value={percentage}
                  precision={1}
                  suffix="%"
                  styles={{ content: { color: statusColor } }}
                />
              </Col>
            </Row>

            <Progress
              percent={Math.min(percentage, 100)}
              strokeColor={statusColor}
              status={percentage >= 100 ? "exception" : undefined}
            />
            <div style={{ marginTop: 8, color: "#666" }}>
              Status:{" "}
              <strong style={{ color: statusColor }}>{statusText}</strong>
            </div>

            {remaining < 0 && (
              <Alert
                message="Budget Exceeded"
                description={`This cost element has exceeded its budget by €${Math.abs(remaining).toFixed(2)}. No additional cost registrations can be created until the budget is increased or costs are removed.`}
                type="error"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}

            {percentage >= 90 && percentage < 100 && (
              <Alert
                message="Budget Warning"
                description={`This cost element has used ${percentage.toFixed(1)}% of its budget. Consider reviewing before adding more costs.`}
                type="warning"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
          </>
        )}
      </Card>

      {/* EVM Forecast Comparison Section */}
      {latestForecast ? (
        <ForecastComparisonCard
          forecast={latestForecast}
          budgetAmount={Number(costElement.budget_amount)}
          actualCost={actualCost}
        />
      ) : (
        <Card
          title="EVM Analysis"
          style={{ marginTop: 16 }}
        >
          <Empty
            description="No forecast created yet. Create a forecast to see EVM analysis."
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      )}

      {/* Cost Element Details Section */}
      <Card
        title="Cost Element Details"
        extra={
          <Button
            type="primary"
            icon={<EditOutlined />}
            onClick={() => setIsEditModalOpen(true)}
          >
            Update
          </Button>
        }
      >
        <Descriptions
          bordered
          column={{ xs: 1, sm: 1, md: 2, lg: 2 }}
        >
          <Descriptions.Item label="Code">{costElement.code}</Descriptions.Item>
          <Descriptions.Item label="Name">{costElement.name}</Descriptions.Item>
          <Descriptions.Item label="Description" span={2}>
            {costElement.description || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Budget Amount">
            €{Number(costElement.budget_amount).toLocaleString()}
          </Descriptions.Item>
          <Descriptions.Item label="Cost Element Type">
            {costElement.cost_element_type_name || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="WBE">
            {costElement.wbe_name || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Branch">
            {costElement.branch || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Created By">
            {costElement.created_by || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Valid Time">
            {costElement.valid_time
              ? new Date(costElement.valid_time).toLocaleString()
              : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Transaction Time">
            {costElement.transaction_time ?? "-"}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <CostElementModal
        open={isEditModalOpen}
        onCancel={() => setIsEditModalOpen(false)}
        onOk={handleUpdate}
        confirmLoading={updateMutation.isPending}
        initialValues={costElement}
        currentBranch={costElement.branch || "main"}
        wbeId={costElement.wbe_id ?? undefined}
        wbeName={costElement.wbe_name ?? undefined}
      />
    </div>
  );
};
