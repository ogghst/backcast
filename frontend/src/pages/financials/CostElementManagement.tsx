import { App, Button, Space, Select, Tag, Input } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
  SearchOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import type { ColumnType } from "antd/es/table";
import {
  CostElementsService,
  WbEsService,
  CostElementTypesService,
} from "@/api/generated";
import { Can } from "@/components/auth/Can";
import type {
  CostElementRead,
  CostElementCreate,
  WBERead,
  CostElementTypeRead,
} from "@/api/generated";
import {
  useCostElements,
  useCreateCostElement,
  useUpdateCostElement,
  useDeleteCostElement,
  CreateWithBranch,
} from "@/features/cost-elements/api/useCostElements";
import { CostElementModal } from "@/features/cost-elements/components/CostElementModal";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";

// Extended types for Branch support
// type CreateWithBranch = CostElementCreate & { branch?: string };
// type UpdateWithBranch = CostElementUpdate & { branch?: string };

// Define the interface that was removed but is still used
interface CostElementApiParams {
  branch?: string;
  pagination?: { current?: number; pageSize?: number };
  filters?: Record<string, (string | number | boolean)[] | null>;
  sortField?: string;
  sortOrder?: string;
  search?: string;
  [key: string]: unknown;
}

interface CostElementManagementProps {
  wbeId?: string;
  wbeName?: string;
}

import { CostElementFilters } from "@/types/filters";

export const CostElementManagement = ({
  wbeId,
  wbeName,
}: CostElementManagementProps) => {
  const navigate = useNavigate();
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

  const { data, isLoading, refetch } = useCostElements(queryParams);
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
        // Unwrap paginated responses (wbesRes is any, typesRes is any)
        const w = Array.isArray(wbesRes) ? wbesRes : wbesRes.items || [];
        const t = Array.isArray(typesRes) ? typesRes : typesRes.items || [];
        setWbes(w);
        setTypes(t);
      } catch {
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

  const { mutateAsync: createCostElement } = useCreateCostElement({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateCostElement } = useUpdateCostElement({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteCostElement } = useDeleteCostElement({
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
      render: (id, record) => record.wbe_name || wbeMap[id] || id,
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
        <Space onClick={stopPropagation}>
          <Can permission="cost-element-read">
            <Button
              icon={<EyeOutlined />}
              onClick={() => {
                navigate(`/cost-elements/${record.cost_element_id}`);
              }}
              title="View Details"
            />
          </Can>
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

  // Handle row click to navigate to cost element detail page
  const handleRowClick = (record: CostElementRead) => {
    navigate(`/cost-elements/${record.cost_element_id}`);
  };

  // Stop propagation on action buttons to prevent row click
  const stopPropagation = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

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
        onRow={(record) => ({
          onClick: () => handleRowClick(record),
          style: { cursor: "pointer" },
        })}
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
              // Force cast to solve type mismatch since CreateWithBranch is derived type
              control_date: null,
            } as CreateWithBranch);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedElement}
        currentBranch={currentBranch}
        wbeId={wbeId}
        wbeName={wbeName || selectedElement?.wbe_name || undefined}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={(historyVersions || []).map((version, idx, arr) => {
          // Helper type for history object variations
          type HistoryItem = {
            valid_from?: string;
            valid_time?: string | { lower: string };
            transaction_time?: string | { lower: string };
            created_by_name?: string;
          };
          const v = version as unknown as HistoryItem;

          return {
            id: `v${arr.length - idx}`,
            valid_from:
              v.valid_from ||
              (typeof v.valid_time === "object" ? v.valid_time?.lower : null) ||
              (typeof v.valid_time === "string"
                ? v.valid_time
                : new Date().toISOString()),
            transaction_time:
              (typeof v.transaction_time === "object"
                ? v.transaction_time?.lower
                : null) ||
              (typeof v.transaction_time === "string"
                ? v.transaction_time
                : new Date().toISOString()),
            changed_by: v.created_by_name || "System",
            changes:
              idx === 0 ? { created: "initial" } : { updated: "changed" },
          };
        })}
        entityName={`Cost Element: ${selectedElement?.name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};
