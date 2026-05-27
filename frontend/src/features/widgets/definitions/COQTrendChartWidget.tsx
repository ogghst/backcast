import { LineChartOutlined } from "@ant-design/icons";
import { Segmented, Typography, theme } from "antd";
import { useState, useMemo } from "react";
import type { FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import { useCOQTrend } from "@/features/cost-events/api/useCostEvents";
import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import {
  useEChartsTheme,
  buildAxisConfig,
  buildTooltipConfig,
  buildLegendConfig,
} from "@/features/evm/utils/echartsTheme";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";
import type { EChartsOption } from "echarts";

const { Text } = Typography;

interface COQTrendChartConfig {
  granularity: "week" | "month";
}

const COQ_COLORS = {
  prevention: "#1677ff",
  appraisal: "#13c2c2",
  internal_failure: "#fa8c16",
  external_failure: "#f5222d",
};

type TrendView = "planned" | "actual";

const COQTrendChartComponent: FC<WidgetComponentProps<COQTrendChartConfig>> = ({
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
  const echartsTheme = useEChartsTheme();
  const context = useDashboardContext();

  const [granularity, setGranularity] = useState<"week" | "month">(
    config.granularity,
  );
  const [trendView, setTrendView] = useState<TrendView>("actual");

  const { data, isLoading, error, refetch } = useCOQTrend(
    context.projectId,
    granularity,
  );

  const option = useMemo<EChartsOption>(() => {
    if (!data?.points?.length) return { series: [] };

    const dates = data.points.map((p) => p.date);
    const toNum = (v: string | undefined) => parseFloat(v ?? "0") || 0;

    const isPlanned = trendView === "planned";

    const seriesData = isPlanned
      ? {
          prevention: data.points.map((p) => toNum(p.planned_prevention)),
          appraisal: data.points.map((p) => toNum(p.planned_appraisal)),
          internal_failure: data.points.map((p) => toNum(p.planned_internal_failure)),
          external_failure: data.points.map((p) => toNum(p.planned_external_failure)),
        }
      : {
          prevention: data.points.map((p) => toNum(p.prevention)),
          appraisal: data.points.map((p) => toNum(p.appraisal)),
          internal_failure: data.points.map((p) => toNum(p.internal_failure)),
          external_failure: data.points.map((p) => toNum(p.external_failure)),
        };

    const stackId = isPlanned ? "planned" : "actual";

    return {
      tooltip: {
        ...buildTooltipConfig(
          echartsTheme.colors,
          token.colorBgElevated,
          token.boxShadow,
          token.borderRadius,
        ),
        trigger: "axis",
      },
      legend: {
        ...buildLegendConfig(echartsTheme.colors),
        bottom: 0,
      },
      grid: {
        left: 8,
        right: 8,
        top: 8,
        bottom: 40,
        containLabel: true,
      },
      xAxis: {
        type: "category",
        data: dates,
        boundaryGap: false,
        ...buildAxisConfig(echartsTheme.colors, token.colorBorderSecondary),
      },
      yAxis: {
        type: "value",
        ...buildAxisConfig(echartsTheme.colors, token.colorBorderSecondary),
      },
      series: [
        {
          name: "Prevention",
          type: "line",
          stack: stackId,
          areaStyle: { opacity: 0.3 },
          data: seriesData.prevention,
          itemStyle: { color: COQ_COLORS.prevention },
          lineStyle: { color: COQ_COLORS.prevention },
          smooth: true,
        },
        {
          name: "Appraisal",
          type: "line",
          stack: stackId,
          areaStyle: { opacity: 0.3 },
          data: seriesData.appraisal,
          itemStyle: { color: COQ_COLORS.appraisal },
          lineStyle: { color: COQ_COLORS.appraisal },
          smooth: true,
        },
        {
          name: "Internal Failure",
          type: "line",
          stack: stackId,
          areaStyle: { opacity: 0.3 },
          data: seriesData.internal_failure,
          itemStyle: { color: COQ_COLORS.internal_failure },
          lineStyle: { color: COQ_COLORS.internal_failure },
          smooth: true,
        },
        {
          name: "External Failure",
          type: "line",
          stack: stackId,
          areaStyle: { opacity: 0.3 },
          data: seriesData.external_failure,
          itemStyle: { color: COQ_COLORS.external_failure },
          lineStyle: { color: COQ_COLORS.external_failure },
          smooth: true,
        },
      ],
    };
  }, [data, echartsTheme, token, trendView]);

  return (
    <WidgetShell
      instanceId={instanceId}
      title={`COQ Trend (${trendView === "planned" ? "Planned" : "Actual"})`}
      icon={<LineChartOutlined />}
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
      {data?.points?.length ? (
        <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: token.paddingXS, marginBottom: token.paddingXS }}>
            <Segmented
              size="small"
              options={[
                { label: "Actual", value: "actual" },
                { label: "Planned", value: "planned" },
              ]}
              value={trendView}
              onChange={(v) => setTrendView(v as TrendView)}
            />
            <Segmented
              size="small"
              options={[
                { label: "Week", value: "week" },
                { label: "Month", value: "month" },
              ]}
              value={granularity}
              onChange={(v) => setGranularity(v as "week" | "month")}
            />
          </div>
          <div style={{ flex: 1, minHeight: 0 }}>
            <EChartsBaseChart option={option} height="100%" />
          </div>
        </div>
      ) : (
        !isLoading &&
        !error && (
          <div style={{ textAlign: "center", padding: token.paddingMD }}>
            <Text type="secondary">No trend data available</Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<COQTrendChartConfig>({
  typeId: widgetTypeId("coq-trend-chart"),
  displayName: "COQ Trend Chart",
  description: "Stacked area chart showing planned vs actual COQ categories over time",
  category: "trend",
  icon: <LineChartOutlined />,
  sizeConstraints: {
    minW: 6,
    minH: 3,
    defaultW: 6,
    defaultH: 3,
  },
  component: COQTrendChartComponent,
  defaultConfig: {
    granularity: "month",
  },
});
