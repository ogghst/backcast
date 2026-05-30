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
import type { WorkPackageBreadcrumb } from "@/features/work-packages/api/useWorkPackages";
import { WorkPackageBreadcrumbBuilder } from "@/components/work-packages/WorkPackageBreadcrumbBuilder";
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
      <div style={{ padding: token.paddingXL }}>
        <Typography.Title level={3}>
          Work Package Not Found
        </Typography.Title>
        <p>The requested work package could not be found.</p>
        <Button onClick={() => { if (projectId) navigate(`/projects/${projectId}`); else navigate("/"); }}>Go Back</Button>
      </div>
    );
  }

  const displayTitle = workPackage
    ? `${workPackage.code} - ${workPackage.name}`
    : "Work Package";

  return (
    <div style={{ padding: isMobile ? token.paddingMD : token.paddingXL }}>
      <PageNavigation items={navItems} />

      <WorkPackageBreadcrumbBuilder breadcrumb={breadcrumb as WorkPackageBreadcrumb | undefined} loading={breadcrumbLoading} />

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
          {displayTitle}
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
