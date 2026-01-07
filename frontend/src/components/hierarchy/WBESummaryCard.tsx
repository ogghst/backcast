import { Card, Descriptions, Tag, Button, Space } from "antd";
import { Link } from "react-router-dom";
import { WBERead } from "@/api/generated";
import {
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import { Can } from "@/components/auth/Can";

interface WBESummaryCardProps {
  wbe: WBERead;
  projectId: string;
  loading?: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onViewHistory?: () => void;
}

export const WBESummaryCard = ({
  wbe,
  projectId,
  loading,
  onEdit,
  onDelete,
  onViewHistory,
}: WBESummaryCardProps) => {
  // Determine parent link
  const parentLink = wbe.parent_wbe_id
    ? `/projects/${projectId}/wbes/${wbe.parent_wbe_id}`
    : `/projects/${projectId}`;

  const parentLabel = wbe.parent_wbe_id ? "Parent WBE" : "Project";

  return (
    <Card
      loading={loading}
      style={{ marginBottom: 16 }}
      extra={
        <Space>
          <Can permission="wbe-read">
            <Button icon={<HistoryOutlined />} onClick={onViewHistory}>
              History
            </Button>
          </Can>
          <Can permission="wbe-update">
            <Button icon={<EditOutlined />} onClick={onEdit}>
              Edit
            </Button>
          </Can>
          <Can permission="wbe-delete">
            <Button danger icon={<DeleteOutlined />} onClick={onDelete}>
              Delete
            </Button>
          </Can>
        </Space>
      }
    >
      <div style={{ marginBottom: 16 }}>
        <h2
          style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}
        >
          <Tag color="cyan">L{wbe.level}</Tag>
          {wbe.code} - {wbe.name}
        </h2>
      </div>

      <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }} bordered>
        <Descriptions.Item label="Code">{wbe.code}</Descriptions.Item>
        <Descriptions.Item label="Level">
          <Tag color="cyan">Level {wbe.level}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Budget Allocation">
          {wbe.budget_allocation
            ? new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: "USD",
              }).format(Number(wbe.budget_allocation))
            : "-"}
        </Descriptions.Item>
        <Descriptions.Item label={parentLabel}>
          <Link to={parentLink}>
            {wbe.parent_wbe_id ? `← Go to Parent WBE` : `← Back to Project`}
          </Link>
        </Descriptions.Item>
        <Descriptions.Item label="Branch">
          <Tag color="orange">{wbe.branch || "main"}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Description" span={3}>
          {wbe.description || "-"}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
};
