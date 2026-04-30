import { useState } from "react";
import { useParams } from "react-router-dom";
import { Space, Card, Button, Modal, Progress, Tag, Typography, theme, Grid } from "antd";
import {
  EditOutlined,
  HistoryOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { useBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";
import { CostElementHeaderCard } from "@/components/cost-elements/CostElementHeaderCard";
import { CostElementInfoCard } from "@/components/cost-elements/CostElementInfoCard";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import {
  useCostElementForecast,
  useUpdateCostElementForecast,
} from "@/features/cost-elements/api/useCostElements";
import {
  useCostElementScheduleBaseline,
} from "@/features/schedule-baselines/api";
import { useProgressEntries, useCreateProgressEntry } from "@/features/progress-entries/api/useProgressEntries";
import { ForecastModal, ForecastHistoryView } from "@/features/forecasts/components";
import { ScheduleBaselineModal } from "@/features/schedule-baselines/components/ScheduleBaselineModal";
import { ProgressEntryModal } from "@/features/progress-entries/components/ProgressEntryModal";
import { ProgressEntriesTab } from "@/features/progress-entries/components/ProgressEntriesTab";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { queryKeys } from "@/api/queryKeys";
import type { ScheduleBaselineRead } from "@/features/schedule-baselines/api/useScheduleBaselines";
import type { ProgressEntryRead } from "@/api/generated";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

const { Text } = Typography;

interface ForecastData {
  forecast_id: string;
  eac_amount: string | number;
  basis_of_estimate: string;
  branch: string;
  created_at: string;
  updated_at: string;
  transaction_time?: string;
}

interface UnifiedMetricsSectionProps {
  costElement: CostElementRead;
}

interface MetricRowProps {
  label: string;
  actions: React.ReactNode;
  children: React.ReactNode;
  token: ReturnType<typeof theme.useToken>["token"];
}

interface EmptyStateProps {
  label: string;
  onCreate: () => void;
  token: ReturnType<typeof theme.useToken>["token"];
}

// Helper components for consistent styling
const MetricRow = ({ label, actions, children, token }: MetricRowProps) => (
  <div style={{ marginBottom: token.paddingLG }}>
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: token.paddingXS,
    }}>
      <Text style={{
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.5px",
        textTransform: "uppercase",
        color: token.colorTextSecondary,
      }}>
        {label}
      </Text>
      <Space size="small">{actions}</Space>
    </div>
    <div style={{
      borderTop: `1px solid ${token.colorBorderSecondary}`,
      paddingTop: token.paddingSM,
    }}>
      {children}
    </div>
  </div>
);

const EmptyState = ({ label, onCreate, token }: EmptyStateProps) => (
  <div style={{
    textAlign: "center",
    padding: token.paddingXL,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: token.paddingSM,
  }}>
    <PlusOutlined style={{ fontSize: 40, color: token.colorPrimary }} />
    <Button type="link" onClick={onCreate} style={{ padding: 0 }}>
      Create {label}
    </Button>
  </div>
);

/**
 * UnifiedMetricsSection Component
 *
 * A refined utilitarian ledger display for cost element metrics.
 * Combines Forecast, Schedule Baseline, and Progress into a single
 * data-dense card with row-based presentation.
 */
