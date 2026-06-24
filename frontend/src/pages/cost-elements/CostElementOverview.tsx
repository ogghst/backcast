import { useParams } from "react-router-dom";
import { Card, Descriptions } from "antd";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { useCostElementTypes } from "@/features/cost-elements/api/useCostElementTypes";
import { EntityMetadataCard } from "@/components/common/EntityMetadataCard";

export const CostElementOverview = () => {
  const { id } = useParams<{ id: string }>();
  const { data: costElement, isLoading } = useCostElement(id!);
  const { data: costElementTypes = [] } = useCostElementTypes();

  if (isLoading || !costElement) return null;

  const typeName =
    costElement.cost_element_type_name ||
    costElement.cost_element_type_code ||
    costElementTypes.find(
      (t) => t.cost_element_type_id === costElement.cost_element_type_id
    )?.name ||
    "-";

  const workPackageValue = costElement.work_package_name
    ? `${costElement.work_package_code ?? ""} ${costElement.work_package_name}`.trim()
    : undefined;

  return (
    <>
      <Card title="Cost Element Details" size="small">
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Type">
            {typeName}
          </Descriptions.Item>
          <Descriptions.Item label="Description">
            {costElement.description || "-"}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <EntityMetadataCard
        entityId={costElement.cost_element_id}
        entityIdLabel="Cost Element ID"
        parentId={costElement.work_package_id}
        parentLabel="Work Package"
        parentValue={workPackageValue}
        createdAt={costElement.created_at}
        updatedAt={costElement.updated_at}
        createdBy={costElement.created_by_name}
        validTime={costElement.valid_time_formatted}
        cardId="cost-element-metadata-card"
      />
    </>
  );
};
