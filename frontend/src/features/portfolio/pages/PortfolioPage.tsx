/**
 * Portfolio Dashboard page.
 *
 * Top-level cross-project roll-up of EVM performance + at-risk projects.
 * Route: `/portfolio` (gated by `portfolio-read`).
 *
 * v1 layout: FilterBar (Date + Status + RAG) → 4 KPI tiles (CPI, SPI, VAC,
 * TCPI) → per-project StandardTable → at-risk list.
 *
 * FILTERING IS CLIENT-SIDE (locked decision, functional-analysis.md §13):
 * the server does NOT filter by CPI/SPI. RAG banding + status filtering are
 * applied in-memory to the per-project rows. Table pagination/sort still
 * sync via useTableParams for URL persistence, but the data source is the
 * already-filtered array.
 *
 * The portfolio summary uses the GENERATED EVMMetricsResponse (it carries
 * TCPI, which the hand-written EVM type does not).
 */

import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { Card, Col, Empty, Row, Space, Spin, Statistic, Tag, Typography, theme } from "antd";
import type { ColumnType } from "antd/es/table";
import type { SortOrder } from "antd/es/table/interface";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { PageShell } from "@/components/layout/PageShell";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { MetricCard } from "@/features/evm/components/MetricCard";
import {
  MetricCategory,
  type MetricMetadata,
} from "@/features/evm/types";
import { formatValue } from "@/features/evm/utils/formatters";
import { useAuthStore } from "@/stores/useAuthStore";
import { usePortfolioFilterUrlSync } from "@/stores/usePortfolioFilterUrlSync";
import { usePortfolioFilterStore } from "@/stores/usePortfolioFilterStore";
import { usePortfolioEVM } from "@/features/portfolio/api/usePortfolioEVM";
import { usePortfolioCO } from "@/features/portfolio/api/usePortfolioCO";
import {
  ragBand,
  ragToStatus,
  RED_BAND_THRESHOLD,
  type RagBand,
} from "@/features/portfolio/utils/rag";
import { FilterBar } from "@/features/portfolio/components/FilterBar";
import {
  cpiCostDistress,
  roleLayout,
  type LayoutConfig,
  type LeadMetric,
  type SectionKey,
} from "@/features/portfolio/roleLayout";
import type { PortfolioProjectMetrics } from "@/api/generated/models/PortfolioProjectMetrics";
import type { ChangeOrderStatsResponse } from "@/api/generated/models/ChangeOrderStatsResponse";

// ── KPI metadata (local — not coupled to a project) ────────────────────────
// CPI/SPI/VAC `key` values ARE valid keyof EVMMetricsResponse, so the literals
// satisfy MetricMetadata directly. TCPI is NOT in the hand-written EVM type
// (only the generated one carries it); its `key` needs the documented double
// cast. The field is only used for a11y IDs in MetricCard.

const CPI_METADATA: MetricMetadata = {
  key: "cpi",
  name: "Portfolio CPI",
  description:
    "Cost Performance Index (EV / AC) rolled up across the portfolio. < 1.0 = over budget.",
  category: MetricCategory.PERFORMANCE,
  targetRanges: { min: 0, max: 2, good: 1.0 },
  higherIsBetter: true,
  format: "number",
};

const SPI_METADATA: MetricMetadata = {
  key: "spi",
  name: "Portfolio SPI",
  description:
    "Schedule Performance Index (EV / PV) rolled up across the portfolio. < 1.0 = behind schedule.",
  category: MetricCategory.SCHEDULE,
  targetRanges: { min: 0, max: 2, good: 1.0 },
  higherIsBetter: true,
  format: "number",
};

const VAC_METADATA: MetricMetadata = {
  key: "vac",
  name: "Portfolio VAC",
  description:
    "Variance at Completion (BAC − EAC) in portfolio base currency. Negative = over budget at completion.",
  category: MetricCategory.FORECAST,
  targetRanges: { min: -Infinity, max: Infinity, good: 0 },
  higherIsBetter: true,
  format: "currency",
};

const TCPI_METADATA = {
  key: "tcpi",
  name: "Portfolio TCPI",
  description:
    "To-Complete Performance Index (BAC / EAC). >= 1.0 = on track for the EAC budget; < 1.0 = remaining work must be done more cheaply.",
  category: MetricCategory.PERFORMANCE,
  targetRanges: { min: 0, max: 2, good: 1.0 },
  higherIsBetter: true,
  format: "number",
} as unknown as MetricMetadata;

/** Lead-metric key → KPI tile metadata. */
const LEAD_METADATA: Record<LeadMetric, MetricMetadata> = {
  cpi: CPI_METADATA,
  spi: SPI_METADATA,
  vac: VAC_METADATA,
  tcpi: TCPI_METADATA,
};

