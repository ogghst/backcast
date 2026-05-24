import { App, Button, Space, Tag } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import type { ColumnType } from "antd/es/table";
import { createResourceHooks } from "@/hooks/useCrud";
import { PackageTypesService } from "@/api/generated";
import { Can } from "@/components/auth/Can";
import type {
  PackageTypeRead,
  PackageTypeCreate,
  PackageTypeUpdate,
} from "@/api/generated";
import { PackageTypeModal } from "@/features/package-type/components/PackageTypeModal";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";

// Create CRUD hooks
const packageTypeApi = {
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

    const res = await PackageTypesService.getPackageTypes(
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
    PackageTypesService.getPackageType(id) as Promise<PackageTypeRead>,
  create: (data: PackageTypeCreate) =>
    PackageTypesService.createPackageType(data) as Promise<PackageTypeRead>,
  update: (id: string, data: PackageTypeUpdate) =>
    PackageTypesService.updatePackageType(id, data) as Promise<PackageTypeRead>,
  delete: (id: string) => PackageTypesService.deletePackageType(id),
};

const { useList, useCreate, useUpdate, useDelete } = createResourceHooks<
  PackageTypeRead,
  PackageTypeCreate,
  PackageTypeUpdate
>("package_types", packageTypeApi as never);

export const PackageTypeManagement = () => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    PackageTypeRead,
    Record<string, never>
  >();
  const { data: types, isLoading, refetch } = useList(tableParams);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedType, setSelectedType] = useState<PackageTypeRead | null>(
    null,
  );
  const [historyOpen, setHistoryOpen] = useState(false);

  // Fetch version history
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "package_types",
      entityId: selectedType?.package_type_id,
      fetchFn: (id) => PackageTypesService.getPackageTypeHistory(id),
      enabled: historyOpen,
    },
  );

  const { mutateAsync: createType } = useCreate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateType } = useUpdate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteType } = useDelete({
    onSuccess: () => refetch(),
  });

  const { modal } = App.useApp();

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this package type?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteType(id),
    });
  };

  const columns: ColumnType<PackageTypeRead>[] = [
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
          <Can permission="package-type-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedType(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="package-type-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedType(record);
                setModalOpen(true);
              }}
              title="Edit Type"
            />
          </Can>
          <Can permission="package-type-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.package_type_id)}
              title="Delete Type"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<PackageTypeRead>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={(types as PackageTypeRead[]) || []}
        columns={columns}
        rowKey="package_type_id"
        searchable={true}
        onSearch={handleSearch}
        toolbar={
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div style={{ fontSize: "16px", fontWeight: "bold" }}>
              Package Types
            </div>
            <Can permission="package-type-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedType(null);
                  setModalOpen(true);
                }}
              >
                Add Package Type
              </Button>
            </Can>
          </div>
        }
      />

      <PackageTypeModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedType) {
            await updateType({
              id: selectedType.package_type_id,
              data: values,
            });
          } else {
            await createType(values as PackageTypeCreate);
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
    </div>
  );
};
