import { App, Button, Space, Select, Tag } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import { useState, useEffect, useMemo } from "react";
import type { ColumnType } from "antd/es/table";
import { createResourceHooks } from "@/hooks/useCrud";
import {
  CostElementsService,
  WbEsService,
  CostElementTypesService,
} from "@/api/generated";
import { Can } from "@/components/auth/Can";
import type {
  CostElementRead,
  CostElementCreate,
  CostElementUpdate,
  WBERead,
  CostElementTypeRead,
} from "@/api/generated";
import { CostElementModal } from "@/features/cost-elements/components/CostElementModal";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";

// Extended types for Branch support
type CreateWithBranch = CostElementCreate & { branch?: string };
type UpdateWithBranch = CostElementUpdate & { branch?: string };
type CostElementApiParams = {
  branch?: string;
  pagination?: { current?: number; pageSize?: number };
  filters?: Record<string, (string | number | boolean)[] | null>;
  sortField?: string;
  sortOrder?: string;
  [key: string]: any;
};

// Custom API wrapper to handle branch and filtering
const costElementApi = {
  getUsers: async (params?: CostElementApiParams) => {
    // Using generic params to match useCrud expectations
    const { branch = "main", pagination, filters } = params || {};
    const current = pagination?.current || 1;
    const pageSize = pagination?.pageSize || 10;
    const skip = (current - 1) * pageSize;

    // Extract filters
    // AntD filters are arrays of values
    const wbe_id =
      filters?.wbe_id && filters.wbe_id.length > 0
        ? (filters.wbe_id[0] as string)
        : undefined;
    const type_id =
      filters?.cost_element_type_id && filters.cost_element_type_id.length > 0
        ? (filters.cost_element_type_id[0] as string)
        : undefined;

    const res = await CostElementsService.getCostElements(
      skip,
      pageSize,
      branch,
      wbe_id,
      type_id
    );
    // Handle both array (Sequence) and paginated response
    return Array.isArray(res) ? res : (res as any).items;
  },
  getUser: (id: string) => CostElementsService.getCostElement(id, "main"),
  createUser: (data: CreateWithBranch) => {
    const { branch, ...rest } = data;
    return CostElementsService.createCostElement(rest, branch || "main");
  },
  updateUser: (id: string, data: UpdateWithBranch) => {
    const { branch, ...rest } = data;
    return CostElementsService.updateCostElement(id, rest, branch || "main");
  },
  deleteUser: (compositeId: string) => {
    // compositeId format: "uuid:::branch"
    const [id, branch] = compositeId.split(":::");
    return CostElementsService.deleteCostElement(id, branch || "main");
  },
};

const { useList, useCreate, useUpdate, useDelete } = createResourceHooks<
  CostElementRead,
  CreateWithBranch,
  UpdateWithBranch
>("cost_elements", costElementApi);

interface CostElementManagementProps {
  wbeId?: string;
  wbeName?: string;
}

