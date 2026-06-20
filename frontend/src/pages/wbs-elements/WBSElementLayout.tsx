import React from "react";
import { useParams, useNavigate, Outlet } from "react-router-dom";
import { useState } from "react";
import { Button } from "antd";
import { EditOutlined, DeleteOutlined, HistoryOutlined, RobotOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { useWBSElement, useWBSElementBreadcrumb, useUpdateWBSElement, useDeleteWBSElement } from "@/features/wbs-elements/api/useWBSElements";
import type { WBSElementRead, WBSElementUpdate } from "@/api/generated";
import { EntityBreadcrumb } from "@/components/common/EntityBreadcrumb";
import { WBSElementModal } from "@/features/wbs-elements/components/WBSElementModal";
import { DeleteWBSElementModal } from "@/components/hierarchy/DeleteWBSElementModal";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";
import { useEntityDetailActions } from "@/hooks/useEntityDetailActions";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { WbsElementsService } from "@/api/generated";
import { PageNavigation } from "@/components/navigation";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { PageHeader } from "@/components/layout/PageHeader";
import { NotFoundState } from "@/components/layout/NotFoundState";

interface BreadcrumbItem {
  code: string;
  name?: string;
  wbs_element_id: string;
}

interface BreadcrumbData {
  project: { code: string; name?: string; project_id: string };
  wbe_path: BreadcrumbItem[];
}

/**
 * WBSElementLayout
 *
 * Layout component for WBS Element detail pages. Provides shared navigation tabs,
 * a header with breadcrumb/title/action buttons, and modals for the current WBE.
 * Sub-pages render inside the Outlet.
 */
export const WBSElementLayout: React.FC = () => {
  const { projectId, wbsElementId } = useParams<{ projectId: string; wbsElementId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Data fetching
  const { data: wbe, isLoading: wbeLoading } = useWBSElement(wbsElementId!);
  const { data: _breadcrumb, isLoading: breadcrumbLoading } = useWBSElementBreadcrumb(wbsElementId);
  const breadcrumb = _breadcrumb as BreadcrumbData | undefined;

  // Navigation items
  const navItems = [
    { key: "overview", label: "Overview", path: `/projects/${projectId}/wbs-elements/${wbsElementId}` },
    { key: "evm-analysis", label: "EVM Analysis", path: `/projects/${projectId}/wbs-elements/${wbsElementId}/evm-analysis` },
    { key: "cost-history", label: "Cost History", path: `/projects/${projectId}/wbs-elements/${wbsElementId}/cost-history` },
    { key: "documents", label: "Documents", path: `/projects/${projectId}/wbs-elements/${wbsElementId}/documents` },
  ];

  const handleOpenChat = () => {
    navigate(`/chat?ctx=wbe:${wbsElementId}&p=${projectId}`, {
      state: { returnTo: `/projects/${projectId}/wbs-elements/${wbsElementId}` },
    });
  };

  // Modal/drawer state
  const {
    editModalOpen,
    selectedEntity: selectedWBE,
    deleteModalOpen,
    historyOpen,
    openEdit,
    closeEdit,
    openDelete,
    closeDelete,
    openHistory,
    closeHistory,
  } = useEntityDetailActions<WBSElementRead>();

  // Delete-specific state (WBE uses a dedicated delete modal)
  const [wbeToDelete, setWbeToDelete] = useState<WBSElementRead | null>(null);
  const [isDeletingCurrent, setIsDeletingCurrent] = useState(false);
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory({
    resource: "wbes",
    entityId: wbsElementId,
    fetchFn: (id) => WbsElementsService.getWbsElementHistory(id),
    enabled: historyOpen,
  });

  // Mutations
  const { mutateAsync: updateWBE } = useUpdateWBSElement({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.wbsElements.detail(wbsElementId!),
      });
      closeEdit();
    },
  });

  const { mutate: deleteWBE } = useDeleteWBSElement({
    onSuccess: () => {
      // Invalidate children queries so parent pages reflect removal
      queryClient.invalidateQueries({ queryKey: queryKeys.wbsElements.all });
    },
  });

  // Handlers
  const handleEditCurrent = () => {
    if (wbe) {
      openEdit(wbe);
    }
  };

  const handleDeleteCurrent = () => {
    if (wbe) {
      setWbeToDelete(wbe);
      setIsDeletingCurrent(true);
      openDelete();
    }
  };

  // Not found state
  if (!wbe && !wbeLoading) {
    return (
      <NotFoundState
        title="WBE Not Found"
        message="The requested Work Breakdown Element could not be found."
        onBack={() => navigate(`/projects/${projectId}`)}
      />
    );
  }

  return (
    <PageWrapper>
      <PageNavigation items={navItems} />

      {/* Shared header rendered on all sub-pages */}
      <EntityBreadcrumb
        loading={breadcrumbLoading}
        items={
          breadcrumb
            ? [
                // Project item — dedup if first WBE code matches project code
                ...(breadcrumb.wbe_path.length > 0 &&
                breadcrumb.wbe_path[0].code !== breadcrumb.project.code
                  ? [
                      {
                        label: breadcrumb.project.code,
                        to: `/projects/${breadcrumb.project.project_id}`,
                      },
                    ]
                  : []),
                // WBE path items — all linked except last
                ...breadcrumb.wbe_path.map((wbe: BreadcrumbItem, idx: number) => ({
                  label:
                    idx === breadcrumb.wbe_path.length - 1
                      ? `${wbe.code} ${wbe.name}`
                      : wbe.code,
                  to:
                    idx === breadcrumb.wbe_path.length - 1
                      ? undefined
                      : `/projects/${breadcrumb.project.project_id}/wbs-elements/${wbe.wbs_element_id}`,
                })),
              ]
            : []
        }
      />

      <PageHeader
        title="WBS Element Details"
        actions={
          <>
            <Can permission="ai-chat">
              <Button
                icon={<RobotOutlined />}
                onClick={handleOpenChat}
              >
                AI Chat
              </Button>
            </Can>
            <Can permission="wbs-element-update">
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={handleEditCurrent}
              >
                Edit
              </Button>
            </Can>
            <Can permission="wbs-element-read">
              <Button
                icon={<HistoryOutlined />}
                onClick={openHistory}
              >
                History
              </Button>
            </Can>
            <Can permission="wbs-element-delete">
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={handleDeleteCurrent}
              >
                Delete
              </Button>
            </Can>
          </>
        }
      />

      {/* Sub-page content */}
      <Outlet />

      {/* Shared modals for the current WBS Element */}

      {/* Edit modal */}
      {selectedWBE && (
        <WBSElementModal
          open={editModalOpen}
          onCancel={closeEdit}
          onOk={async (values) => {
            await updateWBE({
              id: selectedWBE.wbs_element_id,
              data: values as WBSElementUpdate,
            });
          }}
          confirmLoading={false}
          initialValues={selectedWBE}
          projectId={projectId}
          parentWbsElementId={selectedWBE.parent_wbs_element_id}
          parentName={selectedWBE.parent_name}
        />
      )}

      {/* Delete modal */}
      {deleteModalOpen && (
        <DeleteWBSElementModal
          wbe={wbeToDelete}
          open={deleteModalOpen}
          onCancel={() => {
            closeDelete();
            setWbeToDelete(null);
          }}
          onConfirm={() => {
            if (wbeToDelete) {
              deleteWBE(wbeToDelete.wbs_element_id);
              closeDelete();
              setWbeToDelete(null);

              if (isDeletingCurrent) {
                // Navigate back to parent WBS Element or project
                if (wbeToDelete.parent_wbs_element_id) {
                  navigate(`/projects/${projectId}/wbs-elements/${wbeToDelete.parent_wbs_element_id}`);
                } else {
                  navigate(`/projects/${projectId}`);
                }
              }
            }
          }}
        />
      )}

      {/* Version history drawer */}
      {wbe && (
        <VersionHistoryDrawer
          open={historyOpen}
          onClose={closeHistory}
          entityName={`WBE: ${wbe.code} - ${wbe.name}`}
          isLoading={historyLoading}
          versions={(historyVersions || []).map((version: Record<string, unknown>, idx: number, arr: unknown[]) => {
            const validTimeFormatted = version.valid_time_formatted as {
              lower: string | null;
              upper: string | null;
              lower_formatted: string;
              upper_formatted: string;
              is_currently_valid: boolean;
            } | undefined;
            const transactionTimeFormatted = version.transaction_time_formatted as {
              lower: string | null;
              upper: string | null;
              lower_formatted: string;
              upper_formatted: string;
              is_currently_valid: boolean;
            } | undefined;

            return {
              id: `v${arr.length - idx}`,
              valid_from: validTimeFormatted?.lower || "",
              valid_to: validTimeFormatted?.upper || null,
              transaction_time: transactionTimeFormatted?.lower || "",
              changed_by: (version.created_by_name as string) || "System",
              valid_time_formatted: validTimeFormatted,
              transaction_time_formatted: transactionTimeFormatted,
            };
          })}
        />
      )}
    </PageWrapper>
  );
};
