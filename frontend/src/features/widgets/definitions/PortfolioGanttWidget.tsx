/**
 * Portfolio Timeline (Gantt) widget — cross-project start→end span chart.
 *
 * Phase 4 of the global-dashboard-widgets initiative. Renders one bar per
 * portfolio project that has BOTH a start_date and an end_date (the portfolio
 * EVM response now carries these; projects missing either are skipped). Bars
 * are coloured by the project's schedule RAG band (SPI) so a portfolio glance
 * reads at-risk projects instantly.
 *
 * Reuses the shared Gantt engine (`<ScheduleTimeline>` in rows-mode +
 * `defaultCompactConfig`) — the only host-specific concerns supplied here are:
 *   - the GanttRow[] built from `usePortfolioEVM().projects`
 *   - a `barColorFor` override (SPI RAG instead of progression type)
 *   - a `tooltipFormatter` override (project name + status + date range + CPI/SPI)
 *
 * LOCKED constraints (design doc §5.2, G16/G17) — identical to the sibling
 * portfolio widgets:
 *  - Branch FROZEN to `main`/`merged` (G16). NEVER reads `ctx.branch`/`ctx.mode`.
 *  - Reads status / rag from `ctx.portfolioFilter` (NOT the store directly).
 *    When the host (Phase 8) has not populated `portfolioFilter`, all filters
 *    are null → unfiltered (today/main/merged).
 *
 * Currency: the portfolio EVM response is already in the portfolio base
 * currency, and the sibling widgets (`PortfolioProjectsTableWidget`,
 * `PortfolioChangeOrderPipelineWidget`) format as "EUR" — this widget matches
 * that (the tooltip budget line is always 0 here, so the currency is cosmetic,
 * but staying consistent avoids a per-widget base-currency hook that does not
 * exist for portfolio scope).
 *
 * Source design: docs/03-project-plan/iterations/2026-06-29-global-dashboard-widgets/
 *   global-dashboard-widgets-design.md §5.2 (portfolio-gantt) + §7 Phase 4.
 */

