import React from "react";
import { useParams, useNavigate, Outlet } from "react-router-dom";
import { Button, Modal } from "antd";
import {
  EditOutlined,
  DeleteOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import {
  useCostElement,
  useCostElementBreadcrumb,
  useUpdateCostElement,
  useDeleteCostElement,
} from "@/features/cost-elements/api/useCostElements";
import { CostElementUpdate } from "@/api/generated";
import { CostElementModal } from "@/features/cost-elements/components/CostElementModal";
import { Can } from "@/components/auth/Can";
import { useEntityDetailActions } from "@/hooks/useEntityDetailActions";
import { PageNavigation } from "@/components/navigation";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { PageShell } from "@/components/layout/PageShell";
import { NotFoundState } from "@/components/layout/NotFoundState";

/**
 * CostElementLayout - Layout for EOC (Element of Cost) detail pages.
 *
 * EOCs are simple cost line items under a Work Package.
 * They have: type, amount, and a link to their parent work package.
 */
export const CostElementLayout: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: costElement, isLoading: costElementLoading } = useCostElement(
    id!,
  );
  const { data: breadcrumb, isLoading: breadcrumbLoading } = useCostElementBreadcrumb(id);

  const navItems = [
    { key: "overview", label: "Overview", path: `/cost-elements/${id}` },
    {
      key: "cost-registrations",
      label: "Cost Registrations",
      path: `/cost-elements/${id}/cost-registrations`,
    },
    {
      key: "cost-history",
      label: "Cost History",
      path: `/cost-elements/${id}/cost-history`,
    },
    {
      key: "documents",
      label: "Documents",
      path: `/cost-elements/${id}/documents`,
    },
  ];

  // Project root id from the breadcrumb (may be undefined while loading).
  const projectId = breadcrumb?.project?.project_id;

  const handleOpenChat = () => {
    const projectRider = projectId ? `&p=${projectId}` : "";
    navigate(`/chat?ctx=cost_element:${id}${projectRider}`, {
      state: { returnTo: `/cost-elements/${id}` },
    });
  };

  // Modal/drawer state
  const {
    editModalOpen,
    selectedEntity: selectedCE,
    deleteModalOpen,
    openEdit,
    closeEdit,
    openDelete,
    closeDelete,
  } = useEntityDetailActions<import("@/api/generated").CostElementRead>();

  // Mutations
  const { mutateAsync: updateCostElement } = useUpdateCostElement({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.costElements.all,
      });
      closeEdit();
    },
  });

  const { mutate: deleteCostElement } = useDeleteCostElement({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.costElements.all });
    },
  });

  const handleEditCurrent = () => {
    if (costElement) {
      openEdit(costElement);
    }
  };

  const handleDeleteCurrent = () => {
    if (costElement) {
      openDelete();
    }
  };

  if (!costElement && !costElementLoading) {
    return (
      <NotFoundState
        title="Cost Element Not Found"
        message="The requested cost element could not be found."
        onBack={() => navigate(-1)}
      />
    );
  }

  const displayTitle = costElement
    ? (() => {
        const typeName = costElement.cost_element_type_name || costElement.cost_element_type_code;
        return typeName || "Cost Element";
      })()
    : "Cost Element";

  return (
    <PageWrapper>
      <PageNavigation items={navItems} />

      <PageShell
        breadcrumb={
          breadcrumb
            ? [
                // Project item — dedup if WBE code matches project code
                ...(breadcrumb.wbs_element.code !== breadcrumb.project.code
                  ? [
                      {
                        label: breadcrumb.project.code,
                        to: `/projects/${breadcrumb.project.project_id}`,
                      },
                    ]
                  : []),
                {
                  label: breadcrumb.wbs_element.code,
                  to: `/projects/${breadcrumb.project.project_id}/wbs-elements/${breadcrumb.wbs_element.wbs_element_id}`,
                },
                {
                  label:
                    breadcrumb.cost_element.cost_element_type_code ||
                    breadcrumb.cost_element.cost_element_type_name ||
                    "Cost Element",
                },
              ]
            : []
        }
        breadcrumbLoading={breadcrumbLoading}
        title={displayTitle}
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
            <Can permission="cost-element-update">
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={handleEditCurrent}
              >
                Edit
              </Button>
            </Can>
            <Can permission="cost-element-delete">
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

      <Outlet context={{ costElement }} />

      {/* Edit modal */}
      {selectedCE && (
        <CostElementModal
          open={editModalOpen}
          onCancel={closeEdit}
          onOk={async (values) => {
            await updateCostElement({
              id: selectedCE.cost_element_id,
              data: values as CostElementUpdate,
            });
          }}
          confirmLoading={false}
          initialValues={selectedCE}
          currentBranch={"main"}
          workPackageId={selectedCE.work_package_id}
          workPackageName={selectedCE.work_package_name ?? undefined}
        />
      )}

      {/* Delete modal */}
      <Modal
        title="Delete Cost Element?"
        open={deleteModalOpen}
        onCancel={closeDelete}
        onOk={() => {
          if (costElement) {
            const compositeId = `${costElement.cost_element_id}:::main`;
            deleteCostElement(compositeId);
            closeDelete();
            navigate(-1);
          }
        }}
        okText="Delete"
        okType="danger"
      >
        <p>
          Are you sure you want to delete this cost element?
        </p>
      </Modal>
    </PageWrapper>
  );
};
