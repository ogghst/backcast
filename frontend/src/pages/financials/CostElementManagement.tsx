import { Button, Select } from "antd";
import {
  PlusOutlined,
} from "@ant-design/icons";
import { useState, useEffect, useMemo } from "react";
import type { FilterValue, SorterResult } from "antd/es/table/interface";
import {
  WbEsService,
  CostElementTypesService,
} from "@/api/generated";
import { Can } from "@/components/auth/Can";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
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
  CreateWithBranch,
} from "@/features/cost-elements/api/useCostElements";
import { CostElementModal } from "@/features/cost-elements/components/CostElementModal";
import { CostElementCard } from "@/features/cost-elements/components/CostElementCard";
import { EntityGrid, type SortOption } from "@/components/common/EntityGrid";
import { useTableParams } from "@/hooks/useTableParams";

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

const SORT_OPTIONS: SortOption[] = [
  { label: "Code", value: "code" },
  { label: "Name", value: "name" },
  { label: "Budget", value: "budget_amount" },
];

export const CostElementManagement = ({
  wbeId,
  wbeName,
}: CostElementManagementProps) => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    CostElementRead,
    CostElementFilters
  >();
  const { branch } = useTimeMachineParams();

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
      branch: branch,
    };
    // If wbeId prop is provided, always filter by it
    if (wbeId) {
      params.filters = {
        ...params.filters,
        wbe_id: [wbeId],
      };
    }
    return params;
  }, [tableParams, branch, wbeId]);

  const { data, isLoading, refetch } = useCostElements(queryParams);
  const costElements = data?.items || [];
  const total = data?.total || 0;

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedElement, setSelectedElement] =
    useState<CostElementRead | null>(null);

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
  const typeMap = useMemo(() => {
    const m: Record<string, string> = {};
    types.forEach((x) => (m[x.cost_element_type_id] = x.name));
    return m;
  }, [types]);

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

  // Build filter controls: Type select + optional WBE select
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
