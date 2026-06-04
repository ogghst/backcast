import React from "react";
import { useParams, useNavigate, Outlet } from "react-router-dom";
import { Button, Grid, Space, theme, Typography, Flex, Modal } from "antd";
import {
  EditOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import {
  useWorkPackage,
  useWorkPackageBreadcrumb,
  useUpdateWorkPackage,
  useDeleteWorkPackage,
} from "@/features/work-packages/api/useWorkPackages";
import { EntityBreadcrumb } from "@/components/common/EntityBreadcrumb";
import { useControlAccount } from "@/features/control-accounts/api/useControlAccounts";
import { WorkPackageUpdate } from "@/api/generated";
import { WorkPackageModal } from "@/features/work-packages/components/WorkPackageModal";
import { Can } from "@/components/auth/Can";
import { useEntityDetailActions } from "@/hooks/useEntityDetailActions";
import { PageNavigation } from "@/components/navigation";

export const WorkPackageLayout: React.FC = () => {
  const { id, projectId } = useParams<{ id: string; projectId?: string }>();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const queryClient = useQueryClient();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

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
    {
      key: "chat",
      label: "AI Chat",
      path: `${basePath}/chat`,
    },
  ];

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
      <div style={{ padding: `${token.paddingXL}px 0` }}>
        <Typography.Title level={3}>
          Work Package Not Found
        </Typography.Title>
        <p>The requested work package could not be found.</p>
        <Button onClick={() => { if (projectId) navigate(`/projects/${projectId}`); else navigate("/"); }}>Go Back</Button>
      </div>
    );
  }

  return (
    <div style={{ padding: isMobile ? `${token.paddingMD}px 0` : `${token.paddingXL}px 0` }}>
      <PageNavigation items={navItems} />

      <EntityBreadcrumb
        loading={breadcrumbLoading}
        items={
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
                },
              ]
            : []
        }
      />

      <Flex
        justify="space-between"
        align={isMobile ? "flex-start" : "center"}
        vertical={isMobile}
        gap={isMobile ? token.marginSM : 0}
        style={{ marginBottom: token.paddingMD }}
      >
        <Typography.Title
          level={1}
          style={{
            margin: 0,
            fontSize: isMobile ? token.fontSizeXL : undefined,
          }}
        >
          Work Package
        </Typography.Title>
        <Space size={token.marginSM} wrap={isMobile}>
          <Can permission="work-package-update">
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={handleEditCurrent}
            >
              {isMobile ? undefined : "Edit"}
            </Button>
          </Can>
          <Can permission="work-package-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleDeleteCurrent}
            >
              {isMobile ? undefined : "Delete"}
            </Button>
          </Can>
        </Space>
      </Flex>

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
    </div>
  );
};
