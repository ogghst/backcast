/**
 * ApprovalWorkloadTable Component
 *
 * Displays a table showing pending approval workload grouped by approver.
 */
import { Card, Typography, Empty, Spin, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { ApprovalWorkloadItem } from "@/features/change-orders/api/useChangeOrderStats";

const { Title } = Typography;

interface ApprovalWorkloadTableProps {
  data: ApprovalWorkloadItem[] | undefined;
  loading?: boolean;
}

export const ApprovalWorkloadTable = ({
  data,
  loading,
}: ApprovalWorkloadTableProps) => {
  const columns: ColumnsType<ApprovalWorkloadItem> = [
    {
      title: "Approver",
      dataIndex: "approver_name",
      key: "approver_name",
      width: 200,
    },
    {
      title: "Pending",
      dataIndex: "pending_count",
      key: "pending_count",
      width: 100,
      align: "center",
      render: (count: number) => (
        <Tag color={count > 5 ? "orange" : "blue"}>{count}</Tag>
      ),
    },
    {
      title: "Overdue",
      dataIndex: "overdue_count",
      key: "overdue_count",
      width: 100,
      align: "center",
      render: (count: number) => (
        <Tag color={count > 0 ? "red" : "green"}>{count}</Tag>
      ),
    },
    {
      title: "Avg Days Waiting",
      dataIndex: "avg_days_waiting",
      key: "avg_days_waiting",
      width: 150,
      align: "center",
      render: (days: number) => days.toFixed(1),
    },
  ];

  if (!data || data.length === 0) {
    return (
      <Card>
        <Title level={5}>Approval Workload</Title>
        {loading ? <Spin /> : <Empty description="No pending approvals" />}
      </Card>
    );
  }

  return (
    <Card>
      <Title level={5}>Approval Workload</Title>
      <Table
        dataSource={data}
        columns={columns}
        rowKey="approver_id"
        pagination={false}
        size="small"
        loading={loading}
        summary={() => {
          const totalPending = data.reduce((sum, item) => sum + item.pending_count, 0);
          const totalOverdue = data.reduce((sum, item) => sum + item.overdue_count, 0);
          const avgDays = data.reduce((sum, item) => sum + item.avg_days_waiting, 0) / data.length;
          return (
            <Table.Summary.Row>
              <Table.Summary.Cell index={0}>
                <strong>Total</strong>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={1} align="center">
                <Tag color="blue">{totalPending}</Tag>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={2} align="center">
                <Tag color={totalOverdue > 0 ? "red" : "green"}>{totalOverdue}</Tag>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={3} align="center">
                {avgDays.toFixed(1)}
              </Table.Summary.Cell>
            </Table.Summary.Row>
          );
        }}
      />
    </Card>
  );
};
