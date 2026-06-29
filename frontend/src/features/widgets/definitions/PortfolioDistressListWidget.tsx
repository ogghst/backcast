/**
 * At-Risk Projects widget — ranked portfolio distress list (SPI<0.9 or CPI<0.9).
 *
 * Phase 4 of the global-dashboard-widgets initiative. Ports the `DistressList`
 * component of the legacy `PortfolioPage.tsx` (~L234-319, ~L594-616) — including
 * its client-side pagination (10/page) — into a self-registering widget wrapped
 * in `WidgetShell`. `config.mode` selects schedule-distress (at-risk) vs
 * cost-distress; the title moves to `WidgetShell`'s `title` prop.
 *
 * LOCKED constraints (design doc §5.2, G16/G17):
 *  - Branch FROZEN to `main`/`merged` (G16). NEVER reads `ctx.branch`/`ctx.mode`.
 *  - Reads controlDate from `ctx.portfolioFilter?.controlDate` (NOT the store
 *    directly); null = today. Works when `portfolioFilter` is undefined (host
 *    Phase 8 not yet wired) — defaults to today/main/merged.
 *
 * Source design: docs/03-project-plan/iterations/2026-06-29-global-dashboard-widgets/
 *   global-dashboard-widgets-design.md §5.2 (portfolio-distress-list) + §7 Phase 4.
 */

import { WarningOutlined } from "@ant-design/icons";
import { Empty, Pagination, Space, Tag, Typography, theme } from "antd";
import { Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import type { FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import { usePortfolioEVM } from "@/features/portfolio/api/usePortfolioEVM";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { formatValue } from "@/features/evm/utils/formatters";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";
import type { PortfolioProjectMetrics } from "@/api/generated/models/PortfolioProjectMetrics";
import {
  RED_BAND_THRESHOLD,
  cpiCostDistress,
} from "./shared/portfolioMetrics";

interface PortfolioDistressListConfig {
  /** "schedule" = At-Risk (SPI<0.9); "cost" = Cost-Distress (CPI<0.9). */
  mode: "schedule" | "cost";
  /** Page size for the in-widget pagination (default 10). */
  pageSize?: number;
}

const PortfolioDistressListComponent: FC<
  WidgetComponentProps<PortfolioDistressListConfig>
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
  const { spacing } = useThemeTokens();
  const ctx = useDashboardContext();

  // G16: branch FROZEN to main/merged (never reads ctx.branch / ctx.mode).
  const { data, isLoading, error, refetch } = usePortfolioEVM({
    controlDate: ctx.portfolioFilter?.controlDate ?? null,
    branch: "main",
    branchMode: "merged",
  });

  const mode = config.mode ?? "schedule";
  const pageSize = config.pageSize ?? 10;

  const projects = useMemo<PortfolioProjectMetrics[]>(() => {
    if (mode === "cost") return cpiCostDistress(data?.projects ?? []);
    return data?.at_risk_projects ?? [];
  }, [mode, data?.projects, data?.at_risk_projects]);

  const indexKey: "cpi" | "spi" = mode === "cost" ? "cpi" : "spi";
  const title =
    mode === "cost"
      ? `Cost-Distress Projects (CPI < ${RED_BAND_THRESHOLD})`
      : `At-Risk Projects (SPI < ${RED_BAND_THRESHOLD})`;
  const emptyDescription =
    mode === "cost" ? "No cost-distress projects" : "No at-risk projects";

  // Pagination state — ported verbatim from the legacy DistressList (incl. the
  // documented react-hooks/set-state-in-effect reset on data change).
  const [page, setPage] = useState(1);
  const [pagePageSize, setPagePageSize] = useState(pageSize);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset on data change (documented React exception)
    setPage(1);
  }, [projects]);

  const pageItems = projects.slice((page - 1) * pagePageSize, page * pagePageSize);

  return (
    <WidgetShell
      instanceId={instanceId}
      title={title}
      icon={<WarningOutlined />}
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
      {projects.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyDescription} />
      ) : (
        <>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {pageItems.map((p) => (
              <li
                key={p.project_id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: spacing.sm,
                  padding: `${spacing.xs}px 0`,
                  borderBottom: `1px solid ${token.colorBorderSecondary}`,
                }}
              >
                <Link to={`/projects/${p.project_id}`}>{p.name}</Link>
                <Space size={spacing.sm}>
                  <Typography.Text type="secondary">
                    {indexKey.toUpperCase()} {formatValue(p[indexKey] ?? null, "number")}
                  </Typography.Text>
                  <Tag color="error">At Risk</Tag>
                </Space>
              </li>
            ))}
          </ul>
          {projects.length > pagePageSize && (
            <div style={{ display: "flex", justifyContent: "center", marginTop: token.marginLG }}>
              <Pagination
                current={page}
                pageSize={pagePageSize}
                total={projects.length}
                onChange={(p, ps) => {
                  setPage(p);
                  setPagePageSize(ps);
                }}
                showSizeChanger={false}
                size="small"
              />
            </div>
          )}
        </>
      )}
    </WidgetShell>
  );
};

registerWidget<PortfolioDistressListConfig>({
  typeId: widgetTypeId("portfolio-distress-list"),
  displayName: "At-Risk Projects",
  description:
    "Ranked portfolio distress list — At-Risk (SPI<0.9) in schedule mode or Cost-Distress (CPI<0.9) in cost mode, paginated 10/page.",
  category: "diagnostic",
  icon: <WarningOutlined />,
  sizeConstraints: {
    minW: 3,
    minH: 4,
    defaultW: 6,
    defaultH: 5,
  },
  scope: "portfolio",
  requiredPermission: "portfolio-read",
  component: PortfolioDistressListComponent,
  defaultConfig: {
    mode: "schedule",
    pageSize: 10,
  },
});
