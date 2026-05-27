import { App, Button, Input, Space, theme } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import type { ColumnType } from "antd/es/table";
import { createResourceHooks } from "@/hooks/useCrud";
import { OrganizationalUnitsService } from "@/api/generated";
import type {
  OrganizationalUnitRead,
  OrganizationalUnitCreate,
  OrganizationalUnitUpdate,
} from "@/api/generated";
import { Can } from "@/components/auth/Can";
import { OrganizationalUnitModal } from "@/features/organizational-units/components/OrganizationalUnitModal";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";

// Create CRUD hooks using the generated API service
const organizationalUnitApi = {
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

    const res = await OrganizationalUnitsService.getOrganizationalUnits(
      page,
      perPage,
      search,
      filterString,
      sortField,
      serverSortOrder
    );

    return Array.isArray(res) ? res : res.items;
  },
  detail: (id: string) =>
    OrganizationalUnitsService.getOrganizationalUnit(id) as Promise<OrganizationalUnitRead>,
  create: (data: OrganizationalUnitCreate) =>
    OrganizationalUnitsService.createOrganizationalUnit(data) as Promise<OrganizationalUnitRead>,
  update: (id: string, data: OrganizationalUnitUpdate) =>
    OrganizationalUnitsService.updateOrganizationalUnit(id, data) as Promise<OrganizationalUnitRead>,
  delete: (id: string) => OrganizationalUnitsService.deleteOrganizationalUnit(id),
};

const { useList, useCreate, useUpdate, useDelete } = createResourceHooks<
  OrganizationalUnitRead,
  OrganizationalUnitCreate,
  OrganizationalUnitUpdate
>("organizational-units", organizationalUnitApi as never);

import { OrganizationalUnitFilters } from "@/types/filters";

export const OrganizationalUnitManagement = () => {
  const { token } = theme.useToken();
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    OrganizationalUnitRead,
    OrganizationalUnitFilters
  >();
  const { data: departments, isLoading, refetch } = useList(tableParams);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedDepartment, setSelectedDepartment] =
    useState<OrganizationalUnitRead | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  // Fetch version history
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "organizational-units",
      entityId: selectedDepartment?.organizational_unit_id,
      fetchFn: (id) => OrganizationalUnitsService.getOrganizationalUnitHistory(id),
      enabled: historyOpen,
    }
  );

  const { mutateAsync: createDepartment } = useCreate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateDepartment } = useUpdate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteDepartment } = useDelete({
    onSuccess: () => refetch(),
  });

  const { modal } = App.useApp();

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this organizational unit?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteDepartment(id),
    });
  };

  const getColumnSearchProps = (
    dataIndex: keyof OrganizationalUnitRead
  ): ColumnType<OrganizationalUnitRead> => ({
    filterDropdown: ({
      setSelectedKeys,
      selectedKeys,
      confirm,
      clearFilters,
    }) => (
      <div style={{ padding: token.paddingSM }}>
        <Input
          placeholder={`Search ${String(dataIndex)}`}
          value={selectedKeys[0]}
          onChange={(e) =>
            setSelectedKeys(e.target.value ? [e.target.value] : [])
          }
          onPressEnter={() => confirm()}
          style={{ width: 188, marginBottom: token.marginSM, display: "block" }}
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
      <SearchOutlined
        style={{ color: filtered ? token.colorPrimary : undefined }}
      />
    ),
    onFilter: (value, record) => {
      const fieldVal = record[dataIndex];
      return fieldVal
        ? String(fieldVal)
            .toLowerCase()
            .includes((value as string).toLowerCase())
        : false;
    },
  });

  const columns: ColumnType<OrganizationalUnitRead>[] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true,
      ...getColumnSearchProps("name"),
    },
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      sorter: true,
      ...getColumnSearchProps("code"),
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
      sorter: true,
      ...getColumnSearchProps("description"),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, record) => (
        <Space>
          <Can permission="department-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedDepartment(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="department-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedDepartment(record);
                setModalOpen(true);
              }}
              title="Edit Organizational Unit"
            />
          </Can>
          <Can permission="department-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.organizational_unit_id)}
              title="Delete Organizational Unit"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<OrganizationalUnitRead>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={(departments as OrganizationalUnitRead[]) || []}
        columns={columns}
        rowKey="organizational_unit_id"
        searchable={true}
        searchPlaceholder="Search organizational units..."
        onSearch={handleSearch}
        toolbar={
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div style={{ fontSize: token.fontSizeLG, fontWeight: "bold" }}>
              Organizational Unit Management
            </div>
            <Can permission="department-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedDepartment(null);
                  setModalOpen(true);
                }}
              >
                Add Organizational Unit
              </Button>
            </Can>
          </div>
        }
      />

      <OrganizationalUnitModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedDepartment) {
            await updateDepartment({
              id: selectedDepartment.organizational_unit_id,
              data: values,
            });
          } else {
            await createDepartment(values as OrganizationalUnitCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedDepartment}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={(historyVersions || []).map((version: Record<string, unknown>, idx: number, arr: unknown[]) => ({
          id: `v${arr.length - idx}`,
          valid_from: (version.created_at as string) || new Date().toISOString(),
          transaction_time: new Date().toISOString(),
          changed_by: (version.created_by_name as string) || "System",
          changes: idx === 0 ? { created: "initial" } : { updated: "changed" },
        }))}
        entityName={`Organizational Unit: ${selectedDepartment?.name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};
