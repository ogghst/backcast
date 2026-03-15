/**
 * AgingItemsList Component
 *
 * Displays a list/table of change orders that have been in the same status too long.
 */
import { Card, Typography, Empty, Spin, Table, Tag, Button } from "antd";
import { ExclamationCircleOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";
import type { AgingChangeOrder } from "@/features/change-orders/api/useChangeOrderStats";

const { Title, Text } = Typography;

interface AgingItemsListProps {
  data: AgingChangeOrder[] | undefined;
  projectId: string;
  loading?: boolean;
  thresholdDays?: number;
}

// Impact level color mapping
const IMPACT_COLORS: Record<string, string> = {
  LOW: "green",
  MEDIUM: "gold",
  HIGH: "orange",
  CRITICAL: "red",
};

// SLA status color mapping
const SLA_COLORS: Record<string, string> = {
  pending: "blue",
  approaching: "orange",
  overdue: "red",
};

export const AgingItemsList = ({
  data,
  projectId,
  loading,
  thresholdDays = 7,
}: AgingItemsListProps) => {
  const navigate = useNavigate();

  const columns: ColumnsType<AgingChangeOrder> = [
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      width: 120,
      render: (code: string, record) => (
        <Button
          type="link"
          onClick={() =>
            navigate(`/projects/${projectId}/change-orders/${record.change_order_id}`)
          }
          style={{ padding: 0 }}
        >
          {code}
        </Button>
      ),
    },
    {
      title: "Title",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 150,
      render: (status: string) => <Tag>{status}</Tag>,
    },
    {
      title: "Days Waiting",
      dataIndex: "days_in_status",
      key: "days_in_status",
      width: 120,
      align: "center",
      render: (days: number) => (
        <Text type={days > thresholdDays * 2 ? "danger" : "warning"}>
          <ClockCircleOutlined style={{ marginRight: 4 }} />
          {days}
        </Text>
      ),
    },
    {
      title: "Impact",
      dataIndex: "impact_level",
      key: "impact_level",
      width: 100,
      render: (level: string | null) =>
        level ? (
          <Tag color={IMPACT_COLORS[level] || "default"}>{level}</Tag>
        ) : (
          <Tag>-</Tag>
        ),
    },
    {
      title: "SLA",
      dataIndex: "sla_status",
      key: "sla_status",
      width: 100,
      render: (status: string | null) =>
        status ? (
          <Tag color={SLA_COLORS[status] || "default"}>{status}</Tag>
        ) : (
          <Tag>-</Tag>
        ),
    },
  ];

  if (!data || data.length === 0) {
    return (
      <Card>
        <Title level={5}>
          <ExclamationCircleOutlined style={{ marginRight: 8, color: "#52c41a" }} />
          Aging Items
        </Title>
        {loading ? (
          <Spin />
        ) : (
          <Empty description={`No change orders stuck for more than ${thresholdDays} days`} />
        )}
      </Card>
    );
  }

  return (
    <Card>
      <Title level={5}>
        <ExclamationCircleOutlined style={{ marginRight: 8, color: "#faad14" }} />
        Aging Items ({data.length})
      </Title>
      <Text type="secondary">
        Change orders stuck for more than {thresholdDays} days
      </Text>
      <Table
        dataSource={data}
        columns={columns}
        rowKey="change_order_id"
        pagination={false}
        size="small"
        loading={loading}
        style={{ marginTop: 16 }}
      />
    </Card>
  );
};
