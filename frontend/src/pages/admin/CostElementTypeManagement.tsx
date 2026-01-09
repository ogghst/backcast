import { App, Button, Space, Tag } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import { useState, useEffect } from "react";
import type { ColumnType } from "antd/es/table";
import { createResourceHooks } from "@/hooks/useCrud";
import { CostElementTypesService, DepartmentsService } from "@/api/generated";
import { Can } from "@/components/auth/Can";
import type {
  CostElementTypeRead,
  CostElementTypeCreate,
  CostElementTypeUpdate,
  DepartmentRead,
} from "@/api/generated";
import { CostElementTypeModal } from "@/features/cost-element-types/components/CostElementTypeModal";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";

// Create CRUD hooks
const costElementTypeApi = {
  getUsers: async (params?: any) => {
    const { pagination, search, filters, sortField, sortOrder } = params || {};
    const page = pagination?.current || 1;
    const perPage = pagination?.pageSize || 20;

    // Convert Ant Design table filters to server format
    let filterString: string | undefined;
    if (filters) {
      const filterParts: string[] = [];
      Object.entries(filters).forEach(([key, value]) => {
        if (key === "department_id") return; // Handled as explicit param
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

    const deptId = filters?.department_id?.[0] as string | undefined;
    const serverSortOrder = sortOrder === "descend" ? "desc" : "asc";

    const res = await CostElementTypesService.getCostElementTypes(
      page,
      perPage,
      deptId,
      search,
      filterString,
      sortField,
      serverSortOrder
    );

    return Array.isArray(res) ? res : (res as any).items;
  },
  getUser: (id: string) =>
    CostElementTypesService.getCostElementType(
      id
    ) as Promise<CostElementTypeRead>,
  createUser: (data: CostElementTypeCreate) =>
    CostElementTypesService.createCostElementType(
      data
    ) as Promise<CostElementTypeRead>,
  updateUser: (id: string, data: CostElementTypeUpdate) =>
    CostElementTypesService.updateCostElementType(
      id,
      data
    ) as Promise<CostElementTypeRead>,
  deleteUser: (id: string) => CostElementTypesService.deleteCostElementType(id),
};

const { useList, useCreate, useUpdate, useDelete } = createResourceHooks<
  CostElementTypeRead,
  CostElementTypeCreate,
  CostElementTypeUpdate
>("cost_element_types", costElementTypeApi);

import { CostElementTypeFilters } from "@/types/filters";

export const CostElementTypeManagement = () => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    CostElementTypeRead,
    CostElementTypeFilters
  >();
  const { data: types, isLoading, refetch } = useList(tableParams);

  // Department map for display
  const [departmentMap, setDepartmentMap] = useState<Record<string, string>>(
    {}
  );

  useEffect(() => {
    DepartmentsService.getDepartments(1, 1000).then((res: any) => {
      const depts = Array.isArray(res) ? res : res.items || [];
      const map: Record<string, string> = {};
      depts.forEach((d: any) => (map[d.department_id] = d.name));
      setDepartmentMap(map);
    });
  }, []);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedType, setSelectedType] = useState<CostElementTypeRead | null>(
    null
  );
  const [historyOpen, setHistoryOpen] = useState(false);

  // Fetch version history
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "cost_element_types",
      entityId: selectedType?.cost_element_type_id,
      fetchFn: (id) => CostElementTypesService.getCostElementTypeHistory(id),
      enabled: historyOpen,
    }
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
      title: "Are you sure you want to delete this cost element type?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteType(id),
    });
  };

  const columns: ColumnType<CostElementTypeRead>[] = [
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
      render: (code) => <Tag>{code}</Tag>,
    },
    {
      title: "Department",
      dataIndex: "department_id",
      key: "department_id",
      render: (id) => departmentMap[id] || id,
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
          <Can permission="cost-element-type-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedType(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="cost-element-type-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedType(record);
                setModalOpen(true);
              }}
              title="Edit Type"
            />
          </Can>
          <Can permission="cost-element-type-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.cost_element_type_id)}
              title="Delete Type"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<CostElementTypeRead>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={types || []}
        columns={columns}
        rowKey="cost_element_type_id"
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
              Cost Element Types
            </div>
            <Can permission="cost-element-type-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedType(null);
                  setModalOpen(true);
                }}
              >
                Add Type
              </Button>
            </Can>
          </div>
        }
      />

      <CostElementTypeModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedType) {
            await updateType({
              id: selectedType.cost_element_type_id,
              data: values,
            });
          } else {
            await createType(values as CostElementTypeCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedType}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={((historyVersions as any[]) || []).map(
          (version, idx, arr) => ({
            id: `v${arr.length - idx}`,
            valid_from: version.created_at || new Date().toISOString(),
            transaction_time: new Date().toISOString(),
            changed_by: version.created_by_name || "System",
            changes:
              idx === 0 ? { created: "initial" } : { updated: "changed" },
          })
        )}
        entityName={`Type: ${selectedType?.name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};
