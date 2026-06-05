import React from "react";
import { useParams, useNavigate, Outlet } from "react-router-dom";
import { Button, Grid, Modal, Space, theme, Typography, Tag } from "antd";
import { EditOutlined, DeleteOutlined, HistoryOutlined } from "@ant-design/icons";
import { EntityBreadcrumb } from "@/components/common/EntityBreadcrumb";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import {
  useControlAccount,
  useUpdateControlAccount,
  useDeleteControlAccount,
} from "@/features/control-accounts/api/useControlAccounts";
import { useWBSElement } from "@/features/wbs-elements/api/useWBSElements";
import { useProject } from "@/features/projects/api/useProjects";
import type {
  ControlAccountRead,
  ControlAccountUpdate,
} from "@/api/generated";
import { ControlAccountModal } from "@/features/control-accounts/components/ControlAccountModal";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { PageHeader } from "@/components/layout/PageHeader";
import { NotFoundState } from "@/components/layout/NotFoundState";
import { useEntityDetailActions } from "@/hooks/useEntityDetailActions";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { ControlAccountsService } from "@/api/generated";
import { PageNavigation } from "@/components/navigation";
import { getBranchColor } from "@/utils/formatters";

/**
 * ControlAccountLayout
 *
 * Layout component for Control Account detail pages. Provides shared navigation tabs,
 * a header with breadcrumb/title/action buttons, and modals for the current CA.
 * Sub-pages render inside the Outlet.
 */
export const ControlAccountLayout: React.FC = () => {
  const { projectId, controlAccountId } = useParams<{
    projectId: string;
    controlAccountId: string;
  }>();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const queryClient = useQueryClient();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  // Data fetching
  const { data: ca, isLoading: caLoading } = useControlAccount(controlAccountId!);

  // Project and WBS element for breadcrumb context
  const { data: project } = useProject(projectId!, {
    requestHeaders: { "X-Silent-Error": "true" },
  });
  const { data: wbsElement } = useWBSElement(ca?.wbs_element_id || "");

  // Navigation items
  const navItems = [
    { key: "overview", label: "Overview", path: `/projects/${projectId}/control-accounts/${controlAccountId}` },
    { key: "evm-analysis", label: "EVM Analysis", path: `/projects/${projectId}/control-accounts/${controlAccountId}/evm-analysis` },
    { key: "cost-history", label: "Cost History", path: `/projects/${projectId}/control-accounts/${controlAccountId}/cost-history` },
    { key: "documents", label: "Documents", path: `/projects/${projectId}/control-accounts/${controlAccountId}/documents` },
    { key: "chat", label: "AI Chat", path: `/projects/${projectId}/control-accounts/${controlAccountId}/chat` },
  ];

  // Modal/drawer state
  const {
    editModalOpen,
    selectedEntity: selectedCA,
    deleteModalOpen,
    historyOpen,
    openEdit,
    closeEdit,
    openDelete,
    closeDelete,
    openHistory,
    closeHistory,
  } = useEntityDetailActions<ControlAccountRead>();

  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory({
    resource: "control-accounts",
    entityId: controlAccountId,
    fetchFn: (id) => ControlAccountsService.getControlAccountHistory(id),
    enabled: historyOpen,
  });

  // Mutations
  const { mutateAsync: updateCA } = useUpdateControlAccount({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.controlAccounts.detail(controlAccountId!, {}),
      });
      closeEdit();
    },
  });

  const { mutate: deleteCA } = useDeleteControlAccount({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.controlAccounts.all,
      });
    },
  });

  // Handlers
  const handleEditCurrent = () => {
    if (ca) {
      openEdit(ca);
    }
  };

  const handleDeleteCurrent = () => {
    if (ca) {
      openDelete();
    }
  };

  // Not found state
  if (!ca && !caLoading) {
    return (
      <NotFoundState
        title="Control Account Not Found"
        message="The requested control account could not be found."
        onBack={() => navigate(`/projects/${projectId}`)}
      />
    );
  }

  // Breadcrumb: Home / Projects / {ProjectCode} / {WBS Code} / {CA Code}
  const breadcrumbEntries = [
    ...(projectId
      ? [{ label: project?.code || projectId, to: `/projects/${projectId}` }]
      : []),
    ...(wbsElement
      ? [{ label: wbsElement.code, to: `/projects/${projectId}/wbs-elements/${wbsElement.wbs_element_id}` }]
      : []),
    ...(ca
      ? [{ label: ca.code || ca.name }]
      : []),
  ];

  return (
    <PageWrapper>
      <PageNavigation items={navItems} />

      <EntityBreadcrumb loading={caLoading || !wbsElement} items={breadcrumbEntries} />

      <PageHeader
        title={
          <Space align="center" size={token.marginSM}>
            <Typography.Title
              level={1}
              style={{
                margin: 0,
                fontSize: isMobile ? token.fontSizeXL : undefined,
              }}
            >
              {ca ? `${ca.code || ""} ${ca.name}`.trim() : "Control Account"}
            </Typography.Title>
            {ca && ca.branch && (
              <Tag color={getBranchColor(ca.branch)}>{ca.branch}</Tag>
            )}
          </Space>
        }
        actions={
          <>
            <Can permission="control-account-update">
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={handleEditCurrent}
              >
                {isMobile ? undefined : "Edit"}
              </Button>
            </Can>
            <Can permission="control-account-read">
              <Button
                icon={<HistoryOutlined />}
                onClick={openHistory}
              >
                {isMobile ? undefined : "History"}
              </Button>
            </Can>
            <Can permission="control-account-delete">
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={handleDeleteCurrent}
              >
                {isMobile ? undefined : "Delete"}
              </Button>
            </Can>
          </>
        }
      />

      {/* Sub-page content */}
      <Outlet context={{ ca }} />

      {/* Edit modal */}
      {selectedCA && (
        <ControlAccountModal
          open={editModalOpen}
          onCancel={closeEdit}
          onOk={async (values) => {
            await updateCA({
              id: selectedCA.control_account_id,
              data: values as ControlAccountUpdate,
            });
          }}
          confirmLoading={false}
          initialValues={selectedCA}
          projectId={projectId!}
        />
      )}

      {/* Delete modal */}
      <Modal
        title="Delete Control Account?"
        open={deleteModalOpen}
        onCancel={closeDelete}
        onOk={() => {
          if (ca) {
            deleteCA(ca.control_account_id);
            closeDelete();
            // Navigate back to parent WBS element or project
            if (ca.wbs_element_id) {
              navigate(`/projects/${projectId}/wbs-elements/${ca.wbs_element_id}`, {
                state: { scrollTo: "control-accounts" },
              });
            } else {
              navigate(`/projects/${projectId}`);
            }
          }
        }}
        okText="Delete"
        okType="danger"
      >
        <p>
          Are you sure you want to delete control account{" "}
          <strong>{ca?.code || ca?.name}</strong>?
        </p>
      </Modal>

      {/* Version history drawer */}
      {ca && (
        <VersionHistoryDrawer
          open={historyOpen}
          onClose={closeHistory}
          entityName={`CA: ${ca.code || ""} - ${ca.name}`}
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
