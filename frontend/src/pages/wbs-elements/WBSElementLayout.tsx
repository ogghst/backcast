import React from "react";
import { useParams, useNavigate, Outlet, useLocation } from "react-router-dom";
import { useState } from "react";
import { Button } from "antd";
import { EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { useWBSElement, useWBSElementBreadcrumb, useUpdateWBSElement, useDeleteWBSElement } from "@/features/wbs-elements/api/useWBSElements";
import type { WBSElementRead, WBSElementUpdate } from "@/api/generated";
import { WBSElementModal } from "@/features/wbs-elements/components/WBSElementModal";
import { DeleteWBSElementModal } from "@/components/hierarchy/DeleteWBSElementModal";
import { Can } from "@/components/auth/Can";
import { useEntityDetailActions } from "@/hooks/useEntityDetailActions";
import { wbeNavItems } from "@/components/navigation/entityNavItems";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { PageShell } from "@/components/layout/PageShell";
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

  // Resolve the active section label from the shared nav builder (sidebar is
  // the single home for the tab strip; this only feeds the breadcrumb/title).
  const location = useLocation();
  const navItems = wbeNavItems(projectId!, wbsElementId!);
  const activeSection = navItems.find((i) => location.pathname === i.path)?.label ?? navItems[0].label;

  // Modal/drawer state
  const {
    editModalOpen,
    selectedEntity: selectedWBE,
    deleteModalOpen,
    openEdit,
    closeEdit,
    openDelete,
    closeDelete,
  } = useEntityDetailActions<WBSElementRead>();

  // Delete-specific state (WBE uses a dedicated delete modal)
  const [wbeToDelete, setWbeToDelete] = useState<WBSElementRead | null>(null);
  const [isDeletingCurrent, setIsDeletingCurrent] = useState(false);

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
      {/* Shared header rendered on all sub-pages */}
      <PageShell
        breadcrumb={
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
                // WBE path items — all linked
                ...breadcrumb.wbe_path.map((wbe: BreadcrumbItem, idx: number) => ({
                  label:
                    idx === breadcrumb.wbe_path.length - 1
                      ? `${wbe.code} ${wbe.name}`
                      : wbe.code,
                  to: `/projects/${breadcrumb.project.project_id}/wbs-elements/${wbe.wbs_element_id}`,
                })),
                // Active section — bold (last crumb)
                { label: activeSection },
              ]
            : []
        }
        breadcrumbLoading={breadcrumbLoading}
        title={activeSection}
        actions={
          <>
            <Can permission="wbs-element-update">
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={handleEditCurrent}
              >
                Edit
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
    </PageWrapper>
  );
};
