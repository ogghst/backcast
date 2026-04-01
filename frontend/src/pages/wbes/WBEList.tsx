import { App, Button, Select, Tag } from "antd";
import {
  NodeIndexOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { FilterValue, SorterResult } from "antd/es/table/interface";
import { EntityGrid, type SortOption } from "@/components/common/EntityGrid";
import { useTableParams } from "@/hooks/useTableParams";
import {
  WbEsService,
  type WBERead,
  type WBECreate,
  type WBEUpdate,
} from "@/api/generated";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { Can } from "@/components/auth/Can";
import { WBEModal } from "@/features/wbes/components/WBEModal";
import { WBECard } from "@/features/wbes/components/WBECard";

import {
  useWBEs,
  useCreateWBE,
  useUpdateWBE,
  useDeleteWBE,
} from "@/features/wbes/api/useWBEs";

import { WBEFilters } from "@/types/filters";

const SORT_OPTIONS: SortOption[] = [
  { label: "Code", value: "code" },
  { label: "Name", value: "name" },
  { label: "Level", value: "level" },
  { label: "Budget", value: "budget_allocation" },
];

interface WBEListProps {
  projectId?: string;
}

export const WBEList = ({ projectId }: WBEListProps) => {
  const navigate = useNavigate();

  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    WBERead,
    WBEFilters
  >();
  const { data, isLoading, refetch } = useWBEs({
    ...tableParams,
    projectId,
  });
  const wbes = data?.items || [];
  const total = data?.total || 0;

  const [historyOpen, setHistoryOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedWBE, setSelectedWBE] = useState<WBERead | null>(null);

  // Fetch version history for selected WBE
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "wbes",
      entityId: selectedWBE?.wbe_id,
      fetchFn: (id) => WbEsService.getWbeHistory(id),
      enabled: historyOpen,
    }
  );

  const { modal } = App.useApp();

  const { mutateAsync: createWBE } = useCreateWBE({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateWBE } = useUpdateWBE({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteWBE } = useDeleteWBE({ onSuccess: () => refetch() });

  const handleDelete = (wbe: WBERead) => {
    modal.confirm({
      title: "Are you sure you want to delete this WBE?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteWBE(wbe.wbe_id),
    });
  };

  const handleOpen = (wbe: WBERead) => {
    if (projectId) {
      navigate(`/projects/${projectId}/wbes/${wbe.wbe_id}`);
    } else {
      navigate(`/projects/${wbe.project_id}/wbes/${wbe.wbe_id}`);
    }
  };

  const handleGridSortChange = (field: string, order: "ascend" | "descend") => {
    handleTableChange(
      tableParams.pagination!,
      tableParams.filters || {},
      { field, order } as SorterResult<WBERead>
    );
  };

  const handleGridPageChange = (page: number, pageSize: number) => {
    handleTableChange(
      { current: page, pageSize },
      tableParams.filters || {},
      {} as SorterResult<WBERead>
    );
  };

  return (
    <div>
      <EntityGrid<WBERead>
        items={wbes}
        total={total}
        loading={isLoading}
        renderCard={(wbe) => (
          <WBECard
            wbe={wbe}
            onEdit={(w) => {
              setSelectedWBE(w);
              setModalOpen(true);
            }}
            onDelete={handleDelete}
            onOpen={handleOpen}
          />
        )}
        keyExtractor={(w) => w.wbe_id}
        title={
          <>
            <NodeIndexOutlined /> Work Breakdown Elements
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
              Add WBE
            </Button>
          </Can>
        }
        searchValue={tableParams.search || ""}
        onSearch={handleSearch}
        searchPlaceholder="Search WBEs..."
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
                {} as SorterResult<WBERead>
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

      <WBEModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedWBE) {
            await updateWBE({
              id: selectedWBE.wbe_id,
              data: values as WBEUpdate,
            });
          } else {
            await createWBE(values as WBECreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedWBE}
        projectId={projectId}
        parentWbeId={selectedWBE ? selectedWBE.parent_wbe_id : null}
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
        versions={(historyVersions || []).map((version, idx, arr) => ({
          id: `v${arr.length - idx}`,
          valid_from: version.valid_time?.[0] || new Date().toISOString(),
          transaction_time:
            version.transaction_time?.[0] || new Date().toISOString(),
          changed_by: version.created_by_name || "System",
          changes: idx === 0 ? { created: "initial" } : { updated: "changed" },
        }))}
        entityName={`WBE: ${selectedWBE?.name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};
