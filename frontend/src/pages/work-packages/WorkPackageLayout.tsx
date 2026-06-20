import React from "react";
import { useParams, useNavigate, Outlet, useLocation } from "react-router-dom";
import { Button, Modal } from "antd";
import {
  EditOutlined,
  DeleteOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import {
  useWorkPackage,
  useWorkPackageBreadcrumb,
  useUpdateWorkPackage,
  useDeleteWorkPackage,
} from "@/features/work-packages/api/useWorkPackages";
import { useControlAccount } from "@/features/control-accounts/api/useControlAccounts";
import { WorkPackageUpdate } from "@/api/generated";
import { WorkPackageModal } from "@/features/work-packages/components/WorkPackageModal";
import { Can } from "@/components/auth/Can";
import { useEntityDetailActions } from "@/hooks/useEntityDetailActions";
import { PageNavigation } from "@/components/navigation";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { PageShell } from "@/components/layout/PageShell";
import { NotFoundState } from "@/components/layout/NotFoundState";

export const WorkPackageLayout: React.FC = () => {
  const { id, projectId } = useParams<{ id: string; projectId?: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: workPackage, isLoading: workPackageLoading } = useWorkPackage(
    id!,
  );
  const { data: breadcrumb, isLoading: breadcrumbLoading } = useWorkPackageBreadcrumb(id);

  const basePath = projectId
    ? `/projects/${projectId}/work-packages/${id}`
    : `/work-packages/${id}`;

  const navItems = [
    { key: "overview", label: "Overview", path: basePath },
    {
      key: "cost-registrations",
      label: "Cost Registrations",
      path: `${basePath}/cost-registrations`,
    },
    {
      key: "cost-history",
      label: "Cost History",
      path: `${basePath}/cost-history`,
    },
    {
      key: "evm-analysis",
      label: "EVM Analysis",
      path: `${basePath}/evm-analysis`,
    },
    {
      key: "documents",
      label: "Documents",
      path: `${basePath}/documents`,
    },
  ];

  const location = useLocation();
  const activeSection = navItems.find((i) => location.pathname === i.path)?.label ?? navItems[0].label;

  const handleOpenChat = () => {
    const ctxParam = `work_package:${id}`;
    const projectRider = projectId ? `&p=${projectId}` : "";
    navigate(`/chat?ctx=${ctxParam}${projectRider}`, {
      state: { returnTo: basePath },
    });
  };

  // Modal/drawer state
  const {
    editModalOpen,
    selectedEntity: selectedWP,
    deleteModalOpen,
    openEdit,
    closeEdit,
    openDelete,
    closeDelete,
  } = useEntityDetailActions<import("@/api/generated").WorkPackageRead>();

  // Resolve wbs_element_id from the selected WP's control account for CA dropdown scoping
  const { data: controlAccount } = useControlAccount(
    selectedWP?.control_account_id ?? "",
  );

  // Mutations
  const { mutateAsync: updateWorkPackage } = useUpdateWorkPackage({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.all,
      });
      closeEdit();
    },
  });

  const { mutate: deleteWorkPackage } = useDeleteWorkPackage({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.workPackages.all });
      closeDelete();
      if (projectId) navigate(`/projects/${projectId}`); else navigate("/");
    },
  });

  const handleEditCurrent = () => {
    if (workPackage) {
      openEdit(workPackage);
    }
  };

  const handleDeleteCurrent = () => {
    if (workPackage) {
      openDelete();
    }
  };

  if (!workPackage && !workPackageLoading) {
    return (
      <NotFoundState
        title="Work Package Not Found"
        message="The requested work package could not be found."
        onBack={() => { if (projectId) navigate(`/projects/${projectId}`); else navigate("/"); }}
      />
    );
  }

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
                  label: `${breadcrumb.work_package.code} ${breadcrumb.work_package.name}`,
                  to: basePath,
                },
                // Active section — bold (last crumb)
                { label: activeSection },
              ]
            : []
        }
        breadcrumbLoading={breadcrumbLoading}
        title={activeSection}
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
            <Can permission="work-package-update">
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={handleEditCurrent}
              >
                Edit
              </Button>
            </Can>
            <Can permission="work-package-delete">
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

      <Outlet context={{ workPackage }} />

      {/* Edit modal */}
      {selectedWP && (
        <WorkPackageModal
          open={editModalOpen}
          onCancel={closeEdit}
          onOk={async (values) => {
            await updateWorkPackage({
              id: selectedWP.work_package_id,
              data: values as WorkPackageUpdate,
            });
          }}
          confirmLoading={false}
          initialValues={selectedWP}
          wbsElementId={controlAccount?.wbs_element_id}
        />
      )}

      {/* Delete modal */}
      <Modal
        title="Delete Work Package?"
        open={deleteModalOpen}
        onCancel={closeDelete}
        onOk={() => {
          if (workPackage) {
            deleteWorkPackage(workPackage.work_package_id);
          }
        }}
        okText="Delete"
        okType="danger"
      >
        <p>
          Are you sure you want to delete this work package?
        </p>
      </Modal>
    </PageWrapper>
  );
};
