import { useParams } from "react-router-dom";
import { Space, Card, Descriptions, Typography, theme, Row, Col, Statistic, Progress, Alert, Button, Table, Tag, Grid } from "antd";
import { PlusOutlined, DeleteOutlined, EditOutlined, CalendarOutlined, LineChartOutlined } from "@ant-design/icons";
import { ViewModeToggle } from "@/components/common/ViewModeToggle";
import { useViewMode } from "@/hooks/useViewMode";
import { CostElementCard } from "@/features/cost-elements/components/CostElementCard";
import { useWorkPackage } from "@/features/work-packages/api/useWorkPackages";
import { useWorkPackageBudgetStatus } from "@/features/work-packages/api/useWorkPackages";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { formatCurrency, formatTemporalRange, getCurrencySymbol } from "@/utils/formatters";
import { useThemeTokens } from "@/hooks/useThemeTokens";
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
import { App } from "antd";

const { Text } = Typography;

export const WorkPackageOverview = () => {
  const { id } = useParams<{ id: string }>();
  const { token } = theme.useToken();
  const { colors } = useThemeTokens();
  const { data: workPackage, isLoading } = useWorkPackage(id!);
  const { data: budgetStatus, isLoading: budgetLoading } = useWorkPackageBudgetStatus(id!);
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

  // Cost element creation modal state
  const [ceModalOpen, setCeModalOpen] = useState(false);

  // Schedule baseline modal state
  const [sbModalOpen, setSbModalOpen] = useState(false);

  // Forecast modal state
  const [fcModalOpen, setFcModalOpen] = useState(false);

  // Schedule baseline and forecast data
  const { data: scheduleBaseline } = useWorkPackageScheduleBaseline(id!);
  const { data: forecast } = useWorkPackageForecast(id!);
  const { mutateAsync: upsertForecast } = useUpsertWorkPackageForecast();
  const { mutate: deleteForecast } = useDeleteWorkPackageForecast();
  const { mutate: deleteScheduleBaseline } = useDeleteWorkPackageScheduleBaseline();

  // View mode for cost elements
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
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

  const PROGRESSION_LABELS: Record<string, string> = {
    LINEAR: "Linear",
    GAUSSIAN: "Gaussian (S-Curve)",
    LOGARITHMIC: "Logarithmic",
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
  let statusColor = colors.success;
  let statusText = "Healthy";

  if (percentage >= 100) {
    statusColor = colors.error;
    statusText = "Exceeded";
  } else if (percentage >= 90) {
    statusColor = colors.warning;
    statusText = "Warning";
  } else if (percentage >= 75) {
    statusColor = colors.primary;
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
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {/* Basic Info */}
      <Card title="Work Package Details" size="small">
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Code">
            <Text strong>{workPackage.code}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Name">
            {workPackage.name}
          </Descriptions.Item>
          <Descriptions.Item label="Status">
            {workPackage.status || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Control Account">
            {workPackage.control_account_name || "Unknown Control Account"}
          </Descriptions.Item>
          <Descriptions.Item label="Budget Amount">
            <Text strong>{formatCurrency(Number(workPackage.budget_amount || 0), currency)}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Description">
            {workPackage.description || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Created By">
            {workPackage.created_by_name || workPackage.created_by}
          </Descriptions.Item>
          <Descriptions.Item label="Valid Time">
            {workPackage.valid_time_formatted
              ? formatTemporalRange(workPackage.valid_time_formatted)
              : "-"}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Schedule Baseline */}
      <Card
        title={
          <Space>
            <CalendarOutlined />
            <span>Schedule Baseline</span>
          </Space>
        }
        size="small"
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
          <Descriptions column={2} size="small">
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

      {/* Forecast */}
      <Card
        title={
          <Space>
            <LineChartOutlined />
            <span>Forecast</span>
          </Space>
        }
        size="small"
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
          <Descriptions column={2} size="small">
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

      {/* Cost Elements (EOC) */}
      <Card
        title="Cost Elements"
        size="small"
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
                Add Cost Element
              </Button>
            </Can>
          </Space>
        }
      >
        {(() => {
          const useCeCard = ceResolvedMode === "card";
          if (useCeCard) {
            if (costElements.length === 0) return <Text type="secondary">No cost elements defined. Add cost elements to track detailed budget allocations.</Text>;
            return (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: token.marginMD }}>
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
          // Table view
          if (costElements.length === 0) {
            return <Text type="secondary">No cost elements defined. Add cost elements to track detailed budget allocations.</Text>;
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

      {/* Budget Summary */}
      {!budgetLoading && (
        <>
          <Row gutter={[16, 16]}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Budget"
                  value={budget}
                  precision={2}
                  prefix={currencySymbol}
                  styles={{ content: { color: token.colorPrimary } }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Used"
                  value={used}
                  precision={2}
                  prefix={currencySymbol}
                  styles={{
                    content: { color: percentage >= 100 ? token.colorError : token.colorSuccess },
                  }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Remaining"
                  value={remaining}
                  precision={2}
                  prefix={currencySymbol}
                  styles={{
                    content: { color: remaining < 0 ? token.colorError : token.colorSuccess },
                  }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Used %"
                  value={percentage}
                  precision={1}
                  suffix="%"
                  styles={{ content: { color: statusColor } }}
                />
              </Card>
            </Col>
          </Row>

          <Card title="Budget Progress" size="small">
            <Progress
              percent={Math.min(percentage, 100)}
              strokeColor={statusColor}
              status={percentage >= 100 ? "exception" : undefined}
            />
            <div style={{ marginTop: 8, color: token.colorTextTertiary }}>
              Status: <strong style={{ color: statusColor }}>{statusText}</strong>
            </div>
          </Card>

          {percentage >= 100 && (
            <Alert
              message="Budget Exceeded"
              description={`This work package has exceeded its budget by ${formatCurrency(Math.abs(remaining), currency)}.`}
              type="warning"
              showIcon
            />
          )}
          {percentage >= 90 && percentage < 100 && (
            <Alert
              message="Budget Warning"
              description={`This work package has used ${percentage.toFixed(1)}% of its budget. Consider reviewing before adding more costs.`}
              type="warning"
              showIcon
            />
          )}
        </>
      )}

      {/* Cost Element Creation Modal */}
      <CostElementModal
        open={ceModalOpen}
        onCancel={() => setCeModalOpen(false)}
        onOk={async (values) => {
          await createCostElement({
            ...values,
            work_package_id: id!,
          });
        }}
        confirmLoading={false}
        initialValues={null}
        currentBranch="main"
        workPackageId={id}
        workPackageName={workPackage ? `${workPackage.code} - ${workPackage.name}` : undefined}
        currency={currency}
      />

      {/* Schedule Baseline Modal */}
      <WorkPackageScheduleBaselineModal
        visible={sbModalOpen}
        onClose={() => setSbModalOpen(false)}
        workPackageId={id!}
        baseline={scheduleBaseline}
      />

      {/* Forecast Modal */}
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
