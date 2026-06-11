import { App, Button, Card, Space, Tag } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import type { ColumnType } from "antd/es/table";
import { useQueryClient } from "@tanstack/react-query";
import { createResourceHooks } from "@/hooks/useCrud";
import { CostEventTypesService } from "@/api/generated";
import { Can } from "@/components/auth/Can";
import { queryKeys } from "@/api/queryKeys";
import type {
  CostEventTypeRead,
  CostEventTypeCreate,
  CostEventTypeUpdate,
} from "@/api/generated";
import { CostEventTypeModal } from "@/features/cost-event-types/components/CostEventTypeModal";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";

// Create CRUD hooks
const costEventTypeApi = {
  list: async (params?: {
    pagination?: { current?: number; pageSize?: number };
    search?: string;
    filters?: Record<string, unknown>;
    sortField?: string;
    sortOrder?: string;
  }) => {
    const { pagination, search, filters, sortField, sortOrder } = params || {};
    const page = pagination?.current || 1;
    const perPage = pagination?.pageSize || 20;

    // Convert Ant Design table filters to server format
    let filterString: string | undefined;
    if (filters) {
      const filterParts: string[] = [];
      Object.entries(filters).forEach(([key, value]) => {
        if (
          value &&
          (Array.isArray(value) ? value.length > 0 : value !== undefined)
        ) {
          const values = Array.isArray(value) ? value : [value];
          filterParts.push(`${key}:${values.join(",")}`);
        }
      });
      filterString = filterParts.length > 0 ? filterParts.join(";") : undefined;
    }

    const serverSortOrder = sortOrder === "descend" ? "desc" : "asc";

    const res = await CostEventTypesService.getCostEventTypes(
      page,
      perPage,
      search,
      filterString,
      sortField,
      serverSortOrder,
    );

    return Array.isArray(res) ? res : res.items;
  },
  detail: (id: string) =>
    CostEventTypesService.getCostEventType(id) as Promise<CostEventTypeRead>,
  create: (data: CostEventTypeCreate) =>
    CostEventTypesService.createCostEventType(data) as Promise<CostEventTypeRead>,
  update: (id: string, data: CostEventTypeUpdate) =>
    CostEventTypesService.updateCostEventType(id, data) as Promise<CostEventTypeRead>,
  delete: (id: string) => CostEventTypesService.deleteCostEventType(id),
};

const { useList, useCreate, useUpdate, useDelete } = createResourceHooks<
  CostEventTypeRead,
  CostEventTypeCreate,
  CostEventTypeUpdate
>("cost_event_types", costEventTypeApi as never);

export const CostEventTypeManagement = () => {
  const queryClient = useQueryClient();
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    CostEventTypeRead,
    Record<string, never>
  >();
  const { data: types, isLoading, refetch } = useList(tableParams);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedType, setSelectedType] = useState<CostEventTypeRead | null>(
    null,
  );
  const [historyOpen, setHistoryOpen] = useState(false);

  const invalidateCache = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.costEventTypes.list });
  };

  // Fetch version history
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "cost_event_types",
      entityId: selectedType?.cost_event_type_id,
      fetchFn: (id) => CostEventTypesService.getCostEventTypeHistory(id),
      enabled: historyOpen,
    },
  );

  const { mutateAsync: createType } = useCreate({
    onSuccess: () => {
      refetch();
      invalidateCache();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateType } = useUpdate({
    onSuccess: () => {
      refetch();
      invalidateCache();
      setModalOpen(false);
    },
  });

  const { mutate: deleteType } = useDelete({
    onSuccess: () => {
      refetch();
      invalidateCache();
    },
  });

  const { modal } = App.useApp();

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this cost event type?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteType(id),
    });
  };

  const columns: ColumnType<CostEventTypeRead>[] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true,
    },
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      render: (code, record) => <Tag color={record.color}>{code}</Tag>,
    },
    {
      title: "Color",
      dataIndex: "color",
      key: "color",
      render: (color) =>
        color ? <Tag color={color}>{color}</Tag> : "-",
    },
    {
      title: "Quality",
      dataIndex: "is_quality",
      key: "is_quality",
      width: 80,
      render: (isQuality: boolean) =>
        isQuality ? <Tag color="green">COQ</Tag> : "—",
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, record) => (
        <Space>
          <Can permission="cost-event-type-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedType(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="cost-event-type-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedType(record);
                setModalOpen(true);
              }}
              title="Edit Type"
            />
          </Can>
          <Can permission="cost-event-type-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.cost_event_type_id)}
              title="Delete Type"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card
        title="Cost Event Types"
        extra={
          <Can permission="cost-event-type-create">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setSelectedType(null);
                setModalOpen(true);
              }}
            >
              Add Cost Event Type
            </Button>
          </Can>
        }
      >
        <StandardTable<CostEventTypeRead>
          tableParams={tableParams}
          onChange={handleTableChange}
          loading={isLoading}
          dataSource={(types as CostEventTypeRead[]) || []}
          columns={columns}
          rowKey="cost_event_type_id"
          searchable={true}
          onSearch={handleSearch}
        />
      </Card>

      <CostEventTypeModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedType) {
            await updateType({
              id: selectedType.cost_event_type_id,
              data: values,
            });
          } else {
            await createType(values as CostEventTypeCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedType}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={(historyVersions || []).map((version, idx, arr) => {
          const v = version as unknown as {
            created_at?: string;
            created_by_name?: string;
          };
          return {
            id: `v${arr.length - idx}`,
            valid_from: v.created_at || new Date().toISOString(),
            transaction_time: new Date().toISOString(),
            changed_by: v.created_by_name || "System",
            changes:
              idx === 0 ? { created: "initial" } : { updated: "changed" },
          };
        })}
        entityName={`Type: ${selectedType?.name || ""}`}
        isLoading={historyLoading}
      />
    </>
  );
};
