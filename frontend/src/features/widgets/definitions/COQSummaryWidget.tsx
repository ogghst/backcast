import { SafetyCertificateOutlined } from "@ant-design/icons";
import { Col, Row, Statistic, Tag, Typography, theme } from "antd";
import type { FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import {
  useCostEventSummary,
  useCOQMetrics,
} from "@/features/cost-events/api/useCostEvents";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";
import { formatCurrency } from "@/components/explorer/shared/formatters";

const { Text } = Typography;

interface COQSummaryConfig {
  currency?: string;
}

const COQSummaryComponent: FC<WidgetComponentProps<COQSummaryConfig>> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
  onFullscreen,
  widgetType,
  dashboardName,
}) => {
  const { token } = theme.useToken();
  const context = useDashboardContext();

  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
    refetch: summaryRefetch,
  } = useCostEventSummary(context.projectId);

  const {
    data: metrics,
    isLoading: metricsLoading,
    error: metricsError,
    refetch: metricsRefetch,
  } = useCOQMetrics(context.projectId);

  const isLoading = summaryLoading || metricsLoading;
  const error = summaryError ?? metricsError;
  const refetch = () => {
    summaryRefetch();
    metricsRefetch();
  };

  const currency = config.currency ?? "EUR";

  return (
    <WidgetShell
      instanceId={instanceId}
      title="COQ Summary"
      icon={<SafetyCertificateOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
      onFullscreen={onFullscreen}
      widgetType={widgetType}
      dashboardName={dashboardName}
    >
      {summary && metrics ? (
        <div style={{ display: "flex", flexDirection: "column", gap: token.paddingSM }}>
          {/* Planned COQ (from work package cost_impact) */}
          <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
            Planned (Budgeted)
          </Text>
          <Row gutter={[token.paddingSM, token.paddingXS]}>
            <Col span={6}>
              <Statistic
                title="Prevention"
                value={formatCurrency(summary.prevention_cost, currency)}
                valueStyle={{ color: token.colorPrimary, fontSize: token.fontSize }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Appraisal"
                value={formatCurrency(summary.appraisal_cost, currency)}
                valueStyle={{ color: token.colorInfo, fontSize: token.fontSize }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Internal Failure"
                value={formatCurrency(summary.internal_failure_cost, currency)}
                valueStyle={{ color: token.colorWarning, fontSize: token.fontSize }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="External Failure"
                value={formatCurrency(summary.external_failure_cost, currency)}
                valueStyle={{ color: token.colorError, fontSize: token.fontSize }}
              />
            </Col>
          </Row>

          {/* Actual COQ metrics (from cost registrations) */}
          <Row gutter={[token.paddingSM, token.paddingXS]} align="middle">
            <Col span={6}>
              <Statistic
                title="Actual COQ"
                value={formatCurrency(metrics.total_coq, currency)}
                valueStyle={{ fontSize: token.fontSizeSM }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="CPQ"
                value={formatCurrency(metrics.cpq, currency)}
                valueStyle={{ fontSize: token.fontSizeSM }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="COQ Ratio"
                value={metrics.coq_ratio != null ? `${Number(metrics.coq_ratio).toFixed(1)}%` : "-"}
                valueStyle={{ fontSize: token.fontSizeSM }}
              />
            </Col>
            <Col span={6}>
              <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                QPI{" "}
              </Text>
              {metrics.qpi_rating ? (
                <Tag
                  color={
                    metrics.qpi_rating === "Outstanding"
                      ? "success"
                      : metrics.qpi_rating === "Within Target"
                        ? "processing"
                        : metrics.qpi_rating === "Below Target"
                          ? "warning"
                          : "error"
                  }
                >
                  {metrics.qpi_rating}
                </Tag>
              ) : (
                <Text type="secondary">-</Text>
              )}
            </Col>
          </Row>
        </div>
      ) : (
        !isLoading &&
        !error && (
          <div style={{ textAlign: "center", padding: token.paddingMD }}>
            <Text type="secondary">No COQ data available</Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<COQSummaryConfig>({
  typeId: widgetTypeId("coq-summary"),
  displayName: "COQ Summary",
  description:
    "Cost of Quality summary with 4-category breakdown and key metrics",
  category: "summary",
  icon: <SafetyCertificateOutlined />,
  sizeConstraints: {
    minW: 6,
    minH: 2,
    defaultW: 12,
    defaultH: 2,
  },
  component: COQSummaryComponent,
  defaultConfig: {},
});
