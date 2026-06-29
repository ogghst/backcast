/**
 * Portfolio KPIs widget — portfolio-scope EVM roll-up KPI tiles.
 *
 * Phase 4 of the global-dashboard-widgets initiative. Ports the
 * `renderKpis` section of the legacy `PortfolioPage.tsx` (~L532-564) into a
 * self-registering widget wrapped in `WidgetShell`.
 *
 * LOCKED constraints (design doc §5.2, G16/G17):
 *  - Branch is FROZEN to `main`/`merged` (G16). NEVER reads `ctx.branch`/`ctx.mode`
 *    — TimeMachine is global shared state and coupling it here would leak a
 *    project-branch selection into the portfolio dashboard.
 *  - Reads the control date from `ctx.portfolioFilter?.controlDate` (NOT the
 *    `usePortfolioFilterStore` directly); falls back to null (= today) when the
 *    host (Phase 8) has not populated `portfolioFilter` yet.
 *
 * Source design: docs/03-project-plan/iterations/2026-06-29-global-dashboard-widgets/
 *   global-dashboard-widgets-design.md §5.2 (portfolio-kpi) + §7 Phase 4.
 */

import { DashboardOutlined } from "@ant-design/icons";
import { Card, Col, Row, Statistic, theme } from "antd";
import type { FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import { usePortfolioEVM } from "@/features/portfolio/api/usePortfolioEVM";
import { MetricCard } from "@/features/evm/components/MetricCard";
import type { MetricMetadata } from "@/features/evm/types";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";
import {
  CPI_METADATA,
  SPI_METADATA,
  VAC_METADATA,
  TCPI_METADATA,
  cpiCostDistress,
  ragBand,
  ragToStatus,
} from "./shared/portfolioMetrics";

/** KPI metric key — the portfolio quad. (Deliberately omits `LeadMetric`'s
 * doomed extra members; this widget only ever renders the 4 portfolio indices.) */
type PortfolioMetric = "cpi" | "spi" | "vac" | "tcpi";

interface PortfolioKpiConfig {
  /** Which portfolio indices to render, in order. Defaults to all four. */
  metrics: PortfolioMetric[];
  /** Optional distress-count tile. "none" (default) hides it. */
  showDistressCount?: "none" | "cost" | "schedule";
}

/** Metric-key → metadata lookup (mirrors the legacy `LEAD_METADATA` record). */
const METRIC_METADATA: Record<PortfolioMetric, MetricMetadata> = {
  cpi: CPI_METADATA,
  spi: SPI_METADATA,
  vac: VAC_METADATA,
  tcpi: TCPI_METADATA,
};

/** VAC band for the tile status (≥0 good, <0 bad). Ported verbatim from PortfolioPage. */
function vacStatus(vac: number | null | undefined): "good" | "warning" | "bad" {
  if (vac === null || vac === undefined) return "warning";
  return vac >= 0 ? "good" : "bad";
}

/** TCPI band for the tile status (≥1.0 good, [0.9,1.0) warning, <0.9 bad). Ported verbatim. */
function tcpiStatus(
  tcpi: number | null | undefined,
): "good" | "warning" | "bad" {
  if (tcpi === null || tcpi === undefined) return "warning";
  if (tcpi >= 1.0) return "good";
  if (tcpi >= 0.9) return "warning";
  return "bad";
}

const PortfolioKpiComponent: FC<WidgetComponentProps<PortfolioKpiConfig>> = ({
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
  const ctx = useDashboardContext();

  // G16: branch FROZEN to main/merged (never reads ctx.branch / ctx.mode).
  // controlDate from ctx.portfolioFilter (G17-equivalent wiring for EVM).
  const { data, isLoading, error, refetch } = usePortfolioEVM({
    controlDate: ctx.portfolioFilter?.controlDate ?? null,
    branch: "main",
    branchMode: "merged",
  });

  const summary = data?.summary;
  const summaryCpi = summary?.cpi ?? null;
  const summarySpi = summary?.spi ?? null;

  const statusFor = (metric: PortfolioMetric): "good" | "warning" | "bad" => {
    switch (metric) {
      case "cpi":
      case "spi":
        return ragToStatus(ragBand(summaryCpi, summarySpi));
      case "vac":
        return vacStatus(summary?.vac);
      case "tcpi":
        return tcpiStatus(summary?.tcpi);
    }
  };

  const valueFor = (metric: PortfolioMetric): number | null => {
    switch (metric) {
      case "cpi":
        return summaryCpi;
      case "spi":
        return summarySpi;
      case "vac":
        return summary?.vac ?? null;
      case "tcpi":
        return summary?.tcpi ?? null;
    }
  };

  const showDistress = config.showDistressCount ?? "none";
  const distressCount =
    showDistress === "cost"
      ? cpiCostDistress(data?.projects ?? []).length
      : showDistress === "schedule"
        ? (data?.at_risk_projects ?? []).length
        : 0;

  const metrics = config.metrics ?? ["cpi", "spi", "vac", "tcpi"];
  // When the distress tile is shown it takes half the row, matching the legacy
  // `layout.leadDistressCount` 12-span split.
  const tileSpan = showDistress !== "none" ? 12 : 6;

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Portfolio KPIs"
      icon={<DashboardOutlined />}
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
      {summary ? (
        <Row gutter={[token.paddingMD, token.paddingMD]}>
          {metrics.map((metric) => (
            <Col key={metric} xs={24} sm={12} lg={tileSpan}>
              <MetricCard
                metadata={METRIC_METADATA[metric]}
                value={valueFor(metric)}
                status={statusFor(metric)}
                size="medium"
              />
            </Col>
          ))}
          {showDistress !== "none" && (
            <Col xs={24} sm={12} lg={12}>
              <Card variant="outlined" style={{ height: "100%" }}>
                <Statistic
                  title={
                    showDistress === "cost"
                      ? "Cost Distress (CPI < 0.9)"
                      : "At-Risk (SPI < 0.9)"
                  }
                  value={distressCount}
                  valueStyle={
                    distressCount > 0
                      ? { color: token.colorError }
                      : { color: token.colorSuccess }
                  }
                />
              </Card>
            </Col>
          )}
        </Row>
      ) : (
        !isLoading &&
        !error && <span style={{ color: token.colorTextSecondary }}>No portfolio data</span>
      )}
    </WidgetShell>
  );
};

registerWidget<PortfolioKpiConfig>({
  typeId: widgetTypeId("portfolio-kpi"),
  displayName: "Portfolio KPIs",
  description:
    "Portfolio-wide EVM roll-up KPI tiles (CPI, SPI, VAC, TCPI) with an optional at-risk / cost-distress count.",
  category: "summary",
  icon: <DashboardOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 3,
    defaultW: 12,
    defaultH: 3,
    maxW: 12,
  },
  scope: "portfolio",
  requiredPermission: "portfolio-read",
  component: PortfolioKpiComponent,
  defaultConfig: {
    metrics: ["cpi", "spi", "vac", "tcpi"],
    showDistressCount: "none",
  },
});
