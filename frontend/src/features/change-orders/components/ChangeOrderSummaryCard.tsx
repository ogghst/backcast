import { Card, Descriptions, Tag, Button, Space } from "antd";
import { EditOutlined } from "@ant-design/icons";
import { ChangeOrderPublic } from "@/api/generated";
import dayjs from "dayjs";
import { useWorkflowInfo } from "../hooks/useWorkflowInfo";

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
  const { isBranchLocked } = useWorkflowInfo(
    changeOrder.status,
    changeOrder.available_transitions,
    changeOrder.can_edit_status,
    changeOrder.branch_locked
  );

  return (
    <Card
      title="Change Order Details"
      loading={isLoading}
      id="details"
      style={{ marginBottom: 16 }}
      extra={
        <Space>
          <Button
            type="primary"
            icon={<EditOutlined />}
            onClick={onEdit}
            disabled={isBranchLocked || isLoading}
          >
            Edit
          </Button>
        </Space>
      }
    >
      <Descriptions bordered column={1} labelStyle={{ width: "150px" }}>
        <Descriptions.Item label="Code">
          <Tag color="blue">{changeOrder.code}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Title">{changeOrder.title}</Descriptions.Item>
        <Descriptions.Item label="Status">
          <Tag
            color={
              changeOrder.status === "Approved" || changeOrder.status === "Implemented"
                ? "green"
                : changeOrder.status === "Rejected"
                ? "red"
                : "orange"
            }
          >
            {changeOrder.status}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Effective Date">
          {changeOrder.effective_date
            ? dayjs(changeOrder.effective_date).format("YYYY-MM-DD")
            : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="Description" style={{ whiteSpace: "pre-wrap" }}>
          {changeOrder.description}
        </Descriptions.Item>
        <Descriptions.Item label="Justification" style={{ whiteSpace: "pre-wrap" }}>
          {changeOrder.justification || "-"}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
};