// ── Status tag colour (project status → antd Tag color) ────────────────────
const STATUS_TAG_COLOR: Record<string, string> = {
  active: "processing",
  draft: "default",
  completed: "success",
  on_hold: "warning",
};

/** RAG band → antd Tag color. */
const RAG_TAG_COLOR: Record<Exclude<RagBand, "Unknown">, string> = {
  Green: "success",
  Amber: "warning",
  Red: "error",
};

/** VAC band for the KPI tile status (≥0 good, <0 bad). */
function vacStatus(vac: number | null | undefined): "good" | "warning" | "bad" {
  if (vac === null || vac === undefined) return "warning";
  return vac >= 0 ? "good" : "bad";
}

/** TCPI band for the KPI tile status (≥1.0 good, [0.9,1.0) warning, <0.9 bad). */
function tcpiStatus(
  tcpi: number | null | undefined,
): "good" | "warning" | "bad" {
  if (tcpi === null || tcpi === undefined) return "warning";
  if (tcpi >= 1.0) return "good";
  if (tcpi >= 0.9) return "warning";
  return "bad";
}

/** Terminal CO statuses — everything else counts as "open" in the pipeline. */
const TERMINAL_CO_STATUSES = new Set(["Approved", "Rejected", "Closed", "Cancelled"]);

/**
 * Derive the open-pipeline count from the per-status breakdown (every CO whose
 * status is not terminal). Falls back to `total_count` when the breakdown is
 * missing.
 */
function openCOCount(stats: ChangeOrderStatsResponse): number {
  const byStatus = stats.by_status ?? [];
  if (byStatus.length === 0) return stats.total_count ?? 0;
  return byStatus
    .filter((row) => !TERMINAL_CO_STATUSES.has(row.status))
    .reduce((sum, row) => sum + row.count, 0);
}

/**
 * Change-order pipeline summary tiles.
 *
 * Renders portfolio-wide CO KPIs (open count, pending value, approved value,
 * total cost exposure, aging count) sourced from `usePortfolioCO`. The stats
 * are portfolio-wide, so this mirrors the page's client-side-filter philosophy
 * — no extra filter wiring for v1.
 */
function ChangeOrderPipeline({
  stats,
  isLoading,
}: {
  stats?: ChangeOrderStatsResponse;
  isLoading: boolean;
}): React.JSX.Element {
  const { token } = theme.useToken();

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
    <div
      style={{
        background: token.colorBgContainer,
        borderRadius: token.borderRadiusLG,
        padding: token.paddingMD,
        marginBottom: token.paddingMD,
      }}
    >
      <Typography.Title level={5} style={{ marginTop: 0, marginBottom: token.paddingMD }}>
        Change-Order Pipeline
      </Typography.Title>
      {isLoading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: token.paddingMD }}>
          <Spin />
        </div>
      ) : !stats ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No change-order data" />
      ) : (
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
      )}
    </div>
  );
}

/**
 * Ranked distress list — the shared visual pattern behind both the existing
 * At-Risk (SPI<0.9) list and the Phase 2 Cost-Distress (CPI<0.9) list.
 *
 * Renders a simple ranked list of projects whose index is below the given
 * threshold, with the index value + a status tag per row. Mirrors the original
 * inline at-risk markup so the look is identical.
 */
