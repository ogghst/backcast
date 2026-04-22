import { Button, Select, Space, Tag, Grid } from "antd";
import type { ColumnType } from "antd/es/table";
import { PlusOutlined, RightOutlined } from "@ant-design/icons";
import { useState, useMemo, useCallback } from "react";
import type { FilterValue, SorterResult } from "antd/es/table/interface";
import { useNavigate } from "react-router-dom";
import { Can } from "@/components/auth/Can";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import type {
  CostElementRead,
  CostElementCreate,
} from "@/api/generated";
import {
  useCostElements,
  useCreateCostElement,
  useUpdateCostElement,
  CreateWithBranch,
} from "@/features/cost-elements/api/useCostElements";
import { useCostElementTypes } from "@/features/cost-elements/api/useCostElementTypes";
import { useWBEs } from "@/features/wbes/api/useWBEs";
import { CostElementModal } from "@/features/cost-elements/components/CostElementModal";
import { CostElementCard } from "@/features/cost-elements/components/CostElementCard";
import { EntityGrid, type SortOption } from "@/components/common/EntityGrid";
import { ViewModeToggle } from "@/components/common/ViewModeToggle";
import { useTableParams } from "@/hooks/useTableParams";
import { useViewMode } from "@/hooks/useViewMode";
import { formatCurrency } from "@/utils/formatters";
import { CostElementFilters } from "@/types/filters";

const SORT_OPTIONS: SortOption[] = [
  { label: "Code", value: "code" },
  { label: "Name", value: "name" },
  { label: "Budget", value: "budget_amount" },
];

interface CostElementManagementProps {
  wbeId?: string;
  wbeName?: string;
}

