import React from "react";
import { useParams, useNavigate, Outlet } from "react-router-dom";
import { useState } from "react";
import { Button, Grid, Space, theme, Typography, Flex } from "antd";
import { EditOutlined, DeleteOutlined, HistoryOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { useWBE, useWBEBreadcrumb, useUpdateWBE, useDeleteWBE } from "@/features/wbes/api/useWBEs";
import { WBERead, WBEUpdate } from "@/api/generated";
import { BreadcrumbBuilder } from "@/components/hierarchy/BreadcrumbBuilder";
import { WBEModal } from "@/features/wbes/components/WBEModal";
import { DeleteWBEModal } from "@/components/hierarchy/DeleteWBEModal";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { WbEsService } from "@/api/generated";
import { PageNavigation } from "@/components/navigation";

/**
 * WBELayout
 *
 * Layout component for WBE detail pages. Provides shared navigation tabs,
 * a header with breadcrumb/title/action buttons, and modals for the current WBE.
 * Sub-pages render inside the Outlet.
 */
export const WBELayout: React.FC = () => {
  const { projectId, wbeId } = useParams<{ projectId: string; wbeId: string }>();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const queryClient = useQueryClient();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  // Data fetching
  const { data: wbe, isLoading: wbeLoading } = useWBE(wbeId!);
  const { data: breadcrumb, isLoading: breadcrumbLoading } = useWBEBreadcrumb(wbeId);

  // Navigation items
  const navItems = [
    { key: "overview", label: "Overview", path: `/projects/${projectId}/wbes/${wbeId}` },
    { key: "evm-analysis", label: "EVM Analysis", path: `/projects/${projectId}/wbes/${wbeId}/evm-analysis` },
    { key: "cost-history", label: "Cost History", path: `/projects/${projectId}/wbes/${wbeId}/cost-history` },
    { key: "chat", label: "AI Chat", path: `/projects/${projectId}/wbes/${wbeId}/chat` },
  ];

  // Edit modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedWBE, setSelectedWBE] = useState<WBERead | null>(null);

  // Delete modal state
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [wbeToDelete, setWbeToDelete] = useState<WBERead | null>(null);
  const [isDeletingCurrent, setIsDeletingCurrent] = useState(false);

  // History state
  const [historyOpen, setHistoryOpen] = useState(false);
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory({
    resource: "wbes",
    entityId: wbeId,
    fetchFn: (id) => WbEsService.getWbeHistory(id),
    enabled: historyOpen,
  });

  // Mutations
  const { mutateAsync: updateWBE } = useUpdateWBE({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.wbes.detail(wbeId!),
      });
      setModalOpen(false);
    },
  });

  const { mutate: deleteWBE } = useDeleteWBE({
    onSuccess: () => {
      // Invalidate children queries so parent pages reflect removal
      queryClient.invalidateQueries({ queryKey: queryKeys.wbes.all });
    },
  });

  // Handlers
  const handleEditCurrent = () => {
    if (wbe) {
      setSelectedWBE(wbe);
      setModalOpen(true);
    }
  };

  const handleDeleteCurrent = () => {
    if (wbe) {
      setWbeToDelete(wbe);
      setIsDeletingCurrent(true);
      setDeleteModalOpen(true);
    }
  };

  // Not found state
  if (!wbe && !wbeLoading) {
    return (
      <div style={{ padding: token.paddingXL }}>
        <Typography.Title level={3}>WBE Not Found</Typography.Title>
        <p>The requested Work Breakdown Element could not be found.</p>
        <Button onClick={() => navigate(`/projects/${projectId}`)}>
          Back to Project
        </Button>
      </div>
    );
  }

  return (
    <div style={{ padding: isMobile ? token.paddingMD : token.paddingXL }}>
      <PageNavigation items={navItems} />

      {/* Shared header rendered on all sub-pages */}
      <BreadcrumbBuilder breadcrumb={breadcrumb} loading={breadcrumbLoading} />

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
          WBE Details
        </Typography.Title>
        <Space size={token.marginSM} wrap={isMobile}>
          <Can permission="wbe-update">
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={handleEditCurrent}
            >
              {isMobile ? undefined : "Edit"}
            </Button>
          </Can>
          <Can permission="wbe-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => setHistoryOpen(true)}
            >
              {isMobile ? undefined : "History"}
            </Button>
          </Can>
          <Can permission="wbe-delete">
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

      {/* Sub-page content */}
      <Outlet />

      {/* Shared modals for the current WBE */}

      {/* Edit modal */}
      {selectedWBE && (
        <WBEModal
          open={modalOpen}
          onCancel={() => setModalOpen(false)}
          onOk={async (values) => {
            await updateWBE({
              id: selectedWBE.wbe_id,
              data: values as WBEUpdate,
            });
          }}
          confirmLoading={false}
          initialValues={selectedWBE}
          projectId={projectId}
          parentWbeId={selectedWBE.parent_wbe_id}
          parentName={selectedWBE.parent_name}
        />
      )}

      {/* Delete modal */}
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
                // Navigate back to parent WBE or project
                if (wbeToDelete.parent_wbe_id) {
                  navigate(`/projects/${projectId}/wbes/${wbeToDelete.parent_wbe_id}`);
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
          onClose={() => setHistoryOpen(false)}
          entityName={`WBE: ${wbe.code} - ${wbe.name}`}
          isLoading={historyLoading}
          versions={(historyVersions || []).map((version, idx, arr) => {
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
