import { App, Button, Input, Space } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useMemo, useState } from "react";
import type { ColumnType } from "antd/es/table";
import { createResourceHooks } from "@/hooks/useCrud";
import { DepartmentsService } from "@/api/generated";
import { Can } from "@/components/auth/Can";
import type {
  DepartmentRead,
  DepartmentCreate,
  DepartmentUpdate,
} from "@/api/generated";
import { DepartmentModal } from "@/features/departments/components/DepartmentModal";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";

// Create CRUD hooks using the generated API service
const departmentApi = {
  getUsers: async (params?: any) => {
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

    const res = await DepartmentsService.getDepartments(
      page,
      perPage,
      search,
      filterString,
      sortField,
      serverSortOrder
    );

    return Array.isArray(res) ? res : (res as any).items;
  },
  getUser: (id: string) =>
    DepartmentsService.getDepartment(id) as Promise<DepartmentRead>,
  createUser: (data: DepartmentCreate) =>
    DepartmentsService.createDepartment(data) as Promise<DepartmentRead>,
  updateUser: (id: string, data: DepartmentUpdate) =>
    DepartmentsService.updateDepartment(id, data) as Promise<DepartmentRead>,
  deleteUser: (id: string) => DepartmentsService.deleteDepartment(id),
};

const { useList, useCreate, useUpdate, useDelete } = createResourceHooks<
  DepartmentRead,
  DepartmentCreate,
  DepartmentUpdate
>("departments", departmentApi);

import { DepartmentFilters } from "@/types/filters";

export const DepartmentManagement = () => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    DepartmentRead,
    DepartmentFilters
  >();
  const { data: departments, isLoading, refetch } = useList(tableParams);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedDepartment, setSelectedDepartment] =
    useState<DepartmentRead | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  // Fetch version history
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "departments",
      entityId: selectedDepartment?.department_id,
      fetchFn: (id) => DepartmentsService.getDepartmentHistory(id),
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
      title: "Are you sure you want to delete this department?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteDepartment(id),
    });
  };

  const getColumnSearchProps = (
    dataIndex: keyof DepartmentRead
  ): ColumnType<DepartmentRead> => ({
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

  const columns: ColumnType<DepartmentRead>[] = [
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
              title="Edit Department"
            />
          </Can>
          <Can permission="department-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.department_id)}
              title="Delete Department"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<DepartmentRead>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={departments || []}
        columns={columns}
        rowKey="department_id"
        searchable={true}
        searchPlaceholder="Search departments..."
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
              Department Management
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
                Add Department
              </Button>
            </Can>
          </div>
        }
      />

      <DepartmentModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedDepartment) {
            await updateDepartment({
              id: selectedDepartment.department_id,
              data: values,
            });
          } else {
            await createDepartment(values as DepartmentCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedDepartment}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={(historyVersions || []).map((version, idx, arr) => ({
          id: `v${arr.length - idx}`,
          valid_from: version.created_at || new Date().toISOString(), // Use created_at as fallback for valid_from
          transaction_time: new Date().toISOString(), // Transaction time not currently in DepartmentRead
          changed_by: version.created_by_name || "System",
          changes: idx === 0 ? { created: "initial" } : { updated: "changed" },
        }))}
        entityName={`Department: ${selectedDepartment?.name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};
