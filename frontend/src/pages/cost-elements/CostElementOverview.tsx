import { useParams } from "react-router-dom";
import { Card, Descriptions, Typography } from "antd";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { useCostElementTypes } from "@/features/cost-elements/api/useCostElementTypes";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { formatCurrency, formatTemporalRange } from "@/utils/formatters";

const { Text } = Typography;

export const CostElementOverview = () => {
  const { id } = useParams<{ id: string }>();
  const { data: costElement, isLoading } = useCostElement(id!);
  const { data: costElementTypes = [] } = useCostElementTypes();

  const currency = useProjectCurrency(undefined);

  if (isLoading || !costElement) return null;

  const amount = costElement.amount ? Number(costElement.amount) : 0;

  const typeName =
    costElement.cost_element_type_name ||
    costElement.cost_element_type_code ||
    costElementTypes.find(
      (t) => t.cost_element_type_id === costElement.cost_element_type_id
    )?.name ||
    "-";

  return (
    <Card title="Cost Element Details" size="small">
      <Descriptions column={2} bordered size="small">
        <Descriptions.Item label="Type">
          {typeName}
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
  );
};
