import React from "react";
import { useParams, useNavigate, Outlet } from "react-router-dom";
import { useEffect } from "react";
import { Button, Grid, Space, theme, Typography, Flex, Modal } from "antd";
import {
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import {
  useCostElement,
  useCostElementBreadcrumb,
  useUpdateCostElement,
  useDeleteCostElement,
} from "@/features/cost-elements/api/useCostElements";
import { CostElementRead, CostElementUpdate } from "@/api/generated";
import {
  CostElementBreadcrumbBuilder,
  type CostElementBreadcrumb,
} from "@/components/cost-elements/CostElementBreadcrumbBuilder";
import { CostElementModal } from "@/features/cost-elements/components/CostElementModal";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";
import { useEntityDetailActions } from "@/hooks/useEntityDetailActions";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { CostElementsService } from "@/api/generated";
import { PageNavigation } from "@/components/navigation";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";

export const CostElementLayout: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const queryClient = useQueryClient();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const setCurrentProject = useTimeMachineStore((s) => s.setCurrentProject);

  const { data: breadcrumb, isLoading: breadcrumbLoading } =
    useCostElementBreadcrumb(id!) as {
      data: CostElementBreadcrumb | undefined;
      isLoading: boolean;
    };

  const { data: costElement, isLoading: costElementLoading } = useCostElement(
    id!,
  );

  useEffect(() => {
    if (breadcrumb?.project?.project_id) {
      setCurrentProject(breadcrumb.project.project_id);
    }
    return () => {
      setCurrentProject(null);
    };
  }, [breadcrumb?.project?.project_id, setCurrentProject]);

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
      key: "evm-analysis",
      label: "EVM Analysis",
      path: `/cost-elements/${id}/evm-analysis`,
    },
    {
      key: "quality-events",
      label: "Quality Events",
      path: `/cost-elements/${id}/quality-events`,
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
    historyOpen,
    openEdit,
    closeEdit,
    openDelete,
    closeDelete,
    openHistory,
    closeHistory,
  } = useEntityDetailActions<CostElementRead>();
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "cost-elements",
      entityId: id,
      fetchFn: (ceId) => CostElementsService.getHistory(ceId),
      enabled: historyOpen,
    },
  );

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

  const isLoading = breadcrumbLoading || costElementLoading;

  if (!costElement && !isLoading) {
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

  return (
    <div style={{ padding: isMobile ? token.paddingMD : token.paddingXL }}>
      <PageNavigation items={navItems} />

      <CostElementBreadcrumbBuilder
        breadcrumb={breadcrumb}
        loading={breadcrumbLoading}
        isMobile={isMobile}
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
          Cost Element Details
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
          <Can permission="cost-element-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={openHistory}
            >
              {isMobile ? undefined : "History"}
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
          currentBranch={selectedCE.branch || "main"}
          wbeId={selectedCE.wbe_id ?? undefined}
          wbeName={selectedCE.wbe_name ?? undefined}
        />
      )}

      {/* Delete modal */}
      <Modal
        title="Delete Cost Element?"
        open={deleteModalOpen}
        onCancel={closeDelete}
        onOk={() => {
          if (costElement) {
            const compositeId = `${costElement.cost_element_id}:::${costElement.branch || "main"}`;
            deleteCostElement(compositeId);
            closeDelete();
            if (breadcrumb?.wbe?.wbe_id) {
              navigate(
                `/projects/${breadcrumb.project.project_id}/wbes/${breadcrumb.wbe.wbe_id}`,
              );
            } else {
              navigate(-1);
            }
          }
        }}
        okText="Delete"
        okType="danger"
      >
        <p>
          Are you sure you want to delete cost element{" "}
          <strong>{costElement?.code}</strong> &ldquo;{costElement?.name}
          &rdquo;?
        </p>
      </Modal>

      {/* Version history drawer */}
      {costElement && (
        <VersionHistoryDrawer
          open={historyOpen}
          onClose={closeHistory}
          entityName={`Cost Element: ${costElement.code} - ${costElement.name}`}
          isLoading={historyLoading}
          versions={(historyVersions || []).map((version, idx, arr) => {
            const validTimeFormatted = version.valid_time_formatted as {
              lower: string | null;
              upper: string | null;
              lower_formatted: string;
              upper_formatted: string;
              is_currently_valid: boolean;
            } | undefined;
            const transactionTimeFormatted =
              version.transaction_time_formatted as {
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
              changed_by: version.created_by_name || "System",
              valid_time_formatted: validTimeFormatted,
              transaction_time_formatted: transactionTimeFormatted,
            };
          })}
        />
      )}
    </div>
  );
};