function DistressList({
  title,
  projects,
  indexKey,
  emptyDescription,
}: {
  title: React.ReactNode;
  projects: PortfolioProjectMetrics[];
  indexKey: "cpi" | "spi";
  emptyDescription: string;
}): React.JSX.Element {
  const { spacing } = useThemeTokens();
  const { token } = theme.useToken();

  return (
    <div
      style={{
        background: token.colorBgContainer,
        borderRadius: token.borderRadiusLG,
        padding: spacing.md,
      }}
    >
      <Typography.Title level={5} style={{ marginTop: 0 }}>
        {title}
      </Typography.Title>
      {projects.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={emptyDescription}
        />
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {projects.map((p) => (
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
      )}
    </div>
  );
}

/**
 * Portfolio Dashboard — top-level EVM roll-up + at-risk projects.
 *
 * @example
 * ```tsx
 * <Route path="/portfolio" element={<PortfolioPage />} />
 * ```
 */
export function PortfolioPage(): React.JSX.Element {
  const { token } = theme.useToken();
  const { spacing } = useThemeTokens();

  // Role-curated layout (Phase 2). Unknown/null roles fall back to `default`.
  const role = useAuthStore((s) => s.user?.role) ?? "default";
  const layout: LayoutConfig = roleLayout[role] ?? roleLayout.default;

  // Wire the filter store to the URL (one-time on this page).
  usePortfolioFilterUrlSync();

  const controlDate = usePortfolioFilterStore((s) => s.controlDate);
  const statusFilter = usePortfolioFilterStore((s) => s.status);
  const ragFilter = usePortfolioFilterStore((s) => s.rag);

  const { data, isLoading } = usePortfolioEVM({
    controlDate,
    branch: "main",
    branchMode: "merged",
  });

  // Portfolio-wide CO pipeline stats (no filter wiring for v1 — see G17).
  const { data: coStats, isLoading: coLoading } = usePortfolioCO({
    agingThresholdDays: 7,
  });

  const { tableParams, handleTableChange } = useTableParams<PortfolioProjectMetrics>();

  // Client-side filtering (status + RAG) per the locked decision.
  const filteredProjects = useMemo(() => {
    const rows = data?.projects ?? [];
    return rows.filter((row) => {
      if (statusFilter && statusFilter.length > 0) {
        if (!statusFilter.includes(row.status)) return false;
      }
      if (ragFilter && ragFilter.length > 0) {
        const band = ragBand(row.cpi ?? null, row.spi ?? null);
        // "Unknown" bands never match a RAG filter selection.
        if (band === "Unknown" || !ragFilter.includes(band)) return false;
      }
      return true;
    });
  }, [data?.projects, statusFilter, ragFilter]);

  // Resolved sort: URL-persisted sort wins over the role default. When the URL
  // carries `sort_field`/`sort_order` the user has actively sorted, so the role
  // default is only an initial sort applied on first load.
  //
  // `tableParams.sortOrder` is typed `string` (URL-sourced) but antd columns
  // expect the `SortOrder` union; the value only ever lands here via antd's own
  // onChange, so the cast is safe.
  const resolvedSort = useMemo(():
    | { field: string; order: SortOrder }
    | null => {
    if (tableParams.sortField && tableParams.sortOrder) {
      return {
        field: tableParams.sortField,
        order: tableParams.sortOrder as SortOrder,
      };
    }
    return layout.defaultSort
      ? { field: layout.defaultSort.field, order: layout.defaultSort.order }
      : null;
  }, [tableParams.sortField, tableParams.sortOrder, layout.defaultSort]);

  const columns = useMemo<ColumnType<PortfolioProjectMetrics>[]>(
    () => [
      {
        title: "Project",
        dataIndex: "name",
        key: "name",
        render: (_: unknown, record) => (
          <Link to={`/projects/${record.project_id}`}>{record.name}</Link>
        ),
        sorter: (a, b) => a.name.localeCompare(b.name),
        sortOrder:
          resolvedSort?.field === "name" ? resolvedSort.order : undefined,
        ellipsis: true,
      },
      {
        title: "Status",
        dataIndex: "status",
        key: "status",
        width: 130,
        render: (status: string) => (
          <Tag color={STATUS_TAG_COLOR[status] ?? "default"}>
            {status.replace(/_/g, " ")}
          </Tag>
        ),
        sorter: (a, b) => a.status.localeCompare(b.status),
        sortOrder:
          resolvedSort?.field === "status" ? resolvedSort.order : undefined,
      },
      {
        title: "CPI",
        dataIndex: "cpi",
        key: "cpi",
        width: 100,
        align: "right",
        render: (cpi: number | null | undefined) =>
          formatValue(cpi ?? null, "number"),
        sorter: (a, b) => (a.cpi ?? -Infinity) - (b.cpi ?? -Infinity),
        sortOrder:
          resolvedSort?.field === "cpi" ? resolvedSort.order : undefined,
      },
      {
        title: "SPI",
        dataIndex: "spi",
        key: "spi",
        width: 100,
        align: "right",
        render: (spi: number | null | undefined) =>
          formatValue(spi ?? null, "number"),
        sorter: (a, b) => (a.spi ?? -Infinity) - (b.spi ?? -Infinity),
        sortOrder:
          resolvedSort?.field === "spi" ? resolvedSort.order : undefined,
      },
      {
        title: "VAC",
        dataIndex: "vac",
        key: "vac",
        width: 140,
        align: "right",
        render: (vac: number | null | undefined) =>
          formatValue(vac ?? null, "currency", "EUR"),
        sorter: (a, b) => (a.vac ?? -Infinity) - (b.vac ?? -Infinity),
        sortOrder:
          resolvedSort?.field === "vac" ? resolvedSort.order : undefined,
      },
      {
        title: "Contract Value",
        dataIndex: "contract_value",
        key: "contract_value",
        width: 160,
        align: "right",
        render: (cv: number | null | undefined) =>
          formatValue(cv ?? null, "currency", "EUR"),
        sorter: (a, b) => (a.contract_value ?? -Infinity) - (b.contract_value ?? -Infinity),
        sortOrder:
          resolvedSort?.field === "contract_value"
            ? resolvedSort.order
            : undefined,
      },
      {
        title: "RAG",
        key: "rag",
        width: 100,
        align: "center",
        render: (_: unknown, record) => {
          const band = ragBand(record.cpi ?? null, record.spi ?? null);
          if (band === "Unknown") return <Tag>Unknown</Tag>;
          return <Tag color={RAG_TAG_COLOR[band]}>{band}</Tag>;
        },
      },
    ],
    [resolvedSort],
  );

  const summary = data?.summary;
  const summaryCpi = summary?.cpi ?? null;
  const summarySpi = summary?.spi ?? null;

  const atRiskProjects = data?.at_risk_projects ?? [];
  const costDistressProjects = useMemo(
    () => cpiCostDistress(data?.projects ?? []),
    [data?.projects],
  );

  // KPI tile status helpers — CPI/SPI share the RAG band, VAC/TCPI have their own.
  const leadStatusFor = (metric: LeadMetric): "good" | "warning" | "bad" => {
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

  const leadValueFor = (metric: LeadMetric): number | null => {
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

  // Distress count for the role's lead row (cost-controller → CPI<0.9,
  // pmo-director → SPI<0.9). Derived from the (unfiltered) portfolio breakdown.
  const distressCount = layout.leadDistressCount
    ? layout.leadDistressCount === "cost"
      ? costDistressProjects.length
      : atRiskProjects.length
    : 0;

  /** Render the lead KPI tiles row. */
  const renderKpis = (): React.JSX.Element => (
    <Row gutter={[spacing.md, spacing.md]} style={{ marginBottom: spacing.md }}>
      {layout.leadMetrics.map((metric) => (
        <Col key={metric} xs={24} sm={12} lg={layout.leadDistressCount ? 12 : 6}>
          <MetricCard
            metadata={LEAD_METADATA[metric]}
            value={leadValueFor(metric)}
            status={leadStatusFor(metric)}
            size="medium"
          />
        </Col>
      ))}
      {layout.leadDistressCount && (
        <Col xs={24} sm={12} lg={12}>
          <Card variant="outlined" style={{ height: "100%" }}>
            <Statistic
              title={
                layout.leadDistressCount === "cost"
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
  );

  /** Render the CO pipeline section. */
  const renderCoPipeline = (): React.JSX.Element => (
    <div style={{ marginBottom: spacing.md }}>
      <ChangeOrderPipeline stats={coStats} isLoading={coLoading} />
    </div>
  );

  /** Render the per-project table section. */
  const renderTable = (): React.JSX.Element => (
    <div
      style={{
        background: token.colorBgContainer,
        borderRadius: token.borderRadiusLG,
        padding: spacing.md,
        marginBottom: spacing.md,
      }}
    >
      <StandardTable<PortfolioProjectMetrics>
        rowKey="project_id"
        columns={columns}
        dataSource={filteredProjects}
        tableParams={tableParams}
        onChange={handleTableChange}
        size="middle"
      />
    </div>
  );

  /** Render the at-risk (SPI<0.9) section. */
  const renderAtRisk = (): React.JSX.Element => (
    <div style={{ marginBottom: spacing.md }}>
      <DistressList
        title={`At-Risk Projects (SPI < ${RED_BAND_THRESHOLD})`}
        projects={atRiskProjects}
        indexKey="spi"
        emptyDescription="No at-risk projects"
      />
    </div>
  );

  /** Render the cost-distress (CPI<0.9) section. */
  const renderCostDistress = (): React.JSX.Element => (
    <div style={{ marginBottom: spacing.md }}>
      <DistressList
        title={`Cost-Distress Projects (CPI < ${RED_BAND_THRESHOLD})`}
        projects={costDistressProjects}
        indexKey="cpi"
        emptyDescription="No cost-distress projects"
      />
    </div>
  );

  const sectionRenderers: Record<SectionKey, () => React.JSX.Element> = {
    kpis: renderKpis,
    coPipeline: renderCoPipeline,
    table: renderTable,
    atRisk: renderAtRisk,
    costDistress: renderCostDistress,
  };

  return (
    <PageWrapper>
      <PageShell title={layout.title}>
        <FilterBar />

        {isLoading ? (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              padding: spacing.xl,
            }}
          >
            <Spin />
          </div>
        ) : !data || (data.projects ?? []).length === 0 ? (
          <Empty description="No portfolio data available" />
        ) : (
          <>
            {layout.sectionOrder.map((section) => (
              <React.Fragment key={section}>
                {sectionRenderers[section]()}
              </React.Fragment>
            ))}
          </>
        )}
      </PageShell>
    </PageWrapper>
  );
}

export default PortfolioPage;
