import { Table, Button, Space } from "antd";
import type { ColumnType } from "antd/es/table";
import { WBERead } from "@/api/generated";
import { EditOutlined, DeleteOutlined, RightOutlined } from "@ant-design/icons";
import { Can } from "@/components/auth/Can";

interface WBETableProps {
  wbes: WBERead[];
  loading?: boolean;
  onRowClick?: (wbe: WBERead) => void;
  onEdit?: (wbe: WBERead) => void;
  onDelete?: (wbe: WBERead) => void;
}

export const WBETable = ({
  wbes,
  loading,
  onRowClick,
  onEdit,
  onDelete,
}: WBETableProps) => {
  const columns: ColumnType<WBERead>[] = [
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      width: 100,
      sorter: (a, b) =>
        a.code.localeCompare(b.code, undefined, { numeric: true }),
    },
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "Budget",
      dataIndex: "budget_allocation",
      key: "budget_allocation",
      render: (val) =>
        val
          ? new Intl.NumberFormat("en-US", {
              style: "currency",
              currency: "EUR",
            }).format(val)
          : "-",
      width: 150,
      align: "right",
    },
    {
      title: "Actions",
      key: "actions",
      width: 150,
      align: "center",
      render: (_, record) => (
        <Space onClick={(e) => e.stopPropagation()}>
          <Can permission="wbe-update">
            <Button
              icon={<EditOutlined />}
              size="small"
              onClick={() => onEdit?.(record)}
              title="Edit"
            />
          </Can>
          <Can permission="wbe-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              size="small"
              onClick={() => onDelete?.(record)}
              title="Delete"
            />
          </Can>
          <Button
            type="primary"
            ghost
            size="small"
            icon={<RightOutlined />}
            onClick={() => onRowClick?.(record)}
            title="Drill Down"
          >
            Open
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Table
      dataSource={wbes}
      columns={columns}
      rowKey="wbe_id"
      loading={loading}
      onRow={(record) => ({
        onClick: () => onRowClick?.(record),
        style: { cursor: "pointer" },
      })}
      pagination={false}
      size="middle"
    />
  );
};
