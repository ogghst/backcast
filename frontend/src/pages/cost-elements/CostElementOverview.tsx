import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Card, Descriptions } from "antd";
import { HistoryOutlined } from "@ant-design/icons";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { useCostElementTypes } from "@/features/cost-elements/api/useCostElementTypes";
import { EntityMetadataCard } from "@/components/common/EntityMetadataCard";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { CostElementsService } from "@/api/generated";
import { Can } from "@/components/auth/Can";

export const CostElementOverview = () => {
  const { id } = useParams<{ id: string }>();
  const { data: costElement, isLoading } = useCostElement(id!);
  const { data: costElementTypes = [] } = useCostElementTypes();

  // Version history state
  const [historyOpen, setHistoryOpen] = useState(false);
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory({
    resource: "cost-elements",
    entityId: id,
    fetchFn: (ceId) => CostElementsService.getCostElementHistory(ceId),
    enabled: historyOpen,
  });

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
        extra={
          <Can permission="cost-element-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => setHistoryOpen(true)}
            >
              History
            </Button>
          </Can>
        }
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        entityName={`Cost Element: ${typeName}`}
        isLoading={historyLoading}
        versions={(historyVersions || []).map((version: Record<string, unknown>, idx: number, arr: unknown[]) => {
          const validTimeFormatted = version.valid_time_formatted as {
            lower: string | null;
            upper: string | null;
            lower_formatted: string;
            upper_formatted: string;
            is_currently_valid: boolean;
          } | undefined;
          const transactionTimeFormatted = version.transaction_time_formatted as {
            lower: string | null;
            upper: string | null;
            lower_formatted: string;
            upper_formatted: string;
            is_currently_valid: boolean;
          } | undefined;

          return {
            id: `v${arr.length - idx}`,
            valid_from: validTimeFormatted?.lower || "",
            valid_to: validTimeFormatted?.upper || null,
            transaction_time: transactionTimeFormatted?.lower || "",
            changed_by: (version.created_by_name as string) || "System",
            valid_time_formatted: validTimeFormatted,
            transaction_time_formatted: transactionTimeFormatted,
          };
        })}
      />
    </>
  );
};
