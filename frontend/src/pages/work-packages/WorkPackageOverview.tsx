import { useParams } from "react-router-dom";
import {
  Card,
  Descriptions,
  Typography,
  theme,
  Row,
  Col,
  Progress,
  Button,
  Table,
  Tag,
  Grid,
  Space,
  Flex,
} from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  CalendarOutlined,
  LineChartOutlined,
  PieChartOutlined,
} from "@ant-design/icons";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { formatCurrency, formatCompactCurrency, getCurrencySymbol } from "@/utils/formatters";
import { ViewModeToggle } from "@/components/common/ViewModeToggle";
import { useViewMode } from "@/hooks/useViewMode";
import { CostElementCard } from "@/features/cost-elements/components/CostElementCard";
import { useWorkPackage, useWorkPackageBudgetStatus } from "@/features/work-packages/api/useWorkPackages";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { WorkPackagesPmiService, type CostElementRead, type ForecastRead } from "@/api/generated";
import { useState, useMemo } from "react";
import { CostElementModal } from "@/features/cost-elements/components/CostElementModal";
import {
  useCreateCostElement,
  useUpdateCostElement,
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
import { App } from "antd";

const { Text } = Typography;

const PROGRESSION_LABELS: Record<string, string> = {
  LINEAR: "Linear",
  GAUSSIAN: "Gaussian (S-Curve)",
  LOGARITHMIC: "Logarithmic",
};

export const WorkPackageOverview = () => {
  const { id, projectId } = useParams<{ id: string; projectId?: string }>();
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  // Time machine for timeline ring
  const { asOf } = useTimeMachineParams();
  const [nowTime] = useState(() => Date.now());
  const referenceTime = asOf ? new Date(asOf).getTime() : nowTime;

  const { data: workPackage, isLoading } = useWorkPackage(id!);
  const { data: budgetStatus } = useWorkPackageBudgetStatus(id!);
  const queryClient = useQueryClient();
  const { modal } = App.useApp();

  const currency = useProjectCurrency(undefined);
  const currencySymbol = getCurrencySymbol(currency);

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
  const [selectedCostElement, setSelectedCostElement] = useState<CostElementRead | null>(null);
  const [sbModalOpen, setSbModalOpen] = useState(false);
  const [fcModalOpen, setFcModalOpen] = useState(false);

  // Schedule baseline and forecast data
  const { data: scheduleBaseline } = useWorkPackageScheduleBaseline(id!);
  const { data: forecast } = useWorkPackageForecast(id!);
  const { mutateAsync: upsertForecast } = useUpsertWorkPackageForecast();
  const { mutate: deleteForecast } = useDeleteWorkPackageForecast();
  const { mutate: deleteScheduleBaseline } = useDeleteWorkPackageScheduleBaseline();

  // Timeline progress from schedule baseline
  const sbStartDate = scheduleBaseline?.start_date;
  const sbEndDate = scheduleBaseline?.end_date;
  const timePercent = useMemo(() => {
    if (!sbStartDate || !sbEndDate) return 0;
    const start = new Date(sbStartDate).getTime();
    const end = new Date(sbEndDate).getTime();
    if (end <= start) return 0;
    const pct = Math.round(((referenceTime - start) / (end - start)) * 100);
    return Math.max(0, Math.min(100, pct));
  }, [sbStartDate, sbEndDate, referenceTime]);

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
      setSelectedCostElement(null);
    },
  });

  const { mutateAsync: updateCostElement } = useUpdateCostElement({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.costElements.lists() });
      setCeModalOpen(false);
      setSelectedCostElement(null);
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

  const handleEditCE = (ce: CostElementRead) => {
    setSelectedCostElement(ce);
    setCeModalOpen(true);
  };

  const handleAddCE = () => {
    setSelectedCostElement(null);
    setCeModalOpen(true);
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
  const percentage = budgetStatus?.percentage
    ? Number(budgetStatus.percentage)
    : budget > 0
      ? (used / budget) * 100
      : 0;

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
      width: 80,
      render: (_: unknown, record: CostElementRead) => (
        <Space>
          <Can permission="cost-element-update">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditCE(record)}
              title="Edit"
            />
          </Can>
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
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {/* Header Card: Title + Timeline + Cost rings + CostHistoryChart */}
      <Card
        style={{
          borderRadius: token.borderRadiusLG,
          border: `1px solid ${token.colorBorder}`,
        }}
      >
        {/* Title row */}
        <Flex
          justify="space-between"
          align={isMobile ? "flex-start" : "center"}
          vertical={isMobile}
          gap={isMobile ? token.marginXS : 0}
          style={{ marginBottom: token.marginMD }}
        >
          <Typography.Title
            level={3}
            style={{
              margin: 0,
              fontSize: isMobile ? token.fontSizeXL : token.fontSizeXXL,
              fontWeight: 600,
              color: token.colorText,
            }}
          >
            {workPackage.code} &mdash; {workPackage.name}
          </Typography.Title>
          <Tag
            style={{
              fontSize: token.fontSize,
              padding: `${token.paddingXS}px ${token.paddingMD}px`,
              borderRadius: token.borderRadius,
              fontWeight: token.fontWeightMedium,
              margin: 0,
            }}
          >
            {workPackage.status || "draft"}
          </Tag>
        </Flex>

        {/* Description */}
        {workPackage.description && (
          <Typography.Paragraph
            type="secondary"
            style={{
              margin: 0,
              marginBottom: token.marginLG,
              fontSize: token.fontSize,
              lineHeight: token.lineHeight,
            }}
          >
            {workPackage.description}
          </Typography.Paragraph>
        )}

        {/* Control Account label */}
        {workPackage.control_account_name && (
          <Text
            type="secondary"
            style={{ display: "block", marginBottom: token.marginMD, fontSize: token.fontSizeSM }}
          >
            Control Account: <Text strong>{workPackage.control_account_name}</Text>
          </Text>
        )}

        <Row gutter={[token.marginLG, token.marginLG]} align="top">
          {/* Timeline Progress Ring */}
          <Col xs={24} sm={12} md={6}>
            <div style={{ textAlign: "center", padding: token.paddingSM }}>
              <Progress
                type="circle"
                percent={scheduleBaseline ? timePercent : 0}
                size={isMobile ? 120 : 160}
                format={(percent) => (
                  <div>
                    <div
                      style={{
                        fontSize: isMobile ? token.fontSizeLG : token.fontSizeXL,
                        fontWeight: token.fontWeightSemiBold,
                      }}
                    >
                      {scheduleBaseline ? `${percent}%` : "—"}
                    </div>
                    <div
                      style={{
                        fontSize: token.fontSizeXS,
                        color: token.colorTextSecondary,
                      }}
                    >
                      {scheduleBaseline ? "elapsed" : "no baseline"}
                    </div>
                  </div>
                )}
                strokeColor={
                  !scheduleBaseline
                    ? token.colorTextDisabled
                    : timePercent > 90
                      ? token.colorError
                      : timePercent > 70
                        ? token.colorWarning
                        : token.colorPrimary
                }
              />
              <div style={{ marginTop: token.marginMD }}>
                <div>
                  <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                    Timeline
                  </Text>
                </div>
                {scheduleBaseline ? (
                  <div>
                    <Text strong>
                      {formatDate(scheduleBaseline.start_date)}
                    </Text>
                    <Text
                      type="secondary"
                      style={{ margin: `0 ${token.marginXS}px` }}
                    >
                      &rarr;
                    </Text>
                    <Text strong>
                      {formatDate(scheduleBaseline.end_date)}
                    </Text>
                  </div>
                ) : (
                  <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                    No schedule baseline
                  </Text>
                )}
              </div>
            </div>
          </Col>

          {/* Cost Progress Ring */}
          <Col xs={24} sm={12} md={6}>
            <div style={{ textAlign: "center", padding: token.paddingSM }}>
              <Progress
                type="circle"
                percent={budget > 0 ? Math.min(Math.round(percentage), 100) : 0}
                size={isMobile ? 120 : 160}
                strokeWidth={6}
                strokeColor={
                  percentage > 100
                    ? token.colorError
                    : percentage > 85
                      ? token.colorWarning
                      : token.colorPrimary
                }
                format={(percent) => (
                  <div>
                    <div style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightSemiBold }}>
                      {percent}%
                    </div>
                    <div style={{ fontSize: token.fontSizeXS, color: token.colorTextSecondary }}>
                      of budget
                    </div>
                  </div>
                )}
              />
              <div style={{ marginTop: token.marginMD }}>
                <div>
                  <Text strong>{formatCompactCurrency(budget, currency)}</Text>
                  <Text type="secondary" style={{ fontSize: token.fontSizeSM, marginLeft: token.marginXS }}>
                    budget
                  </Text>
                </div>
                <div style={{ marginTop: token.marginXS }}>
                  <span
                    style={{
                      display: "inline-block",
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: percentage > 100
                        ? token.colorError
                        : percentage > 85
                          ? token.colorWarning
                          : token.colorPrimary,
                      marginRight: token.marginXS,
                    }}
                  />
                  <Text style={{ fontSize: token.fontSizeSM }}>
                    {formatCompactCurrency(used, currency)} costs
                  </Text>
                  {budget > 0 && (
                    <Text type="secondary" style={{ fontSize: token.fontSizeSM, marginLeft: token.marginXS }}>
                      ({Math.round(percentage)}%)
                    </Text>
                  )}
                </div>
              </div>
            </div>
          </Col>

          {/* Cost History Chart */}
          <Col xs={24} sm={24} md={12}>
            <CostHistoryChart
              entityType="work_package"
              entityId={id!}
              headless
              projectId={projectId}
            />
          </Col>
        </Row>
      </Card>

      {/* Section 2: Schedule Baseline + Forecast side-by-side on desktop */}
      <Row gutter={[token.marginLG, token.marginLG]}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <CalendarOutlined />
                <span>Schedule Baseline</span>
              </Space>
            }
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
              <Descriptions column={{ xs: 1, sm: 2 }} size="small">
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
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <LineChartOutlined />
                <span>Forecast</span>
              </Space>
            }
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
              <Descriptions column={{ xs: 1, sm: 2 }} size="small">
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
          </Card>
        </Col>
      </Row>

      {/* Section 4: Cost Elements (EOC) */}
      <Card
        title={
          <Space>
            <PieChartOutlined />
            <span>Cost Elements</span>
          </Space>
        }
        extra={
          <Space>
            <ViewModeToggle viewMode={ceViewMode} onCycleViewMode={ceCycleViewMode} />
            <Can permission="cost-element-create">
              <Button
                type="primary"
                size="small"
                icon={<PlusOutlined />}
                onClick={handleAddCE}
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
      </Card>

      {/* Modals */}
      <CostElementModal
        open={ceModalOpen}
        onCancel={() => { setCeModalOpen(false); setSelectedCostElement(null); }}
        onOk={async (values) => {
          if (selectedCostElement) {
            await updateCostElement({
              id: selectedCostElement.id,
              data: values,
            });
          } else {
            await createCostElement({
              cost_element_type_id: values.cost_element_type_id,
              description: values.description,
              work_package_id: id!,
            } as Parameters<typeof createCostElement>[0]);
          }
        }}
        confirmLoading={false}
        initialValues={selectedCostElement}
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
    </Space>
  );
};
