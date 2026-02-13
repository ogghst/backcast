import { App, Button, Input, Space, Tag } from "antd";
import {
  HistoryOutlined,
  NodeIndexOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useMemo, useState } from "react";
import type { ColumnType } from "antd/es/table";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import {
  WbEsService,
  type WBERead,
  type WBECreate,
  type WBEUpdate,
} from "@/api/generated";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { Can } from "@/components/auth/Can";
import { WBEModal } from "@/features/wbes/components/WBEModal";

import {
  useWBEs,
  useCreateWBE,
  useUpdateWBE,
  useDeleteWBE,
} from "@/features/wbes/api/useWBEs";

import { WBEFilters } from "@/types/filters";

interface WBEListProps {
  projectId?: string;
}

export const WBEList = ({ projectId }: WBEListProps) => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    WBERead,
    WBEFilters
  >();
  const { data, isLoading, refetch } = useWBEs({
    ...tableParams,
    projectId,
  });
  const wbes = data?.items || [];
  const total = data?.total || 0;

  const [historyOpen, setHistoryOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedWBE, setSelectedWBE] = useState<WBERead | null>(null);

  // Fetch version history for selected WBE
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "wbes",
      entityId: selectedWBE?.wbe_id,
      fetchFn: (id) => WbEsService.getWbeHistory(id),
      enabled: historyOpen,
    }
  );

  const { modal } = App.useApp();

  const { mutateAsync: createWBE } = useCreateWBE({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateWBE } = useUpdateWBE({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteWBE } = useDeleteWBE({ onSuccess: () => refetch() });

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this WBE?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteWBE(id),
    });
  };

  const getColumnSearchProps = (
    dataIndex: keyof WBERead
  ): ColumnType<WBERead> => ({
    filterDropdown: ({
      setSelectedKeys,
      selectedKeys,
      confirm,
      clearFilters,
    }) => (
      <div style={{ padding: 8 }}>
        <Input
          placeholder={`Search ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e) =>
            setSelectedKeys(e.target.value ? [e.target.value] : [])
          }
          onPressEnter={() => confirm()}
          style={{ width: 188, marginBottom: 8, display: "block" }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => confirm()}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            Search
          </Button>
          <Button
            onClick={() => clearFilters && clearFilters()}
            size="small"
            style={{ width: 90 }}
          >
            Reset
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? "#1890ff" : undefined }} />
    ),
    onFilter: (value, record) => {
      const fieldVal = record[dataIndex];
      return fieldVal
        ? fieldVal
            .toString()
            .toLowerCase()
            .includes((value as string).toLowerCase())
        : false;
    },
  });

  // Extract unique levels for filters (static list)
  const levelFilters = useMemo(() => {
    // Common WBE levels - could be fetched from API in the future
    return [
      { text: "L1", value: 1 },
      { text: "L2", value: 2 },
      { text: "L3", value: 3 },
      { text: "L4", value: 4 },
      { text: "L5", value: 5 },
    ];
  }, []);

  const columns: ColumnType<WBERead>[] = [
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      width: 120,
      sorter: true, // Enable server-side sorting
      ...getColumnSearchProps("code"),
    },
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true, // Enable server-side sorting
      ...getColumnSearchProps("name"),
    },
    {
      title: "Level",
      dataIndex: "level",
      key: "level",
      render: (level: number) => <Tag color="cyan">L{level}</Tag>,
      width: 80,
      filters: levelFilters,
      // Remove onFilter - server-side filtering will handle this
      sorter: true, // Enable server-side sorting
    },
    {
      title: "Budget Allocation",
      dataIndex: "budget_allocation",
      key: "budget_allocation",
      render: (budget: number) =>
        budget
          ? new Intl.NumberFormat("en-US", {
              style: "currency",
              currency: "EUR",
              currencyDisplay: "narrowSymbol",
            }).format(budget)
          : "-",
      width: 150,
      sorter: true, // Enable server-side sorting
    },
    {
      title: "Parent WBE",
      dataIndex: "parent_wbe_id",
      key: "parent_wbe_id",
      render: (parentId: string) => (parentId ? parentId : "Root"),
      width: 150,
      sorter: true, // Enable server-side sorting
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
              onClick={() => handleDelete(record.wbe_id)}
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
        tableParams={{
          ...tableParams,
          pagination: { ...tableParams.pagination, total },
        }}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={wbes} // Use raw data - hierarchical queries return arrays
        columns={columns}
        rowKey="wbe_id"
        searchable={true}
        searchPlaceholder="Search WBEs..."
        onSearch={handleSearch}
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
              id: selectedWBE.wbe_id,
              data: values as WBEUpdate,
            });
          } else {
            await createWBE(values as WBECreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedWBE}
        projectId={projectId}
        parentWbeId={selectedWBE ? selectedWBE.parent_wbe_id : null}
        parentName={
          selectedWBE
            ? selectedWBE.parent_name
            : projectId
              ? "Project Root"
              : null
        }
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={(historyVersions || []).map((version, idx, arr) => ({
          id: `v${arr.length - idx}`,
          valid_from: version.valid_time?.[0] || new Date().toISOString(),
          transaction_time:
            version.transaction_time?.[0] || new Date().toISOString(),
          changed_by: version.created_by_name || "System",
          changes: idx === 0 ? { created: "initial" } : { updated: "changed" },
        }))}
        entityName={`WBE: ${selectedWBE?.name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};