import { BarChartOutlined } from "@ant-design/icons";
import { Empty, Typography } from "antd";
import { useMemo, type FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import { usePortfolioEVM } from "@/features/portfolio/api/usePortfolioEVM";
import { useEChartsTheme } from "@/features/evm/utils/echartsTheme";
import type { EChartsColorPalette } from "@/features/evm/utils/echartsTheme";
import { formatValue } from "@/features/evm/utils/formatters";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";
import type { PortfolioProjectMetrics } from "@/api/generated/models/PortfolioProjectMetrics";
import { indexBand, ragBand } from "./shared/portfolioMetrics";
import type { GanttRow } from "@/features/schedule-baselines/components/GanttChart/GanttDataTransformer";
import { ScheduleTimeline } from "@/features/schedule-baselines/components/GanttChart/ScheduleTimeline";
import { defaultCompactConfig } from "@/features/schedule-baselines/components/GanttChart/config";

const { Text } = Typography;

/** Portfolio base currency — matches the sibling portfolio widgets. */
const PORTFOLIO_CURRENCY = "EUR";

interface PortfolioGanttConfig {
  // No configurable knobs yet — reserved for future zoom/density overrides.
  [key: string]: never;
}

/** Format a Date as a short locale date for the tooltip range line. */
function formatDate(d: Date): string {
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

const PortfolioGanttComponent: FC<
  WidgetComponentProps<PortfolioGanttConfig>
> = ({
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
  onFullscreen,
  widgetType,
  dashboardName,
}) => {
  const ctx = useDashboardContext();

  // G16: branch FROZEN to main/merged (never reads ctx.branch / ctx.mode).
  const { data, isLoading, error, refetch } = usePortfolioEVM({
    controlDate: ctx.portfolioFilter?.controlDate ?? null,
    branch: "main",
    branchMode: "merged",
  });

  const { colors, tooltipConfig } = useEChartsTheme();

  const statusFilter = ctx.portfolioFilter?.status ?? null;
  const ragFilter = ctx.portfolioFilter?.rag ?? null;

  // Apply the portfolio status + RAG filter the SAME way the sibling widgets do
  // (verbatim filter predicate from PortfolioProjectsTableWidget). Done before
  // building rows so a filtered-out project never renders a bar.
  const filteredProjects = useMemo(() => {
    const rows = data?.projects ?? [];
    return rows.filter((row) => {
      if (statusFilter && statusFilter.length > 0) {
        if (!statusFilter.includes(row.status)) return false;
      }
      if (ragFilter && ragFilter.length > 0) {
        const band = ragBand(row.cpi ?? null, row.spi ?? null);
        if (band === "Unknown" || !ragFilter.includes(band)) return false;
      }
      return true;
    });
  }, [data?.projects, statusFilter, ragFilter]);

  // Project lookup keyed by project_id so barColorFor / tooltipFormatter can
  // recover the source PortfolioProjectMetrics from a GanttRow (the row's
  // wbsElementId is set to the project_id — see buildRows below).
  const projectById = useMemo(() => {
    const m = new Map<string, PortfolioProjectMetrics>();
    for (const p of filteredProjects) m.set(p.project_id, p);
    return m;
  }, [filteredProjects]);

  // Build GanttRow[]: one row per project that has BOTH start_date and
  // end_date (skip projects with null on either). Sorted ascending by startDate.
  const rows = useMemo<GanttRow[]>(() => {
    return filteredProjects
      .filter(
        (p) => p.start_date != null && p.end_date != null,
      )
      .map((p) => ({
        name: p.name,
        level: 1,
        // costElementId = project_id keeps buildScheduleBaselineIndex
        // well-formed (there are no deps in portfolio mode).
        costElementId: p.project_id,
        wbsElementId: p.project_id,
        wbeCode: "",
        startDate: new Date(p.start_date as string),
        endDate: new Date(p.end_date as string),
        progressionType: null,
        budgetAmount: 0,
        isWbe: false,
        collapsed: false,
        childrenCount: 0,
      }))
      .sort((a, b) => a.startDate!.getTime() - b.startDate!.getTime());
  }, [filteredProjects]);

  // Bar colour: SPI RAG band. Red/amber/green from the theme palette's
  // error/warning/success tokens; neutral (textSecondary) when SPI is null.
  const barColorFor = useMemo(
    () =>
      (row: GanttRow, c: EChartsColorPalette): string => {
        const project = projectById.get(row.wbsElementId);
        const spi = project?.spi ?? null;
        switch (indexBand(spi)) {
          case "Red":
            return c.error;
          case "Amber":
            return c.warning;
          case "Green":
            return c.success;
          default:
            // Unknown (SPI null) — muted so undated-progress projects recede.
            return c.textSecondary;
        }
      },
    [projectById],
  );

  // Tooltip: project name (bold), status, formatted date range, CPI/SPI.
  const tooltipFormatter = useMemo(
    () =>
      (row: GanttRow, _currency: string, c: EChartsColorPalette): string => {
        const project = projectById.get(row.wbsElementId);
        const start = row.startDate!;
        const end = row.endDate!;
        const durationDays = Math.ceil(
          (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24),
        );
        const statusLine = project
          ? `<div style="color:${c.textSecondary};font-size:11px;margin-bottom:4px;">${project.status.replace(/_/g, " ")}</div>`
          : "";
        const cpiLine =
          project && project.cpi != null
            ? `<div style="display:flex;justify-content:space-between;gap:24px;"><span>CPI</span><span style="font-weight:600;">${formatValue(project.cpi, "number")}</span></div>`
            : "";
        const spiLine =
          project && project.spi != null
            ? `<div style="display:flex;justify-content:space-between;gap:24px;"><span>SPI</span><span style="font-weight:600;">${formatValue(project.spi, "number")}</span></div>`
            : "";
        return `<div style="font-weight:600;margin-bottom:4px;">${row.name}</div>
${statusLine}<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Start</span><span style="font-weight:600;">${formatDate(start)}</span>
</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>End</span><span style="font-weight:600;">${formatDate(end)}</span>
</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Duration</span><span style="font-weight:600;">${durationDays} days</span>
</div>
${cpiLine}${spiLine}`;
      },
    [projectById],
  );

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Portfolio Timeline"
      icon={<BarChartOutlined />}
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
      {rows.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Text type="secondary">No projects with start/end dates</Text>
          }
        />
      ) : (
        <ScheduleTimeline
          rows={rows}
          config={defaultCompactConfig}
          barColorFor={barColorFor}
          tooltipFormatter={tooltipFormatter}
          colors={colors}
          currency={PORTFOLIO_CURRENCY}
          tooltipConfig={tooltipConfig}
          height="100%"
          loading={isLoading}
        />
      )}
    </WidgetShell>
  );
};

registerWidget<PortfolioGanttConfig>({
  typeId: widgetTypeId("portfolio-gantt"),
  displayName: "Portfolio Timeline",
  description:
    "Gantt of all projects' start→end spans, coloured by schedule RAG (SPI).",
  category: "schedule",
  icon: <BarChartOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 3,
    defaultW: 6,
    defaultH: 4,
  },
  scope: "portfolio",
  requiredPermission: "portfolio-read",
  component: PortfolioGanttComponent,
  defaultConfig: {},
});
