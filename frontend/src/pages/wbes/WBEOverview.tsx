import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Button, Card, Space } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import {
  useWBE,
  useWBEs,
  useCreateWBE,
  useUpdateWBE,
  useDeleteWBE,
} from "@/features/wbes/api/useWBEs";
import { WBECreate, WBERead, WBEUpdate } from "@/api/generated";
import { WBESummaryCard } from "@/components/hierarchy/WBESummaryCard";
import { WBECard } from "@/features/wbes/components/WBECard";
import { WBEModal } from "@/features/wbes/components/WBEModal";
import { DeleteWBEModal } from "@/components/hierarchy/DeleteWBEModal";
import { CostElementManagement } from "@/pages/financials/CostElementManagement";
import { Can } from "@/components/auth/Can";
import { EntityGrid } from "@/components/common/EntityGrid";

/**
 * WBEOverview - Overview sub-page for WBE detail.
 *
 * Displays the WBE summary, child WBEs grid, and cost element management.
 * Owns its own modals for child WBE create/edit/delete operations.
 */
export const WBEOverview = () => {
  const { projectId, wbeId } = useParams<{
    projectId: string;
    wbeId: string;
  }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // WBE data (TanStack Query cache hit — layout already fetches)
  const { data: wbe, isLoading: wbeLoading } = useWBE(wbeId!);

  // Pagination state for child WBEs
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });

  // Child WBEs
  const {
    data,
    isLoading: childrenLoading,
    refetch: refetchChildren,
  } = useWBEs({
    projectId,
    parentWbeId: wbeId,
    pagination: { current: pagination.current, pageSize: pagination.pageSize },
  });
  const childWbes = data?.items || [];

  // Modal state for child WBE create/edit
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedWBE, setSelectedWBE] = useState<WBERead | null>(null);
  const [isCreatingChild, setIsCreatingChild] = useState(false);

  // Delete modal state for child WBEs
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [wbeToDelete, setWbeToDelete] = useState<WBERead | null>(null);

  // Mutations
  const { mutateAsync: createWBE } = useCreateWBE({
    onSuccess: () => {
      refetchChildren();
      setModalOpen(false);
      setIsCreatingChild(false);
    },
  });

  const { mutateAsync: updateWBE } = useUpdateWBE({
    onSuccess: () => {
      refetchChildren();
      queryClient.invalidateQueries({
        queryKey: queryKeys.wbes.detail(wbeId!),
      });
      setModalOpen(false);
    },
  });

  const { mutate: deleteWBE } = useDeleteWBE({
    onSuccess: () => refetchChildren(),
  });

  // Child WBE handlers
  const handleCreateChild = () => {
    setSelectedWBE(null);
    setIsCreatingChild(true);
    setModalOpen(true);
  };

  const handleEdit = (childWbe: WBERead) => {
    setSelectedWBE(childWbe);
    setIsCreatingChild(false);
    setModalOpen(true);
  };

  const handleDelete = (childWbe: WBERead) => {
    setWbeToDelete(childWbe);
    setDeleteModalOpen(true);
  };

  const handleRowClick = (childWbe: WBERead) => {
    navigate(`/projects/${projectId}/wbes/${childWbe.wbe_id}`);
  };

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {/* WBE Summary */}
      {wbe && <WBESummaryCard wbe={wbe} loading={wbeLoading} />}

      {/* Child WBEs Section */}
      <EntityGrid<WBERead>
        items={childWbes}
        total={data?.total || 0}
        loading={childrenLoading}
        renderCard={(childWbe) => (
          <WBECard
            wbe={childWbe}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onOpen={handleRowClick}
          />
        )}
        keyExtractor={(w) => w.wbe_id}
        title="Child WBEs"
        addContent={
          <Can permission="wbe-create">
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateChild}>
              Add Child WBE
            </Button>
          </Can>
        }
        searchValue=""
        onSearch={() => {}}
        searchPlaceholder="Search child WBEs..."
        sortOptions={[
          { label: "Code", value: "code" },
          { label: "Name", value: "name" },
          { label: "Budget", value: "budget_allocation" },
        ]}
        sortField={undefined}
        sortOrder={undefined}
        onSortChange={() => {}}
        pagination={pagination}
        onPageChange={(page, pageSize) =>
          setPagination({ current: page, pageSize })
        }
        minCardWidth={280}
      />

      {/* Cost Elements Section */}
      <Card title="Cost Elements">
        {wbeId && <CostElementManagement wbeId={wbeId} wbeName={wbe?.name} />}
      </Card>

      {/* Child WBE Create/Edit Modal */}
      <WBEModal
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          setIsCreatingChild(false);
        }}
        onOk={async (values) => {
          if (selectedWBE) {
            // Edit existing child
            await updateWBE({
              id: selectedWBE.wbe_id,
              data: values as WBEUpdate,
            });
          } else if (isCreatingChild && wbe) {
            // Create child of current WBE
            await createWBE({
              ...values,
              project_id: projectId!,
              level: (wbe.level || 1) + 1,
            } as WBECreate);
          }
        }}
        confirmLoading={false}
        initialValues={selectedWBE}
        projectId={projectId}
        parentWbeId={isCreatingChild ? wbe?.wbe_id : selectedWBE?.parent_wbe_id}
        parentName={isCreatingChild ? wbe?.name : selectedWBE?.parent_name}
      />

      {/* Child WBE Delete Modal */}
      <DeleteWBEModal
        wbe={wbeToDelete}
        open={deleteModalOpen}
        onCancel={() => {
          setDeleteModalOpen(false);
          setWbeToDelete(null);
        }}
        onConfirm={() => {
          if (wbeToDelete) {
            deleteWBE(wbeToDelete.wbe_id);
            setDeleteModalOpen(false);
            setWbeToDelete(null);
          }
        }}
      />
    </Space>
  );
};
