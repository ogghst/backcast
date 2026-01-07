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
  getUsers: async (params?: {
    pagination?: { current?: number; pageSize?: number };
  }) => {
    const current = params?.pagination?.current || 1;
    const pageSize = params?.pagination?.pageSize || 10;
    const skip = (current - 1) * pageSize;
    // Note: API supports department_id filtering, could be added to params later
    const res = await CostElementTypesService.getCostElementTypes(
      skip,
      pageSize,
    );
    return Array.isArray(res)
      ? res
      : (res as { items: CostElementTypeRead[] }).items;
  },
  getUser: (id: string) =>
    CostElementTypesService.getCostElementType(
      id,
    ) as Promise<CostElementTypeRead>,
  createUser: (data: CostElementTypeCreate) =>
    CostElementTypesService.createCostElementType(
      data,
    ) as Promise<CostElementTypeRead>,
  updateUser: (id: string, data: CostElementTypeUpdate) =>
    CostElementTypesService.updateCostElementType(
      id,
      data,
    ) as Promise<CostElementTypeRead>,
  deleteUser: (id: string) => CostElementTypesService.deleteCostElementType(id),
};

const { useList, useCreate, useUpdate, useDelete } = createResourceHooks<
  CostElementTypeRead,
  CostElementTypeCreate,
  CostElementTypeUpdate
>("cost_element_types", costElementTypeApi);

export const CostElementTypeManagement = () => {
  const { tableParams, handleTableChange } = useTableParams();
  const { data: types, isLoading, refetch } = useList(tableParams);

  // Department map for display
  const [departmentMap, setDepartmentMap] = useState<Record<string, string>>(
    {},
  );

  useEffect(() => {
    DepartmentsService.getDepartments(0, 1000).then(
      (depts: DepartmentRead[]) => {
        const map: Record<string, string> = {};
        depts.forEach((d) => (map[d.department_id] = d.name));
        setDepartmentMap(map);
      },
    );
  }, []);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedType, setSelectedType] = useState<CostElementTypeRead | null>(
    null,
  );
  const [historyOpen, setHistoryOpen] = useState(false);

  // Fetch version history
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "cost_element_types",
      entityId: selectedType?.cost_element_type_id,
      fetchFn: (id) => CostElementTypesService.getCostElementTypeHistory(id),
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
          }),
        )}
        entityName={`Type: ${selectedType?.name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};
