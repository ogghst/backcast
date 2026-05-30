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
  useCostElement,
  useUpdateCostElement,
  useDeleteCostElement,
} from "@/features/cost-elements/api/useCostElements";
import { CostElementUpdate } from "@/api/generated";
import { CostElementModal } from "@/features/cost-elements/components/CostElementModal";
import { Can } from "@/components/auth/Can";
import { useEntityDetailActions } from "@/hooks/useEntityDetailActions";
import { PageNavigation } from "@/components/navigation";

/**
 * CostElementLayout - Layout for EOC (Element of Cost) detail pages.
 *
 * EOCs are simple cost line items under a Work Package.
 * They have: type, amount, and a link to their parent work package.
 */
export const CostElementLayout: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const queryClient = useQueryClient();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const { data: costElement, isLoading: costElementLoading } = useCostElement(
    id!,
  );

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
    {
      key: "chat",
      label: "AI Chat",
      path: `/cost-elements/${id}/chat`,
    },
  ];

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
      <div style={{ padding: token.paddingXL }}>
        <Typography.Title level={3}>
          Cost Element Not Found
        </Typography.Title>
        <p>The requested cost element could not be found.</p>
        <Button onClick={() => navigate(-1)}>Go Back</Button>
      </div>
    );
  }

  const displayTitle = costElement
    ? (() => {
        const typeName = costElement.cost_element_type_name || costElement.cost_element_type_code;
        return typeName || "Cost Element";
      })()
    : "Cost Element";

  return (
    <div style={{ padding: isMobile ? token.paddingMD : token.paddingXL }}>
      <PageNavigation items={navItems} />

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
          <Can permission="cost-element-update">
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={handleEditCurrent}
            >
              {isMobile ? undefined : "Edit"}
            </Button>
          </Can>
          <Can permission="cost-element-delete">
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
    </div>
  );
};
