import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useState, useMemo, useEffect, useRef } from "react";
import { App, Button, Card, Space, Grid, Table, Tag, Empty, Spin, theme } from "antd";
import { EditOutlined, DeleteOutlined, PlusOutlined, HistoryOutlined } from "@ant-design/icons";
import { useQueries, useQueryClient } from "@tanstack/react-query";
import {
  useWBSElement,
  useWBSElements,
  useCreateWBSElement,
} from "@/features/wbs-elements/api/useWBSElements";
import { useControlAccounts, useCreateControlAccount, useUpdateControlAccount, useDeleteControlAccount } from "@/features/control-accounts/api/useControlAccounts";
import { ControlAccountModal } from "@/features/control-accounts/components/ControlAccountModal";
import {
  useCreateWorkPackage,
} from "@/features/work-packages/api/useWorkPackages";
import { useProject } from "@/features/projects/api/useProjects";
import { useWBEBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { WBSElementCreate, WBSElementRead, WorkPackageRead, WorkPackageCreate, ControlAccountCreate, ControlAccountUpdate, ControlAccountRead } from "@/api/generated";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";
import { WBSElementHeaderCard } from "@/components/WBSElements/WBSElementHeaderCard";
import { EntityMetadataCard } from "@/components/common/EntityMetadataCard";
import { WBSElementTable } from "@/components/hierarchy/WBSElementTable";
import { WBSElementModal } from "@/features/wbs-elements/components/WBSElementModal";
import { WorkPackageModal } from "@/features/work-packages/components/WorkPackageModal";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { WbsElementsService } from "@/api/generated";
import { Can } from "@/components/auth/Can";
import { ViewModeToggle } from "@/components/common/ViewModeToggle";
import { useViewMode } from "@/hooks/useViewMode";
import { ControlAccountCard } from "@/features/control-accounts/components/ControlAccountCard";
import { WorkPackageCard } from "@/features/work-packages/components/WorkPackageCard";
import { formatCurrency } from "@/utils/formatters";
import { PageContent } from "@/components/layout/PageContent";

/** Status color map matching WorkPackageCard */
const WP_STATUS_COLOR_MAP: Record<string, string> = {
  open: "blue",
  in_progress: "orange",
  closed: "green",
};

/**
 * WBSElementOverview - Overview sub-page for WBS Element detail.
 *
 * Displays the WBS Element header with cost visualization, child WBEs table,
 * cost element management, and collapsible WBS Element info card.
 * Matches the ProjectOverview layout pattern.
 */
export const WBSElementOverview = () => {
  const { projectId, wbsElementId } = useParams<{
    projectId: string;
    wbsElementId: string;
  }>();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const { token } = theme.useToken();
  const { viewMode, resolvedMode, cycleViewMode } = useViewMode("wbes", isMobile);
  const { viewMode: caViewMode, resolvedMode: caResolvedMode, cycleViewMode: caCycleViewMode } = useViewMode("control-accounts", isMobile);
  const { viewMode: wpViewMode, resolvedMode: wpResolvedMode, cycleViewMode: wpCycleViewMode } = useViewMode("work-packages", isMobile);

  // WBS Element data (TanStack Query cache hit — layout already fetches)
  const { data: wbe, isLoading: wbeLoading } = useWBSElement(wbsElementId!);

  // Project data for control_date
  const { data: project } = useProject(projectId!);
  const controlDate = (project as Record<string, unknown>)?.control_date as string | null | undefined;

  // WBS Element budget status (actual costs vs budget)
  const { data: budgetStatus } = useWBEBudgetStatus(wbsElementId!);

  // Child WBEs
  const {
    data,
    isLoading: childrenLoading,
    refetch: refetchChildren,
  } = useWBSElements({
    projectId,
    parentWbsElementId: wbsElementId,
  });
  const childWbes = data?.items || [];

  // Create child WBS Element modal state
  const [modalOpen, setModalOpen] = useState(false);

  // Version history state
  const [historyOpen, setHistoryOpen] = useState(false);
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory({
    resource: "wbes",
    entityId: wbsElementId,
    fetchFn: (id) => WbsElementsService.getWbsElementHistory(id),
    enabled: historyOpen,
  });

  // Mutations
  const { mutateAsync: createWBE, isPending: isCreatingWBE } = useCreateWBSElement({
    onSuccess: () => {
      refetchChildren();
      setModalOpen(false);
    },
  });

  const handleCreateChild = () => {
    setModalOpen(true);
  };

  // Control Accounts for this WBS Element
  const { data: caData } = useControlAccounts({ wbs_element_id: wbsElementId });
  const controlAccounts = useMemo(() => caData?.items || [], [caData?.items]);

  // Work Packages: one query per control account, combined with useQueries
  const wpQueries = useQueries({
    queries: controlAccounts.map((ca) => ({
      queryKey: queryKeys.workPackages.list(ca.control_account_id, {}),
      queryFn: async (): Promise<PaginatedResponse<WorkPackageRead>> => {
        const result = await __request(OpenAPI, {
          method: "GET",
          url: "/api/v1/work-packages",
          query: { control_account_id: ca.control_account_id },
          errors: { 422: "Validation Error" },
        });
        if (Array.isArray(result)) {
          return { items: result, total: result.length, page: 1, per_page: result.length };
        }
        return result as unknown as PaginatedResponse<WorkPackageRead>;
      },
    })),
  });

  // Flatten all work packages with their control account name
  const workPackages: (WorkPackageRead & { control_account_name_resolved: string })[] = [];
  controlAccounts.forEach((ca, idx) => {
    const query = wpQueries[idx];
    if (query.data?.items) {
      query.data.items.forEach((wp) => {
        workPackages.push({ ...wp, control_account_name_resolved: wp.control_account_name || ca.name });
      });
    }
  });

  const wpLoading = wpQueries.some((q) => q.isLoading);

  // Create Work Package modal state
  const [wpModalOpen, setWpModalOpen] = useState(false);
  const { mutateAsync: createWP, isPending: isCreatingWP } = useCreateWorkPackage({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.workPackages.all });
      setWpModalOpen(false);
    },
  });

  // Create Control Account modal state
  const [caModalOpen, setCaModalOpen] = useState(false);
  const { mutateAsync: createCA, isPending: isCreatingCA } = useCreateControlAccount({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.controlAccounts.all });
      setCaModalOpen(false);
    },
  });

  // Edit Control Account state
  const [caEditing, setCaEditing] = useState<ControlAccountRead | null>(null);
  const [caEditModalOpen, setCaEditModalOpen] = useState(false);
  const { mutateAsync: updateCA, isPending: isUpdatingCA } = useUpdateControlAccount({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.controlAccounts.all });
      setCaEditModalOpen(false);
      setCaEditing(null);
    },
  });

  // Delete Control Account
  const { mutateAsync: deleteCA } = useDeleteControlAccount();
  const { modal } = App.useApp();

  const handleDeleteCA = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this Control Account?",
      content: "This will soft delete the control account. Work packages under it will be preserved.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteCA(id),
    });
  };

  const handleRowClick = (childWbe: WBSElementRead) => {
    navigate(`/projects/${projectId}/wbs-elements/${childWbe.wbs_element_id}`);
  };

  // Scroll to CA section when navigated from tree with state.scrollTo
  const caSectionRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (location.state?.scrollTo === "control-accounts" && caSectionRef.current) {
      caSectionRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [location.state]);

  return (
    <PageContent>
      {/* WBS Element Header with cost visualization */}
        {wbe && (
          <WBSElementHeaderCard
            wbsElement={wbe}
            loading={wbeLoading}
            actualCosts={(budgetStatus as Record<string, unknown> | undefined)?.total_spend as number | undefined}
            currency={project?.currency}
            controlDate={controlDate || undefined}
            extraContent={
              wbsElementId ? (
                <CostHistoryChart
                  entityType="wbs_element"
                  entityId={wbsElementId}
                  headless
                  controlDate={controlDate || undefined}
                  projectId={projectId}
                />
              ) : undefined
            }
          />
        )}

        {/* Child WBEs Section */}
        <Card
          title="Child WBS Elements"
          extra={
            <Space>
              <ViewModeToggle viewMode={viewMode} onCycleViewMode={cycleViewMode} />
              <Can permission="wbs-element-create">
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateChild}>
                  {isMobile ? undefined : "Add Child WBS Element"}
                </Button>
              </Can>
            </Space>
          }
        >
          <WBSElementTable
            wbes={childWbes}
            loading={childrenLoading}
            onRowClick={handleRowClick}
            variant={resolvedMode}
          />
        </Card>

        {/* Cost Elements are now managed under Work Packages */}

        {/* Control Accounts Section */}
        <Card
          ref={caSectionRef}
          title="Control Accounts"
          extra={
            <Space>
              <ViewModeToggle viewMode={caViewMode} onCycleViewMode={caCycleViewMode} />
              <Can permission="control-account-create">
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setCaModalOpen(true)}>
                  {isMobile ? undefined : "Add Control Account"}
                </Button>
              </Can>
            </Space>
          }
        >
          {(() => {
            const useCaCard = caResolvedMode === "card";
            if (useCaCard) {
              if (!caData) return <div style={{ display: "flex", justifyContent: "center", padding: token.paddingXL }}><Spin /></div>;
              if (controlAccounts.length === 0) return <Empty description="No control accounts" />;
              return (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: token.marginMD }}>
                  {controlAccounts.map((ca) => (
                    <ControlAccountCard
                      key={ca.control_account_id}
                      controlAccount={ca}
                    />
                  ))}
                </div>
              );
            }
            return (
              <Table
                dataSource={controlAccounts}
                rowKey="control_account_id"
                loading={!caData}
                pagination={false}
                columns={[
                  { title: "Code", dataIndex: "code", key: "code", width: 150 },
                  { title: "Name", dataIndex: "name", key: "name" },
                  { title: "Organizational Unit", dataIndex: "organizational_unit_name", key: "ou", responsive: ["lg"] },
                  {
                    title: "Actions",
                    key: "actions",
                    width: isMobile ? 80 : 120,
                    render: (_, record: ControlAccountRead) => (
                      <Space>
                        <Can permission="control-account-update">
                          <Button
                            icon={<EditOutlined />}
                            onClick={() => {
                              setCaEditing(record);
                              setCaEditModalOpen(true);
                            }}
                            title="Edit"
                          />
                        </Can>
                        <Can permission="control-account-delete">
                          <Button
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => handleDeleteCA(record.control_account_id)}
                            title="Delete"
                          />
                        </Can>
                      </Space>
                    ),
                  },
                ]}
              />
            );
          })()}
        </Card>

        {/* Work Packages Section */}
        <Card
          title="Work Packages"
          extra={
            <Space>
              <ViewModeToggle viewMode={wpViewMode} onCycleViewMode={wpCycleViewMode} />
              <Can permission="work-package-create">
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setWpModalOpen(true)}>
                  {isMobile ? undefined : "Add Work Package"}
                </Button>
              </Can>
            </Space>
          }
        >
          {(() => {
            const useWpCard = wpResolvedMode === "card";
            if (useWpCard) {
              if (wpLoading) return <div style={{ display: "flex", justifyContent: "center", padding: token.paddingXL }}><Spin /></div>;
              if (workPackages.length === 0) return <Empty description="No work packages" />;
              return (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: token.marginMD }}>
                  {workPackages.map((wp) => (
                    <WorkPackageCard
                      key={wp.work_package_id}
                      workPackage={wp}
                      onClick={() => navigate(`/projects/${projectId}/work-packages/${wp.work_package_id}`)}
                    />
                  ))}
                </div>
              );
            }
            return (
              <Table
                dataSource={workPackages}
                rowKey="work_package_id"
                loading={wpLoading}
                pagination={{
                  defaultPageSize: 10,
                  showSizeChanger: true,
                  pageSizeOptions: ["10", "20", "50", "100"],
                  showTotal: (total) => `Total ${total} items`,
                  position: ["bottomRight"],
                }}
                onRow={(record) => ({
                  onClick: () => navigate(`/projects/${projectId}/work-packages/${record.work_package_id}`),
                  style: { cursor: "pointer" },
                })}
                columns={[
                  {
                    title: "Code",
                    dataIndex: "code",
                    key: "code",
                    width: 120,
                    sorter: (a, b) => a.code.localeCompare(b.code, undefined, { numeric: true }),
                  },
                  {
                    title: "Name",
                    dataIndex: "name",
                    key: "name",
                    sorter: (a, b) => a.name.localeCompare(b.name),
                  },
                  {
                    title: "Status",
                    dataIndex: "status",
                    key: "status",
                    width: 130,
                    render: (status: string) => (
                      <Tag color={WP_STATUS_COLOR_MAP[status || "open"] || "default"}>
                        {status || "open"}
                      </Tag>
                    ),
                  },
                  {
                    title: "Budget",
                    dataIndex: "budget_amount",
                    key: "budget_amount",
                    width: 140,
                    align: "right",
                    render: (val: string) => formatCurrency(val),
                    sorter: (a, b) => Number(a.budget_amount || 0) - Number(b.budget_amount || 0),
                  },
                  {
                    title: "Control Account",
                    dataIndex: "control_account_name_resolved",
                    key: "control_account_name_resolved",
                    width: 180,
                    responsive: ["lg"],
                  },
                ]}
              />
            );
          })()}
        </Card>

        {/* WBS Element metadata footer — standardized across entity pages */}
        {wbe && (
          <EntityMetadataCard
            entityId={wbe.wbs_element_id}
            entityIdLabel="WBS Element ID"
            parentId={wbe.parent_wbs_element_id}
            parentLabel="Parent WBS"
            parentValue={wbe.parent_name || "Project Root"}
            createdAt={wbe.created_at}
            updatedAt={wbe.updated_at}
            createdBy={wbe.created_by_name}
            validTime={wbe.valid_time_formatted}
            cardId="wbe-metadata-card"
            customFieldDefinitions={wbe.custom_field_definitions_snapshot}
            customFields={wbe.custom_fields}
            extra={
              <Can permission="wbs-element-read">
                <Button
                  icon={<HistoryOutlined />}
                  onClick={() => setHistoryOpen(true)}
                >
                  {isMobile ? undefined : "History"}
                </Button>
              </Can>
            }
          />
        )}

        {/* Version history drawer */}
        {wbe && (
          <VersionHistoryDrawer
            open={historyOpen}
            onClose={() => setHistoryOpen(false)}
            entityName={`WBE: ${wbe.code} - ${wbe.name}`}
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

        {/* Child WBS Element Create Modal */}
        <WBSElementModal
          open={modalOpen}
          onCancel={() => {
            setModalOpen(false);
          }}
          onOk={async (values) => {
            if (wbe) {
              await createWBE({
                ...values,
                project_id: projectId!,
                level: (wbe.level || 1) + 1,
              } as WBSElementCreate);
            }
          }}
          confirmLoading={isCreatingWBE}
          initialValues={null}
          projectId={projectId}
          parentWbsElementId={wbe?.wbs_element_id}
          parentName={wbe?.name}
        />

        {/* Work Package Create Modal */}
        <WorkPackageModal
          open={wpModalOpen}
          onCancel={() => setWpModalOpen(false)}
          onOk={async (values) => {
            await createWP(values as WorkPackageCreate);
          }}
          confirmLoading={isCreatingWP}
          wbsElementId={wbsElementId}
        />

        {/* Control Account Create Modal */}
        <ControlAccountModal
          open={caModalOpen}
          onCancel={() => setCaModalOpen(false)}
          onOk={async (values) => {
            await createCA({
              ...(values as ControlAccountCreate),
              wbs_element_id: wbsElementId!,
            });
          }}
          confirmLoading={isCreatingCA}
          initialValues={null}
          defaultValues={{ wbs_element_id: wbsElementId }}
          projectId={projectId!}
        />

        {/* Control Account Edit Modal */}
        <ControlAccountModal
          open={caEditModalOpen}
          onCancel={() => {
            setCaEditModalOpen(false);
            setCaEditing(null);
          }}
          onOk={async (values) => {
            if (caEditing) {
              await updateCA({
                id: caEditing.control_account_id,
                data: values as ControlAccountUpdate,
              });
            }
          }}
          confirmLoading={isUpdatingCA}
          initialValues={caEditing}
          projectId={projectId!}
        />
    </PageContent>
  );
};
