import { Card, Progress, Statistic, Row, Col, Alert } from "antd";
import type { CostElementRead } from "@/api/generated";
import { useBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";

interface BudgetTabProps {
  costElement: CostElementRead;
}

export const BudgetTab = ({ costElement }: BudgetTabProps) => {
  const { data: budgetStatus, isLoading } = useBudgetStatus(
    costElement.cost_element_id,
  );

  if (isLoading) {
    return <Card loading />;
  }

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

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Budget"
              value={budget}
              precision={2}
              prefix="€"
              styles={{ content: { color: "#1890ff" } }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Used"
              value={used}
              precision={2}
              prefix="€"
              styles={{
                content: { color: percentage >= 100 ? "#ff4d4f" : "#52c41a" },
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Remaining"
              value={remaining}
              precision={2}
              prefix="€"
              styles={{
                content: { color: remaining < 0 ? "#ff4d4f" : "#52c41a" },
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Used"
              value={percentage}
              precision={1}
              suffix="%"
              styles={{ content: { color: statusColor } }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="Budget Progress" style={{ marginBottom: 16 }}>
        <Progress
          percent={Math.min(percentage, 100)}
          strokeColor={statusColor}
          status={percentage >= 100 ? "exception" : undefined}
        />
        <div style={{ marginTop: 8, color: "#666" }}>
          Status: <strong style={{ color: statusColor }}>{statusText}</strong>
        </div>
      </Card>

      <Alert
        message="Budget Exceeded"
        description={`This cost element has exceeded its budget by €${Math.abs(remaining).toFixed(2)}.`}
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {percentage >= 90 && percentage < 100 && (
        <Alert
          message="Budget Warning"
          description={`This cost element has used ${percentage.toFixed(1)}% of its budget. Consider reviewing before adding more costs.`}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
    </div>
  );
};
