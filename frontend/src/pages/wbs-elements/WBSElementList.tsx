import { Button, Select, Tag } from "antd";
import {
  NodeIndexOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import type { FilterValue, SorterResult } from "antd/es/table/interface";
import { EntityGrid, type SortOption } from "@/components/common/EntityGrid";
import { useTableParams } from "@/hooks/useTableParams";
import {
  WbsElementsService,
  type WBSElementRead,
  type WBSElementCreate,
  type WBSElementUpdate,
} from "@/api/generated";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { Can } from "@/components/auth/Can";
import { WBSElementModal } from "@/features/wbs-elements/components/WBSElementModal";
import { WBSElementCard } from "@/features/wbs-elements/components/WBSElementCard";

import {
  useWBSElements,
  useCreateWBSElement,
  useUpdateWBSElement,
} from "@/features/wbs-elements/api/useWBSElements";

import { WBSElementFilters } from "@/types/filters";

const SORT_OPTIONS: SortOption[] = [
  { label: "Code", value: "code" },
  { label: "Name", value: "name" },
  { label: "Level", value: "level" },
  { label: "Budget", value: "budget_allocation" },
];

interface WBEListProps {
  projectId?: string;
}

export const WBSElementList = ({ projectId }: WBEListProps) => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    WBSElementRead,
    WBSElementFilters
  >();
  const { data, isLoading, refetch } = useWBSElements({
    ...tableParams,
    projectId,
  });
  const wbes = data?.items || [];
  const total = data?.total || 0;

  const [historyOpen, setHistoryOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedWBE, setSelectedWBE] = useState<WBSElementRead | null>(null);

  // Fetch version history for selected WBE
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "wbes",
      entityId: selectedWBE?.wbs_element_id,
      fetchFn: (id) => WbsElementsService.getWbsElementHistory(id),
      enabled: historyOpen,
    }
  );

  const { mutateAsync: createWBE } = useCreateWBSElement({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateWBE } = useUpdateWBSElement({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const handleGridSortChange = (field: string, order: "ascend" | "descend") => {
    handleTableChange(
      tableParams.pagination!,
      tableParams.filters || {},
      { field, order } as SorterResult<WBSElementRead>
    );
  };

  const handleGridPageChange = (page: number, pageSize: number) => {
    handleTableChange(
      { current: page, pageSize },
      tableParams.filters || {},
      {} as SorterResult<WBSElementRead>
    );
  };

  return (
    <div>
      <EntityGrid<WBSElementRead>
        items={wbes}
        total={total}
        loading={isLoading}
        renderCard={(item) => (
          <WBSElementCard
            wbsElement={item}
          />
        )}
        keyExtractor={(w) => w.wbs_element_id}
        title={
          <>
            <NodeIndexOutlined /> WBS Elements
            {projectId && <Tag color="blue">Project: {projectId}</Tag>}
          </>
        }
        addContent={
          <Can permission="wbe-create">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setSelectedWBE(null);
                setModalOpen(true);
              }}
            >
              Add WBS Element
            </Button>
          </Can>
        }
        searchValue={tableParams.search || ""}
        onSearch={handleSearch}
        searchPlaceholder="Search WBS Elements..."
        sortOptions={SORT_OPTIONS}
        sortField={tableParams.sortField}
        sortOrder={tableParams.sortOrder}
        onSortChange={handleGridSortChange}
        filters={
          <Select
            placeholder="Level"
            allowClear
            style={{ minWidth: 100 }}
            options={[
              { label: "L1", value: 1 },
              { label: "L2", value: 2 },
              { label: "L3", value: 3 },
              { label: "L4", value: 4 },
              { label: "L5", value: 5 },
            ]}
            value={tableParams.filters?.level?.[0] as number | undefined}
            onChange={(val) => {
              const newFilters = {
                ...tableParams.filters,
                level: val != null ? [val] : null,
              };
              handleTableChange(
                tableParams.pagination!,
                newFilters as Record<string, FilterValue | null>,
                {} as SorterResult<WBSElementRead>
              );
            }}
          />
        }
        pagination={{
          current: tableParams.pagination?.current || 1,
          pageSize: tableParams.pagination?.pageSize || 10,
        }}
        onPageChange={handleGridPageChange}
      />

      <WBSElementModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedWBE) {
            await updateWBE({
              id: selectedWBE.wbs_element_id,
              data: values as WBSElementUpdate,
            });
          } else {
            await createWBE(values as WBSElementCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedWBE}
        projectId={projectId}
        parentWbsElementId={selectedWBE ? selectedWBE.parent_wbs_element_id : null}
        parentName={
          selectedWBE
            ? selectedWBE.parent_name
            : projectId
              ? "Project Root"
              : null
        }
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={(historyVersions || []).map((version: Record<string, unknown>, idx: number, arr: unknown[]) => ({
          id: `v${arr.length - idx}`,
          valid_from: (version.valid_time as string) || "",
          transaction_time: (version.transaction_time as string) || "",
          valid_to: null,
          changed_by: (version.created_by_name as string) || "System",
        }))}
        entityName={`WBE: ${selectedWBE?.name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};
