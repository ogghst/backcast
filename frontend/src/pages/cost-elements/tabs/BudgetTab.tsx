import { Card, Progress, Statistic, Row, Col, Alert, theme } from "antd";
import type { CostElementRead } from "@/api/generated";
import { useBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";
import { useWBE } from "@/features/wbes/api/useWBEs";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { getCurrencySymbol, formatCurrency } from "@/utils/formatters";
import { useThemeTokens } from "@/hooks/useThemeTokens";

interface BudgetTabProps {
  costElement: CostElementRead;
}

export const BudgetTab = ({ costElement }: BudgetTabProps) => {
  const { token } = theme.useToken();
  const { colors } = useThemeTokens();
  const { data: budgetStatus, isLoading } = useBudgetStatus(
    costElement.cost_element_id,
  );
  const { data: wbe } = useWBE(costElement.wbe_id);
  const currency = useProjectCurrency(wbe?.project_id);
  const currencySymbol = getCurrencySymbol(currency);

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
  let statusColor = colors.success;
  let statusText = "Healthy";

  if (percentage >= 100) {
    statusColor = colors.error;
    statusText = "Exceeded";
  } else if (percentage >= 90) {
    statusColor = colors.warning;
    statusText = "Warning";
  } else if (percentage >= 75) {
    statusColor = colors.primary;
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
              prefix={currencySymbol}
              styles={{ content: { color: token.colorPrimary } }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Used"
              value={used}
              precision={2}
              prefix={currencySymbol}
              styles={{
                content: { color: percentage >= 100 ? token.colorError : token.colorSuccess },
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
              prefix={currencySymbol}
              styles={{
                content: { color: remaining < 0 ? token.colorError : token.colorSuccess },
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
        <div style={{ marginTop: 8, color: token.colorTextTertiary }}>
          Status: <strong style={{ color: statusColor }}>{statusText}</strong>
        </div>
      </Card>

      <Alert
        message="Budget Exceeded"
        description={`This cost element has exceeded its budget by ${formatCurrency(Math.abs(remaining), currency)}.`}
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