export const CostElementManagement = ({
  wbeId,
  wbeName,
}: CostElementManagementProps) => {
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const navigate = useNavigate();
  const { viewMode, resolvedMode, cycleViewMode } = useViewMode("cost-elements", isMobile);

  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    CostElementRead,
    CostElementFilters
  >();
  const { branch } = useTimeMachineParams();

  const queryParams = useMemo(
    () => ({
      pagination: tableParams.pagination,
      sortField: tableParams.sortField,
      sortOrder: tableParams.sortOrder,
      filters: tableParams.filters as
        | Record<string, (string | number | boolean)[] | null>
        | undefined,
      search: tableParams.search,
      branch,
      wbe_id: wbeId,
    }),
    [tableParams, branch, wbeId],
  );

  const { data, isLoading, refetch } = useCostElements(queryParams);
  const costElements = data?.items || [];
  const total = data?.total || 0;

  const { data: types = [] } = useCostElementTypes();
  const { data: wbesData } = useWBEs();
  const wbes = wbesData?.items || [];

  const typeMap = useMemo(() => {
    const m: Record<string, string> = {};
    types.forEach((x) => (m[x.cost_element_type_id] = x.name));
    return m;
  }, [types]);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedElement, setSelectedElement] =
    useState<CostElementRead | null>(null);

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

  const handleRowClick = useCallback(
    (ce: CostElementRead) => {
      navigate(`/cost-elements/${ce.cost_element_id}`);
    },
    [navigate],
  );

  const handleGridSortChange = (field: string, order: "ascend" | "descend") => {
    handleTableChange(
      tableParams.pagination!,
      tableParams.filters || {},
      { field, order } as SorterResult<CostElementRead>
    );
  };

  const handleGridPageChange = (page: number, pageSize: number) => {
    handleTableChange(
      { current: page, pageSize },
      tableParams.filters || {},
      {} as SorterResult<CostElementRead>
    );
  };

  const filterControls = (
    <>
      <Select
        placeholder="Type"
        allowClear
        style={{ minWidth: 140 }}
        options={types.map((t) => ({
          label: t.name,
          value: t.cost_element_type_id,
        }))}
        value={
          tableParams.filters?.cost_element_type_id?.[0] as string | undefined
        }
        onChange={(val) => {
          const newFilters = {
            ...tableParams.filters,
            cost_element_type_id: val ? [val] : null,
          };
          handleTableChange(
            tableParams.pagination!,
            newFilters as Record<string, FilterValue | null>,
            {} as SorterResult<CostElementRead>
          );
        }}
      />
      {!wbeId && (
        <Select
          placeholder="WBE"
          allowClear
          style={{ minWidth: 160 }}
          options={wbes.map((w) => ({
            label: w.code,
            value: w.wbe_id,
          }))}
          value={tableParams.filters?.wbe_id?.[0] as string | undefined}
          onChange={(val) => {
            const newFilters = {
              ...tableParams.filters,
              wbe_id: val ? [val] : null,
            };
            handleTableChange(
              tableParams.pagination!,
              newFilters as Record<string, FilterValue | null>,
              {} as SorterResult<CostElementRead>
            );
          }}
        />
      )}
    </>
  );

  const tableColumns: ColumnType<CostElementRead>[] = useMemo(() => {
    const cols: ColumnType<CostElementRead>[] = [
      { title: "Code", dataIndex: "code", key: "code", width: 100, sorter: true },
      { title: "Name", dataIndex: "name", key: "name", sorter: true },
      {
        title: "Type",
        key: "type",
        width: 120,
        render: (_, record) => {
          const name = record.cost_element_type_name || typeMap[record.cost_element_type_id] || "-";
          return <Tag>{name}</Tag>;
        },
      },
      {
        title: "Budget",
        dataIndex: "budget_amount",
        key: "budget_amount",
        width: 150,
        align: "right" as const,
        render: (val) => (val ? formatCurrency(val) : "-"),
        sorter: true,
      },
    ];
    if (!isMobile) {
      cols.push({
        title: "Branch",
        dataIndex: "branch",
        key: "branch",
        width: 100,
        render: (val) => (val ? <Tag>{val}</Tag> : "-"),
      });
    }
    cols.push({
      title: "",
      key: "actions",
      width: 50,
      align: "center" as const,
      render: (_, record) => (
        <Button
          type="text"
          size="small"
          icon={<RightOutlined />}
          onClick={(e) => {
            e.stopPropagation();
            handleRowClick(record);
          }}
        />
      ),
    });
    return cols;
  }, [typeMap, isMobile, handleRowClick]);

  return (
    <div>
      <EntityGrid<CostElementRead>
        items={costElements}
        total={total}
        loading={isLoading}
        renderCard={(ce) => (
          <CostElementCard
            costElement={ce}
            typeNames={typeMap}
          />
        )}
        keyExtractor={(ce) => ce.cost_element_id}
        title={wbeName ? `Cost Elements - ${wbeName}` : "Cost Elements"}
        addContent={
          <Space>
            <ViewModeToggle viewMode={viewMode} onCycleViewMode={cycleViewMode} />
            <Can permission="cost-element-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedElement(null);
                  setModalOpen(true);
                }}
              >
                {isMobile ? undefined : "Add Cost Element"}
              </Button>
            </Can>
          </Space>
        }
        searchValue={tableParams.search || ""}
        onSearch={handleSearch}
        searchPlaceholder="Search cost elements..."
        sortOptions={SORT_OPTIONS}
        sortField={tableParams.sortField}
        sortOrder={tableParams.sortOrder}
        onSortChange={handleGridSortChange}
        filters={filterControls}
        pagination={{
          current: tableParams.pagination?.current || 1,
          pageSize: tableParams.pagination?.pageSize || 10,
        }}
        onPageChange={handleGridPageChange}
        variant={resolvedMode}
        columns={tableColumns}
        onRowClick={handleRowClick}
      />

      <CostElementModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedElement) {
            await updateCostElement({
              id: selectedElement.cost_element_id,
              data: { ...values, branch: branch },
            });
          } else {
            await createCostElement({
              ...(values as CostElementCreate),
              branch: branch,
              wbe_id: wbeId || (values as CostElementCreate).wbe_id,
              control_date: null,
            } as CreateWithBranch);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedElement}
        currentBranch={branch}
        wbeId={wbeId}
        wbeName={wbeName || selectedElement?.wbe_name || undefined}
      />
    </div>
  );
};
