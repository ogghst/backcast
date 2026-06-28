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

import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Card, Col, Empty, Row, Space, Spin, Statistic, Tag, Typography, theme } from "antd";
import type { ColumnType } from "antd/es/table";
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
import { usePortfolioFilterUrlSync } from "@/stores/usePortfolioFilterUrlSync";
import { usePortfolioFilterStore } from "@/stores/usePortfolioFilterStore";
import { usePortfolioEVM } from "@/features/portfolio/api/usePortfolioEVM";
import { usePortfolioCO } from "@/features/portfolio/api/usePortfolioCO";
import {
  ragBand,
  ragToStatus,
  type RagBand,
} from "@/features/portfolio/utils/rag";
import { FilterBar } from "@/features/portfolio/components/FilterBar";
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
    [],
  );

  const summary = data?.summary;
  const summaryCpi = summary?.cpi ?? null;
  const summarySpi = summary?.spi ?? null;

  const atRiskProjects = data?.at_risk_projects ?? [];

  return (
    <PageWrapper>
      <PageShell title="Portfolio Dashboard">
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
            {/* KPI tiles row */}
            <Row gutter={[spacing.md, spacing.md]} style={{ marginBottom: spacing.md }}>
              <Col xs={24} sm={12} lg={6}>
                <MetricCard
                  metadata={CPI_METADATA}
                  value={summaryCpi}
                  status={ragToStatus(ragBand(summaryCpi, summarySpi))}
                  size="medium"
                />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <MetricCard
                  metadata={SPI_METADATA}
                  value={summarySpi}
                  status={ragToStatus(ragBand(summaryCpi, summarySpi))}
                  size="medium"
                />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <MetricCard
                  metadata={VAC_METADATA}
                  value={summary?.vac ?? null}
                  status={vacStatus(summary?.vac)}
                  size="medium"
                />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <MetricCard
                  metadata={TCPI_METADATA}
                  value={summary?.tcpi ?? null}
                  status={tcpiStatus(summary?.tcpi)}
                  size="medium"
                />
              </Col>
            </Row>

            {/* Change-order pipeline (portfolio-wide; G17). */}
            <ChangeOrderPipeline stats={coStats} isLoading={coLoading} />

            {/* Per-project table — filtering is client-side (server does NOT filter by CPI/SPI). */}
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

            {/* At-risk projects (SPI < 0.9) */}
            <div
              style={{
                background: token.colorBgContainer,
                borderRadius: token.borderRadiusLG,
                padding: spacing.md,
              }}
            >
              <Typography.Title level={5} style={{ marginTop: 0 }}>
                At-Risk Projects (SPI &lt; 0.9)
              </Typography.Title>
              {atRiskProjects.length === 0 ? (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="No at-risk projects"
                />
              ) : (
                <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {atRiskProjects.map((p) => (
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
                          SPI {formatValue(p.spi ?? null, "number")}
                        </Typography.Text>
                        <Tag color="error">At Risk</Tag>
                      </Space>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </PageShell>
    </PageWrapper>
  );
}

export default PortfolioPage;
