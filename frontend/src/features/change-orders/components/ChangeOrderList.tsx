import { App, Badge, Button, Space, Tag } from "antd";
import {
  HistoryOutlined,
  FileTextOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  BranchesOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import type { ColumnType } from "antd/es/table";
import { StandardTable } from "@/components/common/StandardTable";
import type {
  ChangeOrderPublic,
  ChangeOrderCreate,
  ChangeOrderUpdate,
} from "@/api/generated";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";
import { ChangeOrderModal } from "./ChangeOrderModal";
import {
  useChangeOrders,
  useCreateChangeOrder,
  useUpdateChangeOrder,
  useDeleteChangeOrder,
} from "../api/useChangeOrders";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { ChangeOrdersService } from "@/api/generated";

interface ChangeOrderListProps {
  projectId: string;
}

// Status badge colors
const STATUS_COLORS: Record<string, string> = {
  Draft: "default",
  Submitted: "blue",
  "Under Review": "processing",
  Approved: "success",
  Rejected: "error",
  Implemented: "purple",
  Closed: "default",
};

export const ChangeOrderList = ({ projectId }: ChangeOrderListProps) => {
  const [historyOpen, setHistoryOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedChangeOrder, setSelectedChangeOrder] =
    useState<ChangeOrderPublic | null>(null);

  const { modal } = App.useApp();

  // Query change orders for this project
  const { data, isLoading, refetch } = useChangeOrders({
    projectId,
    pagination: { current: 1, pageSize: 20 },
  });
  const changeOrders = data?.items || [];
  const total = data?.total || 0;

  // Extract existing codes for auto-generation
  const existingCodes = changeOrders.map((co) => co.code);

  const { mutateAsync: createChangeOrder } = useCreateChangeOrder({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateChangeOrder } = useUpdateChangeOrder({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteChangeOrder } = useDeleteChangeOrder({
    onSuccess: () => refetch(),
  });

  const handleDelete = (id: string, code: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this change order?",
      content: `Deleting change order ${code}. This action cannot be undone.`,
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteChangeOrder(id),
    });
  };

  const columns: ColumnType<ChangeOrderPublic>[] = [
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      width: 140,
      render: (code: string) => (
        <Space>
          <span style={{ fontWeight: 500 }}>{code}</span>
          <Tag
            icon={<BranchesOutlined />}
            color="geekblue"
            style={{ fontSize: "11px" }}
          >
            co-{code}
          </Tag>
        </Space>
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
      width: 130,
      render: (status: string) => (
        <Badge status={STATUS_COLORS[status] as any} text={status} />
      ),
    },
    {
      title: "Effective Date",
      dataIndex: "effective_date",
      key: "effective_date",
      width: 130,
      render: (date: string | null) =>
        date ? new Date(date).toLocaleDateString() : "-",
    },
    {
      title: "Branch",
      dataIndex: "code",
      key: "branch",
      width: 120,
      render: (code: string) => (
        <Tag color="geekblue" style={{ fontSize: "12px" }}>
          co-{code}
        </Tag>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 140,
      render: (_, record) => (
        <Space size="small">
          <Can permission="change-order-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedChangeOrder(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="change-order-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedChangeOrder(record);
                setModalOpen(true);
              }}
              title="Edit Change Order"
            />
          </Can>
          <Can permission="change-order-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.change_order_id, record.code)}
              title="Delete Change Order"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<ChangeOrderPublic>
        tableParams={{
          pagination: { current: 1, pageSize: 20, total },
        }}
        onChange={() => {}} // Placeholder as pagination logic is static/missing
        loading={isLoading}
        dataSource={changeOrders}
        columns={columns}
        rowKey="change_order_id"
        toolbar={
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div
              style={{
                fontSize: "16px",
                fontWeight: "bold",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <FileTextOutlined />
              Change Orders
            </div>
            <Can permission="change-order-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedChangeOrder(null);
                  setModalOpen(true);
                }}
              >
                New Change Order
              </Button>
            </Can>
          </div>
        }
      />

      <ChangeOrderModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedChangeOrder) {
            await updateChangeOrder({
              id: selectedChangeOrder.change_order_id,
              data: values as ChangeOrderUpdate,
            });
          } else {
            await createChangeOrder(values as ChangeOrderCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedChangeOrder}
        projectId={projectId}
        existingCodes={existingCodes}
      />

      <HistoryDrawerWrapper
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        changeOrder={selectedChangeOrder}
      />
    </div>
  );
};

const HistoryDrawerWrapper = ({
  open,
  onClose,
  changeOrder,
}: {
  open: boolean;
  onClose: () => void;
  changeOrder: ChangeOrderPublic | null;
}) => {
  const { data: history, isLoading } = useEntityHistory({
    resource: "change-orders",
    entityId: changeOrder?.change_order_id,
    fetchFn: (id) => ChangeOrdersService.getChangeOrderHistory(id),
    enabled: open,
  });

  return (
    <VersionHistoryDrawer
      open={open}
      onClose={onClose}
      versions={(history || []).map((v, idx, arr) => {
        const item = v as any;
        return {
          ...item,
          id: `v${arr.length - idx}`,
          valid_from: Array.isArray(item.valid_time)
            ? item.valid_time[0]
            : (item.valid_time as string) || new Date().toISOString(),
          transaction_time: Array.isArray(item.transaction_time)
            ? item.transaction_time[0]
            : (item.transaction_time as string) || new Date().toISOString(),
          changed_by: item.created_by_name || "System",
        };
      })}
      entityName={`Change Order: ${changeOrder?.title || ""} (${changeOrder?.code || ""})`}
      isLoading={isLoading}
    />
  );
};
