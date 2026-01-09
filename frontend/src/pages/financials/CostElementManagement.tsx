import { App, Button, Space, Select, Tag, Input } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
  SearchOutlined,
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
  getUsers: async (
    params?: CostElementApiParams
  ): Promise<PaginatedResponse<CostElementRead>> => {
    // Current Ant Design table params
    const {
      branch = "main",
      pagination,
      filters,
      search,
      sortField,
      sortOrder,
    } = params || {};
    const page = pagination?.current || 1;
    const perPage = pagination?.pageSize || 20;

    // Convert Ant Design table filters to server format
    let filterString: string | undefined;
    if (filters) {
      const filterParts: string[] = [];
      Object.entries(filters).forEach(([key, value]) => {
        // Skip wbe_id and cost_element_type_id as they are handled as explicit params by backend
        if (key === "wbe_id" || key === "cost_element_type_id") return;

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

    const wbeId = filters?.wbe_id?.[0] as string | undefined;
    const typeId = filters?.cost_element_type_id?.[0] as string | undefined;
    const serverSortOrder = sortOrder === "descend" ? "desc" : "asc";

    const res = await CostElementsService.getCostElements(
      page,
      perPage,
      branch,
      wbeId,
      typeId,
      search,
      filterString,
      sortField,
      serverSortOrder
    );

    // Normalize response to PaginatedResponse
    if (Array.isArray(res)) {
      return {
        items: res,
        total: res.length,
        page: 1,
        per_page: res.length,
      };
    }

    // It's already a PaginatedResponse
    return res as unknown as PaginatedResponse<CostElementRead>;
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
  UpdateWithBranch,
  PaginatedResponse<CostElementRead>
>("cost_elements", costElementApi);

interface CostElementManagementProps {
  wbeId?: string;
  wbeName?: string;
}

import { CostElementFilters } from "@/types/filters";

export const CostElementManagement = ({
  wbeId,
  wbeName,
}: CostElementManagementProps) => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    CostElementRead,
    CostElementFilters
  >();
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
      search: tableParams.search,
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

  const { data, isLoading, refetch } = useList(queryParams);
  const costElements = data?.items || [];
  const total = data?.total || 0;

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
        const [wbesRes, typesRes] = await Promise.all([
          WbEsService.getWbes(1, 1000),
          CostElementTypesService.getCostElementTypes(1, 1000),
        ]);
        // Unwrap paginated responses
        const w = Array.isArray(wbesRes)
          ? wbesRes
          : (wbesRes as any).items || [];
        const t = Array.isArray(typesRes)
          ? typesRes
          : (typesRes as any).items || [];
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

  const getColumnSearchProps = (
    dataIndex: keyof CostElementRead
  ): ColumnType<CostElementRead> => ({
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

  const columns: ColumnType<CostElementRead>[] = [
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      sorter: true, // Enable server-side sorting
      render: (code) => <Tag>{code}</Tag>,
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
      title: "Type",
      dataIndex: "cost_element_type_id",
      key: "cost_element_type_id",
      render: (id, record) =>
        record.cost_element_type_name || typeMap[id] || id,
      filters: types.map((t) => ({
        text: t.name,
        value: t.cost_element_type_id,
      })),
      // Remove onFilter - server-side filtering will handle this
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
      // Remove onFilter - server-side filtering will handle this
      // Optionally hide column entirely when wbeId is provided
      hidden: !!wbeId,
    },
    {
      title: "Budget",
      dataIndex: "budget_amount",
      key: "budget_amount",
      align: "right",
      render: (val) => (val ? `€${Number(val).toLocaleString()}` : "-"),
      sorter: true, // Enable server-side sorting
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
        tableParams={{
          ...tableParams,
          pagination: { ...tableParams.pagination, total },
        }}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={costElements || []} // Use raw data - server handles filtering
        columns={columns}
        rowKey="cost_element_id"
        searchable={true}
        searchPlaceholder="Search cost elements..."
        onSearch={handleSearch}
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
