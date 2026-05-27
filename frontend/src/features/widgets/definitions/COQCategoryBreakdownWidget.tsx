import { PieChartOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import { useCostEventSummary } from "@/features/cost-events/api/useCostEvents";
import { useProject } from "@/features/projects/api/useProjects";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";
import { formatCompactCurrency } from "@/utils/formatters";

const { Text } = Typography;

interface COQCategoryBreakdownConfig {
  currency?: string;
}

const COQCategoryBreakdownComponent: FC<WidgetComponentProps<COQCategoryBreakdownConfig>> = ({
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

  const { data: summary, isLoading: summaryLoading, error: summaryError, refetch: refetchSummary } = useCostEventSummary(
    context.projectId,
  );
  const { data: project, isLoading: projectLoading } = useProject(context.projectId);

  const isLoading = summaryLoading || projectLoading;
  const error = summaryError;

  const categories = summary
    ? [
        { name: "Prevention", value: parseFloat(summary.prevention_cost ?? "0") || 0, color: token.colorPrimary },
        { name: "Appraisal", value: parseFloat(summary.appraisal_cost ?? "0") || 0, color: token.colorInfo },
        { name: "Internal Failure", value: parseFloat(summary.internal_failure_cost ?? "0") || 0, color: token.colorWarning },
        { name: "External Failure", value: parseFloat(summary.external_failure_cost ?? "0") || 0, color: token.colorError },
      ]
    : [] as { name: string; value: number; color: string }[];

  const totalCost = categories.reduce((sum, cat) => sum + cat.value, 0);
  const projectBudget = parseFloat(project?.budget || "0") || 0;

  return (
    <WidgetShell
      instanceId={instanceId}
      title="COQ Breakdown (Planned)"
      icon={<PieChartOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetchSummary}
      onConfigure={onConfigure}
      onFullscreen={onFullscreen}
      widgetType={widgetType}
      dashboardName={dashboardName}
    >
      {summary && totalCost > 0 ? (
        <div style={{ padding: `${token.paddingXS}px 0`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%" }}>
          {(() => {
            const size = 130;
            const strokeWidth = 6;
            const radius = (size - strokeWidth) / 2;
            const circumference = 2 * Math.PI * radius;
            const center = size / 2;
            const total = projectBudget > 0 ? projectBudget : totalCost;
            const coqPercent = total > 0 ? Math.round((totalCost / total) * 100) : 0;

            // Build SVG arc segments — each category as % of total (project budget)
            let cumulativeLength = 0;
            const segments = categories
              .filter((cat) => cat.value > 0)
              .map((cat) => {
                const fraction = total > 0 ? cat.value / total : 0;
                const length = fraction * circumference;
                const offset = -cumulativeLength;
                cumulativeLength += length;
                return { ...cat, length, offset };
              });

            return (
              <>
                <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
                  {/* Background track matching antd's track color */}
                  <circle
                    cx={center}
                    cy={center}
                    r={radius}
                    fill="none"
                    stroke={token.colorFillSecondary}
                    strokeWidth={strokeWidth}
                  />
                  {segments.map((seg) => (
                    <circle
                      key={seg.name}
                      cx={center}
                      cy={center}
                      r={radius}
                      fill="none"
                      stroke={seg.color}
                      strokeWidth={strokeWidth}
                      strokeDasharray={`${seg.length} ${circumference - seg.length}`}
                      strokeDashoffset={seg.offset}
                      strokeLinecap="butt"
                    />
                  ))}
                </svg>
                {/* Center label overlaid on the SVG */}
                <div style={{ marginTop: -(size / 2 + 14), marginBottom: size / 2, textAlign: "center" }}>
                  <Text strong style={{ fontSize: token.fontSizeLG, display: "block" }}>
                    {coqPercent}%
                  </Text>
                  <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                    of {formatCompactCurrency(total)}
                  </Text>
                </div>

                {/* Legend */}
                <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: token.paddingXS, marginTop: token.marginSM }}>
                  {categories.map((cat) => (
                    <div key={cat.name} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: cat.color, flexShrink: 0 }} />
                      <Text style={{ fontSize: token.fontSizeSM }}>{cat.name}</Text>
                    </div>
                  ))}
                </div>
              </>
            );
          })()}
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

registerWidget<COQCategoryBreakdownConfig>({
  typeId: widgetTypeId("coq-category-breakdown"),
  displayName: "COQ Category Breakdown",
  description: "Donut chart showing planned COQ by category (budgeted costs)",
  category: "breakdown",
  icon: <PieChartOutlined />,
  sizeConstraints: {
    minW: 3,
    minH: 3,
    defaultW: 3,
    defaultH: 3,
  },
  component: COQCategoryBreakdownComponent,
  defaultConfig: {},
});
