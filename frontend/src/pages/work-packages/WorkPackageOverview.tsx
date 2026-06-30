import { useParams } from "react-router-dom";
import {
  Descriptions,
  Typography,
  theme,
  Row,
  Col,
  Statistic,
  Progress,
  Alert,
  Button,
  Table,
  Tag,
  Grid,
  Space,
  Divider,
} from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  CalendarOutlined,
  LineChartOutlined,
  DollarOutlined,
  PieChartOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import { PanelCard } from "@/components/common/PanelCard";
import { entityInfoDescriptionsProps } from "@/components/common/entityInfoDescriptionsProps";
import { ViewModeToggle } from "@/components/common/ViewModeToggle";
import { useViewMode } from "@/hooks/useViewMode";
import { CostElementCard } from "@/features/cost-elements/components/CostElementCard";
import { useWorkPackage, useWorkPackageBudgetStatus, useWorkPackageBreadcrumb } from "@/features/work-packages/api/useWorkPackages";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { useProject } from "@/features/projects/api/useProjects";
import { WorkPackageHeaderCard } from "@/components/WorkPackages/WorkPackageHeaderCard";
import { EntityMetadataCard } from "@/components/common/EntityMetadataCard";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import { formatCurrency, getCurrencySymbol } from "@/utils/formatters";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { WorkPackagesPmiService, type CostElementRead, type ForecastRead } from "@/api/generated";
import { useState, useMemo } from "react";
import { CostElementModal } from "@/features/cost-elements/components/CostElementModal";
import {
  useCreateCostElement,
  useDeleteCostElement,
} from "@/features/cost-elements/api/useCostElements";
import {
  useWorkPackageForecast,
  useUpsertWorkPackageForecast,
  useDeleteWorkPackageForecast,
} from "@/features/forecasts/api/useWorkPackageForecast";
import {
  useWorkPackageScheduleBaseline,
  useDeleteWorkPackageScheduleBaseline,
} from "@/features/schedule-baselines/api/useWorkPackageScheduleBaseline";
import { WorkPackageScheduleBaselineModal } from "@/features/schedule-baselines/components/WorkPackageScheduleBaselineModal";
import { ForecastModal } from "@/features/forecasts/components/ForecastModal";
import { Can } from "@/components/auth/Can";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { App } from "antd";

const { Text } = Typography;

const PROGRESSION_LABELS: Record<string, string> = {
  LINEAR: "Linear",
  GAUSSIAN: "Gaussian (S-Curve)",
  LOGARITHMIC: "Logarithmic",
};

