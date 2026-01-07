import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Button, Card } from "antd";
import { PlusOutlined } from "@ant-design/icons";

import {
  useWBE,
  useWBEs,
  useWBEBreadcrumb,
  useCreateWBE,
  useUpdateWBE,
  useDeleteWBE,
  useWBEHistory,
} from "@/features/wbes/api/useWBEs";
import { WBECreate, WBERead, WBEUpdate } from "@/api/generated";
import { WBESummaryCard } from "@/components/hierarchy/WBESummaryCard";
import { WBETable } from "@/components/hierarchy/WBETable";
import { BreadcrumbBuilder } from "@/components/hierarchy/BreadcrumbBuilder";
import { WBEModal } from "@/features/wbes/components/WBEModal";
import { CostElementManagement } from "@/pages/financials/CostElementManagement";
import { DeleteWBEModal } from "@/components/hierarchy/DeleteWBEModal";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";

export const WBEDetailPage = () => {
  const { projectId, wbeId } = useParams<{
    projectId: string;
    wbeId: string;
  }>();
  const navigate = useNavigate();

  // Fetch WBE details
  const { data: wbe, isLoading: wbeLoading } = useWBE(wbeId!);

  // Fetch breadcrumb
  const { data: breadcrumb, isLoading: breadcrumbLoading } =
    useWBEBreadcrumb(wbeId);

  // Fetch child WBEs
  const {
    data: childWbes,
    isLoading: childrenLoading,
    refetch: refetchChildren,
  } = useWBEs({
    projectId,
    parentWbeId: wbeId,
  });

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedWBE, setSelectedWBE] = useState<WBERead | null>(null);
  const [isCreatingChild, setIsCreatingChild] = useState(false);

  // Delete Modal State
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [wbeToDelete, setWbeToDelete] = useState<WBERead | null>(null);
  const [isDeletingCurrent, setIsDeletingCurrent] = useState(false);

  // History State
  const [historyOpen, setHistoryOpen] = useState(false);
  const { data: historyVersions, isLoading: historyLoading } = useWBEHistory(
    wbeId,
    historyOpen
  );

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
      setModalOpen(false);
    },
  });

  const { mutate: deleteWBE } = useDeleteWBE({
    onSuccess: () => refetchChildren(),
  });

  // Handlers
  const handleCreateChild = () => {
    setSelectedWBE(null);
    setIsCreatingChild(true);
    setModalOpen(true);
  };

  const handleEdit = (targetWbe: WBERead) => {
    setSelectedWBE(targetWbe);
    setIsCreatingChild(false);
    setModalOpen(true);
  };

  const handleEditCurrent = () => {
    if (wbe) {
      setSelectedWBE(wbe);
      setIsCreatingChild(false);
      setModalOpen(true);
    }
  };

  const handleDelete = (targetWbe: WBERead) => {
    setWbeToDelete(targetWbe);
    setIsDeletingCurrent(false);
    setDeleteModalOpen(true);
  };

  const handleDeleteCurrent = () => {
    if (wbe) {
      setWbeToDelete(wbe);
      setIsDeletingCurrent(true);
      setDeleteModalOpen(true);
    }
  };

  const handleRowClick = (childWbe: WBERead) => {
    navigate(`/projects/${projectId}/wbes/${childWbe.wbe_id}`);
  };

  if (!wbe && !wbeLoading) {
    return (
      <div style={{ padding: 24 }}>
        <h1>WBE Not Found</h1>
        <p>The requested Work Breakdown Element could not be found.</p>
        <Button onClick={() => navigate(`/projects/${projectId}`)}>
          Back to Project
        </Button>
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      {/* Breadcrumb Navigation */}
      <BreadcrumbBuilder breadcrumb={breadcrumb} loading={breadcrumbLoading} />

      {/* Page Title */}
      <h1 style={{ marginBottom: 16 }}>WBE Details</h1>

      {/* WBE Summary */}
      {wbe && (
        <WBESummaryCard
          wbe={wbe}
          projectId={projectId!}
          loading={wbeLoading}
          onEdit={handleEditCurrent}
          onDelete={handleDeleteCurrent}
          onViewHistory={() => setHistoryOpen(true)}
        />
      )}

      {/* Child WBEs Section */}
      <Card
        title="Child WBEs"
        style={{ marginBottom: 16 }}
        extra={
          <Can permission="wbe-create">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateChild}
            >
              Add Child WBE
            </Button>
          </Can>
        }
      >
        {childWbes && childWbes.length > 0 ? (
          <WBETable
            wbes={childWbes}
            loading={childrenLoading}
            onRowClick={handleRowClick}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        ) : (
          <div style={{ textAlign: "center", padding: 24, color: "#999" }}>
            {childrenLoading
              ? "Loading..."
              : "No child WBEs. Click 'Add Child WBE' to create one."}
          </div>
        )}
      </Card>

      {/* Cost Elements Section */}
      <Card title="Cost Elements" style={{ marginBottom: 16 }}>
        {wbeId && <CostElementManagement wbeId={wbeId} />}
      </Card>

      {deleteModalOpen && (
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

              if (isDeletingCurrent) {
                // Navigate back to parent
                if (wbeToDelete.parent_wbe_id) {
                  navigate(
                    `/projects/${projectId}/wbes/${wbeToDelete.parent_wbe_id}`
                  );
                } else {
                  navigate(`/projects/${projectId}`);
                }
              }
            }
          }}
        />
      )}

      {wbe && (
        <VersionHistoryDrawer
          open={historyOpen}
          onClose={() => setHistoryOpen(false)}
          entityName={`WBE: ${wbe.code} - ${wbe.name}`}
          isLoading={historyLoading}
          versions={(historyVersions || []).map((version: any, idx, arr) => {
            // Basic parsing of stringified range "[start, end)"
            let start = new Date().toISOString();
            if (version.valid_time && typeof version.valid_time === "string") {
              const clean = version.valid_time
                .replace("[", "")
                .replace(")", "")
                .split(",")[0];
              if (clean) start = clean.trim();
            } else if (Array.isArray(version.valid_time)) {
              start = version.valid_time[0];
            }

            return {
              id: `v${arr.length - idx}`,
              valid_from: start,
              transaction_time: new Date().toISOString(), // Placeholder if not parsed
              changed_by: version.created_by_name || "System",
              changes:
                idx === 0 ? { created: "initial" } : { updated: "changed" },
            };
          })}
        />
      )}

      {/* WBE Modal for Create/Edit */}
      <WBEModal
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          setIsCreatingChild(false);
        }}
        onOk={async (values) => {
          if (selectedWBE) {
            // Edit existing
            await updateWBE({
              id: selectedWBE.wbe_id,
              data: values as WBEUpdate,
            });
          } else if (isCreatingChild && wbe) {
            // Create child of current WBE
            await createWBE({
              ...values,
              project_id: projectId!,
              parent_wbe_id: wbe.wbe_id,
              level: (wbe.level || 1) + 1,
            } as WBECreate);
          }
        }}
        confirmLoading={false}
        initialValues={selectedWBE}
        projectId={projectId}
      />
    </div>
  );
};
