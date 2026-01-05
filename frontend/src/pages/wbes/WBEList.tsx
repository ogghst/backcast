import { App, Button, Space, Tag } from "antd";
import {
  HistoryOutlined,
  NodeIndexOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import type { ColumnType } from "antd/es/table";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { createResourceHooks } from "@/hooks/useCrud";
import {
  WbEsService,
  type WBERead,
  type WBECreate,
  type WBEUpdate,
} from "@/api/generated";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";
import { WBEModal } from "@/features/wbes/components/WBEModal";

// Adapter for WBEs API
const wbeApi = {
  getUsers: async (params?: {
    pagination?: { current?: number; pageSize?: number };
    projectId?: string;
  }) => {
    const current = params?.pagination?.current || 1;
    const pageSize = params?.pagination?.pageSize || 10;
    const skip = (current - 1) * pageSize;
    const projectId = params?.projectId;

    const res = await WbEsService.getWbes(skip, pageSize, projectId);
    return Array.isArray(res) ? res : (res as { items: WBERead[] }).items;
  },
  getUser: (id: string) => WbEsService.getWbe(id),
  createUser: (data: WBECreate) => WbEsService.createWbe(data),
  updateUser: (id: string, data: WBEUpdate) => WbEsService.updateWbe(id, data),
  deleteUser: (id: string) => WbEsService.deleteWbe(id),
};

const { useList, useCreate, useUpdate, useDelete } = createResourceHooks<
  WBERead,
  WBECreate,
  WBEUpdate
>("wbes", wbeApi);

interface WBEListProps {
  projectId?: string;
}

export const WBEList = ({ projectId }: WBEListProps) => {
  const { tableParams, handleTableChange } = useTableParams<WBERead>();
  const {
    data: wbes,
    isLoading,
    refetch,
  } = useList({
    ...tableParams,
    projectId,
  });

  const [historyOpen, setHistoryOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedWBE, setSelectedWBE] = useState<WBERead | null>(null);

  const { modal } = App.useApp();

  const { mutateAsync: createWBE } = useCreate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateWBE } = useUpdate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteWBE } = useDelete({ onSuccess: () => refetch() });

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this WBE?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteWBE(id),
    });
  };

  const columns: ColumnType<WBERead>[] = [
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      width: 120,
    },
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "Level",
      dataIndex: "level",
      key: "level",
      render: (level: number) => <Tag color="cyan">L{level}</Tag>,
      width: 80,
    },
    {
      title: "Budget Allocation",
      dataIndex: "budget_allocation",
      key: "budget_allocation",
      render: (budget: number) =>
        budget
          ? new Intl.NumberFormat("en-US", {
              style: "currency",
              currency: "USD",
            }).format(budget)
          : "-",
      width: 150,
    },
    {
      title: "Parent WBE",
      dataIndex: "parent_wbe_id",
      key: "parent_wbe_id",
      render: (parentId: string) => (parentId ? parentId : "Root"),
      width: 150,
    },
    {
      title: "Branch",
      dataIndex: "branch",
      key: "branch",
      render: (branch: string) => (
        <Tag color={branch === "main" ? "blue" : "orange"}>
          {branch || "main"}
        </Tag>
      ),
      width: 100,
    },
    {
      title: "Actions",
      key: "actions",
      width: 120,
      render: (_, record) => (
        <Space>
          <Can permission="wbe-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedWBE(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="wbe-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedWBE(record);
                setModalOpen(true);
              }}
              title="Edit WBE"
            />
          </Can>
          <Can permission="wbe-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id)}
              title="Delete WBE"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<WBERead>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={wbes || []}
        columns={columns}
        rowKey="id"
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
              <NodeIndexOutlined />
              Work Breakdown Elements
              {projectId && <Tag color="blue">Project: {projectId}</Tag>}
            </div>
            <Can permission="wbe-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedWBE(null);
                  setModalOpen(true);
                }}
              >
                Add WBE
              </Button>
            </Can>
          </div>
        }
      />

      <WBEModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedWBE) {
            await updateWBE({
              id: selectedWBE.id,
              data: values as WBEUpdate,
            });
          } else {
            await createWBE(values as WBECreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedWBE}
        projectId={projectId}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={[]} // TODO: Implement history fetching when needed
        entityName={`WBE: ${selectedWBE?.name || ""}`}
        isLoading={false}
      />
    </div>
  );
};