export const WorkPackageOverview = () => {
  const { id } = useParams<{ id: string }>();
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const { data: workPackage, isLoading } = useWorkPackage(id!);
  const { data: budgetStatus, isLoading: budgetLoading } = useWorkPackageBudgetStatus(id!);
  const queryClient = useQueryClient();
  const { modal } = App.useApp();

  // Resolve the owning project (for control_date + currency) via breadcrumb.
  const { data: breadcrumb } = useWorkPackageBreadcrumb(id);
  const projectId = breadcrumb?.project?.project_id;
  const { data: wpProject } = useProject(projectId);
  const controlDate = (wpProject as Record<string, unknown> | undefined)
    ?.control_date as string | null | undefined;

  const currency = useProjectCurrency(projectId);
  const currencySymbol = getCurrencySymbol(currency);

  // Version history state
  const [historyOpen, setHistoryOpen] = useState(false);
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory({
    resource: "work-packages",
    entityId: id,
    fetchFn: (wpId) => WorkPackagesPmiService.getWorkPackageHistory(wpId),
    enabled: historyOpen,
  });

  // Fetch cost elements for this work package
  const { data: costElements = [] } = useQuery<CostElementRead[]>({
    queryKey: queryKeys.costElements.list(id),
    queryFn: async () => {
      const res = await WorkPackagesPmiService.getWorkPackageCostElements(id!);
      return (res as CostElementRead[]) || [];
    },
    enabled: !!id,
  });

  // Modal states
  const [ceModalOpen, setCeModalOpen] = useState(false);
  const [sbModalOpen, setSbModalOpen] = useState(false);
  const [fcModalOpen, setFcModalOpen] = useState(false);

  // Schedule baseline and forecast data
  const { data: scheduleBaseline } = useWorkPackageScheduleBaseline(id!);
  const { data: forecast } = useWorkPackageForecast(id!);
  const { mutateAsync: upsertForecast } = useUpsertWorkPackageForecast();
  const { mutate: deleteForecast } = useDeleteWorkPackageForecast();
  const { mutate: deleteScheduleBaseline } = useDeleteWorkPackageScheduleBaseline();

  // View mode for cost elements
  const { viewMode: ceViewMode, resolvedMode: ceResolvedMode, cycleViewMode: ceCycleViewMode } = useViewMode("cost-elements", isMobile);

  // Build typeNames map for CostElementCard
  const ceTypeNames = useMemo(() => {
    const map: Record<string, string> = {};
    costElements.forEach(ce => {
      if (ce.cost_element_type_id && ce.cost_element_type_name) {
        map[ce.cost_element_type_id] = ce.cost_element_type_name;
      }
    });
    return map;
  }, [costElements]);

  const { mutateAsync: createCostElement } = useCreateCostElement({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.costElements.lists() });
      setCeModalOpen(false);
    },
  });

  const { mutate: deleteCostElement } = useDeleteCostElement({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.costElements.lists() });
    },
  });

  const handleDeleteCE = (ce: CostElementRead) => {
    modal.confirm({
      title: "Are you sure you want to delete this Cost Element?",
      content: "This will soft delete the cost element and all its cost registrations.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteCostElement(ce.cost_element_id),
    });
  };

  const handleDeleteForecast = () => {
    modal.confirm({
      title: "Delete Forecast?",
      content: "This will remove the forecast for this work package.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteForecast({ workPackageId: id! }),
    });
  };

  const handleDeleteScheduleBaseline = () => {
    if (!scheduleBaseline) return;
    modal.confirm({
      title: "Delete Schedule Baseline?",
      content: "This will remove the schedule baseline for this work package.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () =>
        deleteScheduleBaseline({
          workPackageId: id!,
          baselineId: scheduleBaseline.schedule_baseline_id,
        }),
    });
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  if (isLoading || !workPackage) return null;

  const budget = budgetStatus?.budget
    ? Number(budgetStatus.budget)
    : Number(workPackage.budget_amount || 0);
  const used = budgetStatus?.used ? Number(budgetStatus.used) : 0;
  const remaining = budgetStatus?.remaining
    ? Number(budgetStatus.remaining)
    : budget - used;
  const percentage = budgetStatus?.percentage
    ? Number(budgetStatus.percentage)
    : budget > 0
      ? (used / budget) * 100
      : 0;

  // Determine status color
  let statusColor = token.colorSuccess;
  let statusText = "Healthy";

  if (percentage >= 100) {
    statusColor = token.colorError;
    statusText = "Exceeded";
  } else if (percentage >= 90) {
    statusColor = token.colorWarning;
    statusText = "Warning";
  } else if (percentage >= 75) {
    statusColor = token.colorPrimary;
    statusText = "Monitoring";
  }

  const ceColumns = [
    {
      title: "Type",
      dataIndex: "cost_element_type_name",
      key: "cost_element_type_name",
      render: (name: string | null, record: CostElementRead) => (
        <Space size={4}>
          <span>{name || "Unknown"}</span>
          {record.cost_element_type_code && (
            <Tag>{record.cost_element_type_code}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: "Amount",
      dataIndex: "amount",
      key: "amount",
      align: "right" as const,
      render: (amount: string | number) => (
        <Text strong>
          {currencySymbol}
          {Number(amount || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
          })}
        </Text>
      ),
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      responsive: ["md" as const],
      render: (desc: string | null) => desc || "-",
    },
    {
      title: "Actions",
      key: "actions",
      width: 60,
      render: (_: unknown, record: CostElementRead) => (
        <Can permission="cost-element-delete">
          <Button
            danger
            type="text"
            size="small"
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteCE(record)}
            title="Delete"
          />
        </Can>
      ),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: token.marginLG }}>
      {/* Unified 3-chart header (time donut + budget donut + EV-PV-AC chart) */}
      <WorkPackageHeaderCard
        workPackage={workPackage}
        actualCosts={budgetStatus?.used as number | undefined}
        scheduleStart={scheduleBaseline?.start_date}
        scheduleEnd={scheduleBaseline?.end_date}
        controlDate={controlDate || undefined}
        currency={currency}
        extraContent={
          id ? (
            <CostHistoryChart
              entityType="work_package"
              entityId={id}
              headless
              controlDate={controlDate || undefined}
              projectId={projectId}
            />
          ) : undefined
        }
      />

      {/* Section 1: Work Package Information (collapsible) — moved to metadata footer below */}

      {/* Section 2: Schedule Baseline + Forecast side-by-side on desktop */}
      <Row gutter={[token.marginLG, token.marginLG]}>
        <Col xs={24} xl={12}>
          <PanelCard
            icon={<CalendarOutlined />}
            title="Schedule Baseline"
            extra={
              <Space>
                {scheduleBaseline ? (
                  <>
                    <Can permission="schedule-baseline-update">
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => setSbModalOpen(true)}
                      >
                        {isMobile ? undefined : "Edit"}
                      </Button>
                    </Can>
                    <Can permission="schedule-baseline-delete">
                      <Button
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={handleDeleteScheduleBaseline}
                      >
                        {isMobile ? undefined : "Delete"}
                      </Button>
                    </Can>
                  </>
                ) : (
                  <Can permission="schedule-baseline-create">
                    <Button
                      type="primary"
                      size="small"
                      icon={<PlusOutlined />}
                      onClick={() => setSbModalOpen(true)}
                    >
                      {isMobile ? undefined : "Add Baseline"}
                    </Button>
                  </Can>
                )}
              </Space>
            }
          >
            {scheduleBaseline ? (
              <Descriptions {...entityInfoDescriptionsProps(token)}>
                <Descriptions.Item label="Name">
                  <Text strong>{scheduleBaseline.name}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Progression">
                  <Tag color="blue">
                    {PROGRESSION_LABELS[scheduleBaseline.progression_type || "LINEAR"] || scheduleBaseline.progression_type}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Start Date">
                  {formatDate(scheduleBaseline.start_date)}
                </Descriptions.Item>
                <Descriptions.Item label="End Date">
                  {formatDate(scheduleBaseline.end_date)}
                </Descriptions.Item>
                {scheduleBaseline.description && (
                  <Descriptions.Item label="Description" span={2}>
                    {scheduleBaseline.description}
                  </Descriptions.Item>
                )}
              </Descriptions>
            ) : (
              <Text type="secondary">
                No schedule baseline defined. Add one to enable Planned Value calculations and EVM analysis.
              </Text>
            )}
          </PanelCard>
        </Col>

        <Col xs={24} xl={12}>
          <PanelCard
            icon={<LineChartOutlined />}
            title="Forecast"
            extra={
              <Space>
                {forecast ? (
                  <>
                    <Can permission="forecast-update">
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => setFcModalOpen(true)}
                      >
                        {isMobile ? undefined : "Edit"}
                      </Button>
                    </Can>
                    <Can permission="forecast-delete">
                      <Button
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={handleDeleteForecast}
                      >
                        {isMobile ? undefined : "Delete"}
                      </Button>
                    </Can>
                  </>
                ) : (
                  <Can permission="forecast-create">
                    <Button
                      type="primary"
                      size="small"
                      icon={<PlusOutlined />}
                      onClick={() => setFcModalOpen(true)}
                    >
                      {isMobile ? undefined : "Add Forecast"}
                    </Button>
                  </Can>
                )}
              </Space>
            }
          >
            {forecast ? (
              <Descriptions {...entityInfoDescriptionsProps(token)}>
                <Descriptions.Item label="Estimate at Complete (EAC)">
                  <Text strong>
                    {formatCurrency(Number(forecast.eac_amount || 0), currency)}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="Variance at Complete (VAC)">
                  <Text
                    strong
                    style={{
                      color:
                        Number(workPackage?.budget_amount || 0) -
                          Number(forecast.eac_amount || 0) >=
                        0
                          ? token.colorSuccess
                          : token.colorError,
                    }}
                  >
                    {formatCurrency(
                      Number(workPackage?.budget_amount || 0) -
                        Number(forecast.eac_amount || 0),
                      currency,
                    )}
                  </Text>
                </Descriptions.Item>
                {forecast.basis_of_estimate && (
                  <Descriptions.Item label="Basis of Estimate" span={2}>
                    <Typography.Paragraph
                      ellipsis={{ rows: 3, expandable: true, symbol: "more" }}
                      style={{ margin: 0 }}
                    >
                      {forecast.basis_of_estimate}
                    </Typography.Paragraph>
                  </Descriptions.Item>
                )}
              </Descriptions>
            ) : (
              <Text type="secondary">
                No forecast defined. Add one to track Estimate at Complete (EAC) and Variance at Complete (VAC).
              </Text>
            )}
          </PanelCard>
        </Col>
      </Row>

      {/* Section 3: Budget Summary */}
      {!budgetLoading && (
        <>
          <PanelCard
            icon={<DollarOutlined />}
            title="Budget Summary"
            extra={
              <Tag color={percentage >= 100 ? "red" : percentage >= 90 ? "orange" : "blue"}>
                {statusText}
              </Tag>
            }
          >
            <Row gutter={[token.marginMD, token.marginMD]}>
              <Col xs={12} sm={6}>
                <Statistic
                  title="Budget"
                  value={budget}
                  precision={2}
                  prefix={currencySymbol}
                  valueStyle={{ color: token.colorPrimary, fontSize: isMobile ? token.fontSizeLG : undefined }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="Used"
                  value={used}
                  precision={2}
                  prefix={currencySymbol}
                  valueStyle={{
                    color: percentage >= 100 ? token.colorError : token.colorSuccess,
                    fontSize: isMobile ? token.fontSizeLG : undefined,
                  }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="Remaining"
                  value={remaining}
                  precision={2}
                  prefix={currencySymbol}
                  valueStyle={{
                    color: remaining < 0 ? token.colorError : token.colorSuccess,
                    fontSize: isMobile ? token.fontSizeLG : undefined,
                  }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="Used %"
                  value={percentage}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: statusColor, fontSize: isMobile ? token.fontSizeLG : undefined }}
                />
              </Col>
            </Row>

            <Divider style={{ margin: `${token.marginMD} 0` }} />

            <Progress
              percent={Math.min(percentage, 100)}
              strokeColor={statusColor}
              status={percentage >= 100 ? "exception" : undefined}
            />
          </PanelCard>

          {(percentage >= 100 || (percentage >= 90 && percentage < 100)) && (
            <Alert
              message={percentage >= 100 ? "Budget Exceeded" : "Budget Warning"}
              description={
                percentage >= 100
                  ? `This work package has exceeded its budget by ${formatCurrency(Math.abs(remaining), currency)}.`
                  : `This work package has used ${percentage.toFixed(1)}% of its budget. Consider reviewing before adding more costs.`
              }
              type="warning"
              showIcon
            />
          )}
        </>
      )}

      {/* Section 4: Cost Elements (EOC) */}
      <PanelCard
        icon={<PieChartOutlined />}
        title="Cost Elements"
        extra={
          <Space>
            <ViewModeToggle viewMode={ceViewMode} onCycleViewMode={ceCycleViewMode} />
            <Can permission="cost-element-create">
              <Button
                type="primary"
                size="small"
                icon={<PlusOutlined />}
                onClick={() => setCeModalOpen(true)}
              >
                {isMobile ? undefined : "Add Cost Element"}
              </Button>
            </Can>
          </Space>
        }
      >
        {(() => {
          const useCeCard = ceResolvedMode === "card";
          if (costElements.length === 0) {
            return <Text type="secondary">No cost elements defined. Add cost elements to track detailed budget allocations.</Text>;
          }
          if (useCeCard) {
            return (
              <div style={{ display: "grid", gridTemplateColumns: `repeat(auto-fill, minmax(280px, 1fr))`, gap: token.marginMD }}>
                {costElements.map((ce) => (
                  <CostElementCard
                    key={ce.cost_element_id}
                    costElement={ce}
                    typeNames={ceTypeNames}
                  />
                ))}
              </div>
            );
          }
          return (
            <Table
              dataSource={costElements}
              columns={ceColumns}
              rowKey="cost_element_id"
              size="small"
              pagination={false}
            />
          );
        })()}
      </PanelCard>

      {/* Work Package metadata footer — standardized across entity pages */}
      <EntityMetadataCard
        entityId={workPackage.work_package_id}
        entityIdLabel="Work Package ID"
        parentId={workPackage.control_account_id}
        parentLabel="Control Account"
        parentValue={workPackage.control_account_name || "Unknown Control Account"}
        createdAt={workPackage.created_at}
        updatedAt={workPackage.updated_at}
        createdBy={workPackage.created_by_name}
        validTime={workPackage.valid_time_formatted}
        cardId="wp-metadata-card"
        customFieldDefinitions={workPackage.custom_field_definitions_snapshot}
        customFields={workPackage.custom_fields}
        extra={
          <Can permission="work-package-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => setHistoryOpen(true)}
            >
              {isMobile ? undefined : "History"}
            </Button>
          </Can>
        }
      />

      {/* Version history drawer */}
      {workPackage && (
        <VersionHistoryDrawer
          open={historyOpen}
          onClose={() => setHistoryOpen(false)}
          entityName={`WP: ${workPackage.code || ""} - ${workPackage.name}`}
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

      {/* Modals */}
      <CostElementModal
        open={ceModalOpen}
        onCancel={() => setCeModalOpen(false)}
        onOk={async (values) => {
          await createCostElement({
            cost_element_type_id: values.cost_element_type_id,
            description: values.description,
            work_package_id: id!,
          } as Parameters<typeof createCostElement>[0]);
        }}
        confirmLoading={false}
        initialValues={null}
        currentBranch="main"
        workPackageId={id}
        workPackageName={workPackage ? `${workPackage.code} - ${workPackage.name}` : undefined}
      />

      <WorkPackageScheduleBaselineModal
        visible={sbModalOpen}
        onClose={() => setSbModalOpen(false)}
        workPackageId={id!}
        baseline={scheduleBaseline}
      />

      <ForecastModal
        open={fcModalOpen}
        onCancel={() => setFcModalOpen(false)}
        onOk={async (values) => {
          await upsertForecast({
            workPackageId: id!,
            data: {
              eac_amount: (values as { eac_amount: number }).eac_amount,
              basis_of_estimate: (values as { basis_of_estimate: string }).basis_of_estimate,
            },
          });
        }}
        confirmLoading={false}
        initialValues={forecast as ForecastRead | null}
        currentBranch="main"
        costElementName={
          workPackage
            ? `${workPackage.code} - ${workPackage.name}`
            : undefined
        }
        budgetAmount={
          workPackage?.budget_amount
            ? Number(workPackage.budget_amount)
            : undefined
        }
      />
    </div>
  );
};
