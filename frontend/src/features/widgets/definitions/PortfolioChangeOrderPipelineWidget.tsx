/**
 * Change-Order Pipeline widget — portfolio-wide CO KPI tiles.
 *
 * Phase 4 of the global-dashboard-widgets initiative. Ports the
 * `ChangeOrderPipeline` component of the legacy `PortfolioPage.tsx` (~L127-224)
 * into a self-registering widget wrapped in `WidgetShell`.
 *
 * LOCKED constraints (design doc §5.2, G16/G17):
 *  - Branch FROZEN to `main` (G16). NEVER reads `ctx.branch`/`ctx.mode`.
 *  - G17 BEHAVIORAL CHANGE vs the legacy page: this widget now respects the
 *    control date by passing `asOf = ctx.portfolioFilter?.controlDate` into
 *    `usePortfolioCO`. The old `PortfolioPage` called `usePortfolioCO` with NO
 *    `asOf`, so the CO pipeline ignored the controlDate filter (latent gap).
 *    This is a positive fix — the pipeline snapshot now aligns with the EVM
 *    tiles. Reads `ctx.portfolioFilter` (NOT the store directly); null = now.
 *
 * Source design: docs/03-project-plan/iterations/2026-06-29-global-dashboard-widgets/
 *   global-dashboard-widgets-design.md §5.2 (portfolio-co-pipeline) + §7 Phase 4 + G17.
 */

import { SwapOutlined } from "@ant-design/icons";
import { Card, Col, Row, Statistic, theme } from "antd";
import type { FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import { usePortfolioCO } from "@/features/portfolio/api/usePortfolioCO";
import { formatValue } from "@/features/evm/utils/formatters";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";
import type { ChangeOrderStatsResponse } from "@/api/generated/models/ChangeOrderStatsResponse";

interface PortfolioChangeOrderPipelineConfig {
  agingThresholdDays?: number;
}

/** Terminal CO statuses — everything else counts as "open" in the pipeline. Ported verbatim. */
const TERMINAL_CO_STATUSES = new Set([
  "Approved",
  "Rejected",
  "Closed",
  "Cancelled",
]);

/**
 * Derive the open-pipeline count from the per-status breakdown (every CO whose
 * status is not terminal). Falls back to `total_count` when the breakdown is
 * missing. Ported verbatim from PortfolioPage.
 */
function openCOCount(stats: ChangeOrderStatsResponse): number {
  const byStatus = stats.by_status ?? [];
  if (byStatus.length === 0) return stats.total_count ?? 0;
  return byStatus
    .filter((row) => !TERMINAL_CO_STATUSES.has(row.status))
    .reduce((sum, row) => sum + row.count, 0);
}

const PortfolioChangeOrderPipelineComponent: FC<
  WidgetComponentProps<PortfolioChangeOrderPipelineConfig>
> = ({
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

  // G16: branch FROZEN to main (never reads ctx.branch / ctx.mode).
  // G17: asOf now wired to the control date (legacy page passed no asOf).
  const { data: stats, isLoading, error, refetch } = usePortfolioCO({
    asOf: ctx.portfolioFilter?.controlDate ?? null,
    branch: "main",
    agingThresholdDays: config.agingThresholdDays ?? 7,
  });

  // `transformCOStatsNumeric` already coerced these to numbers at runtime; the
  // generated type still declares `string`, so parseFloat + null-guard keeps
  // the value prop clean (Statistic's `valueType` is `number | string`).
  const toNum = (v: string | number | null | undefined): number | undefined => {
    if (v === null || v === undefined) return undefined;
    const n = typeof v === "number" ? v : parseFloat(v);
    return Number.isNaN(n) ? undefined : n;
  };

  const openCount = stats ? openCOCount(stats) : 0;
  const pendingValue = toNum(stats?.pending_value);
  const approvedValue = toNum(stats?.approved_value);
  const costExposure = toNum(stats?.total_cost_exposure);
  const agingCount = stats?.aging_items?.length ?? 0;

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Change-Order Pipeline"
      icon={<SwapOutlined />}
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
      {stats ? (
        <Row gutter={[token.paddingMD, token.paddingMD]}>
          <Col xs={24} sm={12} lg={6}>
            <Card variant="outlined" style={{ height: "100%" }}>
              <Statistic title="Open COs" value={openCount} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card variant="outlined" style={{ height: "100%" }}>
              <Statistic
                title="Pending Value"
                value={pendingValue}
                formatter={(v) =>
                  formatValue(typeof v === "number" ? v : null, "currency", "EUR")
                }
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card variant="outlined" style={{ height: "100%" }}>
              <Statistic
                title="Approved Value"
                value={approvedValue}
                formatter={(v) =>
                  formatValue(typeof v === "number" ? v : null, "currency", "EUR")
                }
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card variant="outlined" style={{ height: "100%" }}>
              <Statistic
                title="Cost Exposure"
                value={costExposure}
                formatter={(v) =>
                  formatValue(typeof v === "number" ? v : null, "currency", "EUR")
                }
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card variant="outlined" style={{ height: "100%" }}>
              <Statistic
                title={`Aging (> ${stats.aging_threshold_days ?? 7}d)`}
                value={agingCount}
                valueStyle={
                  agingCount > 0 ? { color: token.colorWarning } : undefined
                }
              />
            </Card>
          </Col>
        </Row>
      ) : (
        !isLoading &&
        !error && <span style={{ color: token.colorTextSecondary }}>No change-order data</span>
      )}
    </WidgetShell>
  );
};

registerWidget<PortfolioChangeOrderPipelineConfig>({
  typeId: widgetTypeId("portfolio-co-pipeline"),
  displayName: "Change-Order Pipeline",
  description:
    "Portfolio-wide change-order pipeline KPIs: open count, pending value, approved value, total cost exposure, and aging count.",
  category: "summary",
  icon: <SwapOutlined />,
  sizeConstraints: {
    minW: 6,
    minH: 3,
    defaultW: 12,
    defaultH: 3,
    maxW: 12,
  },
  scope: "portfolio",
  // G14 (capstone F-7): gated on `portfolio-read` to match the sole data route
  // (`GET /change-orders/portfolio-stats` enforces portfolio-read), per D2
  // ("gate on the permission the data route enforces"). Aligns this widget with
  // the other 3 portfolio widgets.
  requiredPermission: "portfolio-read",
  component: PortfolioChangeOrderPipelineComponent,
  defaultConfig: {
    agingThresholdDays: 7,
  },
});