export const CostElementManagement = ({
  wbeId,
  wbeName,
}: CostElementManagementProps) => {
  const { tableParams, handleTableChange } = useTableParams();
  const [currentBranch, setCurrentBranch] = useState("main");

  // Build query params, including wbeId filter if provided
  const queryParams = useMemo((): CostElementApiParams => {
    const params: CostElementApiParams = {
      pagination: tableParams.pagination,
      sortField: tableParams.sortField,
      sortOrder: tableParams.sortOrder,
      filters: tableParams.filters as
        | Record<string, (string | number | boolean)[] | null>
        | undefined,
      branch: currentBranch,
    };
    // If wbeId prop is provided, always filter by it
    if (wbeId) {
      params.filters = {
        ...params.filters,
        wbe_id: [wbeId],
      };
    }
    return params;
  }, [tableParams, currentBranch, wbeId]);

  const { data: costElements, isLoading, refetch } = useList(queryParams);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedElement, setSelectedElement] =
    useState<CostElementRead | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  // Lookup data
  const [wbes, setWbes] = useState<WBERead[]>([]);
  const [types, setTypes] = useState<CostElementTypeRead[]>([]);

  // Fetch lookups
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [w, t] = await Promise.all([
          WbEsService.getWbes(0, 1000),
          CostElementTypesService.getCostElementTypes(0, 1000),
        ]);
        setWbes(w);
        setTypes(t);
      } catch (e) {
        /* ignore */
      }
    };
    fetchData();
  }, []);

  // Create Lookup Maps
  const wbeMap = useMemo(() => {
    const m: Record<string, string> = {};
    wbes.forEach((x) => (m[x.wbe_id] = x.code));
    return m;
  }, [wbes]);

  const typeMap = useMemo(() => {
    const m: Record<string, string> = {};
    types.forEach((x) => (m[x.cost_element_type_id] = x.name));
    return m;
  }, [types]);

  // History hook
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "cost_elements",
      entityId: selectedElement?.cost_element_id,
      fetchFn: (id) => CostElementsService.getCostElementHistory(id),
      enabled: historyOpen,
    }
  );

  const { mutateAsync: createCostElement } = useCreate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateCostElement } = useUpdate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteCostElement } = useDelete({
    onSuccess: () => refetch(),
  });

  const { modal } = App.useApp();

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this Cost Element?",
      content: `This will delete it from branch '${currentBranch}'.`,
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteCostElement(`${id}:::${currentBranch}`),
    });
  };

  const columns: ColumnType<CostElementRead>[] = [
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      sorter: true,
      render: (code) => <Tag>{code}</Tag>,
    },
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true,
    },
    {
      title: "Type",
      dataIndex: "cost_element_type_id",
      key: "cost_element_type_id",
      render: (id, record) =>
        record.cost_element_type_name || typeMap[id] || id,
      filters: types.map((t) => ({
        text: t.name,
        value: t.cost_element_type_id,
      })),
    },
    {
      title: "WBE",
      dataIndex: "wbe_id",
      key: "wbe_id",
      render: (id, record) => (record as any).wbe_name || wbeMap[id] || id,
      // Hide WBE filter when wbeId prop is provided (already filtered)
      filters: wbeId
        ? undefined
        : wbes.map((w) => ({ text: w.code, value: w.wbe_id })),
      // Optionally hide column entirely when wbeId is provided
      hidden: !!wbeId,
    },
    {
      title: "Budget",
      dataIndex: "budget_amount",
      key: "budget_amount",
      align: "right",
      render: (val) => (val ? `€${Number(val).toLocaleString()}` : "-"),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, record) => (
        <Space>
          <Can permission="cost-element-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedElement(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="cost-element-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedElement(record);
                setModalOpen(true);
              }}
              title="Edit"
            />
          </Can>
          <Can permission="cost-element-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.cost_element_id)}
              title="Delete"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<CostElementRead>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={costElements || []}
        columns={columns}
        rowKey="cost_element_id"
        toolbar={
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              width: "100%",
            }}
          >
            <Space>
              <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                Cost Elements
              </div>
              <Select
                value={currentBranch}
                onChange={setCurrentBranch}
                style={{ width: 200 }}
                params={{}}
                showSearch
                placeholder="Select Branch"
                options={[
                  { label: "Main", value: "main" },
                  { label: "Draft", value: "draft" },
                  { label: "Dev", value: "dev" },
                ]}
              />
            </Space>

            <Can permission="cost-element-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedElement(null);
                  setModalOpen(true);
                }}
              >
                Add Cost Element
              </Button>
            </Can>
          </div>
        }
      />

      <CostElementModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedElement) {
            await updateCostElement({
              id: selectedElement.cost_element_id,
              data: { ...values, branch: currentBranch },
            });
          } else {
            await createCostElement({
              ...(values as CostElementCreate),
              branch: currentBranch,
              // Pre-fill wbeId when creating from WBE detail page
              wbe_id: wbeId || (values as CostElementCreate).wbe_id,
            });
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedElement}
        currentBranch={currentBranch}
        wbeId={wbeId}
        wbeName={wbeName || (selectedElement as any)?.wbe_name}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={(historyVersions || []).map((version, idx, arr) => ({
          id: `v${arr.length - idx}`,
          valid_from:
            version.valid_from ||
            (version as any).valid_time?.lower ||
            new Date().toISOString(),
          transaction_time:
            (version as any).transaction_time?.lower ||
            new Date().toISOString(),
          changed_by: (version as any).created_by_name || "System",
          changes: idx === 0 ? { created: "initial" } : { updated: "changed" },
        }))}
        entityName={`Cost Element: ${selectedElement?.name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};