export const UnifiedMetricsSection = ({ costElement }: UnifiedMetricsSectionProps) => {
  const { token } = theme.useToken();
  const { branch: tmBranch, asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();
  const { modal } = Modal;
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const currentBranch = tmBranch || costElement.branch || "main";

  // Forecast state
  const [isForecastModalOpen, setIsForecastModalOpen] = useState(false);
  const [showForecastHistory, setShowForecastHistory] = useState(false);

  // Schedule baseline state
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);
  const [editingBaseline, setEditingBaseline] = useState<ScheduleBaselineRead | null>(null);
  const [showScheduleHistory, setShowScheduleHistory] = useState(false);

  // Progress state
  const [isProgressModalOpen, setIsProgressModalOpen] = useState(false);
  const [showProgressHistory, setShowProgressHistory] = useState(false);

  // Fetch data
  const { data: forecastData, isLoading: isForecastLoading, isError: isForecastError } = useCostElementForecast(
    costElement.cost_element_id,
    currentBranch
  );
  const forecast = forecastData as ForecastData | null;

  const { data: baseline, isLoading: isScheduleLoading, isError: isScheduleError } = useCostElementScheduleBaseline(
    costElement.cost_element_id,
    currentBranch
  );

  const { data: progressData, isLoading: isProgressLoading, isError: isProgressError } = useProgressEntries({
    cost_element_id: costElement.cost_element_id,
    perPage: 1,
  });

  const latestEntry = progressData?.items?.[0] as ProgressEntryRead | undefined;

  // Mutations
  const updateForecastMutation = useUpdateCostElementForecast({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forecasts.byCostElement(costElement.cost_element_id, currentBranch, { asOf })
      });
      setIsForecastModalOpen(false);
    },
  });

  const createProgressMutation = useCreateProgressEntry({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.progressEntries.list(costElement.cost_element_id, {})
      });
      setIsProgressModalOpen(false);
    },
  });

  // Handlers
  const handleSaveForecast = (values: Record<string, unknown>) => {
    updateForecastMutation.mutate({
      costElementId: costElement.cost_element_id,
      data: values,
      branch: currentBranch,
    });
  };

  const handleAddProgress = (values: Record<string, unknown>) => {
    createProgressMutation.mutate(values as {
      progress_percentage: number;
      control_date: string | null;
      notes: string | null;
      cost_element_id: string;
    });
  };

  // Calculations for Forecast
  const bac = Number(costElement.budget_amount);
  const eac = forecast ? Number(forecast.eac_amount) : null;
  const vac = eac !== null ? bac - eac : null;
  const vacPercentage = vac !== null && bac > 0 ? (vac / bac) * 100 : null;

  const getVacColor = () => {
    if (vac === null) return token.colorTextSecondary;
    if (vac > 0) return token.colorSuccess;
    if (vac < 0) return token.colorError;
    return token.colorTextSecondary;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  // Progression type labels
  const PROGRESSION_LABELS: Record<string, string> = {
    LINEAR: "Linear",
    GAUSSIAN: "Gaussian S-Curve",
    LOGARITHMIC: "Logarithmic",
  };

  return (
    <Card
      title="COST ELEMENT METRICS"
      styles={{
        header: {
          backgroundColor: token.colorFillSecondary,
          fontWeight: 600,
          fontSize: 11,
          letterSpacing: "0.5px",
        },
        body: { padding: token.paddingLG },
      }}
    >
      {/* Forecast Section */}
      <MetricRow
        token={token}
        label="Forecast"
        actions={
          <>
            {forecast && (
              <>
                <Button
                  type="text"
                  icon={<EditOutlined style={{ fontSize: 14 }} />}
                  onClick={() => setIsForecastModalOpen(true)}
                  style={{ padding: "4px 8px" }}
                />
                <Button
                  type="text"
                  icon={<HistoryOutlined style={{ fontSize: 14 }} />}
                  onClick={() => setShowForecastHistory(true)}
                  style={{ padding: "4px 8px" }}
                />
              </>
            )}
          </>
        }
      >
        {isForecastLoading ? (
          <Text type="secondary">Loading...</Text>
        ) : isForecastError ? (
          <Text type="danger">Error loading forecast</Text>
        ) : !forecast ? (
          <EmptyState token={token} label="Forecast" onCreate={() => setIsForecastModalOpen(true)} />
        ) : (
          <div style={{
            display: "flex",
            flexWrap: "wrap",
            gap: isMobile ? token.paddingSM : token.paddingLG,
          }}>
            <div>
              <Text type="secondary" style={{ fontSize: 11, display: "block", marginBottom: 2 }}>
                EAC
              </Text>
              <Text style={{
                fontFamily: "monospace, tabular-nums",
                fontSize: token.fontSizeLG,
                fontWeight: 600,
              }}>
                €{eac?.toLocaleString()}
              </Text>
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 11, display: "block", marginBottom: 2 }}>
                VAC
              </Text>
              <Text style={{
                fontFamily: "monospace, tabular-nums",
                fontSize: token.fontSizeLG,
                fontWeight: 600,
                color: getVacColor(),
              }}>
                {vac !== null ? (vac > 0 ? "+" : "") + `€${vac.toLocaleString()}` : "-"}
              </Text>
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 11, display: "block", marginBottom: 2 }}>
                VAC%
              </Text>
              <Text style={{
                fontFamily: "monospace, tabular-nums",
                fontSize: token.fontSizeLG,
                fontWeight: 600,
                color: getVacColor(),
              }}>
                {vacPercentage !== null ? (vacPercentage > 0 ? "+" : "") + `${vacPercentage.toFixed(1)}%` : "-"}
              </Text>
            </div>
          </div>
        )}
      </MetricRow>

      {/* Schedule Baseline Section */}
      <MetricRow
        token={token}
        label="Schedule Baseline"
        actions={
          <>
            {baseline && (
              <>
                <Button
                  type="text"
                  icon={<EditOutlined style={{ fontSize: 14 }} />}
                  onClick={() => {
                    setEditingBaseline(baseline);
                    setIsScheduleModalOpen(true);
                  }}
                  style={{ padding: "4px 8px" }}
                />
                <Button
                  type="text"
                  icon={<HistoryOutlined style={{ fontSize: 14 }} />}
                  onClick={() => setShowScheduleHistory(true)}
                  style={{ padding: "4px 8px" }}
                />
              </>
            )}
          </>
        }
      >
        {isScheduleLoading ? (
          <Text type="secondary">Loading...</Text>
        ) : isScheduleError ? (
          <Text type="danger">Error loading schedule baseline</Text>
        ) : !baseline ? (
          <EmptyState token={token} label="Schedule Baseline" onCreate={() => setIsScheduleModalOpen(true)} />
        ) : (
          <div style={{
            display: "flex",
            flexWrap: "wrap",
            gap: isMobile ? token.paddingSM : token.paddingLG,
            alignItems: "center",
          }}>
            <Tag color="green" style={{ margin: 0 }}>
              {PROGRESSION_LABELS[baseline.progression_type] || baseline.progression_type}
            </Tag>
            <Text style={{
              fontFamily: "monospace, tabular-nums",
              fontSize: token.fontSizeMD,
            }}>
              {formatDate(baseline.start_date)} → {formatDate(baseline.end_date)}
            </Text>
          </div>
        )}
      </MetricRow>

      {/* Progress Section */}
      <MetricRow
        token={token}
        label="Progress"
        actions={
          <>
            <Button
              type="text"
              icon={<PlusOutlined style={{ fontSize: 14 }} />}
              onClick={() => setIsProgressModalOpen(true)}
              style={{ padding: "4px 8px" }}
            />
            {latestEntry && (
              <Button
                type="text"
                icon={<HistoryOutlined style={{ fontSize: 14 }} />}
                onClick={() => setShowProgressHistory(true)}
                style={{ padding: "4px 8px" }}
              />
            )}
          </>
        }
      >
        {isProgressLoading ? (
          <Text type="secondary">Loading...</Text>
        ) : isProgressError ? (
          <Text type="danger">Error loading progress</Text>
        ) : !latestEntry ? (
          <EmptyState token={token} label="Progress Entry" onCreate={() => setIsProgressModalOpen(true)} />
        ) : (
          <div style={{
            display: "flex",
            flexDirection: "column",
            gap: token.paddingSM,
          }}>
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: token.paddingMD,
              flexWrap: "wrap",
            }}>
              <Text style={{
                fontFamily: "monospace, tabular-nums",
                fontSize: token.fontSizeXL,
                fontWeight: 600,
              }}>
                {Math.round(parseFloat(latestEntry.progress_percentage))}%
              </Text>
              <Progress
                percent={Math.round(parseFloat(latestEntry.progress_percentage))}
                showInfo={false}
                strokeColor={parseFloat(latestEntry.progress_percentage) === 100
                  ? token.colorSuccess
                  : token.colorPrimary
                }
                trailColor={token.colorFillSecondary}
                size="small"
                style={{
                  flex: 1,
                  minWidth: 100,
                  height: 4,
                  marginBottom: 2,
                }}
              />
              <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                As of {latestEntry.valid_time_formatted?.lower
                  ? formatDate(latestEntry.valid_time_formatted.lower)
                  : "-"
                }
              </Text>
            </div>
          </div>
        )}
      </MetricRow>

      {/* Modals */}
      <ForecastModal
        open={isForecastModalOpen}
        onCancel={() => setIsForecastModalOpen(false)}
        onOk={handleSaveForecast}
        confirmLoading={updateForecastMutation.isPending}
        initialValues={forecast}
        currentBranch={currentBranch}
        costElementId={costElement.cost_element_id}
        costElementName={`Cost Element ${costElement.cost_element_id}`}
        budgetAmount={bac}
      />

      <Modal
        title="Forecast History & Time Travel"
        open={showForecastHistory}
        onCancel={() => setShowForecastHistory(false)}
        footer={null}
        width={1000}
      >
        <ForecastHistoryView
          costElementId={costElement.cost_element_id}
          currentBranch={currentBranch}
        />
      </Modal>

      <ScheduleBaselineModal
        visible={isScheduleModalOpen}
        onClose={() => {
          setIsScheduleModalOpen(false);
          setEditingBaseline(null);
        }}
        onSuccess={() => {
          setIsScheduleModalOpen(false);
          setEditingBaseline(null);
        }}
        costElementId={costElement.cost_element_id}
        baseline={editingBaseline || undefined}
      />

      <VersionHistoryDrawer
        open={showScheduleHistory}
        onClose={() => setShowScheduleHistory(false)}
        versions={[
          {
            id: "v1",
            valid_from: baseline?.start_date || "",
            transaction_time: new Date().toISOString(),
            changed_by: "System",
          },
        ]}
        entityName={`Schedule Baseline: ${baseline?.name || ""}`}
        isLoading={false}
      />

      <ProgressEntryModal
        open={isProgressModalOpen}
        onCancel={() => setIsProgressModalOpen(false)}
        onOk={handleAddProgress}
        confirmLoading={createProgressMutation.isPending}
        costElementId={costElement.cost_element_id}
      />

      <Modal
        title="Progress History"
        open={showProgressHistory}
        onCancel={() => setShowProgressHistory(false)}
        footer={null}
        width={1000}
        destroyOnClose
      >
        <ProgressEntriesTab costElement={costElement} />
      </Modal>
    </Card>
  );
};

export const CostElementOverview = () => {
  const { id } = useParams<{ id: string }>();
  const { data: costElement, isLoading } = useCostElement(id!);
  const { data: budgetStatus } = useBudgetStatus(id!);

  if (isLoading || !costElement) return null;

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <CostElementHeaderCard
        costElement={costElement}
        loading={isLoading}
        actualCosts={budgetStatus?.used}
        extraContent={
          id ? (
            <CostHistoryChart
              entityType="cost_element"
              entityId={id}
              headless
            />
          ) : undefined
        }
      />

      <CostElementInfoCard costElement={costElement} loading={isLoading} />

      <UnifiedMetricsSection
        costElement={costElement}
      />
    </Space>
  );
};
