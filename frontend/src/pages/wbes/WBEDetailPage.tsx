import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Button, Card, Grid, Tabs, Collapse, Space, theme, Typography, Flex } from "antd";
import { PlusOutlined, LineChartOutlined, EditOutlined, DeleteOutlined, HistoryOutlined, RobotOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";

import {
  useWBE,
  useWBEs,
  useWBEBreadcrumb,
  useCreateWBE,
  useUpdateWBE,
  useDeleteWBE,
} from "@/features/wbes/api/useWBEs";
import { WBECreate, WBERead, WBEUpdate } from "@/api/generated";
import { WBESummaryCard } from "@/components/hierarchy/WBESummaryCard";
import { WBECard } from "@/features/wbes/components/WBECard";
import { BreadcrumbBuilder } from "@/components/hierarchy/BreadcrumbBuilder";
import { WBEModal } from "@/features/wbes/components/WBEModal";
import { CostElementManagement } from "@/pages/financials/CostElementManagement";
import { DeleteWBEModal } from "@/components/hierarchy/DeleteWBEModal";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { WbEsService } from "@/api/generated";
import { EntityGrid } from "@/components/common/EntityGrid";

import {
  useEVMMetrics,
  useEVMTimeSeries,
} from "@/features/evm/api/useEVMMetrics";
import { EVMSummaryView } from "@/features/evm/components/EVMSummaryView";
import { EVMTimeSeriesChart } from "@/features/evm/components/EVMTimeSeriesChart";
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import { EVMTimeSeriesGranularity, EntityType } from "@/features/evm/types";
import { ChatInterface } from "@/features/ai/chat/components/ChatInterface";

export const WBEDetailPage = () => {
  const { projectId, wbeId } = useParams<{
    projectId: string;
    wbeId: string;
  }>();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const queryClient = useQueryClient();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  // Pagination State
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });

  const { data: wbe, isLoading: wbeLoading } = useWBE(wbeId!);

  // Fetch breadcrumb
  const { data: breadcrumb, isLoading: breadcrumbLoading } =
    useWBEBreadcrumb(wbeId);

  // Fetch child WBEs
  const {
    data,
    isLoading: childrenLoading,
    refetch: refetchChildren,
  } = useWBEs({
    projectId,
    parentWbeId: wbeId,
    pagination: { current: pagination.current, pageSize: pagination.pageSize },
  });
  const childWbes = data?.items || [];

  // EVM State & Queries
  const [evmGranularity, setEvmGranularity] =
    useState<EVMTimeSeriesGranularity>(EVMTimeSeriesGranularity.WEEK);
  const { data: evmMetrics } = useEVMMetrics(EntityType.WBE, wbeId!);
  const { data: timeSeries, isLoading: timeSeriesLoading } = useEVMTimeSeries(
    EntityType.WBE,
    wbeId!,
    evmGranularity,
  );

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedWBE, setSelectedWBE] = useState<WBERead | null>(null);
  const [isCreatingChild, setIsCreatingChild] = useState(false);
  const [isEVMModalOpen, setIsEVMModalOpen] = useState(false);

  // Delete Modal State
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [wbeToDelete, setWbeToDelete] = useState<WBERead | null>(null);
  const [isDeletingCurrent, setIsDeletingCurrent] = useState(false);

  // History State
  const [historyOpen, setHistoryOpen] = useState(false);
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "wbes",
      entityId: wbeId,
      fetchFn: (id) => WbEsService.getWbeHistory(id),
      enabled: historyOpen,
    },
  );

  // Mutations
  const { mutateAsync: createWBE } = useCreateWBE({
    onSuccess: () => {
      refetchChildren();
      setModalOpen(false);
      setIsCreatingChild(false);
    },
  });

  const { mutateAsync: updateWBE } = useUpdateWBE({
    onSuccess: () => {
      refetchChildren();
      // Invalidate the current WBE detail query to refresh the header/info cards
      queryClient.invalidateQueries({
        queryKey: queryKeys.wbes.detail(wbeId!),
      });
      setModalOpen(false);
    },
  });

  const { mutate: deleteWBE } = useDeleteWBE({
    onSuccess: () => refetchChildren(),
  });

  // Handlers
  const handleCreateChild = () => {
    setSelectedWBE(null);
    setIsCreatingChild(true);
    setModalOpen(true);
  };

  const handleEdit = (targetWbe: WBERead) => {
    setSelectedWBE(targetWbe);
    setIsCreatingChild(false);
    setModalOpen(true);
  };

  const handleEditCurrent = () => {
    if (wbe) {
      setSelectedWBE(wbe);
      setIsCreatingChild(false);
      setModalOpen(true);
    }
  };

  const handleDelete = (targetWbe: WBERead) => {
    setWbeToDelete(targetWbe);
    setIsDeletingCurrent(false);
    setDeleteModalOpen(true);
  };

  const handleDeleteCurrent = () => {
    if (wbe) {
      setWbeToDelete(wbe);
      setIsDeletingCurrent(true);
      setDeleteModalOpen(true);
    }
  };

  const handleRowClick = (childWbe: WBERead) => {
    navigate(`/projects/${projectId}/wbes/${childWbe.wbe_id}`);
  };

  if (!wbe && !wbeLoading) {
    return (
      <div style={{ padding: token.paddingXL }}>
        <h1>WBE Not Found</h1>
        <p>The requested Work Breakdown Element could not be found.</p>
        <Button onClick={() => navigate(`/projects/${projectId}`)}>
          Back to Project
        </Button>
      </div>
    );
  }

  const overviewTabContent = (
    <Space
      direction="vertical"
      size="middle"
      style={{ width: "100%" }}
    >
      {/* WBE Summary */}
      {wbe && (
        <WBESummaryCard
          wbe={wbe}
          loading={wbeLoading}
        />
      )}

      {/* Child WBEs Section */}
      <EntityGrid<WBERead>
        items={childWbes}
        total={data?.total || 0}
        loading={childrenLoading}
        renderCard={(childWbe) => (
          <WBECard
            wbe={childWbe}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onOpen={handleRowClick}
          />
        )}
        keyExtractor={(w) => w.wbe_id}
        title="Child WBEs"
        addContent={
          <Can permission="wbe-create">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateChild}
            >
              Add Child WBE
            </Button>
          </Can>
        }
        searchValue=""
        onSearch={() => {}}
        searchPlaceholder="Search child WBEs..."
        sortOptions={[
          { label: "Code", value: "code" },
          { label: "Name", value: "name" },
          { label: "Budget", value: "budget_allocation" },
        ]}
        sortField={undefined}
        sortOrder={undefined}
        onSortChange={() => {}}
        pagination={pagination}
        onPageChange={(page, pageSize) =>
          setPagination({ current: page, pageSize })
        }
        minCardWidth={280}
      />

      {/* Cost Elements Section */}
      <Card title="Cost Elements">
        {wbeId && <CostElementManagement wbeId={wbeId} wbeName={wbe?.name} />}
      </Card>
    </Space>
  );

  const evmTabContent = (
    <Space
      direction="vertical"
      size="large"
      style={{ width: "100%" }}
    >
      {evmMetrics && (
        <EVMSummaryView
          metrics={evmMetrics}
          onAdvanced={() => setIsEVMModalOpen(true)}
        />
      )}

      <Collapse
        defaultActiveKey={["historical-trends"]}
        bordered
        style={{ backgroundColor: "transparent" }}
        items={[
          {
            key: "historical-trends",
            label: (
              <Space>
                <LineChartOutlined />
                <span>Historical Trends</span>
              </Space>
            ),
            children: (
              <div
                style={{
                  backgroundColor: token.colorBgContainer,
                  padding: token.paddingMD,
                  borderRadius: token.borderRadiusLG,
                }}
              >
                <EVMTimeSeriesChart
                  timeSeries={timeSeries}
                  loading={timeSeriesLoading}
                  onGranularityChange={setEvmGranularity}
                  currentGranularity={evmGranularity}
                  headless={true}
                  height={400}
                />
              </div>
            ),
          },
        ]}
      />
    </Space>
  );

  return (
    <div style={{ padding: token.paddingXL }}>
      {/* Tabs - moved to top like project page */}
      <Tabs
        defaultActiveKey="overview"
        items={[
          {
            key: "overview",
            label: "Overview",
            children: (
              <>
                {/* Breadcrumb Navigation */}
                <BreadcrumbBuilder breadcrumb={breadcrumb} loading={breadcrumbLoading} />

                {/* Page Title with Action Buttons */}
                <Flex
                  justify="space-between"
                  align={isMobile ? "stretch" : "center"}
                  vertical={isMobile}
                  gap={isMobile ? token.marginSM : 0}
                  style={{ marginBottom: token.paddingMD }}
                >
                  <Typography.Title level={1} style={{ margin: 0 }}>
                    WBE Details
                  </Typography.Title>
                  <Space size={token.marginSM}>
                    <Can permission="wbe-update">
                      <Button
                        type="primary"
                        icon={<EditOutlined />}
                        onClick={handleEditCurrent}
                      >
                        Edit
                      </Button>
                    </Can>
                    <Can permission="wbe-read">
                      <Button
                        icon={<HistoryOutlined />}
                        onClick={() => setHistoryOpen(true)}
                      >
                        History
                      </Button>
                    </Can>
                    <Can permission="wbe-delete">
                      <Button
                        danger
                        icon={<DeleteOutlined />}
                        onClick={handleDeleteCurrent}
                      >
                        Delete
                      </Button>
                    </Can>
                  </Space>
                </Flex>

                {overviewTabContent}
              </>
            ),
          },
          {
            key: "evm",
            label: "EVM Analysis",
            children: (
              <>
                {/* Breadcrumb Navigation */}
                <BreadcrumbBuilder breadcrumb={breadcrumb} loading={breadcrumbLoading} />

                {/* Page Title with Action Buttons */}
                <Flex
                  justify="space-between"
                  align={isMobile ? "stretch" : "center"}
                  vertical={isMobile}
                  gap={isMobile ? token.marginSM : 0}
                  style={{ marginBottom: token.paddingMD }}
                >
                  <Typography.Title level={1} style={{ margin: 0 }}>
                    WBE Details
                  </Typography.Title>
                  <Space size={token.marginSM}>
                    <Can permission="wbe-update">
                      <Button
                        type="primary"
                        icon={<EditOutlined />}
                        onClick={handleEditCurrent}
                      >
                        Edit
                      </Button>
                    </Can>
                    <Can permission="wbe-read">
                      <Button
                        icon={<HistoryOutlined />}
                        onClick={() => setHistoryOpen(true)}
                      >
                        History
                      </Button>
                    </Can>
                    <Can permission="wbe-delete">
                      <Button
                        danger
                        icon={<DeleteOutlined />}
                        onClick={handleDeleteCurrent}
                      >
                        Delete
                      </Button>
                    </Can>
                  </Space>
                </Flex>

                {evmTabContent}
              </>
            ),
          },
          {
            key: "chat",
            label: (
              <Space>
                <RobotOutlined />
                <span>AI Chat</span>
              </Space>
            ),
            children: (
              <>
                {/* Breadcrumb Navigation */}
                <BreadcrumbBuilder breadcrumb={breadcrumb} loading={breadcrumbLoading} />

                {/* Chat interface with WBE-specific context */}
                <ChatInterface
                  contextOverride={{
                    type: "wbe",
                    id: wbe?.wbe_id,
                    project_id: wbe?.project_id,
                    name: wbe?.name,
                  }}
                />
              </>
            ),
          },
        ]}
      />

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
                // Navigate back to parent
                if (wbeToDelete.parent_wbe_id) {
                  navigate(
                    `/projects/${projectId}/wbes/${wbeToDelete.parent_wbe_id}`,
                  );
                } else {
                  navigate(`/projects/${projectId}`);
                }
              }
            }
          }}
        />
      )}

      {wbe && (
        <VersionHistoryDrawer
          open={historyOpen}
          onClose={() => setHistoryOpen(false)}
          entityName={`WBE: ${wbe.code} - ${wbe.name}`}
          isLoading={historyLoading}
          versions={(historyVersions || []).map((version, idx, arr) => {
            // Use backend-formatted temporal data (computed fields)
            const validTimeFormatted = version.valid_time_formatted;
            const transactionTimeFormatted = version.transaction_time_formatted;

            return {
              id: `v${arr.length - idx}`,
              // Pass the formatted temporal data directly to VersionHistoryDrawer
              valid_from: validTimeFormatted?.lower || "",
              valid_to: validTimeFormatted?.upper || null,
              transaction_time: transactionTimeFormatted?.lower || "",
              changed_by: version.created_by_name || "System",
              // Also pass the formatted objects for the drawer to use
              valid_time_formatted: validTimeFormatted,
              transaction_time_formatted: transactionTimeFormatted,
            };
          })}
        />
      )}

      {/* WBE Modal for Create/Edit */}
      <WBEModal
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          setIsCreatingChild(false);
        }}
        onOk={async (values) => {
          if (selectedWBE) {
            // Edit existing
            await updateWBE({
              id: selectedWBE.wbe_id,
              data: values as WBEUpdate,
            });
          } else if (isCreatingChild && wbe) {
            // Create child of current WBE - context inherited from props/effect
            await createWBE({
              ...values,
              project_id: projectId!,
              level: (wbe.level || 1) + 1,
            } as WBECreate);
          }
        }}
        confirmLoading={false}
        initialValues={selectedWBE}
        projectId={projectId}
        parentWbeId={isCreatingChild ? wbe?.wbe_id : selectedWBE?.parent_wbe_id}
        parentName={isCreatingChild ? wbe?.name : selectedWBE?.parent_name}
      />

      <EVMAnalyzerModal
        open={isEVMModalOpen}
        onClose={() => setIsEVMModalOpen(false)}
        evmMetrics={evmMetrics}
        timeSeries={timeSeries}
        loading={timeSeriesLoading}
        onGranularityChange={setEvmGranularity}
      />
    </div>
  );
};
