import { theme, Card, Descriptions, Tag, Button, Space, Divider, Typography } from "antd";
import { EditOutlined } from "@ant-design/icons";
import { ChangeOrderPublic } from "@/api/generated";
import { formatDate } from "@/utils/formatters";
import { useWorkflowInfo } from "../hooks/useWorkflowInfo";
import { CustomFieldsRenderer } from "@/features/custom-fields/components/CustomFieldsRenderer";

interface ChangeOrderSummaryCardProps {
  changeOrder: ChangeOrderPublic;
  onEdit: () => void;
  isLoading?: boolean;
}

export const ChangeOrderSummaryCard = ({
  changeOrder,
  onEdit,
  isLoading,
}: ChangeOrderSummaryCardProps) => {
  const { token } = theme.useToken();
  const { isStatusDisabled } = useWorkflowInfo(
    changeOrder.status,
    changeOrder.available_transitions,
    changeOrder.can_edit_status,
    changeOrder.branch_locked
  );

  const fieldDefinitions = changeOrder.custom_field_definitions_snapshot ?? undefined;
  const hasCustomFields =
    !!fieldDefinitions && Object.keys(fieldDefinitions).length > 0;

  return (
    <Card
      title="Change Order Details"
      loading={isLoading}
      id="details"
      style={{ marginBottom: token.marginMD }}
      extra={
        <Space>
          <Button
            type="primary"
            icon={<EditOutlined />}
            onClick={onEdit}
            disabled={isStatusDisabled || isLoading}
          >
            Edit
          </Button>
        </Space>
      }
    >
      <Descriptions bordered column={1} styles={{ label: { width: "150px" } }}>
        <Descriptions.Item label="Code">
          <Tag color="blue">{changeOrder.code}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Title">{changeOrder.title}</Descriptions.Item>
        <Descriptions.Item label="Status">
          <Tag
            color={
              changeOrder.status === "approved" || changeOrder.status === "implemented"
                ? "green"
                : changeOrder.status === "rejected"
                ? "red"
                : "orange"
            }
          >
            {changeOrder.status}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Effective Date">
          {changeOrder.effective_date
            ? formatDate(changeOrder.effective_date, { style: "short" })
            : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="Description" style={{ whiteSpace: "pre-wrap" }}>
          {changeOrder.description}
        </Descriptions.Item>
        <Descriptions.Item label="Justification" style={{ whiteSpace: "pre-wrap" }}>
          {changeOrder.justification || "-"}
        </Descriptions.Item>
      </Descriptions>

      {hasCustomFields && (
        <>
          <Divider style={{ marginBlock: token.marginMD }} />
          <Typography.Text
            strong
            style={{ display: "block", marginBottom: token.marginXS }}
          >
            Custom Fields
          </Typography.Text>
          <CustomFieldsRenderer
            readOnly
            fieldDefinitions={fieldDefinitions!}
            values={changeOrder.custom_fields ?? undefined}
          />
        </>
      )}
    </Card>
  );
};
