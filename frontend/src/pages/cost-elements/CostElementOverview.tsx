import { useParams } from "react-router-dom";
import { Space, Card, Descriptions, Typography, theme } from "antd";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { useBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { formatCurrency, formatTemporalRange } from "@/utils/formatters";

const { Text } = Typography;

export const CostElementOverview = () => {
  const { id } = useParams<{ id: string }>();
  const { token } = theme.useToken();
  const { data: costElement, isLoading } = useCostElement(id!);
  const { data: budgetStatus } = useBudgetStatus(id!);

  const currency = useProjectCurrency(undefined);

  if (isLoading || !costElement) return null;

  const amount = costElement.amount ? Number(costElement.amount) : 0;
  const used = budgetStatus?.used ? Number(budgetStatus.used) : 0;
  const remaining = amount - used;

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {/* Basic Info */}
      <Card title="Cost Element Details" size="small">
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Type">
            {costElement.cost_element_type_name || costElement.cost_element_type_code || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Work Package">
            {costElement.work_package_name || costElement.work_package_code || costElement.work_package_id}
          </Descriptions.Item>
          <Descriptions.Item label="Amount">
            <Text strong>{formatCurrency(amount, currency)}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Description">
            {costElement.description || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Created By">
            {costElement.created_by_name || costElement.created_by}
          </Descriptions.Item>
          <Descriptions.Item label="Valid Time">
            {costElement.valid_time_formatted
              ? formatTemporalRange(costElement.valid_time_formatted)
              : "-"}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Budget Summary */}
      <Card title="Budget Status" size="small">
        <Descriptions column={3} bordered size="small">
          <Descriptions.Item label="Budget">
            <Text strong style={{ color: token.colorPrimary }}>
              {formatCurrency(amount, currency)}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="Spent">
            <Text strong style={{ color: used > amount ? token.colorError : token.colorSuccess }}>
              {formatCurrency(used, currency)}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="Remaining">
            <Text strong style={{ color: remaining >= 0 ? token.colorSuccess : token.colorError }}>
              {formatCurrency(remaining, currency)}
            </Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  );
};
