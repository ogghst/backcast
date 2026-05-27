import { useParams } from "react-router-dom";
import { Space, Card, Descriptions, Typography, theme, Row, Col, Statistic, Progress, Alert } from "antd";
import { useWorkPackage } from "@/features/work-packages/api/useWorkPackages";
import { useWorkPackageBudgetStatus } from "@/features/work-packages/api/useWorkPackages";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { formatCurrency, formatTemporalRange, getCurrencySymbol } from "@/utils/formatters";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { Text } = Typography;

export const WorkPackageOverview = () => {
  const { id } = useParams<{ id: string }>();
  const { token } = theme.useToken();
  const { colors } = useThemeTokens();
  const { data: workPackage, isLoading } = useWorkPackage(id!);
  const { data: budgetStatus, isLoading: budgetLoading } = useWorkPackageBudgetStatus(id!);

  const currency = useProjectCurrency(undefined);
  const currencySymbol = getCurrencySymbol(currency);

  if (isLoading || !workPackage) return null;

  const budget = budgetStatus?.budget
    ? Number(budgetStatus.budget)
    : Number(workPackage.budget_amount || 0);
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
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {/* Basic Info */}
      <Card title="Work Package Details" size="small">
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Code">
            <Text strong>{workPackage.code}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Name">
            {workPackage.name}
          </Descriptions.Item>
          <Descriptions.Item label="Status">
            {workPackage.status || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Control Account">
            {workPackage.control_account_name || workPackage.control_account_id}
          </Descriptions.Item>
          <Descriptions.Item label="Budget Amount">
            <Text strong>{formatCurrency(Number(workPackage.budget_amount || 0), currency)}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Description">
            {workPackage.description || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Created By">
            {workPackage.created_by_name || workPackage.created_by}
          </Descriptions.Item>
          <Descriptions.Item label="Valid Time">
            {workPackage.valid_time_formatted
              ? formatTemporalRange(workPackage.valid_time_formatted)
              : "-"}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Budget Summary */}
      {!budgetLoading && (
        <>
          <Row gutter={[16, 16]}>
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
                  title="Used %"
                  value={percentage}
                  precision={1}
                  suffix="%"
                  styles={{ content: { color: statusColor } }}
                />
              </Card>
            </Col>
          </Row>

          <Card title="Budget Progress" size="small">
            <Progress
              percent={Math.min(percentage, 100)}
              strokeColor={statusColor}
              status={percentage >= 100 ? "exception" : undefined}
            />
            <div style={{ marginTop: 8, color: token.colorTextTertiary }}>
              Status: <strong style={{ color: statusColor }}>{statusText}</strong>
            </div>
          </Card>

          {percentage >= 100 && (
            <Alert
              message="Budget Exceeded"
              description={`This work package has exceeded its budget by ${formatCurrency(Math.abs(remaining), currency)}.`}
              type="warning"
              showIcon
            />
          )}
          {percentage >= 90 && percentage < 100 && (
            <Alert
              message="Budget Warning"
              description={`This work package has used ${percentage.toFixed(1)}% of its budget. Consider reviewing before adding more costs.`}
              type="warning"
              showIcon
            />
          )}
        </>
      )}
    </Space>
  );
};
